"use client";

import { useEffect, useState } from "react";
import AnalysisRow from "@/components/AnalysisRow";
import { api } from "@/lib/api";
import { TRIAGE_LABEL, type AnalysisPage, type Triage } from "@/lib/types";

const PAGE_SIZE = 20;

export default function History() {
  const [q, setQ] = useState("");
  const [query, setQuery] = useState("");
  const [triage, setTriage] = useState("");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<AnalysisPage | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const t = setTimeout(() => { setQuery(q.trim()); setPage(1); }, 300);
    return () => clearTimeout(t);
  }, [q]);

  useEffect(() => {
    const params = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) });
    if (query) params.set("q", query);
    if (triage) params.set("triage", triage);
    api<AnalysisPage>(`/analyses?${params}`).then(setData).catch((e: Error) => setError(e.message));
  }, [query, triage, page]);

  const pages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;

  return (
    <>
      <div className="page-head">
        <div><h1>Historique</h1><p className="muted">{data ? `${data.total} analyse(s)` : "…"}</p></div>
      </div>
      <div className="card">
        <div className="row" style={{ marginBottom: 12 }}>
          <input className="input" style={{ flex: 1, minWidth: 200 }} placeholder="Rechercher (symptôme, diagnostic, intitulé)…"
            maxLength={100} value={q} onChange={(e) => setQ(e.target.value)} aria-label="Rechercher" />
          <select className="select" style={{ width: 220 }} value={triage} aria-label="Filtrer par urgence"
            onChange={(e) => { setTriage(e.target.value); setPage(1); }}>
            <option value="">Tous les niveaux</option>
            {(Object.keys(TRIAGE_LABEL) as Triage[]).map((t) => <option key={t} value={t}>{TRIAGE_LABEL[t]}</option>)}
          </select>
        </div>
        {error && <div className="alert bad">{error}</div>}
        {data?.items.length === 0 && <p className="muted">Aucune analyse ne correspond.</p>}
        <div className="list">{data?.items.map((a) => <AnalysisRow key={a.id} a={a} />)}</div>
        {pages > 1 && (
          <div className="row" style={{ justifyContent: "center", marginTop: 14 }}>
            <button className="btn sec sm" disabled={page <= 1} onClick={() => setPage(page - 1)}>Précédent</button>
            <span className="muted">Page {page} / {pages}</span>
            <button className="btn sec sm" disabled={page >= pages} onClick={() => setPage(page + 1)}>Suivant</button>
          </div>
        )}
      </div>
    </>
  );
}
