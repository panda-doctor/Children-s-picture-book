"""儿童故事绘本应用 - Flask 主应用"""

import json
import os
import uuid
from pathlib import Path

from flask import (
    Flask, abort, render_template, request, jsonify, send_file,
    send_from_directory, Response, stream_with_context
)
from werkzeug.utils import secure_filename

from config import Config, DATA_DIR, STORIES_DIR, BOOKS_DIR, IMAGES_DIR
from utils.content_filter import validate_story
from utils.story_parser import StoryParser, create_demo_story
from utils.image_generator import generate_book_images, iter_generate_book_images
from utils.layout_engine import create_picture_book

app = Flask(__name__)
app.config.from_object(Config)


def json_response(success: bool, message: str = "", data: dict = None, status_code: int = 200):
    """统一 JSON 响应格式"""
    resp = {
        "success": success,
        "message": message,
        "data": data or {}
    }
    return jsonify(resp), status_code


def asset_url(asset_path: str) -> str:
    """将本地生成资源路径转换为浏览器可访问的 /data/... URL。"""
    if not asset_path:
        return ""

    try:
        relative_path = Path(asset_path).resolve().relative_to(DATA_DIR)
    except (ValueError, OSError):
        normalized = str(asset_path).replace("\\", "/")
        marker = "/data/"
        if marker not in normalized:
            return ""
        relative_path = Path(normalized.split(marker, 1)[1])

    return f"/data/{relative_path.as_posix()}"


def enrich_book_assets(meta: dict) -> dict:
    """给绘本元数据补充前端可直接使用的图片 URL。"""
    enriched = dict(meta)
    enriched_pages = []

    for page in meta.get("pages", []):
        enriched_page = dict(page)
        enriched_page["image_url"] = asset_url(page.get("image", ""))
        enriched_pages.append(enriched_page)

    enriched["pages"] = enriched_pages
    return enriched


@app.route("/")
def index():
    """主页 - 故事录入"""
    return render_template("index.html")


@app.route("/editor")
def editor():
    """故事编辑器页面"""
    return render_template("editor.html")


@app.route("/reader/<book_id>")
def reader(book_id):
    """绘本阅读器页面"""
    return render_template("reader.html", book_id=book_id)


@app.route("/api/story/validate", methods=["POST"])
def api_validate_story():
    """校验故事内容安全性"""
    data = request.get_json() or {}
    title = data.get("title", "").strip()
    content = data.get("content", "").strip()
    author = data.get("author", "").strip()
    
    if not title or not content:
        return json_response(False, "故事标题和正文不能为空", status_code=400)
    
    if len(content) > Config.MAX_STORY_LENGTH:
        return json_response(False, f"故事内容超过最大限制 {Config.MAX_STORY_LENGTH} 字", status_code=400)
    
    result = validate_story(title, content, author)
    return json_response(True, "校验完成", data=result)


@app.route("/api/story/parse", methods=["POST"])
def api_parse_story():
    """解析故事文本并分章节"""
    data = request.get_json() or {}
    title = data.get("title", "未命名故事").strip()
    content = data.get("content", "").strip()
    author = data.get("author", "佚名").strip()
    
    if not content:
        return json_response(False, "故事正文不能为空", status_code=400)
    
    # 先进行安全校验
    safety = validate_story(title, content, author)
    if not safety["safe"] and safety["risk_level"] == "high":
        return json_response(
            False,
            f"故事内容包含不当词汇，请修改后重试：{', '.join(safety['matched_words'])}",
            data={"safety": safety},
            status_code=400
        )
    
    try:
        story = StoryParser.parse_text(content, title, author)
        story["safety"] = safety
        return json_response(True, "故事解析成功", data=story)
    except Exception as e:
        return json_response(False, f"故事解析失败: {str(e)}", status_code=500)


