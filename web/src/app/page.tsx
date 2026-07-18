"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { browserSupabase } from "@/lib/supabase";

const LANGUAGES = [
  "日本語",
  "English",
  "简体中文",
  "繁體中文",
  "한국어",
  "Español",
  "Português",
  "Français",
  "Deutsch",
  "ไทย",
  "Tiếng Việt",
  "Bahasa Indonesia",
  "हिन्दी",
  "العربية",
];

type UserInfo = { email: string; role: "owner" | "tester" };
type TranslationResult = {
  originalText: string;
  translatedText: string;
  saved: boolean;
};

async function authorizedFetch(path: string, init?: RequestInit) {
  const { data } = await browserSupabase().auth.getSession();
  const token = data.session?.access_token;
  if (!token) throw new Error("ログインが必要です。");
  return fetch(path, {
    ...init,
    headers: { ...init?.headers, Authorization: `Bearer ${token}` },
  });
}

export default function Home() {
  const [checking, setChecking] = useState(true);
  const [user, setUser] = useState<UserInfo | null>(null);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [mode, setMode] = useState<"text" | "file" | "camera">("text");
  const [result, setResult] = useState<TranslationResult | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  async function restoreSession() {
    try {
      const { data } = await browserSupabase().auth.getSession();
      if (!data.session) return;
      const response = await authorizedFetch("/api/session");
      if (!response.ok) {
        await browserSupabase().auth.signOut();
        return;
      }
      setUser(await response.json());
    } finally {
      setChecking(false);
    }
  }

  useEffect(() => {
    void restoreSession();
  }, []);

  async function login(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    const form = new FormData(event.currentTarget);
    try {
      const { error } = await browserSupabase().auth.signInWithPassword({
        email: String(form.get("email") || "").trim(),
        password: String(form.get("password") || ""),
      });
      if (error) throw new Error("メールアドレスまたはパスワードが正しくありません。");
      const response = await authorizedFetch("/api/session");
      if (!response.ok) {
        await browserSupabase().auth.signOut();
        throw new Error("このアカウントには利用権限がありません。");
      }
      setUser(await response.json());
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "ログインできませんでした。");
    } finally {
      setBusy(false);
    }
  }

  async function setup(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    const form = new FormData(event.currentTarget);
    try {
      const response = await fetch("/api/setup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ownerPassword: form.get("ownerPassword"),
          setupCode: form.get("setupCode"),
        }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error);
      setMessage("初回登録が完了しました。上のフォームからログインしてください。");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "初回登録に失敗しました。");
    } finally {
      setBusy(false);
    }
  }

  async function translate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    setResult(null);
    const form = new FormData(event.currentTarget);
    const input = fileRef.current?.files?.[0];
    if (mode !== "text" && input) form.set("file", input);
    try {
      const response = await authorizedFetch("/api/translate", {
        method: "POST",
        body: form,
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error);
      setResult(data);
      if (!data.saved) setMessage("翻訳は完了しましたが、履歴を保存できませんでした。");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "翻訳できませんでした。");
    } finally {
      setBusy(false);
    }
  }

  async function logout() {
    await browserSupabase().auth.signOut();
    setUser(null);
    setResult(null);
  }

  if (checking) {
    return <main className="center-screen"><div className="loader" aria-label="読み込み中" /></main>;
  }

  if (!user) {
    return (
      <main className="auth-shell">
        <section className="brand-panel">
          <div>
            <p className="eyebrow">SUZUKI TOTAL SERVICE</p>
            <h1>言葉を、<br />届く表現へ。</h1>
            <p className="brand-copy">
              相手の知識や文化に合わせて伝え方まで整える、
              Gemini搭載の文脈特化型翻訳ツール。
            </p>
          </div>
          <p className="brand-foot">Text · Document · Camera</p>
        </section>
        <section className="auth-panel">
          <div className="auth-card">
            <p className="eyebrow dark">MEMBERS ONLY</p>
            <h2>ログイン</h2>
            <p className="muted">オーナーと承認済みテスターのみ利用できます。</p>
            <form onSubmit={login} className="form-stack">
              <label>メールアドレス<input name="email" type="email" autoComplete="email" required /></label>
              <label>パスワード<input name="password" type="password" autoComplete="current-password" required /></label>
              <button className="primary" disabled={busy}>{busy ? "確認中…" : "ログイン"}</button>
            </form>
            {message && <p className="notice">{message}</p>}
            <details className="setup">
              <summary>オーナーの初回登録</summary>
              <form onSubmit={setup} className="form-stack compact">
                <label>最初に登録するパスワード<input name="ownerPassword" type="password" minLength={10} required /></label>
                <label>初回セットアップコード<input name="setupCode" type="password" required /></label>
                <button className="secondary" disabled={busy}>オーナーとテスターを準備</button>
              </form>
            </details>
          </div>
          <LegalFooter />
        </section>
      </main>
    );
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow dark">CONTEXT TRANSLATOR</p>
          <h1>文脈特化型翻訳</h1>
        </div>
        <div className="user-area">
          <span><strong>{user.role === "owner" ? "Owner" : "Tester"}</strong><small>{user.email}</small></span>
          <button className="ghost" onClick={logout}>ログアウト</button>
        </div>
      </header>

      <section className="workspace">
        <form className="translator-card" onSubmit={translate}>
          <div className="settings-row">
            <label>翻訳先言語
              <select name="targetLanguage" defaultValue="日本語">
                {LANGUAGES.map((language) => <option key={language}>{language}</option>)}
              </select>
            </label>
            <label>ターゲット層
              <input name="targetAudience" defaultValue="一般の方" placeholder="例：日本を初めて訪れる観光客" required />
            </label>
          </div>

          <div className="mode-tabs" role="tablist">
            {(["text", "file", "camera"] as const).map((item) => (
              <button
                type="button"
                role="tab"
                aria-selected={mode === item}
                className={mode === item ? "active" : ""}
                onClick={() => { setMode(item); setResult(null); }}
                key={item}
              >
                {item === "text" ? "テキスト" : item === "file" ? "ファイル" : "カメラ"}
              </button>
            ))}
          </div>

          {mode === "text" ? (
            <label className="input-block">翻訳する内容
              <textarea name="text" rows={12} maxLength={50_000} placeholder="翻訳したい文章を入力してください。" required />
            </label>
          ) : (
            <label className="drop-zone">
              <strong>{mode === "camera" ? "文書や案内板を撮影" : "文書または画像を選択"}</strong>
              <span>PDF / TXT / CSV / JSON / JPG / PNG / WEBP（最大10MB）</span>
              <input
                ref={fileRef}
                name="file"
                type="file"
                accept={mode === "camera" ? "image/*" : ".pdf,.txt,.md,.csv,.json,.jpg,.jpeg,.png,.webp"}
                capture={mode === "camera" ? "environment" : undefined}
                required
              />
            </label>
          )}

          <button className="translate-button" disabled={busy}>
            {busy ? "翻訳しています…" : "文脈に合わせて翻訳"}
          </button>
          {message && <p className="notice">{message}</p>}
        </form>

        <section className={`result-card ${result ? "has-result" : ""}`}>
          <div className="result-heading">
            <div><p className="eyebrow dark">RESULT</p><h2>翻訳結果</h2></div>
            {result && (
              <button className="ghost" onClick={() => navigator.clipboard.writeText(result.translatedText)}>
                コピー
              </button>
            )}
          </div>
          {result ? (
            <>
              <p className="translated">{result.translatedText}</p>
              <details><summary>読み取った原文</summary><p className="original">{result.originalText}</p></details>
              <a
                className="download"
                download="translation.txt"
                href={`data:text/plain;charset=utf-8,${encodeURIComponent(result.translatedText)}`}
              >
                テキストで保存
              </a>
            </>
          ) : (
            <div className="empty-result">
              <span>A</span>
              <p>翻訳結果がここに表示されます。</p>
            </div>
          )}
        </section>
      </section>
      <LegalFooter />
    </main>
  );
}

function LegalFooter() {
  return (
    <footer className="legal-footer">
      <details>
        <summary>運営者情報・利用規約・プライバシー</summary>
        <div className="legal-copy">
          <h3>運営者情報</h3>
          <p>鈴木トータルサービス／代表 鈴木 茂<br />〒343-0804 埼玉県越谷市南荻島580-8<br />keikamotushige@gmail.com</p>
          <h3>利用上の注意</h3>
          <p>本サービスはAIによる翻訳支援です。契約・医療・法務・公的証明書など重要な文書は、資格を有する専門家による確認を受けてください。</p>
          <h3>データの取り扱い</h3>
          <p>入力内容は翻訳のためGoogle Geminiへ送信され、翻訳履歴はSupabaseへ保存されます。個人情報・機密情報は必要最小限にしてください。</p>
        </div>
      </details>
      <p>© 2026 鈴木トータルサービス</p>
    </footer>
  );
}
