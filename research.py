from google import genai
from google.genai import types

from config import RESEARCH_MODEL, RESEARCH_FALLBACK_MODEL, RETRY_WAIT_SECONDS, MAX_RETRIES
from utils import call_with_retry_and_fallback


def research_version(api_key: str, version: str, release_data: dict) -> dict:
    """指定バージョンの変更内容を Gemini + Google Search Grounding で調査する。"""

    release_notes = release_data.get("body") or ""
    published_at = release_data.get("published_at") or ""
    html_url = release_data.get("html_url") or ""

    prompt = f"""あなたは技術リサーチャーです。
Claude Code バージョン {version} のアップデート内容について、詳しく調査してください。

## 公式リリース情報
- バージョン: {version}
- リリース日時: {published_at}
- URL: {html_url}
- リリースノート:
{release_notes}

## 調査してほしい内容
Google Search を使って以下の観点で情報を収集し、日本語で詳しくまとめてください。

1. **新機能**: このバージョンで追加された主要な新機能
2. **変更点**: 既存機能の変更・改善
3. **バグ修正**: 解決された問題・不具合
4. **破壊的変更**: 後方互換性に影響する変更（ある場合）
5. **使いやすさの向上**: UX・DX の改善
6. **コミュニティの反応**: ユーザーや開発者の評価・感想（ある場合）

## 出力形式
Podcast のコンテンツとして使いやすいよう、具体的で分かりやすい日本語でまとめてください。
専門用語は必要に応じて補足説明を加えてください。
各項目について、「なぜそれが重要か」「ユーザーにどんな影響があるか」を意識して記述してください。
"""

    client = genai.Client(api_key=api_key)

    def call_primary():
        print(f"[ログ] 調査モデル: {RESEARCH_MODEL}")
        response = client.models.generate_content(
            model=RESEARCH_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())]
            ),
        )
        return response.text

    def call_fallback():
        print(f"[ログ] フォールバック調査モデル: {RESEARCH_FALLBACK_MODEL}")
        response = client.models.generate_content(
            model=RESEARCH_FALLBACK_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())]
            ),
        )
        return response.text

    research_text = call_with_retry_and_fallback(
        call_primary, call_fallback, MAX_RETRIES, RETRY_WAIT_SECONDS
    )

    return {
        "version": version,
        "published_at": published_at,
        "html_url": html_url,
        "release_notes": release_notes,
        "research": research_text,
    }
