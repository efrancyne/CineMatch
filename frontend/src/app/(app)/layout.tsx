"use client";

import { Suspense, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { AppHeader } from "@/components/Header";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { token, ready } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (ready && !token) router.replace("/login");
  }, [ready, token, router]);

  // enquanto não sabemos se há sessão (ou durante o redirecionamento), não mostra nada
  if (!ready || !token) return null;

  return (
    <>
      {/* useSearchParams no header exige Suspense */}
      <Suspense fallback={null}>
        <AppHeader />
      </Suspense>
      {children}
    </>
  );
}
