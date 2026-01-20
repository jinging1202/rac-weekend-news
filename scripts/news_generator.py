import os
import json
import sys
from datetime import datetime

from google import genai
from google.genai.errors import ClientError


OUTPUT_PATH = "public/data/latest.json"
MODEL_NAME = "gemini-2.0-flash"


def generate_news_content():
    """
    Generate weekly news content using Gemini.
    Returns:
        ("SUCCESS", data_dict)
        ("SKIP", reason_string)
    """

    try:
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents="""
            Generate a structured weekly news digest for architecture,
            urban design, and landscape students.
            Output valid JSON only.
            """
        )

        if not response or not response.text:
            return "SKIP", "Empty response from model"

        try:
            data = json.loads(response.text)
        except json.JSONDecodeError:
            return "SKIP", "Model output is not valid JSON"

        return "SUCCESS", data

    except ClientError as e:
        # ✅ 核心：配额、429、限流全部在这里被吃掉
        print(f"[WARN] Gemini API unavailable: {e}", file=sys.stderr)
        return "SKIP", "Gemini quota or API error"

    except Exception as e:
        # 兜底保护，防止任何未知错误炸 CI
        print(f"[ERROR] Unexpected error: {e}", file=sys.stderr)
        return "SKIP", "Unexpected runtime error"


def write_output(data: dict):
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    payload = {
        "generated_at": datetime.utcnow().isoformat(),
        "data": data
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def main():
    status, result = generate_news_content()

    if status != "SUCCESS":
        # ✅ 关键：软失败 → 直接退出，但 exit code = 0
        print(f"[INFO] News generation skipped: {result}")
        return

    write_output(result)
    print("[INFO] Weekly news generated successfully")


if __name__ == "__main__":
    main()
