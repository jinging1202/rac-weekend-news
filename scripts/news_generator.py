import os
import re
import json
import datetime
import time
import google.generativeai as genai

# ================= 配置区 =================
# 从 GitHub Secrets 获取 API Key
API_KEY = os.environ.get("GEMINI_API_KEY")
HTML_FILE_PATH = "index.html"
# 使用支持搜索功能的最新模型
MODEL_NAME = 'gemini-2.0-flash' 

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
    """尝试从 AI 返回的文本中稳健提取 JSON"""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # 尝试匹配 markdown 代码块
    try:
        match = re.search(r'```json\s*(\[[\s\S]*?\])\s*```', text)
        if match:
            return json.loads(match.group(1))
        # 尝试直接寻找数组括号
        start = text.find('[')
        end = text.rfind(']')
        if start != -1 and end != -1:
            return json.loads(text[start:end+1])
    except Exception:
        pass
    return None

def generate_news_content():
    """调用 Gemini API 生成新闻数据"""
    if not API_KEY:
        raise ValueError("❌ 错误: 未找到 GEMINI_API_KEY 环境变量。请在 GitHub Secrets 中配置。")

    print(f"正在初始化 Google GenAI Client...")
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel(MODEL_NAME)
    
    # 核心 Prompt - 严格植入用户的编辑指令 (30条规则)
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
    请围绕以下六类资讯进行筛选与整理（**每个板块必须包含 5 条资讯，总计 30 条**）：
    1. global (社会热点 / 国际新闻)
    2. education (海内外热点教育类新闻)
    3. university (世界顶尖院校官方动态)
    4. design (数字媒体 / 游戏动画 / 交互设计 / 智能工程 / 建筑 / 景观 / 城市相关类/ 工业产品类 / 视觉传达/交叉学科等相关专业的本科/硕士留学申请趋势、官方课程结构或培养方向变化)
    5. summer (Summer School / 暑期科研项目信息)
    6. competitions (截止时间在未来的国际权威竞赛)

    【筛选与排序规则】
    - 总数：严格保留 30 条。
    - 编号：所有资讯的 ID 必须在整个列表中连续递增。

    【格式要求转换】
    请将你作为编辑整理好的内容映射到以下 JSON 结构中。
    
    **关键字段要求：**
    1. `url`: **必须是真实的、可访问的原始新闻链接（以 http 开头），绝对不能留空或使用模拟链接。**
    2. `image`: 请尝试寻找每条新闻的相关图片 URL 填入 image 字段（如 og:image）。
    3. `analysis`: 针对该新闻，写一段简短犀利的“专家点评”（2句话），针对学生/家长，分析其对申请或未来的影响。
    4. `content`: **关键词 / 关键词**：两行文字概述事件核心信息。

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

    print("正在调用 Gemini API 进行严格筛选与生成... (Target: 30 items)")
    
    # 配置 Google Search 工具
    tools = [{'google_search': {}}]
    
    response = model.generate_content(
        prompt, 
        tools=tools,
        generation_config={'response_mime_type': 'application/json'}
    )
    
    news_data = extract_json_from_text(response.text)
    if not news_data:
        print("Raw Output:", response.text)
        raise ValueError("Error: AI 返回的数据无法解析为 JSON。")
    
    return news_data

