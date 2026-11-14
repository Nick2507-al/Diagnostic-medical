"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { useUser } from "@/components/UserContext";
import { api, formatDate } from "@/lib/api";

export default function Profile() {
  const user = useUser();
  const router = useRouter();
  const [confirmText, setConfirmText] = useState("");
  const [error, setError] = useState("");

  async function deleteAccount() {
    try {
      await api("/auth/me", { method: "DELETE" });
      router.replace("/inscription");
    } catch (e) {
      setError((e as Error).message);
    }
  }

  return (
    <>
      <div className="page-head"><h1>Mon compte</h1></div>
      <section className="card stack">
        <div className="grid c2">
          <div><span className="muted small">Nom</span><div style={{ fontWeight: 700 }}>{user.full_name}</div></div>
          <div><span className="muted small">Email</span><div style={{ fontWeight: 700 }}>{user.email}</div></div>
          <div><span className="muted small">Spécialité</span><div>{user.specialty ?? "—"}</div></div>
          <div><span className="muted small">Membre depuis</span><div>{formatDate(user.created_at)}</div></div>
        </div>
      </section>
      <section className="card stack">
        <h2 style={{ color: "var(--bad)" }}>Supprimer mon compte</h2>
        <p className="muted">Supprime définitivement le compte, toutes ses analyses, documents et discussions.</p>
        {error && <div className="alert bad">{error}</div>}
        <div className="row">
          <input className="input" style={{ maxWidth: 280 }} placeholder='Tapez "SUPPRIMER"' value={confirmText}
            onChange={(e) => setConfirmText(e.target.value)} aria-label="Confirmation" />
          <button className="btn bad" disabled={confirmText !== "SUPPRIMER"} onClick={deleteAccount}>Supprimer définitivement</button>
        </div>
      </section>
    </>
  );
}
