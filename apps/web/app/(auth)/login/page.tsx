import { redirect } from "next/navigation";
import { createSupabaseServerClient } from "@/lib/supabase-auth/server";
import { GoogleSignInButton } from "@/components/google-sign-in-button";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ error?: string }>;
}) {
  const supabase = await createSupabaseServerClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (user) {
    redirect("/dashboard");
  }

  const { error } = await searchParams;

  return (
    <main className="flex min-h-screen items-center justify-center px-4 py-8">
      <section className="w-full max-w-[480px] rounded-md border border-border bg-surface p-8">
        <h1 className="text-display">Masuk ke SecureSign</h1>
        <p className="mt-3 max-w-[65ch] text-small text-ink-muted">
          Masuk dengan akun Google untuk mengunggah dan menandatangani dokumen.
        </p>

        {error === "auth_failed" ? (
          <Alert
            variant="destructive"
            className="mt-6 border-error bg-error-bg text-error"
          >
            <AlertTitle>Gagal masuk</AlertTitle>
            <AlertDescription>
              Gagal masuk dengan Google. Coba lagi.
            </AlertDescription>
          </Alert>
        ) : null}

        <div className="mt-6">
          <GoogleSignInButton />
        </div>
      </section>
    </main>
  );
}
