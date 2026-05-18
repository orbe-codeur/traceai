"""
Wiki Engine — TraceAI Phase B.

Gestion du Machine Wiki selon le pattern Karpathy/llm-wiki.

Sources :
  - SamurAIGPT/llm-wiki-agent (MIT) → ingest one-call, health, lint étendu, heal
  - Hermes llm-wiki/SKILL.md        → orientation, sha256, drift, log rotation
  - agent/skill_utils.py (Hermes)   → parse_frontmatter() copié verbatim

Structure wiki étendue :
  wiki/{project_id}/
  ├── SCHEMA.md / index.md / log.md / overview.md
  ├── raw/        sources immuables (SHA256)
  ├── sources/    1 page résumé par document ingéré
  ├── machines/   pages machine (notre extension industrielle)
  ├── entities/   fournisseurs, pièces, personnes
  ├── concepts/   procédures, standards, types de maintenance
  └── syntheses/  réponses aux questions sauvegardées
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

WIKI_BASE = Path(__file__).parent / "wiki"


# ---------------------------------------------------------------------------
# parse_frontmatter — copié verbatim de hermes/agent/skill_utils.py
# ---------------------------------------------------------------------------

def parse_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Parse YAML frontmatter from a markdown string.

    Returns (frontmatter_dict, remaining_body).
    Copié verbatim de Hermes agent/skill_utils.py avec fallback simple.
    """
    frontmatter: dict[str, Any] = {}
    body = content

    if not content.startswith("---"):
        return frontmatter, body

    end_match = re.search(r"\n---\s*\n", content[3:])
    if not end_match:
        return frontmatter, body

    yaml_content = content[3: end_match.start() + 3]
    body = content[end_match.end() + 3:]

    try:
        import yaml
        loader = getattr(yaml, "CSafeLoader", None) or yaml.SafeLoader
        parsed = yaml.load(yaml_content, Loader=loader)
        if isinstance(parsed, dict):
            frontmatter = parsed
    except Exception:
        for line in yaml_content.strip().split("\n"):
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            frontmatter[key.strip()] = value.strip()

    return frontmatter, body


# ---------------------------------------------------------------------------
# Templates (adaptés de llm-wiki/SKILL.md)
# ---------------------------------------------------------------------------

_SCHEMA_TEMPLATE = """# Wiki Schema — {domain}

## Domaine
{domain}

## Conventions
- Noms de fichiers : lowercase, tirets, sans espaces (ex: turbine-orc.md)
- Chaque page machine commence par un frontmatter YAML
- Utiliser `[[wikilinks]]` pour les références croisées (min 2 liens sortants)
- Toujours mettre à jour la date `updated` lors d'une modification
- Chaque nouvelle page doit être ajoutée à index.md
- Chaque action doit être ajoutée à log.md

## Frontmatter obligatoire
```yaml
---
title: Nom de la machine
machine_ref: REF_CONSTRUCTEUR
constructeur: NomConstructeur
created: YYYY-MM-DD
updated: YYYY-MM-DD
type: machine
tags: [tag1, tag2]
sources: [raw/sha256.pdf]
confidence: high | medium | low
contested: false
contradictions: []
---
```

## Tags disponibles
- Équipements : turbine, pompe, compresseur, echangeur, moteur, variateur
- Constructeurs : enogia, grundfos, danfoss, abb, siemens, schneider
- Systèmes : orc, hydraulique, electrique, pneumatique, regulation
- Actions : maintenance-preventive, maintenance-corrective, inspection

## Seuils de création de page
- Créer une page quand une machine apparaît dans 2+ sources OU est centrale dans 1 source
- Ne PAS créer de page pour les mentions passagères
- Diviser une page quand elle dépasse ~200 lignes

## Politique de mise à jour
En cas de contradiction entre sources :
1. Vérifier les dates — les sources récentes prévalent généralement
2. Si contradiction réelle → noter les deux positions avec sources et dates
3. Marquer en frontmatter : `contradictions: [autre-machine]`
4. Signaler pour révision dans le rapport de lint
"""

_INDEX_TEMPLATE = """# Wiki Index

> Catalogue des machines et équipements.
> Lire en PREMIER pour trouver les pages pertinentes.
> Dernière mise à jour : {today} | Total pages : 0

## Machines
<!-- Une ligne par machine : [[machine_ref]] — résumé court -->

"""

# Template étendu avec toutes les sections (llm-wiki-agent pattern)
_INDEX_EXTENDED_TEMPLATE = """# Wiki Index

> Catalogue de toutes les pages. Lire EN PREMIER pour trouver les pages pertinentes.
> Dernière mise à jour : {today} | Total pages : 0

## Vue d'ensemble
- [overview.md](overview.md) — synthèse vivante de toutes les sources

## Sources
<!-- Une ligne par document ingéré : [Titre](sources/slug.md) — résumé -->

## Machines
<!-- Une ligne par machine : [[machine_ref]] — description courte -->

## Entités
<!-- Fournisseurs, pièces, personnes : [[entite]] — rôle -->

## Concepts
<!-- Procédures, standards, types : [[concept]] — définition courte -->

## Synthèses
<!-- Réponses sauvegardées : [question](syntheses/slug.md) — date -->
"""

