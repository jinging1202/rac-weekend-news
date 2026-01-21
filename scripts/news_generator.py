import os
import json
import datetime
import re
from google import genai
from google.genai import types

# 配置
API_KEY = os.environ.get("GEMINI_API_KEY")
HTML_FILE_PATH = "index.html"

# 定义板块
CATEGORIES = [
    "Global", "Education", "University", "Design", "Summer", "Competitions"
]

def get_gemini_client():
    if not API_KEY:
        raise ValueError("GEMINI_API_KEY not found in environment variables")
    return genai.Client(api_key=API_KEY)

def generate_news_for_category(client, category):
    """
    使用 Gemini 搜索并生成特定板块的新闻。
    """
    print(f"Generating news for category: {category}...")
    
    today = datetime.date.today().isoformat()
    
    # 构建 Prompt
    prompt = f"""
    You are a strict international design education editor. 
    Current Date: {today}.
    
    Task: Find 5 DISTINCT, FACTUAL news items specifically for the category '{category}' from the LAST 7 DAYS.
    
    Category Definition:
    - Global: World news, art tech, society (e.g., AI law, climate change affecting design).
    - Education: General education policy, art education market trends.
    - University: Official updates from top art schools (RCA, UAL, RISD, Parsons, MIT Media Lab, etc.).
    - Design: Trends in UX, Architecture, Industrial Design, Visual Communication, Fashion.
    - Summer: New summer school openings or research programs for high school/uni students.
    - Competitions: International design awards (Red Dot, iF, young architect competitions) calling for entries.

    Constraints:
    1. TIME: Must be published within the last 7 days.
    2. SOURCE: Official university websites, major news outlets (BBC, Dezeen, ArchDaily), or reputable social media.
    3. BLACKLIST: NO training agency ads, NO "New Oriental", NO "EIC Education". 
    4. IMAGE: Provide a direct URL to a relevant image if found, otherwise leave empty string.
    
    Output Format: Return a JSON object with a key "items" containing a list of 5 objects.
    Each object must have:
    - title (Chinese, engaging, max 20 chars)
    - content (Chinese, format: "核心关键词：KeyWord。Summary.")
    - fullContent (Chinese, HTML formatted <p> tags, 300-400 words, journalistic tone)
    - analysis (Chinese, 2 sentences, expert advice for students applying to art schools)
    - tags (Array of 3 strings, mixed EN/CN)
    - url (The source URL)
    - image (Direct image URL or empty string)
    """

    # 调用 Gemini
    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash-exp', # Or gemini-2.5-flash-preview-09-2025
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                response_mime_type="application/json"
            )
        )
        
        # 解析结果
        result = json.loads(response.text)
        return result.get("items", [])
        
    except Exception as e:
        print(f"Error generating {category}: {e}")
        # 返回空列表，后续处理会填补
        return []

def update_html_file(new_data):
    """
    读取 HTML，找到 MOCK DATA 区域并替换
    """
    with open(HTML_FILE_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    # 构造新的 JSON 字符串
    json_str = json.dumps(new_data, ensure_ascii=False, indent=4)
    
    # 使用正则替换 INITIAL_DATA 变量的内容
    # 匹配 const INITIAL_DATA = { ... }; 
    # 注意：JS 对象结尾的分号
    pattern = r"const INITIAL_DATA = \{[\s\S]*?\};"
    replacement = f"const INITIAL_DATA = {json_str};"
    
    new_content = re.sub(pattern, replacement, content)
    
    with open(HTML_FILE_PATH, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("HTML file updated successfully.")

def main():
    client = get_gemini_client()
    
    all_news = []
    global_id = 1
    
    for category in CATEGORIES:
        items = generate_news_for_category(client, category)
        
        # 确保每个板块有 5 条，如果不够（API 失败），生成 Mock 数据填补，保证 ID 连续
        while len(items) < 5:
            items.append({
                "title": f"{category} 资讯获取中...",
                "content": "核心关键词：系统维护。该板块数据暂未更新，请稍后查看。",
                "fullContent": "<p>由于网络原因或信息源不足，AI 暂时无法获取该板块的最新实时新闻。</p>",
                "analysis": "建议直接咨询人工顾问获取最新动态。",
                "tags": ["System", "Update"],
                "url": "https://racstudio.cn",
                "image": ""
            })
        
        # 截取前5条并处理 ID
        for item in items[:5]:
            item['id'] = global_id
            item['category'] = category
            # 简单的清洗，确保字段存在
            if 'image' not in item: item['image'] = ""
            if 'fullContent' not in item: item['fullContent'] = f"<p>{item.get('content', '')}</p>"
            all_news.append(item)
            global_id += 1
            
    final_data = {
        "updateTime": datetime.date.today().isoformat(),
        "news": all_news
    }
    
    update_html_file(final_data)

if __name__ == "__main__":
    main()
