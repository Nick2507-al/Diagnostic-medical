# -*- coding: utf-8 -*-
"""
Utilitaires pour l'interface MediAI : parsing des réponses et génération de graphiques.
"""
import re
from typing import Dict, List, Tuple, Any

# Import plotly seulement si disponible (éviter erreur si pas installé)
try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False


# Couleurs thème médical professionnel
COLORS = {
    "primary": "#0d47a1",
    "secondary": "#1565c0",
    "success": "#2e7d32",
    "warning": "#ed6c02",
    "danger": "#c62828",
    "neutral": "#546e7a",
    "bg_light": "#f5f9fc",
    "card_border": "#e3f2fd",
}


def parse_diagnostic_response(raw_text: str) -> Dict[str, Any]:
    """
    Parse la réponse du modèle pour extraire les sections (## Titre) et compter les éléments.
    Retourne un dict avec: sections (texte par section), counts (nombre d'items), urgency_level.
    """
    sections = {}
    counts = {}
    current_section = "autre"
    current_lines = []

    # Noms de sections reconnus (regex insensible à la casse et aux emojis)
    section_pattern = re.compile(
        r"^#+\s*(?:🔍\s*)?(?:DIAGNOSTIC\s+PRINCIPAL|diagnostic principal)"
        r"|^#+\s*(?:📋\s*)?(?:DIAGNOSTICS?\s+DIFF[EÉ]RENTIELS?|diagnostics? différentiels?)"
        r"|^#+\s*(?:💊\s*)?(?:MESURES?\s+CURATIVES?|curatives?)"
        r"|^#+\s*(?:🛡️\s*)?(?:MESURES?\s+PR[EÉ]VENTIVES?|préventives?)"
        r"|^#+\s*(?:⏱️\s*)?(?:NIVEAU\s+D'?URGENCE|urgence)"
        r"|^#+\s*(?:🚨\s*)?(?:SIGNES?\s+D'?ALARME|signes d'alarme)",
        re.IGNORECASE
    )

    # Comptage des listes (lignes qui commencent par - • * ou numérotées)
    list_item_pattern = re.compile(r"^\s*[-•*]\s+|\s*\d+[.)]\s+", re.MULTILINE)

    for line in raw_text.split("\n"):
        line_stripped = line.strip()
        if not line_stripped:
            if current_lines:
                text = "\n".join(current_lines).strip()
                if text:
                    sections[current_section] = sections.get(current_section, "") + "\n" + text
                current_lines = []
            continue

        # Détection section par ## ou ### (avec ou sans emoji)
        if re.match(r"^#+\s+", line_stripped):
            if current_lines:
                text = "\n".join(current_lines).strip()
                if text:
                    sections[current_section] = sections.get(current_section, "") + "\n" + text
                current_lines = []

            lower = line_stripped.lower()
            if "diagnostic principal" in lower and "diff" not in lower:
                current_section = "diagnostic_principal"
            elif "différentiel" in lower or "differentiel" in lower:
                current_section = "diagnostics_differentiels"
            elif "curative" in lower:
                current_section = "mesures_curatives"
            elif "préventive" in lower or "preventive" in lower:
                current_section = "mesures_preventives"
            elif "urgence" in lower:
                current_section = "niveau_urgence"
            elif "alarme" in lower:
                current_section = "signes_alarme"
            else:
                current_section = "autre"
            current_lines = [line_stripped]
        else:
            current_lines.append(line_stripped)

    if current_lines:
        text = "\n".join(current_lines).strip()
        if text:
            sections[current_section] = sections.get(current_section, "") + "\n" + text

    # Compter les items par section (lignes avec puces)
    for key in ["diagnostics_differentiels", "mesures_curatives", "mesures_preventives", "signes_alarme"]:
        text = sections.get(key, "")
        items = [l for l in text.split("\n") if l.strip() and re.match(r"^\s*[-•*⚠️]\s+|\s*\d+[.)]\s+", l)]
        counts[key] = len(items) if items else 0
    counts["diagnostic_principal"] = 1 if sections.get("diagnostic_principal") else 0
    counts["niveau_urgence"] = 1 if sections.get("niveau_urgence") else 0

    # Niveau d'urgence déduit du texte (0 à 3)
    urgency_level = _infer_urgency_level(raw_text)

    return {
        "sections": sections,
        "counts": counts,
        "urgency_level": urgency_level,
        "raw": raw_text,
    }


def _infer_urgency_level(text: str) -> int:
    """Retourne 0=non urgent, 1=consultation, 2=urgent, 3=vital."""
    text_lower = text.lower()
    if "urgence vitale" in text_lower or "urgent absolu" in text_lower or "samu" in text_lower or "15 " in text_lower:
        return 3
    if "urgence" in text_lower or "urgent" in text_lower or "hospitalisation" in text_lower:
        return 2
    if "consulter" in text_lower or "consultation" in text_lower:
        return 1
    return 0


