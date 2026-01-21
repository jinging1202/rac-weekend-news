import os
import json
import time
from typing import List, Dict
from google import genai

# =========================
# 基础配置
# =========================
MODEL_NAME = "gemini-3.0-flash"
TARGET_TOTAL = 30
OUTPUT_FILE = "data/news.json"

SECTIONS = [
    ("Global", "社会热点 / 国际新闻", 5),
    ("Education", "海内外热点教育类新闻", 5),
    ("University", "世界顶尖院校官方动态", 5),
    (
        "Design",
        "设计 / 艺术 / 城市建筑 / 数字媒体 / 游戏 / 交互 / 工业 / 视觉等专业趋势与课程变化",
        5,
    ),
    ("Summer", "Summer School / 暑期科研项目", 5),
    ("Competitions", "截止时间在未来的国际权威竞赛", 5),
]

<script type="text/babel">
const { useEffect, useState } = React;

function App() {
  const [news, setNews] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("./data/news.json?_=" + Date.now())
      .then(res => res.json())
      .then(data => {
        setNews(data);
        setLoading(false);
      })
      .catch(err => {
        console.error("Failed to load news.json", err);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return <div className="p-6 text-center">Loading Weekly News…</div>;
  }

  if (!news || news.total !== 30) {
    return <div className="p-6 text-red-600">News data invalid.</div>;
  }

  return <NewsLayout data={news} />;
}
</script>


# =========================
# 工具函数
# =========================
def is_valid_item(item: Dict) -> bool:
    required_fields = ["title", "summary", "source", "url"]
    return all(item.get(f) for f in required_fields)


def safe_json_load(text: str):
    try:
        return json.loads(text)
    except Exception:
        return None


# =========================
# 单板块生成（核心）
# =========================
def generate_by_section(
    client: genai.Client,
    section_name: str,
    section_desc: str,
    target_count: int,
    max_rounds: int = 3,
    sleep_sec: int = 3,
) -> List[Dict]:

    items: List[Dict] = []
    seen_titles = set()

    for round_idx in range(max_rounds):
        print(f"[{section_name}] Round {round_idx + 1}")

        prompt = f"""
        You are an international education and global affairs editor.

        Generate news strictly for the following section:

        Section: {section_name}
        Description: {section_desc}

        Requirements:
        - Real, verifiable news or official announcements
        - Clear relevance to the section
        - Avoid duplicated topics
        - If section is Competitions: deadlines must be in the future

        Output ONLY a JSON array.
        Each item must include:
        - title
        - summary （400-500 words)
        - source (organization / media / institution)
        - url (real, starts with https)
        """

        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt,
            )
        except Exception as e:
            print(f"[{section_name}] API error: {e}")
            time.sleep(sleep_sec)
            continue

        candidates = safe_json_load(response.text)
        if not isinstance(candidates, list):
            print(f"[{section_name}] Invalid JSON")
            time.sleep(sleep_sec)
            continue

        for item in candidates:
            if not is_valid_item(item):
                continue

            title = item["title"].strip()
            if title in seen_titles:
                continue

            seen_titles.add(title)
            item["section"] = section_name
            items.append(item)

            if len(items) >= target_count:
                print(f"[{section_name}] Completed ({target_count})")
                return items

        time.sleep(sleep_sec)

    return items


# =========================
# 六板块调度器（结构保障）
# =========================
def generate_news_by_sections(client: genai.Client) -> List[Dict] | None:
    all_items: List[Dict] = []

    for section_name, desc, count in SECTIONS:
        section_items = generate_by_section(
            client=client,
            section_name=section_name,
            section_desc=desc,
            target_count=count,
        )

        if len(section_items) < count:
            print(
                f"[ABORT] Section '{section_name}' only generated "
                f"{len(section_items)}/{count} items"
            )
            return None

        all_items.extend(section_items)

    if len(all_items) != TARGET_TOTAL:
        print(f"[ABORT] Total {len(all_items)} != {TARGET_TOTAL}")
        return None

    return all_items


# =========================
# 输出
# =========================
def write_output(data: Dict):
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# =========================
# 主入口
# =========================
def main():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("[ERROR] GEMINI_API_KEY not set")
        return

    client = genai.Client(api_key=api_key)

    print("[INFO] Start weekly news generation (6 sections × 5 items)")
    items = generate_news_by_sections(client)

    if not items:
        print("[INFO] Generation incomplete. Skip publish.")
        return  # exit 0，CI 不失败

    write_output(
        {
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total": len(items),
            "sections": SECTIONS,
            "items": items,
        }
    )

    print("[SUCCESS] Weekly news generated (30 items)")


if __name__ == "__main__":
    main()
