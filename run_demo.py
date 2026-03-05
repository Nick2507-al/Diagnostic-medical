# -*- coding: utf-8 -*-
"""
Interface MediAI : diagnostic médical avec visualisations et graphiques.
Usage : python run_demo.py
Requis : GPU recommandé (CUDA).
"""
import sys
import warnings
from pathlib import Path
from typing import Tuple, List, Dict, Any, Optional

warnings.filterwarnings("ignore")

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import BASE_MODEL_ID, MODEL_DIR

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from peft import PeftModel

# ─── Chargement du modèle ───
def load_model():
    """Charge le modèle : fine-tuné si présent, sinon base BioMedLM."""
    use_finetuned = MODEL_DIR.is_dir() and any(MODEL_DIR.iterdir())
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.float16,
    )

    print("Chargement du tokenizer...")
    if use_finetuned:
        tokenizer = AutoTokenizer.from_pretrained(str(MODEL_DIR), trust_remote_code=True)
    else:
        tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_ID, trust_remote_code=True)

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    print("Chargement du modele (4-bit)...")
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL_ID,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
    )

    if use_finetuned:
        print("Application des poids fine-tunes (LoRA)...")
        model = PeftModel.from_pretrained(model, str(MODEL_DIR))
        print("Modele fine-tune charge")
    else:
        print("Modele de base BioMedLM charge")

    model.eval()
    return model, tokenizer


SYSTEM_PROMPT = """Tu es MediAI, un assistant médical expert formé pour aider les professionnels de santé.
Tu analyses les symptômes présentés, proposes des diagnostics différentiels, et formules des recommandations.
IMPORTANT : Tes analyses sont des outils d'aide à la décision. Seul un médecin peut établir un diagnostic officiel.
En cas d'urgence vitale, oriente toujours vers les services d'urgence (15, 18, 112)."""


def diagnose(
    symptoms: str,
    patient_info: str = "",
    max_new_tokens: int = 600,
    temperature: float = 0.3,
    top_p: float = 0.9,
) -> str:
    """Génère un diagnostic à partir des symptômes."""
    patient_str = f"\nPatient : {patient_info}" if patient_info else ""
    prompt = (
        f"<|system|>\n{SYSTEM_PROMPT}</s>\n<|user|>\n"
        f"Analyse ce cas clinique et fournis un diagnostic complet avec recommandations.{patient_str}\n"
        f"Symptômes : {symptoms}</s>\n<|assistant|>\n"
    )

    inputs = tokenizer(
        prompt,
        return_tensors="pt",
        truncation=True,
        max_length=512,
    ).to(model.device)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_p=top_p,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id,
            repetition_penalty=1.15,
        )

    input_len = inputs["input_ids"].shape[1]
    response_ids = outputs[0][input_len:]
    response = tokenizer.decode(response_ids, skip_special_tokens=True)
    return response.strip()


# ─── Interface : une seule fonction qui retourne tout (résultat + graphiques + état) ───
def run_analysis(
    symptoms: str,
    patient_info: str,
    temperature: float,
    max_tokens: int,
    history_state: List[Dict],
) -> Tuple[str, str, Optional[Any], Optional[Any], Optional[Any], List[Dict]]:
    """
    Lance l'analyse et retourne : rapport complet, HTML structuré, 3 graphiques, état mis à jour.
    """
    from ui_utils import (
        parse_diagnostic_response,
        build_structure_chart,
        build_urgency_gauge,
        build_session_history_chart,
        format_structured_html,
        PLOTLY_AVAILABLE,
    )

    if not (symptoms or "").strip():
        empty_msg = "Veuillez decrire les symptomes du patient."
        return empty_msg, "<p>" + empty_msg + "</p>", None, None, None, history_state

    raw_result = diagnose(
        symptoms=symptoms,
        patient_info=patient_info or "",
        max_new_tokens=int(max_tokens),
        temperature=float(temperature),
    )

    parsed = parse_diagnostic_response(raw_result)
    structured_html = format_structured_html(parsed)

    # Historique de session (garder les 20 derniers)
    new_entry = {
        "symptoms": symptoms[:200],
        "patient_info": patient_info or "",
        "urgency_level": parsed.get("urgency_level", 0),
        "parsed": parsed,
    }
    new_history = (history_state or []) + [new_entry]
    new_history = new_history[-20:]

    fig_structure = build_structure_chart(parsed) if PLOTLY_AVAILABLE else None
    fig_urgency = build_urgency_gauge(parsed.get("urgency_level", 0)) if PLOTLY_AVAILABLE else None
    fig_history = build_session_history_chart(new_history) if PLOTLY_AVAILABLE else None

    return raw_result, structured_html, fig_structure, fig_urgency, fig_history, new_history


