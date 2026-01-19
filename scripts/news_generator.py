import os
import re
import json
import datetime
from google import genai
from google.genai import types

# ================= 配置区 =================
# 从 GitHub Secrets 获取 API Key
API_KEY = os.environ.get("GEMINI_API_KEY")
HTML_FILE_PATH = "index.html"

def get_current_week_info():
    """获取当前的日期、年份和周数"""
    today = datetime.date.today()
    # ISO 周历
    year, week_num, _ = today.isocalendar()
    return {
        "vol": f"VOL.{week_num:02d}",
        "week": f"Week {week_num:02d}",
        "date": today.strftime("%Y.%m.%d"),
        "year": str(year)
    }

def extract_json_from_text(text):
    """尝试从混合文本中提取 JSON 列表"""
    try:
        # 1. 尝试直接解析
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    try:
        # 2. 尝试提取 Markdown 代码块 ```json ... ```
        match = re.search(r'```json\s*(\[[\s\S]*?\])\s*```', text)
        if match:
            return json.loads(match.group(1))
        
        # 3. 尝试寻找最外层的方括号 []
        start = text.find('[')
        end = text.rfind(']')
        if start != -1 and end != -1:
            json_str = text[start:end+1]
            return json.loads(json_str)
            
    except Exception as e:
        print(f"JSON 提取失败: {e}")
    
    return None

def generate_news_content():
    """调用 Gemini API 生成新闻数据 (使用新版 google-genai SDK)"""
    if not API_KEY:
        raise ValueError("❌ 错误: 未找到 GEMINI_API_KEY 环境变量。请在 GitHub Secrets 或本地环境变量中配置。")

    print(f"🚀 正在连接 Gemini API (key length: {len(API_KEY)})...")
    
    # 初始化新版客户端
    client = genai.Client(api_key=API_KEY)

    # 核心 Prompt
    prompt = f"""
    你是一名严格遵守事实核查与信息溯源规范的国际教育与全球资讯编辑。
    现在是 {datetime.date.today().strftime("%Y年%m月%d日")}。

    请你完成以下任务，并【只输出最终资讯内容本身】。为了让程序能够处理，**请务必将结果封装为 JSON 格式**（具体格式见下方）。

    【时间范围】
    仅检索并整理【最近 7 天内首次发布】的信息。

    【信息来源要求】
    仅限以下来源：
    - 微博、微信公众号（高校 / 权威媒体官方账号）
    - 国内外权威新闻媒体官方账号（如 BBC / Reuters / FT / NYTimes 等）
    - 海外大学官方 网站/Instagram / X(Twitter) / Facebook 账号

    【明确排除】
    - 任何教培、留学中介、商业推广内容（如新东方、启德、IDP 等）
    - 二次转载、观点评论、未经证实的信息

    【内容主题范围】
    请围绕以下六类资讯进行筛选与整理（每个板块精选 5 条，总计 30 条）：
    1. global (社会热点 / 国际新闻)
    2. education (海内外热点教育类新闻)
    3. university (世界顶尖院校官方动态)
    4. design (数字媒体 / 游戏动画 / 交互设计 / 智能工程 / 建筑 / 景观 / 城市相关类/ 工业产品类 / 视觉传达/交叉学科等相关专业的本科/硕士留学申请趋势、官方课程结构或培养方向变化)
    5. summer (Summer School / 暑期科研项目信息)
    6. competitions (截止时间在未来的国际权威竞赛)

    【筛选与排序规则】
    - 总数：严格保留 30 条
    - 按“社交媒体讨论热度 + 权威性”综合排序
    - 同一事件只保留 1 条

    【格式要求转换】
    请将你作为编辑整理好的内容映射到以下 JSON 结构中。
    对于 content 字段，请严格执行：**关键词 / 关键词**：两行文字概述事件核心信息。
    对于 source 和 date 字段，请提取括号内的（发布方 – 推送时间）。
    
    **关键要求：**
    1. `url`: 必须是真实的、可访问的原始新闻链接（以 http 开头），不能留空。
    2. `image`: 请尝试寻找每条新闻的相关图片 URL。
    3. `analysis`: 针对该新闻，写一段简短犀利的“专家点评”（2句话），针对学生/家长，分析其对申请或未来的影响。

    JSON 输出示例：
    [
        {{
            "id": "global",
            "items": [
                {{
                    "title": "关键词 (Emoji + 中文)", 
                    "content": "**关键词 / 关键词**：两行文字概述事件核心信息。", 
                    "source": "发布方", 
                    "date": "MM.DD", 
                    "image": "https://example.com/news-image.jpg",
                    "tags": ["Tag1", "Tag2"],
                    "url": "https://www.bbc.com/news/example-story",
                    "fullContent": "<p>这里写一段详细报道（约150字），支持HTML标签。</p>",
                    "analysis": "这里写专家点评..."
                }}
            ]
        }},
        ... 其他板块
    ]
    """

    print("🔍 正在调用 Gemini API 进行严格筛选与生成... (Target: 30 items)")
    try:
        # 使用新版 SDK 调用方法
        response = client.models.generate_content(
            model='gemini-2.0-flash-exp',
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())] # 新版工具定义方式
            )
        )
    except Exception as e:
        print(f"❌ API 调用失败: {e}")
        raise

    print("✅ API 响应成功，正在解析 JSON...")
    
    # 新版 SDK 的 response.text 直接可用
    news_data = extract_json_from_text(response.text)
    
    if not news_data:
        print("❌ 错误: 无法从 AI 响应中提取有效的 JSON 数据。")
        print("🔍 原始响应片段 (前500字符):")
        try:
            print(response.text[:500] + "...")
        except:
            print("无法打印响应内容")
        raise ValueError("Invalid JSON response from AI")
        
    return news_data

