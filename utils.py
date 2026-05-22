import time


def call_with_retry_and_fallback(primary_func, fallback_func, max_retries=3, wait_seconds=60):
    """プライマリ関数を最大 max_retries 回試みた後、失敗したらフォールバック関数を試みる。
    429 / 503 の場合のみ wait_seconds 秒待ってリトライ。それ以外は即例外を再送出。
    """
    last_error = None

    # プライマリモデルを試みる
    for attempt in range(max_retries):
        try:
            return primary_func()
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "503" in error_str:
                last_error = e
                if attempt < max_retries - 1:
                    print(
                        f"[リトライ] プライマリモデルで {wait_seconds} 秒後に再試行します..."
                        f" ({attempt + 1}/{max_retries})"
                    )
                    time.sleep(wait_seconds)
            else:
                raise

    print(
        f"[警告] プライマリモデルのリトライ上限に達しました。"
        f"フォールバックモデルへ切り替えます。"
    )

    # フォールバックモデルを試みる
    for attempt in range(max_retries):
        try:
            return fallback_func()
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "503" in error_str:
                last_error = e
                if attempt < max_retries - 1:
                    print(
                        f"[リトライ] フォールバックモデルで {wait_seconds} 秒後に再試行します..."
                        f" ({attempt + 1}/{max_retries})"
                    )
                    time.sleep(wait_seconds)
                else:
                    raise
            else:
                raise

    raise RuntimeError(f"全てのリトライが失敗しました: {last_error}")
