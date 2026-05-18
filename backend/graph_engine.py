"""
Graph Engine — TraceAI Phase B.

Knowledge Graph du Machine Wiki : extraction des relations, inférence
sémantique, visualisation vis.js, heal auto-repair.

Sources :
  - SamurAIGPT/llm-wiki-agent/tools/build_graph.py (MIT)
      → Pass 1 EXTRACTED (wikilinks regex, SHA256 cache)
      → Template vis.js HTML (copié et adapté)
      → Checkpoint/resume JSONL pour INFERRED
  - SamurAIGPT/llm-wiki-agent/tools/heal.py (MIT)
      → find_missing_entities(), heal_missing_entities()
  - SamurAIGPT/llm-wiki-agent/tools/query.py (MIT)
      → expand_via_graph() (graph-aware query expansion)

Adapté pour TraceAI :
  - LLM : mistral-small via llm_json() (pas litellm)
  - Chemins : graph/{project_id}/ (par projet)
  - Contexte industriel français dans les prompts
"""

from __future__ import annotations

import json
import logging
import re
from datetime import date
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

GRAPH_BASE = Path(__file__).parent / "graph"
WIKI_BASE = Path(__file__).parent / "wiki"

# Couleurs par type de page (inspiré de build_graph.py TYPE_COLORS)
TYPE_COLORS = {
    "source":    "#4CAF50",   # vert
    "machine":   "#2196F3",   # bleu
    "entity":    "#FF9800",   # orange
    "concept":   "#9C27B0",   # violet
    "synthesis": "#00BCD4",   # cyan
    "unknown":   "#9E9E9E",   # gris
}

EDGE_COLORS = {
    "EXTRACTED": "#555555",
    "INFERRED":  "#FF5722",
    "AMBIGUOUS": "#BDBDBD",
}


# ---------------------------------------------------------------------------
# Chemins
# ---------------------------------------------------------------------------

