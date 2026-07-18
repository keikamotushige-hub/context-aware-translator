import { NextResponse } from "next/server";
import { requireAllowedUser } from "@/lib/auth";

export async function GET(request: Request) {
  try {
    const { email } = await requireAllowedUser(request);
    const owner = process.env.OWNER_EMAIL?.trim().toLowerCase();
    return NextResponse.json({ email, role: email === owner ? "owner" : "tester" });
  } catch {
    return NextResponse.json({ error: "利用権限がありません。" }, { status: 401 });
  }
}
