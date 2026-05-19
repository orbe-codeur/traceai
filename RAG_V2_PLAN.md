# TraceAI — Pipeline RAG Agentique Autonome v2

> **Règle fondamentale :** on ne garde un changement que s'il améliore le score
> sur le test set. Pas de technologie sans delta mesuré.

---

## Philosophie

Trois choses font un bon RAG : **chunks propres + embeddings de qualité + reranker**.
Tout le reste est marginal sans données pour le prouver.

Le pipeline est décisionnel, pas fixe. Un agent analyse le lot de documents et
choisit la stratégie. Il s'améliore seul après chaque ingestion.

---

## Architecture

```
N documents hétérogènes
         ↓
[Agent 1 — Arborescence]    zéro LLM · détection structure projet
         ↓
[Agent 2 — Tri]             SHA256 vs DB · déduplication cross-sessions
         ↓
[Agent 3 — Parser]          Docling + PyMuPDF safety net · → .md sur disque
         ↓
[Agent 3.5 — BatchIngestPlanner]  1 appel Mistral small · tout le batch d'un coup
         ↓                        doc_type + machine_ref + contexte projet global
[Agent 4 — Chunker adaptatif]     stratégie par doc_type · overlap calibré
         ↓
[Agent 6 — Indexeur]        Mistral Embed 8192 tok · ChromaDB metadata riche
         ↓
[Agents 7-10]               Compilateur wiki · Qualité · Répondeur · Alertes
         ↓
[Étape 11 — Wiki Phase B]   wiki_engine LLM + graph_engine (non-bloquant)
         ↓
[Retrieval]                 hybrid ChromaDB + SQLite · assess_context loop (⏳)
         ↓
[Learning]                  background review · skills auto-générés
```

---

## Stratégies de chunking par doc_type

| doc_type | Méthode | max_chars | overlap | tokens ~|
|---|---|---|---|---|
| `manual_constructor` | markdown sections | 6 000 | 400 | 1 500 |
| `technical_datasheet` | markdown sections | 8 000 | 500 | 2 000 |
| `intervention_report` | paragraphes | 3 200 | 200 | 800 |
| `parts_inventory` | lignes (20/chunk) | 2 000 | 0 | 500 |
| `procedure_checklist` | étapes numérotées | 1 600 | 150 | 400 |
| `unknown` | paragraphes | 4 000 | 250 | 1 000 |

Tables markdown → chunk atomique (jamais découpé) dans toutes les stratégies.
Limite dure : 30 000 chars (Mistral Embed = 8 192 tokens ≈ 32 000 chars).

---

## Metadata ChromaDB (par chunk)

```json
{
  "doc_id":       "42",
  "page":         "12",
  "machine":      "Jenny W-1.5-H",
  "doc_type":     "manual_constructor",
  "manufacturer": "Jenny",
  "language":     "en",
  "is_table":     "True",
  "chunk_method": "markdown_sections",
  "section":      "Maintenance > Filtre à air > Nettoyage",
  "filename":     "jennycompressormanual.pdf"
}
```

---

## Stack

| Composant | Technologie | Statut |
|---|---|---|
| PDF structuré | **Docling** + PyMuPDF safety net | ✅ Fait |
| Chunking adaptatif | 5 stratégies par doc_type | ✅ Fait |
| BatchIngestPlanner | 1 appel Mistral small / batch | ✅ Fait |
| Embeddings | Mistral Embed (8192 tok, no truncation) | ✅ Fix fait |
| Metadata riche | ChromaDB + SQLite metadata_json | ✅ Fait |
| Réindexation | `reindex.py --project-id N` | ✅ Fait |
| Hybrid retrieval | ChromaDB + SQLite fallback | ✅ Existant |
| Fusion RRF | Reciprocal Rank Fusion | ⏳ Semaine 2 |
| Reranking | BGE-reranker-v2-m3 local | ⏳ Semaine 2 |
| assess_context | Boucle retrieval itérative (max 3) | ⏳ Semaine 2 |
| PDF scanné | Tesseract fallback | 🔮 Si besoin prouvé |
| PDF visuel (P&IDs) | ColPali (GPU) | 🔮 Si besoin prouvé |

---

## Résultats benchmark

| Run | Config | Score | Recall moy | Notes |
|---|---|---|---|---|
| `baseline_pymupdf.json` | PyMuPDF + chunker basique + embed tronqué | — | — | baseline |
| `docling_v2.json` | Docling hybrid + MarkdownChunker | 13/30 (43%) | 46.7% | bug embed [:2000] actif |
| `full_embed_v1.json` | Docling hybrid + fix embed [:30000] | **21/30 (70%)** | **53.4%** | +27% vs docling_v2 |

**Leçon principale :** la troncature artificielle `[:2000]` dans indexeur.py était
le bug le plus impactant — 8 questions récupérées d'un seul fix.

---

## Roadmap

```
FAIT ✅
  ✅ Test set 30 questions           baseline mesurée
  ✅ Docling + PyMuPDF safety net    couverture 100% contenu
  ✅ MarkdownChunker + .md disque    sections, tables atomiques, section_path
  ✅ Fix embed truncation [:2000]    13/30 → 21/30 (+27%)
  ✅ BatchIngestPlanner              1 LLM call / batch, contexte projet global
  ✅ Chunker adaptatif 5 stratégies  par doc_type, overlap calibré
  ✅ SHA256 dedup cross-session      pas de réindexation inutile
  ✅ Pipeline accumulatif            additive, upsert par machine

SEMAINE 2
  ⏳ BGE-reranker-v2-m3 local       mesurer delta sur test set
  ⏳ assess_context tool             boucle retrieval max 3 tours
  ⏳ RRF (ChromaDB + SQLite fusion)  combiner les deux scores

SEMAINE 3
  ⏳ Mapping Excel intelligent       colonnes auto-détectées par BatchPlanner
  ⏳ Alimentation ChromaDB Phase B   wiki pages indexées = meilleure recall

PLUS TARD (data driven)
  🔮 BGE-M3 si test set > Mistral Embed
  🔮 BM25s si références exactes ratent
  🔮 ColPali si scans = vrai sujet

JAMAIS sans delta mesuré
  ❌ Chonkie sur manuels structurés
  ❌ Empilement modèles lourds (4-5GB permanents)
  ❌ Changer le modèle d'embedding sans re-benchmark
```

---

## Benchmark

### Test set : `backend/benchmark/test_set.json`
30 questions Jenny Compressor — valeurs exactes / procédures / compréhension

### Runner
```bash
# Lancer un benchmark
python -u benchmark/runner.py --project-id 7 --output benchmark/results/montest.json

# Comparer deux runs
python -u benchmark/runner.py --compare benchmark/results/A.json benchmark/results/B.json
```

### Réindexation forcée (après modif indexeur)
```bash
python reindex.py --project-id 7
```

### Décision merge
- Delta > +10% → merger
- Delta 0-10%  → investiguer
- Delta négatif → ne pas merger

---

## Ce qu'on ne touche pas

```
Hermes agent loop        → inchangé
Background review        → inchangé (+ crée pipeline skills)
Skills système           → inchangé
Mémoire persistante      → inchangée
ChromaDB project_{id}    → inchangé (même dims 1024)
SQLite                   → inchangé (metadata_json enrichi)
```