@app.route("/api/story/upload", methods=["POST"])
def api_upload_story():
    """上传故事文件"""
    if "file" not in request.files:
        return json_response(False, "未找到上传文件", status_code=400)
    
    file = request.files["file"]
    if file.filename == "":
        return json_response(False, "未选择文件", status_code=400)
    
    filename = secure_filename(file.filename)
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    
    if f".{ext}" not in Config.UPLOAD_EXTENSIONS:
        return json_response(False, f"不支持的文件格式: {ext}，仅支持 {', '.join(Config.UPLOAD_EXTENSIONS)}", status_code=400)
    
    try:
        file_content = file.read()
        story = StoryParser.parse_file(file_content, filename)
        
        # 安全校验
        all_content = "\n".join([c["content"] for c in story["chapters"]])
        safety = validate_story(story["title"], all_content, story["author"])
        story["safety"] = safety
        
        if not safety["safe"] and safety["risk_level"] == "high":
            return json_response(
                False,
                f"故事内容包含不当词汇：{', '.join(safety['matched_words'])}",
                data={"story": story, "safety": safety},
                status_code=400
            )
        
        # 保存故事到本地
        story_path = STORIES_DIR / f"{story['id']}.json"
        with open(story_path, "w", encoding="utf-8") as f:
            json.dump(story, f, ensure_ascii=False, indent=2)
        
        return json_response(True, "故事上传成功", data=story)
    except Exception as e:
        return json_response(False, f"文件解析失败: {str(e)}", status_code=500)


