import type { Metadata } from "next";
import { Feed } from "@/components/Feed";
import { Recommendations } from "@/components/Recommendations";
import styles from "./home.module.css";

export const metadata: Metadata = { title: "Home · CineMatch" };

export default function HomePage() {
  return (
    <main className={styles.main}>
      <Recommendations />
      <Feed />
    </main>
  );
}
