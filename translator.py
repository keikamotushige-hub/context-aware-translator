"""Gemini-powered context-aware translation services."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import google.generativeai as genai
from PIL import Image
from supabase import Client

SYSTEM_INSTRUCTION = (
    "あなたはプロの翻訳家です。ターゲット層の属性を考慮し、"
    "直訳ではなく自然で相手に伝わりやすい言葉遣いに変換してください。"
    "原文の意味と重要な情報を保持し、翻訳結果だけを返してください。"
)
DEFAULT_MODEL = "gemini-flash-latest"
TEXT_MIME_TYPES = {
    "text/plain",
    "text/markdown",
    "text/csv",
    "application/json",
}


class TranslationError(RuntimeError):
    """Raised when Gemini cannot produce a translation."""


class StorageError(RuntimeError):
    """Raised when a translation cannot be persisted."""


def create_model(api_key: str, model_name: str = DEFAULT_MODEL) -> Any:
    if not api_key:
        raise ValueError("GEMINI_API_KEY が設定されていません。")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(
        model_name=model_name,
        system_instruction=SYSTEM_INSTRUCTION,
    )


def build_prompt(target_audience: str, target_language: str) -> str:
    if not target_audience.strip():
        raise ValueError("ターゲット層を入力してください。")
    if not target_language.strip():
        raise ValueError("翻訳先の言語を入力してください。")
    return (
        f"翻訳先の言語: {target_language}\n"
        f"ターゲット層: {target_audience}\n\n"
        "入力内容を読み取り、ターゲット層の知識レベル・関心・語調に合わせて"
        "自然で伝わりやすく翻訳してください。画像やPDFの場合は、その中の文字を"
        "読み取って翻訳してください。説明、注釈、前置きは不要です。"
    )


def translate_text(
    model: Any,
    text: str,
    target_audience: str,
    target_language: str,
) -> str:
    if not text.strip():
        raise ValueError("翻訳するテキストが空です。")
    return _generate(
        model,
        [build_prompt(target_audience, target_language), text],
    )


def translate_image(
    model: Any,
    image: Image.Image,
    target_audience: str,
    target_language: str,
) -> str:
    return _generate(
        model,
        [build_prompt(target_audience, target_language), image],
    )


def extract_text(model: Any, content: Any) -> str:
    """Extract source text from an image or document with Gemini."""
    return _generate(
        model,
        [
            "入力された画像または文書内の文字を、元の言語のまま正確に抽出してください。"
            "説明やMarkdownのコードフェンスは付けず、抽出した文字だけを返してください。",
            content,
        ],
    )


def translate_file(
    model: Any,
    data: bytes,
    mime_type: str,
    target_audience: str,
    target_language: str,
) -> str:
    if not data:
        raise ValueError("ファイルが空です。")

    prompt = build_prompt(target_audience, target_language)
    if mime_type in TEXT_MIME_TYPES:
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ValueError("テキストファイルはUTF-8形式で保存してください。") from exc
        return _generate(model, [prompt, text])

    part = {"mime_type": mime_type, "data": data}
    return _generate(model, [prompt, part])


def _generate(model: Any, contents: list[Any]) -> str:
    try:
        response = model.generate_content(contents)
        translated = (getattr(response, "text", None) or "").strip()
    except Exception as exc:
        raise TranslationError(f"Gemini APIで翻訳できませんでした: {exc}") from exc

    if not translated:
        raise TranslationError(
            "翻訳結果が空でした。入力内容またはGeminiの安全性設定を確認してください。"
        )
    return translated


def save_translation(
    client: Client,
    *,
    original_text: str,
    translated_text: str,
    target_audience: str,
    target_language: str,
    source_type: str,
    user_id: str | None,
) -> dict[str, Any]:
    record = {
        "original_text": original_text,
        "translated_text": translated_text,
        "target_audience": target_audience,
        "target_language": target_language,
        "source_type": source_type,
        "user_id": user_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        result = client.table("translations").insert(record).execute()
    except Exception as exc:
        raise StorageError(f"Supabaseへの保存に失敗しました: {exc}") from exc
    if not result.data:
        raise StorageError("Supabaseから保存結果が返されませんでした。")
    return result.data[0]
