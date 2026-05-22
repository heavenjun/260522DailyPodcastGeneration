import requests
from config import GITHUB_REPO

_HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


def get_latest_claude_code_release() -> dict | None:
    """GitHub Releases API から Claude Code の最新リリース情報を取得する。"""

    url_latest = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
    print(f"[ログ] GitHub Releases API を呼び出し中: {url_latest}")

    try:
        resp = requests.get(url_latest, headers=_HEADERS, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        print(f"[ログ] 最新リリース取得成功: {data.get('tag_name', '不明')}")
        return data
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            print("[警告] /releases/latest が 404。全リリース一覧から取得を試みます。")
        else:
            print(f"[警告] /releases/latest エラー: {e}")
    except requests.exceptions.RequestException as e:
        print(f"[警告] /releases/latest 接続エラー: {e}")

    # /releases/latest が失敗した場合は一覧の先頭を使う
    url_all = f"https://api.github.com/repos/{GITHUB_REPO}/releases"
    try:
        resp = requests.get(url_all, headers=_HEADERS, timeout=30, params={"per_page": 5})
        resp.raise_for_status()
        releases = resp.json()
        # pre-release を除いた最新を返す
        for release in releases:
            if not release.get("prerelease", False) and not release.get("draft", False):
                print(f"[ログ] リリース一覧から取得: {release.get('tag_name', '不明')}")
                return release
        if releases:
            print(f"[ログ] 安定版がなかったため先頭を使用: {releases[0].get('tag_name', '不明')}")
            return releases[0]
    except requests.exceptions.RequestException as e:
        print(f"[エラー] GitHub API 接続エラー: {e}")

    return None
