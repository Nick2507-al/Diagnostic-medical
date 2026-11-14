"use client";

import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { api, streamChat } from "@/lib/api";
import type { ChatMessage, Conversation } from "@/lib/types";

type Msg = Pick<ChatMessage, "role" | "content"> & { id: string };

/** Markdown is rendered without raw HTML (react-markdown default), so model output can't inject markup. */
export function Markdown({ text }: { text: string }) {
  return (
    <ReactMarkdown remarkPlugins={[remarkGfm]}
      components={{ a: ({ href, children }) => <a href={href} target="_blank" rel="noopener noreferrer nofollow">{children}</a> }}>
      {text}
    </ReactMarkdown>
  );
}

export default function ChatPanel({ conversationId, suggestions = [] }: { conversationId: string; suggestions?: string[] }) {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const log = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api<Conversation>(`/conversations/${conversationId}`)
      .then((c) => setMessages(c.messages))
      .catch((e: Error) => setError(e.message));
  }, [conversationId]);

  useEffect(() => {
    log.current?.scrollTo({ top: log.current.scrollHeight });
  }, [messages]);

  async function send(text: string) {
    const content = text.trim();
    if (!content || busy) return;
    setBusy(true);
    setError("");
    setDraft("");
    const pendingId = `a-${Date.now()}`;
    setMessages((m) => [...m, { id: `u-${Date.now()}`, role: "user", content }, { id: pendingId, role: "assistant", content: "" }]);
    await streamChat(conversationId, content, {
      onDelta: (t) => setMessages((m) => m.map((x) => (x.id === pendingId ? { ...x, content: x.content + t } : x))),
      onError: (msg) => setError(msg),
      onDone: () => {
        setMessages((m) => m.filter((x) => !(x.id === pendingId && !x.content)));
        setBusy(false);
      },
    });
  }

  return (
    <div className="chat">
      <div className="chat-log" ref={log} aria-live="polite">
        {messages.length === 0 && (
          <div className="muted">
            <p>Posez une question sur le cas : alternatives thérapeutiques, examens, posologies, éléments qui feraient changer le diagnostic…</p>
            <div className="chips" style={{ marginTop: 10 }}>
              {suggestions.map((s) => (
                <button key={s} type="button" className="chip" style={{ border: 0, cursor: "pointer" }} onClick={() => send(s)}>{s}</button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m) => (
          <div key={m.id} className={`bubble ${m.role}`}>
            {m.role === "assistant"
              ? (m.content ? <Markdown text={m.content} /> : <span className="spinner" aria-label="Réponse en cours" />)
              : m.content}
          </div>
        ))}
      </div>
      {error && <div className="alert bad small" role="alert" style={{ marginBottom: 8 }}>{error}</div>}
      <form className="chat-input" onSubmit={(e) => { e.preventDefault(); send(draft); }}>
        <textarea className="textarea" value={draft} maxLength={8000} placeholder="Votre question…"
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(draft); } }} />
        <button className="btn" disabled={busy || !draft.trim()}>{busy ? <span className="spinner" /> : "Envoyer"}</button>
      </form>
    </div>
  );
}
