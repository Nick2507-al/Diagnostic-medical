# 🏥 MediAI — Système de Diagnostic Médical par IA

> **Prototype BioMedLM fine-tuné pour l'analyse de symptômes, l'identification de maladies
> et les recommandations thérapeutiques.**

---

## 📁 Structure du projet

```
medical_ai/
├── 01_setup_and_data.ipynb      ← Étape 1 : Données & préparation
├── 02_finetuning.ipynb          ← Étape 2 : Entraînement QLoRA
├── 03_inference_and_demo.ipynb  ← Étape 3 : Test & Interface Gradio
├── config.py                    ← Chemins (local / Colab)
├── medical_data.py             ← Cas médicaux de base
├── prepare_data.py              ← Script : génère le dataset (local)
├── run_demo.py                  ← Script : lance l’interface Gradio (local)
├── requirements.txt            ← Dépendances Python
├── ENTRAINEMENT_CLOUD.md       ← Guide : entraînement 100 % cloud (Colab)
└── README.md                   ← Ce fichier
```

---

## ☁️ Entraînement 100 % dans le cloud (sans utiliser votre disque)

Pour **ne pas utiliser votre espace de stockage** (modèle 10,7 Go, données, checkpoints) : tout se fait sur **Google Colab** et le modèle est sauvegardé sur **Google Drive** ou **Hugging Face Hub**.

→ Voir le guide détaillé : **[ENTRAINEMENT_CLOUD.md](ENTRAINEMENT_CLOUD.md)**

En résumé : ouvrir les 3 notebooks dans Colab, activer le GPU, exécuter dans l’ordre. Données et modèle restent dans le cloud (Colab + Drive ou HF Hub).

---

## 🚀 Guide de démarrage rapide (Google Colab)

### Prérequis
- Compte Google (Colab + Drive)
- GPU activé : **Exécution → Modifier le type d'exécution → GPU T4**

### Ordre d'exécution

#### 📌 Étape 1 — Préparation des données
Ouvrir `01_setup_and_data.ipynb` et exécuter toutes les cellules.

Ce notebook :
- Installe toutes les dépendances
- Crée le dataset médical (15 pathologies × 10 variations = 150 cas)
- Formate les données au format instruction-tuning
- Sauvegarde sur Google Drive

**Durée :** ~5 minutes

---

### 🖥️ Exécution en local (Windows / Linux / macOS)

1. **Environnement** : Python 3.10+, GPU NVIDIA avec CUDA recommandé pour l’inférence et le fine-tuning.

2. **Installation des dépendances :**
   ```bash
   pip install -r requirements.txt
   ```

3. **Préparer le dataset** (sans GPU) :
   ```bash
   python prepare_data.py
   ```
   Crée le dossier `medical_ai/data/` et y enregistre le dataset (train/validation).

4. **Lancer l’interface de démo** (GPU recommandé) :
   ```bash
   python run_demo.py
   ```
   - Si le dossier `medical_ai/model_finetuned/` existe (modèle entraîné), il est utilisé.
   - Sinon, le modèle de base BioMedLM est chargé (réponses moins ciblées).
   - L’interface Gradio s’ouvre dans le navigateur (par défaut `http://127.0.0.1:7860`).

5. **Fine-tuning en local** : exécuter les notebooks `01_setup_and_data.ipynb`, puis `02_finetuning.ipynb` en adaptant les chemins `/content/medical_ai` vers `./medical_ai` (ou utiliser `config.WORK_DIR`).

---

#### 📌 Étape 2 — Fine-tuning
Ouvrir `02_finetuning.ipynb` et exécuter toutes les cellules.

Ce notebook :
- Charge **BioMedLM** (Stanford, 2.7B paramètres) en 4-bit
- Applique **QLoRA** (r=16) pour réduire la mémoire requise
- Lance l'entraînement supervisé (3 epochs)
- Affiche les courbes de convergence
- Sauvegarde le modèle final

**Durée :** ~35-45 minutes sur T4

---

