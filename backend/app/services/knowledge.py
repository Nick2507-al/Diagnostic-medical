"""Clinical reference context injected (and prompt-cached) into every AI request.

This is not a substitute for the model's medical knowledge: it is a checklist that forces the
differential to cover conditions that are frequent or dangerous in Africa, and anchors the
treatment section to the reference guidelines clinicians there actually use.
"""

AFRICAN_CONDITIONS: dict[str, list[str]] = {
    "Fièvres aiguës / infections systémiques": [
        "Paludisme simple et grave (P. falciparum, vivax, ovale, malariae)",
        "Fièvre typhoïde et paratyphoïde",
        "Sepsis bactérien / bactériémie à salmonelles non typhiques",
        "Méningite bactérienne (méningocoque, pneumocoque, Hib) — ceinture de la méningite",
        "Dengue, chikungunya, Zika, fièvre jaune",
        "Fièvres hémorragiques virales : Ebola, Marburg, Lassa, fièvre de Crimée-Congo, fièvre de la vallée du Rift",
        "Leptospirose", "Rickettsioses (typhus, fièvre à tiques africaine)", "Brucellose",
        "Borréliose à tiques (fièvre récurrente)", "Peste", "Mpox (variole simienne)",
        "Rougeole", "Varicelle", "Fièvre Q",
    ],
    "VIH, tuberculose et infections opportunistes": [
        "Infection à VIH (primo-infection, stade avancé, syndrome inflammatoire de reconstitution)",
        "Tuberculose pulmonaire, extrapulmonaire, méningée, TB-MR/UR",
        "Cryptococcose neuroméningée", "Pneumocystose", "Toxoplasmose cérébrale",
        "Histoplasmose disséminée", "Talaromycose", "Sarcome de Kaposi", "Candidose œsophagienne",
        "Maladie à cytomégalovirus",
    ],
    "Infections respiratoires": [
        "Pneumonie communautaire de l'enfant et de l'adulte", "Bronchiolite", "Coqueluche",
        "Diphtérie", "Grippe", "COVID-19", "Pleurésie / empyème",
    ],
    "Diarrhées et maladies digestives": [
        "Choléra", "Shigellose / dysenterie bacillaire", "Amibiase intestinale et abcès amibien du foie",
        "Gastro-entérite à rotavirus", "Giardiase", "Hépatites virales A, B, C, D, E",
        "Ulcère gastroduodénal / H. pylori", "Appendicite, péritonite, occlusion",
        "Malnutrition aiguë sévère (kwashiorkor, marasme)",
    ],
    "Maladies tropicales négligées et parasitoses": [
        "Schistosomiase urinaire et intestinale", "Trypanosomiase humaine africaine (maladie du sommeil)",
        "Leishmaniose viscérale (kala-azar) et cutanée", "Onchocercose", "Filariose lymphatique",
        "Loase", "Dracunculose", "Ulcère de Buruli", "Lèpre", "Pian", "Trachome", "Rage",
        "Envenimation ophidienne", "Géohelminthiases (ascaris, ankylostome, trichocéphale)",
        "Strongyloïdose", "Cysticercose / neurocysticercose", "Échinococcose", "Gale", "Tungose",
        "Mycétome", "Teigne",
    ],
    "Santé maternelle et néonatale": [
        "Pré-éclampsie / éclampsie", "Hémorragie du post-partum", "Sepsis puerpéral",
        "Grossesse extra-utérine", "Avortement compliqué", "Paludisme de la grossesse",
        "Anémie de la grossesse", "Sepsis néonatal", "Ictère néonatal", "Tétanos néonatal",
        "Asphyxie néonatale",
    ],
    "Infections sexuellement transmissibles et génito-urinaires": [
        "Syphilis", "Gonococcie", "Chlamydiose", "Trichomonase", "Chancre mou",
        "Herpès génital", "Infection urinaire / pyélonéphrite", "Maladie inflammatoire pelvienne",
    ],
    "Maladies non transmissibles": [
        "Hypertension artérielle et urgences hypertensives", "Insuffisance cardiaque",
        "Cardiomyopathie (péripartum, dilatée)", "Cardiopathie rhumatismale", "Accident vasculaire cérébral",
        "Infarctus du myocarde", "Diabète type 1 et 2, acidocétose, état hyperosmolaire",
        "Drépanocytose et ses crises (vaso-occlusive, séquestration, syndrome thoracique aigu)",
        "Anémie ferriprive, anémie hémolytique, déficit en G6PD", "Maladie rénale chronique",
        "Asthme", "BPCO", "Épilepsie", "Cancers (col utérin, sein, prostate, foie, lymphome de Burkitt)",
        "Hypothyroïdie / hyperthyroïdie / goitre", "Insuffisance hépatique, cirrhose",
    ],
    "Santé mentale et neurologie": [
        "Dépression", "Psychose aiguë / schizophrénie", "Troubles liés à l'alcool et aux substances",
        "Konzo et neuropathies toxiques/nutritionnelles", "Neuropathie périphérique",
    ],
    "Dermatologie, ORL, ophtalmologie": [
        "Infections cutanées bactériennes (impétigo, érysipèle, cellulite)", "Mycoses cutanées",
        "Otite moyenne aiguë", "Angine streptococcique", "Conjonctivite", "Cataracte", "Glaucome",
    ],
    "Intoxications et urgences": [
        "Intoxication aux organophosphorés", "Intoxication au paracétamol", "Brûlures",
        "Traumatismes", "Coup de chaleur", "Morsures et piqûres venimeuses",
    ],
}

REFERENCE_GUIDELINES = [
    "OMS — WHO Guidelines for malaria (version la plus récente)",
    "OMS — Consolidated guidelines on tuberculosis (modules traitement, TB de l'enfant)",
    "OMS — Consolidated guidelines on HIV prevention, testing, treatment, service delivery and monitoring",
    "OMS — Prise en charge intégrée des maladies de l'enfant (PCIME / IMCI)",
    "OMS — Pocket book of hospital care for children",
    "OMS — The WHO AWaRe antibiotic book",
    "OMS — Liste modèle des médicaments essentiels (LME) adultes et enfants",
    "OMS — Recommandations sur les soins prénatals, l'accouchement et le post-partum",
    "OMS — Lignes directrices sur les maladies tropicales négligées (feuille de route MTN)",
    "OMS AFRO — Guide technique pour la surveillance intégrée de la maladie et la riposte (SIMR/IDSR)",
    "OMS — PEN (Package of essential noncommunicable disease interventions) et HEARTS",
    "OMS — mhGAP (santé mentale)",
    "Protocoles nationaux du pays du patient lorsqu'ils diffèrent des recommandations OMS",
]

NOTIFIABLE_HINT = (
    "Maladies à déclaration obligatoire / potentiel épidémique (SIMR) : choléra, méningite, rougeole, "
    "fièvre jaune, fièvres hémorragiques virales, mpox, peste, poliomyélite (PFA), dengue, rage, "
    "diarrhée sanglante en grappe, COVID-19, grippe à nouveau sous-type."
)


def conditions_block() -> str:
    lines = []
    for category, items in AFRICAN_CONDITIONS.items():
        lines.append(f"- {category} : " + " ; ".join(items))
    return "\n".join(lines)


def guidelines_block() -> str:
    return "\n".join(f"- {g}" for g in REFERENCE_GUIDELINES)
