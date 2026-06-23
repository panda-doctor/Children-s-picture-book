"""儿童故事绘本应用配置文件"""

import os
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent

# Agnes AI 图像生成配置
AGNES_API_KEY = os.environ.get("AGNES_API_KEY", "").strip()
AGNES_IMAGE_ENDPOINT = "https://apihub.agnes-ai.com/v1/images/generations"
AGNES_IMAGE_MODEL = "agnes-image-2.1-flash"
LOCAL_IMAGE_FALLBACK = os.environ.get("LOCAL_IMAGE_FALLBACK", "true").lower() not in {"0", "false", "no"}

# 数据存储路径
DATA_DIR = BASE_DIR / "data"
STORIES_DIR = DATA_DIR / "stories"
IMAGES_DIR = DATA_DIR / "images"
BOOKS_DIR = DATA_DIR / "books"
FILTERS_DIR = DATA_DIR / "filters"
SAMPLES_DIR = BASE_DIR / "samples"

# 确保目录存在
for d in [DATA_DIR, STORIES_DIR, IMAGES_DIR, BOOKS_DIR, FILTERS_DIR, SAMPLES_DIR]:
    d.mkdir(parents=True, exist_ok=True)

IMAGE_SIZE = os.environ.get("IMAGE_SIZE", "1024x768")
IMAGE_TIMEOUT = int(os.environ.get("IMAGE_TIMEOUT", "30"))

# 应用配置
class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "children-storybook-secret-key-2026")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 最大上传 16MB
    UPLOAD_EXTENSIONS = [".txt", ".json"]
    
    # 儿童友好配置
    CHILD_AGE_MIN = 3
    CHILD_AGE_MAX = 8
    
    # 图像生成配置
    IMAGE_SIZE = IMAGE_SIZE
    IMAGE_TIMEOUT = IMAGE_TIMEOUT  # 单次生成超时时间（秒）
    MAX_IMAGE_PROMPT_LENGTH = 800
    
    # 插画风格预设
    IMAGE_STYLES = {
        "cartoon": "cartoon style, cute and friendly characters, bright colors, children's book illustration",
        "watercolor": "watercolor painting style, soft colors, gentle brush strokes, warm children's illustration",
        "crayon": "crayon drawing style, colorful hand-drawn, childlike illustration",
        "flat": "flat vector illustration, minimalist, cute characters, vibrant colors"
    }
    
    # 安全防护配置
    CONTENT_SAFETY_LEVEL = "strict"  # strict, normal, relaxed
    MAX_STORY_LENGTH = 10000  # 最大故事字数
    MAX_CHAPTERS = 10  # 最大章节数
