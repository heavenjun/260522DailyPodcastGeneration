import os

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from config import DRIVE_FOLDER_NAME, OAUTH_SCOPES


def _build_credentials(client_id: str, client_secret: str, refresh_token: str) -> Credentials:
    """リフレッシュトークンから Credentials オブジェクトを生成し、必要なら更新する。"""
    credentials = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=OAUTH_SCOPES,
    )
    if not credentials.valid:
        credentials.refresh(Request())
    return credentials


def _find_or_create_folder(service, folder_name: str, parent_id: str | None = None) -> str:
    """指定名のフォルダを検索し、なければ作成して ID を返す。"""
    query = (
        f"name='{folder_name}'"
        " and mimeType='application/vnd.google-apps.folder'"
        " and trashed=false"
    )
    if parent_id:
        query += f" and '{parent_id}' in parents"

    results = service.files().list(q=query, fields="files(id, name)").execute()
    files = results.get("files", [])
    if files:
        return files[0]["id"]

    # フォルダが存在しないので作成
    metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder",
    }
    if parent_id:
        metadata["parents"] = [parent_id]

    folder = service.files().create(body=metadata, fields="id").execute()
    print(f"[ログ] Google Drive フォルダを作成しました: {folder_name} (id={folder['id']})")
    return folder["id"]


def upload_to_drive(
    client_id: str,
    client_secret: str,
    refresh_token: str,
    file_path: str,
    version_folder_name: str,
) -> str:
    """ポッドキャスト MP3 を Google Drive の Podcasts/<version_folder_name>/ にアップロードする。
    アップロードしたファイルの ID を返す。
    """
    print("[ログ] Google Drive 認証中...")
    credentials = _build_credentials(client_id, client_secret, refresh_token)
    service = build("drive", "v3", credentials=credentials)

    # Podcasts フォルダを検索または作成
    podcasts_folder_id = _find_or_create_folder(service, DRIVE_FOLDER_NAME)
    print(f"[ログ] Podcasts フォルダ ID: {podcasts_folder_id}")

    # バージョン+日付フォルダを作成
    version_folder_id = _find_or_create_folder(service, version_folder_name, podcasts_folder_id)
    print(f"[ログ] バージョンフォルダ ID: {version_folder_id} ({version_folder_name})")

    # ファイルをアップロード
    file_name = os.path.basename(file_path)
    media = MediaFileUpload(file_path, mimetype="audio/mpeg", resumable=True)
    metadata = {
        "name": file_name,
        "parents": [version_folder_id],
    }

    print(f"[ログ] アップロード中: {file_path} → Drive/{DRIVE_FOLDER_NAME}/{version_folder_name}/{file_name}")
    uploaded = service.files().create(
        body=metadata,
        media_body=media,
        fields="id, webViewLink",
    ).execute()

    file_id = uploaded.get("id", "")
    web_link = uploaded.get("webViewLink", "")
    print(f"[ログ] アップロード完了: id={file_id}")
    if web_link:
        print(f"[ログ] Drive リンク: {web_link}")

    return file_id