_LOG_TEMPLATE = """# Wiki Log

> Registre chronologique de toutes les actions wiki. Append-only.
> Format : `## [YYYY-MM-DD] action | sujet`
> Actions : ingest, update, query, lint, create, archive

## [{today}] create | Wiki initialisé
- Domaine : {domain}
- Structure créée : SCHEMA.md, index.md, log.md, raw/, machines/
"""

_MACHINE_PAGE_TEMPLATE = """---
title: {title}
machine_ref: {machine_ref}
constructeur: {constructeur}
created: {today}
updated: {today}
type: machine
tags: [{tags}]
sources: [{sources}]
confidence: medium
contested: false
contradictions: []
---

# {title}

## Spécifications techniques
<!-- Paramètres clés : puissance, pression, débit, température, etc. -->

## Procédures de maintenance

### Maintenance préventive

### Maintenance corrective

## Historique des interventions

## Pièces de rechange

## Machines liées
<!-- [[machine-liee-1]], [[machine-liee-2]] -->

## ⚠️ Contradictions détectées

## ❓ Lacunes identifiées
"""


# ---------------------------------------------------------------------------
# Chemins
# ---------------------------------------------------------------------------

def _wiki_path(project_id: int) -> Path:
    return WIKI_BASE / str(project_id)


def _raw_path(project_id: int) -> Path:
    return _wiki_path(project_id) / "raw"


def _machines_path(project_id: int) -> Path:
    return _wiki_path(project_id) / "machines"


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

def init_wiki(project_id: int, domain: str = "maintenance industrielle") -> None:
    """Crée la structure wiki complète pour un nouveau projet."""
    wiki = _wiki_path(project_id)
    wiki.mkdir(parents=True, exist_ok=True)

    # Sous-dossiers (structure étendue inspirée de llm-wiki-agent)
    for subdir in ("raw", "machines", "sources", "entities", "concepts", "syntheses"):
        (wiki / subdir).mkdir(exist_ok=True)

    today = date.today().isoformat()

    schema = wiki / "SCHEMA.md"
    if not schema.exists():
        schema.write_text(_SCHEMA_TEMPLATE.format(domain=domain), encoding="utf-8")

    index = wiki / "index.md"
    if not index.exists():
        index.write_text(_INDEX_EXTENDED_TEMPLATE.format(today=today), encoding="utf-8")

    log = wiki / "log.md"
    if not log.exists():
        log.write_text(_LOG_TEMPLATE.format(today=today, domain=domain), encoding="utf-8")

    overview = wiki / "overview.md"
    if not overview.exists():
        overview.write_text(
            f"# Vue d'ensemble — {domain}\n\n"
            f"> Synthèse vivante mise à jour à chaque ingestion.\n\n"
            f"*Wiki initialisé le {today}. Aucun document ingéré pour l'instant.*\n",
            encoding="utf-8",
        )

    logger.info("[wiki] Initialisé — projet %d, domaine: %s", project_id, domain)


# ---------------------------------------------------------------------------
# Orientation (pattern llm-wiki : lire AVANT toute opération)
# ---------------------------------------------------------------------------

def orient_agent(project_id: int) -> str:
    """
    Lecture d'orientation obligatoire avant tout traitement.
    Lit SCHEMA.md + index.md + les 40 dernières lignes de log.md.

    Pattern exact de llm-wiki/SKILL.md section 'Resuming an Existing Wiki'.
    """
    wiki = _wiki_path(project_id)
    parts = []

    schema = wiki / "SCHEMA.md"
    if schema.exists():
        parts.append(f"=== SCHEMA.md ===\n{schema.read_text(encoding='utf-8')}")
    else:
        parts.append("=== SCHEMA.md === [absent — wiki non initialisé]")

    index = wiki / "index.md"
    if index.exists():
        parts.append(f"=== index.md ===\n{index.read_text(encoding='utf-8')}")
    else:
        parts.append("=== index.md === [absent]")

    log_tail = get_log_tail(project_id, n_lines=40)
    parts.append(f"=== log.md (40 dernières lignes) ===\n{log_tail}")

    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# SHA256 & déduplication
# ---------------------------------------------------------------------------

def compute_file_hash(filepath: Path) -> str:
    """Calcule le SHA256 du contenu binaire d'un fichier."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def is_already_ingested(project_id: int, file_hash: str) -> bool:
    """
    Vérifie si ce fichier a déjà été traité (par son SHA256).
    Pattern de llm-wiki/SKILL.md : "sha256 lets a future re-ingest skip processing".
    """
    meta_path = _raw_path(project_id) / f"{file_hash}.md"
    return meta_path.exists()


def ingest_raw_file(project_id: int, filepath: Path, doc_type: str,
                    source_url: str = "") -> dict:
    """
    Copie le fichier dans raw/{sha256}.ext et crée raw/{sha256}.md avec métadonnées.
    Retourne {"sha256": ..., "already_ingested": bool, "raw_path": str}.
    """
    init_wiki(project_id)
    file_hash = compute_file_hash(filepath)

    if is_already_ingested(project_id, file_hash):
        logger.info("[wiki] Fichier déjà ingéré (sha256=%s)", file_hash[:12])
        return {
            "sha256": file_hash,
            "already_ingested": True,
            "raw_path": str(_raw_path(project_id) / f"{file_hash}.md"),
        }

    # Copier le fichier brut
    suffix = filepath.suffix.lower()
    raw_file = _raw_path(project_id) / f"{file_hash}{suffix}"
    import shutil
    shutil.copy2(filepath, raw_file)

    # Créer les métadonnées
    today = date.today().isoformat()
    meta_content = f"""---
