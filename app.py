"""Streamlit UI for the context-aware translator."""

from __future__ import annotations

import io
import os
from pathlib import Path
from typing import Any

import streamlit as st
from dotenv import load_dotenv
from PIL import Image

from legal import APP_NAME, BUSINESS_INFO, legal_markdown
from translator import (
    StorageError,
    TranslationError,
    create_model,
    extract_text,
    save_translation,
    translate_text,
)
from web_auth import (
    AuthenticationError,
    AuthenticatedUser,
    authenticate,
    ensure_test_user,
    register_owner,
)

load_dotenv(Path(__file__).with_name(".env"))

OWNER_EMAIL = os.getenv("OWNER_EMAIL", "keikamotushige@gmail.com")
TEST_EMAIL = os.getenv("TEST_EMAIL", "test@translator.local")
TEST_PASSWORD = os.getenv("TEST_PASSWORD", "TestPass123!")


def allowed_emails() -> set[str]:
    """Owner plus configured testers are the only accounts allowed to log in."""
    extra = os.getenv("TESTER_EMAILS", "")
    testers = {addr for addr in (e.strip() for e in extra.split(",")) if addr}
    return {OWNER_EMAIL, TEST_EMAIL, *testers}
SUPPORTED_FILES = ["txt", "md", "csv", "json", "pdf", "png", "jpg", "jpeg", "webp"]
TEXT_MIME_TYPES = {
    "text/plain",
    "text/markdown",
    "text/csv",
    "application/json",
}


def setting(name: str, default: str = "") -> str:
    """Read a secret from Streamlit secrets, then environment variables."""
    try:
        value = st.secrets.get(name)
        if value is not None:
            return str(value)
    except (FileNotFoundError, KeyError):
        pass
    return os.getenv(name, default)


def required_settings() -> dict[str, str]:
    values = {
        "gemini_api_key": setting("GEMINI_API_KEY"),
        "supabase_url": setting("SUPABASE_URL"),
        "supabase_key": setting("SUPABASE_KEY"),
    }
    missing = [name for name, value in values.items() if not value]
    if missing:
        raise RuntimeError(f"未設定の環境変数: {', '.join(missing)}")
    return values


def login_view(config: dict[str, str]) -> None:
    st.title("文脈特化型翻訳")
    st.caption("ログインして、文章・文書・写真を相手に伝わる表現へ翻訳します。")

    with st.form("login"):
        email = st.text_input("メールアドレス")
        password = st.text_input("パスワード", type="password")
        submitted = st.form_submit_button("ログイン", use_container_width=True)
    if submitted:
        try:
            st.session_state.user = authenticate(
                supabase_url=config["supabase_url"],
                supabase_key=config["supabase_key"],
                owner_email=OWNER_EMAIL,
                allowed_emails=allowed_emails(),
                email=email,
                password=password,
            )
            st.rerun()
        except (ValueError, AuthenticationError) as exc:
            st.error(str(exc))

    with st.expander("オーナーの初回登録"):
        st.warning("初回登録は一度だけ行います。最初に入力したパスワードが登録されます。")
        with st.form("owner_setup"):
            owner_password = st.text_input(
                "新しいオーナーパスワード（8文字以上）",
                type="password",
            )
            setup_code = st.text_input("初回セットアップコード", type="password")
            register = st.form_submit_button("オーナーを登録")
        if register:
            try:
                message = register_owner(
                    supabase_url=config["supabase_url"],
                    supabase_key=config["supabase_key"],
                    owner_email=OWNER_EMAIL,
                    password=owner_password,
                    setup_code=setup_code,
                    expected_setup_code=setting("OWNER_SETUP_CODE"),
                )
                st.success(message)
            except (ValueError, AuthenticationError) as exc:
                st.error(str(exc))

    with st.expander("テストアカウント"):
        st.code(f"ID: {TEST_EMAIL}\nPassword: {TEST_PASSWORD}")
        if setting("SUPABASE_SERVICE_ROLE_KEY") and st.button(
            "テストアカウントを準備",
            use_container_width=True,
        ):
            try:
                ensure_test_user(
                    supabase_url=config["supabase_url"],
                    service_role_key=setting("SUPABASE_SERVICE_ROLE_KEY"),
                    test_email=TEST_EMAIL,
                    test_password=TEST_PASSWORD,
                )
                st.success("テストアカウントを利用できます。")
            except (ValueError, AuthenticationError) as exc:
                st.error(str(exc))

    render_legal_footer()


