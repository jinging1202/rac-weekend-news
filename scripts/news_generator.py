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
MODEL_NAME = "gemini-2.0-flash"

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
        prompt = f"""你是一名严格遵守事实核查与信息溯源规范的国际教育与全球资讯编辑。
现在是 {datetime.date.today().strftime("%Y-%m-%d")}。
生成《RAC 周末闪讯》，严格 6 个板块，每个板块 {ITEMS_PER_SECTION} 条资讯。

板块：{', '.join(SECTIONS)}

JSON 格式示例：
[
  {{
    "id": "global",
    "items": [
      {{
        "title": "",
        "content": "",
        "source": "",
        "date": "",
        "image": "",
        "tags": [],
        "url": "",
        "fullContent": "",
        "analysis": ""
      }}
    ]
  }}
]
"""

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )

        news_data = extract_json_from_text(response.text)
        if news_data and all(len(sec.get("items", [])) == ITEMS_PER_SECTION for sec in news_data):
            break
        print(f"⚠️ 第 {attempt} 次生成未达到要求，重试...")
        time.sleep(5)

    if not news_data:
        raise ValueError("❌ AI 返回数据无法解析为 JSON")

    return news_data

def update_html_file(news_data, week_info):
    if not os.path.exists(HTML_FILE_PATH):
        raise FileNotFoundError(f"{HTML_FILE_PATH} 不存在")

    with open(HTML_FILE_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    # 更新版本号信息
    new_config = f"""const ISSUE_CONFIG = {{
        vol: "{week_info['vol']}",
        week: "{week_info['week']}",
        date: "{week_info['date']}",
        year: "{week_info['year']}"
    }};"""
    content = re.sub(r'const ISSUE_CONFIG = \{[\s\S]*?\};', new_config, content)

    # 更新数据
    js_sections_str = "const SECTIONS = [\n"
    global_id = 1
    for section in SECTIONS:
        sec_data = next((s for s in news_data if s['id'] == section), {"items":[]})
        js_sections_str += f"  {{ id: '{section}', items: [\n"
        for item in sec_data.get("items", []):
            clean = lambda s: str(s).replace('\n',' ').replace('"','\\"')
            js_sections_str += f"    {{ id:{global_id}, title:\"{clean(item.get('title',''))}\", content:\"{clean(item.get('content',''))}\", source:\"{clean(item.get('source',''))}\", date:\"{item.get('date','')}\", image:\"{item.get('image','')}\", tags:{json.dumps(item.get('tags',[]), ensure_ascii=False)}, url:\"{item.get('url','#')}\", fullContent:\"{clean(item.get('fullContent',''))}\", analysis:\"{clean(item.get('analysis',''))}\" }},\n"
            global_id += 1
        js_sections_str += "  ]},\n"
    js_sections_str += "];"
    content = re.sub(r'const SECTIONS = \[[\s\S]*?\];', js_sections_str, content)

    with open(HTML_FILE_PATH, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"✅ 更新完成: {HTML_FILE_PATH} ({week_info['vol']})")

# ================= 主函数 =================
def main():
    try:
        print("开始执行周更任务...")
        week_info = get_current_week_info()
        print(f"目标版本: {week_info['vol']}")
        news_data = generate_news_content()
        update_html_file(news_data, week_info)
        print("所有任务完成")
    except Exception as e:
        print(f"❌ 任务失败: {e}")
        exit(1)

if __name__ == "__main__":
    main()
