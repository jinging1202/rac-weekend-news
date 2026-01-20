import os
import re
import json
import datetime
from google import genai
from google.genai import types

# ================= 配置区 =================
API_KEY = os.environ.get("GEMINI_API_KEY")
HTML_FILE_PATH = "index.html"
MODEL_NAME = "gemini-2.0-flash"

# ================= 时间信息 =================
def get_current_week_info():
    today = datetime.date.today()
    year, week_num, _ = today.isocalendar()
    return {
        "vol": f"VOL.{week_num:02d}",
        "week": f"WEEK {week_num:02d}",
        "date": today.strftime("%Y.%m.%d"),
        "year": str(year)
    }

# ================= JSON 解析 =================
def extract_json(text: str):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r'\[\s*{[\s\S]*}\s*\]', text)
    if match:
        try:
            return json.loads(match.group())
        except Exception:
            pass

    return None

# ================= 内容生成 =================
def generate_news_content():
    if not API_KEY:
        raise RuntimeError("GEMINI_API_KEY 未配置")

    client = genai.Client(api_key=API_KEY)

    prompt = f"""
你是一名严格遵守事实核查与信息溯源规范的国际教育与全球资讯编辑。
现在是 {datetime.date.today().strftime("%Y年%m月%d日")}。

请检索【最近 7 天内首次发布】的信息，生成《RAC 周末闪讯》。

【板块要求】（每个板块 5 条）
1. global
2. education
3. university
4. design
5. summer
6. competitions

【JSON 输出格式】（只输出 JSON，不要解释）
[
  {{
    "id": "global",
    "items": [
      {{
        "title": "标题",
        "content": "两行内关键词概述",
        "source": "来源",
        "date": "MM.DD",
        "image": "https://...",
        "tags": ["TAG1", "TAG2"],
        "url": "https://...",
        "fullContent": "<p>详细内容</p>",
        "analysis": "两句话专家点评"
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

    data = extract_json(response.text)
    if not data:
        raise RuntimeError("无法解析 Gemini 返回的 JSON")

    return data

# ================= HTML 注入 =================
def update_html(news_data, week_info):
    with open(HTML_FILE_PATH, "r", encoding="utf-8") as f:
        html = f.read()

    issue_config = f"""const ISSUE_CONFIG = {{
            vol: "{week_info['vol']}",
            week: "{week_info['week']}",
            date: "{week_info['date']}",
            year: "{week_info['year']}"
        }};"""

    html = re.sub(
        r'const ISSUE_CONFIG = \{[\s\S]*?\};',
        issue_config,
        html
    )

    static = {
        "global": ("GLOBAL NEWS", "全球视野 / VISION", "bg-[#FF4D00]", "text-white"),
        "education": ("EDUCATION", "教育观察 / INSIGHT", "bg-[#CCFF00]", "text-black"),
        "university": ("UNIVERSITY", "院校动态 / UPDATE", "bg-[#0047FF]", "text-white"),
        "design": ("TECH & DESIGN", "前沿设计 / FUTURE", "bg-[#FF00FF]", "text-white"),
        "summer": ("LABS", "夏校科研 / LABS", "bg-[#00FF94]", "text-black"),
        "competitions": ("COMPETITIONS", "竞赛信息 / TROPHY", "bg-[#1A1A1A]", "text-white"),
    }

    sections_js = "const SECTIONS = [\n"
    global_id = 1
    data_map = {s["id"]: s for s in news_data}

    for sec_id in static:
        title, subtitle, bg, color = static[sec_id]
        items = data_map.get(sec_id, {}).get("items", [])

        sections_js += f"""  {{
    id: "{sec_id}",
    title: "{title}",
    subtitle: "{subtitle}",
    bgColor: "{bg}",
    textColor: "{color}",
    items: [
"""

        for item in items:
            clean = lambda x: str(x).replace("\n", "").replace('"', '\\"')
            sections_js += f"""      {{
        id: {global_id},
        title: "{clean(item.get('title', ''))}",
        content: "{clean(item.get('content', ''))}",
        source: "{clean(item.get('source', ''))}",
        date: "{clean(item.get('date', ''))}",
        image: "{clean(item.get('image', ''))}",
        tags: {json.dumps(item.get('tags', []), ensure_ascii=False)},
        url: "{clean(item.get('url', '#'))}",
        fullContent: "{clean(item.get('fullContent', ''))}",
        analysis: "{clean(item.get('analysis', ''))}"
      }},
"""
            global_id += 1

        sections_js += "    ]\n  },\n"

    sections_js += "];"

    html = re.sub(
        r'const SECTIONS = \[[\s\S]*?\];',
        sections_js,
        html
    )

    with open(HTML_FILE_PATH, "w", encoding="utf-8") as f:
        f.write(html)

# ================= 主入口 =================
if __name__ == "__main__":
    print("RAC Weekly News Auto Update")
    week = get_current_week_info()
    data = generate_news_content()
    update_html(data, week)
    print("Update complete:", week["vol"])
