import Link from "next/link";
import { formatDate } from "@/lib/api";
import { TRIAGE_LABEL, type AnalysisSummary } from "@/lib/types";

export function StatusBadge({ a }: { a: Pick<AnalysisSummary, "status" | "triage_level"> }) {
  if (a.status === "pending") return <span className="badge pending"><span className="spinner" style={{ width: 10, height: 10, borderWidth: 2 }} /> En cours</span>;
  if (a.status === "error") return <span className="badge error">Échec</span>;
  return a.triage_level ? <span className={`badge ${a.triage_level}`}>{TRIAGE_LABEL[a.triage_level]}</span> : null;
}

export default function AnalysisRow({ a }: { a: AnalysisSummary }) {
  return (
    <Link href={`/analyses/${a.id}`} className="list-item">
      <div className="grow">
        <div className="ellipsis" style={{ fontWeight: 700 }}>{a.title}</div>
        <div className="muted small ellipsis">
          {a.top_diagnosis ?? (a.status === "pending" ? "Analyse en cours…" : "—")} · {formatDate(a.created_at)}
        </div>
      </div>
      <StatusBadge a={a} />
    </Link>
  );
}
