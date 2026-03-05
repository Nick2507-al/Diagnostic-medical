# -*- coding: utf-8 -*-
"""
Préparation du dataset médical pour MediAI (exécution locale).
Génère le dataset au format instruction-tuning et le sauvegarde.
"""
import random
from pathlib import Path

from datasets import Dataset, DatasetDict

from config import DATA_DIR, DATASET_PATH
from medical_data import MEDICAL_CASES

SYSTEM_PROMPT = """Tu es MediAI, un assistant médical expert formé pour aider les professionnels de santé.
Tu analyses les symptômes présentés, proposes des diagnostics différentiels, et formules des recommandations.
IMPORTANT : Tes analyses sont des outils d'aide à la décision. Seul un médecin peut établir un diagnostic officiel.
En cas d'urgence vitale, oriente toujours vers les services d'urgence (15, 18, 112)."""


def augment_case(case, variation_id):
    """Crée des variations légères d'un cas médical."""
    age_variations = [15, 22, 30, 35, 42, 48, 55, 62, 70, 78]
    gender_variations = ["Homme", "Femme"]
    symptom_intensity = ["légers", "modérés", "intenses", "sévères"]

    age = age_variations[variation_id % len(age_variations)]
    gender = gender_variations[variation_id % 2]
    intensity = symptom_intensity[variation_id % len(symptom_intensity)]

    augmented = case.copy()
    augmented["patient_info"] = f"{gender} {age} ans, symptômes {intensity}"

    if variation_id % 3 == 0:
        augmented["symptoms"] = case["symptoms"] + f", depuis {random.randint(1, 14)} jours"
    elif variation_id % 3 == 1:
        augmented["symptoms"] = case["symptoms"] + ", antécédents familiaux notables"

    return augmented


def format_for_training(case):
    """Formate un cas en paire instruction/réponse pour le fine-tuning."""
    instruction = f"""Analyse ce cas clinique et fournis un diagnostic complet avec recommandations.

Patient : {case['patient_info']}
Symptômes : {case['symptoms']}"""

    differential_str = "\n".join([f"   - {d}" for d in case["differential"]])
    curative_str = "\n".join([f"   • {c}" for c in case["curative"]])
    preventive_str = "\n".join([f"   • {p}" for p in case["preventive"]])
    red_flags_str = "\n".join([f"   ⚠️ {r}" for r in case["red_flags"]])

    response = f"""## 🔍 DIAGNOSTIC PRINCIPAL
{case['diagnosis']}

## 📋 DIAGNOSTICS DIFFÉRENTIELS
{differential_str}

## 💊 MESURES CURATIVES
{curative_str}

## 🛡️ MESURES PRÉVENTIVES
{preventive_str}

## ⏱️ NIVEAU D'URGENCE
{case['urgency']}

## 🚨 SIGNES D'ALARME (consulter immédiatement)
{red_flags_str}

---
*Cette analyse est une aide à la décision. Consultez un médecin pour tout diagnostic officiel.*"""

    full_text = f"<|system|>\n{SYSTEM_PROMPT}</s>\n<|user|>\n{instruction}</s>\n<|assistant|>\n{response}</s>"

    return {
        "instruction": instruction,
        "response": response,
        "text": full_text,
    }


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    augmented_cases = []
    for case in MEDICAL_CASES:
        augmented_cases.append(case)
        for i in range(9):
            augmented_cases.append(augment_case(case, i))

    formatted_data = [format_for_training(c) for c in augmented_cases]
    random.shuffle(formatted_data)

    split_idx = int(len(formatted_data) * 0.85)
    train_data = formatted_data[:split_idx]
    val_data = formatted_data[split_idx:]

    dataset = DatasetDict({
        "train": Dataset.from_list(train_data),
        "validation": Dataset.from_list(val_data),
    })

    dataset.save_to_disk(str(DATASET_PATH))
    print(f"[OK] Dataset cree : {len(train_data)} train, {len(val_data)} validation")
    print(f"[OK] Sauvegarde dans : {DATASET_PATH}")
    return dataset


if __name__ == "__main__":
    main()
