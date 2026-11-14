"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import ChatPanel from "@/components/ChatPanel";
import { api, formatDate } from "@/lib/api";
import type { Conversation, ConversationSummary } from "@/lib/types";

const SUGGESTIONS = [
  "Schéma thérapeutique du paludisme grave chez l'enfant de 15 kg",
  "Conduite à tenir devant une fièvre chez un patient VIH+ sous ARV",
  "Critères de référence d'une pré-éclampsie en centre de santé",
  "Prise en charge d'une crise vaso-occlusive drépanocytaire",
];

export default function Assistant() {
  const [list, setList] = useState<ConversationSummary[]>([]);
  const [current, setCurrent] = useState<string | null>(null);
  const [error, setError] = useState("");

  const refresh = () => api<ConversationSummary[]>("/conversations").then(setList).catch((e: Error) => setError(e.message));
  useEffect(() => { refresh(); }, []);

  async function create() {
    try {
      const c = await api<Conversation>("/conversations", { method: "POST", body: JSON.stringify({}) });
      setCurrent(c.id);
      refresh();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function remove(id: string) {
    if (!confirm("Supprimer cette discussion ?")) return;
    await api(`/conversations/${id}`, { method: "DELETE" }).catch((e: Error) => setError(e.message));
    if (current === id) setCurrent(null);
    refresh();
  }

  return (
    <>
      <div className="page-head">
        <div>
          <h1>Assistant clinique</h1>
          <p className="muted">Posez vos questions médicales ; pour discuter d&apos;un patient précis, ouvrez son analyse.</p>
        </div>
        <button className="btn" onClick={create}>✚ Nouvelle discussion</button>
      </div>
      {error && <div className="alert bad" style={{ marginBottom: 16 }}>{error}</div>}
      <div className="split narrow-left">
        <aside className="card" style={{ padding: 12 }}>
          {list.length === 0 && <p className="muted small" style={{ padding: 8 }}>Aucune discussion.</p>}
          <div className="list">
            {list.map((c) => (
              <div key={c.id} className="list-item" style={{ cursor: "pointer", background: current === c.id ? "var(--pale)" : undefined }}
                onClick={() => setCurrent(c.id)}>
                <div className="grow">
                  <div className="ellipsis" style={{ fontWeight: 700 }}>{c.title}</div>
                  <div className="muted small">
                    {formatDate(c.updated_at)}
                    {c.analysis_id && <> · <Link href={`/analyses/${c.analysis_id}`} onClick={(e) => e.stopPropagation()}>cas lié</Link></>}
                  </div>
                </div>
                <button aria-label="Supprimer" onClick={(e) => { e.stopPropagation(); remove(c.id); }}
                  style={{ border: 0, background: "none", cursor: "pointer", color: "var(--mut)" }}>✕</button>
              </div>
            ))}
          </div>
        </aside>
        <section className="card">
          {current ? (
            <ChatPanel key={current} conversationId={current} suggestions={SUGGESTIONS} />
          ) : (
            <div className="stack" style={{ alignItems: "flex-start" }}>
              <p className="muted">Sélectionnez une discussion ou démarrez-en une nouvelle.</p>
              <button className="btn sec" onClick={create}>Démarrer une discussion</button>
            </div>
          )}
        </section>
      </div>
    </>
  );
}
