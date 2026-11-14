"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import AuthLayout from "@/components/AuthLayout";
import { api, ApiError } from "@/lib/api";

export default function RegisterPage() {
  const router = useRouter();
  const [form, setForm] = useState({ full_name: "", email: "", specialty: "", password: "", confirm: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const set = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm({ ...form, [k]: e.target.value });

  const weak = form.password.length > 0 && !(form.password.length >= 10 && /\d/.test(form.password) && /[a-zA-ZÀ-ÿ]/.test(form.password));
  const mismatch = form.confirm.length > 0 && form.confirm !== form.password;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (weak || mismatch) return;
    setBusy(true);
    setError("");
    try {
      await api("/auth/register", {
        method: "POST",
        body: JSON.stringify({
          full_name: form.full_name, email: form.email, password: form.password,
          specialty: form.specialty || null,
        }),
      });
      router.replace("/tableau-de-bord");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Inscription impossible");
      setBusy(false);
    }
  }

  return (
    <AuthLayout>
      <form onSubmit={submit} noValidate>
        <div>
          <h1>Créer un compte</h1>
          <p className="muted">Chaque compte dispose de ses propres analyses et de son historique.</p>
        </div>
        {error && <div className="alert bad" role="alert">{error}</div>}
        <div className="field">
          <label htmlFor="name">Nom complet</label>
          <input id="name" className="input" autoComplete="name" required maxLength={120} value={form.full_name} onChange={set("full_name")} />
        </div>
        <div className="field">
          <label htmlFor="email">Email professionnel</label>
          <input id="email" className="input" type="email" autoComplete="email" required maxLength={254} value={form.email} onChange={set("email")} />
        </div>
        <div className="field">
          <label htmlFor="spec">Spécialité (optionnel)</label>
          <input id="spec" className="input" maxLength={120} value={form.specialty} onChange={set("specialty")} placeholder="Médecine générale, pédiatrie…" />
        </div>
        <div className="field">
          <label htmlFor="pw">Mot de passe</label>
          <input id="pw" className="input" type="password" autoComplete="new-password" required maxLength={128} value={form.password} onChange={set("password")} />
          <span className={`small ${weak ? "" : "muted"}`} style={weak ? { color: "var(--bad)" } : undefined}>
            Au moins 10 caractères, avec au moins une lettre et un chiffre.
          </span>
        </div>
        <div className="field">
          <label htmlFor="pw2">Confirmer le mot de passe</label>
          <input id="pw2" className="input" type="password" autoComplete="new-password" required maxLength={128} value={form.confirm} onChange={set("confirm")} />
          {mismatch && <span className="small" style={{ color: "var(--bad)" }}>Les mots de passe ne correspondent pas.</span>}
        </div>
        <button className="btn lg" disabled={busy || weak || mismatch || !form.email || !form.full_name || !form.confirm}>
          {busy ? <span className="spinner" /> : "Créer mon compte"}
        </button>
        <p className="muted">Déjà inscrit ? <Link href="/connexion">Se connecter</Link></p>
      </form>
    </AuthLayout>
  );
}
