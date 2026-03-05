# Entraînement MediAI 100 % dans le cloud

Ce guide permet d’**entraîner le modèle entièrement dans le cloud**, sans utiliser l’espace disque de votre ordinateur (ni les ~10,7 Go du modèle, ni les données, ni les checkpoints).

---

## Principe

| Étape              | Où ça tourne   | Stockage utilisé                    |
|--------------------|----------------|-------------------------------------|
| Données            | Google Colab   | Disque Colab (/content)             |
| Entraînement       | Google Colab   | RAM/VRAM Colab (GPU T4)             |
| Modèle final       | Cloud          | Google Drive **ou** Hugging Face Hub|

Votre PC ne stocke rien de lourd : vous ouvrez un notebook dans le navigateur et tout s’exécute sur les serveurs Google.

---

## Option 1 : Google Colab + Google Drive (recommandé)

### 1. Prérequis

- Un compte Google (Gmail).
- Ouvrir [Google Colab](https://colab.research.google.com/).

### 2. Préparer les notebooks dans Colab

- Soit **importer** le dossier du projet depuis GitHub ou depuis votre Drive (Fichier → Importer un notebook).
- Soit **copier-coller** le contenu des 3 notebooks du projet :
  - `01_setup_and_data.ipynb`
  - `02_finetuning.ipynb`
  - `03_inference_and_demo.ipynb`

### 3. Activer le GPU

Dans Colab : **Exécution → Modifier le type d’exécution → GPU** (T4 suffit). Valider.

### 4. Ordre d’exécution

**Notebook 1 — Données**

1. Exécuter toutes les cellules de `01_setup_and_data.ipynb`.
2. À la fin, une cellule monte Google Drive et enregistre le dataset dans **Drive** (ex. `Mon Drive/medical_ai_project/`).
3. Aucun téléchargement du modèle ici : uniquement création des données (~quelques Mo).

**Notebook 2 — Entraînement**

1. Au début du notebook, exécuter la cellule qui **monte Google Drive** (si ce n’est pas déjà fait) :
   ```python
   from google.colab import drive
   drive.mount('/content/drive')
   ```
2. Vérifier que le dataset est bien dans Drive (même chemin que sauvegardé par le notebook 1), ou adapter le chemin de chargement vers `/content/drive/MyDrive/medical_ai_project/data/medical_dataset`.
3. Exécuter toutes les cellules. Le modèle **BioMedLM est téléchargé sur le disque Colab** (~10,7 Go), pas sur votre PC.
4. À la fin, le modèle fine-tuné est sauvegardé dans **Google Drive** (ex. `medical_ai_project/model_finetuned`). Seuls les poids LoRA (~quelques dizaines de Mo) sont copiés sur Drive.

**Notebook 3 — Test / démo**

1. Monter Drive, charger le modèle depuis `.../medical_ai_project/model_finetuned`.
2. Tester et lancer l’interface Gradio dans Colab (lien public temporaire).

### 5. Récupérer le modèle sur votre PC (optionnel)

Si vous voulez utiliser le modèle en local plus tard :

- Depuis **Google Drive** : télécharger uniquement le dossier **`model_finetuned`** (poids LoRA + config, pas les 10,7 Go du modèle de base). Le modèle de base BioMedLM sera re-téléchargé au premier lancement de `run_demo.py` si besoin.

Vous n’avez donc jamais à stocker les 10,7 Go sur votre machine pour l’entraînement.

---

## Option 2 : Sauvegarder le modèle sur Hugging Face Hub

Pour garder le modèle **uniquement dans le cloud** (sans Drive ni disque local), vous pouvez pousser l’adaptateur LoRA sur le **Hugging Face Hub**. Ensuite, vous chargez ce modèle par son identifiant (par ex. depuis Colab ou depuis votre appli).

### 1. Créer un token Hugging Face

1. Aller sur [huggingface.co](https://huggingface.co/), créer un compte.
2. **Paramètres → Access tokens → Nouveau token** (type “Write”). Copier le token.

### 2. Dans Colab, après l’entraînement (notebook 2)

Ajouter une cellule et l’exécuter (remplacer `VOTRE_UTILISATEUR` et `VOTRE_TOKEN`) :

```python
# Enregistrement du modèle sur le Hugging Face Hub (optionnel)
!pip install -q huggingface_hub

from huggingface_hub import login, HfApi
login(token="VOTRE_TOKEN")  # ou utilisez une variable d'environnement HF_TOKEN

model_id = "VOTRE_UTILISATEUR/mediai-finetuned"  # ex. "dupont/mediai-finetuned"
trainer.push_to_hub(model_id)
tokenizer.push_to_hub(model_id)

print("Modèle publié sur https://huggingface.co/" + model_id)
```

Le modèle fine-tuné (adaptateur) sera alors **stocké sur le cloud** Hugging Face. Vous pourrez le charger avec :

```python
from peft import PeftModel
model = PeftModel.from_pretrained(base_model, "VOTRE_UTILISATEUR/mediai-finetuned")
```

sans rien garder sur votre disque.

---

## Résumé

- **Entraînement** : 100 % sur **Google Colab** (GPU T4), sans utiliser votre espace disque.
- **Stockage du modèle** :
  - **Google Drive** : après entraînement, copie automatique du dossier `model_finetuned` dans Drive.
  - **Hugging Face Hub** : optionnel, en ajoutant une cellule qui fait `push_to_hub` après l’entraînement.
- **Utilisation après entraînement** :
  - Tester dans Colab avec le notebook 3.
  - En local : télécharger seulement `model_finetuned` depuis Drive (léger) et lancer `run_demo.py` ; le modèle de base sera téléchargé une fois par la lib si besoin.

Ainsi, le modèle de 10,7 Go n’a jamais besoin d’être stocké sur votre machine pour l’entraînement.
