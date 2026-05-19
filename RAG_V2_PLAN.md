# TraceAI — Pipeline RAG Agentique Autonome v2

> **Règle fondamentale :** on ne garde un changement que s'il améliore le score
> sur le test set. Pas de technologie sans delta mesuré.

---

## Philosophie

Trois choses font un bon RAG : **chunks propres + embeddings de qualité + reranker**.
Tout le reste est marginal sans données pour le prouver.

Le pipeline est décisionnel, pas fixe. Un agent analyse chaque document et
choisit sa stratégie. Il s'améliore seul après chaque ingestion.

---

## Architecture

```
100 documents hétérogènes
         ↓
[Phase 0 — DocRecon]        zéro LLM · profil par fichier · 30s
         ↓
[Phase 1 — PlannerAgent]    1 appel Mistral small · stratégie par fichier
         ↓                  mapping colonnes Excel · relations inter-docs
[Phase 2 — Execution]       agents spécialisés en parallèle
         ↓
[Phase 3 — Index]           Mistral Embed Pro · ChromaDB + SQLite
         ↓
[Phase 4 — Retrieval]       hybrid · reranker · assess_context loop
         ↓
[Phase 5 — Learning]        pipeline skills auto-générés
```

---

## Stratégies de chunking par type

| Type | Stratégie | Frontières | LLM |
|---|---|---|---|
| Manuel constructeur | Section Docling | H1/H2/H3 du TOC | Non |
| Tableau specs | 1 chunk = 1 tableau entier | Docling table | Non |
| Rapport Excel | 1 chunk = 1 ligne | Row iterator | Non |
| Datasheet | 1 chunk = 1 tableau | Docling table | Non |
| Procédure | 1 chunk = 1 étape numérotée | Regex numéros | Non |
| PDF scanné | Paragraphes OCR | Tesseract | Non |
| Inconnu | Paragraphes 500t overlap 50t | Regex fallback | Non |

**Jamais Chonkie sur documents structurés** — Docling donne déjà les frontières.

---

## Stack

| Composant | Technologie | Statut |
|---|---|---|
| PDF structuré | **Docling** | ⏳ Semaine 1 |
| PDF scanné | Tesseract fallback | ✅ Existant |
| PDF visuel (P&IDs) | ColPali (GPU) | 🔮 Si besoin prouvé |
| Embeddings | **Mistral Embed Pro** | ⏳ 15$/mois |
| Chunking | Docling sections + règles | ⏳ Semaine 1 |
| Fusion | RRF | ⏳ Semaine 2 |
| Reranking | **BGE-reranker-v2-m3** local | ⏳ Semaine 2 |
| Boucle retrieval | **assess_context** tool | ⏳ Semaine 2 |
| Planning | IngestionPlannerAgent | ⏳ Semaine 3 |
| Self-improving | Pipeline Skills | ⏳ Continu |

---

## Roadmap

```
MAINTENANT
  ✅ Test set 30 questions        mesure la baseline actuelle

SEMAINE 1
  ⏳ Docling remplace PyMuPDF    mesurer le delta
  ⏳ Mistral Pro 15$/mois        fin des 429

SEMAINE 2 (si delta Docling prouvé)
  ⏳ BGE-reranker-v2-m3 local    mesurer le delta
  ⏳ assess_context tool          boucle itérative max 3 tours

SEMAINE 3
  ⏳ IngestionPlannerAgent       stratégie par document
  ⏳ Mapping Excel intelligent    colonnes auto-détectées

PLUS TARD (data driven)
  🔮 BGE-M3 si test set > Mistral Embed
  🔮 BM25s si références exactes ratent
  🔮 ColPali si scans = vrai sujet

JAMAIS sans delta mesuré
  ❌ Chonkie sur manuels structurés
  ❌ Empilement modèles lourds (4-5GB permanents)
```

---

## Benchmark

### Test set : `backend/benchmark/test_set.json`
30 questions sur les documents du projet (valeurs exactes / procédures / cross-docs)

### Runner : `backend/benchmark/runner.py`
```bash
python benchmark/runner.py --project-id 1 --config pymupdf   # baseline
python benchmark/runner.py --project-id 1 --config docling   # après impl
```

### Décision
- Delta > +10% → merger
- Delta 0-10%  → investiguer
- Delta négatif → ne pas merger

---

## Ce qu'on ne touche pas

```
Hermes agent loop        → inchangé
Background review        → inchangé (+ crée pipeline skills)
Skills système           → inchangé (+ pipeline skills)
Mémoire persistante      → inchangée
ChromaDB project_{id}    → inchangé (Mistral Pro = même dims)
SQLite                   → inchangé (+ colonnes metadata enrichies)
```
