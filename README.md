# 文脈特化型翻訳アプリ

Gemini APIで、ターゲット層に合わせた自然な翻訳を生成するStreamlitアプリです。
テキスト、UTF-8文書、PDF、画像、カメラ撮影に対応し、翻訳履歴をSupabaseへ保存します。

## 機能

- ターゲット層と翻訳先言語を指定
- テキスト、TXT、Markdown、CSV、JSON、PDF、画像の翻訳
- スマートフォンやPCのカメラで撮影した文字の読み取り・翻訳
- Supabase Authによるログイン
- オーナーは初回に入力したパスワードを登録
- 行レベルセキュリティ（RLS）付き翻訳履歴

## ローカル実行

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

`.env` に実際のGemini/Supabase認証情報と、十分に長い
`OWNER_SETUP_CODE` を設定します。次にSupabase SQL Editorで `schema.sql` を実行します。

```powershell
streamlit run app.py
```

CLI版は次のコマンドで実行できます。

```powershell
python translate.py
```

## 初回ログイン

1. アプリの「オーナーの初回登録」を開く
2. オーナーパスワードと `.env` の `OWNER_SETUP_CODE` を入力
3. Supabaseでメール確認が有効なら、届いたメールを確認
4. 通常のログインフォームからログイン

オーナーIDは `keikamotushige@gmail.com` です。

テスト用の初期値:

- ID: `test@translator.local`
- Password: `TestPass123!`

ログイン画面の「テストアカウントを準備」を押すと、
`SUPABASE_SERVICE_ROLE_KEY` を使ってテストユーザーを作成します。
公開環境ではテストアカウントを無効化するか、パスワードを変更してください。

## Streamlit Community Cloud

1. このリポジトリをGitHubへpush
2. Streamlit Community Cloudで `app.py` を指定
3. `.env` の各値をアプリのSecretsへ登録

`.env`、`.credentials.json`、APIキー、Service Role KeyはGitへ追加しないでください。
