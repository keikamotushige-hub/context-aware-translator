"""
文脈特化型翻訳ツール
ターゲット層を考慮した自然な翻訳を Gemini API で生成し、Supabase に保存する。
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

import google.generativeai as genai
from dotenv import load_dotenv
from supabase import Client, create_client

from auth import login_prompt

SYSTEM_INSTRUCTION = (
    "あなたはプロの翻訳家です。"
    "ターゲット層の属性を考慮し、直訳ではなく自然で相手に伝わりやすい言葉遣いに変換してください。"
)

DEFAULT_MODEL = "gemini-2.0-flash"


def load_config() -> dict[str, str]:
    """Load required credentials from .env."""
    load_dotenv()

    required_keys = ("GEMINI_API_KEY", "SUPABASE_URL", "SUPABASE_KEY")
    missing = [key for key in required_keys if not os.getenv(key)]
    if missing:
        raise EnvironmentError(
            f".env に次の環境変数が設定されていません: {', '.join(missing)}"
        )

    return {
        "gemini_api_key": os.environ["GEMINI_API_KEY"],
        "supabase_url": os.environ["SUPABASE_URL"],
        "supabase_key": os.environ["SUPABASE_KEY"],
    }


def get_supabase_client(url: str, key: str) -> Client:
    """Create a Supabase client."""
    try:
        return create_client(url, key)
    except Exception as exc:
        raise ConnectionError(f"Supabase クライアントの初期化に失敗しました: {exc}") from exc


def translate_text(
    text: str,
    target_audience: str,
    api_key: str,
    model_name: str = DEFAULT_MODEL,
) -> str:
    """
    Translate text with Gemini, tailored to the target audience.

    Raises:
        ValueError: If inputs are empty.
        RuntimeError: If the Gemini API call fails or returns an empty result.
    """
    if not text.strip():
        raise ValueError("翻訳するテキストが空です。")
    if not target_audience.strip():
        raise ValueError("ターゲット層が空です。")

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=SYSTEM_INSTRUCTION,
        )
        prompt = (
            f"ターゲット層: {target_audience}\n\n"
            "以下のテキストを翻訳してください。"
            "ターゲット層の知識レベル・関心・言葉遣いに合わせ、直訳ではなく自然で伝わりやすい表現にしてください。"
            "説明や前置きは不要です。翻訳結果のみを出力してください。\n\n"
            f"{text}"
        )
        response = model.generate_content(prompt)
    except Exception as exc:
        raise RuntimeError(f"Gemini API エラー: {exc}") from exc

    translated = (getattr(response, "text", None) or "").strip()
    if not translated:
        raise RuntimeError("Gemini API から翻訳結果を取得できませんでした。")

    return translated


def save_translation(
    client: Client,
    original_text: str,
    translated_text: str,
    target_audience: str,
    timestamp: datetime | None = None,
) -> dict:
    """
    Save a translation record to the Supabase `translations` table.

    Columns: original_text, translated_text, target_audience, created_at
    """
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)

    record = {
        "original_text": original_text,
        "translated_text": translated_text,
        "target_audience": target_audience,
        "created_at": timestamp.isoformat(),
    }

    try:
        result = client.table("translations").insert(record).execute()
    except Exception as exc:
        raise ConnectionError(f"Supabase への保存に失敗しました: {exc}") from exc

    if not result.data:
        raise ConnectionError("Supabase への保存結果が空でした。テーブル定義と権限を確認してください。")

    return result.data[0]


def run_translation(text: str, target_audience: str) -> str:
    """Translate, print, and persist the result. Returns the translated text."""
    config = load_config()
    translated = translate_text(text, target_audience, config["gemini_api_key"])
    print(translated)

    client = get_supabase_client(config["supabase_url"], config["supabase_key"])
    saved = save_translation(client, text, translated, target_audience)
    print(
        f"[保存完了] id={saved.get('id')} created_at={saved.get('created_at')}",
        file=sys.stderr,
    )
    return translated


def main() -> int:
    print("=== 文脈特化型翻訳ツール ===")
    try:
        login_prompt()
        text = input("翻訳したいテキスト: ").strip()
        target_audience = input("ターゲット層（例: 観光客、技術者）: ").strip()
        run_translation(text, target_audience)
        return 0
    except EnvironmentError as exc:
        print(f"[設定エラー] {exc}", file=sys.stderr)
        return 1
    except PermissionError as exc:
        print(f"[認証エラー] {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"[入力エラー] {exc}", file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print(f"[APIエラー] {exc}", file=sys.stderr)
        return 1
    except ConnectionError as exc:
        print(f"[DBエラー] {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n中断されました。", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"[予期しないエラー] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
