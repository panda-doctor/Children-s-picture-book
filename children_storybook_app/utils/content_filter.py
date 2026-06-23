"""内容安全审核模块

提供儿童故事内容的安全检查，包含敏感词过滤、暴力恐怖内容检测、
成人内容防护等功能。适配 3-8 岁儿童内容安全标准。
"""

import re
from pathlib import Path
from typing import Dict, List, Tuple

from config import FILTERS_DIR


class ContentFilter:
    """内容过滤器"""
    
    # 默认中文敏感词（基础词库）
    DEFAULT_CHINESE_WORDS = [
        "暴力", "血腥", "恐怖", "鬼", "杀人", "死亡", "尸体", "色情",
        "暴力", "虐待", "自残", "自杀", "毒品", "赌博", "烟酒", "喝酒",
        "抽烟", "吸毒", "性", "裸体", "裸体", "枪支", "枪械", "炸弹",
        "爆炸", "战争", "屠杀", "恶魔", "妖怪", "僵尸", "骷髅", "鬼魂",
        "阴间", "地狱", "诅咒", "血腥", "残害", "凶杀", "变态", "猥亵",
        "粗俗", "脏话", "骂人", "欺凌", "霸凌", "歧视", "仇恨"
    ]
    
    # 默认英文敏感词
    DEFAULT_ENGLISH_WORDS = [
        "violence", "blood", "horror", "ghost", "kill", "death", "corpse",
        "porn", "sex", "naked", "gun", "bomb", "explosion", "war", "devil",
        "demon", "zombie", "skull", "curse", "abuse", "drug", "smoke",
        "alcohol", "gamble", "bully", "hate", "discrimination", "suicide",
        "torture", "murder", "terror", "monster"
    ]
    
    def __init__(self, chinese_words_path: str = None, english_words_path: str = None):
        """初始化过滤器
        
        Args:
            chinese_words_path: 中文敏感词文件路径
            english_words_path: 英文敏感词文件路径
        """
        self.chinese_words = self._load_words(
            chinese_words_path, FILTERS_DIR / "chinese_words.txt", self.DEFAULT_CHINESE_WORDS
        )
        self.english_words = self._load_words(
            english_words_path, FILTERS_DIR / "english_words.txt", self.DEFAULT_ENGLISH_WORDS
        )
        
        # 编译中文敏感词匹配正则（忽略大小写）
        self.chinese_pattern = self._compile_patterns(self.chinese_words)
        self.english_pattern = self._compile_patterns(self.english_words)
    
    def _load_words(self, custom_path: str, default_path: Path, default_words: List[str]) -> List[str]:
        """加载敏感词列表
        
        优先从自定义文件加载，若不存在则创建默认词库文件并加载。
        """
        path = Path(custom_path) if custom_path else default_path
        
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                words = [line.strip() for line in f if line.strip() and not line.startswith("#")]
            return words
        
        # 创建默认词库文件
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write("# 儿童内容安全敏感词库\n")
            f.write("# 每行一个词\n\n")
            for word in default_words:
                f.write(word + "\n")
        
        return default_words
    
    def _compile_patterns(self, words: List[str]) -> re.Pattern:
        """编译敏感词正则表达式"""
        if not words:
            return re.compile(r"a^")  # 永不匹配的模式
        
        # 转义特殊字符，按词长度降序排序避免短词覆盖长词
        escaped = [re.escape(word) for word in sorted(words, key=len, reverse=True)]
        pattern = "|".join(escaped)
        return re.compile(pattern, flags=re.IGNORECASE | re.UNICODE)
    
    def detect(self, text: str) -> Dict:
        """检测文本中的敏感内容
        
        Args:
            text: 待检测文本
            
        Returns:
            检测结果字典，包含：
            - safe: 是否通过检测
            - risk_level: 风险等级 (low/medium/high)
            - matched_words: 命中的敏感词列表
            - score: 风险评分 (0-100)
        """
        if not text or not isinstance(text, str):
            return {"safe": True, "risk_level": "low", "matched_words": [], "score": 0}
        
        chinese_matches = self.chinese_pattern.findall(text)
        english_matches = self.english_pattern.findall(text)
        matched_words = list(set(chinese_matches + english_matches))
        
        # 计算风险评分：命中次数越多、词越长风险越高
        score = min(len(matched_words) * 20, 100)
        
        # 判断风险等级
        if len(matched_words) >= 3 or score >= 60:
            risk_level = "high"
            safe = False
        elif len(matched_words) >= 1:
            risk_level = "medium"
            # 中等风险时仍允许，但需提示
            safe = True
        else:
            risk_level = "low"
            safe = True
        
        return {
            "safe": safe,
            "risk_level": risk_level,
            "matched_words": matched_words,
            "score": score
        }
    
    def check_story(self, title: str, content: str, author: str = "") -> Dict:
        """对儿童故事进行综合安全检测
        
        Args:
            title: 故事标题
            content: 故事正文
            author: 作者名
            
        Returns:
            检测结果
        """
        combined_text = f"{title} {author} {content}"
        result = self.detect(combined_text)
        
        # 补充内容长度检查
        content_length = len(content)
        if content_length > 10000:
            result["warnings"] = ["故事内容较长，建议适当精简以提升儿童阅读体验"]
        else:
            result["warnings"] = []
        
        return result


# 全局过滤器实例
content_filter = ContentFilter()


def validate_story(title: str, content: str, author: str = "") -> Dict:
    """对外暴露的故事安全校验接口"""
    return content_filter.check_story(title, content, author)
