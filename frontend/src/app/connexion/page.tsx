"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import AuthLayout from "@/components/AuthLayout";
import { api, ApiError } from "@/lib/api";

/** Only same-site relative paths are accepted (prevents open redirects such as //evil.com). */
function safeNext(value: string | null): string {
  return value && value.startsWith("/") && !value.startsWith("//") && !value.startsWith("/\\")
    ? value
    : "/tableau-de-bord";
}

function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) });
      router.replace(safeNext(params.get("suite")));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Connexion impossible");
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} noValidate>
      <div>
        <h1>Connexion</h1>
        <p className="muted">Accédez à vos analyses et à votre historique.</p>
      </div>
      {error && <div className="alert bad" role="alert">{error}</div>}
      <div className="field">
        <label htmlFor="email">Email professionnel</label>
        <input id="email" className="input" type="email" autoComplete="email" required maxLength={254}
          value={email} onChange={(e) => setEmail(e.target.value)} />
      </div>
      <div className="field">
        <label htmlFor="password">Mot de passe</label>
        <input id="password" className="input" type="password" autoComplete="current-password" required maxLength={128}
          value={password} onChange={(e) => setPassword(e.target.value)} />
      </div>
      <button className="btn lg" disabled={busy || !email || !password}>
        {busy ? <span className="spinner" /> : "Se connecter"}
      </button>
      <p className="muted">Pas encore de compte ? <Link href="/inscription">Créer un compte</Link></p>
    </form>
  );
}

export default function LoginPage() {
  return (
    <AuthLayout>
      <Suspense>
        <LoginForm />
      </Suspense>
    </AuthLayout>
  );
}
