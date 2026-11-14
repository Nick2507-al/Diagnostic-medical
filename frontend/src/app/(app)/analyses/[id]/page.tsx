"use client";

import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import ChatPanel from "@/components/ChatPanel";
import ReportView from "@/components/ReportView";
import { StatusBadge } from "@/components/AnalysisRow";
import { api, formatDate } from "@/lib/api";
import type { Analysis, Conversation, ConversationSummary } from "@/lib/types";

const SUGGESTIONS = [
  "Quels éléments feraient basculer vers le 2e diagnostic ?",
  "Quelle alternative si l'antibiotique de 1re intention n'est pas disponible ?",
  "Adapte le traitement si la patiente est enceinte.",
  "Quels examens prioriser avec un plateau technique limité ?",
];

export default function AnalysisPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [a, setA] = useState<Analysis | null>(null);
  const [error, setError] = useState("");
  const [conversationId, setConversationId] = useState<string | null>(null);

  const load = useCallback(() => api<Analysis>(`/analyses/${id}`).then(setA).catch((e: Error) => setError(e.message)), [id]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {  // poll while the analysis runs
    if (a?.status !== "pending") return;
    const t = setInterval(load, 3000);
    return () => clearInterval(t);
  }, [a?.status, load]);

  useEffect(() => {  // reuse this case's discussion, or create it
    if (a?.status !== "done" || conversationId) return;
    api<ConversationSummary[]>(`/conversations?analysis_id=${a.id}`)
      .then((list) => list[0] ?? api<Conversation>("/conversations", { method: "POST", body: JSON.stringify({ analysis_id: a.id }) }))
      .then((c) => setConversationId(c.id))
      .catch((e: Error) => setError(e.message));
  }, [a?.status, a?.id, conversationId]);

  async function retry() {
    setError("");
    await api(`/analyses/${id}/retry`, { method: "POST" }).then(load).catch((e: Error) => setError(e.message));
  }

  async function remove() {
    if (!confirm("Supprimer définitivement cette analyse et sa discussion ?")) return;
    await api(`/analyses/${id}`, { method: "DELETE" }).then(() => router.replace("/historique")).catch((e: Error) => setError(e.message));
  }

  if (error && !a) return <div className="alert bad">{error}</div>;
  if (!a) return <span className="spinner" />;

  return (
    <>
      <div className="page-head">
        <div style={{ minWidth: 0 }}>
          <p className="muted small">{formatDate(a.created_at)}{a.files.length > 0 && ` · ${a.files.length} document(s)`}</p>
          <h1 className="ellipsis">{a.title}</h1>
        </div>
        <div className="row">
          <StatusBadge a={a} />
          {a.status !== "pending" && <button className="btn sec sm" onClick={retry}>Relancer</button>}
          <button className="btn bad sm" onClick={remove}>Supprimer</button>
        </div>
      </div>
      {error && <div className="alert bad" style={{ marginBottom: 16 }}>{error}</div>}

      {a.status === "pending" && (
        <div className="card row"><span className="spinner" /> Analyse en cours : raisonnement clinique et vérification des recommandations (30 s à 2 min)…</div>
      )}
      {a.status === "error" && <div className="alert bad">{a.error_message}</div>}

      {a.status === "done" && a.result && (
        <div className="split">
          <ReportView r={a.result} />
          <aside className="card sticky">
            <h2 style={{ marginBottom: 10 }}>Discuter du cas</h2>
            {conversationId ? <ChatPanel conversationId={conversationId} suggestions={SUGGESTIONS} /> : <span className="spinner" />}
          </aside>
        </div>
      )}

      <details className="card" style={{ marginTop: 16 }}>
        <summary style={{ cursor: "pointer", fontWeight: 700 }}>Données saisies</summary>
        <div className="stack" style={{ marginTop: 12 }}>
          <div className="chips">{Object.entries(a.patient).map(([k, v]) => <span key={k} className="chip">{k} : {String(v)}</span>)}</div>
          {a.symptoms && <p style={{ whiteSpace: "pre-wrap" }}><b>Symptômes :</b> {a.symptoms}</p>}
          {a.clinical_notes && <p style={{ whiteSpace: "pre-wrap" }}><b>Notes :</b> {a.clinical_notes}</p>}
          {a.files.length > 0 && <div className="chips">{a.files.map((f) => <span key={f.id} className="chip">{f.filename}</span>)}</div>}
        </div>
      </details>
    </>
  );
}
