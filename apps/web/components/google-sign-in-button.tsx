"use client";

import { useState } from "react";
import { createSupabaseBrowserClient } from "@/lib/supabase-auth/client";
import { Button } from "@/components/ui/button";
import { Loader2 } from "lucide-react";

export function GoogleSignInButton() {
  const [loading, setLoading] = useState(false);

  async function handleClick() {
    setLoading(true);
    const supabase = createSupabaseBrowserClient();
    await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: `${process.env.NEXT_PUBLIC_SITE_URL}/auth/callback`,
      },
    });
  }

  return (
    <Button
      type="button"
      size="lg"
      className="w-full"
      onClick={handleClick}
      disabled={loading}
      aria-busy={loading}
    >
      {loading ? <Loader2 className="animate-spin" aria-hidden="true" /> : null}
      Masuk dengan Google
    </Button>
  );
}
