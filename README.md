# Contextia — 文脈特化型AI翻訳

鈴木トータルサービス向けの業務用翻訳アプリです。
Next.js + Gemini + Supabase で構成し、Vercel で公開できます。

## 機能

- オーナー / テスター限定ログイン
- テキスト・文書・画像の文脈特化翻訳
- Gemini による多言語翻訳
- Supabase への翻訳履歴保存（RLS）
- 利用規約・プライバシー・特商法表記

## ローカル実行

```bash
npm install
# .env を設定
npm run dev
```

## Vercel 環境変数

- `GEMINI_API_KEY`
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `OWNER_EMAIL`
- `OWNER_SETUP_CODE`
- `TEST_EMAIL`
- `TEST_PASSWORD`
- `TEST_EMAILS`

## ログイン

1. 初回はオーナーのセットアップコードでオーナー／テスターを準備
2. オーナー: `OWNER_EMAIL`
3. テスター: `TEST_EMAIL` / `TEST_PASSWORD`
