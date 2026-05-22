"""メインエントリポイント。GitHub Actions から実行される。"""

import json
import os
import sys
from datetime import datetime, timezone, timedelta

from config import (
    INVESTIGATED_VERSIONS_FILE,
    RESEARCH_OUTPUT,
    SCRIPT_OUTPUT,
    PODCAST_OUTPUT,
    OUTPUT_DIR,
    DRIVE_FOLDER_NAME,
)
from github_releases import get_latest_claude_code_release
from research import research_version
from script_generator import generate_script
from tts import generate_audio, combine_and_convert_to_mp3
from drive_uploader import upload_to_drive


JST = timezone(timedelta(hours=9))


def _load_investigated_versions() -> dict:
    if os.path.exists(INVESTIGATED_VERSIONS_FILE):
        with open(INVESTIGATED_VERSIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"versions": []}


def _save_investigated_versions(data: dict) -> None:
    with open(INVESTIGATED_VERSIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _save_json(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[ログ] 保存: {path}")


def main() -> None:
    # 実行日時（JST）
    now_jst = datetime.now(JST)
    today = now_jst.strftime("%Y-%m-%d")

    # ワークフロー手動実行時の日付オーバーライド
    date_override = os.environ.get("DATE_OVERRIDE", "").strip()
    if date_override:
        today = date_override
        print(f"[ログ] 日付オーバーライド: {today}")

    print(f"[ログ] ==============================")
    print(f"[ログ] Claude Code ポッドキャスト生成開始")
    print(f"[ログ] 実行日: {today}")
    print(f"[ログ] ==============================")

    # 環境変数確認
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        print("[エラー] 環境変数 GEMINI_API_KEY が未設定です")
        sys.exit(1)

    client_id = os.environ.get("GOOGLE_CLIENT_ID", "")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "")
    refresh_token = os.environ.get("GOOGLE_REFRESH_TOKEN", "")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # ─── Step 1: 最新リリース確認 ─────────────────────────────────────────
    print("\n[ステップ 1] GitHub Releases から最新バージョンを確認中...")
    release = get_latest_claude_code_release()
    if not release:
        print("[エラー] リリース情報の取得に失敗しました")
        sys.exit(1)

    tag_name = release.get("tag_name", "")
    version = tag_name.lstrip("v")
    print(f"[ログ] 最新バージョン: {version} (tag: {tag_name})")

    # ─── Step 2: 調査済み確認 ─────────────────────────────────────────────
    investigated = _load_investigated_versions()
    if version in investigated.get("versions", []):
        print(f"[スキップ] バージョン {version} は既に調査済みです。処理を終了します。")
        sys.exit(0)

    print(f"[ログ] バージョン {version} は未調査です。処理を開始します。")

    # ─── Step 3: 調査 ─────────────────────────────────────────────────────
    print(f"\n[ステップ 2] Claude Code v{version} の調査中...")
    research_data = None
    try:
        research_data = research_version(api_key, version, release)
        _save_json(RESEARCH_OUTPUT, research_data)
    except Exception as e:
        print(f"[エラー] 調査に失敗しました: {e}")
        _save_json(RESEARCH_OUTPUT, {"error": str(e), "version": version})
        sys.exit(1)

    # ─── Step 4: 台本生成 ─────────────────────────────────────────────────
    print(f"\n[ステップ 3] ポッドキャスト台本を生成中...")
    script_data = None
    try:
        script_data = generate_script(api_key, research_data, version)
        _save_json(SCRIPT_OUTPUT, script_data)
    except Exception as e:
        print(f"[エラー] 台本生成に失敗しました: {e}")
        _save_json(SCRIPT_OUTPUT, {"error": str(e), "version": version})
        sys.exit(1)

    # ─── Step 5: 音声生成 ─────────────────────────────────────────────────
    print(f"\n[ステップ 4] 音声を生成中 ({len(script_data['chunks'])} チャンク)...")
    wav_files = []
    try:
        wav_files = generate_audio(api_key, script_data)
    except Exception as e:
        print(f"[エラー] 音声生成に失敗しました: {e}")
        sys.exit(1)

    if not wav_files:
        print("[エラー] 音声ファイルが 1 つも生成されませんでした")
        sys.exit(1)

    # ─── Step 6: MP3 変換 ─────────────────────────────────────────────────
    print(f"\n[ステップ 5] WAV を MP3 に変換中...")
    try:
        combine_and_convert_to_mp3(wav_files, PODCAST_OUTPUT)
    except Exception as e:
        print(f"[エラー] MP3 変換に失敗しました: {e}")
        sys.exit(1)

    # ─── Step 7: Google Drive アップロード ────────────────────────────────
    if client_id and client_secret and refresh_token:
        print(f"\n[ステップ 6] Google Drive にアップロード中...")
        folder_name = f"v{version}_{today}"
        try:
            upload_to_drive(client_id, client_secret, refresh_token, PODCAST_OUTPUT, folder_name)
            print(f"[ログ] Drive/{DRIVE_FOLDER_NAME}/{folder_name}/podcast.mp3 にアップロード完了")
        except Exception as e:
            print(f"[エラー] Google Drive アップロードに失敗しました: {e}")
            # アップロード失敗は致命的ではないので処理継続
    else:
        print("[警告] Google Drive の認証情報が未設定のため、アップロードをスキップします")

    # ─── Step 8: 調査済みバージョンを記録 ────────────────────────────────
    investigated["versions"].append(version)
    _save_investigated_versions(investigated)
    print(f"\n[ログ] バージョン {version} を調査済みとして記録しました")

    print(f"\n[ログ] ==============================")
    print(f"[ログ] 全ての処理が完了しました！")
    print(f"[ログ] ポッドキャスト: {PODCAST_OUTPUT}")
    print(f"[ログ] ==============================")


if __name__ == "__main__":
    main()
