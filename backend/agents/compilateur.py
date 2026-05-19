"""
Agent 7 — Compilateur / Machine Wiki  ★ LE PLUS IMPORTANT ★
Pour chaque machine identifiée :
1. Récupère tous les chunks liés
2. Appelle LLM pour compiler une page wiki Markdown
3. Sauvegarde dans wiki_pages
4. Génère un index.md + détecte contradictions et lacunes
"""
import json
import logging
import sqlite3
from collections import defaultdict

from .utils import llm_json, update_agent, append_log

logger = logging.getLogger(__name__)

WIKI_SYSTEM = """Tu es un expert en maintenance industrielle. Tu compiles des documents techniques en une page wiki structurée.

Ta mission : à partir des extraits ci-dessous sur la machine "{machine}", génère une page wiki Markdown complète et structurée.

Structure obligatoire :
# {machine}

## Spécifications techniques
(tableau des paramètres clés : puissance, pression, débit, etc.)

## Procédures de maintenance
### Maintenance préventive
### Maintenance corrective

## Historique des interventions
(si des rapports sont mentionnés)

## Pannes récurrentes
(si ≥ 2 occurrences dans les documents)

## Pièces de rechange
(références, fournisseurs)

## Machines liées
(utilise [[Nom de la machine]] pour les liens)

## ⚠️ Contradictions détectées
(valeurs contradictoires entre documents — source 1 vs source 2)

## ❓ Lacunes identifiées
(informations manquantes ou à compléter)

Règles :
- Citer les sources avec [Fichier, p.X] à chaque information importante
- Mettre en gras les valeurs critiques (couples, pressions, températures)
- [[wikilinks]] pour les références croisées entre machines
- Sois exhaustif et précis
- Retourne le Markdown UNIQUEMENT, sans JSON wrapper
"""


def _compile_machine_wiki(machine: str, chunks: list[dict]) -> dict:
    """Génère la page wiki pour une machine via LLM."""
    # Construire le contexte à partir des chunks
    context_parts = []
    for c in chunks[:40]:  # max 40 chunks pour limiter le contexte
        src = f"[{c.get('filename', '?')}"
        if c.get("page_ref"):
            src += f", p.{c['page_ref']}"
        src += "]"
        context_parts.append(f"{src}\n{c['content'][:800]}")

    context = "\n\n---\n\n".join(context_parts)
    if len(context) > 20000:
        context = context[:20000]

    prompt = f"""Extraits de documentation pour la machine "{machine}" :

{context}

Compile une page wiki Markdown complète pour cette machine.
Retourne UNIQUEMENT ce JSON :
{{
  "content_md": "# {machine}\\n\\n...",
  "contradictions": [
    {{"topic": "sujet", "val_a": "valeur source A", "src_a": "fichier p.X", "val_b": "valeur source B", "src_b": "fichier p.Y"}}
  ],
  "gaps": ["Information manquante 1", "Information manquante 2"]
}}
"""

    try:
        result = llm_json(
            [
                {"role": "system", "content": WIKI_SYSTEM.format(machine=machine)},
                {"role": "user", "content": prompt},
            ],
            timeout=120.0,
        )
        return {
            "content_md": result.get("content_md", f"# {machine}\n\n*Compilation en cours...*"),
            "contradictions": result.get("contradictions", []),
            "gaps": result.get("gaps", []),
        }
    except Exception as e:
        logger.error(f"[compl] Wiki '{machine}' échoué: {e}")
        return {
            "content_md": f"# {machine}\n\n*Erreur de compilation: {e}*",
            "contradictions": [],
            "gaps": [],
        }


