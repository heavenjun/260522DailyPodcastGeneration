import json
from google import genai
from google.genai import types

from config import (
    RESEARCH_MODEL,
    RESEARCH_FALLBACK_MODEL,
    RETRY_WAIT_SECONDS,
    MAX_RETRIES,
    TTS_CHUNK_MAX_CHARS,
    SPEAKERS,
)
from utils import call_with_retry_and_fallback


def generate_script(api_key: str, research_data: dict, version: str) -> dict:
    """調査結果をもとにポッドキャスト台本を生成し、TTS チャンクに分割して返す。"""

    speaker_names = [s["name"] for s in SPEAKERS]
    host_male = speaker_names[0]    # 田中
    host_female = speaker_names[1]  # 鈴木

    research_text = research_data.get("research", "")
    published_at = research_data.get("published_at", "")

    prompt = f"""あなたはプロの日本語ポッドキャスト台本作家です。
以下の調査結果をもとに、Claude Code バージョン {version} の変更内容を解説する
約5分間の日本語ポッドキャスト台本を作成してください。

## 調査結果
{research_text}

## 話者設定
- {host_male}（男性）: 技術に詳しいホスト役。技術的な内容を分かりやすく説明する。
- {host_female}（女性）: 聴衆代表のホスト役。素朴な疑問を投げかけ、内容を整理する。

## 台本の構成（合計 2500〜3500 文字程度）
1. **オープニング**（約 300 文字）: 番組紹介と今回のテーマ提示
2. **メインコンテンツ**（約 2200〜2500 文字）: 変更点・新機能を順に解説
3. **クロージング**（約 300 文字）: まとめと聴取者へのメッセージ

## 出力形式（厳守）
- 各発言を「話者名: 発言内容」の形式で 1 行ずつ記述
- 番組名は「Claude Code ポッドキャスト」
- 専門用語には自然な形で補足説明を入れる
- 台本テキストのみ出力（説明文・注釈・マークダウン見出し等は不要）
- バージョン番号を冒頭で明示する

## 出力例（形式のみ。内容は調査結果に基づくこと）
{host_male}: こんにちは、Claude Code ポッドキャストへようこそ。{host_male}です。
{host_female}: {host_female}です。今日もよろしくお願いします。
{host_male}: 今回は Claude Code バージョン X.X.X についてお話しします。
{host_female}: どんな変更があったんですか？
{host_male}: まず最初の大きな変更点は...
"""

    client = genai.Client(api_key=api_key)

    def call_primary():
        print(f"[ログ] 台本生成モデル: {RESEARCH_MODEL}")
        response = client.models.generate_content(
            model=RESEARCH_MODEL,
            contents=prompt,
        )
        return response.text

    def call_fallback():
        print(f"[ログ] フォールバック台本生成モデル: {RESEARCH_FALLBACK_MODEL}")
        response = client.models.generate_content(
            model=RESEARCH_FALLBACK_MODEL,
            contents=prompt,
        )
        return response.text

    script_text = call_with_retry_and_fallback(
        call_primary, call_fallback, MAX_RETRIES, RETRY_WAIT_SECONDS
    )

    # 台本を TTS チャンクに分割
    chunks = split_into_chunks(script_text, TTS_CHUNK_MAX_CHARS)
    print(f"[ログ] 台本を {len(chunks)} チャンクに分割しました（合計 {len(script_text)} 文字）")

    return {
        "title": f"Claude Code v{version} アップデート解説",
        "version": version,
        "published_at": published_at,
        "full_script": script_text,
        "chunks": chunks,
    }


def split_into_chunks(script_text: str, max_chars: int = TTS_CHUNK_MAX_CHARS) -> list:
    """台本を発言行の境界で max_chars 文字未満に分割する。"""
    lines = [line.strip() for line in script_text.strip().split("\n") if line.strip()]

    chunks = []
    current_lines = []
    current_length = 0

    for line in lines:
        # 改行 1 文字分も加算
        line_length = len(line) + 1

        if current_length + line_length >= max_chars and current_lines:
            chunks.append("\n".join(current_lines))
            current_lines = [line]
            current_length = line_length
        else:
            current_lines.append(line)
            current_length += line_length

    if current_lines:
        chunks.append("\n".join(current_lines))

    return chunks
