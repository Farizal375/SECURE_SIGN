import { createSupabaseServerClient } from "@/lib/supabase-auth/server";
import { prisma } from "@/lib/prisma";
import { AppSidebar } from "@/components/app-sidebar";

export async function AppShell({ children }: { children: React.ReactNode }) {
  const supabase = await createSupabaseServerClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  const profile = user
    ? await prisma.profile.findUnique({ where: { id: user.id } })
    : null;

  const sidebarUser = {
    fullName: profile?.fullName ?? user?.email ?? "",
    email: user?.email ?? "",
    role: profile?.role ?? "signer",
  };

  return (
    <div className="min-h-screen bg-paper">
      <AppSidebar user={sidebarUser} />
      <div className="lg:pl-[260px]">
        <main className="mx-auto w-full max-w-[1120px] px-4 py-6 md:px-8 md:py-8">
          {children}
        </main>
      </div>
    </div>
  );
}
