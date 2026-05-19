"""
Agent Core — TraceAI Phase B.

Boucle agent autonome inspirée de Hermes Agent (MIT).

Références Hermes (code copié verbatim indiqué) :
  - agent/iteration_budget.py  → class IterationBudget (copié verbatim)
  - agent/memory_manager.py    → build_memory_context_block (via memory_engine)
  - agent/prompt_builder.py    → TOOL_USE_ENFORCEMENT_GUIDANCE, MEMORY_GUIDANCE,
                                  SKILLS_GUIDANCE, ordre d'assemblage du prompt
  - agent/conversation_loop.py → structure boucle while, system prompt caching,
                                  memory injection dans user message (pas system),
                                  nudge post-tour budget.used >= 5

Différences TraceAI vs Hermes :
  - LLM : Mistral API (pas Anthropic)
  - BDD : SQLite TraceAI existant (pas state.db Hermes)
  - Budget : 15 itérations (90 chez Hermes — ajusté pour coût Mistral)
  - Tools : domaine maintenance industrielle (pas terminal, web, etc.)
  - Mémoire injectée dans user message (même pattern que Hermes)
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config LLM (même pattern que agents/utils.py)
# ---------------------------------------------------------------------------

LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "mistral-large-latest")
LLM_MODEL_FAST = os.getenv("LLM_MODEL_FAST", "mistral-small-latest")
LLM_API_URL = "https://api.mistral.ai/v1/chat/completions"

DB_PATH = Path(__file__).parent / "traceai.db"
PHASE2_DIR = Path(__file__).parent / "uploads_phase2"
UPLOADS_DIR = Path(__file__).parent / "uploads"


# ---------------------------------------------------------------------------
# IterationBudget — copié verbatim de agent/iteration_budget.py
# ---------------------------------------------------------------------------

class IterationBudget:
    """
    Per-agent iteration budget — thread-safe consume/refund counter.
    Copié verbatim de Hermes agent/iteration_budget.py.

    Budget TraceAI : 15 itérations max (90 chez Hermes — ajusté pour coût Mistral).
    """

    def __init__(self, max_total: int):
        self.max_total = max_total
        self._used = 0
        self._lock = threading.Lock()

    def consume(self) -> bool:
        """Try to consume one iteration. Returns True if allowed."""
        with self._lock:
            if self._used >= self.max_total:
                return False
            self._used += 1
            return True

    def refund(self) -> None:
        """Give back one iteration."""
        with self._lock:
            if self._used > 0:
                self._used -= 1

    @property
    def used(self) -> int:
        with self._lock:
            return self._used

    @property
    def remaining(self) -> int:
        with self._lock:
            return max(0, self.max_total - self._used)


# ---------------------------------------------------------------------------
# Constantes prompt — copiées de agent/prompt_builder.py
# ---------------------------------------------------------------------------

TRACEAI_IDENTITY = """Tu es TraceAI, un agent expert en maintenance industrielle.
Tu aides les techniciens à traiter des documents techniques (manuels, rapports, fiches)
et à construire une base de connaissances précise par machine.
Tu es méthodique, tu cites tes sources, et tu signales les incohérences.
Tu réponds en français."""

# Copié verbatim de prompt_builder.py TOOL_USE_ENFORCEMENT_GUIDANCE (adapté)
TOOL_USE_ENFORCEMENT = """# Discipline d'exécution
Tu DOIS utiliser tes tools pour agir — ne décris pas ce que tu ferais, fais-le.
Chaque réponse doit soit contenir des tool calls qui font avancer la tâche,
soit livrer un résultat final. Les réponses qui ne font que décrire des intentions
sans agir sont inacceptables.
Continue de travailler jusqu'à ce que la tâche soit réellement terminée.

RÈGLE ABSOLUE : si tu dois poser une question à l'utilisateur, tu DOIS appeler
le tool ask_clarification — JAMAIS poser une question en texte libre.
Une question en texte libre sera ignorée par le système."""

# Copié verbatim de prompt_builder.py MEMORY_GUIDANCE (adapté TraceAI)
MEMORY_GUIDANCE = """# Mémoire
Tu as une mémoire persistante par projet. Utilise save_memory pour mémoriser :
- Constructeurs connus du client, patterns de leurs documents
- Conventions du site (noms de machines, abréviations locales)
- Préférences client
NE PAS mémoriser : avancement des jobs, SHA256 déjà traités, sessions passées.
Si un fait sera périmé dans 7 jours → il n'appartient PAS à la mémoire.
Les procédures appartiennent aux skills, pas à la mémoire."""

# Copié verbatim de prompt_builder.py SKILLS_GUIDANCE
SKILLS_GUIDANCE = """# Skills
Après une tâche complexe (5+ tool calls), sauvegarde l'approche comme skill
avec create_skill pour la réutiliser. Si un skill chargé est incomplet ou faux,
mets-le à jour immédiatement. Les skills non maintenus deviennent des obstacles."""

THINKING_GUIDANCE = """# Chaîne de raisonnement (Chain of Thought)
Avant chaque réponse ET avant d'appeler tes premiers outils, raisonne toujours
entre balises <thinking>...</thinking>. Contenu attendu :
- Ce que tu comprends de la demande (machine ? procédure ? valeur ?)
- Ton plan d'action (quels outils, dans quel ordre)
- Les skills ou souvenirs pertinents que tu vas charger
- Ton niveau de confiance

