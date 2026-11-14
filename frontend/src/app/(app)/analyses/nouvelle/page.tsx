"use client";

import { useRouter } from "next/navigation";
import { useRef, useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { Analysis } from "@/lib/types";

const ACCEPT = ".pdf,.doc,.docx,.xls,.xlsx,.csv,.txt,.md,.json,.rtf,.png,.jpg,.jpeg,.webp,.gif";
const MAX_FILES = 5;
const MAX_MB = 10;

const COUNTRIES = [
  "Afrique du Sud", "Algérie", "Angola", "Bénin", "Botswana", "Burkina Faso", "Burundi", "Cameroun", "Cap-Vert",
  "Centrafrique", "Comores", "Congo", "Côte d'Ivoire", "Djibouti", "Égypte", "Érythrée", "Eswatini", "Éthiopie",
  "Gabon", "Gambie", "Ghana", "Guinée", "Guinée équatoriale", "Guinée-Bissau", "Kenya", "Lesotho", "Liberia",
  "Libye", "Madagascar", "Malawi", "Mali", "Maroc", "Maurice", "Mauritanie", "Mozambique", "Namibie", "Niger",
  "Nigeria", "Ouganda", "RD Congo", "Rwanda", "Sao Tomé-et-Principe", "Sénégal", "Seychelles", "Sierra Leone",
  "Somalie", "Soudan", "Soudan du Sud", "Tanzanie", "Tchad", "Togo", "Tunisie", "Zambie", "Zimbabwe", "Autre",
];

type P = Record<string, string>;
const NUMERIC = ["age_years", "weight_kg", "pregnancy_weeks", "temperature_c", "heart_rate", "respiratory_rate",
  "systolic_bp", "diastolic_bp", "spo2", "glycemia_g_l"];

export default function NewAnalysis() {
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [symptoms, setSymptoms] = useState("");
  const [notes, setNotes] = useState("");
  const [p, setP] = useState<P>({ sex: "inconnu", pregnant: "inconnu", setting: "inconnu", hiv_status: "inconnu" });
  const [files, setFiles] = useState<File[]>([]);
  const [drag, setDrag] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const input = useRef<HTMLInputElement>(null);

  const field = (k: string) => ({
    value: p[k] ?? "",
    onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => setP({ ...p, [k]: e.target.value }),
  });

  function addFiles(list: FileList | null) {
    if (!list) return;
    const next = [...files];
    for (const f of Array.from(list)) {
      if (f.size > MAX_MB * 1024 * 1024) { setError(`${f.name} dépasse ${MAX_MB} Mo`); continue; }
      if (!next.some((x) => x.name === f.name && x.size === f.size)) next.push(f);
    }
    if (next.length > MAX_FILES) setError(`Maximum ${MAX_FILES} fichiers par analyse`);
    setFiles(next.slice(0, MAX_FILES));
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    const patient: Record<string, string | number> = {};
    for (const [k, v] of Object.entries(p)) {
      if (v === "" || v == null) continue;
      if (p.sex !== "femme" && (k === "pregnant" || k === "pregnancy_weeks")) continue;
      if (p.pregnant !== "oui" && k === "pregnancy_weeks") continue;
      patient[k] = NUMERIC.includes(k) ? Number(String(v).replace(",", ".")) : v;
    }
    if (Object.values(patient).some((v) => typeof v === "number" && Number.isNaN(v))) {
      setError("Une valeur numérique est invalide");
      return;
    }
    const form = new FormData();
    form.append("data", JSON.stringify({ title: title || null, symptoms, clinical_notes: notes, patient }));
    files.forEach((f) => form.append("files", f));
    setBusy(true);
    try {
      const a = await api<Analysis>("/analyses", { method: "POST", body: form });
      router.push(`/analyses/${a.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Envoi impossible");
      setBusy(false);
    }
  }

  const female = p.sex === "femme";

  return (
    <form onSubmit={submit} className="stack" noValidate>
      <div className="page-head">
        <div>
          <h1>Nouvelle analyse</h1>
          <p className="muted">Plus le contexte est précis (pays, âge, poids, constantes), plus l&apos;analyse est fiable.</p>
        </div>
      </div>
      {error && <div className="alert bad" role="alert">{error}</div>}

      <section className="card stack">
        <h2>Patient</h2>
        <div className="grid c4">
          <div className="field"><label>Âge (années)</label><input className="input" inputMode="decimal" {...field("age_years")} placeholder="ex. 0.5 pour 6 mois" /></div>
          <div className="field"><label>Sexe</label>
            <select className="select" {...field("sex")}>
              <option value="inconnu">Non précisé</option><option value="femme">Femme</option><option value="homme">Homme</option><option value="autre">Autre</option>
            </select>
          </div>
          <div className="field"><label>Poids (kg)</label><input className="input" inputMode="decimal" {...field("weight_kg")} /></div>
          <div className="field"><label>Statut VIH</label>
            <select className="select" {...field("hiv_status")}>
              <option value="inconnu">Inconnu</option><option value="negatif">Négatif</option><option value="positif">Positif</option>
            </select>
          </div>
          {female && (
            <>
              <div className="field"><label>Grossesse</label>
                <select className="select" {...field("pregnant")}>
                  <option value="inconnu">Inconnu</option><option value="non">Non</option><option value="oui">Oui</option>
                </select>
              </div>
              {p.pregnant === "oui" && <div className="field"><label>Terme (SA)</label><input className="input" inputMode="numeric" {...field("pregnancy_weeks")} /></div>}
            </>
          )}
          <div className="field"><label>Pays</label>
            <select className="select" {...field("country")}>
              <option value="">Non précisé</option>{COUNTRIES.map((c) => <option key={c}>{c}</option>)}
            </select>
          </div>
          <div className="field"><label>Région / ville</label><input className="input" maxLength={120} {...field("region")} /></div>
          <div className="field"><label>Niveau de soins</label>
            <select className="select" {...field("setting")}>
              <option value="inconnu">Non précisé</option><option value="communautaire">Communautaire</option>
              <option value="centre_de_sante">Centre de santé</option><option value="hopital_district">Hôpital de district</option>
              <option value="hopital_reference">Hôpital de référence</option>
            </select>
          </div>
        </div>
        <div className="grid c3">
          <div className="field"><label>Antécédents / comorbidités</label><input className="input" maxLength={1000} {...field("comorbidities")} placeholder="drépanocytose, diabète, HTA…" /></div>
          <div className="field"><label>Allergies</label><input className="input" maxLength={500} {...field("allergies")} /></div>
          <div className="field"><label>Traitements en cours</label><input className="input" maxLength={1000} {...field("current_medications")} placeholder="ARV, antituberculeux…" /></div>
          <div className="field"><label>Vaccinations</label><input className="input" maxLength={500} {...field("vaccination")} /></div>
          <div className="field"><label>Voyages / déplacements récents</label><input className="input" maxLength={500} {...field("recent_travel")} /></div>
        </div>
      </section>

      <section className="card stack">
        <h2>Constantes</h2>
        <div className="grid c4">
          <div className="field"><label>Température (°C)</label><input className="input" inputMode="decimal" {...field("temperature_c")} /></div>
          <div className="field"><label>FC (/min)</label><input className="input" inputMode="numeric" {...field("heart_rate")} /></div>
          <div className="field"><label>FR (/min)</label><input className="input" inputMode="numeric" {...field("respiratory_rate")} /></div>
          <div className="field"><label>SpO2 (%)</label><input className="input" inputMode="numeric" {...field("spo2")} /></div>
          <div className="field"><label>PA systolique</label><input className="input" inputMode="numeric" {...field("systolic_bp")} /></div>
          <div className="field"><label>PA diastolique</label><input className="input" inputMode="numeric" {...field("diastolic_bp")} /></div>
          <div className="field"><label>Glycémie (g/L)</label><input className="input" inputMode="decimal" {...field("glycemia_g_l")} /></div>
        </div>
      </section>

      <section className="card stack">
        <h2>Tableau clinique</h2>
        <div className="field"><label>Intitulé (optionnel)</label><input className="input" maxLength={200} value={title} onChange={(e) => setTitle(e.target.value)} placeholder="ex. Enfant fébrile, Brazzaville" /></div>
        <div className="field">
          <label>Symptômes et motif de consultation</label>
          <textarea className="textarea" maxLength={8000} value={symptoms} onChange={(e) => setSymptoms(e.target.value)}
            placeholder="Fièvre à 39,5 °C depuis 3 jours, céphalées, vomissements, refus de s'alimenter…" />
        </div>
        <div className="field">
          <label>Examen clinique, résultats d&apos;examens, notes</label>
          <textarea className="textarea" maxLength={20000} value={notes} onChange={(e) => setNotes(e.target.value)}
            placeholder="Pâleur, splénomégalie, TDR paludisme positif, Hb 7 g/dL…" />
        </div>
        <div className={`dropzone ${drag ? "drag" : ""}`} role="button" tabIndex={0}
          onClick={() => input.current?.click()} onKeyDown={(e) => e.key === "Enter" && input.current?.click()}
          onDragOver={(e) => { e.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)}
          onDrop={(e) => { e.preventDefault(); setDrag(false); addFiles(e.dataTransfer.files); }}>
          <b>Joindre des documents</b>
          <div className="muted small">PDF, Word, Excel, CSV, texte, images (bilans, comptes rendus, photos) — {MAX_FILES} fichiers, {MAX_MB} Mo max chacun</div>
          <input ref={input} type="file" hidden multiple accept={ACCEPT} onChange={(e) => { addFiles(e.target.files); e.target.value = ""; }} />
        </div>
        {files.length > 0 && (
          <div className="chips">
            {files.map((f) => (
              <span key={f.name + f.size} className="chip">
                {f.name} ({Math.max(1, Math.round(f.size / 1024))} Ko){" "}
                <button type="button" aria-label={`Retirer ${f.name}`} style={{ border: 0, background: "none", cursor: "pointer", color: "var(--bad)" }}
                  onClick={() => setFiles(files.filter((x) => x !== f))}>✕</button>
              </span>
            ))}
          </div>
        )}
      </section>

      <div className="row" style={{ justifyContent: "flex-end" }}>
        <button className="btn" disabled={busy || (!symptoms.trim() && !notes.trim() && files.length === 0)}>
          {busy ? <><span className="spinner" /> Envoi…</> : "Lancer l'analyse"}
        </button>
      </div>
    </form>
  );
}