@app.route("/api/story/save", methods=["POST"])
def api_save_story():
    """保存故事数据"""
    data = request.get_json() or {}
    
    if not data.get("chapters"):
        return json_response(False, "故事章节数据不能为空", status_code=400)
    
    try:
        if "id" not in data:
            data["id"] = str(uuid.uuid4())
        
        story_path = STORIES_DIR / f"{data['id']}.json"
        with open(story_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return json_response(True, "故事保存成功", data={"id": data["id"], "path": str(story_path)})
    except Exception as e:
        return json_response(False, f"保存失败: {str(e)}", status_code=500)


@app.route("/api/book/generate", methods=["POST"])
def api_generate_book():
    """生成绘本（插画 + 排版）"""
    data = request.get_json() or {}
    story = data.get("story")
    style = data.get("style", "cartoon")
    
    if not story:
        return json_response(False, "故事数据不能为空", status_code=400)
    
    if not story.get("chapters"):
        return json_response(False, "故事章节不能为空", status_code=400)
    
    # 保存故事
    story_id = story.get("id") or str(uuid.uuid4())
    story["id"] = story_id
    story_path = STORIES_DIR / f"{story_id}.json"
    with open(story_path, "w", encoding="utf-8") as f:
        json.dump(story, f, ensure_ascii=False, indent=2)
    
    # 生成插画
    def progress_callback(current, total, chapter):
        print(f"[进度] 正在生成第 {current}/{total} 页插画：{chapter.get('title', '')}")
    
    image_results = generate_book_images(story, style, progress_callback)
    
    # 检查是否有生成失败的图片
    failed = [r for r in image_results if not r.get("success")]
    if failed:
        errors = [f"{r.get('chapter', '?')}: {r.get('error', '未知错误')}" for r in failed]
        print(f"[警告] 部分插画生成失败: {errors}")
    
    # 排版生成绘本
    try:
        book_meta = create_picture_book(story, image_results)
        book_meta["image_results"] = image_results
        return json_response(True, "绘本生成成功", data=book_meta)
    except Exception as e:
        return json_response(False, f"绘本排版失败: {str(e)}", status_code=500)


@app.route("/api/book/generate/stream", methods=["POST"])
def api_generate_book_stream():
    """生成绘本（流式版）：以 SSE 逐页推送插画生成进度，最后推送绘本结果。

    前端用 fetch + ReadableStream 消费，事件为 `data: {json}\\n\\n` 格式。
    """
    data = request.get_json() or {}
    story = data.get("story")
    style = data.get("style", "cartoon")

    if not story or not story.get("chapters"):
        return json_response(False, "故事数据不能为空", status_code=400)

    def sse(event: dict) -> str:
        return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    @stream_with_context
    def generate():
        try:
            # 保存故事
            story_id = story.get("id") or str(uuid.uuid4())
            story["id"] = story_id
            story_path = STORIES_DIR / f"{story_id}.json"
            with open(story_path, "w", encoding="utf-8") as f:
                json.dump(story, f, ensure_ascii=False, indent=2)

            yield sse({"stage": "start", "message": "开始生成绘本"})

            # 逐页生成插画并推送进度
            image_results = []
            for event in iter_generate_book_images(story, style):
                if event["type"] == "progress":
                    chapter = event["chapter"]
                    yield sse({
                        "stage": "image",
                        "current": event["current"],
                        "total": event["total"],
                        "chapter": chapter.get("title", "") if isinstance(chapter, dict) else "",
                    })
                elif event["type"] == "page_done":
                    image_results.append(event["result"])

            # 排版生成绘本
            yield sse({"stage": "layout", "message": "正在排版生成绘本..."})
            book_meta = create_picture_book(story, image_results)
            book_meta["image_results"] = image_results

            yield sse({
                "stage": "done",
                "success": True,
                "book": {
                    "id": book_meta["id"],
                    "title": book_meta["title"],
                    "page_count": book_meta["page_count"],
                },
            })
        except Exception as e:
            yield sse({"stage": "error", "success": False, "message": str(e)})

    return Response(generate(), mimetype="text/event-stream")


@app.route("/api/books/list", methods=["GET"])
def api_list_books():
    """获取绘本列表"""
    books = []
    try:
        for meta_file in sorted(BOOKS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            with open(meta_file, "r", encoding="utf-8") as f:
                meta = json.load(f)
                books.append({
                    "id": meta.get("id"),
                    "title": meta.get("title"),
                    "author": meta.get("author"),
                    "created_at": meta.get("created_at"),
                    "page_count": meta.get("page_count"),
                    "cover": meta["pages"][0]["image"] if meta.get("pages") else None,
                    "cover_url": asset_url(meta["pages"][0]["image"]) if meta.get("pages") else None
                })
    except Exception as e:
        return json_response(False, f"获取绘本列表失败: {str(e)}", status_code=500)
    
    return json_response(True, "获取成功", data={"books": books})


@app.route("/api/books/<book_id>", methods=["GET"])
def api_get_book(book_id):
    """获取绘本详情"""
    meta_path = BOOKS_DIR / f"{book_id}.json"
    
    if not meta_path.exists():
        return json_response(False, "绘本不存在", status_code=404)
    
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        return json_response(True, "获取成功", data=enrich_book_assets(meta))
    except Exception as e:
        return json_response(False, f"读取绘本失败: {str(e)}", status_code=500)


@app.route("/api/books/<book_id>/read", methods=["GET"])
def api_read_book(book_id):
    """计划兼容入口 - 在线阅读绘本"""
    return reader(book_id)


@app.route("/api/books/<book_id>/download", methods=["GET"])
def api_download_book(book_id):
    """下载绘本 PDF"""
    pdf_path = BOOKS_DIR / f"{book_id}.pdf"
    
    if not pdf_path.exists():
        return json_response(False, "PDF 文件不存在", status_code=404)
    
    try:
        return send_file(
            pdf_path,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"{book_id}.pdf"
        )
    except Exception as e:
        return json_response(False, f"下载失败: {str(e)}", status_code=500)


@app.route("/data/<path:filename>", methods=["GET"])
def generated_asset(filename):
    """访问绘本生成的图片资源。

    仅开放排版后的页面图和插画缓存，避免直接暴露故事 JSON 等数据文件。
    """
    path = Path(filename)
    allowed_roots = {"books", "images"}
    allowed_extensions = {".png", ".jpg", ".jpeg", ".webp"}

    if (
        not path.parts
        or path.parts[0] not in allowed_roots
        or path.suffix.lower() not in allowed_extensions
    ):
        abort(404)

    return send_from_directory(DATA_DIR, filename)


@app.route("/api/demo-story", methods=["GET"])
def api_demo_story():
    """获取示例故事"""
    story = create_demo_story()
    return json_response(True, "获取示例故事成功", data=story)


@app.route("/api/styles", methods=["GET"])
def api_styles():
    """获取支持的绘画风格列表"""
    styles = [
        {"id": "cartoon", "name": "卡通风格", "desc": "可爱卡通，色彩明亮"},
        {"id": "watercolor", "name": "水彩风格", "desc": "柔和水彩，温暖手绘"},
        {"id": "crayon", "name": "蜡笔风格", "desc": "童趣蜡笔，手绘质感"},
        {"id": "flat", "name": "扁平风格", "desc": "简洁扁平，色彩鲜艳"}
    ]
    return json_response(True, "获取成功", data={"styles": styles})


@app.errorhandler(404)
def not_found(error):
    return json_response(False, "请求的资源不存在", status_code=404)


@app.errorhandler(500)
def internal_error(error):
    return json_response(False, "服务器内部错误", status_code=500)


if __name__ == "__main__":
    # 确保数据目录存在
    for d in [STORIES_DIR, BOOKS_DIR, IMAGES_DIR]:
        d.mkdir(parents=True, exist_ok=True)
    
    app.run(host="0.0.0.0", port=5000, debug=True)
