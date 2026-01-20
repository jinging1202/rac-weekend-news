from google.genai.errors import ClientError

def generate_news_content():
    if not API_KEY:
        raise RuntimeError("GEMINI_API_KEY 未配置")

    client = genai.Client(api_key=API_KEY)

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
    except ClientError as e:
        if "RESOURCE_EXHAUSTED" in str(e):
            print("⚠️ Gemini 配额耗尽，跳过本周自动更新。")
            return None
        raise

    data = extract_json(response.text)
    if not data:
        raise RuntimeError("无法解析 Gemini 返回的 JSON")

    return data