EXEMPLE :
<thinking>
L'utilisateur demande le couple de serrage des brides DN150.
Aucune machine précisée — je vais d'abord chercher "brides DN150 couple" dans le wiki.
Si rien, je consulte la mémoire (on a peut-être déjà répondu à ça).
Le skill "bilan-compresseur-jenny" pourrait être pertinent.
Confiance : medium (l'info est peut-être dans le manuel p.47).
</thinking>

Les balises <thinking> sont rendues visuellement côté interface — le technicien
voit ta réflexion en temps réel. Rends-la claire et utile, pas verbeuse."""

GUIDANCE_BY_MODE = {
    "ingestion": """# Mode INGESTION
0. Si le nom du fichier à ingérer n'est PAS mentionné → utilise ask_clarification IMMÉDIATEMENT.
1. OBLIGATOIRE : Commence par orient_wiki pour lire SCHEMA + index + log
2. Classifie chaque document avec classify_doc
3. Trie les documents par priorité (manuels constructeur d'abord)
4. Traite chaque document : parse_pdf → chunk_text → index_chunks
5. Compile le Machine Wiki : compile_wiki pour chaque machine identifiée
6. Détecte les contradictions entre sources
7. Sauvegarde ce que tu as appris en mémoire et en skills""",

    "chat": """# Mode CHAT
0. Utilise ask_clarification UNIQUEMENT si la question ne contient aucun mot-clé permettant de chercher.
   N'utilise PAS ask_clarification si la question mentionne une machine, une pièce, une valeur ou une procédure.
1. Cherche dans le wiki avec search_wiki (recherche par mots-clés)
2. Si un skill pertinent existe, charge-le avec load_skill
3. Complète avec search_memory si le wiki ne suffit pas
4. Cite TOUJOURS tes sources [Fichier, p.X] ou [Machine Wiki]
5. Si une info est absente du wiki, dis-le clairement sans inventer

# Si search_wiki ET search_chunks retournent 0 résultat
→ Le wiki n'a pas encore été construit pour ce projet.
→ Réponds EXACTEMENT : "Aucun document n'a été indexé pour ce projet.
  Utilisez le bouton '+ Ajouter des documents' pour lancer l'ingestion."
→ NE cherche PAS davantage, NE invente PAS de réponse.""",

    "alerte": """# Mode ALERTE
Tu tournes en tâche planifiée sans utilisateur présent.
1. Cherche les contradictions non résolues dans le wiki (contested: true)
2. Vérifie les échéances de maintenance dépassées
3. Crée des alertes avec create_alert pour chaque problème trouvé
4. Sois synthétique — le résultat est livré automatiquement""",
}


# ---------------------------------------------------------------------------
# Schémas des tools par mode
# ---------------------------------------------------------------------------

def _make_tool(name: str, description: str,
               properties: dict, required: list[str] | None = None) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required or [],
            },
        },
    }


TOOL_SCHEMAS: dict[str, list[dict]] = {
    "ingestion": [
        _make_tool("orient_wiki",
            "Lis SCHEMA.md + index.md + log récent du wiki projet AVANT tout traitement. "
            "À appeler EN PREMIER dans toute session d'ingestion.",
            {}),
        _make_tool("classify_doc",
            "Classifie le type d'un document (manual_constructor, intervention_report, "
            "technical_datasheet, parts_inventory, scanned_handwritten, procedure_checklist, unknown).",
            {"filename": {"type": "string", "description": "Nom du fichier à classifier"}},
            ["filename"]),
        _make_tool("parse_pdf",
            "Extrait le texte d'un PDF page par page.",
            {"filename": {"type": "string"}},
            ["filename"]),
        _make_tool("chunk_text",
            "Découpe un texte en chunks selon la stratégie du type de document.",
            {
                "text": {"type": "string", "description": "Texte à découper"},
                "doc_type": {"type": "string", "description": "Type de document"},
                "source_ref": {"type": "string", "description": "Référence source (nom fichier)"},
            },
            ["text", "doc_type"]),
        _make_tool("index_chunks",
            "Indexe des chunks dans SQLite et ChromaDB pour la recherche future.",
            {
                "chunks": {"type": "array", "items": {"type": "object"}},
                "machine_ref": {"type": "string"},
            },
            ["chunks"]),
        _make_tool("compile_wiki",
            "Compile une page Machine Wiki complète à partir des chunks d'une machine.",
            {
                "machine_ref": {"type": "string", "description": "Référence machine"},
                "sources": {"type": "array", "items": {"type": "string"},
                            "description": "Liste des fichiers sources"},
            },
            ["machine_ref"]),
        _make_tool("detect_contradictions",
            "Détecte les contradictions entre plusieurs sources pour une machine.",
            {
                "machine_ref": {"type": "string"},
                "sources": {"type": "array", "items": {"type": "string"}},
            },
            ["machine_ref"]),
        _make_tool("ingest_document_llm",
            "Ingère un document avec UN SEUL appel LLM. Crée source_page, machine_pages, "
            "entity_pages, concept_pages, met à jour overview.md. Préférer à la séquence "
            "parse_pdf→chunk_text→compile_wiki pour les documents complets.",
            {
                "filename": {"type": "string", "description": "Nom du fichier à ingérer"},
                "doc_type": {"type": "string", "description": "Type de document détecté"},
            },
            ["filename"]),
        _make_tool("save_memory",
            "Sauvegarde un fait durable sur le projet (constructeur, site, conventions). "
            "Ne pas utiliser pour des faits éphémères.",
            {
                "key": {"type": "string", "description": "Clé unique du fait"},
                "value": {"type": "string", "description": "Valeur à mémoriser"},
            },
            ["key", "value"]),
        _make_tool("create_skill",
            "Crée ou met à jour un skill pour réutilisation future. "
            "Utiliser après 5+ tool calls pour capitaliser l'approche.",
            {
                "name": {"type": "string", "description": "Nom du skill (lowercase, tirets)"},
                "content": {"type": "string", "description": "Contenu SKILL.md complet"},
            },
            ["name", "content"]),
        _make_tool("ask_clarification",
            "Pose une question à l'utilisateur quand sa requête est ambiguë. "
            "Fournir choices[] (2-4 options) pour guider la réponse. À utiliser AVANT de supposer.",
            {
                "question": {"type": "string", "description": "La question à poser"},
                "choices": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Options de réponse (max 4). Omis = question ouverte.",
                },
            },
            ["question"]),
    ],
    "chat": [
        _make_tool("search_wiki",
            "Recherche des informations dans le Machine Wiki du projet.",
            {
                "query": {"type": "string", "description": "Question ou mots-clés à rechercher"},
                "limit": {"type": "integer", "default": 5},
            },
            ["query"]),
        _make_tool("search_memory",
            "Recherche dans la mémoire persistante du projet.",
            {
                "query": {"type": "string"},
                "limit": {"type": "integer", "default": 3},
            },
            ["query"]),
        _make_tool("load_skill",
            "Charge le contenu d'un skill disponible pour ce projet.",
            {"name": {"type": "string", "description": "Nom du skill à charger"}},
            ["name"]),
        _make_tool("search_chunks",
            "Recherche sémantique dans les chunks indexés (ChromaDB).",
            {
                "query": {"type": "string"},
                "limit": {"type": "integer", "default": 5},
            },
            ["query"]),
        _make_tool("save_synthesis",
            "Sauvegarde une réponse importante dans wiki/syntheses/ pour réutilisation future.",
            {
                "question": {"type": "string", "description": "La question posée"},
                "content": {"type": "string", "description": "Contenu markdown de la réponse"},
            },
            ["question", "content"]),
        _make_tool("ask_clarification",
            "Pose une question à l'utilisateur quand sa requête est ambiguë. "
            "Fournir choices[] (2-4 options) pour guider la réponse. À utiliser AVANT de supposer.",
            {
                "question": {"type": "string", "description": "La question à poser"},
                "choices": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Options de réponse (max 4). Omis = question ouverte.",
                },
            },
            ["question"]),
    ],
    "alerte": [
        _make_tool("search_wiki",
            "Recherche dans le Machine Wiki.",
            {"query": {"type": "string"}, "limit": {"type": "integer", "default": 10}},
            ["query"]),
        _make_tool("check_deadlines",
            "Vérifie les échéances de maintenance dépassées ou imminentes.",
            {}),
        _make_tool("create_alert",
            "Crée une alerte dans la base de données.",
            {
                "title": {"type": "string"},
                "description": {"type": "string"},
                "severity": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                "machine_ref": {"type": "string"},
            },
            ["title", "description", "severity"]),
    ],
}


# ---------------------------------------------------------------------------
# ThinkingStreamParser — détecte <thinking>...</thinking> dans le stream SSE
# ---------------------------------------------------------------------------

class ThinkingStreamParser:
    """
    Parse un stream de tokens et distingue le contenu <thinking> du texte normal.
    Gère les balises partielles (tag coupé en plusieurs tokens).

    Usage :
        parser = ThinkingStreamParser()
        for delta in token_stream:
            for event_type, content in parser.feed(delta):
                # event_type : 'thinking' | 'thinking_end' | 'text'
    """

    _OPEN  = '<thinking>'
    _CLOSE = '</thinking>'

    def __init__(self):
        self._mode = 'text'   # 'text' | 'thinking'
        self._buf  = ''       # buffer pour les balises partielles

    def feed(self, delta: str) -> list:
        events = []
        self._buf += delta

        while self._buf:
            if self._mode == 'text':
                idx = self._buf.find('<')
                if idx == -1:
                    # Pas de '<' — tout est du texte
                    events.append(('text', self._buf))
                    self._buf = ''
                elif idx > 0:
                    # Texte avant le '<'
                    events.append(('text', self._buf[:idx]))
                    self._buf = self._buf[idx:]
                else:
                    # Commence par '<'
                    if self._buf.startswith(self._OPEN):
                        self._mode = 'thinking'
                        self._buf = self._buf[len(self._OPEN):]
                    elif len(self._buf) < len(self._OPEN) and self._OPEN.startswith(self._buf):
                        break  # tag partiel — attendre plus de tokens
                    else:
                        # '<' qui n'est pas une balise thinking
                        events.append(('text', '<'))
                        self._buf = self._buf[1:]

            else:  # mode thinking
                idx = self._buf.find('<')
                if idx == -1:
                    events.append(('thinking', self._buf))
                    self._buf = ''
                elif idx > 0:
                    events.append(('thinking', self._buf[:idx]))
                    self._buf = self._buf[idx:]
                else:
                    if self._buf.startswith(self._CLOSE):
                        events.append(('thinking_end', ''))
                        self._mode = 'text'
                        self._buf = self._buf[len(self._CLOSE):].lstrip('\n')
                    elif len(self._buf) < len(self._CLOSE) and self._CLOSE.startswith(self._buf):
                        break  # balise fermante partielle
                    else:
                        events.append(('thinking', '<'))
                        self._buf = self._buf[1:]

        return events

    def flush(self) -> list:
        """Vide le buffer restant à la fin du stream."""
        events = []
        if self._buf:
            mode = 'thinking' if self._mode == 'thinking' else 'text'
            events.append((mode, self._buf))
            self._buf = ''
        return events


# ---------------------------------------------------------------------------
# Helpers résumé raisonnement (pour événements SSE tool_call / tool_result)
# ---------------------------------------------------------------------------

def _summarize_tool_args(fn_name: str, fn_args: dict) -> str:
    """Résumé court des arguments d'un tool call (affiché dans la trace live)."""
    q = fn_args.get("query", fn_args.get("task", fn_args.get("question", "")))
    if q:
        return str(q)[:80]
    if fn_name == "ingest_document_llm":
        return fn_args.get("filename", "")[:60]
    if fn_name == "save_memory":
        return fn_args.get("key", "")[:60]
    if fn_name == "create_skill":
        return fn_args.get("name", "")[:60]
    if fn_name == "create_alert":
        return fn_args.get("title", "")[:60]
    if fn_name == "classify_doc":
        return fn_args.get("filename", "")[:60]
    if fn_name == "save_synthesis":
        return fn_args.get("question", "")[:60]
    if fn_name == "check_deadlines":
        return fn_args.get("machine_ref", "toutes les machines")[:40]
    return ""


def _summarize_tool_result(fn_name: str, result_str: str) -> str:
    """Résumé court du résultat d'un tool call (affiché dans la trace live)."""
    try:
        data = json.loads(result_str) if result_str else {}
    except (json.JSONDecodeError, TypeError):
        return (result_str or "")[:80]

    if fn_name == "search_wiki":
        results = data.get("results", data.get("pages", []))
        if not results:
            return "Aucun résultat wiki"
        titles = [r.get("title", r.get("page", "?"))[:30] for r in results[:3]]
        expanded = data.get("expanded", 0)
        suffix = f" (+{expanded} graph)" if expanded else ""
        return f"{len(results)} page(s){suffix} — {', '.join(titles)}"

    if fn_name == "search_memory":
        results = data.get("results", data.get("entries", []))
        if not results:
            return "Mémoire vide"
        first = results[0]
        preview = first.get("value", str(first))[:60] if isinstance(first, dict) else str(first)[:60]
        return f"{len(results)} entrée(s) — {preview}"

    if fn_name == "search_chunks":
        results = data.get("results", data.get("chunks", []))
        if not results:
            return "Aucun extrait trouvé"
        return f"{len(results)} extrait(s) trouvé(s)"

    if fn_name == "save_synthesis":
        return "Synthèse sauvegardée"

    if fn_name == "save_memory":
        key = data.get("key", "?")
        return f"Mémorisé : {key}"

    if fn_name == "create_skill":
        return f"Skill créé : {data.get('name', '?')}"

    if fn_name == "create_alert":
        return f"Alerte créée : {data.get('title', '?')[:50]}"

    if fn_name == "ingest_document_llm":
        pages = data.get("pages_created", [])
        return f"{len(pages)} page(s) créée(s)"

    if fn_name == "ask_clarification":
        return f"Question : {data.get('question', '')[:60]}"

    if fn_name == "orient_wiki":
        direction = data.get("direction", data.get("target", ""))
        return f"Orientation : {str(direction)[:60]}" if direction else "Orientation calculée"

    if fn_name == "classify_doc":
        return f"Type : {data.get('doc_type', '?')}"

    if fn_name == "load_skill":
        name = data.get("name", "?")
        return f"Skill chargé : {name}"

    if fn_name == "check_deadlines":
        items = data.get("deadlines", data.get("items", []))
        overdue = [i for i in items if i.get("overdue")]
        return f"{len(overdue)} échéance(s) dépassée(s)" if overdue else f"{len(items)} échéance(s) vérifiée(s)"

    if fn_name == "parse_pdf":
        pages = data.get("pages", data.get("page_count", "?"))
        return f"{pages} page(s) extraite(s)"

    if fn_name == "chunk_text":
        chunks = data.get("chunks", [])
        return f"{len(chunks)} chunk(s)"

    if fn_name == "detect_contradictions":
        contradictions = data.get("contradictions", [])
        return f"{len(contradictions)} contradiction(s) détectée(s)" if contradictions else "Aucune contradiction"

    # Fallback
    result_preview = str(data)[:80]
    return result_preview


# ---------------------------------------------------------------------------
# TraceAIAgent
# ---------------------------------------------------------------------------

class TraceAIAgent:
    """
    Agent autonome TraceAI — boucle Hermes adaptée pour Mistral.

    Architecture copiée de conversation_loop.py :
    - System prompt caché UNE FOIS par session (prefix cache Mistral)
    - Mémoire prefetchée AVANT la boucle, injectée dans le user message
    - IterationBudget reset à chaque appel process() (pas dans __init__)
    - Nudge post-tour si budget.used >= 5 (même seuil que Hermes)
    """

    MAX_ITERATIONS = 15  # 90 chez Hermes, 15 pour contrôler les coûts Mistral

    def __init__(self, project_id: int, db_path: Path = DB_PATH):
        self.project_id = project_id
        self.db_path = db_path
        # Copié de conversation_loop.py : prompt caché, jamais rebuild mid-session
        self._cached_system_prompt: str | None = None

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # ------------------------------------------------------------------
    # Boucle principale
    # ------------------------------------------------------------------

    def process(self, task: str, mode: str = "chat",
                history: list[dict] | None = None,
                session_id: str | None = None) -> dict:
        """
        Exécute une tâche en mode agent.

        Structure exacte de conversation_loop.run_conversation() :
        1. Reset budget (PAS dans __init__, reset à chaque appel)
        2. Build/reuse system prompt caché
        3. Prefetch mémoire ONCE avant boucle
        4. while budget.consume(): call LLM → execute tools → loop
        5. Post-tour: si budget.used >= 5 → trigger_skill_update
        """
        if mode not in TOOL_SCHEMAS:
            mode = "chat"

        # 1. Budget reset — copié de conversation_loop.py ligne 215
        budget = IterationBudget(self.MAX_ITERATIONS)

        conn = self._get_conn()
        try:
            return self._run(task, mode, history or [], budget, session_id, conn)
        finally:
            conn.close()

    def _run(self, task: str, mode: str, history: list[dict],
             budget: IterationBudget,
             session_id: str | None,
             conn: sqlite3.Connection) -> dict:

        # 2. System prompt — buildé UNE FOIS, caché (conversation_loop.py ligne 315)
        # Continuité cross-session : restaurer depuis SQLite si session connue
        if self._cached_system_prompt is None:
            if session_id:
                from memory_engine import load_session_prompt
                self._cached_system_prompt = load_session_prompt(session_id, conn)
                if self._cached_system_prompt:
                    logger.debug("[agent] System prompt restauré (session %s)", session_id)
            if self._cached_system_prompt is None:
                self._cached_system_prompt = self._build_system_prompt(mode, conn)
                if session_id:
                    from memory_engine import save_session_prompt
                    save_session_prompt(
                        session_id, self.project_id, mode,
                        self._cached_system_prompt, conn,
                    )

        # 3. Prefetch mémoire + auto-load skills pertinents ONCE avant boucle
        memory_block = self._prefetch_memory(conn)
        skills_block = self._autoload_skills(task, mode)
        if skills_block:
            memory_block = (memory_block + "\n\n" + skills_block) if memory_block else skills_block

        # Initialiser les messages
        messages: list[dict] = list(history)
        messages.append({"role": "user", "content": task})
        current_user_idx = len(messages) - 1

        tools = TOOL_SCHEMAS[mode]
        final_response = ""
        error = None

        # 4. Boucle principale — structure de conversation_loop.py ligne 532
        while budget.consume():
            try:
                # Injecter mémoire dans le user message courant (jamais dans system)
                # Pattern exact de conversation_loop.py lignes 685–696
                api_messages = self._inject_memory(
                    messages, memory_block, current_user_idx
                )

                # Appel Mistral avec tool calling
                response_msg = self._call_mistral(api_messages, tools)

            except Exception as e:
                logger.error("[agent] Erreur API Mistral: %s", e)
                error = str(e)
                break

            # Normaliser content : Mistral retourne parfois une liste de blocs
            # [{type: text, text: ...}, {type: reference, ...}] (format citations)
            raw_content = response_msg.get("content") or ""
            if isinstance(raw_content, list):
                raw_content = " ".join(
                    b.get("text", "") for b in raw_content
                    if isinstance(b, dict) and b.get("type") == "text"
                )
            response_msg["content"] = raw_content

            tool_calls = response_msg.get("tool_calls") or []

            if tool_calls:
                # Ajouter le message assistant avec ses tool_calls
                messages.append({
                    "role": "assistant",
                    "content": response_msg.get("content") or "",
                    "tool_calls": tool_calls,
                })

                # Exécuter chaque tool et ajouter les résultats
                for tc in tool_calls:
                    if not isinstance(tc, dict) or "function" not in tc:
                        continue
                    fn_name = tc["function"]["name"]
                    try:
                        fn_args = json.loads(tc["function"].get("arguments", "{}"))
                    except json.JSONDecodeError:
                        fn_args = {}

                    result = self._execute_tool(fn_name, fn_args, conn)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.get("id", ""),
                        "name": fn_name,
                        "content": result,
                    })
                    # Sortie anticipée si l'agent demande une clarification
                    try:
                        result_data = json.loads(result)
                        if result_data.get("needs_clarification"):
                            question = result_data.get("question", "")
                            return {
                                "answer": question,
                                "needs_clarification": True,
                                "question": question,
                                "choices": result_data.get("choices", []),
                                "messages": messages,
                                "iterations": budget.used,
                                "mode": mode,
                            }
                    except (json.JSONDecodeError, AttributeError):
                        pass
            else:
                # Réponse finale — sortir de la boucle
                final_response = response_msg.get("content") or ""
                messages.append({
                    "role": "assistant",
                    "content": final_response,
                })
                break

        # 5. Post-tour : background review + compression si nécessaire
        # Remplace trigger_skill_update par le vrai background review Hermes
        if budget.used >= 3:
            try:
                from background_review import spawn_background_review
                spawn_background_review(
                    self.project_id,
                    messages,
                    self._cached_system_prompt or "",
                    review_memory=(budget.used >= 5),
                    review_skills=True,
                )
            except Exception as e:
                logger.debug("[agent] Background review spawn échoué: %s", e)

        # Compression de contexte si les messages dépassent le seuil
        if len(messages) > 10:
            try:
                from context_compressor import needs_compression, compress
                if needs_compression(messages):
                    messages = compress(messages)
                    logger.info("[agent] Contexte compressé après tour")
            except Exception as e:
                logger.debug("[agent] Compression échouée: %s", e)

        return {
            "answer": final_response or (error and f"[Erreur: {error}]") or "",
            "messages": messages,
            "iterations": budget.used,
            "mode": mode,
        }

    # ------------------------------------------------------------------
    # Construction du system prompt
    # ------------------------------------------------------------------

    def _build_system_prompt(self, mode: str,
                              conn: sqlite3.Connection) -> str:
        """
        Assemble le system prompt bloc par bloc.
        Ordre exact de prompt_builder.py build_context_files_prompt() :
        1. Identité
        2. Mémoire (frozen snapshot)
        3. Skills index
        4. Guidance par mode
        5. Tool use enforcement
        """
        from memory_engine import build_memory_prompt_block
        from skills_engine import build_skills_prompt_block

        parts = [TRACEAI_IDENTITY]

        # 2. Mémoire (frozen snapshot — memory_tool.py pattern)
        mem_block = build_memory_prompt_block(self.project_id, conn)
        if mem_block:
            parts.append(mem_block)
        parts.append(MEMORY_GUIDANCE)

        # 3. Skills index
        skills_block = build_skills_prompt_block(self.project_id)
        if skills_block:
            parts.append(skills_block)
        parts.append(SKILLS_GUIDANCE)

        # 4. Guidance par mode
        parts.append(GUIDANCE_BY_MODE.get(mode, GUIDANCE_BY_MODE["chat"]))

        # 5. Tool use enforcement
        parts.append(TOOL_USE_ENFORCEMENT)

        # 6. Chain of Thought — uniquement pour chat (pas alerte cron)
        if mode == "chat":
            parts.append(THINKING_GUIDANCE)

        return "\n\n".join(parts)

    # ------------------------------------------------------------------
    # Injection mémoire dans le user message (pattern Hermes)
    # ------------------------------------------------------------------

    def _prefetch_memory(self, conn: sqlite3.Connection) -> str:
        """
        Prefetch la mémoire ONCE avant la boucle.
        Adapté de conversation_loop.py ligne 511–516 (_ext_prefetch_cache).
        """
        try:
            from memory_engine import load_project_memory, build_memory_context_block
            raw = load_project_memory(self.project_id, conn)
            return build_memory_context_block(raw) if raw else ""
        except Exception as e:
            logger.debug("[agent] Prefetch mémoire échoué: %s", e)
            return ""

    def _autoload_skills(self, task: str, mode: str) -> str:
        """
        Pré-charge les skills pertinents avant la boucle.
        Injecte le contenu des skills dont la description/tags matchent la tâche.
        Analogue au prefetch mémoire — même pattern d'injection dans le user message.
        """
        if mode == "alerte":
            return ""
        try:
            from skills_engine import parse_frontmatter, _skills_dir
            skills_dir = _skills_dir(self.project_id)
            if not skills_dir.exists():
                return ""

            task_lower = task.lower()
            loaded = []
            stopwords = {"when", "this", "that", "with", "from", "pour", "dans",
                         "avec", "sur", "les", "des", "une", "use"}

            for skill_file in sorted(skills_dir.glob("*.md")):
                try:
                    raw = skill_file.read_text(encoding="utf-8")
                    fm, body = parse_frontmatter(raw)
                    if not body.strip():
                        continue
                    name = fm.get("name") or skill_file.stem
                    desc = str(fm.get("description", "")).lower()
                    tags = fm.get("metadata", {}).get("hermes", {}).get("tags", [])
                    relevant_words = [
                        w for w in desc.split()
                        if len(w) > 4 and w not in stopwords
                    ]
                    tag_match = any(str(t).lower() in task_lower for t in tags)
                    word_match = any(w in task_lower for w in relevant_words)
                    if word_match or tag_match:
                        loaded.append(f"### Skill : {name}\n{body.strip()}")
                except Exception:
                    pass

            if not loaded:
                return ""

            logger.debug("[agent] Auto-load skills : %d skill(s) chargé(s)", len(loaded))
            return (
                "<auto-loaded-skills>\n"
                "[Skills chargés automatiquement — pertinents pour cette tâche]\n\n"
                + "\n\n---\n\n".join(loaded)
                + "\n</auto-loaded-skills>"
            )
        except Exception as e:
            logger.debug("[agent] _autoload_skills échoué: %s", e)
            return ""

    def _inject_memory(self, messages: list[dict], memory_block: str,
                        current_user_idx: int) -> list[dict]:
        """
        Injecte le bloc mémoire dans le message utilisateur courant.
        NE MUTE JAMAIS messages[] original.
        Pattern exact de conversation_loop.py lignes 685–696 :
        mémoire dans user message, PAS dans system prompt.
        """
        if not memory_block:
            return messages

        api_messages = []
        for idx, msg in enumerate(messages):
            api_msg = dict(msg)
            if idx == current_user_idx and msg.get("role") == "user":
                base = api_msg.get("content", "")
                api_msg["content"] = base + "\n\n" + memory_block
            api_messages.append(api_msg)
        return api_messages

    # ------------------------------------------------------------------
    # Appel Mistral avec tool calling
    # ------------------------------------------------------------------

    def _call_mistral(self, messages: list[dict],
                       tools: list[dict]) -> dict:
        """
        Appel HTTP à l'API Mistral avec function calling.
        Retry exponentiel sur 429 (rate limit) — adapté de agents/utils.py _SEM pattern.
        """
        payload: dict[str, Any] = {
            "model": LLM_MODEL,
            "messages": [{"role": "system", "content": self._cached_system_prompt}]
                        + messages,
        }
        if tools:
            payload["tools"] = tools

        max_retries = 5
        base_delay = 8.0  # secondes, Mistral free tier ~3 RPM

        for attempt in range(max_retries):
            with httpx.Client(timeout=120.0) as client:
                resp = client.post(
                    LLM_API_URL,
                    headers={"Authorization": f"Bearer {LLM_API_KEY}"},
                    json=payload,
                )

            if resp.status_code == 429:
                # Lire Retry-After header si présent
                retry_after = resp.headers.get("retry-after")
                delay = float(retry_after) if retry_after else base_delay * (2 ** attempt)
                logger.warning(
                    "[agent] Rate limit Mistral (429) — attente %.0fs (tentative %d/%d)",
                    delay, attempt + 1, max_retries,
                )
                time.sleep(delay)
                continue

            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]

        raise RuntimeError(f"Mistral rate limit — {max_retries} tentatives épuisées")

    def _call_mistral_stream(self, messages: list[dict],
                              tools: list[dict]):
        """
        Appel Mistral en mode streaming (stream=True).
        Yield des chunks de texte au fil de la génération.
        Retourne le message complet à la fin via StopIteration value.

        Retry exponentiel sur 429 — même pattern que _call_mistral.
        Adapté de Hermes conversation_loop.py stream_callback pattern.
        Note : Mistral ne streame PAS les tool_calls — si l'appel contient
        des tools et que le modèle appelle un tool, on reçoit le message
        complet en un seul chunk (même avec stream=True).
        """
        payload: dict[str, Any] = {
            "model": LLM_MODEL,
            "messages": [{"role": "system", "content": self._cached_system_prompt}]
                        + messages,
            "stream": True,
        }
        if tools:
            payload["tools"] = tools

        max_retries = 5
        base_delay = 8.0

        for attempt in range(max_retries):
            full_content = ""
            full_message: dict = {}
            got_429 = False
            wait_delay = base_delay * (2 ** attempt)

            with httpx.Client(timeout=120.0) as client:
                with client.stream(
                    "POST",
                    LLM_API_URL,
                    headers={"Authorization": f"Bearer {LLM_API_KEY}"},
                    json=payload,
                ) as resp:
                    if resp.status_code == 429:
                        retry_after = resp.headers.get("retry-after")
                        wait_delay = float(retry_after) if retry_after else wait_delay
                        logger.warning(
                            "[agent/stream] Rate limit Mistral (429) — attente %.0fs (tentative %d/%d)",
                            wait_delay, attempt + 1, max_retries,
                        )
                        got_429 = True
                    else:
                        resp.raise_for_status()
                        for line in resp.iter_lines():
                            if not line or line == "data: [DONE]":
                                continue
                            if line.startswith("data: "):
                                try:
                                    chunk = json.loads(line[6:])
                                    choice = chunk["choices"][0]
                                    delta = choice.get("delta", {})

                                    # Tool calls → pas de streaming de texte
                                    if delta.get("tool_calls"):
                                        if not full_message.get("tool_calls"):
                                            full_message["tool_calls"] = []
                                        for tc in delta["tool_calls"]:
                                            idx = tc.get("index", 0)
                                            while len(full_message["tool_calls"]) <= idx:
                                                full_message["tool_calls"].append(
                                                    {"id": "", "function": {"name": "", "arguments": ""}}
                                                )
                                            existing = full_message["tool_calls"][idx]
                                            if tc.get("id"):
                                                existing["id"] = tc["id"]
                                            fn = tc.get("function", {})
                                            if fn.get("name"):
                                                existing["function"]["name"] += fn["name"]
                                            if fn.get("arguments"):
                                                existing["function"]["arguments"] += fn["arguments"]

                                    # Texte → yield chunk (normaliser liste blocs citations)
                                    text_delta = delta.get("content") or ""
                                    if isinstance(text_delta, list):
                                        text_delta = " ".join(
                                            b.get("text", "") for b in text_delta
                                            if isinstance(b, dict) and b.get("type") == "text"
                                        )
                                    if text_delta:
                                        full_content += text_delta
                                        yield text_delta

                                    if choice.get("finish_reason"):
                                        full_message["content"] = full_content
                                        full_message["role"] = "assistant"

                                except (json.JSONDecodeError, KeyError):
                                    continue

            if not got_429:
                return full_message

            # 429 — attendre avant de réessayer
            if attempt < max_retries - 1:
                # Signaler l'attente via un event spécial (lu par process_stream)
                yield f"\x00RATE_LIMIT_WAIT:{wait_delay:.0f}\x00"
                time.sleep(wait_delay)

        raise RuntimeError(f"Mistral rate limit — {max_retries} tentatives épuisées. Réessayez dans quelques minutes.")

    def process_stream(self, task: str, mode: str = "chat",
                       history: list[dict] | None = None,
                       session_id: str | None = None):
        """
        Version streaming de process().
        Yield des événements SSE en JSON.

        Événements :
          {"type": "thinking",     "delta": "..."}           — raisonnement live
          {"type": "thinking_end"}                           — fin du bloc thinking
          {"type": "tool_call",    "name": "search_wiki",
                                   "args": "..."}            — tool en cours
          {"type": "tool_result",  "name": "...",
                                   "summary": "...", "ok": true}
          {"type": "text",         "delta": "..."}           — token de réponse
          {"type": "done",         "iterations": N,
           "needs_clarification": false, "choices": []}      — fin

        Pattern inspiré de Hermes conversation_loop.py stream_callback.
        Les tool calls ne sont pas streamés (Mistral ne le supporte pas) —
        on envoie seulement un événement de status.
        """
        if mode not in TOOL_SCHEMAS:
            mode = "chat"

        budget = IterationBudget(self.MAX_ITERATIONS)
        conn = self._get_conn()

        try:
            # Setup identique à _run()
            if self._cached_system_prompt is None:
                if session_id:
                    from memory_engine import load_session_prompt
                    self._cached_system_prompt = load_session_prompt(session_id, conn)
                if self._cached_system_prompt is None:
                    self._cached_system_prompt = self._build_system_prompt(mode, conn)
                    if session_id:
                        from memory_engine import save_session_prompt
                        save_session_prompt(session_id, self.project_id, mode,
                                            self._cached_system_prompt, conn)

            memory_block = self._prefetch_memory(conn)
            skills_block = self._autoload_skills(task, mode)
            if skills_block:
                memory_block = (memory_block + "\n\n" + skills_block) if memory_block else skills_block

            messages: list[dict] = list(history or [])
            messages.append({"role": "user", "content": task})
            current_user_idx = len(messages) - 1
            tools = TOOL_SCHEMAS[mode]
            needs_clarification = False
            clarification_question = ""
            clarification_choices: list = []

            while budget.consume():
                api_messages = self._inject_memory(messages, memory_block, current_user_idx)

                try:
                    gen = self._call_mistral_stream(api_messages, tools)
                    response_msg: dict = {"content": "", "role": "assistant"}
                    parser = ThinkingStreamParser()

                    try:
                        while True:
                            delta = next(gen)
                            # Signal interne rate_limit — intercepté avant le parser
                            if delta.startswith("\x00RATE_LIMIT_WAIT:") and delta.endswith("\x00"):
                                try:
                                    wait_s = int(float(delta[16:-1]))
                                except ValueError:
                                    wait_s = 8
                                yield json.dumps({"type": "rate_limit", "wait": wait_s})
                                continue
                            for ev_type, ev_content in parser.feed(delta):
                                if ev_type == 'thinking' and ev_content:
                                    yield json.dumps({"type": "thinking", "delta": ev_content})
                                elif ev_type == 'thinking_end':
                                    yield json.dumps({"type": "thinking_end"})
                                elif ev_type == 'text' and ev_content:
                                    yield json.dumps({"type": "text", "delta": ev_content})
                    except StopIteration as e:
                        # Vider le buffer restant
                        for ev_type, ev_content in parser.flush():
                            if ev_type == 'thinking' and ev_content:
                                yield json.dumps({"type": "thinking", "delta": ev_content})
                            elif ev_type == 'text' and ev_content:
                                yield json.dumps({"type": "text", "delta": ev_content})
                        if e.value:
                            response_msg = e.value

                except Exception as e:
                    yield json.dumps({"type": "error", "message": str(e)})
                    break

                # Normaliser content
                raw_content = response_msg.get("content") or ""
                if isinstance(raw_content, list):
                    raw_content = " ".join(
                        b.get("text", "") for b in raw_content
                        if isinstance(b, dict) and b.get("type") == "text"
                    )
                response_msg["content"] = raw_content

                tool_calls = response_msg.get("tool_calls") or []

                if tool_calls:
                    messages.append({
                        "role": "assistant",
                        "content": raw_content,
                        "tool_calls": tool_calls,
                    })

                    for tc in tool_calls:
                        if not isinstance(tc, dict) or "function" not in tc:
                            continue
                        fn_name = tc["function"]["name"]
                        try:
                            fn_args = json.loads(tc["function"].get("arguments", "{}"))
                        except json.JSONDecodeError:
                            fn_args = {}

                        # Signaler le tool call (avec résumé des args)
                        yield json.dumps({
                            "type": "tool_call",
                            "name": fn_name,
                            "args": _summarize_tool_args(fn_name, fn_args),
                        })

                        result = self._execute_tool(fn_name, fn_args, conn)

                        # Signaler le résultat du tool
                        yield json.dumps({
                            "type": "tool_result",
                            "name": fn_name,
                            "summary": _summarize_tool_result(fn_name, result),
                            "ok": True,
                        })

                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.get("id", ""),
                            "name": fn_name,
                            "content": result,
                        })

                        try:
                            result_data = json.loads(result)
                            if result_data.get("needs_clarification"):
                                needs_clarification = True
                                clarification_question = result_data.get("question", "")
                                clarification_choices = result_data.get("choices", [])
                                break
                        except (json.JSONDecodeError, AttributeError):
                            pass

                    if needs_clarification:
                        break
                else:
                    messages.append({"role": "assistant", "content": raw_content})
                    break

            # Background review
            if budget.used >= 3:
                try:
                    from background_review import spawn_background_review
                    spawn_background_review(
                        self.project_id, messages,
                        self._cached_system_prompt or "",
                        review_memory=(budget.used >= 5),
                        review_skills=True,
                    )
                except Exception:
                    pass

            yield json.dumps({
                "type": "done",
                "iterations": budget.used,
                "mode": mode,
                "needs_clarification": needs_clarification,
                "question": clarification_question,
                "choices": clarification_choices,
            })

        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Exécution des tools — dispatch vers fonctions TraceAI
    # ------------------------------------------------------------------

    def _execute_tool(self, name: str, args: dict,
                       conn: sqlite3.Connection) -> str:
        """
        Dispatche un tool call vers la fonction Python correspondante.
        Retourne TOUJOURS un JSON string (pattern tool_executor.py).
        Les agents existants (parser, chunker, compilateur, repondeur)
        sont wrappés ici sans modification.
        """
        try:
            result = self._dispatch(name, args, conn)
            return json.dumps(result, ensure_ascii=False)
        except Exception as e:
            logger.error("[agent] Tool '%s' échoué: %s", name, e)
            return json.dumps({"error": str(e), "tool": name})

    def _dispatch(self, name: str, args: dict,
                   conn: sqlite3.Connection) -> Any:
        """Routing des tool calls vers les implémentations TraceAI."""

        # --- Wiki ---
        if name == "orient_wiki":
            from wiki_engine import orient_agent, init_wiki
            init_wiki(self.project_id)
            return {"context": orient_agent(self.project_id)}

        if name == "ingest_document_llm":
            return self._tool_ingest_document_llm(args)

        # --- Parsing PDF ---
        if name == "parse_pdf":
            return self._tool_parse_pdf(args)

        # --- Classification ---
        if name == "classify_doc":
            return self._tool_classify_doc(args)

        # --- Chunking ---
        if name == "chunk_text":
            return self._tool_chunk_text(args, conn)

        # --- Indexation ---
        if name == "index_chunks":
            return self._tool_index_chunks(args, conn)

        # --- Compilation wiki ---
        if name == "compile_wiki":
            return self._tool_compile_wiki(args, conn)

        # --- Contradictions ---
        if name == "detect_contradictions":
            return self._tool_detect_contradictions(args, conn)

        # --- Recherche wiki (graph-aware) ---
        if name == "search_wiki":
            return self._tool_search_wiki_graph(args, conn)

        # --- Recherche chunks (ChromaDB + SQLite fallback) ---
        if name == "search_chunks":
            return self._tool_search_chunks(args, conn)

        # --- Mémoire ---
        if name == "save_memory":
            from memory_engine import save_memory
            return save_memory(
                self.project_id,
                args.get("key", ""),
                args.get("value", ""),
                conn,
            )

        if name == "search_memory":
            from memory_engine import search_memory
            results = search_memory(
                self.project_id,
                args.get("query", ""),
                conn,
                limit=args.get("limit", 3),
            )
            return {"results": results}

        # --- Skills ---
        if name == "load_skill":
            from skills_engine import load_skill
            body = load_skill(args.get("name", ""), self.project_id)
            return {"content": body, "found": bool(body)}

        if name == "create_skill":
            from skills_engine import save_skill
            save_skill(args["name"], self.project_id, args["content"])
            return {"success": True, "name": args["name"]}

        if name == "save_synthesis":
            from wiki_engine import save_synthesis
            slug = save_synthesis(
                self.project_id,
                args.get("question", ""),
                args.get("content", ""),
            )
            return {"success": True, "slug": slug}

        # --- Alertes ---
        if name == "create_alert":
            return self._tool_create_alert(args, conn)

        if name == "check_deadlines":
            return self._tool_check_deadlines(conn)

        if name == "ask_clarification":
            choices = args.get("choices") or []
            return {
                "needs_clarification": True,
                "question": args.get("question", ""),
                "choices": choices[:4] if choices else [],
            }

        return {"error": f"Tool inconnu : {name}"}

    # ------------------------------------------------------------------
    # Implémentations des tools (wrappers agents existants)
    # ------------------------------------------------------------------

    def _tool_parse_pdf(self, args: dict) -> dict:
        """Wrapper de agents/parser.py — extrait le texte d'un PDF."""
        filename = args.get("filename", "")
        filepath = PHASE2_DIR / str(self.project_id) / filename
        if not filepath.exists():
            # Chercher aussi dans uploads/
            filepath = UPLOADS_DIR / filename
        if not filepath.exists():
            return {"error": f"Fichier introuvable : {filename}"}

        try:
            import fitz
            doc = fitz.open(str(filepath))
            pages_text = []
            for i, page in enumerate(doc):
                text = page.get_text()
                if text.strip():
                    pages_text.append(f"--- PAGE {i+1} ---\n{text}")
            full_text = "\n".join(pages_text)
            return {
                "text": full_text[:20000],  # Limite contexte
                "pages": len(doc),
                "filename": filename,
            }
        except Exception as e:
            return {"error": str(e)}

    def _tool_classify_doc(self, args: dict) -> dict:
        """Classifie le type d'un document via LLM léger."""
        filename = args.get("filename", "")
        from agents.utils import llm_json
        from rag_strategies import list_doc_types

        doc_types = list_doc_types()
        try:
            result = llm_json(
                [{
                    "role": "user",
                    "content": (
                        f"Classifie ce document industriel selon son type :\n"
                        f"Nom du fichier : {filename}\n\n"
                        f"Types possibles : {', '.join(doc_types)}, unknown\n\n"
                        f'Retourne JSON : {{"doc_type": "...", "confidence": 0.0-1.0, '
                        f'"reasoning": "..."}}'
                    ),
                }],
                timeout=30.0,
                model_override=LLM_MODEL_FAST,
            )
            return result
        except Exception as e:
            return {"doc_type": "unknown", "confidence": 0.0, "error": str(e)}

    def _tool_chunk_text(self, args: dict,
                          conn: sqlite3.Connection) -> dict:
        """
        Wrapper de agents/chunker.py avec stratégie RAG dynamique.
        Le chunker existant n'est PAS modifié.
        """
        text = args.get("text", "")
        doc_type = args.get("doc_type", "unknown")
        source_ref = args.get("source_ref", "")

        from rag_strategies import select_strategy
        strategy = select_strategy(doc_type)

        # Chunking simple basé sur la stratégie (le vrai chunker est dans agents/)
        max_size = strategy.get("max_chunk_size", 1000)
        chunks = []

        if strategy["chunk_by"] == "none":
            # Une fiche = un chunk
            chunks = [{"content": text, "index": 0, "source": source_ref}]
        elif strategy["chunk_by"] in ("sections", "paragraphs", "steps"):
            # Découpage par paragraphes / sections
            paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
            current = []
            current_len = 0
            for para in paragraphs:
                if current_len + len(para) > max_size and current:
                    chunks.append({
                        "content": "\n\n".join(current),
                        "index": len(chunks),
                        "source": source_ref,
                    })
                    current = []
                    current_len = 0
                current.append(para)
                current_len += len(para)
            if current:
                chunks.append({
                    "content": "\n\n".join(current),
                    "index": len(chunks),
                    "source": source_ref,
                })
        else:
            # Fallback paragraphes
            chunks = [
                {"content": text[i:i+max_size], "index": i//max_size, "source": source_ref}
                for i in range(0, len(text), max_size)
            ]

        return {
            "chunks": chunks,
            "count": len(chunks),
            "strategy": strategy["chunk_by"],
        }

    def _tool_index_chunks(self, args: dict,
                            conn: sqlite3.Connection) -> dict:
        """Wrapper de agents/indexeur.py — indexe les chunks en base."""
        chunks = args.get("chunks", [])
        machine_ref = args.get("machine_ref", "")

        try:
            for chunk in chunks:
                conn.execute(
                    """INSERT OR IGNORE INTO chunks
                       (project_id, chunk_index, content, machine_ref, created_at)
                       VALUES (?, ?, ?, ?, datetime('now'))""",
                    (self.project_id, chunk.get("index", 0),
                     chunk.get("content", ""), machine_ref),
                )
            conn.commit()
            return {"indexed": len(chunks), "machine_ref": machine_ref}
        except Exception as e:
            return {"error": str(e)}

    def _tool_compile_wiki(self, args: dict,
                            conn: sqlite3.Connection) -> dict:
        """
        Wrapper de agents/compilateur.py.
        Compile une page Machine Wiki et la sauvegarde via wiki_engine.
        """
        machine_ref = args.get("machine_ref", "")
        sources = args.get("sources", [])

        try:
            from agents import compilateur
            from wiki_engine import init_wiki, save_machine_page

            # Récupérer les chunks de cette machine
            rows = conn.execute(
                """SELECT content FROM chunks
                   WHERE project_id=? AND (machine_ref=? OR machine_ref='')
                   LIMIT 30""",
                (self.project_id, machine_ref),
            ).fetchall()
            chunks = [{"content": r[0], "machine": machine_ref} for r in rows]

            if not chunks:
                return {"error": f"Aucun chunk trouvé pour {machine_ref}"}

            result = compilateur._compile_machine_wiki(machine_ref, chunks)
            wiki_content = result.get("content", "")

            if wiki_content:
                init_wiki(self.project_id)
                # Wrapper le contenu avec frontmatter si absent
                if not wiki_content.startswith("---"):
                    from wiki_engine import create_machine_page_template
                    template = create_machine_page_template(
                        self.project_id, machine_ref,
                        title=machine_ref, sources=sources
                    )
                    # Ajouter le contenu LLM après le template
                    wiki_content = template + "\n\n" + wiki_content

                save_machine_page(self.project_id, machine_ref,
                                  wiki_content, sources)

                # Sauvegarder aussi dans wiki_pages (base existante)
                existing = conn.execute(
                    "SELECT id FROM wiki_pages WHERE project_id=? AND title=?",
                    (self.project_id, machine_ref),
                ).fetchone()
                if existing:
                    conn.execute(
                        "UPDATE wiki_pages SET content_md=? WHERE id=?",
                        (wiki_content, existing[0]),
                    )
                else:
                    conn.execute(
                        """INSERT INTO wiki_pages
                           (project_id, title, page_type, content_md, created_at)
                           VALUES (?, ?, 'machine', ?, datetime('now'))""",
                        (self.project_id, machine_ref, wiki_content),
                    )
                conn.commit()

            return {"success": True, "machine_ref": machine_ref,
                    "wiki_chars": len(wiki_content)}
        except Exception as e:
            logger.error("[agent] compile_wiki échoué: %s", e)
            return {"error": str(e)}

    def _tool_detect_contradictions(self, args: dict,
                                     conn: sqlite3.Connection) -> dict:
        """Détecte les contradictions entre sources pour une machine."""
        machine_ref = args.get("machine_ref", "")
        try:
            from agents import alertes
            rows = conn.execute(
                """SELECT content FROM chunks
                   WHERE project_id=? AND machine_ref=? LIMIT 20""",
                (self.project_id, machine_ref),
            ).fetchall()
            chunks = [{"content": r[0], "machine": machine_ref} for r in rows]
            if not chunks:
                return {"contradictions": [], "machine_ref": machine_ref}
            result = alertes.detect_contradictions(machine_ref, chunks)
            return result or {"contradictions": [], "machine_ref": machine_ref}
        except Exception as e:
            return {"error": str(e)}

    def _tool_search_chunks(self, args: dict,
                             conn: sqlite3.Connection | None = None) -> dict:
        """
        Recherche dans les chunks : ChromaDB (sémantique) + SQLite (keyword fallback).
        ChromaDB est souvent vide — le fallback SQLite couvre le pipeline legacy.
        """
        query = args.get("query", "")
        limit = args.get("limit", 5)
        results = []

        # 1. ChromaDB (sémantique)
        try:
            from agents.repondeur import _search_chroma
            from pathlib import Path as _Path
            chroma_dir = _Path(__file__).parent / "chroma_data"
            chroma_results = _search_chroma(
                self.project_id,
                query,
                chroma_dir if chroma_dir.exists() else None,
                limit=limit,
            )
            results.extend(chroma_results or [])
        except Exception:
            pass

        # 2. SQLite fallback si ChromaDB vide
        if not results and conn:
            try:
                words = [w for w in query.lower().split() if len(w) > 2]
                if words:
                    like_clauses = " OR ".join(["LOWER(content) LIKE ?" for _ in words])
                    params = [f"%{w}%" for w in words] + [self.project_id, limit * 2]
                    rows = conn.execute(
                        f"""SELECT content, machine_ref, page_ref FROM chunks
                            WHERE ({like_clauses}) AND project_id = ?
                            LIMIT ?""",
                        params,
                    ).fetchall()
                    for row in rows:
                        results.append({
                            "content": row[0][:600],
                            "machine_ref": row[1] or "",
                            "page_ref": row[2] or "",
                            "source": "sqlite_chunks",
                        })
            except Exception:
                pass

        return {"results": results[:limit]}

    def _tool_ingest_document_llm(self, args: dict) -> dict:
        """
        Ingestion one-call LLM via wiki_engine.ingest_document_llm().
        Génère source_page + machine_pages + entity_pages + concept_pages en 1 appel Mistral.
        """
        from wiki_engine import ingest_document_llm
        filename = args.get("filename", "")
        doc_type = args.get("doc_type", "unknown")

        # Chercher le fichier
        filepath = PHASE2_DIR / str(self.project_id) / filename
        if not filepath.exists():
            filepath = UPLOADS_DIR / filename
        if not filepath.exists():
            # Chercher dans uploads/ par project_id
            candidate = UPLOADS_DIR / f"{self.project_id}.pdf"
            if candidate.exists():
                filepath = candidate
            else:
                return {"error": f"Fichier introuvable : {filename}"}

        result = ingest_document_llm(self.project_id, filepath, doc_type)
        return result

    def _tool_search_wiki_graph(self, args: dict,
                                 conn: sqlite3.Connection) -> dict:
        """
        Recherche wiki enrichie par expansion graph.
        1. Recherche LIKE dans wiki_pages SQLite (existant)
        2. Recherche dans les fichiers wiki markdown
        3. Expansion via graph.json (voisins confidence >= 0.7)
        Inspiré de query.py find_relevant_pages() + expand_via_graph().
        """
        from agents.repondeur import _search_wiki
        from graph_engine import expand_via_graph, load_graph
        from wiki_engine import WIKI_BASE

        query = args.get("query", "")
        limit = args.get("limit", 5)

        # Recherche SQLite (existant)
        sql_results = _search_wiki(self.project_id, query, conn, limit=limit)

        # Recherche dans les fichiers wiki markdown (nouveaux)
        file_results = []
        wiki_dir = WIKI_BASE / str(self.project_id)
        if wiki_dir.exists():
            words = [w for w in query.lower().split() if len(w) > 2]
            for page in wiki_dir.rglob("*.md"):
                if page.name in ("index.md", "log.md"):
                    continue
                try:
                    content = page.read_text(encoding="utf-8")
                    if any(w in content.lower() for w in words):
                        file_results.append({
                            "title": page.stem,
                            "content": content[:1500],
                            "source": f"wiki/{page.relative_to(wiki_dir)}",
                        })
                        if len(file_results) >= limit:
                            break
                except Exception:
                    pass

        all_results = sql_results + file_results

        # Expansion via graph
        if load_graph(self.project_id):
            found_page_ids = [
                r.get("source", "").replace("wiki/", "").replace(".md", "")
                for r in all_results
            ]
            neighbor_ids = expand_via_graph(
                self.project_id, found_page_ids, min_confidence=0.7
            )
            for nid in neighbor_ids[:3]:  # max 3 voisins
                page_path = wiki_dir / f"{nid}.md"
                if page_path.exists():
                    try:
                        content = page_path.read_text(encoding="utf-8")
                        file_results.append({
                            "title": page_path.stem,
                            "content": content[:1000],
                            "source": f"wiki/{nid}.md",
                            "via_graph": True,
                        })
                    except Exception:
                        pass

        return {"results": all_results[:limit + 3], "expanded": len(neighbor_ids) if load_graph(self.project_id) else 0}

    def _tool_create_alert(self, args: dict,
                            conn: sqlite3.Connection) -> dict:
        """Crée une alerte dans la table alerts."""
        title = args.get("title", "")
        description = args.get("description", "")
        message = f"{title} — {description}" if description else title
        try:
            conn.execute(
                """INSERT INTO alerts
                   (project_id, title, description, message, severity, machine_ref,
                    alert_type, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, 'agent', datetime('now'))""",
                (
                    self.project_id,
                    title,
                    description,
                    message,
                    args.get("severity", "medium"),
                    args.get("machine_ref", ""),
                ),
            )
            conn.commit()
            return {"success": True, "title": title}
        except Exception as e:
            return {"error": str(e)}

    def _tool_check_deadlines(self, conn: sqlite3.Connection) -> dict:
        """Vérifie les échéances de maintenance dans la mémoire et le wiki."""
        try:
            from memory_engine import load_project_memory
            memory = load_project_memory(self.project_id, conn)
            deadline_hints = [
                line for line in memory.split("\n")
                if any(kw in line.lower() for kw in
                       ["maintenance", "échéance", "révision", "contrôle", "deadline"])
            ]
            return {
                "deadline_hints": deadline_hints,
                "count": len(deadline_hints),
            }
        except Exception as e:
            return {"error": str(e)}
