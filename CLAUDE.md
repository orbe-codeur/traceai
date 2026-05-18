# CLAUDE.md — TraceAI

## Ce qu'est TraceAI

TraceAI est une GMAO IA industrielle. Un collègue non-technicien dépose des documents, l'agent travaille seul, le collègue pose des questions et obtient des réponses fiables avec citations.

**Phase 1 — Checklist intelligente**
Upload PDF manuel d'installation. L'IA (Mistral, 3 passes : TOC → chunks → merge) extrait toutes les étapes. Traçabilité complète (qui, quand, note, témoin). Export PV HTML.

**Phase 2 — Machine Wiki Agentique**
Upload documents industriels en vrac. Agent autonome (Hermes Agent, Nous Research) + Wiki LLM (llm-wiki-agent, SamurAIGPT). Construit un wiki structuré par machine, knowledge graph, répond aux questions avec citations.

**Phase B+ — Autonomie Hermes complète**
Background review, context compression, orchestration multi-agent, cron engine, streaming SSE. Agent qui apprend et s'améliore entre les sessions sans intervention.

> Voir `ETAT_DES_LIEUX.md` pour l'analyse critique et la roadmap.
> Voir `PHASE2_FRONTEND.md` pour la spec frontend Phase 2.

---

## Stack technique

| Composant | Technologie |
|---|---|
| Backend | FastAPI (Python 3.11+), `backend/main.py` |
| Frontend | Vue.js 3 Composition API + Vite + Tailwind CSS |
| BDD | SQLite via `sqlite3` standard, requêtes SQL directes, pas d'ORM |
| PDF | PyMuPDF (`import fitz`) |
| LLM raisonnement | Mistral API (`mistral-large-latest`) via `httpx` |
| LLM réflexion/skills/review | Mistral API (`mistral-small-latest`) |
| Embeddings | Mistral Embed API (`mistral-embed`) |
| Vector store | ChromaDB (optionnel — pas encore alimenté Phase B) |
| Streaming | Server-Sent Events (SSE) via FastAPI `StreamingResponse` |
| Pas de | Docker, auth, JWT, notifications email |

---

## Arborescence réelle

