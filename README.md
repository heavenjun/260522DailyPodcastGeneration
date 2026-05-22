# Claude Code ポッドキャスト自動生成

Claude Code の最新バージョンリリースを毎日自動調査し、日本語の男女二人が対話する約 5 分間のポッドキャスト MP3 を生成して Google Drive にアップロードします。

## システム概要

```
GitHub Releases API
      ↓（最新バージョン確認）
Gemini 2.5 Flash Lite + Google Search Grounding
      ↓（変更内容を調査）
Gemini 2.5 Flash Lite
      ↓（ポッドキャスト台本を生成）
Gemini 2.5 Flash Preview TTS（多話者 TTS）
      ↓（PCM → WAV → MP3）
Google Drive（Podcasts/<バージョン>_<日付>/podcast.mp3）
```

**話者設定**

| 話者 | 性別 | 声 | 役割 |
|------|------|----|------|
| 田中 | 男性 | Charon | 技術解説役 |
| 鈴木 | 女性 | Aoede | リスナー代表役 |

---

## セットアップ手順

### 1. Google Cloud Console の設定

#### 1-1. プロジェクト作成と API 有効化

1. [Google Cloud Console](https://console.cloud.google.com/) を開く
2. 新しいプロジェクトを作成（例: `claude-podcast`）
3. 以下の API を有効化:
   - **Google Drive API**（検索して「有効にする」）

#### 1-2. OAuth 同意画面の設定

1. 左メニュー → 「API とサービス」→「OAuth 同意画面」
2. ユーザーの種類: **外部**を選択 → 「作成」
3. アプリ名・メールアドレスを入力 → 「保存して次へ」
4. スコープは追加不要 → 「保存して次へ」
5. テストユーザーに **自分の Gmail アドレス**を追加
6. **公開ステータスを「本番環境」に変更**（テスト環境のままだと 7 日でリフレッシュトークンが失効するため必須）

#### 1-3. OAuth クライアント ID の作成

1. 「API とサービス」→「認証情報」→「認証情報を作成」→「OAuth クライアント ID」
2. アプリケーションの種類: **ウェブアプリケーション**
3. 承認済みのリダイレクト URI に以下を追加:
   ```
   https://developers.google.com/oauthplayground
   ```
4. 「作成」→ **クライアント ID** と **クライアント シークレット**をメモ

### 2. Gemini API キーの取得

1. [Google AI Studio](https://aistudio.google.com/apikey) を開く
2. 「API キーを作成」→ キーをコピー（クレジットカード不要）

### 3. OAuth Playground でリフレッシュトークンを取得

1. [OAuth 2.0 Playground](https://developers.google.com/oauthplayground) を開く
2. 右上の歯車アイコン → 「Use your own OAuth credentials」にチェック
3. OAuth Client ID と OAuth Client Secret に手順 1-3 でメモした値を入力
4. 左ペインのスコープ入力欄に以下を入力して「Authorize APIs」:
   ```
   https://www.googleapis.com/auth/drive.file
   ```
5. Google アカウントでログインして権限を許可
6. 「Exchange authorization code for tokens」をクリック
7. 表示された **Refresh token** をコピー

### 4. GitHub Secrets の設定

リポジトリの「Settings」→「Secrets and variables」→「Actions」→「New repository secret」で以下の順に登録:

| 順序 | Secret 名 | 値 | 説明 |
|------|-----------|-----|------|
| 1 | `GEMINI_API_KEY` | Google AI Studio で取得したキー | 調査・台本生成・TTS に使用 |
| 2 | `GOOGLE_CLIENT_ID` | OAuth クライアント ID | Drive API 認証 |
| 3 | `GOOGLE_CLIENT_SECRET` | OAuth クライアント シークレット | Drive API 認証 |
| 4 | `GOOGLE_REFRESH_TOKEN` | OAuth Playground で取得したトークン | Drive API 認証（長期有効） |

---

## GitHub Actions の実行方法

### 定期実行（毎日 JST 6:00）

セットアップ完了後、毎日自動で実行されます。新しい Claude Code バージョンがリリースされていれば処理を実行し、既に調査済みの場合はスキップします。

### 手動実行

1. リポジトリの「Actions」タブを開く
2. 「Daily Podcast Generation」ワークフローを選択
3. 「Run workflow」→「Run workflow」

手動実行時は「date_override」に任意の日付文字列（例: `2026-05-22`）を入力できます（フォルダ名に使用）。

---

## ファイル構成

```
├── .github/
│   └── workflows/
│       └── podcast.yml       # GitHub Actions ワークフロー
├── output/
│   ├── research.json         # 調査結果（git 管理対象）
│   ├── script.json           # 台本（git 管理対象）
│   ├── chunk_*.wav           # 音声チャンク（git 管理外）
│   └── podcast.mp3           # 最終 MP3（git 管理外）
├── config.py                 # 話者・モデル・設定の集約
├── github_releases.py        # GitHub Releases API 連携
├── research.py               # Gemini + Google Search 調査
├── script_generator.py       # ポッドキャスト台本生成
├── tts.py                    # Gemini TTS 音声生成
├── drive_uploader.py         # Google Drive アップロード
├── main.py                   # メインエントリポイント
├── utils.py                  # リトライユーティリティ
├── requirements.txt          # Python ライブラリ一覧
└── investigated_versions.json # 調査済みバージョン記録
```

## 使用技術・モデル

| 用途 | プライマリ | フォールバック |
|------|-----------|--------------|
| 調査・台本生成 | gemini-2.5-flash-lite | gemini-2.5-flash |
| 音声合成（TTS） | gemini-2.5-flash-preview-tts | gemini-3.1-flash-tts-preview |

- API レート制限（429/503）時は 60 秒待機後にリトライ（最大 3 回）
- プライマリモデルが全リトライ失敗後、フォールバックモデルに切り替え
- フォールバックモデルも同様にリトライ

## Google Drive の構成

```
マイドライブ/
└── Podcasts/
    ├── v1.0.0_2026-05-22/
    │   └── podcast.mp3
    └── v1.1.0_2026-05-30/
        └── podcast.mp3
```