source_url: {source_url or filepath.name}
original_filename: {filepath.name}
doc_type: {doc_type}
ingested: {today}
sha256: {file_hash}
---

Fichier source ingéré le {today}.
Type : {doc_type}
"""
    meta_path = _raw_path(project_id) / f"{file_hash}.md"
    meta_path.write_text(meta_content, encoding="utf-8")

    log_action(project_id, "ingest", filepath.name,
               f"- sha256: {file_hash[:12]}...\n- doc_type: {doc_type}")

    return {
        "sha256": file_hash,
        "already_ingested": False,
        "raw_path": str(meta_path),
    }


# ---------------------------------------------------------------------------
# Pages machine
# ---------------------------------------------------------------------------

def get_machine_page(project_id: int, machine_ref: str) -> str:
    """Lit la page wiki d'une machine. Retourne '' si absente."""
    page = _machines_path(project_id) / f"{machine_ref}.md"
    if page.exists():
        return page.read_text(encoding="utf-8")
    return ""


def save_machine_page(project_id: int, machine_ref: str, content: str,
                      sources: list[str] | None = None) -> None:
    """
    Écrit ou met à jour la page wiki d'une machine.
    Met à jour index.md et log.md automatiquement.
    """
    init_wiki(project_id)

    # Valider le frontmatter minimum
    fm, body = parse_frontmatter(content)
    if not fm.get("title"):
        raise ValueError(f"Page machine '{machine_ref}' sans titre dans le frontmatter")
    if not fm.get("machine_ref"):
        # Injecter machine_ref si absent
        content = content.replace(
            "---\n",
            f"---\nmachine_ref: {machine_ref}\n",
            1,
        )

    # Mise à jour de la date updated
    today = date.today().isoformat()
    content = re.sub(r"updated: \d{4}-\d{2}-\d{2}", f"updated: {today}", content)

    page_path = _machines_path(project_id) / f"{machine_ref}.md"
    is_new = not page_path.exists()
    page_path.write_text(content, encoding="utf-8")

    # Extraire résumé pour l'index (première ligne non-vide du body)
    summary = _extract_summary(body)
    update_index(project_id, machine_ref, fm.get("title", machine_ref), summary)

    action = "create" if is_new else "update"
    source_list = "\n".join(f"  - {s}" for s in (sources or []))
    log_action(
        project_id, action, machine_ref,
        f"- titre: {fm.get('title', machine_ref)}\n"
        + (f"- sources:\n{source_list}\n" if source_list else ""),
    )

    logger.info("[wiki] Page %s '%s'", action, machine_ref)


def _extract_summary(body: str, max_chars: int = 100) -> str:
    """Extrait la première phrase utile du body pour l'index."""
    for line in body.splitlines():
        line = line.strip()
        if line and not line.startswith("#") and not line.startswith("<!--"):
            return line[:max_chars] + ("…" if len(line) > max_chars else "")
    return ""


def list_machines(project_id: int) -> list[str]:
    """Liste toutes les machine_refs avec une page wiki."""
    machines_dir = _machines_path(project_id)
    if not machines_dir.exists():
        return []
    return [p.stem for p in sorted(machines_dir.glob("*.md"))]


def create_machine_page_template(project_id: int, machine_ref: str,
                                 title: str, constructeur: str = "",
                                 tags: list[str] | None = None,
                                 sources: list[str] | None = None) -> str:
    """Génère un template de page machine avec frontmatter complet."""
    today = date.today().isoformat()
    tags_str = ", ".join(tags or [machine_ref.lower()])
    sources_str = ", ".join(sources or [])
    return _MACHINE_PAGE_TEMPLATE.format(
        title=title,
        machine_ref=machine_ref,
        constructeur=constructeur or "Inconnu",
        today=today,
        tags=tags_str,
        sources=sources_str,
    )


# ---------------------------------------------------------------------------
# Index
# ---------------------------------------------------------------------------

