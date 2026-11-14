"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { UserContext } from "@/components/UserContext";
import { api } from "@/lib/api";
import type { User } from "@/lib/types";

const NAV = [
  { href: "/tableau-de-bord", label: "Tableau de bord", icon: "◧" },
  { href: "/analyses/nouvelle", label: "Nouvelle analyse", icon: "✚" },
  { href: "/historique", label: "Historique", icon: "☰" },
  { href: "/assistant", label: "Assistant clinique", icon: "✉" },
  { href: "/profil", label: "Mon compte", icon: "◉" },
];

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<User | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    api<User>("/auth/me")
      .then(setUser)
      .catch(() => router.replace(`/connexion?suite=${encodeURIComponent(pathname)}`));
    // pathname intentionally excluded: the session check runs once per load
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [router]);

  useEffect(() => setMenuOpen(false), [pathname]);

  async function logout() {
    await api("/auth/logout", { method: "POST" }).catch(() => undefined);
    router.replace("/connexion");
  }

  if (!user) {
    return (
      <div style={{ minHeight: "100vh", display: "grid", placeItems: "center", color: "var(--mut)" }}>
        <span className="spinner" aria-label="Chargement" />
      </div>
    );
  }

  return (
    <UserContext.Provider value={user}>
      <div className="mobile-bar">
        <span className="brand" style={{ padding: 0 }}><span className="brand-dot">✚</span> MEDIAI</span>
        <button aria-label="Menu" onClick={() => setMenuOpen(!menuOpen)}>☰</button>
      </div>
      <div className="shell">
        <aside className={`sidebar ${menuOpen ? "open" : ""}`}>
          <div className="brand"><span className="brand-dot" aria-hidden>✚</span> MEDIAI</div>
          <nav className="nav" aria-label="Navigation principale">
            {NAV.map((item) => (
              <Link key={item.href} href={item.href}
                className={pathname === item.href || (item.href !== "/analyses/nouvelle" && pathname.startsWith(item.href + "/")) ? "active" : ""}>
                <span aria-hidden>{item.icon}</span> {item.label}
              </Link>
            ))}
          </nav>
          <div className="sidebar-foot">
            <div style={{ fontWeight: 700 }}>{user.full_name}</div>
            <div style={{ color: "rgba(255,255,255,.6)" }} className="ellipsis">{user.email}</div>
            <button onClick={logout}>Se déconnecter</button>
          </div>
        </aside>
        <main className="main">{children}</main>
      </div>
    </UserContext.Provider>
  );
}
