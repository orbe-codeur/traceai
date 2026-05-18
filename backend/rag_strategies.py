"""
Stratégies RAG dynamiques — TraceAI Phase B.

Notre innovation (pas dans Hermes) : l'agent choisit la stratégie via
classify_doc(), puis select_strategy() retourne les paramètres de chunking.
Après apprentissage, l'agent peut créer de nouvelles stratégies comme skills.
"""

# ---------------------------------------------------------------------------
# Stratégies connues
# ---------------------------------------------------------------------------

RAG_STRATEGIES: dict[str, dict] = {
    "manual_constructor": {
        "chunk_by": "sections",     # Délimiteurs h2/h3
        "keep_tables": True,        # Ne pas splitter les tableaux techniques
        "min_chunk_size": 200,
        "max_chunk_size": 1500,
        "extract_specs": True,      # Extraction structurée des specs numériques
        "description": "Manuel d'installation ou de maintenance constructeur",
    },
    "intervention_report": {
        "chunk_by": "paragraphs",
        "keep_tables": False,
        "max_chunk_size": 800,
        "extract_fields": ["date", "machine_ref", "technicien", "actions", "pieces"],
        "extract_specs": False,
        "description": "Rapport d'intervention ou de maintenance corrective",
    },
    "technical_datasheet": {
        "chunk_by": "none",         # Une fiche = un seul chunk
        "keep_tables": True,
        "max_chunk_size": 5000,
        "extract_specs": True,
        "description": "Fiche technique ou fiche produit (1–5 pages)",
    },
    "parts_inventory": {
        "chunk_by": "rows",         # Excel ou CSV : une ligne = un chunk
        "keep_tables": True,
        "max_chunk_size": 500,
        "extract_fields": ["ref", "designation", "quantite", "machine_ref", "fournisseur"],
        "description": "Inventaire de pièces détachées (Excel, CSV, tableau PDF)",
    },
    "scanned_handwritten": {
        "chunk_by": "paragraphs",
        "keep_tables": False,
        "max_chunk_size": 600,
        "ocr_required": True,
        "confidence_threshold": 0.7,  # Rejeter les chunks OCR peu fiables
        "description": "Document scanné ou manuscrit nécessitant OCR",
    },
    "procedure_checklist": {
        "chunk_by": "steps",        # Une étape = un chunk
        "keep_tables": True,
        "min_chunk_size": 50,
        "max_chunk_size": 400,
        "extract_specs": False,
        "description": "Checklist de procédure ou gamme opératoire",
    },
    "unknown": {
        "chunk_by": "paragraphs",
        "keep_tables": False,
        "max_chunk_size": 1000,
        "description": "Type de document non identifié — traitement générique",
    },
}

# ---------------------------------------------------------------------------
# Priorités d'ingestion (P1 = plus important, traité en premier)
# ---------------------------------------------------------------------------

INGESTION_PRIORITY: dict[str, int] = {
    "manual_constructor":  1,   # Fondation du wiki
    "technical_datasheet": 2,   # Specs précises
    "parts_inventory":     3,   # Références pièces
    "intervention_report": 4,   # Historique
    "procedure_checklist": 4,
    "scanned_handwritten": 5,
    "unknown":             5,
}


# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------

def select_strategy(doc_type: str) -> dict:
    """Retourne la stratégie de chunking pour un type de document."""
    return RAG_STRATEGIES.get(doc_type, RAG_STRATEGIES["unknown"])


def sort_by_priority(docs: list[dict]) -> list[dict]:
    """Trie des documents par priorité d'ingestion (P1 d'abord)."""
    return sorted(
        docs,
        key=lambda d: INGESTION_PRIORITY.get(d.get("doc_type", "unknown"), 5),
    )


def strategy_to_skill_content(doc_type: str, strategy: dict,
                               observations: str = "") -> str:
    """
    Convertit une stratégie en contenu SKILL.md pour persistance.
    Utilisé par trigger_skill_update() si l'agent découvre un nouveau pattern.
    """
    name = doc_type.replace("_", "-")
    description = strategy.get("description", f"Stratégie pour {doc_type}")
    chunk_by = strategy.get("chunk_by", "paragraphs")
    max_size = strategy.get("max_chunk_size", 1000)
    fields = strategy.get("extract_fields", [])

    return f"""---
name: rag-{name}
description: "Use when traitement de documents de type '{doc_type}'. {description}"
version: 1.0.0
author: TraceAI
metadata:
  hermes:
    tags: [rag, chunking, {doc_type}]
---

# Stratégie RAG — {doc_type}

## Quand utiliser
{description}

## Paramètres de chunking
- Découpage : `{chunk_by}`
- Taille max chunk : {max_size} caractères
- Garder les tableaux : {strategy.get("keep_tables", False)}
- Extraire specs numériques : {strategy.get("extract_specs", False)}
{f"- Champs à extraire : {', '.join(fields)}" if fields else ""}

## Observations terrain
{observations if observations else "Aucune observation enregistrée pour l'instant."}

## Checklist de validation
- [ ] Type de document correctement identifié
- [ ] Chunks de taille cohérente générés
- [ ] Specs numériques extraites si applicable
- [ ] Tableaux préservés intacts
"""


def list_doc_types() -> list[str]:
    """Retourne la liste des types de documents connus."""
    return [k for k in RAG_STRATEGIES if k != "unknown"]