def update_index(project_id: int, machine_ref: str, title: str,
                 summary: str = "") -> None:
    """
    Ajoute ou met à jour la ligne [[machine_ref]] dans index.md.
    Met à jour le compteur 'Total pages' et 'Dernière mise à jour'.
    """
    index_path = _wiki_path(project_id) / "index.md"
    if not index_path.exists():
        init_wiki(project_id)

    content = index_path.read_text(encoding="utf-8")
    today = date.today().isoformat()
    entry = f"[[{machine_ref}]] — {title}"
    if summary:
        entry += f" : {summary}"

    # Remplacer l'entrée existante ou ajouter
    pattern = rf"\[\[{re.escape(machine_ref)}\]\][^\n]*"
    if re.search(pattern, content):
        content = re.sub(pattern, entry, content)
    else:
        # Ajouter sous ## Machines
        machines_section = re.search(r"(## Machines\n)", content)
        if machines_section:
            insert_pos = machines_section.end()
            content = content[:insert_pos] + entry + "\n" + content[insert_pos:]
        else:
            content += f"\n{entry}\n"

    # Mettre à jour les métadonnées du header
    total = len(list_machines(project_id))
    content = re.sub(r"Total pages : \d+", f"Total pages : {total}", content)
    content = re.sub(
        r"Dernière mise à jour : \d{4}-\d{2}-\d{2}",
        f"Dernière mise à jour : {today}",
        content,
    )

    index_path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Log
# ---------------------------------------------------------------------------

def log_action(project_id: int, action: str, subject: str,
               details: str = "") -> None:
    """
    Ajoute une entrée au log wiki (append-only).
    Format : ## [YYYY-MM-DD] action | sujet
    Copié du pattern de llm-wiki/SKILL.md.
    """
    wiki = _wiki_path(project_id)
    log_path = wiki / "log.md"
    if not log_path.exists():
        init_wiki(project_id)

    today = date.today().isoformat()
    entry = f"\n## [{today}] {action} | {subject}\n"
    if details:
        entry += details.rstrip("\n") + "\n"

    with open(log_path, "a", encoding="utf-8") as f:
        f.write(entry)


def get_log_tail(project_id: int, n_lines: int = 40) -> str:
    """Retourne les N dernières lignes du log.md."""
    log_path = _wiki_path(project_id) / "log.md"
    if not log_path.exists():
        return "[log.md absent]"
    lines = log_path.read_text(encoding="utf-8").splitlines()
    return "\n".join(lines[-n_lines:])


# ---------------------------------------------------------------------------
# Lint (adapté de llm-wiki/SKILL.md section 'Lint')
# ---------------------------------------------------------------------------

def lint_wiki(project_id: int) -> dict:
    """
    Vérifie l'intégrité du wiki — toutes les sous-pages (machines, sources, entities, concepts).
    Adapté de llm-wiki/SKILL.md — 12 checks d'intégrité + llm-wiki-agent lint.py.
    """
    wiki = _wiki_path(project_id)
    if not wiki.exists():
        return {"error": "Wiki non initialisé", "total_issues": 0}

    meta_names = {"index.md", "log.md", "overview.md", "SCHEMA.md", "lint-report.md",
                  "health-report.md"}
    all_pages = [
        p for p in wiki.rglob("*.md")
        if p.name not in meta_names
        and not p.name.startswith("log-")
        and p.parent.name != "raw"   # ignorer les métadonnées raw/
    ]
    # Construire le dict nom_relatif → contenu
    pages = {
        p.relative_to(wiki).with_suffix("").as_posix(): p.read_text(encoding="utf-8")
        for p in all_pages
    }
    # Aussi un set des stems pour la résolution rapide des [[wikilinks]]
    stems = {Path(k).name.lower() for k in pages}
    wikilink_re = re.compile(r"\[\[([^\]]+)\]\]")
    report: dict[str, Any] = {
        "orphans": [],
        "broken_links": [],
        "contested": [],
        "low_confidence": [],
        "missing_frontmatter": [],
        "oversized_pages": [],
        "missing_entities": [],
        "sparse_pages": [],
    }

    inbound: dict[str, list[str]] = {name: [] for name in pages}
    mention_counts: dict[str, int] = {}

    for name, content in pages.items():
        fm, body = parse_frontmatter(content)

        # Frontmatter minimum : title OU machine_ref OU type suffit
        if not (fm.get("title") or fm.get("machine_ref") or fm.get("type")):
            report["missing_frontmatter"].append(name)

        if fm.get("contested") is True:
            report["contested"].append(name)

        if fm.get("confidence") == "low":
            report["low_confidence"].append(name)

        if len(content.splitlines()) > 200:
            report["oversized_pages"].append(name)

        # Analyser les wikilinks — résolution par stem (insensible à la casse)
        for link in wikilink_re.findall(body):
            target = link.strip()
            target_lower = target.lower()
            resolved = any(
                Path(k).name.lower() == target_lower or k.lower() == target_lower
                for k in pages
            )
            if resolved:
                for k in pages:
                    if Path(k).name.lower() == target_lower or k.lower() == target_lower:
                        inbound[k].append(name)
                        break
            else:
                report["broken_links"].append({"page": name, "link": target})
                mention_counts[target] = mention_counts.get(target, 0) + 1

    report["orphans"] = [name for name, srcs in inbound.items() if not srcs]

    report["missing_entities"] = [
        e for e, count in mention_counts.items() if count >= 3
    ]

    report["sparse_pages"] = [
        name for name, content in pages.items()
        if len(set(wikilink_re.findall(parse_frontmatter(content)[1]))) < 2
    ]

    total = sum(len(v) for v in report.values() if isinstance(v, list))
    report["total_issues"] = total
    report["total_pages"] = len(pages)

    return report


