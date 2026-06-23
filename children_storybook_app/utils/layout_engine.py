"""绘本排版引擎

使用 Pillow 将故事文本和 generated 插画排版成绘本页面，并导出 PDF。
"""

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

from PIL import Image, ImageDraw, ImageFont, ImageOps

from config import BOOKS_DIR


class LayoutEngine:
    """绘本排版引擎"""
    
    # 页面尺寸 (横版 1024x768，与图片尺寸一致)
    PAGE_WIDTH = 1024
    PAGE_HEIGHT = 768
    
    # 儿童友好配色
    COLORS = {
        "white": (255, 255, 255),
        "cream": (255, 250, 240),
        "soft_yellow": (255, 245, 200),
        "light_blue": (200, 230, 255),
        "orange": (255, 180, 100),
        "green": (150, 220, 150),
        "pink": (255, 200, 210),
        "purple": (220, 200, 255),
        "text_dark": (60, 50, 45),
        "text_light": (120, 110, 100)
    }
    
    def __init__(self):
        self.books_dir = Path(BOOKS_DIR)
        self.books_dir.mkdir(parents=True, exist_ok=True)
        # 使用 Pillow 默认字体
        self.title_font = self._load_font(48, bold=True)
        self.text_font = self._load_font(28)
        self.small_font = self._load_font(20)
    
    def _load_font(self, size: int, bold: bool = False):
        """加载字体"""
        # 尝试加载系统中文字体
        font_paths = [
            "C:/Windows/Fonts/simhei.ttf",
            "C:/Windows/Fonts/simsun.ttc",
            "C:/Windows/Fonts/msyh.ttc",
            "C:/Windows/Fonts/msyhbd.ttc"
        ]
        
        for path in font_paths:
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, size)
                except Exception:
                    pass
        
        return ImageFont.load_default()
    
    def create_book(self, story: Dict, image_results: List[Dict]) -> Dict:
        """根据故事和图片生成完整绘本
        
        Args:
            story: 故事数据结构
            image_results: 图片生成结果列表
            
        Returns:
            绘本生成结果，包含 PDF 路径、页面列表等
        """
        story_id = story.get("id", str(uuid.uuid4()))
        title = story.get("title", "未命名绘本")
        author = story.get("author", "佚名")
        chapters = story.get("chapters", [])
        
        pages = []
        
        # 封面页
        cover_path = self._create_cover(title, author, image_results)
        pages.append({
            "type": "cover",
            "title": title,
            "author": author,
            "image": str(cover_path)
        })
        
        # 章节页面
        for i, chapter in enumerate(chapters):
            image_path = self._get_chapter_image(image_results, i)
            page_path = self._create_page(chapter, i + 1, image_path)
            pages.append({
                "type": "content",
                "chapter": chapter.get("title", f"第{i + 1}页"),
                "content": chapter.get("content", ""),
                "image": str(page_path)
            })
        
        # 封底页
        back_path = self._create_back_cover(title, author)
        pages.append({
            "type": "back",
            "title": title,
            "image": str(back_path)
        })
        
        # 生成 PDF
        pdf_path = self._create_pdf(pages, story_id)
        
        # 保存绘本元数据
        book_meta = {
            "id": story_id,
            "title": title,
            "author": author,
            "created_at": datetime.now().isoformat(),
            "page_count": len(pages),
            "pages": pages,
            "pdf_path": str(pdf_path)
        }
        
        meta_path = self.books_dir / f"{story_id}.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(book_meta, f, ensure_ascii=False, indent=2)
        
        return book_meta
    
    def _create_cover(self, title: str, author: str, image_results: List[Dict]) -> Path:
        """创建封面页"""
        width, height = self.PAGE_WIDTH, self.PAGE_HEIGHT
        img = Image.new("RGB", (width, height), self.COLORS["soft_yellow"])
        draw = ImageDraw.Draw(img)
        
        # 装饰圆角矩形边框
        draw.rounded_rectangle(
            [30, 30, width - 30, height - 30],
            radius=30,
            outline=self.COLORS["orange"],
            width=8
        )
        
        # 标题
        title_text = title[:20]
        bbox = draw.textbbox((0, 0), title_text, font=self.title_font)
        text_width = bbox[2] - bbox[0]
        draw.text(
            ((width - text_width) // 2, 150),
            title_text,
            fill=self.COLORS["text_dark"],
            font=self.title_font
        )
        
        # 副标题
        subtitle = "儿童故事绘本"
        bbox = draw.textbbox((0, 0), subtitle, font=self.text_font)
        text_width = bbox[2] - bbox[0]
        draw.text(
            ((width - text_width) // 2, 240),
            subtitle,
            fill=self.COLORS["orange"],
            font=self.text_font
        )
        
        # 作者
        author_text = f"作者：{author}"
        bbox = draw.textbbox((0, 0), author_text, font=self.small_font)
        text_width = bbox[2] - bbox[0]
        draw.text(
            ((width - text_width) // 2, height - 120),
            author_text,
            fill=self.COLORS["text_light"],
            font=self.small_font
        )
        
        # 装饰图案：彩色小星星
        self._draw_stars(draw, [
            (150, 350), (width - 150, 380), (200, 550), (width - 200, 520)
        ])
        
        output_path = self.books_dir / f"cover_{uuid.uuid4().hex[:8]}.png"
        img.save(output_path, "PNG")
        return output_path
    
    def _create_page(self, chapter: Dict, page_num: int, image_path: str = None) -> Path:
        """创建单个绘本内容页
        
        布局：右侧图片，左侧文字，大字体圆角设计
        """
        width, height = self.PAGE_WIDTH, self.PAGE_HEIGHT
        img = Image.new("RGB", (width, height), self.COLORS["cream"])
        draw = ImageDraw.Draw(img)
        
        # 外边框
        draw.rounded_rectangle(
            [20, 20, width - 20, height - 20],
            radius=25,
            outline=self.COLORS["light_blue"],
            width=6
        )
        
        # 内部分割：左侧 45% 文字，右侧 55% 图片
        left_margin = 50
        text_area_width = 420
        text_start_y = 80
        
        # 章节标题
        chapter_title = chapter.get("title", f"第{page_num}页")
        draw.text(
            (left_margin, 50),
            chapter_title,
            fill=self.COLORS["orange"],
            font=self.small_font
        )
        
        # 正文内容（自动换行）
        content = chapter.get("content", "")
        lines = self._wrap_text(draw, content, self.text_font, text_area_width - 20)
        y = text_start_y
        for line in lines[:12]:  # 最多显示 12 行
            draw.text((left_margin, y), line, fill=self.COLORS["text_dark"], font=self.text_font)
            y += 42
        
        # 图片区域
        if image_path and os.path.exists(image_path):
            try:
                page_img = Image.open(image_path).convert("RGB")
                # 目标尺寸
                target_width = 480
                target_height = 680
                page_img = self._resize_with_aspect(page_img, target_width, target_height)
                
                # 计算居中位置
                img_x = width - target_width - 40
                img_y = (height - page_img.height) // 2
                
                # 圆角图片
                img = self._paste_rounded_image(img, page_img, (img_x, img_y), 20)
                draw = ImageDraw.Draw(img)
                
            except Exception as e:
                # 图片加载失败，绘制占位图
                draw.rectangle(
                    [width - 520, 60, width - 40, height - 60],
                    fill=self.COLORS["light_blue"],
                    outline=self.COLORS["orange"],
                    width=4
                )
                draw.text(
                    (width - 350, height // 2),
                    "插画加载中",
                    fill=self.COLORS["text_dark"],
                    font=self.text_font
                )
        else:
            # 无图片占位
            draw.rounded_rectangle(
                [width - 520, 60, width - 40, height - 60],
                radius=20,
                fill=self.COLORS["light_blue"],
                outline=self.COLORS["orange"],
                width=4
            )
        
        # 页码
        page_text = f"{page_num}"
        bbox = draw.textbbox((0, 0), page_text, font=self.small_font)
        text_width = bbox[2] - bbox[0]
        draw.text(
            ((width - text_width) // 2, height - 45),
            page_text,
            fill=self.COLORS["text_light"],
            font=self.small_font
        )
        
        output_path = self.books_dir / f"page_{uuid.uuid4().hex[:8]}.png"
        img.save(output_path, "PNG")
        return output_path
    
    def _create_back_cover(self, title: str, author: str) -> Path:
        """创建封底页"""
        width, height = self.PAGE_WIDTH, self.PAGE_HEIGHT
        img = Image.new("RGB", (width, height), self.COLORS["light_blue"])
        draw = ImageDraw.Draw(img)
        
        draw.rounded_rectangle(
            [30, 30, width - 30, height - 30],
            radius=30,
            outline=self.COLORS["white"],
            width=8
        )
        
        # 结束语
        end_text = "~ 完 ~"
        bbox = draw.textbbox((0, 0), end_text, font=self.title_font)
        text_width = bbox[2] - bbox[0]
        draw.text(
            ((width - text_width) // 2, height // 2 - 50),
            end_text,
            fill=self.COLORS["text_dark"],
            font=self.title_font
        )
        
        # 书名
        book_text = f"《{title}》"
        bbox = draw.textbbox((0, 0), book_text, font=self.text_font)
        text_width = bbox[2] - bbox[0]
        draw.text(
            ((width - text_width) // 2, height // 2 + 40),
            book_text,
            fill=self.COLORS["text_light"],
            font=self.text_font
        )
        
        # 装饰
        self._draw_stars(draw, [
            (120, 150), (width - 120, 180), (180, height - 150), (width - 160, height - 180)
        ])
        
        output_path = self.books_dir / f"back_{uuid.uuid4().hex[:8]}.png"
        img.save(output_path, "PNG")
        return output_path
    
    def _create_pdf(self, pages: List[Dict], story_id: str) -> Path:
        """将所有页面合并为 PDF"""
        from PIL import Image
        
        images = []
        for page in pages:
            img_path = page.get("image")
            if img_path and os.path.exists(img_path):
                img = Image.open(img_path).convert("RGB")
                images.append(img)
        
        if not images:
            raise ValueError("没有可生成 PDF 的页面")
        
        output_path = self.books_dir / f"{story_id}.pdf"
        images[0].save(
            output_path,
            save_all=True,
            append_images=images[1:],
            resolution=100.0
        )
        
        return output_path
    
    def _wrap_text(self, draw: ImageDraw.Draw, text: str, font: ImageFont.FreeTypeFont,
                   max_width: int) -> List[str]:
        """文字自动换行"""
        if not text:
            return []
        
        lines = []
        paragraphs = text.split("\n")
        
        for paragraph in paragraphs:
            if not paragraph.strip():
                continue
            
            current_line = ""
            for char in paragraph:
                test_line = current_line + char
                bbox = draw.textbbox((0, 0), test_line, font=font)
                width = bbox[2] - bbox[0]
                
                if width <= max_width:
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = char
            
            if current_line:
                lines.append(current_line)
        
        return lines
    
    def _resize_with_aspect(self, img: Image.Image, max_width: int, max_height: int) -> Image.Image:
        """等比缩放图片"""
        img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        return img
    
    def _paste_rounded_image(self, background: Image.Image, img: Image.Image,
                            position: Tuple[int, int], radius: int) -> Image.Image:
        """将图片以圆角形式粘贴到背景"""
        # 创建圆角蒙版
        mask = Image.new("L", img.size, 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle([0, 0, img.width, img.height], radius=radius, fill=255)
        
        background_copy = background.copy()
        background_copy.paste(img, position, mask)
        return background_copy
    
    def _draw_stars(self, draw: ImageDraw.Draw, positions: List[Tuple[int, int]]):
        """绘制装饰星星"""
        colors = [self.COLORS["orange"], self.COLORS["green"], self.COLORS["pink"], self.COLORS["purple"]]
        for i, pos in enumerate(positions):
            x, y = pos
            size = 20
            color = colors[i % len(colors)]
            # 绘制简单四角星
            draw.polygon([
                (x, y - size), (x + size // 3, y - size // 3),
                (x + size, y), (x + size // 3, y + size // 3),
                (x, y + size), (x - size // 3, y + size // 3),
                (x - size, y), (x - size // 3, y - size // 3)
            ], fill=color)
    
    def _get_chapter_image(self, image_results: List[Dict], index: int) -> str:
        """获取章节对应的图片路径"""
        if index < len(image_results):
            return image_results[index].get("local_path", "")
        return ""


# 全局实例
layout_engine = LayoutEngine()


def create_picture_book(story: Dict, image_results: List[Dict]) -> Dict:
    """对外暴露的绘本生成接口"""
    return layout_engine.create_book(story, image_results)