# ─── CSS et structure de l'interface ───
CUSTOM_CSS = """
/* Thème médical professionnel */
:root {
    --med-primary: #0d47a1;
    --med-secondary: #1565c0;
    --med-success: #2e7d32;
    --med-warning: #ed6c02;
    --med-danger: #c62828;
    --med-bg: #f5f9fc;
    --med-card: #ffffff;
    --med-border: #e3f2fd;
}
.gradio-container { font-family: 'Segoe UI', system-ui, sans-serif; background: var(--med-bg) !important; }
h1, h2, h3 { color: var(--med-primary) !important; font-weight: 600 !important; }
.diagnostic-card {
    background: var(--med-card);
    border-left: 4px solid var(--med-primary);
    border-radius: 8px;
    padding: 1rem 1.25rem;
    margin-bottom: 1rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}
.diagnostic-card h4 {
    color: var(--med-primary);
    margin: 0 0 0.5rem 0;
    font-size: 1rem;
    text-transform: uppercase;
    letter-spacing: 0.02em;
}
.diagnostic-content { color: #37474f; line-height: 1.6; font-size: 0.95rem; }
.med-header {
    background: linear-gradient(135deg, #0d47a1 0%, #1565c0 100%);
    color: white !important;
    padding: 1.25rem 1.5rem;
    border-radius: 10px;
    margin-bottom: 1.5rem;
    box-shadow: 0 4px 12px rgba(13,71,161,0.25);
}
.med-header h1 { color: white !important; margin: 0 !important; }
.med-header p { color: rgba(255,255,255,0.9) !important; margin: 0.25rem 0 0 0 !important; }
.med-warning-box {
    background: #fff8e1;
    border: 1px solid #ffc107;
    border-radius: 8px;
    padding: 0.75rem 1rem;
    margin-bottom: 1rem;
    font-size: 0.9rem;
}
"""


def build_interface():
    import gradio as gr
    from ui_utils import PLOTLY_AVAILABLE

    examples = [
        ["Fièvre 39°C, toux productive, douleurs thoraciques, dyspnée depuis 4 jours", "Homme 50 ans, fumeur", 0.3, 600],
        ["Douleur thoracique irradiant au bras gauche, sueurs froides, nausées", "Homme 60 ans, hypertendu", 0.3, 600],
        ["Polyurie, polydipsie, amaigrissement rapide, fatigue extrême", "Adolescent 15 ans", 0.3, 600],
        ["Céphalées sévères, raideur de la nuque, fièvre 40°C, photophobie", "Jeune adulte 20 ans", 0.3, 600],
    ]

    with gr.Blocks(
        title="MediAI — Diagnostic médical",
        theme=gr.themes.Soft(
            primary_hue="blue",
            secondary_hue="slate",
        ),
        css=CUSTOM_CSS,
    ) as demo:
        history_state = gr.State([])

        gr.HTML("""
        <div class="med-header">
            <h1>MediAI — Assistant de diagnostic médical</h1>
            <p>Prototype BioMedLM · Aide à la décision · Visualisation des résultats</p>
        </div>
        <div class="med-warning-box">
            <strong>Avertissement :</strong> Cet outil est un prototype de recherche. Il ne remplace pas un avis médical.
            En cas d'urgence, appelez le <strong>15 (SAMU)</strong> ou le <strong>112</strong>.
        </div>
        """)

        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### Saisie du cas clinique")
                symptoms_input = gr.Textbox(
                    label="Symptômes",
                    placeholder="Décrivez les symptômes : fièvre, douleurs, durée, intensité...",
                    lines=4,
                )
                patient_input = gr.Textbox(
                    label="Informations patient (optionnel)",
                    placeholder="Ex. : Homme 45 ans, diabétique, antécédents cardiovasculaires",
                    lines=2,
                )
                with gr.Accordion("Paramètres avancés", open=False):
                    temp_slider = gr.Slider(0.1, 0.9, value=0.3, step=0.1, label="Température")
                    tokens_slider = gr.Slider(200, 800, value=600, step=100, label="Longueur max. réponse")
                btn = gr.Button("Analyser le cas clinique", variant="primary", size="lg")

        with gr.Tabs():
            with gr.TabItem("Rapport complet"):
                output_md = gr.Markdown(label="Résultat", value="*Lancez une analyse pour afficher le rapport.*")

            with gr.TabItem("Résumé structuré"):
                output_html = gr.HTML(value="<p><em>Lancez une analyse pour afficher le résumé par sections.</em></p>")

            with gr.TabItem("Graphiques"):
                with gr.Row():
                    plot_structure = gr.Plot(label="Structure de la reponse")
                    plot_urgency = gr.Plot(label="Niveau d'urgence")
                plot_history = gr.Plot(label="Historique de la session")
                if not PLOTLY_AVAILABLE:
                    gr.Markdown("Installez `plotly` pour afficher les graphiques : `pip install plotly`")

        gr.Markdown("---")
        gr.Markdown("### Exemples de cas")
        gr.Examples(
            examples=examples,
            inputs=[symptoms_input, patient_input, temp_slider, tokens_slider],
            label="Charger un exemple",
        )

        outputs = [output_md, output_html, plot_structure, plot_urgency, plot_history, history_state]

        btn.click(
            fn=run_analysis,
            inputs=[symptoms_input, patient_input, temp_slider, tokens_slider, history_state],
            outputs=outputs,
        )

    return demo


if __name__ == "__main__":
    if not torch.cuda.is_available():
        print("Aucun GPU detecte. Utilisez un environnement avec CUDA ou Google Colab.")
    else:
        print("GPU :", torch.cuda.get_device_name(0))

    model, tokenizer = load_model()
    demo = build_interface()
    print("Lancement de l'interface...")
    demo.launch(share=False, show_error=True)