# ---------------------------------------------------------------------------
# Health check — ZERO appel LLM, lancé à chaque session
# Inspiré de tools/health.py (llm-wiki-agent, MIT)
# ---------------------------------------------------------------------------

def health_check(project_id: int) -> dict:
    """
    Checks structurels déterministes — aucun appel LLM.
    À lancer à chaque session (rapide, ~50ms).

    Checks :
      - Fichiers vides / stubs (body < 100 chars)
      - Pages sur disque absentes de l'index
      - Pages dans l'index absentes sur disque
      - Log coverage : pages sources sans entrée dans log.md
    """
    wiki = _wiki_path(project_id)
    if not wiki.exists():
        return {"error": "Wiki non initialisé", "healthy": False}

    STUB_THRESHOLD = 100
    report: dict = {
        "healthy": True,
        "stubs": [],
        "on_disk_not_in_index": [],
        "in_index_not_on_disk": [],
        "no_log_entry": [],
    }

    # Toutes les pages (hors meta et hors raw/)
    meta_names = {"index.md", "log.md", "overview.md", "SCHEMA.md",
                  "lint-report.md", "health-report.md"}
    all_pages = [
        p for p in wiki.rglob("*.md")
        if p.name not in meta_names
        and not p.name.startswith("log-")
        and p.parent.name != "raw"   # les métadonnées raw/ ne sont pas des pages wiki
    ]

    # Check stubs (inspiré de health.py check_empty_files)
    for p in all_pages:
        try:
            raw = p.read_text(encoding="utf-8")
            _, body = parse_frontmatter(raw)
            if len(body.strip()) < STUB_THRESHOLD:
                report["stubs"].append(str(p.relative_to(wiki)))
        except Exception:
            pass

    # Check sync index (inspiré de health.py check_index_sync)
    index_path = wiki / "index.md"
    index_content = index_path.read_text(encoding="utf-8") if index_path.exists() else ""
    # Supprimer les commentaires HTML (<!-- ... -->) avant d'extraire les liens
    index_no_comments = re.sub(r'<!--.*?-->', '', index_content, flags=re.DOTALL)
    # Extraire liens markdown [Titre](path.md) de l'index (hors commentaires)
    index_links = set(re.findall(r'\[.*?\]\(([^)]+\.md)\)', index_no_comments))
    # Extraire wikilinks [[name]] de l'index (hors commentaires)
    index_wikilinks = set(re.findall(r'\[\[([^\]]+)\]\]', index_no_comments))

    disk_stems = {p.stem.lower() for p in all_pages}
    index_stems = {Path(l).stem.lower() for l in index_links} | {l.lower() for l in index_wikilinks}

    report["on_disk_not_in_index"] = [
        p.stem for p in all_pages
        if p.stem.lower() not in index_stems
        and p.parent.name in ("machines", "entities", "concepts", "sources")
    ]
    # Exclure "overview" du check in_index_not_on_disk — c'est un fichier méta
    # qui est volontairement dans l'index mais pas dans all_pages
    report["in_index_not_on_disk"] = [
        stem for stem in index_stems
        if stem and stem not in disk_stems and stem not in ("overview",)
    ]

    # Check log coverage pour les sources
    sources_dir = wiki / "sources"
    if sources_dir.exists():
        log_content = (wiki / "log.md").read_text(encoding="utf-8") if (wiki / "log.md").exists() else ""
        for src in sources_dir.glob("*.md"):
            if src.stem.lower() not in log_content.lower():
                report["no_log_entry"].append(src.name)

    # Statut global
    issues = sum(len(v) for v in report.values() if isinstance(v, list))
    report["healthy"] = (issues == 0)
    report["total_issues"] = issues

    return report


# ---------------------------------------------------------------------------
# Drift detection (Hermes llm-wiki/SKILL.md)
# ---------------------------------------------------------------------------

def check_drift(project_id: int, filepath: Path) -> dict:
    """
    Compare le SHA256 courant d'un fichier vs celui stocké dans raw/.
    Retourne {"drifted": bool, "old_hash": str, "new_hash": str}.
    """
    new_hash = compute_file_hash(filepath)
    meta_path = _raw_path(project_id) / f"{new_hash}.md"

    if meta_path.exists():
        return {"drifted": False, "new_hash": new_hash, "old_hash": new_hash}

    # Chercher un ancien hash pour ce nom de fichier
    old_hash = None
    for meta in _raw_path(project_id).glob("*.md"):
        try:
            content = meta.read_text(encoding="utf-8")
            if filepath.name in content:
                fm, _ = parse_frontmatter(content)
                old_hash = fm.get("sha256", meta.stem)
                break
        except Exception:
            pass

    return {
        "drifted": old_hash is not None,
        "old_hash": old_hash or "",
        "new_hash": new_hash,
    }


