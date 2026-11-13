import { PublicHeader } from "@/components/Header";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <PublicHeader />
      <main>{children}</main>
    </>
  );
}