def _graph_dir(project_id: int) -> Path:
    d = GRAPH_BASE / str(project_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


def _wiki_dir(project_id: int) -> Path:
    return WIKI_BASE / str(project_id)


# ---------------------------------------------------------------------------
# Utilitaires (copiés de build_graph.py)
# ---------------------------------------------------------------------------

def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _all_wiki_pages(project_id: int) -> list[Path]:
    """Toutes les pages wiki sauf les fichiers méta."""
    meta = {"index.md", "log.md", "overview.md", "lint-report.md", "health-report.md"}
    wiki = _wiki_dir(project_id)
    return [
        p for p in wiki.rglob("*.md")
        if p.name not in meta and not p.name.startswith("log-")
    ]


def extract_wikilinks(content: str) -> list[str]:
    """Extrait tous les [[wikilinks]] d'un contenu. Copié de build_graph.py."""
    return list(set(re.findall(r'\[\[([^\]]+)\]\]', content)))


def _extract_type(content: str) -> str:
    """Extrait le champ 'type' du frontmatter."""
    m = re.search(r'^type:\s*(\S+)', content, re.MULTILINE)
    return m.group(1).strip('"\'') if m else "unknown"


def _extract_title(content: str, fallback: str = "") -> str:
    m = re.search(r'^title:\s*"?([^"\n]+)"?', content, re.MULTILINE)
    return m.group(1).strip() if m else fallback


def _page_id(path: Path, wiki_dir: Path) -> str:
    return path.relative_to(wiki_dir).as_posix().replace(".md", "")


def _sha256_short(text: str) -> str:
    import hashlib
    return hashlib.sha256(text.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Cache SHA256 (inspiré de build_graph.py load_cache / save_cache)
# ---------------------------------------------------------------------------

def _load_cache(project_id: int) -> dict:
    cache_file = _graph_dir(project_id) / ".cache.json"
    if cache_file.exists():
        try:
            return json.loads(cache_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def _save_cache(project_id: int, cache: dict) -> None:
    cache_file = _graph_dir(project_id) / ".cache.json"
    cache_file.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")


# ---------------------------------------------------------------------------
# Pass 1 — EXTRACTED edges (déterministe, 0 LLM)
# Copié de build_graph.py build_extracted_edges()
# ---------------------------------------------------------------------------

def build_nodes(project_id: int) -> list[dict]:
    """Construit la liste des nœuds depuis toutes les pages wiki."""
    pages = _all_wiki_pages(project_id)
    wiki = _wiki_dir(project_id)
    nodes = []
    for p in pages:
        content = _read(p)
        node_type = _extract_type(content)
        label = _extract_title(content, fallback=p.stem)
        # Preview : premières lignes du body
        body = re.sub(r"^---\n.*?\n---\n?", "", content, flags=re.DOTALL)
        preview_lines = [l.strip() for l in body.splitlines() if l.strip()]
        preview = " ".join(preview_lines[:3])[:200]
        nodes.append({
            "id": _page_id(p, wiki),
            "label": label,
            "type": node_type,
            "color": TYPE_COLORS.get(node_type, TYPE_COLORS["unknown"]),
            "path": str(p.relative_to(Path(__file__).parent)),
            "preview": preview,
        })
    return nodes


def build_extracted_edges(project_id: int) -> list[dict]:
    """
    Pass 1 : edges EXTRACTED depuis les [[wikilinks]] explicites.
    Déterministe, zéro appel LLM.
    Copié de build_graph.py build_extracted_edges().
    """
    pages = _all_wiki_pages(project_id)
    wiki = _wiki_dir(project_id)

    # Map stem → page_id pour résolution des liens
    stem_map = {p.stem.lower(): _page_id(p, wiki) for p in pages}

    edges = []
    seen: set[tuple[str, str]] = set()

    for p in pages:
        content = _read(p)
        src = _page_id(p, wiki)
        for link in extract_wikilinks(content):
            target = stem_map.get(link.lower())
            if target and target != src:
                key = (src, target)
                if key not in seen:
                    seen.add(key)
                    edges.append({
                        "id": f"{src}->{target}:EXTRACTED",
                        "from": src,
                        "to": target,
                        "type": "EXTRACTED",
                        "color": EDGE_COLORS["EXTRACTED"],
                        "confidence": 1.0,
                        "title": "Lien explicite [[wikilink]]",
                    })
    return edges


# ---------------------------------------------------------------------------
# Pass 2 — INFERRED edges (LLM, checkpoint/resume)
# Adapté de build_graph.py build_inferred_edges() → mistral-small
# ---------------------------------------------------------------------------

def _load_checkpoint(project_id: int) -> tuple[list[dict], set[str]]:
    """Charge le checkpoint JSONL des edges déjà inférés."""
    checkpoint_file = _graph_dir(project_id) / ".inferred_edges.jsonl"
    edges, completed = [], set()
    if not checkpoint_file.exists():
        return edges, completed
    for line in checkpoint_file.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
            completed.add(record["page_id"])
            for e in record.get("edges", []):
                rel_type = e.get("type", "INFERRED")
                edges.append({
                    "id": e.get("id", f"{e['from']}->{e['to']}:{rel_type}"),
                    "from": e["from"],
                    "to": e["to"],
                    "type": rel_type,
                    "title": e.get("relationship", ""),
                    "color": EDGE_COLORS.get(rel_type, EDGE_COLORS["INFERRED"]),
                    "confidence": float(e.get("confidence", 0.7)),
                })
        except (json.JSONDecodeError, KeyError):
            continue
    return edges, completed


def _append_checkpoint(project_id: int, page_id_str: str, edges: list[dict]) -> None:
    """Ajoute les edges d'une page au checkpoint JSONL."""
    checkpoint_file = _graph_dir(project_id) / ".inferred_edges.jsonl"
    record = {
        "page_id": page_id_str,
        "edges": edges,
        "ts": date.today().isoformat(),
    }
    with open(checkpoint_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def build_inferred_edges(project_id: int,
                          existing_edges: list[dict],
                          resume: bool = True) -> list[dict]:
    """
    Pass 2 : edges INFERRED par LLM pour les relations sémantiques implicites.
    Utilise mistral-small (rapide, moins cher).
    Checkpoint/resume JSONL — ne reprocesse que les pages modifiées.
    Adaptée de build_graph.py build_inferred_edges().
    """
    from agents.utils import llm_json

    pages = _all_wiki_pages(project_id)
    wiki = _wiki_dir(project_id)
    cache = _load_cache(project_id)

    checkpoint_edges, completed_ids = [], set()
    if resume:
        checkpoint_edges, completed_ids = _load_checkpoint(project_id)
        if completed_ids:
            logger.info("[graph] Checkpoint: %d pages déjà traitées", len(completed_ids))

    new_edges = list(checkpoint_edges)

    # Pages à traiter (exclure celles déjà dans le checkpoint et non-modifiées)
    to_process = []
    for p in pages:
        pid = _page_id(p, wiki)
        content = _read(p)
        h = _sha256_short(content)
        entry = cache.get(str(p))

        if pid in completed_ids:
            continue
        if isinstance(entry, dict) and entry.get("hash") == h:
            # Page non modifiée, utiliser le cache
            for rel in entry.get("edges", []):
                rel_type = rel.get("type", "INFERRED")
                new_edges.append({
                    "id": f"{pid}->{rel['to']}:{rel_type}",
                    "from": pid,
                    "to": rel["to"],
                    "type": rel_type,
                    "title": rel.get("relationship", ""),
                    "color": EDGE_COLORS.get(rel_type, EDGE_COLORS["INFERRED"]),
                    "confidence": float(rel.get("confidence", 0.7)),
                })
        else:
            to_process.append(p)

    if not to_process:
        logger.info("[graph] Aucune page modifiée — inférence ignorée")
        return new_edges

    logger.info("[graph] Inférence LLM pour %d pages...", len(to_process))

    # Résumé de tous les nœuds pour le contexte LLM
    node_list = "\n".join(
        f"- {_page_id(p, wiki)} ({_extract_type(_read(p))})"
        for p in pages
    )

    for p in to_process:
        content = _read(p)[:1500]
        pid = _page_id(p, wiki)
        h = _sha256_short(_read(p))

        prompt = f"""Tu analyses une page d'un wiki de maintenance industrielle.
Identifie les relations IMPLICITES (non déjà exprimées par des [[wikilinks]]) avec d'autres pages.

Page analysée : {pid}
Contenu :
{content}

Pages disponibles dans le wiki :
{node_list}

Retourne UNIQUEMENT ce JSON :
{{
  "edges": [
    {{"to": "page-id", "relationship": "description courte", "confidence": 0.0-1.0, "type": "INFERRED ou AMBIGUOUS"}}
  ]
}}

Règles :
- confidence >= 0.7 → INFERRED, < 0.7 → AMBIGUOUS
- Ne pas répéter les [[wikilinks]] déjà explicites
- Retourner {{"edges": []}} si aucune relation implicite trouvée
- Uniquement les pages de la liste ci-dessus"""

        page_edges: list[dict] = []
        try:
            import os
            model_fast = os.getenv("LLM_MODEL_FAST", "mistral-small-latest")
            result = llm_json(
                [{"role": "user", "content": prompt}],
                timeout=60.0,
                model_override=model_fast,
            )
            valid_ids = {_page_id(p2, wiki) for p2 in pages}
            for e in result.get("edges", []):
                if not isinstance(e, dict) or "to" not in e:
                    continue
                if e["to"] not in valid_ids or e["to"] == pid:
                    continue
                rel_type = e.get("type", "INFERRED")
                confidence = float(e.get("confidence", 0.7))
                edge = {
                    "id": f"{pid}->{e['to']}:{rel_type}",
                    "from": pid,
                    "to": e["to"],
                    "type": rel_type,
                    "title": e.get("relationship", ""),
                    "color": EDGE_COLORS.get(rel_type, EDGE_COLORS["INFERRED"]),
                    "confidence": confidence,
                }
                page_edges.append(edge)
                new_edges.append(edge)

            # Sauvegarder checkpoint
            _append_checkpoint(project_id, pid, page_edges)

            # Mettre à jour cache SHA256
            cache[str(p)] = {
                "hash": h,
                "edges": [
                    {"to": e["to"], "type": e["type"],
                     "relationship": e["title"], "confidence": e["confidence"]}
                    for e in page_edges
                ],
            }
        except Exception as ex:
            logger.debug("[graph] Inférence échouée pour '%s': %s", pid, ex)

    _save_cache(project_id, cache)
    return new_edges


# ---------------------------------------------------------------------------
# Graphe complet
# ---------------------------------------------------------------------------

def build_graph(project_id: int, infer: bool = True) -> dict:
    """
    Construit le graphe complet (nodes + edges) et le sauvegarde dans graph.json.
    Optionnellement lance l'inférence LLM (Pass 2).
    """
    logger.info("[graph] Construction du graphe — projet %d (infer=%s)", project_id, infer)

    nodes = build_nodes(project_id)
    extracted = build_extracted_edges(project_id)

    if infer and nodes:
        inferred = build_inferred_edges(project_id, extracted)
    else:
        inferred = []

    # Dédupliquer les edges
    all_edges_map: dict[str, dict] = {}
    for e in extracted + inferred:
        if e["id"] not in all_edges_map:
            all_edges_map[e["id"]] = e

    graph = {
        "nodes": nodes,
        "edges": list(all_edges_map.values()),
        "meta": {
            "project_id": project_id,
            "built_at": date.today().isoformat(),
            "total_nodes": len(nodes),
            "total_edges": len(all_edges_map),
            "extracted_edges": len(extracted),
            "inferred_edges": len(inferred),
        },
    }

    graph_path = _graph_dir(project_id) / "graph.json"
    graph_path.write_text(json.dumps(graph, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("[graph] Graphe sauvegardé — %d nœuds, %d edges", len(nodes), len(all_edges_map))

    # Générer HTML automatiquement
    generate_graph_html(project_id, graph)

    return graph


def load_graph(project_id: int) -> dict | None:
    """Charge graph.json si existant."""
    graph_path = _graph_dir(project_id) / "graph.json"
    if not graph_path.exists():
        return None
    try:
        return json.loads(graph_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, IOError):
        return None


# ---------------------------------------------------------------------------
# Visualisation vis.js HTML
# Copié et adapté de build_graph.py (llm-wiki-agent, MIT)
# ---------------------------------------------------------------------------

_VIS_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Machine Wiki — Graphe Projet {project_id}</title>
<script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Segoe UI', sans-serif; background: #1a1a1a; color: #eee; }}
  #header {{ padding: 12px 20px; background: #111; border-bottom: 1px solid #333;
             display: flex; align-items: center; gap: 16px; }}
  #header h1 {{ font-size: 16px; font-weight: 600; color: #fff; }}
  #stats {{ font-size: 12px; color: #888; }}
  #legend {{ display: flex; gap: 12px; margin-left: auto; flex-wrap: wrap; }}
  .legend-item {{ display: flex; align-items: center; gap: 5px; font-size: 11px; }}
  .legend-dot {{ width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }}
  #container {{ width: 100%; height: calc(100vh - 50px); }}
  #mynetwork {{ width: 100%; height: 100%; }}
  #tooltip {{ position: fixed; background: #222; border: 1px solid #444; border-radius: 4px;
              padding: 10px 14px; font-size: 12px; max-width: 280px; z-index: 100;
              display: none; pointer-events: none; }}
  #tooltip .t-title {{ font-weight: 600; color: #fff; margin-bottom: 4px; }}
  #tooltip .t-type {{ color: #888; font-size: 11px; margin-bottom: 6px; }}
  #tooltip .t-preview {{ color: #ccc; line-height: 1.4; }}
  #controls {{ position: fixed; bottom: 16px; right: 16px; display: flex; gap: 8px; }}
  .ctrl-btn {{ background: #333; border: 1px solid #555; color: #eee; padding: 6px 12px;
               border-radius: 3px; cursor: pointer; font-size: 12px; }}
  .ctrl-btn:hover {{ background: #444; }}
</style>
</head>
<body>
<div id="header">
  <h1>Machine Wiki — Knowledge Graph</h1>
  <span id="stats">{total_nodes} nœuds · {total_edges} liens</span>
  <div id="legend">
    <div class="legend-item"><div class="legend-dot" style="background:#4CAF50"></div>Source</div>
    <div class="legend-item"><div class="legend-dot" style="background:#2196F3"></div>Machine</div>
    <div class="legend-item"><div class="legend-dot" style="background:#FF9800"></div>Entité</div>
    <div class="legend-item"><div class="legend-dot" style="background:#9C27B0"></div>Concept</div>
    <div class="legend-item"><div class="legend-dot" style="background:#00BCD4"></div>Synthèse</div>
    <div class="legend-item"><div class="legend-dot" style="background:#FF5722; border-radius:0"></div>Inféré</div>
  </div>
</div>
<div id="container"><div id="mynetwork"></div></div>
<div id="tooltip"><div class="t-title" id="tt-title"></div><div class="t-type" id="tt-type"></div><div class="t-preview" id="tt-preview"></div></div>
<div id="controls">
  <button class="ctrl-btn" onclick="network.fit()">Recentrer</button>
  <button class="ctrl-btn" onclick="togglePhysics()">Physique</button>
</div>
<script>
const graphData = {graph_json};
const nodes = new vis.DataSet(graphData.nodes.map(n => ({{
  id: n.id, label: n.label.length > 25 ? n.label.slice(0,25)+'…' : n.label,
  color: {{ background: n.color, border: n.color, highlight: {{ background: '#fff', border: n.color }} }},
  font: {{ color: '#eee', size: 12 }},
  title: n.preview,
  shape: n.type === 'machine' ? 'box' : n.type === 'source' ? 'diamond' : 'dot',
  size: n.type === 'machine' ? 18 : 14,
  _meta: n,
}})));
const edges = new vis.DataSet(graphData.edges.map(e => ({{
  id: e.id, from: e.from, to: e.to,
  color: {{ color: e.color, opacity: e.type === 'AMBIGUOUS' ? 0.35 : 0.8 }},
  width: e.type === 'EXTRACTED' ? 2 : 1,
  dashes: e.type === 'AMBIGUOUS',
  title: e.title || e.type,
  arrows: {{ to: {{ enabled: true, scaleFactor: 0.6 }} }},
}})));
const container = document.getElementById('mynetwork');
const options = {{
  physics: {{ enabled: true, stabilization: {{ iterations: 120 }},
    barnesHut: {{ gravitationalConstant: -8000, springLength: 120, damping: 0.2 }} }},
  interaction: {{ hover: true, tooltipDelay: 100, hideEdgesOnDrag: true }},
}};
const network = new vis.Network(container, {{ nodes, edges }}, options);
let physicsOn = true;
function togglePhysics() {{
  physicsOn = !physicsOn;
  network.setOptions({{ physics: {{ enabled: physicsOn }} }});
}}
const tooltip = document.getElementById('tooltip');
network.on('hoverNode', params => {{
  const n = nodes.get(params.node);
  if (!n) return;
  document.getElementById('tt-title').textContent = n._meta.label;
  document.getElementById('tt-type').textContent = n._meta.type;
  document.getElementById('tt-preview').textContent = n._meta.preview || '';
  tooltip.style.display = 'block';
  tooltip.style.left = (params.event.pageX + 12) + 'px';
  tooltip.style.top = (params.event.pageY - 20) + 'px';
}});
network.on('blurNode', () => tooltip.style.display = 'none');
network.on('stabilizationIterationsDone', () => network.setOptions({{ physics: {{ enabled: false }} }}));
</script>
</body>
</html>"""


def generate_graph_html(project_id: int, graph: dict | None = None) -> Path:
    """
    Génère graph.html avec vis.js.
    Inspiré de build_graph.py (llm-wiki-agent, MIT).
    """
    if graph is None:
        graph = load_graph(project_id)
    if not graph:
        graph = {"nodes": [], "edges": [], "meta": {}}

    meta = graph.get("meta", {})
    html = _VIS_HTML_TEMPLATE.format(
        project_id=project_id,
        total_nodes=meta.get("total_nodes", len(graph.get("nodes", []))),
        total_edges=meta.get("total_edges", len(graph.get("edges", []))),
        graph_json=json.dumps(graph, ensure_ascii=False),
    )

    html_path = _graph_dir(project_id) / "graph.html"
    html_path.write_text(html, encoding="utf-8")
    logger.info("[graph] HTML généré : %s", html_path)
    return html_path


# ---------------------------------------------------------------------------
# Query expansion via graphe
# Inspiré de query.py expand_via_graph() (llm-wiki-agent, MIT)
# ---------------------------------------------------------------------------

def expand_via_graph(project_id: int, page_ids: list[str],
                     min_confidence: float = 0.7) -> list[str]:
    """
    Trouve les voisins des pages données dans le graphe.
    Utilisé par agent_core search_wiki pour enrichir les résultats.
    Inspiré de query.py find_relevant_pages() + graph expansion.
    """
    graph = load_graph(project_id)
    if not graph:
        return []

    input_set = set(page_ids)
    neighbors: set[str] = set()

    for edge in graph.get("edges", []):
        if edge.get("confidence", 0) < min_confidence:
            continue
        src, tgt = edge.get("from", ""), edge.get("to", "")
        if src in input_set and tgt not in input_set:
            neighbors.add(tgt)
        elif tgt in input_set and src not in input_set:
            neighbors.add(src)

    return list(neighbors)


# ---------------------------------------------------------------------------
# Détection communautés (optionnelle — NetworkX)
# Inspiré de build_graph.py community detection
# ---------------------------------------------------------------------------

def detect_communities(project_id: int) -> dict[str, int]:
    """
    Détecte les communautés dans le graphe (clustering).
    Retourne {node_id: community_id}.
    Graceful degradation si NetworkX absent.
    """
    try:
        import networkx as nx
    except ImportError:
        logger.debug("[graph] NetworkX absent — communautés non calculées")
        return {}

    graph = load_graph(project_id)
    if not graph:
        return {}

    G = nx.Graph()
    for node in graph.get("nodes", []):
        G.add_node(node["id"])
    for edge in graph.get("edges", []):
        if edge.get("confidence", 0) >= 0.7:
            G.add_edge(edge["from"], edge["to"])

    try:
        from networkx.algorithms import community as nx_community
        communities = nx_community.louvain_communities(G, seed=42)
        result = {}
        for i, comm in enumerate(communities):
            for node_id in comm:
                result[node_id] = i
        return result
    except Exception as e:
        logger.debug("[graph] Détection communautés échouée: %s", e)
        return {}


# ---------------------------------------------------------------------------
# Heal — auto-repair des entités manquantes
# Copié et adapté de tools/heal.py (llm-wiki-agent, MIT)
# ---------------------------------------------------------------------------

def find_missing_entities(project_id: int, min_mentions: int = 3) -> list[str]:
    """
    Entités mentionnées min_mentions+ fois via [[wikilinks]] sans page propre.
    Copié de lint.py find_missing_entities() (llm-wiki-agent, MIT).
    """
    pages = _all_wiki_pages(project_id)
    wiki = _wiki_dir(project_id)
    existing_stems = {p.stem.lower() for p in pages}
    mention_counts: dict[str, int] = {}

    for p in pages:
        content = _read(p)
        for link in extract_wikilinks(content):
            if link.lower() not in existing_stems:
                mention_counts[link] = mention_counts.get(link, 0) + 1

    return [name for name, count in mention_counts.items() if count >= min_mentions]


def _search_entity_context(project_id: int, entity: str,
                            max_pages: int = 10) -> list[str]:
    """
    Trouve les passages où l'entité est mentionnée dans le wiki.
    Inspiré de heal.py search_sources().
    """
    pages = _all_wiki_pages(project_id)
    contexts = []
    for p in pages:
        content = _read(p)
        if entity.lower() in content.lower():
            # Extraire les paragraphes qui mentionnent l'entité
            for para in content.split("\n\n"):
                if entity.lower() in para.lower():
                    contexts.append(f"[{p.stem}] {para[:400]}")
                    break
        if len(contexts) >= max_pages:
            break
    return contexts


def heal_missing_entities(project_id: int) -> list[str]:
    """
    Génère automatiquement les pages d'entités manquantes via LLM.
    Copié et adapté de tools/heal.py heal_missing_entities() (llm-wiki-agent, MIT).

    Utilise mistral-small (rapide, moins cher).
    """
    from agents.utils import llm_json
    import os

    missing = find_missing_entities(project_id)
    if not missing:
        logger.info("[graph] Aucune entité manquante — wiki complet")
        return []

    logger.info("[graph] %d entités manquantes à générer", len(missing))
    created = []
    model_fast = os.getenv("LLM_MODEL_FAST", "mistral-small-latest")

    for entity in missing:
        contexts = _search_entity_context(project_id, entity)
        context_text = "\n\n".join(contexts[:8])

        prompt = f"""Tu complètes un wiki de maintenance industrielle.
Crée une page pour l'entité "{entity}" en te basant sur les contextes où elle apparaît.

Contextes :
{context_text or "(aucun contexte trouvé)"}

Format de réponse — retourne UNIQUEMENT ce JSON :
{{
  "content": "---\\ntitle: \\"{entity}\\"\\ntype: entity\\ntags: []\\nsources: []\\n---\\n\\n# {entity}\\n\\n[contenu de la page]"
}}

Le contenu doit inclure :
- Ce qu'est cette entité dans le contexte industriel
- Son rôle / ses caractéristiques clés
- Au moins 2 [[wikilinks]] vers d'autres pages
"""
        try:
            result = llm_json(
                [{"role": "user", "content": prompt}],
                timeout=60.0,
                model_override=model_fast,
            )
            content = result.get("content", "")
            if content:
                from wiki_engine import save_entity_page
                entity_ref = re.sub(r'[^a-z0-9]+', '-', entity.lower()).strip('-')
                save_entity_page(project_id, entity_ref, content)
                created.append(f"entities/{entity_ref}.md")
                logger.info("[graph] Page entité créée : %s", entity_ref)
        except Exception as e:
            logger.warning("[graph] Heal échoué pour '%s': %s", entity, e)

    return created


# ---------------------------------------------------------------------------
# Rapport lint graph-aware
# Inspiré de lint.py check_hub_stubs + check_fragile_bridges (llm-wiki-agent)
# ---------------------------------------------------------------------------

def graph_lint(project_id: int) -> dict:
    """
    Checks graph-aware : hub stubs, ponts fragiles, communities isolées.
    Nécessite graph.json (lancer build_graph d'abord).
    Inspiré de lint.py run_lint() graph-aware section (llm-wiki-agent, MIT).
    """
    import statistics

    graph = load_graph(project_id)
    if not graph or not graph.get("nodes"):
        return {"error": "Pas de graphe — lancer build_graph d'abord"}

    nodes = graph["nodes"]
    edges = graph["edges"]

    # Degré de chaque nœud
    degrees: dict[str, int] = {n["id"]: 0 for n in nodes}
    for e in edges:
        degrees[e["from"]] = degrees.get(e["from"], 0) + 1
        degrees[e["to"]] = degrees.get(e["to"], 0) + 1

    report: dict = {
        "hub_stubs": [],
        "isolated_nodes": [],
        "low_degree_nodes": [],
    }

    # Hub stubs : nœuds très connectés mais contenu court
    if len(degrees) >= 2:
        deg_values = list(degrees.values())
        mean_deg = statistics.mean(deg_values)
        std_deg = statistics.stdev(deg_values) if len(deg_values) > 1 else 0
        threshold = mean_deg + 2 * std_deg

        wiki = _wiki_dir(project_id)
        for node in nodes:
            nid = node["id"]
            deg = degrees.get(nid, 0)
            if deg > threshold:
                # Vérifier la longueur du contenu
                page_path = wiki / f"{nid}.md"
                if page_path.exists():
                    content_len = len(_read(page_path))
                    if content_len < 500:
                        report["hub_stubs"].append({
                            "node": nid, "degree": deg, "content_len": content_len
                        })

    # Nœuds isolés (degré 0)
    report["isolated_nodes"] = [
        nid for nid, deg in degrees.items() if deg == 0
    ]

    # Nœuds avec peu de connexions (degré 1)
    report["low_degree_nodes"] = [
        nid for nid, deg in degrees.items() if deg == 1
    ]

    report["total_nodes"] = len(nodes)
    report["total_edges"] = len(edges)
    report["total_issues"] = (
        len(report["hub_stubs"])
        + len(report["isolated_nodes"])
    )

    return report