```
traceai/
├── backend/
│   ├── main.py               # TOUT le backend FastAPI — Phase 1 + Phase 2 + Phase B+
│   ├── requirements.txt
│   ├── traceai.db            # SQLite auto-créé au démarrage
│   ├── uploads/              # PDFs Phase 1 (gitignored)
│   ├── uploads_phase2/       # Docs Phase 2 par projet (gitignored)
│   ├── wiki/                 # Machine Wiki fichiers markdown par projet
│   │   └── {project_id}/
│   │       ├── SCHEMA.md     # Conventions, tag taxonomy, constructeurs
│   │       ├── index.md      # Catalogue de toutes les pages
│   │       ├── log.md        # Journal append-only (rotation à 500 entrées)
│   │       ├── overview.md   # Synthèse vivante, mise à jour à chaque ingest
│   │       ├── raw/          # Sources immuables (SHA256 pour déduplication)
│   │       ├── sources/      # 1 page résumé par document ingéré
│   │       ├── machines/     # Pages machine
│   │       ├── entities/     # Fournisseurs, pièces, personnes
│   │       ├── concepts/     # Procédures, standards, types de maintenance
│   │       └── syntheses/    # Réponses aux questions sauvegardées
│   ├── graph/                # Knowledge graphs par projet
│   │   └── {project_id}/
│   │       ├── graph.json    # Nodes + edges (EXTRACTED + INFERRED)
│   │       ├── graph.html    # Visualisation vis.js interactive
│   │       └── .cache.json   # Cache SHA256 pour ne reprocesser que les changements
│   ├── skills/               # Skills auto-améliorés par projet
│   │   └── {project_id}/
│   │       └── {skill}.md    # Format Hermes : frontmatter YAML + body markdown
│   ├── cron_output/          # Outputs des jobs cron (markdown par run)
│   │   └── {job_id}_{timestamp}.md
│   ├── agents/               # Agents Phase 2 legacy
│   │   ├── parser.py         # Extraction texte PDF/DOCX/XLSX
│   │   ├── chunker.py        # Découpage par sections techniques
│   │   ├── indexeur.py       # Indexation ChromaDB + SQLite
│   │   ├── compilateur.py    # Machine Wiki legacy
│   │   ├── repondeur.py      # RAG hybride wiki + vecteur
│   │   ├── alertes.py        # Détection contradictions/lacunes
│   │   └── utils.py          # llm_json(), embed_texts()
│   ├── agent_core.py         # Agent principal — boucle Hermes + Mistral tool calling
│   │                         # TraceAIAgent.process() + process_stream() (SSE)
│   ├── orchestrator.py       # Multi-agent — TraceAIOrchestratorAgent + delegate_task
│   ├── background_review.py  # Fork daemon post-tour (review memory + skills)
│   ├── context_compressor.py # Compression contexte long (middle summary)
│   ├── curator.py            # Maintenance skills périodique (merge, improve, archive)
│   ├── cron_engine.py        # Scheduler jobs planifiés (SQLite, tick/60s)
│   ├── wiki_engine.py        # Gestion wiki markdown (init, ingest LLM, lint, health)
│   ├── graph_engine.py       # Knowledge graph (EXTRACTED + INFERRED, vis.js, heal)
│   ├── skills_engine.py      # Système de skills auto-améliorés + nudge post-tour
│   ├── memory_engine.py      # Mémoire persistante par projet (SQLite + FTS5)
│   └── rag_strategies.py     # Stratégies RAG dynamiques par type de document
└── frontend/
    └── src/
        ├── views/
        │   ├── DesktopUploadView.vue      # Accueil + upload PDF Phase 1
        │   ├── DesktopChecklistView.vue   # Checklist 3 volets
        │   ├── DesktopOverviewView.vue    # Vue d'ensemble projet + stats
        │   ├── SummaryView.vue            # Rapport/timeline
        │   └── Phase2IngestView.vue       # Back office wiki (à refondre — voir PHASE2_FRONTEND.md)
        ├── views/mobile/                  # 5 vues mobile adaptatives
        ├── components/
        │   ├── Phase2WikiTab.vue          # Onglet wiki (legacy)
        │   ├── Phase2ChatTab.vue          # Onglet chat RAG (legacy)
        │   └── Phase2AlertsTab.vue        # Onglet alertes (legacy)
        ├── composables/
        │   ├── useBreakpoint.js           # Routing adaptatif mobile/desktop
        │   ├── useExport.js               # Export PV HTML
        │   └── useToast.js                # Toasts non-bloquants
        └── services/api.js                # Axios, baseURL http://localhost:8000
```

---

## Tables SQLite (traceai.db)

### Phase 1
- `projects` — projets avec progression (total_steps, completed_steps)
- `steps` — étapes extraites (title, description, category, is_critical, requires_witness, status, technician_name, note, validated_at)

### Phase 2 — Pipeline legacy
- `documents` — documents ingérés (filename, file_type, sha256, doc_type, status)
- `chunks` — chunks de texte (content, machine_ref, page_ref, embedding_id)
- `wiki_pages` — pages wiki SQLite (title, content_md, page_type)
- `batch_jobs` — jobs d'ingestion background (status, agents_json, logs_json)
- `conversations` / `messages` — historique chat
- `alerts` — alertes détectées (title, description, severity, machine_ref)

### Phase B — Agent
- `project_memory` — mémoire persistante par projet (key, value) + FTS5
- `agent_sessions` — sessions agent avec system_prompt figé (continuité cross-session)

### Phase B+ — Cron
- `cron_jobs` — jobs planifiés (id, project_id, name, mode, prompt, schedule JSON, next_run_at, last_run_at, last_output, enabled)

---

## Endpoints API complets

### Phase 1 — Checklist
```
POST   /api/upload                          → Upload PDF, extraction 3 passes, retourne steps
GET    /api/projects                        → Liste projets + stats
GET    /api/projects/{id}/steps             → Toutes les étapes d'un projet
POST   /api/steps/{id}/validate             → Valider une étape (done/issue/skipped)
GET    /api/projects/{id}/timeline          → Étapes validées par ordre chronologique
GET    /api/projects/{id}/pdf/{page}        → Page PDF en PNG (aperçu)
DELETE /api/projects/{id}                   → Supprimer un projet
POST   /api/projects/{id}/chat              → Chat assistant sur le manuel (Phase 1)
```

