"""
簡易ログイン認証。
- オーナー: 初回に入力したパスワードを登録し、以降はそれで認証する。
- テスト用アカウント: 固定の ID / パスワードでログインできる。
"""

from __future__ import annotations

import getpass
import hashlib
import json
import os
import secrets
from pathlib import Path

# オーナー（所有者）アカウント
OWNER_EMAIL = "keikamotushige@gmail.com"

# テスト用アカウント（開発・動作確認用）
TEST_USER_ID = "test@translator.local"
TEST_PASSWORD = "TestPass123!"

CREDENTIALS_PATH = Path(__file__).resolve().parent / ".credentials.json"
_PBKDF2_ITERATIONS = 200_000


def _hash_password(password: str, salt: bytes | None = None) -> tuple[str, str]:
    """Return (salt_hex, hash_hex)."""
    if salt is None:
        salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        _PBKDF2_ITERATIONS,
    )
    return salt.hex(), digest.hex()


def _verify_password(password: str, salt_hex: str, hash_hex: str) -> bool:
    salt = bytes.fromhex(salt_hex)
    _, candidate = _hash_password(password, salt)
    return secrets.compare_digest(candidate, hash_hex)


def _load_store() -> dict:
    if not CREDENTIALS_PATH.exists():
        return {"users": {}}
    try:
        with CREDENTIALS_PATH.open(encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"認証情報ファイルの読み込みに失敗しました: {exc}") from exc
    if "users" not in data or not isinstance(data["users"], dict):
        data["users"] = {}
    return data


def _save_store(data: dict) -> None:
    try:
        with CREDENTIALS_PATH.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        # Restrict permissions where the OS supports it (no-op on Windows for chmod bits).
        try:
            os.chmod(CREDENTIALS_PATH, 0o600)
        except OSError:
            pass
    except OSError as exc:
        raise RuntimeError(f"認証情報ファイルの保存に失敗しました: {exc}") from exc


def ensure_test_account() -> None:
    """Ensure the fixed test account exists in the credentials store."""
    store = _load_store()
    users = store["users"]
    if TEST_USER_ID not in users:
        salt_hex, hash_hex = _hash_password(TEST_PASSWORD)
        users[TEST_USER_ID] = {
            "salt": salt_hex,
            "hash": hash_hex,
            "role": "test",
        }
        _save_store(store)


def register_owner_password(password: str) -> None:
    """Register the owner's first-entered password."""
    if not password:
        raise ValueError("パスワードが空です。")
    store = _load_store()
    salt_hex, hash_hex = _hash_password(password)
    store["users"][OWNER_EMAIL] = {
        "salt": salt_hex,
        "hash": hash_hex,
        "role": "owner",
    }
    _save_store(store)


def owner_password_is_set() -> bool:
    store = _load_store()
    return OWNER_EMAIL in store["users"]


def authenticate(user_id: str, password: str) -> str:
    """
    Authenticate a user.

    For the owner, if no password is registered yet, the first typed password
    becomes the registered password.

    Returns:
        Role string: "owner" or "test".

    Raises:
        ValueError: Invalid credentials or empty input.
        PermissionError: Unknown user.
    """
    user_id = user_id.strip()
    if not user_id:
        raise ValueError("ユーザー ID が空です。")
    if not password:
        raise ValueError("パスワードが空です。")

    ensure_test_account()
    store = _load_store()
    users = store["users"]

    # Owner: first password typed becomes the password.
    if user_id.lower() == OWNER_EMAIL.lower():
        if OWNER_EMAIL not in users:
            register_owner_password(password)
            return "owner"
        record = users[OWNER_EMAIL]
        if not _verify_password(password, record["salt"], record["hash"]):
            raise ValueError("パスワードが正しくありません。")
        return "owner"

    if user_id.lower() == TEST_USER_ID.lower():
        record = users[TEST_USER_ID]
        if not _verify_password(password, record["salt"], record["hash"]):
            raise ValueError("パスワードが正しくありません。")
        return "test"

    raise PermissionError(
        f"未登録のユーザーです。利用可能な ID: {OWNER_EMAIL} / {TEST_USER_ID}"
    )


def login_prompt() -> tuple[str, str]:
    """
    Interactive login. Returns (user_id, role).

    Raises:
        ValueError, PermissionError on auth failure.
    """
    ensure_test_account()
    print("--- ログイン ---")
    print(f"オーナー: {OWNER_EMAIL}（初回入力のパスワードが登録されます）")
    print(f"テスト:  {TEST_USER_ID} / {TEST_PASSWORD}")

    user_id = input("ユーザー ID (メール): ").strip()
    password = getpass.getpass("パスワード: ")

    if user_id.lower() == OWNER_EMAIL.lower() and not owner_password_is_set():
        print("オーナー初回ログイン: 入力したパスワードを登録します。")

    role = authenticate(user_id, password)
    print(f"ログイン成功（{role}）: {user_id}")
    return user_id, role
