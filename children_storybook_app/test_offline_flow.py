"""Offline integration checks for the storybook generation flow."""

import os
import unittest
import uuid
from pathlib import Path


os.environ.pop("AGNES_API_KEY", None)
os.environ["LOCAL_IMAGE_FALLBACK"] = "true"

from app import app  # noqa: E402


class OfflineGenerationFlowTest(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.created_paths = []

    def tearDown(self):
        for path in self.created_paths:
            try:
                Path(path).unlink(missing_ok=True)
            except OSError:
                pass

    def test_generate_book_without_external_image_api(self):
        story_id = f"offline-test-{uuid.uuid4()}"
        story = {
            "id": story_id,
            "title": "离线生成测试绘本",
            "author": "自动化测试",
            "chapters": [
                {
                    "title": "第1页",
                    "content": "清晨的花园里，阳光照在小路上，朋友们一起分享温暖的故事。",
                }
            ],
            "chapter_count": 1,
            "word_count": 33,
        }

        response = self.client.post("/api/book/generate", json={"story": story, "style": "cartoon"})
        self.assertEqual(response.status_code, 200)

        payload = response.get_json()
        self.assertTrue(payload["success"], payload.get("message"))

        book = payload["data"]
        self.assertEqual(book["id"], story_id)
        self.assertGreaterEqual(book["page_count"], 3)
        self.assertTrue(Path(book["pdf_path"]).exists())
        self.created_paths.append(book["pdf_path"])

        image_results = book["image_results"]
        self.assertEqual(len(image_results), 1)
        self.assertTrue(image_results[0]["success"])
        self.assertTrue(image_results[0].get("local_fallback"))
        self.assertTrue(Path(image_results[0]["local_path"]).exists())
        self.created_paths.append(image_results[0]["local_path"])

        detail = self.client.get(f"/api/books/{story_id}").get_json()["data"]
        first_page_url = detail["pages"][0]["image_url"]
        self.assertTrue(first_page_url.startswith("/data/books/"))
        self.assertEqual(self.client.get(first_page_url).status_code, 200)

        self.created_paths.extend(page["image"] for page in book["pages"] if page.get("image"))
        self.created_paths.append(Path("data/stories") / f"{story_id}.json")
        self.created_paths.append(Path("data/books") / f"{story_id}.json")


if __name__ == "__main__":
    unittest.main()