def build_structure_chart(parsed: Dict[str, Any]) -> "go.Figure":
    """Graphique en barres : nombre d'éléments par section du diagnostic."""
    if not PLOTLY_AVAILABLE:
        return None

    labels_fr = {
        "diagnostic_principal": "Diagnostic principal",
        "diagnostics_differentiels": "Diagnostics différentiels",
        "mesures_curatives": "Mesures curatives",
        "mesures_preventives": "Mesures préventives",
        "niveau_urgence": "Niveau urgence",
        "signes_alarme": "Signes d'alarme",
    }
    counts = parsed.get("counts", {})
    labels = [labels_fr.get(k, k) for k in counts.keys()]
    values = list(counts.values())

    if not values:
        values = [0]
        labels = ["Aucune section"]

    fig = go.Figure(data=[
        go.Bar(
            x=labels,
            y=values,
            marker_color=[COLORS["primary"], COLORS["secondary"], COLORS["success"], COLORS["warning"], COLORS["neutral"], COLORS["danger"]][: len(labels)],
            text=values,
            textposition="outside",
        )
    ])
    fig.update_layout(
        title="Structure de la réponse — Éléments par section",
        template="plotly_white",
        font=dict(family="Segoe UI, sans-serif", size=12),
        margin=dict(t=50, b=80, l=20, r=20),
        xaxis_tickangle=-35,
        yaxis_title="Nombre d'éléments",
        height=320,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def build_urgency_gauge(urgency_level: int) -> "go.Figure":
    """Jauge (gauge) du niveau d'urgence (0-3)."""
    if not PLOTLY_AVAILABLE:
        return None

    level_labels = ["Non urgent", "Consultation recommandée", "Urgent", "Urgence vitale"]
    colors_gauge = [COLORS["success"], COLORS["neutral"], COLORS["warning"], COLORS["danger"]]

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=urgency_level,
        number=dict(suffix="", font=dict(size=28)),
        title=dict(text="Niveau d'urgence", font=dict(size=14)),
        gauge=dict(
            axis=dict(range=[0, 3], tickvals=[0, 1, 2, 3], ticktext=level_labels),
            bar=dict(color=colors_gauge[min(urgency_level, 3)]),
            steps=[],
            threshold=dict(line=dict(color="gray", width=2), value=urgency_level),
        ),
    ))
    fig.update_layout(
        template="plotly_white",
        font=dict(family="Segoe UI, sans-serif"),
        margin=dict(t=40, b=30, l=30, r=30),
        height=260,
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def build_session_history_chart(history: List[Dict]) -> "go.Figure":
    """Graphique de l'historique des analyses (urgence par analyse)."""
    if not PLOTLY_AVAILABLE or not history:
        return None

    indices = list(range(1, len(history) + 1))
    urgencies = [h.get("urgency_level", 0) for h in history]
    labels_short = [h.get("symptoms", "")[:40] + "..." if len(h.get("symptoms", "")) > 40 else h.get("symptoms", "") for h in history]

    fig = go.Figure(data=[
        go.Scatter(
            x=indices,
            y=urgencies,
            mode="lines+markers",
            line=dict(color=COLORS["primary"], width=2),
            marker=dict(size=10),
            text=labels_short,
            hovertemplate="Analyse %{x}<br>Urgence: %{y}<br>%{text}<extra></extra>",
        )
    ])
    fig.update_layout(
        title="Historique de la session — Niveau d'urgence par analyse",
        template="plotly_white",
        font=dict(family="Segoe UI, sans-serif"),
        xaxis=dict(title="Numéro d'analyse", tickvals=indices),
        yaxis=dict(title="Niveau urgence", range=[-0.2, 3.2], tickvals=[0, 1, 2, 3], ticktext=["Non urgent", "Consultation", "Urgent", "Vital"]),
        margin=dict(t=50, b=50),
        height=280,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def format_structured_html(parsed: Dict[str, Any]) -> str:
    """Formatte les sections en HTML pour affichage dans une carte élégante."""
    sections = parsed.get("sections", {})
    labels_fr = {
        "diagnostic_principal": "Diagnostic principal",
        "diagnostics_differentiels": "Diagnostics différentiels",
        "mesures_curatives": "Mesures curatives",
        "mesures_preventives": "Mesures préventives",
        "niveau_urgence": "Niveau d'urgence",
        "signes_alarme": "Signes d'alarme",
    }
    order = ["diagnostic_principal", "diagnostics_differentiels", "mesures_curatives", "mesures_preventives", "niveau_urgence", "signes_alarme"]

    html_parts = []
    for key in order:
        content = sections.get(key, "").strip()
        if not content:
            continue
        title = labels_fr.get(key, key)
        # Convertir retours à la ligne en <br> et échapper HTML basique
        content_safe = content.replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
        html_parts.append(
            f'<div class="diagnostic-card"><h4>{title}</h4><div class="diagnostic-content">{content_safe}</div></div>'
        )

    if not html_parts:
        return "<p>Aucune section structurée détectée. Affichage du texte brut ci-dessus.</p>"
    return "\n".join(html_parts)