# ---------------------------------------------------------------------------
# Log rotation (Hermes llm-wiki/SKILL.md — 500 entrées max)
# ---------------------------------------------------------------------------

def rotate_log_if_needed(project_id: int, max_entries: int = 500) -> bool:
    """
    Si log.md dépasse max_entries entrées → renomme log-YYYY.md, repart à zéro.
    Retourne True si rotation effectuée.
    """
    log_path = _wiki_path(project_id) / "log.md"
    if not log_path.exists():
        return False

    content = log_path.read_text(encoding="utf-8")
    # Compter les entrées (lignes ## [...])
    entry_count = len(re.findall(r"^## \[", content, re.MULTILINE))

    if entry_count < max_entries:
        return False

    year = date.today().year
    archive = _wiki_path(project_id) / f"log-{year}.md"
    log_path.rename(archive)

    today = date.today().isoformat()
    log_path.write_text(
        f"# Wiki Log\n\n> Rotation effectuée le {today}. "
        f"Historique dans log-{year}.md\n\n",
        encoding="utf-8",
    )
    logger.info("[wiki] Log rotation — projet %d, %d entrées archivées", project_id, entry_count)
    return True


# ---------------------------------------------------------------------------
# Pages étendues (sources, entities, concepts, syntheses)
# Inspiré de llm-wiki-agent ingest.py write_file + update_index
# ---------------------------------------------------------------------------

def _update_index_section(project_id: int, section: str, entry: str) -> None:
    """Ajoute ou met à jour une entrée dans une section de l'index."""
    index_path = _wiki_path(project_id) / "index.md"
    if not index_path.exists():
        init_wiki(project_id)

    content = index_path.read_text(encoding="utf-8")
    today = date.today().isoformat()
    header = f"## {section}"

    if header in content:
        # Vérifier si l'entrée existe déjà (slug ou title)
        entry_slug = re.sub(r'\[.*?\]\(([^)]+)\)', r'\1', entry).strip()
        if entry_slug and entry_slug in content:
            # Remplacer
            content = re.sub(re.escape(entry_slug) + r'[^\n]*', entry.strip(), content)
        else:
            content = content.replace(header + "\n", header + "\n" + entry.strip() + "\n")
    else:
        content += f"\n{header}\n{entry.strip()}\n"

    # Mettre à jour date et compteur
    total = len(re.findall(r'^\s*[-*]', content, re.MULTILINE))
    content = re.sub(r"Dernière mise à jour : \d{4}-\d{2}-\d{2}", f"Dernière mise à jour : {today}", content)
    content = re.sub(r"Total pages : \d+", f"Total pages : {total}", content)

    index_path.write_text(content, encoding="utf-8")


def save_source_page(project_id: int, slug: str, content: str,
                     title: str = "") -> None:
    """Sauvegarde wiki/sources/{slug}.md + update index section Sources."""
    init_wiki(project_id)
    path = _wiki_path(project_id) / "sources" / f"{slug}.md"
    path.write_text(content, encoding="utf-8")
    entry = f"- [{title or slug}](sources/{slug}.md) — résumé du document"
    _update_index_section(project_id, "Sources", entry)
    logger.info("[wiki] Source page '%s' sauvegardée", slug)


def save_entity_page(project_id: int, entity_ref: str, content: str) -> None:
    """Sauvegarde wiki/entities/{entity_ref}.md + update index section Entités."""
    init_wiki(project_id)
    path = _wiki_path(project_id) / "entities" / f"{entity_ref}.md"
    is_new = not path.exists()
    path.write_text(content, encoding="utf-8")
    if is_new:
        entry = f"- [[{entity_ref}]] — entité"
        _update_index_section(project_id, "Entités", entry)
    logger.info("[wiki] Entity page '%s' %s", entity_ref, "créée" if is_new else "mise à jour")


def save_concept_page(project_id: int, concept_ref: str, content: str) -> None:
    """Sauvegarde wiki/concepts/{concept_ref}.md + update index section Concepts."""
    init_wiki(project_id)
    path = _wiki_path(project_id) / "concepts" / f"{concept_ref}.md"
    is_new = not path.exists()
    path.write_text(content, encoding="utf-8")
    if is_new:
        entry = f"- [[{concept_ref}]] — concept"
        _update_index_section(project_id, "Concepts", entry)
    logger.info("[wiki] Concept page '%s' %s", concept_ref, "créée" if is_new else "mise à jour")


def save_synthesis(project_id: int, question: str, content: str) -> str:
    """Sauvegarde une réponse dans wiki/syntheses/{slug}.md. Retourne le slug."""
    init_wiki(project_id)
    today = date.today().isoformat()
    slug = re.sub(r'[^a-z0-9]+', '-', question.lower())[:60].strip('-')
    slug = f"{today}-{slug}"
    path = _wiki_path(project_id) / "syntheses" / f"{slug}.md"
    path.write_text(content, encoding="utf-8")
    entry = f"- [{question[:80]}](syntheses/{slug}.md) — {today}"
    _update_index_section(project_id, "Synthèses", entry)
    log_action(project_id, "query", question[:60], f"- synthèse sauvegardée : {slug}.md")
    return slug


