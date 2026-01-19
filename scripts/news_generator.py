import os
import json
import datetime
from google import genai

# ================= 配置区 =================
API_KEY = os.environ.get("GEMINI_API_KEY")
HTML_FILE_PATH = "index.html"

def get_current_week_info():
    """获取当前的日期、年份和周数"""
    today = datetime.date.today()
    year, week_num, _ = today.isocalendar()
    return {
        "vol": f"VOL.{week_num:02d}",
        "week": f"Week {week_num:02d}",
        "date": today.strftime("%Y.%m.%d"),
        "year": str(year)
    }

def generate_news_content():
    """调用 Gemini API 生成新闻数据"""
    if not API_KEY:
        raise ValueError("❌ 错误: 未找到 GEMINI_API_KEY 环境变量。")

    print(f"🚀 正在连接 Gemini API (key length: {len(API_KEY)})...")
    
    # 初始化客户端
    client = genai.Client(api_key=API_KEY)

    # 核心 Prompt
    prompt = f"""
    你是一名严格遵守事实核查与信息溯源规范的国际教育与全球资讯编辑。
    现在是 {datetime.date.today().strftime("%Y年%m月%d日")}。

    请检索【最近 7 天内首次发布】的信息，并按要求生成《RAC 周末闪讯》的内容。

    【信息来源要求】
    仅限：微博/公众号（高校/权威媒体）、权威新闻媒体（BBC/Reuters/FT/NYTimes等）、海外大学官方社媒。
    【明确排除】
    任何教培中介商业推广（新东方/启德等）、观点评论、未经证实信息。

    【内容主题范围】
    请围绕以下六类资讯进行筛选与整理（**每个板块必须包含 5 条资讯，总共 30 条**）：
    1. global (社会热点 / 国际新闻)
    2. education (海内外热点教育类新闻)
    3. university (世界顶尖院校官方动态)
    4. design (数字媒体 / 游戏动画 / 交互设计 / 智能工程 / 建筑 / 景观 / 城市相关类/ 工业产品类 / 视觉传达/交叉学科等相关专业的本科/硕士留学申请趋势、官方课程结构或培养方向变化)
    5. summer (Summer School / 暑期科研项目信息)
    6. competitions (截止时间在未来的国际权威竞赛)

    【JSON 输出格式要求】
    请直接输出以下 JSON 结构：
    [
        {{
            "id": "global",
            "items": [
                {{
                    "title": "标题 (Emoji + 中文)", 
                    "content": "**关键词**：两行摘要...", 
                    "source": "发布方", 
                    "date": "MM.DD", 
                    "image": "https://...",
                    "tags": ["Tag1", "Tag2"],
                    "relevant_majors": ["Interaction Design", "HCI"],
                    "key_points": ["核心点1", "核心点2", "核心点3"],
                    "url": "https://... (必须是真实链接)",
                    "fullContent": "<h3>小标题</h3><p>详细内容(400-600字)...</p>",
                    "analysis": "专家点评(2句话)..."
                }}
            ]
        }}
    ]
    """

    print("🔍 正在调用 Gemini API (Model: gemini-2.0-flash-exp)...")
    
    try:
        # 使用纯字典配置，这是最兼容的方式
        response = client.models.generate_content(
            model='gemini-2.0-flash-exp',
            contents=prompt,
            config={
                'tools': [{'google_search': {}}], # 启用搜索
                'response_mime_type': 'application/json' # 强制 JSON 模式
            }
        )
    except Exception as e:
        print(f"❌ API 调用失败: {e}")
        raise

    print("✅ API 响应成功，正在解析 JSON...")
    
    try:
        # JSON Mode 下，response.text 应该直接是合法的 JSON 字符串
        news_data = json.loads(response.text)
        return news_data
    except json.JSONDecodeError:
        print("❌ 错误: 无法解析 AI 返回的 JSON。")
        print(f"原始响应: {response.text[:500]}...")
        raise

def update_html_file(news_data, week_info):
    """读取 index.html 并更新 JS 数据部分"""
    if not os.path.exists(HTML_FILE_PATH):
        raise FileNotFoundError(f"❌ 未找到 {HTML_FILE_PATH} 文件")

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
        'global': {'subtitle': '全球视野', 'bgColor': 'bg-[#FF4D00]', 'textColor': 'text-white'},
        'education': {'subtitle': '教育观察', 'bgColor': 'bg-[#CCFF00]', 'textColor': 'text-black'},
        'university': {'subtitle': '院校动态', 'bgColor': 'bg-[#0047FF]', 'textColor': 'text-white'},
        'design': {'subtitle': '前沿设计', 'bgColor': 'bg-[#FF00FF]', 'textColor': 'text-white'},
        'summer': {'subtitle': '夏校科研', 'bgColor': 'bg-[#00FF94]', 'textColor': 'text-black'},
        'competitions': {'subtitle': '竞赛信息', 'bgColor': 'bg-[#1A1A1A]', 'textColor': 'text-white'}
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
            
            majors = item.get('relevant_majors', [])
            majors_str = json.dumps(majors, ensure_ascii=False) if isinstance(majors, list) else "[]"

            kps = item.get('key_points', [])
            kps_str = json.dumps(kps, ensure_ascii=False) if isinstance(kps, list) else "[]"
            
            js_sections_str += "                    {\n"
            js_sections_str += f"                        id: {current_id},\n"
            js_sections_str += f"                        title: \"{clean_title}\",\n"
            js_sections_str += f"                        content: \"{clean_summary}\",\n"
            js_sections_str += f"                        source: \"{clean_source}\",\n"
            js_sections_str += f"                        date: \"{clean_date}\",\n"
            js_sections_str += f"                        image: \"{clean_image}\",\n"
            js_sections_str += f"                        tags: {tags_str},\n"
            js_sections_str += f"                        relevant_majors: {majors_str},\n"
            js_sections_str += f"                        key_points: {kps_str},\n"
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