### Phase 2 — Pipeline legacy
```
POST   /api/projects/{id}/ingest            → Upload docs, lance pipeline 10 agents background
GET    /api/jobs/{id}/status                → Statut batch job + logs temps réel
GET    /api/projects/{id}/documents         → Documents ingérés
GET    /api/projects/{id}/wiki              → Index wiki pages SQLite
GET    /api/wiki/{id}                       → Contenu d'une page wiki
POST   /api/projects/{id}/wiki-chat         → Chat RAG hybride (wiki + ChromaDB)
GET    /api/projects/{id}/conversations     → Historique conversations
GET    /api/conversations/{id}/messages     → Messages d'une conversation
GET    /api/projects/{id}/alerts            → Alertes actives
PATCH  /api/alerts/{id}/dismiss             → Ignorer une alerte
```

### Phase B — Agent autonome + Wiki LLM
```
POST   /api/projects/{id}/agent-chat        → Chat agent autonome (mode: chat|ingestion|alerte)
POST   /api/projects/{id}/agent-chat/stream → Chat agent en streaming SSE (même modes)
GET    /api/projects/{id}/memory            → Mémoire persistante du projet
GET    /api/projects/{id}/skills            → Skills disponibles pour ce projet

POST   /api/projects/{id}/wiki-ingest       → Ingestion LLM one-call (1 appel Mistral)
GET    /api/projects/{id}/wiki-health       → Health check structurel, zéro LLM, rapide
GET    /api/projects/{id}/wiki-lint         → Lint complet (orphans, broken links, missing entities)
GET    /api/projects/{id}/wiki-overview     → Synthèse vivante overview.md
POST   /api/projects/{id}/wiki-heal         → Auto-génère les pages manquantes (3+ mentions)

POST   /api/projects/{id}/build-graph       → Construit knowledge graph (Pass1 + Pass2 LLM)
GET    /api/projects/{id}/graph             → graph.json (nodes + edges)
GET    /api/projects/{id}/graph.html        → Visualisation vis.js interactive
GET    /api/projects/{id}/graph-lint        → Lint graph-aware (hub stubs, nœuds isolés)
```

### Phase B+ — Orchestration + Cron
```
POST   /api/projects/{id}/orchestrate       → Orchestrateur multi-agent (delegate_task)
POST   /api/projects/{id}/curator           → Passe curator maintenant (sync)

POST   /api/projects/{id}/cron              → Créer un job cron planifié
GET    /api/projects/{id}/cron              → Lister les jobs cron du projet
GET    /api/cron/{job_id}                   → Détails d'un job
DELETE /api/cron/{job_id}                   → Supprimer un job
POST   /api/cron/{job_id}/pause             → Mettre en pause
POST   /api/cron/{job_id}/resume            → Réactiver
POST   /api/cron/{job_id}/trigger           → Déclencher immédiatement
```

### Format réponse agent-chat / orchestrate
```json
{
  "answer": "...",
  "iterations": 3,
  "mode": "chat",
  "needs_clarification": false,
  "question": "",
  "choices": []
}
```

Quand `needs_clarification: true` → l'agent attend une réponse de l'utilisateur.
`choices[]` contient les options suggérées (max 4).

### Événements SSE (agent-chat/stream)
```
data: {"type": "tool_call", "name": "search_wiki"}
data: {"type": "text", "delta": "...token..."}
data: {"type": "done", "iterations": 2, "needs_clarification": false, "choices": []}
data: {"type": "error", "message": "..."}
```

---

## Agent autonome — architecture (Phase B+)

Sources : Hermes Agent (NousResearch, MIT) + llm-wiki-agent (SamurAIGPT, MIT).

### Patterns Hermes intégrés

**Copiés verbatim :**
- `IterationBudget` — budget 15 itérations, thread-safe
- `build_memory_context_block()` — wrap mémoire en `<memory-context>` tags
- `StreamingContextScrubber` — supprime les balises mémoire du stream
- `parse_frontmatter()` — parser YAML frontmatter markdown
- `TOOL_USE_ENFORCEMENT`, `MEMORY_GUIDANCE`, `SKILLS_GUIDANCE` — constantes prompt

