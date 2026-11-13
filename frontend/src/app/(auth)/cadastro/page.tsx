import type { Metadata } from "next";
import { AuthForm } from "@/components/AuthForm";

export const metadata: Metadata = { title: "Criar Conta · CineMatch" };

export default function CadastroPage() {
  return <AuthForm mode="cadastro" />;
}