def run(
    project_id: int,
    job_id: int,
    chunks: list[dict],
    conn: sqlite3.Connection,
) -> list[dict]:
    """
    Groupe les chunks par machine et compile une page wiki pour chacune.
    Utilise TOUS les chunks du projet (pas seulement le batch courant)
    pour que les anciens documents restent visibles après chaque nouvel ajout.
    Génère aussi un index.md.
    Retourne la liste des wiki_pages créées.
    """
    update_agent(conn, job_id, "compl", "running", "")

    # Charger TOUS les chunks du projet (accumulatif)
    all_rows = conn.execute(
        """SELECT c.id, c.content, c.machine_ref, c.page_ref,
                  c.category, c.section_ref, d.filename
           FROM chunks c
           LEFT JOIN documents d ON c.document_id = d.id
           WHERE c.project_id = ?""",
        (project_id,),
    ).fetchall()
    all_chunks = [
        {
            "id": r[0], "content": r[1], "machine_ref": r[2],
            "page_ref": r[3], "category": r[4],
            "section_ref": r[5], "filename": r[6] or "",
        }
        for r in all_rows
    ]
    append_log(conn, job_id, "info", "compl",
               f"Compilation du Machine Wiki — {len(all_chunks)} chunks totaux ({len(chunks)} nouveaux)")

    MIN_CHUNKS = 5   # ignorer les machines avec moins de 5 chunks
    MAX_MACHINES = 10  # max 10 pages wiki

    # Machines qui ont reçu de nouveaux chunks dans ce batch
    new_machines: set[str] = {c.get("machine_ref") or "Général" for c in chunks}

    # Grouper les chunks par machine
    by_machine: dict[str, list[dict]] = defaultdict(list)
    for chunk in all_chunks:
        machine = chunk.get("machine_ref") or "Général"
        by_machine[machine].append(chunk)

    # Fusionner les machines avec peu de chunks dans "Général"
    small = [m for m, c in by_machine.items() if len(c) < MIN_CHUNKS and m != "Général"]
    for m in small:
        by_machine["Général"].extend(by_machine.pop(m))

    # Garder seulement les MAX_MACHINES machines les plus riches
    sorted_machines = sorted(by_machine.items(), key=lambda x: len(x[1]), reverse=True)
    if len(sorted_machines) > MAX_MACHINES:
        overflow = sorted_machines[MAX_MACHINES:]
        for m, cks in overflow:
            by_machine["Général"].extend(cks)
            del by_machine[m]

    wiki_pages: list[dict] = []
    machines = list(by_machine.keys())

    # Machines sans page wiki existante → toujours compiler (nouveau projet ou nouvelle machine)
    existing_wiki = {
        row[0]
        for row in conn.execute(
            "SELECT page_name FROM wiki_pages WHERE project_id=? AND page_type='machine'",
            (project_id,),
        ).fetchall()
    }
    machines_no_wiki = [m for m in machines if m not in existing_wiki]

    # Séparer machines à recompiler (nouvelles données OU pas de wiki) et machines inchangées
    machines_to_compile = [m for m in machines
                           if m in new_machines or m in machines_no_wiki]
    machines_unchanged  = [m for m in machines if m not in machines_to_compile]

    if machines_unchanged:
        append_log(conn, job_id, "info", "compl",
                   f"{len(machines_unchanged)} machine(s) inchangée(s) — wiki conservé : {', '.join(machines_unchanged)}")

    append_log(conn, job_id, "info", "compl",
               f"{len(machines_to_compile)} page(s) wiki à compiler : {', '.join(machines_to_compile) or 'aucune'}")

    # Récupérer les pages existantes des machines inchangées
    for machine in machines_unchanged:
        row = conn.execute(
            "SELECT id, content_md, contradictions_json, gaps_json FROM wiki_pages "
            "WHERE project_id=? AND page_type='machine' AND page_name=?",
            (project_id, machine),
        ).fetchone()
        if row:
            wiki_pages.append({
                "id": row[0], "machine": machine,
                "content_md": row[1] or "",
                "contradictions": json.loads(row[2] or "[]"),
                "gaps": json.loads(row[3] or "[]"),
                "n_chunks": len(by_machine[machine]),
            })

    for i, machine in enumerate(machines_to_compile):
        machine_chunks = by_machine[machine]
        append_log(conn, job_id, "info", "compl", f"Compilation wiki '{machine}' — {len(machine_chunks)} chunks · appel LLM")
        update_agent(conn, job_id, "compl", "running",
                     f"{i}/{len(machines_to_compile)} machines", i / max(len(machines_to_compile), 1))

        wiki = _compile_machine_wiki(machine, machine_chunks)

        # Upsert par machine : supprimer l'ancienne entrée puis réinsérer
        conn.execute(
            "DELETE FROM wiki_pages WHERE project_id=? AND page_type='machine' AND page_name=?",
            (project_id, machine),
        )
        cursor = conn.execute(
            """INSERT INTO wiki_pages
               (project_id, page_type, page_name, title, content_md,
                sources_json, contradictions_json, gaps_json, last_compiled_at)
               VALUES (?, 'machine', ?, ?, ?, '[]', ?, ?, datetime('now'))""",
            (
                project_id,
                machine,
                machine,
                wiki["content_md"],
                json.dumps(wiki["contradictions"], ensure_ascii=False),
                json.dumps(wiki["gaps"], ensure_ascii=False),
            ),
        )
        page_id = cursor.lastrowid
        conn.commit()

        wiki_pages.append({
            "id": page_id,
            "machine": machine,
            "content_md": wiki["content_md"],
            "contradictions": wiki["contradictions"],
            "gaps": wiki["gaps"],
            "n_chunks": len(machine_chunks),
        })

    # Générer l'index
    index_lines = ["# Index — Machine Wiki\n"]
    for p in wiki_pages:
        n_cont = len(p["contradictions"])
        n_gaps = len(p["gaps"])
        badges = ""
        if n_cont:
            badges += f" · ⚠️ {n_cont} contradiction{'s' if n_cont > 1 else ''}"
        if n_gaps:
            badges += f" · ❓ {n_gaps} lacune{'s' if n_gaps > 1 else ''}"
        index_lines.append(f"- [[{p['machine']}]]{badges}")

    index_md = "\n".join(index_lines)
    conn.execute("DELETE FROM wiki_pages WHERE project_id=? AND page_type='index'", (project_id,))
    conn.execute(
        """INSERT INTO wiki_pages
           (project_id, page_type, page_name, title, content_md, last_compiled_at)
           VALUES (?, 'index', 'index', 'Index du Wiki', ?, datetime('now'))""",
        (project_id, index_md),
    )
    conn.commit()

    total_contradictions = sum(len(p["contradictions"]) for p in wiki_pages)
    wikilinks = sum(p["content_md"].count("[[") for p in wiki_pages)
    counter = f"{len(wiki_pages)} pages · {wikilinks} wikilinks · {total_contradictions} contradiction{'s' if total_contradictions != 1 else ''}"
    update_agent(conn, job_id, "compl", "done", counter, 1.0)
    append_log(conn, job_id, "ok", "compl", f"Compilateur ✓ — {counter}")
    return wiki_pages
