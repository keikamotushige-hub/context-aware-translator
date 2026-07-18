import { createClient } from "@supabase/supabase-js";

function env(name: string): string {
  const value = process.env[name]?.trim();
  if (!value) throw new Error(`Missing server environment variable: ${name}`);
  return value;
}

export function adminClient() {
  return createClient(env("SUPABASE_URL"), env("SUPABASE_SERVICE_ROLE_KEY"), {
    auth: { autoRefreshToken: false, persistSession: false },
  });
}

export function allowedEmails(): Set<string> {
  const owner = env("OWNER_EMAIL").toLowerCase();
  const testers = (process.env.TEST_EMAILS || process.env.TEST_EMAIL || "")
    .split(",")
    .map((email) => email.trim().toLowerCase())
    .filter(Boolean);
  return new Set([owner, ...testers]);
}

export async function requireAllowedUser(request: Request) {
  const header = request.headers.get("authorization");
  const token = header?.startsWith("Bearer ") ? header.slice(7) : "";
  if (!token) throw new Error("UNAUTHORIZED");

  const { data, error } = await adminClient().auth.getUser(token);
  const email = data.user?.email?.toLowerCase();
  if (error || !data.user || !email || !allowedEmails().has(email)) {
    throw new Error("UNAUTHORIZED");
  }
  return { user: data.user, email };
}
