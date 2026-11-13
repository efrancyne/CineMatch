import Link from "next/link";
import type { UsuarioPublico } from "@/lib/types";
import { Avatar } from "./Avatar";
import styles from "./PersonRow.module.css";

export function PersonRow({ user, action }: { user: UsuarioPublico; action?: React.ReactNode }) {
  return (
    <article className={styles.row}>
      <Link href={`/usuarios/${user.id}`} className={styles.who}>
        <Avatar name={user.name} src={user.avatar_url} size={52} />
        <span>
          <strong>{user.name}</strong>
          <small>@{user.username}</small>
          {user.bio && <em>{user.bio}</em>}
        </span>
      </Link>
      {action}
    </article>
  );
}
