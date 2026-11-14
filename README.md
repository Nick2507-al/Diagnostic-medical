# MediAI — Aide à la décision clinique

Application web destinée aux médecins exerçant en Afrique. À partir d'un cas clinique (contexte patient,
constantes, symptômes, documents joints), MediAI produit :

- une liste de diagnostics différentiels, chacun avec une probabilité estimée, une justification, les
  arguments pour et contre, et les examens de confirmation adaptés au plateau technique ;
- un triage (urgence vitale → non urgent), les signes d'alarme et les critères de référence ;
- une décision de prise en charge ;
- un plan de traitement complet : première intention, alternatives, traitement symptomatique, posologies
  adaptées (âge, poids, grossesse), précautions, surveillance et suivi, d'après les recommandations OMS et
  nationales ;
- un **assistant clinique** (chatbot) pour discuter de chaque cas ou poser des questions générales.

Chaque médecin a son compte, ses analyses et son historique.

> ⚠️ MediAI est un outil d'aide à la décision. Les probabilités sont des estimations du modèle, pas des
> mesures statistiques validées. Le diagnostic et la prescription restent sous la responsabilité du médecin.
> Avant tout usage clinique réel, une validation clinique et une conformité réglementaire sont nécessaires
> (marquage CE dispositif médical, autorités sanitaires nationales, protection des données de santé).

## Architecture

| Couche | Technologie |
|---|---|
| Interface | Next.js 16 + React 19 (TypeScript), CSS natif d'après les maquettes `design/` |
| API | Python 3.14, FastAPI, SQLAlchemy 2, Alembic |
| Base de données | PostgreSQL 18 |
| IA | Claude Opus 5.5 (API Anthropic) : sortie JSON structurée et validée, réflexion adaptative, repli automatique en cas de refus, mise en cache du prompt |

**Pourquoi un modèle via API plutôt qu'un modèle local ?** Un modèle médical ouvert performant pèse entre
8 et 50 Go et exige un GPU. Il ne tient ni sur une machine ordinaire, ni sur un hébergement web classique.
Les études sur des cas cliniques africains montrent que la fiabilité vient surtout d'un raisonnement ancré
dans les recommandations (OMS, PCIME, protocoles nationaux). C'est le rôle de
`backend/app/services/knowledge.py` et du prompt système de `backend/app/services/ai.py`.

### Documents acceptés

PDF (y compris scannés), Word `.docx`, Excel `.xlsx`/`.xls`, CSV, TXT, Markdown, JSON, RTF, images
PNG/JPEG/WEBP/GIF. Le type est détecté d'après le contenu du fichier, pas son extension. Les PDF et les
images sont lus directement par le modèle ; le texte des autres formats est extrait intégralement (tableaux
compris). Un document trop long est refusé avec un message clair au lieu d'être tronqué en silence.

## Installation

Prérequis : Python 3.12 ou plus récent, Node.js 20 ou plus récent, PostgreSQL 16 ou plus récent, une clé
API Anthropic.

```bash
# 1. Base de données (dans psql, en tant que postgres)
CREATE ROLE mediai LOGIN PASSWORD '<mot de passe>';
CREATE DATABASE mediai OWNER mediai;
CREATE DATABASE mediai_test OWNER mediai;   # pour les tests

# 2. Backend
cd backend
python -m venv .venv
.venv\Scripts\pip install -r requirements-dev.txt     # Linux/macOS : .venv/bin/pip
copy .env.example .env                                 # puis renseigner DATABASE_URL, ANTHROPIC_API_KEY…
.venv\Scripts\alembic upgrade head

# 3. Frontend
cd ../frontend
npm ci
```

## Démarrage

Depuis la racine du projet :

```bash
npm run dev
```

Cette commande applique les migrations, puis lance l'API (port 8000, rechargement automatique) et
l'interface (port 3000) dans le même terminal, avec des journaux préfixés `[api]` et `[web]`. Ctrl+C arrête
les deux. Si un ancien serveur MediAI occupe encore un port (terminal fermé sans Ctrl+C), il est arrêté
automatiquement ; une autre application sur ce port provoque un message d'erreur, sans rien arrêter.
Sous Windows, `demarrer.bat` fait la même chose et ouvre le navigateur.

Ouvrez ensuite http://localhost:3000. Le compte défini par `DEFAULT_USER_EMAIL` et `DEFAULT_USER_PASSWORD`
dans `backend/.env` est créé au premier démarrage.

## Tests

```bash
cd backend && .venv/Scripts/python -m pytest
```

Les tests utilisent la base `mediai_test` et une IA simulée : ils sont gratuits et reproductibles. Ils
couvrent l'authentification (session, CSRF, verrouillage, limitation de débit), l'isolation des comptes
(IDOR), les tentatives d'injection SQL, l'extraction de chaque format de document et les fichiers piégés
(extension trompeuse, bombe zip, nom de fichier malveillant), ainsi que le chatbot (streaming, historique,
erreurs).

## Sécurité

- Mots de passe hachés avec argon2id. La session est un jeton aléatoire, conservé haché en base, dans un
  cookie `HttpOnly` et `SameSite=Lax`, et révoqué à la déconnexion. Protection CSRF par double soumission.
- Verrouillage du compte après 5 échecs ; limitation de débit sur la connexion, l'inscription, les analyses
  et le chat.
- Toutes les requêtes SQL sont paramétrées ; chaque accès est filtré par propriétaire ; les identifiants sont
  des UUID.
- En-têtes de sécurité (CSP, `X-Frame-Options`, `nosniff`, `Referrer-Policy`) et `Cache-Control: no-store`
  sur les données médicales. Les erreurs sont génériques : aucune trace interne n'est exposée.
- Le contenu des documents est présenté au modèle comme des données, jamais comme des instructions
  (protection contre l'injection de prompt). La sortie du modèle est validée par schéma puis affichée sans
  HTML brut.
- Les secrets sont dans `backend/.env`, ignoré par Git. Les scripts d'installation npm sont désactivés
  (`.npmrc`) et les versions des dépendances sont figées.

## Structure

```
backend/   API FastAPI (app/), migrations Alembic, tests
frontend/  Interface Next.js (src/app, src/components, src/lib)
design/    Maquettes de référence pour l'interface
legacy/    Ancien prototype BioMedLM (notebooks réparés), conservé pour mémoire
```
