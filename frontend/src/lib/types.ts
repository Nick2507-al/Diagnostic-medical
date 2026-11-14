export type User = {
  id: string;
  email: string;
  full_name: string;
  specialty: string | null;
  role: string;
  created_at: string;
};

export type Triage = "urgence_vitale" | "urgent" | "consultation_rapide" | "non_urgent";

export type Medication = {
  medicament: string;
  posologie: string;
  voie: string;
  frequence: string;
  duree: string;
  remarques: string;
};

export type Hypothesis = {
  maladie: string;
  code_cim10: string;
  probabilite: number;
  justification: string;
  elements_pour: string[];
  elements_contre: string[];
  examens_de_confirmation: string[];
};

export type Report = {
  synthese_clinique: string;
  donnees_manquantes: string[];
  triage: { niveau: Triage; justification: string };
  hypotheses: Hypothesis[];
  diagnostic_retenu: string;
  signes_d_alarme: string[];
  decision: {
    conduite_a_tenir: string;
    justification: string;
    examens_prioritaires: string[];
    criteres_de_reference: string[];
  };
  traitement: {
    pour_diagnostic: string;
    premiere_intention: Medication[];
    alternatives: Medication[];
    traitement_symptomatique: Medication[];
    mesures_non_medicamenteuses: string[];
    contre_indications_et_precautions: string[];
    surveillance: string[];
    suivi: string;
  };
  prevention: string[];
  references: string[];
  niveau_de_confiance: "eleve" | "modere" | "faible";
  avertissement: string;
};

export type FileInfo = { id: string; filename: string; kind: string; media_type: string; size_bytes: number };

export type AnalysisSummary = {
  id: string;
  title: string;
  status: "pending" | "done" | "error";
  triage_level: Triage | null;
  top_diagnosis: string | null;
  created_at: string;
  completed_at: string | null;
};

export type Analysis = AnalysisSummary & {
  patient: Record<string, string | number>;
  symptoms: string;
  clinical_notes: string;
  result: Report | null;
  error_message: string | null;
  model: string | null;
  files: FileInfo[];
};

export type AnalysisPage = { items: AnalysisSummary[]; total: number; page: number; page_size: number };

export type ChatMessage = { id: string; role: "user" | "assistant"; content: string; created_at: string };

export type ConversationSummary = {
  id: string;
  title: string;
  analysis_id: string | null;
  created_at: string;
  updated_at: string;
};

export type Conversation = ConversationSummary & { messages: ChatMessage[] };

export type Stats = {
  total_analyses: number;
  analyses_this_month: number;
  by_triage: Partial<Record<Triage, number>>;
  top_diagnoses: { diagnostic: string; nombre: number }[];
  conversations: number;
};

export const TRIAGE_LABEL: Record<Triage, string> = {
  urgence_vitale: "Urgence vitale",
  urgent: "Urgent",
  consultation_rapide: "Consultation rapide",
  non_urgent: "Non urgent",
};
