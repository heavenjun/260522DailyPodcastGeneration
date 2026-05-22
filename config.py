# 話者と声の設定（固定値）
SPEAKERS = [
    {
        "name": "田中",
        "gender": "male",
        "voice": "Charon",
    },
    {
        "name": "鈴木",
        "gender": "female",
        "voice": "Aoede",
    },
]

# Google Drive アップロード先フォルダ
DRIVE_FOLDER_NAME = "Podcasts"

# 調査モデル
RESEARCH_MODEL = "gemini-2.5-flash-lite"
RESEARCH_FALLBACK_MODEL = "gemini-2.5-flash"

# 音声モデル
TTS_MODEL = "gemini-2.5-flash-preview-tts"
TTS_FALLBACK_MODEL = "gemini-3.1-flash-tts-preview"

# TTS 台本チャンクの最大文字数（この値未満に分割）
TTS_CHUNK_MAX_CHARS = 1800

# リトライ設定
RETRY_WAIT_SECONDS = 60
MAX_RETRIES = 3

# GitHub リリース取得先
GITHUB_REPO = "anthropics/claude-code"

# 調査済みバージョンの記録ファイル
INVESTIGATED_VERSIONS_FILE = "investigated_versions.json"

# 中間成果物のファイル名
OUTPUT_DIR = "output"
RESEARCH_OUTPUT = "output/research.json"
SCRIPT_OUTPUT = "output/script.json"
PODCAST_OUTPUT = "output/podcast.mp3"

# TTS 音声フォーマット（Gemini TTS は 24kHz / 16bit / mono の PCM を返す）
TTS_SAMPLE_RATE = 24000
TTS_CHANNELS = 1
TTS_SAMPLE_WIDTH = 2  # 16-bit = 2 bytes

# OAuth スコープ（固定）
OAUTH_SCOPES = ["https://www.googleapis.com/auth/drive.file"]