def get_overview(project_id: int) -> str:
    """Retourne le contenu de overview.md, '' si absent."""
    path = _wiki_path(project_id) / "overview.md"
    return path.read_text(encoding="utf-8") if path.exists() else ""


def update_overview(project_id: int, content: str) -> None:
    """Met à jour overview.md."""
    init_wiki(project_id)
    path = _wiki_path(project_id) / "overview.md"
    path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Ingestion LLM one-call — cœur du wiki
# Inspiré de tools/ingest.py (llm-wiki-agent, MIT)
# Adapté : Mistral via llm_json(), prompt industriel français
# ---------------------------------------------------------------------------

_INGEST_SYSTEM = """Tu es un agent expert en maintenance industrielle.
Tu maintiens un Machine Wiki — une base de connaissances structurée sur des équipements industriels.

À chaque nouveau document, tu dois :
1. Créer une page résumé du document (section ## Summary, ## Key Claims, ## Connections)
2. Créer/mettre à jour les pages des machines mentionnées
3. Créer/mettre à jour les pages des entités (fournisseurs, pièces critiques, personnes)
4. Créer/mettre à jour les pages des concepts (procédures, standards, types de maintenance)
5. Mettre à jour la synthèse globale (overview.md) si le document apporte du nouveau
6. Signaler les contradictions avec le wiki existant

Règles critiques :
- Utilise [[wikilinks]] AGGRESSIVEMENT pour lier les pages entre elles
- Chaque claim technique doit citer sa source avec [Fichier, p.X]
- Conserve les valeurs avec unités exactes (250 N·m, 3.5 bar, 80°C)
- Ne jamais inventer une valeur — si absente du doc, le dire
- Réponse en JSON uniquement, sans prose"""

_INGEST_USER_PROMPT = """## État du wiki actuel
{wiki_context}

## Document à ingérer
Fichier : {filename}
Type : {doc_type}
Date : {today}

=== CONTENU DU DOCUMENT ===
{content}
=== FIN DU DOCUMENT ===

Retourne UNIQUEMENT ce JSON (sans balises markdown) :
{{
  "title": "Titre lisible du document",
  "slug": "kebab-case-slug",
  "source_page": "contenu markdown complet pour sources/{{slug}}.md avec frontmatter",
  "machine_pages": [
    {{"ref": "ENO180MTV3", "content": "contenu markdown complet avec frontmatter"}}
  ],
  "entity_pages": [
    {{"ref": "grundfos", "content": "contenu markdown complet avec frontmatter"}}
  ],
  "concept_pages": [
    {{"ref": "maintenance-preventive-orc", "content": "contenu markdown complet avec frontmatter"}}
  ],
  "overview_update": "contenu complet mis à jour pour overview.md, ou null si pas de changement majeur",
  "contradictions": ["description si contradiction détectée avec le wiki existant"],
  "index_entry": "- [Titre](sources/{{slug}}.md) — résumé en une ligne",
  "log_entry": "## [{today}] ingest | Titre\\n- doc_type: {doc_type}\\n- claims clés: ..."
}}"""


