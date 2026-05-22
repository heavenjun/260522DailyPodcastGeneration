import os
import wave
import base64

from google import genai
from google.genai import types

from config import (
    TTS_MODEL,
    TTS_FALLBACK_MODEL,
    RETRY_WAIT_SECONDS,
    MAX_RETRIES,
    TTS_SAMPLE_RATE,
    TTS_CHANNELS,
    TTS_SAMPLE_WIDTH,
    SPEAKERS,
    OUTPUT_DIR,
)
from utils import call_with_retry_and_fallback


def _build_speaker_voice_configs() -> list:
    """SPEAKERS 設定から SpeakerVoiceConfig リストを生成する。"""
    configs = []
    for speaker in SPEAKERS:
        configs.append(
            types.SpeakerVoiceConfig(
                speaker=speaker["name"],
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=speaker["voice"]
                    )
                ),
            )
        )
    return configs


def _parse_sample_rate(mime_type: str) -> int:
    """mime_type 文字列からサンプルレートを抽出する。取得できない場合はデフォルト値を返す。"""
    if mime_type and "rate=" in mime_type:
        try:
            return int(mime_type.split("rate=")[1].split(";")[0].strip())
        except (ValueError, IndexError):
            pass
    return TTS_SAMPLE_RATE


def _generate_chunk_audio(client: genai.Client, chunk_text: str, model: str) -> tuple[bytes, int]:
    """1 チャンクの台本テキストから PCM 音声データを取得する。(audio_bytes, sample_rate) を返す。"""
    speaker_voice_configs = _build_speaker_voice_configs()

    response = client.models.generate_content(
        model=model,
        contents=chunk_text,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                multi_speaker_voice_config=types.MultiSpeakerVoiceConfig(
                    speaker_voice_configs=speaker_voice_configs
                )
            ),
        ),
    )

    part = response.candidates[0].content.parts[0]
    inline = part.inline_data

    # データは bytes または base64 文字列の場合がある
    raw = inline.data
    if isinstance(raw, str):
        raw = base64.b64decode(raw)

    sample_rate = _parse_sample_rate(inline.mime_type or "")
    return raw, sample_rate


def _save_pcm_as_wav(pcm_data: bytes, output_path: str, sample_rate: int) -> None:
    """PCM バイト列を WAV ファイルとして保存する。"""
    with wave.open(output_path, "wb") as wf:
        wf.setnchannels(TTS_CHANNELS)
        wf.setsampwidth(TTS_SAMPLE_WIDTH)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_data)


def generate_audio(api_key: str, script_data: dict) -> list:
    """台本の各チャンクから音声を生成し WAV ファイルとして保存する。WAV ファイルパスのリストを返す。"""
    chunks = script_data.get("chunks", [])
    if not chunks:
        raise ValueError("台本にチャンクが存在しません")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    client = genai.Client(api_key=api_key)
    wav_files = []

    for i, chunk_text in enumerate(chunks):
        print(f"[ログ] 音声チャンク {i + 1}/{len(chunks)} を生成中...")
        wav_path = os.path.join(OUTPUT_DIR, f"chunk_{i:03d}.wav")

        def make_primary(text=chunk_text):
            return lambda: _generate_chunk_audio(client, text, TTS_MODEL)

        def make_fallback(text=chunk_text):
            return lambda: _generate_chunk_audio(client, text, TTS_FALLBACK_MODEL)

        pcm_data, sample_rate = call_with_retry_and_fallback(
            make_primary(), make_fallback(), MAX_RETRIES, RETRY_WAIT_SECONDS
        )

        _save_pcm_as_wav(pcm_data, wav_path, sample_rate)
        wav_files.append(wav_path)
        print(f"[ログ] 音声チャンク {i + 1} を保存: {wav_path}")

    return wav_files


def combine_and_convert_to_mp3(wav_files: list, output_mp3: str) -> None:
    """複数の WAV ファイルを結合して MP3 に変換する。"""
    if not wav_files:
        raise ValueError("WAV ファイルが 1 つもありません")

    from pydub import AudioSegment

    print(f"[ログ] {len(wav_files)} 個の WAV ファイルを結合中...")
    combined = AudioSegment.empty()
    for wav_path in wav_files:
        segment = AudioSegment.from_wav(wav_path)
        combined += segment

    duration_sec = len(combined) / 1000.0
    print(f"[ログ] 結合完了: 合計 {duration_sec:.1f} 秒")

    print(f"[ログ] MP3 に変換中: {output_mp3}")
    combined.export(output_mp3, format="mp3", bitrate="128k")
    print(f"[ログ] MP3 保存完了: {output_mp3}")
