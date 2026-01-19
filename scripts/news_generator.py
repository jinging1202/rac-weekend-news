import os
import re
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

def extract_json_from_text(text):
    """尝试从混合文本中提取 JSON 列表"""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    try:
        # 提取 ```json ... ```
        match = re.search(r'```json\s*(\[[\s\S]*?\])\s*```', text)
        if match:
            return json.loads(match.group(1))
        
        # 提取 [ ... ]
        start = text.find('[')
        end = text.rfind(']')
        if start != -1 and end != -1:
            json_str = text[start:end+1]
            return json.loads(json_str)
            
    except Exception as e:
        print(f"JSON 提取失败: {e}")
    
    return None

def generate_news_content():
    """调用 Gemini API 生成新闻数据 (使用新版 SDK)"""
    if not API_KEY:
        raise ValueError("❌ 错误: 未找到 GEMINI_API_KEY。请在 GitHub Secrets 中配置。")

    print(f"🚀 正在连接 Gemini API (新版 SDK)...")
    
    # 关键修改：使用新版 SDK 客户端
    client = genai.Client(api_key=API_KEY)

    prompt = f"""
    你是一名专业、犀利、有深度的国际教育与设计艺术资讯主编。
    现在是 {datetime.date.today().strftime("%Y年%m月%d日")}。

    请检索【最近 7 天内首次发布】的信息，并按要求生成《RAC 周末闪讯》的内容。

    【内容主题范围】
    请围绕以下六类资讯进行筛选与整理（**每个板块必须包含 5 条资讯，总共 30 条**）：
    1. global (社会热点 / 国际新闻)
    2. education (海内外热点教育类新闻)
    3. university (世界顶尖院校官方动态)
    4. design (数字媒体 / 游戏动画 / 交互设计 / 智能工程 / 建筑 / 景观 / 城市相关类/ 工业产品类 / 视觉传达/交叉学科等相关专业的本科/硕士留学申请趋势、官方课程结构或培养方向变化)
    5. summer (Summer School / 暑期科研项目信息)
    6. competitions (截止时间在未来的国际权威竞赛)

    【深度内容生成要求】
    不要只写简介！**每条新闻必须是一篇 400-600 字的深度微报道。**
    
    1.  **key_points**: 提炼 3 个核心情报（Bullet points）。
    2.  **relevant_majors**: 列出受此新闻影响的具体设计/艺术专业名称（英文）。
    3.  **fullContent**: 
        * 必须包含 HTML 标签（`<h3>` 小标题, `<p>` 段落, `<ul>` 列表）。
        * 内容必须详实，包含数据支持、背景分析和未来预测。
    4.  **analysis**: 针对学生/家长的犀利点评（2句话），直击痛点，给出行动建议。
    5.  **url**: 必须是真实的原始新闻链接，不能留空。
    6.  **image**: 必须提供一张相关图片的 URL (og:image)。

    【格式要求】
    请直接输出 JSON 数组，无需 Markdown 标记。
    """

    print("🔍 正在调用 Gemini API 进行深度内容生成... (Target: 30 items)")
    
    try:
        # 关键修改：使用新版 SDK 的调用方式
        response = client.models.generate_content(
            model='gemini-2.0-flash-exp',
            contents=prompt,
            config={
                'tools': [{'google_search': {}}], # 新版 SDK 的搜索工具配置
                'response_mime_type': 'application/json' # 强制 JSON 模式
            }
        )
    except Exception as e:
        print(f"❌ API 调用失败: {e}")
        raise

    print("✅ API 响应成功，正在解析 JSON...")
    
    # 新版 SDK 直接从 response.text 获取内容
    news_data = extract_json_from_text(response.text)
    
    if not news_data:
        print("❌ 错误: 无法从 AI 响应中提取有效的 JSON 数据。")
        print(f"原始响应片段: {response.text[:500]}")
        raise ValueError("Invalid JSON response from AI")
        
    return news_data

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
    
    content = re.sub(r'const\s+ISSUE_CONFIG\s*=\s*\{[\s\S]*?\};', new_config_str, content)

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

    # 处理 AI 返回的数据（兼容列表或字典结构）
    data_list = news_data if isinstance(news_data, list) else []
    
    # 建立 ID 到数据的映射，防止 AI 返回顺序错乱
    data_map = {item['id']: item for item in data_list if 'id' in item}

    # 按照我们预定义的顺序遍历板块
    for sec_key in ['global', 'education', 'university', 'design', 'summer', 'competitions']:
        section_data = data_map.get(sec_key, {'items': []})
        props = static_props.get(sec_key, {})
        display_title = titles.get(sec_key, sec_key.upper())
        
        js_sections_str += "            {\n"
        js_sections_str += f"                id: '{sec_key}',\n"
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

    content = re.sub(r'const\s+SECTIONS\s*=\s*\[([\s\S]*?)\];', js_sections_str, content)

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
