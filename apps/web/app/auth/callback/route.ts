import { NextRequest, NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/lib/supabase-auth/server";
import { prisma } from "@/lib/prisma";
import { auditEventHash } from "@/lib/audit";

export async function GET(request: NextRequest) {
  const requestUrl = new URL(request.url);
  const code = requestUrl.searchParams.get("code");
  const next = requestUrl.searchParams.get("next") ?? "/dashboard";

  if (!code) {
    return NextResponse.redirect(new URL("/login?error=auth_failed", requestUrl.origin));
  }

  const supabase = await createSupabaseServerClient();
  const { error } = await supabase.auth.exchangeCodeForSession(code);

  if (error) {
    return NextResponse.redirect(new URL("/login?error=auth_failed", requestUrl.origin));
  }

  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user?.email) {
    return NextResponse.redirect(new URL("/login?error=auth_failed", requestUrl.origin));
  }

  const existing = await prisma.profile.findUnique({ where: { id: user.id } });

  if (!existing) {
    await prisma.profile.create({
      data: {
        id: user.id,
        email: user.email,
        fullName:
          (user.user_metadata?.full_name as string | undefined) ?? user.email,
        role: "signer",
      },
    });
  }

  await prisma.auditLog.create({
    data: {
      actorId: user.id,
      eventType: "USER_LOGIN",
      metadata: {},
      previousEventHash: "",
      eventHash: auditEventHash(
        "USER_LOGIN",
        { actorId: user.id, createdAt: new Date().toISOString() },
        "",
      ),
    },
  });

  return NextResponse.redirect(new URL(next, requestUrl.origin));
}
