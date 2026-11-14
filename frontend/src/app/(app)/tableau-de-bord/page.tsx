"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useUser } from "@/components/UserContext";
import AnalysisRow from "@/components/AnalysisRow";
import { api } from "@/lib/api";
import { TRIAGE_LABEL, type AnalysisPage, type Stats, type Triage } from "@/lib/types";

export default function Dashboard() {
  const user = useUser();
  const [stats, setStats] = useState<Stats | null>(null);
  const [recent, setRecent] = useState<AnalysisPage | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api<Stats>("/stats"), api<AnalysisPage>("/analyses?page_size=6")])
      .then(([s, r]) => { setStats(s); setRecent(r); })
      .catch((e: Error) => setError(e.message));
  }, []);

  return (
    <>
      <div className="page-head">
        <div>
          <p className="muted">Bonjour</p>
          <h1>{user.full_name}</h1>
        </div>
        <Link href="/analyses/nouvelle" className="btn">✚ Nouvelle analyse</Link>
      </div>
      {error && <div className="alert bad">{error}</div>}

      <div className="grid c4">
        <div className="card stat"><span className="muted">Analyses</span><b>{stats?.total_analyses ?? "–"}</b></div>
        <div className="card stat"><span className="muted">Ce mois-ci</span><b>{stats?.analyses_this_month ?? "–"}</b></div>
        <div className="card stat"><span className="muted">Urgences vitales</span><b>{stats?.by_triage.urgence_vitale ?? 0}</b></div>
        <div className="card stat"><span className="muted">Discussions</span><b>{stats?.conversations ?? "–"}</b></div>
      </div>

      <div className="grid c2" style={{ marginTop: 16, alignItems: "start" }}>
        <section className="card">
          <div className="row spread" style={{ marginBottom: 8 }}>
            <h2>Analyses récentes</h2>
            <Link href="/historique" className="small">Tout voir</Link>
          </div>
          {recent && recent.items.length === 0 && (
            <p className="muted">Aucune analyse pour l&apos;instant. Lancez votre premier cas clinique.</p>
          )}
          <div className="list">{recent?.items.map((a) => <AnalysisRow key={a.id} a={a} />)}</div>
        </section>
        <section className="card">
          <h2 style={{ marginBottom: 12 }}>Répartition par niveau d&apos;urgence</h2>
          {(Object.keys(TRIAGE_LABEL) as Triage[]).map((t) => {
            const n = stats?.by_triage[t] ?? 0;
            const pct = stats?.total_analyses ? Math.round((n / stats.total_analyses) * 100) : 0;
            return (
              <div key={t} className="prob" style={{ marginBottom: 10 }}>
                <span className={`badge ${t}`} style={{ width: 150 }}>{TRIAGE_LABEL[t]}</span>
                <div className="prob-bar"><span style={{ width: `${pct}%` }} /></div>
                <span className="prob-val">{n}</span>
              </div>
            );
          })}
          {!!stats?.top_diagnoses.length && (
            <>
              <h3 style={{ margin: "18px 0 8px" }}>Diagnostics les plus fréquents</h3>
              <ul className="clean">
                {stats.top_diagnoses.map((d) => <li key={d.diagnostic}>{d.diagnostic} <span className="muted">({d.nombre})</span></li>)}
              </ul>
            </>
          )}
        </section>
      </div>
    </>
  );
}
