"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";

/** Quem já tem sessão vai direto para a home logada. */
export function RedirectIfLoggedIn() {
  const { token, ready } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (ready && token) router.replace("/home");
  }, [ready, token, router]);

  return null;
}
