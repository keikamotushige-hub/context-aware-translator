import { timingSafeEqual } from "node:crypto";
import { NextResponse } from "next/server";
import { adminClient } from "@/lib/auth";

export const runtime = "nodejs";

function matchesSetupCode(received: string) {
  const expected = process.env.OWNER_SETUP_CODE || "";
  if (!expected || received.length !== expected.length) return false;
  return timingSafeEqual(Buffer.from(received), Buffer.from(expected));
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const setupCode = String(body.setupCode || "");
    const ownerPassword = String(body.ownerPassword || "");
    if (!matchesSetupCode(setupCode)) {
      return NextResponse.json({ error: "セットアップコードが正しくありません。" }, { status: 403 });
    }
    if (ownerPassword.length < 10) {
      return NextResponse.json({ error: "パスワードは10文字以上にしてください。" }, { status: 400 });
    }

    const ownerEmail = process.env.OWNER_EMAIL?.trim().toLowerCase();
    const testEmail = process.env.TEST_EMAIL?.trim().toLowerCase();
    const testPassword = process.env.TEST_PASSWORD || "";
    if (!ownerEmail || !testEmail || testPassword.length < 10) {
      return NextResponse.json({ error: "アカウント設定が不足しています。" }, { status: 503 });
    }

    const admin = adminClient();
    const { data: listed, error: listError } = await admin.auth.admin.listUsers({
      page: 1,
      perPage: 1000,
    });
    if (listError) throw listError;
    const emails = new Set(
      listed.users.map((user) => user.email?.toLowerCase()).filter(Boolean),
    );

    if (emails.has(ownerEmail)) {
      return NextResponse.json(
        { error: "オーナーは登録済みです。通常ログインしてください。" },
        { status: 409 },
      );
    }

    const { error: ownerError } = await admin.auth.admin.createUser({
      email: ownerEmail,
      password: ownerPassword,
      email_confirm: true,
      user_metadata: { role: "owner" },
    });
    if (ownerError) throw ownerError;

    if (!emails.has(testEmail)) {
      const { error: testerError } = await admin.auth.admin.createUser({
        email: testEmail,
        password: testPassword,
        email_confirm: true,
        user_metadata: { role: "tester" },
      });
      if (testerError) throw testerError;
    }

    return NextResponse.json({ ok: true });
  } catch (error) {
    console.error("Account setup failed", error instanceof Error ? error.name : "Unknown");
    return NextResponse.json({ error: "初回登録に失敗しました。" }, { status: 500 });
  }
}
