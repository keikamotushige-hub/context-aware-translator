"""Supabase authentication helpers for the Streamlit application."""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from typing import Any

from supabase import Client, create_client


class AuthenticationError(RuntimeError):
    """Raised when sign-in or first-time setup fails."""


@dataclass(frozen=True)
class AuthenticatedUser:
    id: str
    email: str
    role: str
    client: Client


def authenticate(
    *,
    supabase_url: str,
    supabase_key: str,
    owner_email: str,
    allowed_emails: set[str],
    email: str,
    password: str,
) -> AuthenticatedUser:
    if not email.strip() or not password:
        raise ValueError("メールアドレスとパスワードを入力してください。")

    normalized = email.strip().casefold()
    allowlist = {addr.strip().casefold() for addr in allowed_emails if addr.strip()}
    if normalized not in allowlist:
        raise AuthenticationError(
            "このアカウントはログインを許可されていません。"
            "オーナーまたはテスターのアカウントでログインしてください。"
        )

    client = create_client(supabase_url, supabase_key)
    try:
        response = client.auth.sign_in_with_password(
            {"email": email.strip(), "password": password}
        )
    except Exception as exc:
        raise AuthenticationError("メールアドレスまたはパスワードが正しくありません。") from exc

    if not response.user:
        raise AuthenticationError("ログイン情報を取得できませんでした。")
    actual_email = response.user.email or email.strip()

    # Enforce the allowlist against the email Supabase actually authenticated.
    if actual_email.strip().casefold() not in allowlist:
        try:
            client.auth.sign_out()
        except Exception:
            pass
        raise AuthenticationError(
            "このアカウントはログインを許可されていません。"
        )

    role = (
        "owner"
        if actual_email.casefold() == owner_email.strip().casefold()
        else "test"
    )
    return AuthenticatedUser(
        id=str(response.user.id),
        email=actual_email,
        role=role,
        client=client,
    )


def register_owner(
    *,
    supabase_url: str,
    supabase_key: str,
    owner_email: str,
    password: str,
    setup_code: str,
    expected_setup_code: str,
) -> str:
    """Register the fixed owner email using the first entered password."""
    if len(password) < 8:
        raise ValueError("パスワードは8文字以上にしてください。")
    if not expected_setup_code:
        raise AuthenticationError("OWNER_SETUP_CODE が設定されていません。")
    if not secrets.compare_digest(setup_code, expected_setup_code):
        raise AuthenticationError("初回セットアップコードが正しくありません。")

    client = create_client(supabase_url, supabase_key)
    try:
        response = client.auth.sign_up(
            {"email": owner_email.strip(), "password": password}
        )
    except Exception as exc:
        raise AuthenticationError(
            "オーナー登録に失敗しました。すでに登録済みの場合は通常ログインしてください。"
        ) from exc

    if not response.user:
        raise AuthenticationError("オーナーアカウントを作成できませんでした。")
    if response.session is None:
        return "登録確認メールを送信しました。確認後、通常ログインしてください。"
    return "オーナー登録が完了しました。通常ログインしてください。"


def ensure_test_user(
    *,
    supabase_url: str,
    service_role_key: str,
    test_email: str,
    test_password: str,
) -> None:
    """Create the configured test user if it does not already exist."""
    if not service_role_key:
        raise ValueError("SUPABASE_SERVICE_ROLE_KEY が設定されていません。")
    admin_client = create_client(supabase_url, service_role_key)
    try:
        users: Any = admin_client.auth.admin.list_users()
        existing = getattr(users, "users", users)
        if any(
            (getattr(user, "email", "") or "").casefold() == test_email.casefold()
            for user in existing
        ):
            return
        admin_client.auth.admin.create_user(
            {
                "email": test_email,
                "password": test_password,
                "email_confirm": True,
            }
        )
    except Exception as exc:
        raise AuthenticationError(f"テストユーザーの作成に失敗しました: {exc}") from exc
