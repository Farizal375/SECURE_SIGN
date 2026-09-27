"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  FileText,
  LayoutDashboard,
  LogOut,
  Menu,
  PenLine,
} from "lucide-react";
import { createSupabaseBrowserClient } from "@/lib/supabase-auth/client";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";

export type AppSidebarUser = {
  fullName: string;
  email: string;
  role: string;
};

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/documents", label: "Dokumen", icon: FileText },
  { href: "/sign", label: "Penandatanganan", icon: PenLine },
];

const ROLE_LABELS: Record<string, string> = {
  signer: "Penandatangan",
  admin_secretary: "Sekretaris",
};

function getInitials(name: string) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
}

function SidebarContent({ user }: { user: AppSidebarUser }) {
  const router = useRouter();

  async function handleSignOut() {
    const supabase = createSupabaseBrowserClient();
    await supabase.auth.signOut();
    router.push("/login");
    router.refresh();
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex h-14 items-center border-b border-border px-4">
        <span className="text-h3 font-semibold">SecureSign</span>
      </div>

      <nav className="flex-1 space-y-1 p-2" aria-label="Navigasi utama">
        {NAV_ITEMS.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className="flex items-center gap-2 rounded-sm px-3 py-2 text-small text-ink-muted hover:bg-surface-muted hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          >
            <item.icon className="size-4" aria-hidden="true" />
            {item.label}
          </Link>
        ))}
      </nav>

      <Separator />

      <div className="p-3">
        <div className="flex items-center gap-2">
          <Avatar className="size-8">
            <AvatarFallback>{getInitials(user.fullName)}</AvatarFallback>
          </Avatar>
          <div className="min-w-0 flex-1">
            <p className="truncate text-small text-ink">{user.fullName}</p>
            <p className="truncate text-label text-ink-muted">
              {ROLE_LABELS[user.role] ?? user.role}
            </p>
          </div>
        </div>
        <Button
          variant="ghost"
          className="mt-2 w-full justify-start text-ink-muted hover:text-ink"
          onClick={handleSignOut}
        >
          <LogOut className="size-4" aria-hidden="true" />
          Keluar
        </Button>
      </div>
    </div>
  );
}

export function AppSidebar({ user }: { user: AppSidebarUser }) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <aside className="hidden w-[260px] flex-col border-r border-border bg-surface lg:flex fixed inset-y-0 left-0 z-30">
        <SidebarContent user={user} />
      </aside>

      <header className="sticky top-0 z-30 flex h-14 items-center gap-2 border-b border-border bg-surface px-4 lg:hidden">
        <Sheet open={open} onOpenChange={setOpen}>
          <SheetTrigger
            render={
              <Button
                variant="ghost"
                size="icon"
                aria-label="Buka menu"
              />
            }
          >
            <Menu className="size-5" aria-hidden="true" />
          </SheetTrigger>
          <SheetContent side="left" className="w-[260px] p-0">
            <SheetHeader className="sr-only">
              <SheetTitle>Menu</SheetTitle>
            </SheetHeader>
            <SidebarContent user={user} />
          </SheetContent>
        </Sheet>
        <span className="text-h3 font-semibold">SecureSign</span>
      </header>
    </>
  );
}
