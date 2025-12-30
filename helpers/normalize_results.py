import json

def normalize_results(results):
    normalized = []

    for item in results:

        # 1️⃣ Best case: already structured
        if hasattr(item, "structuredContent") and item.structuredContent:
            result = item.structuredContent.get("result")
            if isinstance(result, list):
                normalized.extend(result)
            elif isinstance(result, dict):
                normalized.append(result)
            continue

        # 2️⃣ CallToolResult with text content
        if hasattr(item, "content"):
            for tc in item.content:
                try:
                    normalized.append(json.loads(tc.text))
                except json.JSONDecodeError:
                    pass
            continue

        # 3️⃣ ReadResourceResult
        if hasattr(item, "contents"):
            for rc in item.contents:
                try:
                    normalized.append(json.loads(rc.text))
                except json.JSONDecodeError:
                    pass

    return normalized
