"""插画生成模块

封装 Agnes Image 2.1 Flash API 调用，基于章节内容自动生成英文 Prompt，
下载并缓存插画图片。
"""

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Dict, List, Optional

import requests
from PIL import Image, ImageDraw, ImageFont

from config import (
    AGNES_API_KEY, AGNES_IMAGE_ENDPOINT, AGNES_IMAGE_MODEL,
    IMAGES_DIR, IMAGE_SIZE, IMAGE_TIMEOUT, LOCAL_IMAGE_FALLBACK
)


class ImageGenerator:
    """插画生成器"""
    
    def __init__(self, api_key: str = None):
        """初始化插画生成器
        
        Args:
            api_key: Agnes AI API Key，默认从配置文件读取
        """
        self.api_key = api_key or AGNES_API_KEY
        self.endpoint = AGNES_IMAGE_ENDPOINT
        self.model = AGNES_IMAGE_MODEL
        self.image_size = IMAGE_SIZE
        self.timeout = IMAGE_TIMEOUT
        self.local_fallback = LOCAL_IMAGE_FALLBACK
        self.images_dir = Path(IMAGES_DIR)
        self.images_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_prompt(self, chapter_content: str, story_title: str = "",
                       style: str = "cartoon", character_description: str = "") -> str:
        """根据章节内容生成适合图像生成的英文 Prompt
        
        Args:
            chapter_content: 章节中文内容
            story_title: 故事标题
            style: 绘画风格 (cartoon/watercolor/crayon/flat)
            character_description: 角色一致性描述
            
        Returns:
            英文提示词
        """
        # 提取关键场景描述（简化版本：截断并翻译关键词）
        # 实际生产环境可接入翻译 API，这里使用模板化英文描述
        
        style_presets = {
            "cartoon": "cute cartoon style, children's book illustration, bright colors, friendly characters",
            "watercolor": "warm watercolor painting, soft colors, gentle brush strokes, children's storybook",
            "crayon": "colorful crayon drawing, hand-drawn style, childlike illustration",
            "flat": "flat vector illustration, cute minimalist design, vibrant colors"
        }
        
        style_text = style_presets.get(style, style_presets["cartoon"])
        
        # 提取章节内容核心场景（取前 80 个字符）
        scene_chinese = chapter_content[:120].strip()
        
        # 构建 Prompt（针对儿童绘本，强调安全正向内容）
        prompt = (
            f"Children's picture book illustration, {style_text}, "
            f"peaceful and joyful scene from a story titled '{story_title}', "
            f"scene: {scene_chinese}, "
            f"no text, no words, no scary elements, safe for 3-8 year old children, "
            f"high quality, detailed, warm lighting"
        )
        
        if character_description:
            prompt += f", consistent characters: {character_description}"
        
        return prompt[:800]  # 限制长度
    
    def generate_image(self, prompt: str, size: str = None, output_path: str = None) -> Dict:
        """调用 Agnes Image API 生成单张图片
        
        Args:
            prompt: 英文提示词
            size: 图片尺寸，默认使用配置
            output_path: 输出文件路径，默认自动保存到 images 目录
            
        Returns:
            包含 image_url 和 local_path 的字典
        """
        size = size or self.image_size
        local_path = output_path or self._generate_local_path(prompt)

        if not self.api_key:
            return self._generate_local_image(prompt, size, local_path, "missing_api_key")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "size": size
        }
        
        try:
            response = requests.post(
                self.endpoint,
                headers=headers,
                json=payload,
                timeout=self.timeout
            )
            result = response.json()
            
            if "data" in result and len(result["data"]) > 0:
                image_url = result["data"][0].get("url", "")
                
                # 下载图片保存到本地
                if image_url:
                    local_path = self.download_image(image_url, local_path)
                    return {
                        "success": True,
                        "image_url": image_url,
                        "local_path": str(local_path),
                        "prompt": prompt,
                        "size": size
                    }
            
            if self.local_fallback:
                return self._generate_local_image(prompt, size, local_path, "api_empty_response")

            return {
                "success": False,
                "error": result,
                "prompt": prompt,
                "size": size
            }
            
        except requests.exceptions.Timeout:
            if self.local_fallback:
                return self._generate_local_image(prompt, size, local_path, "api_timeout")
            return {"success": False, "error": "生成图片超时，请稍后重试", "prompt": prompt}
        except requests.exceptions.RequestException as e:
            if self.local_fallback:
                return self._generate_local_image(prompt, size, local_path, f"api_request_error: {str(e)}")
            return {"success": False, "error": str(e), "prompt": prompt}
        except Exception as e:
            if self.local_fallback:
                return self._generate_local_image(prompt, size, local_path, f"unknown_error: {str(e)}")
            return {"success": False, "error": f"未知错误: {str(e)}", "prompt": prompt}
    
    def generate_for_story(self, story: Dict, style: str = "cartoon",
                          progress_callback=None) -> List[Dict]:
        """为整个故事的每个章节生成插画

        Args:
            story: 故事结构化数据
            style: 绘画风格
            progress_callback: 进度回调函数，接收 (current, total, chapter) 参数

        Returns:
            各章节图片生成结果列表
        """
        chapters = story.get("chapters", [])
        title = story.get("title", "")
        results = []
        total = len(chapters)

        # 提取角色一致性描述（从第一个章节和标题中推断）
        character_description = self._extract_characters(story)

        for i, chapter in enumerate(chapters, 1):
            progress_callback(i, total, chapter) if progress_callback else None

            prompt = self.generate_prompt(
                chapter["content"],
                title,
                style,
                character_description
            )

            # 根据章节序号命名输出文件
            story_id = story.get("id", "unknown")
            safe_title = self._safe_filename(title)[:30]
            output_filename = f"{safe_title}_{story_id[:8]}_page{i}.png"
            output_path = self.images_dir / output_filename

            # 若有缓存则直接返回
            if output_path.exists():
                results.append({
                    "success": True,
                    "chapter": chapter["title"],
                    "local_path": str(output_path),
                    "image_url": None,
                    "prompt": prompt,
                    "cached": True
                })
                continue

            result = self.generate_image(prompt, output_path=str(output_path))
            result["chapter"] = chapter["title"]
            results.append(result)

            # 简单限流，避免调用过快
            time.sleep(0.5)

        return results
    
    def download_image(self, image_url: str, output_path: str) -> Path:
        """下载图片到本地
        
        Args:
            image_url: 图片 URL
            output_path: 本地保存路径
            
        Returns:
            保存后的本地路径
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        response = requests.get(image_url, timeout=60)
        response.raise_for_status()
        
        with open(output_path, "wb") as f:
            f.write(response.content)
        
        return output_path
    
    def _generate_local_path(self, prompt: str) -> Path:
        """根据 Prompt 生成本地文件路径（基于哈希避免重名）"""
        prompt_hash = hashlib.md5(prompt.encode("utf-8")).hexdigest()[:8]
        timestamp = int(time.time())
        filename = f"generated_{timestamp}_{prompt_hash}.png"
        return self.images_dir / filename

    def _generate_local_image(self, prompt: str, size: str, output_path: str, reason: str) -> Dict:
        """生成本地开发预览插画，保证无外部 API 时流程仍可执行。"""
        width, height = self._parse_size(size)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        seed = int(hashlib.md5(prompt.encode("utf-8")).hexdigest()[:8], 16)
        palette = self._local_palette(prompt)

        img = Image.new("RGB", (width, height), palette["sky"])
        draw = ImageDraw.Draw(img)

        horizon = int(height * 0.68)
        draw.rectangle([0, horizon, width, height], fill=palette["ground"])
        draw.ellipse(
            [int(width * 0.07), int(height * 0.08), int(width * 0.23), int(height * 0.29)],
            fill=palette["sun"],
        )

        for i in range(4):
            x = int(width * (0.18 + i * 0.22)) + ((seed >> (i * 3)) % 35) - 18
            y = int(height * (0.16 + (i % 2) * 0.08))
            self._draw_cloud(draw, x, y, int(width * 0.055), palette["cloud"])

        rainbow_box = [
            int(width * 0.33),
            int(height * 0.18),
            int(width * 0.95),
            int(height * 0.88),
        ]
        rainbow_colors = [(255, 118, 117), (255, 195, 18), (29, 209, 161), (84, 160, 255), (162, 155, 254)]
        for idx, color in enumerate(rainbow_colors):
            inset = idx * max(8, width // 90)
            draw.arc(
                [rainbow_box[0] + inset, rainbow_box[1] + inset, rainbow_box[2] - inset, rainbow_box[3] - inset],
                start=195,
                end=345,
                fill=color,
                width=max(8, width // 85),
            )

        for i in range(6):
            x = int(width * (0.08 + i * 0.15))
            y = horizon - int(height * (0.03 + ((seed >> i) % 5) * 0.012))
            self._draw_flower(draw, x, y, max(10, width // 80), palette["accent"])

        label = "Local Preview"
        font = self._load_local_font(max(20, width // 35))
        bbox = draw.textbbox((0, 0), label, font=font)
        label_w = bbox[2] - bbox[0]
        label_h = bbox[3] - bbox[1]
        pad = max(12, width // 80)
        x = width - label_w - pad * 2
        y = height - label_h - pad * 2
        draw.rounded_rectangle([x - pad, y - pad, width - pad, height - pad], radius=16, fill=(255, 255, 255), outline=palette["accent"], width=3)
        draw.text((x, y), label, fill=(78, 70, 60), font=font)

        img.save(output_path, "PNG")

        return {
            "success": True,
            "image_url": None,
            "local_path": str(output_path),
            "prompt": prompt,
            "size": size,
            "local_fallback": True,
            "fallback_reason": reason,
        }

    def _parse_size(self, size: str) -> tuple:
        try:
            width, height = [int(part) for part in size.lower().split("x", 1)]
            return width, height
        except Exception:
            return 1024, 768

    def _local_palette(self, prompt: str) -> Dict:
        if "watercolor" in prompt:
            return {"sky": (226, 244, 250), "ground": (211, 232, 201), "sun": (255, 225, 168), "cloud": (255, 255, 250), "accent": (255, 168, 138)}
        if "crayon" in prompt:
            return {"sky": (196, 231, 255), "ground": (163, 222, 142), "sun": (255, 210, 79), "cloud": (255, 252, 234), "accent": (255, 116, 150)}
        if "flat vector" in prompt:
            return {"sky": (205, 237, 255), "ground": (139, 213, 176), "sun": (255, 190, 90), "cloud": (250, 250, 250), "accent": (90, 144, 255)}
        return {"sky": (209, 235, 255), "ground": (169, 225, 154), "sun": (255, 213, 102), "cloud": (255, 255, 255), "accent": (255, 154, 91)}

    def _load_local_font(self, size: int):
        for path in ["C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf", "C:/Windows/Fonts/arial.ttf"]:
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, size)
                except Exception:
                    pass
        return ImageFont.load_default()

    def _draw_cloud(self, draw: ImageDraw.ImageDraw, x: int, y: int, radius: int, color: tuple):
        draw.ellipse([x - radius, y, x + radius, y + radius], fill=color)
        draw.ellipse([x, y - radius // 2, x + radius * 2, y + radius], fill=color)
        draw.ellipse([x + radius, y, x + radius * 3, y + radius], fill=color)

    def _draw_flower(self, draw: ImageDraw.ImageDraw, x: int, y: int, size: int, color: tuple):
        stem = (70, 150, 95)
        draw.line([x, y, x, y + size * 4], fill=stem, width=max(2, size // 5))
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            draw.ellipse(
                [x + dx * size - size // 2, y + dy * size - size // 2, x + dx * size + size // 2, y + dy * size + size // 2],
                fill=color,
            )
        draw.ellipse([x - size // 2, y - size // 2, x + size // 2, y + size // 2], fill=(255, 225, 95))
    
    def _safe_filename(self, text: str) -> str:
        """将文本转为安全文件名"""
        import re
        return re.sub(r'[\\/:*?"<>|]', "_", text).strip() or "story"
    
    def _extract_characters(self, story: Dict) -> str:
        """从故事中尝试提取主要角色描述"""
        # 简单规则：从标题中提取常见动物/角色名
        title = story.get("title", "")
        characters = []
        
        # 常见儿童故事角色词
        role_keywords = ["小兔子", "小猫", "小狗", "小熊", "小鸟", "小鱼", "小青蛙",
                        "小老鼠", "小狐狸", "小狮子", "小象", "小熊猫", "小朋友",
                        "小男孩", "小女孩", "小精灵", "小公主", "小王子"]
        
        for keyword in role_keywords:
            if keyword in title:
                characters.append(f"a cute {keyword.replace('小', '')}")
        
        return ", ".join(characters[:3])


# 全局实例
image_generator = ImageGenerator()


def generate_book_images(story: Dict, style: str = "cartoon",
                        progress_callback=None) -> List[Dict]:
    """对外暴露的绘本图片生成接口"""
    return image_generator.generate_for_story(story, style, progress_callback)