def update_html_file(news_data, week_info):
    """读取 index.html 并更新 JS 数据部分"""
    if not os.path.exists(HTML_FILE_PATH):
        raise FileNotFoundError(f"未找到 {HTML_FILE_PATH} 文件")

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
        r'const ISSUE_CONFIG = \{[\s\S]*?\};', 
        new_config_str, 
        content
    )

    # 2. 更新 SECTIONS
    # 静态属性映射 (确保颜色和图标正确)
    static_props = {
        'global': {'subtitle': '全球视野 / VISION', 'bgColor': 'bg-[#FF4D00]', 'textColor': 'text-white'},
        'education': {'subtitle': '教育观察 / INSIGHT', 'bgColor': 'bg-[#CCFF00]', 'textColor': 'text-black'},
        'university': {'subtitle': '院校动态 / UPDATE', 'bgColor': 'bg-[#0047FF]', 'textColor': 'text-white'},
        'design': {'subtitle': '前沿设计 / FUTURE', 'bgColor': 'bg-[#FF00FF]', 'textColor': 'text-white'},
        'summer': {'subtitle': '夏校科研 / LABS', 'bgColor': 'bg-[#00FF94]', 'textColor': 'text-black'},
        'competitions': {'subtitle': '竞赛信息 / TROPHY', 'bgColor': 'bg-[#1A1A1A]', 'textColor': 'text-white'}
    }

    # 标题映射
    titles = {
        'global': 'GLOBAL NEWS', 'education': 'EDUCATION',
        'university': 'UNIVERSITY', 'design': 'TECH & DESIGN',
        'summer': 'LABS', 'competitions': 'COMPETITIONS'
    }

    js_sections_str = "const SECTIONS = [\n"
    
    # 【核心逻辑】：强制连续 ID 生成器 (1-30)
    # 不依赖 AI 返回的 ID，而是由代码强制分配，确保前端显示正确
    global_id_counter = 1

    # 将 news_data 转换为字典方便查找
    data_dict = {item['id']: item for item in news_data if 'id' in item}
    
    # 按固定顺序遍历板块
    section_order = ['global', 'education', 'university', 'design', 'summer', 'competitions']

    for sec_id in section_order:
        props = static_props.get(sec_id, {})
        # 获取该板块的 AI 数据，如果没有则为空列表
        sec_data = data_dict.get(sec_id, {'items': []})
        
        js_sections_str += "            {\n"
        js_sections_str += f"                id: '{sec_id}',\n"
        js_sections_str += f"                title: '{titles.get(sec_id, sec_id.upper())}',\n"
        js_sections_str += f"                subtitle: '{props.get('subtitle', '')}',\n"
        js_sections_str += f"                bgColor: '{props.get('bgColor', '')}',\n"
        js_sections_str += f"                textColor: '{props.get('textColor', '')}',\n"
        js_sections_str += "                items: [\n"
        
        for item in sec_data.get('items', []):
            current_id = global_id_counter
            global_id_counter += 1

            # 清理字符串转义，防止 JS 语法错误
            clean = lambda s: str(s).replace('\n', '').replace('"', '\\"').replace("'", "\\'")
            
            clean_title = clean(item.get('title', ''))
            clean_summary = clean(item.get('content', ''))
            clean_source = clean(item.get('source', 'RAC News'))
            clean_date = clean(item.get('date', ''))
            clean_image = clean(item.get('image', ''))
            clean_url = clean(item.get('url', '#'))
            clean_full = clean(item.get('fullContent', ''))
            clean_analysis = clean(item.get('analysis', ''))
            
            # 处理 tags 列表
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
            js_sections_str += f"                        fullContent: \"{clean_full}\",\n"
            js_sections_str += f"                        analysis: \"{clean_analysis}\"\n"
            js_sections_str += "                    },\n"
        
        js_sections_str += "                ]\n"
        js_sections_str += "            },\n"

    js_sections_str += "        ];"

    content = re.sub(
        r'const SECTIONS = \[([\s\S]*?)\];', 
        js_sections_str, 
        content
    )

    with open(HTML_FILE_PATH, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ 成功更新 {HTML_FILE_PATH}！版本: {week_info['vol']}")

if __name__ == "__main__":
    try:
        print("开始执行周更任务...")
        week_info = get_current_week_info()
        print(f"目标版本: {week_info['vol']} ({week_info['date']})")
        
        news_data = generate_news_content()
        update_html_file(news_data, week_info)
        
        print("所有任务完成。")
    except Exception as e:
        print(f"❌ 任务失败: {e}")
        exit(1)
