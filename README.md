# TraceAI — Session README

> Document de continuité pour la prochaine session Claude.
> Dernière session : 11 mai 2026

---

## Qu'est-ce que TraceAI ?

Application qui transforme un PDF de manuel industriel en checklist interactive signée.
Un technicien uploade un PDF → l'IA extrait les étapes → il coche ses tâches avec traçabilité (qui, quand, témoin, notes).

---

## Stack

| Couche | Techno |
|---|---|
| Backend | FastAPI (Python 3.11+), un seul fichier `backend/main.py` |
| Frontend | Vue 3 Composition API + Vite + Tailwind CSS |
| BDD | SQLite via `sqlite3` standard (pas d'ORM) |
| PDF | PyMuPDF (`import fitz`) |
| LLM | API Mistral via `httpx` (configurable OpenAI via `.env`) |

---

## Lancer le projet

```bash
# Terminal 1 — Backend
cd traceai/backend
python3 -m venv venv          # une seule fois
./venv/bin/pip install -r requirements.txt
./venv/bin/uvicorn main:app --reload --port 8000

# Terminal 2 — Frontend
cd traceai/frontend
npm install                   # une seule fois
npm run dev
```

Ouvrir **http://localhost:5173**

---

## Configuration `.env`

```env
LLM_PROVIDER=mistral
LLM_API_KEY=<clé Mistral>
LLM_MODEL=mistral-large-latest
```

> ⚠️ Ne jamais partager la clé dans le chat — la regénérer sur console.mistral.ai si exposée.

---

## Ce qui est terminé ✅

### Backend (`backend/main.py`)

- **Agent d'extraction 3 passes** :
  - Pass 1 : analyse la TOC (pages 1-6) → identifie `first_page` / `last_page` utiles
  - Pass 2 : chunks de 8 pages entre ces bornes → extraction parallèle Mistral (sémaphore 3)
  - Pass 3 : déduplique par titre normalisé + tri par page source + renumérotation
  - Validé sur Jenny Compressor Manual (54 pages) : **120 étapes**

- **8 endpoints** :
  - `POST /api/upload` — upload PDF + agent extraction → projet en base
  - `GET /api/projects` — liste projets avec stats
  - `GET /api/projects/{id}/steps` — étapes triées
  - `POST /api/steps/{id}/validate` — validation (done/issue/skipped/active) + témoin
  - `GET /api/projects/{id}/timeline` — journal filtré (non-pending)
  - `GET /api/projects/{id}/pdf/{page}` — page PDF en PNG (DPI 150)
  - `DELETE /api/projects/{id}` — supprime projet + étapes + fichier PDF
  - `POST /api/projects/{id}/chat` — assistant IA sur le manuel (citations page source)

- **Sécurité backend** :
  - Validation MIME + signature `%PDF-` + limite 50 Mo sur l'upload
  - Messages d'erreur génériques (pas de stack trace exposée)
  - CORS restreint aux ports Vite (5173 + 5174), méthodes et headers limités
  - Toutes les requêtes SQL paramétrées (pas d'injection SQL possible)

### Frontend (`frontend/src/`)

#### Design system
- Palette "paper" : `--paper #F4F0E8`, `--teal #1F5F5B`, `--amber #E89A2D`, `--red #C8312D`
- Typographie Geist + Geist Mono (Google Fonts)

#### Composants
- `CatChip.vue` — pastille catégorie (SEC/MEC/HYD/ELEC/TEST/VERIF)
- `Avatar.vue` — initiales technicien colorées
- `ProgressTrack.vue` — progression par catégorie avec segments colorés
- `StepCard.vue` — carte mobile 4 états
- `StepRow.vue` — ligne desktop avec nouveau design :
  - Numéro d'étape `#01` noir bold mono en avant
  - Badge `▲ CRITIQUE` rouge typé
  - Pastille statut explicite `VALIDÉE / EN COURS / PROBLÈME / À FAIRE` en haut à droite
  - Rail unique à gauche (plus de double rail)
  - Méta-ligne séparée par pointillé (avatar + nom + heure)
  - Padding 12px vertical
- `StepDetailPane.vue` — volet détail, formulaire validation, aperçu PDF réel
- `TopBar.vue` — barre dark, breadcrumb, progression, bouton "Exporter PV"
- `LeftRail.vue` — navigation latérale + autres projets
- `ToastContainer.vue` — toasts non-bloquants
- `AssistantPanel.vue` — **NOUVEAU** : drawer IA sur le manuel
  - Colonne gauche : contexte étape active, suggestions contextuelles par catégorie, sections du manuel
  - Colonne droite : bulles de chat, citations `[p.X]` cliquables → ouvre page PDF
  - XSS protégé : `escapeHtml()` avant tout rendu `v-html`
  - Accès : bouton **✦ Assistant** fixe en bas à droite de la checklist desktop

#### Composables
- `useToast.js` — toasts non-bloquants
- `useExport.js` — génère rapport HTML + ouvre impression
- `useBreakpoint.js` — détecte mobile (< 768px) pour le routing adaptatif

#### Vues desktop
- `/` → `DesktopUploadView.vue` — drop zone + liste projets + **recherche temps réel** + écran extraction live
- `/project/:id` → `DesktopChecklistView.vue` — 3-volets + bouton Assistant IA
- `/project/:id/overview` → `DesktopOverviewView.vue` — KPIs + équipe + activité + suppression
- `/project/:id/summary` → `SummaryView.vue` — timeline journal

#### Vues mobile
- `/` → `MobileProjectListView.vue` — projets + **recherche temps réel**
- `/upload` → `MobileUploadView.vue` — formulaire + file picker natif
- `/project/:id` → `MobileChecklistView.vue` — tap-to-expand + validation inline
- `/project/:id/overview` → **`MobileOverviewView.vue` (NOUVEAU)** — KPIs + progression + équipe + activité + modal suppression
- `/project/:id/summary` → `MobileSummaryView.vue` — timeline compacte

#### Routing adaptatif
Router détecte automatiquement le device via `useBreakpoint` et sert la vue appropriée.

#### Recherche projets
Filtre temps réel sur nom + nom de fichier PDF, avec bouton ✕ pour effacer. Présent sur desktop et mobile.

---

## Ce qui reste à faire ❌

### Priorité haute

1. **Règles métier** (à implémenter ensemble) :
   - Note obligatoire si statut = `issue`
   - Témoin ≠ technicien sur les étapes `requires_witness`
   - Une seule étape `active` à la fois (l'ancienne repasse en `pending`)
   - Étapes sécurité à valider en premier
   - Blocage si issue critique non résolue en amont

2. **Authentification basique** :
   - Mot de passe unique en `.env` + middleware FastAPI + session cookie

### Priorité basse

3. **Thèmes alternatifs** (dark `charcoal` + bleu nuit `blueprint`)
   - Variables CSS déjà définies dans `design_handoff_traceai/`
   - Toggle dans la TopBar

4. **Rate limiting** sur `/chat` et `/upload` si déployé (`slowapi`)

---

## Fichiers clés

| Fichier | Rôle |
|---|---|
| `backend/main.py` | Tout le backend + logique agent + chat IA |
| `frontend/src/components/StepDetailPane.vue` | Volet validation + aperçu PDF |
| `frontend/src/components/AssistantPanel.vue` | Chat IA sur le manuel |
| `frontend/src/views/DesktopChecklistView.vue` | Vue principale 3-volets |
| `frontend/src/views/mobile/MobileChecklistView.vue` | Checklist mobile |
| `frontend/src/views/mobile/MobileOverviewView.vue` | Aperçu mobile (nouveau) |
| `frontend/src/composables/useExport.js` | Générateur PV HTML |
| `frontend/src/router/index.js` | Routing adaptatif mobile/desktop |
| `design_handoff_traceai/desktop-screens.jsx` | Référence design desktop (source de vérité) |
| `design_handoff_traceai/screens.jsx` | Référence design mobile |

---

## Problèmes connus

- `backend/traceai.db` contient des projets de test (ids 1-6) — supprimer le fichier et relancer le backend pour repartir propre
- `backend/venv/` — toujours utiliser `./venv/bin/uvicorn` et non `uvicorn` directement
- Le bouton **✦ Assistant** est en `position: fixed` en bas à droite de l'écran (visible depuis la checklist desktop)