def build_wiki_context(project_id: int, max_chars: int = 8000) -> str:
    """
    Construit le contexte wiki pour le prompt d'ingestion.
    Lit index.md + overview.md + 5 dernières pages sources.
    Inspiré de build_wiki_context() dans llm-wiki-agent/ingest.py.
    """
    wiki = _wiki_path(project_id)
    parts = []

    index_path = wiki / "index.md"
    if index_path.exists():
        parts.append(f"## index.md\n{index_path.read_text(encoding='utf-8')[:3000]}")

    overview_path = wiki / "overview.md"
    if overview_path.exists():
        parts.append(f"## overview.md\n{overview_path.read_text(encoding='utf-8')[:2000]}")

    # 3 pages sources récentes pour détection de contradictions
    sources_dir = wiki / "sources"
    if sources_dir.exists():
        recent = sorted(
            sources_dir.glob("*.md"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )[:3]
        for p in recent:
            parts.append(f"## sources/{p.name}\n{p.read_text(encoding='utf-8')[:1000]}")

    context = "\n\n---\n\n".join(parts)
    return context[:max_chars] if len(context) > max_chars else context


def ingest_document_llm(project_id: int, filepath: Path,
                        doc_type: str = "unknown",
                        text_content: str | None = None) -> dict:
    """
    Ingestion LLM one-call — UN seul appel Mistral génère tout le wiki.
    Inspiré de ingest() dans llm-wiki-agent/tools/ingest.py (MIT).

    Adapté pour TraceAI :
    - Utilise llm_json() de agents/utils.py (Mistral via httpx)
    - Prompt industriel français
    - Ajoute machine_pages (notre extension)
    - Sauvegarde via wiki_engine (save_source_page, save_machine_page, etc.)

    Args:
        project_id: ID du projet
        filepath: Chemin du fichier source
        doc_type: Type de document (manual_constructor, intervention_report, etc.)
        text_content: Texte extrait (si déjà parsé), sinon extrait par PyMuPDF

    Returns:
        dict avec title, slug, pages_created, contradictions
    """
    from agents.utils import llm_json

    init_wiki(project_id)
    rotate_log_if_needed(project_id)

    # Extraire le texte si pas fourni
    if text_content is None:
        try:
            import fitz
            doc = fitz.open(str(filepath))
            pages_text = []
            for i, page in enumerate(doc):
                t = page.get_text().strip()
                if t:
                    pages_text.append(f"--- PAGE {i+1} ---\n{t}")
            text_content = "\n".join(pages_text)
        except Exception as e:
            return {"error": f"Impossible d'extraire le texte : {e}"}

    # Tronquer à 12000 chars (contexte Mistral)
    if len(text_content) > 12000:
        text_content = text_content[:12000] + "\n[...tronqué...]"

    today = date.today().isoformat()
    wiki_context = build_wiki_context(project_id)

    prompt = _INGEST_USER_PROMPT.format(
        wiki_context=wiki_context or "(wiki vide — premier document)",
        filename=filepath.name,
        doc_type=doc_type,
        today=today,
        content=text_content,
    )

    logger.info("[wiki] Ingestion LLM one-call — %s", filepath.name)

    try:
        data = llm_json(
            [
                {"role": "system", "content": _INGEST_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            timeout=180.0,
        )
    except Exception as e:
        logger.error("[wiki] Ingestion LLM échouée : %s", e)
        return {"error": str(e)}

    pages_created: list[str] = []

    # Sauvegarder la page source
    slug = data.get("slug", re.sub(r'[^a-z0-9]+', '-', filepath.stem.lower())[:50])
    source_content = data.get("source_page", "")
    if source_content:
        save_source_page(project_id, slug, source_content, data.get("title", slug))
        pages_created.append(f"sources/{slug}.md")

    # Sauvegarder les pages machine
    for mp in data.get("machine_pages", []):
        ref = mp.get("ref", "")
        content = mp.get("content", "")
        if ref and content:
            save_machine_page(project_id, ref, content,
                              sources=[f"sources/{slug}.md"])
            pages_created.append(f"machines/{ref}.md")

    # Sauvegarder les pages entités
    for ep in data.get("entity_pages", []):
        ref = ep.get("ref", "")
        content = ep.get("content", "")
        if ref and content:
            save_entity_page(project_id, ref, content)
            pages_created.append(f"entities/{ref}.md")

    # Sauvegarder les pages concepts
    for cp in data.get("concept_pages", []):
        ref = cp.get("ref", "")
        content = cp.get("content", "")
        if ref and content:
            save_concept_page(project_id, ref, content)
            pages_created.append(f"concepts/{ref}.md")

    # Mettre à jour overview.md si fourni
    overview_content = data.get("overview_update")
    if overview_content:
        update_overview(project_id, overview_content)

    # Log entry
    log_entry = data.get("log_entry", f"## [{today}] ingest | {filepath.name}")
    wiki_log = _wiki_path(project_id) / "log.md"
    existing = wiki_log.read_text(encoding="utf-8") if wiki_log.exists() else ""
    wiki_log.write_text(log_entry.strip() + "\n\n" + existing, encoding="utf-8")

    # Insérer dans raw/ pour déduplication future
    file_hash = compute_file_hash(filepath)
    ingest_raw_file(project_id, filepath, doc_type)

    # Post-ingest validation (inspiré de validate_ingest() dans llm-wiki-agent)
    validation = _validate_after_ingest(project_id, pages_created)

    result = {
        "title": data.get("title", filepath.stem),
        "slug": slug,
        "pages_created": pages_created,
        "contradictions": data.get("contradictions", []),
        "sha256": file_hash,
        "validation": validation,
    }

    logger.info("[wiki] Ingestion terminée — %d pages créées/mises à jour", len(pages_created))
    return result


def _validate_after_ingest(project_id: int, changed_pages: list[str]) -> dict:
    """
    Validation post-ingestion : broken links + pages non-indexées.
    Inspiré de validate_ingest() dans llm-wiki-agent/tools/ingest.py.
    Zero appel LLM.
    """
    wiki = _wiki_path(project_id)
    existing_stems = {
        p.stem.lower()
        for p in wiki.rglob("*.md")
        if p.name not in ("index.md", "log.md", "overview.md")
    }
    index_content = (wiki / "index.md").read_text(encoding="utf-8").lower() \
        if (wiki / "index.md").exists() else ""

    broken_links: list[dict] = []
    unindexed: list[str] = []
    wikilink_re = re.compile(r'\[\[([^\]]+)\]\]')

    for rel_path in changed_pages:
        page_path = wiki / rel_path
        if not page_path.exists():
            continue
        body = page_path.read_text(encoding="utf-8")
        for link in wikilink_re.findall(body):
            if link.lower() not in existing_stems:
                broken_links.append({"page": rel_path, "link": link})
        if page_path.stem.lower() not in index_content:
            unindexed.append(rel_path)

    return {"broken_links": broken_links, "unindexed": unindexed}