def update_html_file(news_data, week_info):
    """读取 index.html 并更新 JS 数据部分"""
    if not os.path.exists(HTML_FILE_PATH):
        raise FileNotFoundError(f"❌ 未找到 {HTML_FILE_PATH} 文件，请确保脚本在项目根目录下运行。")

    with open(HTML_FILE_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. 更新 ISSUE_CONFIG
    new_config_str = f"""const ISSUE_CONFIG = {{
            vol: "{week_info['vol']}",           
            week: "{week_info['week']}",         
            date: "{week_info['date']}",      
            year: "{week_info['year']}"
        }};"""
    
    content = re.sub(
        r'const\s+ISSUE_CONFIG\s*=\s*\{[\s\S]*?\};', 
        new_config_str, 
        content
    )

    # 2. 更新 SECTIONS
    static_props = {
        'global': {'subtitle': '政策风向与大事件', 'bgColor': 'bg-[#FF4D00]', 'textColor': 'text-white'},
        'education': {'subtitle': '留学趋势与学费变动', 'bgColor': 'bg-[#CCFF00]', 'textColor': 'text-black'},
        'university': {'subtitle': '招生简章与截止日', 'bgColor': 'bg-[#0047FF]', 'textColor': 'text-white'},
        'design': {'subtitle': '黑科技与设计风口', 'bgColor': 'bg-[#FF00FF]', 'textColor': 'text-white'},
        'summer': {'subtitle': '背景提升机会', 'bgColor': 'bg-[#00FF94]', 'textColor': 'text-black'},
        'competitions': {'subtitle': '高含金量赛事', 'bgColor': 'bg-[#1A1A1A]', 'textColor': 'text-white'}
    }
    
    titles = {
        'global': 'GLOBAL NEWS', 'education': 'EDUCATION',
        'university': 'UNIVERSITY', 'design': 'TECH & DESIGN',
        'summer': 'LABS', 'competitions': 'COMPETITIONS'
    }

    js_sections_str = "const SECTIONS = [\n"
    
    global_id_counter = 1

    for section_data in news_data:
        sec_id = section_data['id']
        props = static_props.get(sec_id, {})
        
        display_title = titles.get(sec_id, sec_id.upper())
        
        js_sections_str += "            {\n"
        js_sections_str += f"                id: '{sec_id}',\n"
        js_sections_str += f"                title: '{display_title}',\n"
        js_sections_str += f"                subtitle: '{props.get('subtitle', '')}',\n"
        js_sections_str += f"                bgColor: '{props.get('bgColor', '')}',\n"
        js_sections_str += f"                textColor: '{props.get('textColor', '')}',\n"
        js_sections_str += "                items: [\n"
        
        items = section_data.get('items', [])
        for item in items:
            current_id = global_id_counter
            global_id_counter += 1

            clean_content = str(item.get('fullContent', '')).replace('\n', '').replace('"', '\\"').replace("'", "\\'")
            clean_summary = str(item.get('content', '')).replace('"', '\\"').replace("'", "\\'")
            clean_title = str(item.get('title', '')).replace('"', '\\"').replace("'", "\\'")
            clean_image = str(item.get('image', '')).replace('"', '\\"')
            clean_analysis = str(item.get('analysis', '')).replace('"', '\\"').replace("'", "\\'")
            clean_source = str(item.get('source', 'RAC News'))
            clean_date = str(item.get('date', ''))
            clean_url = str(item.get('url', '#'))
            
            tags = item.get('tags', [])
            tags_str = json.dumps(tags, ensure_ascii=False) if isinstance(tags, list) else "[]"
            
            js_sections_str += "                    {\n"
            js_sections_str += f"                        id: {current_id},\n"
            js_sections_str += f"                        title: \"{clean_title}\",\n"
            js_sections_str += f"                        content: \"{clean_summary}\",\n"
            js_sections_str += f"                        source: \"{clean_source}\",\n"
            js_sections_str += f"                        date: \"{clean_date}\",\n"
            js_sections_str += f"                        image: \"{clean_image}\",\n"
            js_sections_str += f"                        tags: {tags_str},\n"
            js_sections_str += f"                        url: \"{clean_url}\",\n"
            js_sections_str += f"                        fullContent: \"{clean_content}\",\n"
            js_sections_str += f"                        analysis: \"{clean_analysis}\"\n"
            js_sections_str += "                    },\n"
        
        js_sections_str += "                ]\n"
        js_sections_str += "            },\n"

    js_sections_str += "        ];"

    content = re.sub(
        r'const\s+SECTIONS\s*=\s*\[([\s\S]*?)\];', 
        js_sections_str, 
        content
    )

    with open(HTML_FILE_PATH, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ 成功更新 {HTML_FILE_PATH}！版本: {week_info['vol']} ({week_info['date']})")

if __name__ == "__main__":
    try:
        print("🎬 开始执行周更任务...")
        week_info = get_current_week_info()
        print(f"📅 目标版本: {week_info['vol']} ({week_info['date']})")
        
        news_data = generate_news_content()
        update_html_file(news_data, week_info)
        
        print("🎉 所有任务完成。")
    except Exception as e:
        print(f"❌ 任务失败: {e}")
        exit(1)
