import { TRIAGE_LABEL, type Medication, type Report } from "@/lib/types";

const CONFIDENCE = { eleve: "Élevé", modere: "Modéré", faible: "Faible" } as const;

function List({ items, empty = "—" }: { items: string[]; empty?: string }) {
  if (!items.length) return <p className="muted">{empty}</p>;
  return <ul className="clean">{items.map((x, i) => <li key={i}>{x}</li>)}</ul>;
}

function Meds({ title, meds }: { title: string; meds: Medication[] }) {
  if (!meds.length) return null;
  return (
    <div style={{ marginTop: 14 }}>
      <h3 style={{ marginBottom: 6 }}>{title}</h3>
      <div className="table-wrap">
        <table className="med-table">
          <thead><tr><th>Médicament</th><th>Posologie</th><th>Voie</th><th>Fréquence</th><th>Durée</th><th>Remarques</th></tr></thead>
          <tbody>
            {meds.map((m, i) => (
              <tr key={i}>
                <td style={{ fontWeight: 700 }}>{m.medicament}</td><td>{m.posologie}</td><td>{m.voie}</td>
                <td>{m.frequence}</td><td>{m.duree}</td><td className="muted">{m.remarques}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/** Renders the structured report. All values are text nodes: React escapes them (no HTML injection). */
export default function ReportView({ r }: { r: Report }) {
  const t = r.traitement;
  return (
    <div className="stack">
      <section className="card">
        <div className="row spread">
          <h2>Synthèse</h2>
          <div className="row">
            <span className={`badge ${r.triage.niveau}`}>{TRIAGE_LABEL[r.triage.niveau]}</span>
            <span className="badge pending">Confiance : {CONFIDENCE[r.niveau_de_confiance]}</span>
          </div>
        </div>
        <p style={{ marginTop: 10 }}>{r.synthese_clinique}</p>
        <p className="muted small" style={{ marginTop: 8 }}>{r.triage.justification}</p>
        {r.donnees_manquantes.length > 0 && (
          <div className="alert warn" style={{ marginTop: 12 }}>
            Données manquantes : {r.donnees_manquantes.join(" · ")}
          </div>
        )}
      </section>

      <section className="card">
        <h2 style={{ marginBottom: 4 }}>Diagnostics possibles</h2>
        <p className="muted small" style={{ marginBottom: 14 }}>
          Probabilités estimées par le modèle à partir du dossier : ce ne sont pas des mesures statistiques validées.
        </p>
        {r.hypotheses.map((h, i) => (
          <div key={i} className="hyp">
            <div className="row spread">
              <div><b>{h.maladie}</b> {h.code_cim10 && <span className="chip">{h.code_cim10}</span>}</div>
            </div>
            <div className="prob" style={{ marginTop: 8 }}>
              <div className="prob-bar"><span style={{ width: `${h.probabilite}%` }} /></div>
              <span className="prob-val">{h.probabilite} %</span>
            </div>
            <p style={{ marginTop: 8 }}>{h.justification}</p>
            <details>
              <summary>Arguments et examens de confirmation</summary>
              <div className="grid c3" style={{ marginTop: 10 }}>
                <div><h3>Pour</h3><List items={h.elements_pour} /></div>
                <div><h3>Contre</h3><List items={h.elements_contre} /></div>
                <div><h3>Confirmer / exclure</h3><List items={h.examens_de_confirmation} /></div>
              </div>
            </details>
          </div>
        ))}
      </section>

      <div className="grid c2" style={{ alignItems: "start" }}>
        <section className="card">
          <h2 style={{ marginBottom: 8 }}>Décision</h2>
          <p style={{ fontWeight: 700 }}>{r.decision.conduite_a_tenir}</p>
          <p className="muted" style={{ marginTop: 6 }}>{r.decision.justification}</p>
          <h3 style={{ margin: "14px 0 6px" }}>Examens prioritaires</h3>
          <List items={r.decision.examens_prioritaires} />
          <h3 style={{ margin: "14px 0 6px" }}>Critères de référence</h3>
          <List items={r.decision.criteres_de_reference} />
        </section>
        <section className="card">
          <h2 style={{ marginBottom: 8, color: "var(--bad)" }}>Signes d&apos;alarme</h2>
          <List items={r.signes_d_alarme} />
          <h3 style={{ margin: "14px 0 6px" }}>Prévention</h3>
          <List items={r.prevention} />
        </section>
      </div>

      <section className="card">
        <h2>Traitement — {t.pour_diagnostic}</h2>
        <Meds title="Première intention" meds={t.premiere_intention} />
        <Meds title="Alternatives" meds={t.alternatives} />
        <Meds title="Traitement symptomatique" meds={t.traitement_symptomatique} />
        <div className="grid c3" style={{ marginTop: 16 }}>
          <div><h3>Mesures non médicamenteuses</h3><List items={t.mesures_non_medicamenteuses} /></div>
          <div><h3>Contre-indications et précautions</h3><List items={t.contre_indications_et_precautions} /></div>
          <div><h3>Surveillance</h3><List items={t.surveillance} /></div>
        </div>
        <p style={{ marginTop: 12 }}><b>Suivi :</b> {t.suivi}</p>
      </section>

      <section className="card">
        <h3 style={{ marginBottom: 6 }}>Références</h3>
        <List items={r.references} />
        <p className="muted small" style={{ marginTop: 12 }}>{r.avertissement}</p>
      </section>
    </div>
  );
}