**Adaptés :**
- Boucle agent (conversation_loop.py)
- Background review daemon thread (background_review.py)
- Context compressor middle-summary (context_compressor.py)
- Skills system + nudge post-tour (skills_engine.py)
- Cron scheduler (cron/scheduler.py)
- delegate_task multi-agent (delegate_tool.py)
- Curator skills maintenance (curator.py)

### Boucle agent (TraceAIAgent.process)
```
1. Budget reset (15 iterations max)
2. Continuité cross-session : load_session_prompt() depuis SQLite si session_id connu
   Sinon : build system prompt UNE FOIS + save_session_prompt()
3. Prefetch mémoire ONCE avant boucle → injecté dans user message (jamais system)
4. Auto-load skills pertinents → injecté avec la mémoire (match desc/tags vs tâche)
5. while budget.consume():
     Normaliser content Mistral (liste blocs → string plat)
     si tool_calls → exécuter → si ask_clarification → return early
     sinon → réponse finale → break
6. Post-tour :
   - Si budget.used >= 3 → spawn_background_review() (daemon thread)
   - Si len(messages) > 10 et tokens > 20K → compress() (résume middle)
```

### Patterns clés (non-évidents)

**Mémoire dans user message, pas system**
Préserve le prefix cache Mistral. Sans ça, chaque tour rebuild le system prompt (coût × 2).

**ask_clarification tool avec choices[]**
L'agent NE pose JAMAIS de questions en texte libre. Il DOIT appeler le tool.
`TOOL_USE_ENFORCEMENT` contient la règle absolue.
Retour : `{"needs_clarification": true, "question": "...", "choices": ["opt1", "opt2"]}`

**Auto-load skills**
Avant la boucle, `_autoload_skills()` scanne `skills/{project_id}/*.md`, compare les mots de la description/tags contre la tâche. Si match → injecté dans le contexte. Mode alerte exclu.

**Continuité cross-session**
`load_session_prompt(session_id, conn)` → si trouvé, réutilisé sans rebuild.
System prompt figé UNE FOIS par session, jamais modifié mid-session.

### Tools par mode

| Mode | Tools disponibles |
|---|---|
| INGESTION | orient_wiki, ingest_document_llm, classify_doc, parse_pdf, chunk_text, index_chunks, compile_wiki, detect_contradictions, save_memory, create_skill, **ask_clarification** |
| CHAT | search_wiki (graph-aware), search_memory, load_skill, search_chunks, save_synthesis, **ask_clarification** |
| ALERTE | search_wiki, check_deadlines, create_alert |
| ORCHESTRATION | delegate_task, orient_wiki, search_wiki, save_memory, ask_clarification |

### Règle mémoire
Ne mémoriser que les faits durables > 7 jours : constructeur connu, site client, conventions locales.
Ne PAS mémoriser : avancement des jobs, SHA256, sessions passées. Les procédures → skills.

Mots-clés rejetés automatiquement : avancement, job_id, session, sha256, étape en cours, progression, commit, PR #, terminé le.

---

## Background Review (Phase B+)

Adapté de `background_review.py` Hermes (MIT).

**Déclenchement :** `budget.used >= 3` après chaque tour agent.
**Exécution :** thread daemon (non-bloquant pour le thread principal).
**Whitelist stricte :** uniquement `save_memory` + `create_skill`. Tous les autres tools refusés.
**Modèle :** mistral-small (pas large).

3 prompts selon le contexte :
- `_SKILL_REVIEW_PROMPT` — si `budget.used < 5`
- `_MEMORY_REVIEW_PROMPT` — rare, si info durable détectée
- `_COMBINED_REVIEW_PROMPT` — si `budget.used >= 5`

Le review relit la conversation et décide s'il faut créer/mettre à jour un skill ou sauvegarder un fait en mémoire. "Nothing to save" est une réponse valide.

---

## Context Compressor (Phase B+)

Adapté de `context_compressor.py` Hermes (MIT).

**Seuil :** `CONTEXT_THRESHOLD_TOKENS` (défaut : 20 000 tokens, ~4 chars/token).
**Déclenchement :** après chaque tour si `len(messages) > 10`.

