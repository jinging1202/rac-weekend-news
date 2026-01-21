import os
import re
import json
import time
import datetime
from google import genai
from google.genai import types

# ================= 配置区 =================
API_KEY = os.environ.get("GEMINI_API_KEY")
HTML_FILE_PATH = "index.html"
MODEL_NAME = "gemini-3.0-flash"

SECTIONS = ["global", "education", "university", "design", "summer", "competitions"]
ITEMS_PER_SECTION = 5  # 每板块条数

# ================= 工具函数 =================
def get_current_week_info():
    today = datetime.date.today()
    year, week_num, _ = today.isocalendar()
    return {
        "vol": f"VOL.{week_num:02d}",
        "week": f"Week {week_num:02d}",
        "date": today.strftime("%Y.%m.%d"),
        "year": str(year)
    }

def extract_json_from_text(text):
    """尝试从 AI 返回的文本中提取 JSON"""
    try:
        return json.loads(text)
    except Exception:
        pass
    try:
        match = re.search(r'```json\s*(\[[\s\S]*?\])\s*```', text)
        if match: return json.loads(match.group(1))
        start = text.find('[')
        end = text.rfind(']')
        if start != -1 and end != -1: return json.loads(text[start:end+1])
    except Exception:
        pass
    return None

# ================= 核心逻辑 =================
def generate_news_content():
    if not API_KEY:
        raise ValueError("❌ GEMINI_API_KEY 未配置")

    client = genai.Client(api_key=API_KEY)
    news_data = []

    # 循环直到生成30条有效内容
    max_attempts = 5
    attempt = 0

    while attempt < max_attempts:
        attempt += 1
        prompt = f"""
        你是一名严格遵守事实核查与信息溯源规范的