def render_legal_footer() -> None:
    st.divider()
    with st.expander("運営者情報・特定商取引法に基づく表記"):
        st.markdown(legal_markdown())
    st.caption(
        f"運営: {BUSINESS_INFO['事業者名']}（代表: {BUSINESS_INFO['代表者']}）"
        f" ・ お問い合わせ: {BUSINESS_INFO['メールアドレス']}"
    )


def media_to_source_text(model: Any, uploaded: Any) -> tuple[str, str]:
    data = uploaded.getvalue()
    mime_type = uploaded.type or "application/octet-stream"
    if mime_type in TEXT_MIME_TYPES:
        try:
            return data.decode("utf-8-sig"), "file"
        except UnicodeDecodeError as exc:
            raise ValueError("テキストファイルはUTF-8形式で保存してください。") from exc
    if mime_type.startswith("image/"):
        image = Image.open(io.BytesIO(data)).convert("RGB")
        return extract_text(model, image), "image"
    if mime_type == "application/pdf":
        return extract_text(
            model,
            {"mime_type": mime_type, "data": data},
        ), "pdf"
    raise ValueError(f"未対応のファイル形式です: {mime_type}")


def translation_view(config: dict[str, str], user: AuthenticatedUser) -> None:
    st.title("文脈特化型翻訳")
    st.caption(f"{user.email}（{user.role}）でログイン中")

    with st.sidebar:
        st.header("翻訳設定")
        target_language = st.text_input("翻訳先の言語", value="日本語")
        target_audience = st.text_input(
            "ターゲット層",
            placeholder="例: 日本を初めて訪れる観光客",
        )
        if st.button("ログアウト", use_container_width=True):
            try:
                user.client.auth.sign_out()
            finally:
                st.session_state.pop("user", None)
                st.rerun()

    source_kind = st.radio(
        "入力方法",
        ["テキスト", "ファイル", "カメラ"],
        horizontal=True,
    )
    text = ""
    uploaded = None
    if source_kind == "テキスト":
        text = st.text_area("翻訳するテキスト", height=220)
    elif source_kind == "ファイル":
        uploaded = st.file_uploader(
            "文書または画像を選択",
            type=SUPPORTED_FILES,
        )
    else:
        uploaded = st.camera_input("文書や案内板を撮影")

    if not st.button("翻訳する", type="primary", use_container_width=True):
        return

    try:
        model = create_model(config["gemini_api_key"])
        if source_kind == "テキスト":
            source_text = text
            source_type = "text"
        else:
            if uploaded is None:
                raise ValueError("ファイルまたは写真を選択してください。")
            with st.spinner("文字を読み取っています…"):
                source_text, source_type = media_to_source_text(model, uploaded)

        with st.spinner("ターゲット層に合わせて翻訳しています…"):
            translated = translate_text(
                model,
                source_text,
                target_audience,
                target_language,
            )
        st.subheader("翻訳結果")
        st.text_area(
            "結果",
            value=translated,
            height=240,
            label_visibility="collapsed",
        )

        with st.expander("読み取った原文"):
            st.text(source_text)

        try:
            save_translation(
                user.client,
                original_text=source_text,
                translated_text=translated,
                target_audience=target_audience,
                target_language=target_language,
                source_type=source_type,
                user_id=user.id,
            )
            st.success("翻訳履歴を保存しました。")
        except StorageError as exc:
            st.warning(f"翻訳は完了しましたが、履歴を保存できませんでした: {exc}")
    except (ValueError, TranslationError) as exc:
        st.error(str(exc))
    except Exception as exc:
        st.error(f"処理中にエラーが発生しました: {exc}")

    render_legal_footer()


def main() -> None:
    st.set_page_config(
        page_title="文脈特化型翻訳",
        page_icon="🌐",
        layout="centered",
    )
    try:
        config = required_settings()
    except RuntimeError as exc:
        st.error(str(exc))
        st.stop()

    user = st.session_state.get("user")
    if user is None:
        login_view(config)
    else:
        translation_view(config, user)


if __name__ == "__main__":
    main()
