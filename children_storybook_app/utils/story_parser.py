"""故事解析模块

支持 TXT 和 JSON 格式故事的解析、章节分割与格式标准化。
"""

import json
import re
import uuid
from datetime import datetime
from typing import Dict, List, Optional


class StoryParser:
    """故事解析器"""
    
    # 章节分隔标记
    CHAPTER_MARKERS = ["第\u4e00章", "第\u4e8c章", "第\u4e09章", "第\u56db章", "第\u4e94章",
                      "第\u516d章", "第\u4e03章", "第\u516b章", "第\u4e5d章", "第\u5341章"]
    
    @classmethod
    def parse_text(cls, text: str, title: str = "未命名故事", author: str = "", 
                   split_by_paragraph: bool = True) -> Dict:
        """解析纯文本故事
        
        Args:
            text: 故事正文
            title: 故事标题
            author: 作者
            split_by_paragraph: 是否按段落自动分章节
            
        Returns:
            标准化故事结构
        """
        # 清理文本
        text = cls._clean_text(text)
        
        # 尝试检测章节标记
        chapters = cls._split_by_markers(text)
        
        # 若无章节标记且按段落分，则按段落分章
        if not chapters and split_by_paragraph:
            chapters = cls._split_by_paragraphs(text)
        
        # 若仍无章节，则作为单章
        if not chapters:
            chapters = [{"title": "", "content": text}]
        
        # 生成章节标题
        for i, chapter in enumerate(chapters, 1):
            if not chapter["title"]:
                chapter["title"] = f"第{i}页"
        
        # 限制最大章节数
        if len(chapters) > 10:
            # 合并多余章节到最后章
            remaining = "\n\n".join([c["content"] for c in chapters[9:]])
            chapters = chapters[:9]
            chapters.append({"title": "第10页", "content": remaining})
        
        story = {
            "id": str(uuid.uuid4()),
            "title": title.strip() or "未命名故事",
            "author": author.strip() or "佚名",
            "created_at": datetime.now().isoformat(),
            "chapters": chapters,
            "chapter_count": len(chapters),
            "word_count": len(text)
        }
        
        return story
    
    @classmethod
    def parse_json(cls, json_data: str) -> Dict:
        """解析 JSON 格式故事
        
        Args:
            json_data: JSON 字符串或字典
            
        Returns:
            标准化故事结构
        """
        if isinstance(json_data, str):
            data = json.loads(json_data)
        else:
            data = json_data
        
        # 标准化字段
        title = data.get("title", "未命名故事")
        author = data.get("author", "佚名")
        content = data.get("content", "")
        chapters = data.get("chapters", [])
        
        if chapters:
            # 规范化章节字段
            normalized_chapters = []
            for i, chapter in enumerate(chapters, 1):
                if isinstance(chapter, str):
                    chapter = {"title": f"第{i}页", "content": chapter}
                else:
                    chapter = {
                        "title": chapter.get("title", f"第{i}页"),
                        "content": cls._clean_text(chapter.get("content", ""))
                    }
                if chapter["content"]:
                    normalized_chapters.append(chapter)
            chapters = normalized_chapters
        elif content:
            # 没有 chapters 字段但有 content
            return cls.parse_text(content, title, author)
        
        if not chapters:
            raise ValueError("JSON 数据中未找到故事内容")
        
        # 合并内容计算字数
        all_content = "\n".join([c["content"] for c in chapters])
        
        story = {
            "id": data.get("id") or str(uuid.uuid4()),
            "title": title.strip() or "未命名故事",
            "author": author.strip() or "佚名",
            "created_at": data.get("created_at") or datetime.now().isoformat(),
            "chapters": chapters,
            "chapter_count": len(chapters),
            "word_count": len(all_content)
        }
        
        return story
    
    @classmethod
    def parse_file(cls, file_content: bytes, filename: str) -> Dict:
        """根据文件类型解析故事
        
        Args:
            file_content: 文件二进制内容
            filename: 文件名
            
        Returns:
            标准化故事结构
        """
        ext = filename.lower().split(".")[-1] if "." in filename else ""
        
        if ext == "txt":
            text = file_content.decode("utf-8")
            return cls.parse_text(text, title=filename.rsplit(".", 1)[0])
        elif ext == "json":
            return cls.parse_json(file_content.decode("utf-8"))
        else:
            raise ValueError(f"不支持的文件格式: {ext}")
    
    @classmethod
    def _clean_text(cls, text: str) -> str:
        """清理文本格式"""
        # 统一换行符
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        # 去除多余空行
        text = re.sub(r"\n{3,}", "\n\n", text)
        # 去除行首行尾空白
        text = text.strip()
        return text
    
    @classmethod
    def _split_by_markers(cls, text: str) -> List[Dict]:
        """按章节标记分割"""
        # 匹配 "第X章"、"第X节"、"Chapter X" 等模式
        pattern = r"(?:^|\n\n)(?:第[一二三四五六七八九十百千万\d]+[章节篇回]|Chapter\s+\d+)\s*[：:]?\s*"
        matches = list(re.finditer(pattern, text))
        
        if len(matches) <= 1:
            return []
        
        chapters = []
        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            segment = text[start:end].strip()
            
            # 提取标题和正文
            lines = segment.split("\n", 1)
            title = cls._clean_text(lines[0])
            if title.startswith(("第", "C")):
                # 只保留章节名，去除后续正文
                title_parts = re.split(r"[：:\n]", title, 1)
                title = title_parts[0].strip()
                content = lines[1].strip() if len(lines) > 1 else ""
            else:
                content = segment
            
            if content:
                chapters.append({"title": title, "content": content})
        
        return chapters
    
    @classmethod
    def _split_by_paragraphs(cls, text: str, max_paragraphs_per_chapter: int = 2) -> List[Dict]:
        """按段落自动分章节"""
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        
        if len(paragraphs) <= 1:
            return [{"title": "第1页", "content": text}]
        
        chapters = []
        i = 0
        chapter_num = 1
        while i < len(paragraphs):
            # 每 1-2 个段落作为一页
            chunk_size = min(max_paragraphs_per_chapter, max(1, len(paragraphs) // 3))
            chunk = paragraphs[i:i + chunk_size]
            content = "\n\n".join(chunk)
            chapters.append({
                "title": f"第{chapter_num}页",
                "content": content
            })
            i += chunk_size
            chapter_num += 1
            
            # 若已接近最大章节数，后续合并
            if chapter_num >= 10:
                remaining = "\n\n".join(paragraphs[i:])
                if remaining:
                    chapters.append({"title": f"第{chapter_num}页", "content": remaining})
                break
        
        return chapters


def create_demo_story() -> Dict:
    """创建示例故事"""
    return {
        "id": str(uuid.uuid4()),
        "title": "小兔子找彩虹",
        "author": "故事绘本应用",
        "chapters": [
            {
                "title": "第1页",
                "content": "清晨，小兔子跳跳从温暖的窝里醒来。她揉揉眼睛，透过窗户看见天空中出现了一道美丽的彩虹。跳跳兴奋地想：'我要找到彩虹的尽头，看看那里有什么宝贝！'"
            },
            {
                "title": "第2页",
                "content": "跳跳背上小背包，里面装满了胡萝卜和一朵小野花。她蹦蹦跳跳地穿过绿色的草地，一路上遇到了歌唱的小鸟和忙碌的蜜蜂。"
            },
            {
                "title": "第3页",
                "content": "走呀走，跳跳来到了一条清澈的小河边。她看见水里有一群小鱼在欢快地游来游去。小鱼们告诉她：'彩虹的尽头有很多彩色的石头，但是最重要的宝藏就在你身边。'"
            },
            {
                "title": "第4页",
                "content": "跳跳继续往前走，太阳慢慢地落山了，彩虹也渐渐消失了。她有点难过，但当她回头一看，发现朋友们都跟在她身后。"
            },
            {
                "title": "第5页",
                "content": "原来，朋友们就是跳跳找到的最大宝藏。大家围坐在一起，分享胡萝卜，看着满天的星星。跳跳明白了：友谊是最珍贵的东西。"
            }
        ],
        "chapter_count": 5,
        "word_count": 300
    }


# 向后兼容
parse_story = StoryParser.parse_text