Stratégie :
1. Garder `head_pairs=2` premiers échanges (contexte initial)
2. Garder `tail_pairs=4` derniers échanges (contexte récent)
3. Pruner les vieux tool outputs dans le milieu (`[Ancien résultat d'outil supprimé]`)
4. Résumer le milieu avec mistral-small
5. Injecter le résumé avec le marqueur `[RÉSUMÉ DE CONTEXTE — RÉFÉRENCE UNIQUEMENT]`

Fallback sans LLM si l'appel échoue (marqueur texte simple).

---

## Orchestrateur Multi-agent (Phase B+)

Adapté de `delegate_tool.py` Hermes (MIT). Fichier : `orchestrator.py`.

`TraceAIOrchestratorAgent` hérite de `TraceAIAgent`. Override `process()` pour injecter le mode `orchestration` et `_dispatch()` pour gérer `delegate_task`.

**delegate_task** : spawn un `TraceAIAgent` dans `ThreadPoolExecutor` (max 3 workers).
- Contexte enfant **isolé** (pas d'historique parent)
- `SUBAGENT_BLOCKED_TOOLS` : delegate_task (pas de récursion), ask_clarification (pas d'interaction)
- Timeout configurable : `SUBAGENT_TIMEOUT` (défaut 120s)

Endpoint : `POST /api/projects/{id}/orchestrate`

---

## Curator (Phase B+)

Adapté de `curator.py` Hermes (MIT).

**Déclenchement automatique :** tous les `CURATOR_INTERVAL` ingestions (défaut : 10).
**Invariant strict :** jamais de suppression — seulement archive (`archived: true` dans frontmatter).

3 actions possibles :
- `merge` : fusionner 2 skills qui se chevauchent → créer le skill fusionné + archiver les originaux
- `improve_description` : améliorer une description vague ("Use when...")
- `archive` : marquer un skill obsolète

Endpoint synchrone : `POST /api/projects/{id}/curator`

---

## Cron Engine (Phase B+)

Adapté de `cron/jobs.py` + `cron/scheduler.py` Hermes (MIT). Fichier : `cron_engine.py`.

**Stockage :** SQLite table `cron_jobs` (pas de fichier JSON comme Hermes).
**Scheduler :** thread daemon, tick toutes les 60 secondes.
**Anti-injection :** scan des prompts à la création (`_scan_cron_prompt`).

Schedules supportés :
```
"every 30 minutes"  → interval 30 min
"every 2 hours"     → interval 120 min
"every night"       → daily_at 02:00
"daily at 08:00"    → daily_at 08:00
"every week"        → interval 10080 min
"0 2 * * *"         → cron expr (croniter si installé, sinon 24h fallback)
```

Exécution : lance `TraceAIAgent.process()` en thread daemon. Output sauvegardé dans `cron_output/`.

---

## Streaming SSE (Phase B+)

`TraceAIAgent.process_stream()` + `_call_mistral_stream()`.

**Pattern :** Mistral `stream=True` sur la réponse finale + tool_calls status events sur les tours intermédiaires.

**Normalisation content :** Mistral retourne parfois `content` comme liste de blocs (format citations). Normalisé en string plat à **deux endroits** :
- `_run()` ligne ~425 : pour les appels non-streaming
- `_call_mistral_stream()` : `delta["content"]` peut être une liste → même normalisation

Endpoint : `POST /api/projects/{id}/agent-chat/stream`
Media type : `text/event-stream`
Headers : `Cache-Control: no-cache`, `X-Accel-Buffering: no`

---

## Wiki LLM — architecture (Phase B)

Sources : llm-wiki-agent (SamurAIGPT, MIT).

### Ingestion one-call
UN seul appel Mistral-large génère en JSON :
- `source_page` — résumé structuré du document (key claims + citations page par page)
- `machine_pages[]` — pages machine
- `entity_pages[]` — fournisseurs, pièces, personnes
- `concept_pages[]` — procédures, standards, types de maintenance
- `overview_update` — synthèse vivante
- `contradictions[]` — contradictions détectées avec le wiki existant
- `log_entry` — entrée dans log.md

### Limites actuelles du wiki
- Pages en **LLM prose** (pas de tableaux typés avec valeurs vérifiables)
- **Pas de merge** champ par champ — réingestion = réécriture complète
- **ChromaDB non alimenté** par les pages Phase B → recherche sémantique aveugle
- Validé sur 1 seul document (Jenny Compressor Manual)

### Knowledge graph
- **Pass 1 EXTRACTED** — regex `[[wikilinks]]` explicites, zéro LLM
- **Pass 2 INFERRED** — mistral-small, relations sémantiques implicites
- Checkpoint JSONL — SHA256, ne reprocesse que les pages modifiées
- `expand_via_graph()` — enrichit search_wiki (confidence ≥ 0.7)

### Health vs Lint
- **`health_check()`** — zéro LLM, < 50ms → lancer à chaque session
- **`lint_wiki()`** — checks complets → lancer tous les 10-15 ingests

---

## Stratégies RAG dynamiques

| Type de doc | chunk_by | max_size | Particularités |
|---|---|---|---|
| `manual_constructor` | sections (h2/h3) | 1500 | keep_tables, extract_specs |
| `intervention_report` | paragraphs | 800 | extract_fields: date, machine, technicien |
| `technical_datasheet` | none (1 chunk) | 5000 | extract_specs |
| `parts_inventory` | rows | 500 | extract_fields: ref, quantite, machine_ref |
| `scanned_handwritten` | paragraphs | 600 | ocr_required, confidence_threshold: 0.7 |
| `procedure_checklist` | steps | 400 | — |
| `unknown` | paragraphs | 1000 | fallback générique |

---

## Frontend

### Routing adaptatif
`useBreakpoint.js` détecte mobile/desktop. Router injecte la vue adaptée.

### Vues desktop
- `/` — `DesktopUploadView` : accueil, upload PDF, liste projets
- `/project/:id` — `DesktopChecklistView` : checklist 3 volets
- `/project/:id/overview` — `DesktopOverviewView` : stats, progression
- `/project/:id/summary` — `SummaryView` : timeline, export PV
- `/project/:id/wiki-admin` — `Phase2IngestView` : **À REFONDRE** (voir PHASE2_FRONTEND.md)

### Vues mobile
5 vues dédiées dans `views/mobile/`.

---

## Commandes pour lancer

```bash
# Terminal 1 — Backend
cd traceai/backend
./venv/bin/uvicorn main:app --reload --port 8000

# Terminal 2 — Frontend
cd traceai/frontend
npm run dev
# → http://localhost:5173
```

---

## Variables d'environnement (.env)

```
LLM_PROVIDER=mistral
LLM_API_KEY=<clé Mistral>
LLM_MODEL=mistral-large-latest
LLM_MODEL_FAST=mistral-small-latest
EMBEDDING_MODEL=mistral-embed

# Optionnel
CONTEXT_THRESHOLD_TOKENS=20000   # Seuil compression contexte
SUBAGENT_TIMEOUT=120             # Timeout sous-agents (secondes)
CURATOR_INTERVAL=10              # Ingestions entre passes curator
```

---

## Conventions de code

- Python : snake_case, type hints, pas d'ORM
- Vue : Composition API (`<script setup>`), pas d'Options API
- Commentaires en français
- Variables en anglais, textes UI en français
- Pas de Docker, pas d'auth, tout en local

---

## Ce qui n'est PAS encore câblé / fait

### Frontend (priorité absolue)
Tous les endpoints Phase B/B+ sont accessibles **uniquement via curl**. Le front utilise encore le pipeline legacy pour la Phase 2.
Voir `PHASE2_FRONTEND.md` pour la spec complète de refonte.

### Data layer (priorité haute)
- Wiki en LLM prose → à refondre en tableaux typés avec merge champ par champ
- ChromaDB non alimenté par les pages wiki Phase B → recherche sémantique aveugle
- Pas de vérification anti-hallucination (claims numériques non cross-checkés)

### Scale (priorité moyenne)
- Pas de pipeline batch avec checkpoint (ingestion séquentielle uniquement)
- Pas d'on-premise / Ollama (dépendance Mistral cloud)
- Testé sur 1 seul document — comportement multi-documents non validé

### Agents RAG spécialisés (priorité basse — après data layer)
- `WikiRAGAgent`, `ChunkRAGAgent`, `GraphRAGAgent` non construits
- `HermesBrain` routing non construit
- `IngestionPlannerAgent` non construit
