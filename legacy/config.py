# -*- coding: utf-8 -*-
"""
Configuration des chemins pour MediAI (exécution locale ou Colab).
"""
from pathlib import Path

# Racine du projet (dossier contenant les notebooks et ce fichier)
PROJECT_ROOT = Path(__file__).resolve().parent

# Dossier de travail pour données et modèles (compatible local + Colab)
def get_work_dir():
    """Retourne le dossier de travail : medical_ai à la racine du projet."""
    work_dir = PROJECT_ROOT / "medical_ai"
    work_dir.mkdir(parents=True, exist_ok=True)
    return work_dir

WORK_DIR = get_work_dir()
DATA_DIR = WORK_DIR / "data"
MODEL_DIR = WORK_DIR / "model_finetuned"
DATASET_PATH = DATA_DIR / "medical_dataset"

# Modèle de base Hugging Face
BASE_MODEL_ID = "stanford-crfm/BioMedLM"