#### 📌 Étape 3 — Inférence & Interface
Ouvrir `03_inference_and_demo.ipynb` et exécuter toutes les cellules.

Ce notebook :
- Charge le modèle fine-tuné
- Teste 3 cas cliniques nouveaux
- Calcule les scores ROUGE
- Lance l'**interface Gradio** avec lien public

**Durée :** ~5 minutes

---

## 🧠 Architecture technique

```
BioMedLM (stanford-crfm/BioMedLM)
├── Base : GPT-Neo 2.7B
├── Pré-entraîné sur : PubMed + littérature biomédicale
└── Fine-tuning : QLoRA (4-bit quantisation + LoRA r=16)

Dataset d'entraînement :
├── 15 pathologies couvrant les spécialités majeures
├── 10 variations par pathologie (âge, sexe, intensité)
└── Format : Instruction-tuning (system/user/assistant)

Sorties du modèle :
├── Diagnostic principal
├── Diagnostics différentiels
├── Mesures curatives (protocoles thérapeutiques)
├── Mesures préventives
├── Niveau d'urgence
└── Signes d'alarme
```

---

## 📊 Pathologies couvertes

| Spécialité          | Pathologies |
|---------------------|-------------|
| Pneumologie         | Pneumonie, Rhinopharyngite, Grippe |
| Cardiologie         | IDM, Fibrillation auriculaire |
| Gastro-entérologie  | Ulcère, Gastro-entérite |
| Neurologie          | Méningite, Migraine |
| Endocrinologie      | Diabète T1, Hypothyroïdie |
| Dermatologie        | Psoriasis |
| Infectiologie       | Paludisme |
| Rhumatologie        | Polyarthrite rhumatoïde |
| Psychiatrie         | Dépression majeure |

---

## ⚙️ Hyperparamètres recommandés

| Paramètre | Valeur | Justification |
|-----------|--------|---------------|
| LoRA rank (r) | 16 | Bon équilibre performance/mémoire |
| LoRA alpha | 32 | 2×r, standard |
| Learning rate | 2e-4 | Optimal QLoRA |
| Batch size effectif | 16 | 2×8 gradient accumulation |
| Epochs | 3 | Évite surapprentissage |
| Max seq length | 1024 | Couvre les cas longs |
| Temperature (inférence) | 0.3 | Réponses médicales conservatrices |

---

## 📈 Pour améliorer les performances

### Données supplémentaires (recommandé)
1. **DDXPlus** — 1.3M cas synthétiques : `https://github.com/mila-iqia/ddxplus`
2. **MedQA (USMLE)** — Questions médicales : disponible sur HuggingFace
3. **PubMedQA** — Questions sur articles scientifiques
4. **Vos propres données** — Cas cliniques anonymisés (RGPD/HIPAA)

### Pour augmenter les performances
```python
# Augmenter le rang LoRA si plus de VRAM disponible
lora_config = LoraConfig(r=32, lora_alpha=64, ...)

# Plus d'epochs avec early stopping
num_train_epochs=5

# Dataset plus large (recommandé : 1000+ cas)
```

---

## ⚠️ Avertissements importants

### Usage éthique
- Ce prototype est un **outil de recherche** uniquement
- Il **ne remplace pas** un médecin qualifié
- Ne pas utiliser pour des décisions médicales réelles sans validation
- Toujours mentionner qu'il s'agit d'une **aide à la décision**

### Réglementation
- Dispositif médical logiciel : soumis à **CE Medical Device** en Europe
- Aux USA : réglementation **FDA Software as a Medical Device (SaMD)**
- Validation clinique obligatoire avant tout déploiement

### Biais connus
- Dataset limité → biais de représentation (populations, ethnicités)
- Ne couvre pas toutes les pathologies rares
- Performances variables selon la spécificité des symptômes

---

## 📞 Urgences
En cas d'urgence médicale :
- **France** : SAMU 15 | Pompiers 18 | Urgences 112
- **Belgique** : 112
- **Suisse** : 144
- **Canada** : 911

---

*Projet éducatif — Anthropic Claude*
