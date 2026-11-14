"""Deterministic stand-in for the Claude provider."""
from app.schemas import DiagnosisReport
from app.services.ai import AIError, AnalysisResult, CaseContext, normalise_report


def sample_report(probs=(50, 25, 15)) -> DiagnosisReport:
    names = ["Paludisme grave à P. falciparum", "Méningite bactérienne", "Fièvre typhoïde"]
    med = {"medicament": "Artésunate", "posologie": "2,4 mg/kg", "voie": "IV", "frequence": "H0, H12, H24 puis /24h",
           "duree": "au moins 24 h puis relais oral", "remarques": "LME OMS"}
    return DiagnosisReport.model_validate({
        "synthese_clinique": "Fièvre avec troubles de conscience en zone d'endémie.",
        "donnees_manquantes": ["TDR paludisme", "Ponction lombaire"],
        "triage": {"niveau": "urgence_vitale", "justification": "Troubles de conscience"},
        "hypotheses": [
            {"maladie": n, "code_cim10": c, "probabilite": p, "justification": "j",
             "elements_pour": ["fièvre"], "elements_contre": [], "examens_de_confirmation": ["TDR"]}
            for n, c, p in zip(names, ["B50.0", "G00.9", "A01.0"], probs)
        ],
        "diagnostic_retenu": names[0],
        "signes_d_alarme": ["Convulsions"],
        "decision": {"conduite_a_tenir": "Hospitalisation", "justification": "Paludisme grave",
                     "examens_prioritaires": ["TDR", "Glycémie"], "criteres_de_reference": ["Coma"]},
        "traitement": {"pour_diagnostic": names[0], "premiere_intention": [med], "alternatives": [],
                       "traitement_symptomatique": [], "mesures_non_medicamenteuses": ["PLS"],
                       "contre_indications_et_precautions": [], "surveillance": ["Glycémie /4h"], "suivi": "J3, J7"},
        "prevention": ["MII"],
        "references": ["OMS — WHO Guidelines for malaria 2025"],
        "niveau_de_confiance": "modere",
        "avertissement": "Aide à la décision.",
    })


class FakeAI:
    def __init__(self) -> None:
        self.analyze_calls: list[CaseContext] = []
        self.chat_calls: list[tuple[CaseContext | None, list[dict]]] = []
        self.fail_with: str | None = None

    def analyze(self, case: CaseContext) -> AnalysisResult:
        self.analyze_calls.append(case)
        if self.fail_with:
            raise AIError(self.fail_with)
        return AnalysisResult(normalise_report(sample_report()), "fake-model", 100, 200)

    def chat_stream(self, case, history):
        self.chat_calls.append((case, history))
        if self.fail_with:
            raise AIError(self.fail_with)
        yield "Réponse "
        yield "clinique."
