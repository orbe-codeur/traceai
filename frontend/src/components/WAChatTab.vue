<template>
  <div class="wac-root">

    <!-- ─── Zone conversation (70%) ─────────────────────────────────────── -->
    <div class="wac-main">

      <!-- Welcome / suggestions -->
      <div v-if="!messages.length && !streaming" class="wac-welcome">
        <div class="wac-welcome-icon">🤖</div>
        <h2 class="wac-welcome-title">Wiki Agent</h2>
        <p class="wac-welcome-sub">
          Posez n'importe quelle question sur vos machines. L'agent consulte le wiki,
          la mémoire et les sources pour vous répondre avec citations vérifiables.
        </p>
        <div class="wac-suggestions">
          <button v-for="s in SUGGESTIONS" :key="s" class="wac-suggest" @click="sendSuggestion(s)">
            {{ s }}
          </button>
        </div>
      </div>

      <!-- Messages -->
      <div v-else class="wac-messages" ref="msgsEl">

        <div v-for="(msg, i) in messages" :key="i" class="wac-msg" :class="msg.role">

          <!-- User bubble -->
          <template v-if="msg.role === 'user'">
            <div class="wac-bubble wac-bubble--user">{{ msg.content }}</div>
          </template>

          <!-- Agent bubble -->
          <template v-else>
            <!-- Bloc thinking collapsible (après réponse) -->
            <div v-if="msg.thinking" class="wac-thinking-wrap">
              <button class="wac-thinking-toggle" @click="msg.thinkingOpen = !msg.thinkingOpen">
                <span class="wac-thinking-icon">🧠</span>
                <span class="wac-mono" style="font-size:11px;color:var(--inkMute)">
                  {{ msg.thinkingOpen ? '▾' : '▸' }} Réflexion
                </span>
              </button>
              <div v-if="msg.thinkingOpen" class="wac-thinking-body">
                {{ msg.thinking }}
              </div>
            </div>

            <!-- Trace de raisonnement (collapsible après réponse) -->
            <div v-if="msg.trace?.length" class="wac-trace-wrap" :class="'trace-type-'+traceType(msg.trace)">
              <button class="wac-trace-toggle" @click="msg.traceOpen = !msg.traceOpen">
                <span class="wac-trace-toggle-icon">{{ msg.traceOpen ? '▾' : '▸' }}</span>
                <span class="wac-trace-toggle-badge wac-mono" :class="'badge-'+traceType(msg.trace)">
                  {{ traceTypeLabel(msg.trace) }}
                </span>
                <span class="wac-trace-toggle-label wac-mono">
                  {{ msg.trace.length }} étape{{ msg.trace.length !== 1 ? 's' : '' }}
                </span>
                <span class="wac-trace-iters wac-mono" v-if="msg.iterations">
                  {{ msg.iterations }} iter.
                </span>
              </button>
              <div v-if="msg.traceOpen" class="wac-trace-body">
                <TraceStep v-for="(step, si) in msg.trace" :key="si" :step="step" />
              </div>
            </div>

            <div class="wac-bubble wac-bubble--agent">
              <div class="wac-bubble-content" v-html="renderMessage(msg.content)" />

              <!-- Clarification choices -->
              <div v-if="msg.clarification" class="wac-choices">
                <button v-for="c in msg.clarification.choices" :key="c"
                  class="wac-choice-btn" @click="sendClarification(c)">
                  {{ c }}
                </button>
              </div>

              <!-- Footer meta -->
              <div v-if="msg.sources?.length" class="wac-msg-meta">
                <button class="wac-see-sources" @click="openSources(msg.sources)">
                  {{ msg.sources.length }} source{{ msg.sources.length !== 1 ? 's' : '' }} — Voir →
                </button>
              </div>
            </div>
          </template>
        </div>

        <!-- Raisonnement en cours (live) -->
        <div v-if="streaming" class="wac-msg assistant">
          <div class="wac-reasoning-live">

            <!-- Bloc thinking live -->
            <div v-if="thinkingStream || thinkingDone" class="wac-thinking-live"
                 :class="{ done: thinkingDone }">
              <div class="wac-thinking-header">
                <span class="wac-thinking-icon">🧠</span>
                <span class="wac-mono" style="font-size:11px;font-weight:700;color:var(--inkMute)">
                  Réflexion{{ thinkingDone ? '' : '…' }}
                </span>
                <span v-if="!thinkingDone" class="wac-mini-dot animate-trace-dot" style="margin-left:6px" />
              </div>
              <div class="wac-thinking-text">{{ thinkingStream }}</div>
            </div>

            <!-- Rate limit wait -->
            <div v-if="rateLimitWait > 0" class="wac-rate-limit-banner">
              <span class="wac-mono">⏳ Limite Mistral atteinte — nouvel essai dans {{ rateLimitWait }}s…</span>
            </div>

            <!-- Trace live des outils -->
            <div v-if="liveTrace.length" class="wac-trace-live" :class="'trace-type-'+traceType(liveTrace)">
              <div class="wac-trace-live-header">
                <span class="wac-live-dot animate-trace-dot" />
                <span class="wac-trace-toggle-badge wac-mono" :class="'badge-'+traceType(liveTrace)" style="margin-left:4px">
                  {{ traceTypeLabel(liveTrace) }}
                </span>
                <span class="wac-mono" style="font-size:11px;color:var(--inkMute);margin-left:6px">en cours…</span>
              </div>
              <TraceStep v-for="(step, si) in liveTrace" :key="si" :step="step" :live="true" />
            </div>

            <!-- Texte de réponse en cours -->
            <div v-if="currentStream" class="wac-bubble wac-bubble--agent" style="margin-top:8px">
              <div class="wac-bubble-content" v-html="renderMessage(currentStream)" />
            </div>

            <!-- Curseur initial (rien encore) -->
            <div v-if="!thinkingStream && !liveTrace.length && !currentStream"
                 class="wac-bubble wac-bubble--agent">
              <span class="wac-typing">
                <span v-for="n in 3" :key="n" class="wac-dot"
                      :style="{ animationDelay: (n-1)*200+'ms' }" />
              </span>
            </div>
          </div>
        </div>

      </div>

      <!-- Zone saisie -->
      <div class="wac-input-wrap">
        <div class="wac-input-box" :class="{ focused: inputFocused }">
          <textarea
            v-model="userInput"
            ref="inputEl"
            class="wac-input"
            placeholder="Quel est le couple de serrage recommandé ?"
            rows="1"
            @keydown.enter.exact.prevent="send"
            @input="autoResize"
            @focus="inputFocused = true"
            @blur="inputFocused = false"
          />
          <button class="wac-send" :disabled="!userInput.trim() || streaming" @click="send">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round">
              <path d="M22 2L11 13M22 2L15 22l-4-9-9-4 20-7z"/>
            </svg>
          </button>
        </div>
        <div class="wac-input-hint wac-mono wac-mute">Entrée pour envoyer · Shift+Entrée pour nouvelle ligne</div>
      </div>
    </div>

    <!-- ─── Panneau sources (30%) ────────────────────────────────────────── -->
    <div class="wac-sources-panel" :class="{ open: sourcesPanelOpen }">
      <div class="wac-sources-head">
        <span class="wac-mono wac-mute" style="font-size:10px;letter-spacing:.18em;text-transform:uppercase">Sources</span>
        <button class="wac-sources-close" @click="sourcesPanelOpen = false">✕</button>
      </div>
      <div v-if="!activeSources.length" class="wac-sources-empty">
        <div class="wac-mono wac-mute" style="font-size:12px;text-align:center;padding:20px">
          Les sources apparaîtront après la première réponse.
        </div>
      </div>
      <div v-else class="wac-sources-list">
        <div v-for="(s, i) in activeSources" :key="i" class="wac-source-item">
          <div class="wac-source-doc wac-mono">{{ s.doc }}<span v-if="s.page"> · p.{{ s.page }}</span></div>
          <div v-if="s.excerpt" class="wac-source-excerpt">{{ s.excerpt }}</div>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, nextTick, onMounted, defineComponent, h } from 'vue'
import api from '../services/api.js'

const props = defineProps({
  projectId: { type: Number, required: true },
})

const emit = defineEmits(['wikilink'])

// ── Types de raisonnement ─────────────────────────────────────────────────────
function traceType(steps) {
  if (!steps?.length) return 'recherche'
  if (steps.some(s => s.tool === 'ask_clarification'))  return 'clarification'
  if (steps.some(s => s.tool === 'create_alert'))        return 'alerte'
  if (steps.some(s => s.tool === 'ingest_document_llm'
                    || s.tool === 'compile_wiki'
                    || s.tool === 'index_chunks'))        return 'ingestion'
  return 'recherche'
}

function traceTypeLabel(steps) {
  const t = traceType(steps)
  const m = {
    clarification: '❓ Clarification',
    alerte:        '🔔 Détection anomalie',
    ingestion:     '📥 Ingestion',
    recherche:     '🔍 Recherche',
  }
  return m[t] || '🔍 Recherche'
}

// ── Composant TraceStep (inline) ─────────────────────────────────────────────
const TraceStep = defineComponent({
  props: { step: Object, live: Boolean },
  setup(p) {
    const ICONS = {
      search_wiki:'🔍', search_memory:'🧠', search_chunks:'📄',
      save_synthesis:'💾', save_memory:'💾', create_skill:'⚡',
      create_alert:'🔔', ingest_document_llm:'📥', ask_clarification:'❓',
      orient_wiki:'🗂️', classify_doc:'🏷️', load_skill:'⚙️',
      check_deadlines:'📅', parse_pdf:'📃', chunk_text:'✂️',
      detect_contradictions:'⚠️', delegate_task:'🤝',
      index_chunks:'🗄️', compile_wiki:'📚',
    }

    return () => {
      const step = p.step
      const icon = ICONS[step.tool] || '🔧'
      const isClarif = step.tool === 'ask_clarification'

      // Clarification → traitement visuel spécial
      if (isClarif) {
        return h('div', { class: 'wac-trace-clarif' }, [
          h('div', { class: 'wac-trace-clarif-header' }, [
            h('span', { class: 'wac-trace-clarif-icon' }, '❓'),
            h('span', { class: 'wac-trace-clarif-title' }, "L'agent a besoin de précisions"),
          ]),
          step.args && h('div', { class: 'wac-trace-clarif-question' }, `"${step.args}"`),
          step.pending && h('div', { class: 'wac-trace-clarif-pending' }, [
            h('span', { class: 'wac-mini-dot animate-trace-dot' }),
            h('span', null, ' préparation de la question…'),
          ]),
        ])
      }

      // Tool normal
      return h('div', { class: `wac-trace-step${step.pending && p.live ? ' live' : ''}` }, [
        h('span', { class: 'wac-trace-step-icon' }, icon),
        h('div', { class: 'wac-trace-step-info' }, [
          h('span', { class: 'wac-trace-tool wac-mono' }, step.tool),
          step.args && h('span', { class: 'wac-trace-args' }, step.args),
          step.pending && p.live
            ? h('div', { class: 'wac-trace-pending' }, [
                h('span', { class: 'wac-mini-dot animate-trace-dot' }),
                h('span', { class: 'wac-mono', style: 'font-size:11px;color:var(--inkMute)' }, ' en cours…'),
              ])
            : h('div', { class: `wac-trace-result ${step.ok ? 'ok' : 'err'}` }, [
                h('span', { class: 'wac-trace-result-icon' }, step.ok ? '✓' : '✗'),
                ` ${step.result}`,
              ]),
        ]),
      ])
    }
  },
})

// ── État ──────────────────────────────────────────────────────────────────────
const messages = ref([])
const userInput = ref('')
const streaming = ref(false)
const currentStream = ref('')
const liveTrace = ref([])        // trace live pendant le streaming
const thinkingStream = ref('')   // texte thinking en cours
const thinkingDone = ref(false)  // thinking terminé (</thinking> reçu)
const rateLimitWait = ref(0)     // secondes restantes avant retry (0 = inactif)
let rateLimitTimer = null
const inputFocused = ref(false)
const msgsEl = ref(null)
const inputEl = ref(null)
const sessionId = ref(crypto.randomUUID())
const sourcesPanelOpen = ref(false)
const activeSources = ref([])

let abortController = null

const SUGGESTIONS = [
  'Quel est le couple de serrage recommandé ?',
  'Quelle est la procédure de maintenance à 500h ?',
  'Quelles pièces de rechange sont critiques ?',
  'Y a-t-il des contradictions entre les sources ?',
]

const TOOL_ICONS = {
  search_wiki:            '🔍',
  search_memory:          '🧠',
  search_chunks:          '📄',
  save_synthesis:         '💾',
  save_memory:            '💾',
  create_skill:           '⚡',
  create_alert:           '🔔',
  ingest_document_llm:    '📥',
  ask_clarification:      '❓',
  orient_wiki:            '🗂️',
  classify_doc:           '🏷️',
  load_skill:             '⚙️',
  check_deadlines:        '📅',
  parse_pdf:              '📃',
  chunk_text:             '✂️',
  detect_contradictions:  '⚠️',
  delegate_task:          '🤝',
  index_chunks:           '🗄️',
  compile_wiki:           '📚',
}

function toolIcon(name) {
  return TOOL_ICONS[name] || '🔧'
}

// ── SSE helper ────────────────────────────────────────────────────────────────
function buildHistory() {
  // Transforme les messages UI en format [{role, content}] pour l'agent
  return messages.value
    .filter(m => m.role === 'user' || (m.role === 'assistant' && m.content && m.content !== '…'))
    .map(m => ({ role: m.role, content: m.content }))
    .slice(-20)  // max 20 messages (10 échanges) pour ne pas exploser le contexte
}

async function streamAgentChat(message) {
  abortController = new AbortController()
  const response = await fetch(`/api/projects/${props.projectId}/agent-chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      mode: 'chat',
      session_id: sessionId.value,
      history: buildHistory(),
    }),
    signal: abortController.signal,
  })

  if (!response.ok) throw new Error(`HTTP ${response.status}`)

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop()
    for (const line of lines) {
      if (!line.startsWith('data: ')) continue
      try {
        const evt = JSON.parse(line.slice(6))
        handleEvent(evt)
      } catch { /* skip malformed */ }
    }
  }
}

function handleEvent(evt) {
  if (evt.type === 'thinking') {
    thinkingStream.value += evt.delta
    scrollBottom()

  } else if (evt.type === 'thinking_end') {
    thinkingDone.value = true
    scrollBottom()

  } else if (evt.type === 'tool_call') {
    liveTrace.value.push({
      tool: evt.name,
      args: evt.args || '',
      result: null,
      ok: true,
      pending: true,
    })
    scrollBottom()

  } else if (evt.type === 'tool_result') {
    const step = [...liveTrace.value].reverse().find(s => s.tool === evt.name && s.pending)
    if (step) {
      step.result = evt.summary || ''
      step.ok = evt.ok !== false
      step.pending = false
    }
    scrollBottom()

  } else if (evt.type === 'text') {
    currentStream.value += evt.delta
    scrollBottom()

  } else if (evt.type === 'done') {
    const text = currentStream.value
    const thinking = thinkingStream.value
    currentStream.value = ''
    thinkingStream.value = ''
    thinkingDone.value = false
    const trace = [...liveTrace.value]
    liveTrace.value = []

    if (evt.needs_clarification) {
      messages.value.push({
        role: 'assistant',
        content: evt.question || '…',
        clarification: { choices: evt.choices || [] },
        sources: [], iterations: evt.iterations,
        thinking, thinkingOpen: false,
        trace, traceOpen: trace.length > 0,
      })
    } else if (text) {
      const sources = parseSources(text)
      if (sources.length) activeSources.value = sources
      messages.value.push({
        role: 'assistant',
        content: text,
        sources, iterations: evt.iterations,
        thinking, thinkingOpen: false,
        trace, traceOpen: false,
      })
    } else if (trace.length || thinking) {
      messages.value.push({
        role: 'assistant',
        content: '…',
        sources: [], iterations: evt.iterations,
        thinking, thinkingOpen: !!thinking,
        trace, traceOpen: true,
      })
    }
    scrollBottom()

  } else if (evt.type === 'rate_limit') {
    rateLimitWait.value = evt.wait || 8
    if (rateLimitTimer) clearInterval(rateLimitTimer)
    rateLimitTimer = setInterval(() => {
      rateLimitWait.value = Math.max(0, rateLimitWait.value - 1)
      if (rateLimitWait.value === 0) { clearInterval(rateLimitTimer); rateLimitTimer = null }
    }, 1000)
    scrollBottom()

  } else if (evt.type === 'error') {
    if (rateLimitTimer) { clearInterval(rateLimitTimer); rateLimitTimer = null }
    rateLimitWait.value = 0
    currentStream.value = ''
    thinkingStream.value = ''
    thinkingDone.value = false
    liveTrace.value = []
    const isRateLimit = evt.message?.includes('rate limit') || evt.message?.includes('429')
    messages.value.push({
      role: 'assistant',
      content: isRateLimit
        ? '⏳ Limite de requêtes Mistral atteinte. Réessayez dans quelques secondes.'
        : `⚠️ ${evt.message}`,
      sources: [], trace: [],
    })
    scrollBottom()
  }
}

// ── Envoi ─────────────────────────────────────────────────────────────────────
async function send() {
  const q = userInput.value.trim()
  if (!q || streaming.value) return
  userInput.value = ''
  if (inputEl.value) inputEl.value.style.height = 'auto'

  messages.value.push({ role: 'user', content: q })
  streaming.value = true
  liveTrace.value = []
  currentStream.value = ''
  thinkingStream.value = ''
  thinkingDone.value = false
  rateLimitWait.value = 0
  if (rateLimitTimer) { clearInterval(rateLimitTimer); rateLimitTimer = null }
  await nextTick()
  scrollBottom()

  try {
    await streamAgentChat(q)
  } catch (e) {
    if (e.name !== 'AbortError') {
      messages.value.push({
        role: 'assistant',
        content: '⚠️ Connexion perdue. Réessayez dans quelques instants.',
        sources: [], trace: [],
      })
    }
  } finally {
    streaming.value = false
    liveTrace.value = []
    currentStream.value = ''
    thinkingStream.value = ''
    thinkingDone.value = false
    rateLimitWait.value = 0
    if (rateLimitTimer) { clearInterval(rateLimitTimer); rateLimitTimer = null }
    await nextTick()
    scrollBottom()
  }
}

function sendSuggestion(s) {
  userInput.value = s
  send()
}

async function sendClarification(choice) {
  messages.value.push({ role: 'user', content: choice })
  streaming.value = true
  liveTrace.value = []
  currentStream.value = ''
  await nextTick()
  scrollBottom()
  try {
    await streamAgentChat(choice)
  } catch (e) {
    if (e.name !== 'AbortError') {
      messages.value.push({ role: 'assistant', content: '⚠️ Erreur de connexion.', sources: [], trace: [] })
    }
  } finally {
    streaming.value = false
    liveTrace.value = []
    currentStream.value = ''
    await nextTick()
    scrollBottom()
  }
}

// ── Rendu message ─────────────────────────────────────────────────────────────
function renderMessage(text) {
  if (!text) return ''
  let html = text

  // Wikilinks [[name]] → chip cliquable
  html = html.replace(/\[\[([^\]]+?)\]\]/g, (_, name) =>
    `<button class="wac-wikilink" onclick="window.__waWikilink && window.__waWikilink('${name.replace(/'/g, "\\'")}')">🔧 ${name}</button>`
  )

  // Sources [doc p.N] → badge vert inline
  html = html.replace(/\[([^\]]{1,60}?)\s+p\.(\d+)\]/g, (_, doc, page) =>
    `<span class="wac-src-badge">📄 ${doc} p.${page}</span>`
  )

  // Citations [quelque chose] → badge sobre
  html = html.replace(/\[([^\]]{1,80}?)\]/g, (_, ref) =>
    `<span class="wac-ref-badge">${ref}</span>`
  )

  // Bold / italic
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>')

  // Titres
  html = html.replace(/^### (.+)$/gm, '<h4 class="wac-h4">$1</h4>')
  html = html.replace(/^## (.+)$/gm, '<h3 class="wac-h3">$1</h3>')
  html = html.replace(/^# (.+)$/gm, '<h2 class="wac-h2">$1</h2>')

  // Listes
  html = html.replace(/^- (.+)$/gm, '<li>$1</li>')

  // Sauts de ligne
  html = html.replace(/\n/g, '<br>')

  return html
}

function parseSources(text) {
  const sources = []
  const seen = new Set()
  const re = /\[([^\]]{1,60}?)\s+p\.(\d+)\]/g
  let m
  while ((m = re.exec(text)) !== null) {
    const key = `${m[1]}:${m[2]}`
    if (!seen.has(key)) {
      seen.add(key)
      sources.push({ doc: m[1], page: m[2] })
    }
  }
  return sources
}

function openSources(sources) {
  activeSources.value = sources
  sourcesPanelOpen.value = true
}

function scrollBottom() {
  if (msgsEl.value) msgsEl.value.scrollTop = msgsEl.value.scrollHeight
}

function autoResize(e) {
  e.target.style.height = 'auto'
  e.target.style.height = Math.min(e.target.scrollHeight, 160) + 'px'
}

onMounted(async () => {
  window.__waWikilink = (name) => emit('wikilink', name)
  // Charger l'historique de conversation
  try {
    const res = await api.getAgentChatHistory(props.projectId, 40)
    const hist = res.data?.messages || []
    if (hist.length) {
      messages.value = hist.map(m => ({
        role: m.role,
        content: m.content,
        sources: [],
        trace: [],
        thinking: '',
        thinkingOpen: false,
        traceOpen: false,
        _fromHistory: true,
      }))
      await nextTick()
      scrollBottom()
    }
  } catch {
    // Historique indisponible — pas grave, on repart de zéro
  }
})
</script>

<style scoped>
.wac-root {
  display: flex;
  height: 100%;
  overflow: hidden;
}

/* ─── Conversation ─────────────────────────────────────────────────────────── */
.wac-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  overflow: hidden;
}

.wac-welcome {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 48px;
  text-align: center;
}
.wac-welcome-icon { font-size: 52px; margin-bottom: 16px; }
.wac-welcome-title { font-size: 22px; font-weight: 700; margin: 0 0 10px; }
.wac-welcome-sub { font-size: 14px; color: var(--inkSoft); max-width: 480px; line-height: 1.65; margin: 0 0 28px; }
.wac-suggestions { display: flex; flex-direction: column; gap: 8px; width: 100%; max-width: 520px; }
.wac-suggest {
  padding: 10px 16px;
  background: var(--paperAlt);
  border: 1px solid var(--rule);
  border-radius: 4px;
  cursor: pointer;
  font-family: var(--font-sans);
  font-size: 13px;
  color: var(--ink);
  text-align: left;
  transition: background .12s;
}
.wac-suggest:hover { background: var(--ruleSoft); }

.wac-messages {
  flex: 1;
  overflow-y: auto;
  padding: 24px 32px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.wac-msg { display: flex; flex-direction: column; gap: 6px; }
.wac-msg.user { align-items: flex-end; }
.wac-msg.assistant { align-items: flex-start; max-width: 80%; }

.wac-bubble {
  padding: 12px 16px;
  border-radius: 8px;
  font-size: 14px;
  line-height: 1.65;
}
.wac-bubble--user {
  background: var(--teal);
  color: #fff;
  border-bottom-right-radius: 3px;
  max-width: 72%;
}
.wac-bubble--agent {
  background: var(--paperAlt);
  border: 1px solid var(--rule);
  color: var(--ink);
  border-bottom-left-radius: 3px;
  width: 100%;
}

/* ─── Badges inline dans réponse agent ─────────────────────────────────────── */
.wac-bubble-content :deep(.wac-src-badge) {
  display: inline-block;
  font-family: var(--font-mono);
  font-size: 11px;
  padding: 1px 6px;
  background: var(--tealBg);
  border: 1px solid color-mix(in srgb, var(--teal) 30%, transparent);
  color: var(--teal);
  border-radius: 2px;
  margin: 0 2px;
  font-weight: 600;
}
.wac-bubble-content :deep(.wac-ref-badge) {
  display: inline-block;
  font-family: var(--font-mono);
  font-size: 11px;
  padding: 1px 5px;
  background: var(--paper);
  border: 1px solid var(--rule);
  color: var(--inkMute);
  border-radius: 2px;
  margin: 0 2px;
}
.wac-bubble-content :deep(.wac-wikilink) {
  display: inline-block;
  font-size: 12px;
  font-weight: 600;
  padding: 2px 8px;
  background: color-mix(in srgb, var(--blue) 10%, transparent);
  border: 1px solid color-mix(in srgb, var(--blue) 30%, transparent);
  color: var(--blue);
  border-radius: 3px;
  cursor: pointer;
  margin: 0 2px;
  font-family: var(--font-sans);
}
.wac-bubble-content :deep(.wac-wikilink):hover { background: color-mix(in srgb, var(--blue) 18%, transparent); }
.wac-bubble-content :deep(strong) { font-weight: 700; }
.wac-bubble-content :deep(em) { font-style: italic; }
.wac-bubble-content :deep(.wac-h2) { font-size: 16px; font-weight: 700; margin: 12px 0 6px; }
.wac-bubble-content :deep(.wac-h3) { font-size: 14.5px; font-weight: 700; margin: 10px 0 5px; }
.wac-bubble-content :deep(.wac-h4) { font-size: 13.5px; font-weight: 700; margin: 8px 0 4px; }
.wac-bubble-content :deep(ul) { padding-left: 18px; margin: 6px 0; }
.wac-bubble-content :deep(li) { margin: 3px 0; }

/* ─── Rate limit banner ─────────────────────────────────────────────────────── */
.wac-rate-limit-banner {
  background: color-mix(in srgb, var(--amber) 12%, transparent);
  border: 1px solid color-mix(in srgb, var(--amber) 40%, transparent);
  border-radius: 4px;
  padding: 8px 14px;
  margin-bottom: 8px;
  font-size: 12px;
  color: color-mix(in srgb, var(--amber) 80%, var(--ink));
}

/* ─── Bloc thinking live ───────────────────────────────────────────────────── */
.wac-thinking-live {
  background: color-mix(in srgb, var(--inkMute) 6%, transparent);
  border: 1px solid var(--ruleSoft);
  border-left: 3px solid var(--inkMute);
  border-radius: 4px;
  padding: 10px 14px;
  margin-bottom: 8px;
  width: 100%;
  transition: border-left-color .3s;
}
.wac-thinking-live.done {
  border-left-color: var(--teal);
  opacity: .85;
}
.wac-thinking-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
}
.wac-thinking-icon { font-size: 13px; }
.wac-thinking-text {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--inkSoft);
  line-height: 1.6;
  white-space: pre-wrap;
  font-style: italic;
  max-height: 160px;
  overflow: hidden;
}

/* ─── Bloc thinking collapsible (messages finalisés) ────────────────────────── */
.wac-thinking-wrap {
  width: 100%;
  margin-bottom: 4px;
}
.wac-thinking-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 4px 0;
  font-family: var(--font-sans);
}
.wac-thinking-toggle:hover .wac-thinking-icon { opacity: .7; }
.wac-thinking-body {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--inkMute);
  line-height: 1.6;
  white-space: pre-wrap;
  font-style: italic;
  padding: 8px 12px;
  background: color-mix(in srgb, var(--inkMute) 4%, transparent);
  border-left: 2px solid var(--ruleSoft);
  border-radius: 0 4px 4px 0;
  margin-top: 4px;
}

/* ─── Raisonnement — trace collapsible (messages finalisés) ────────────────── */
.wac-trace-wrap {
  background: var(--paper);
  border: 1px solid var(--rule);
  border-radius: 6px;
  overflow: hidden;
  width: 100%;
}
/* Couleur de bordure selon le type */
.wac-trace-wrap.trace-type-clarification { border-color: color-mix(in srgb, var(--amber) 50%, transparent); }
.wac-trace-wrap.trace-type-alerte        { border-color: color-mix(in srgb, var(--red) 40%, transparent); }
.wac-trace-wrap.trace-type-ingestion     { border-color: color-mix(in srgb, var(--blue) 40%, transparent); }

.wac-trace-live.trace-type-clarification { border-color: color-mix(in srgb, var(--amber) 50%, transparent); }
.wac-trace-live.trace-type-alerte        { border-color: color-mix(in srgb, var(--red) 40%, transparent); }
.wac-trace-live.trace-type-ingestion     { border-color: color-mix(in srgb, var(--blue) 40%, transparent); }

.wac-trace-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: transparent;
  border: none;
  cursor: pointer;
  width: 100%;
  text-align: left;
  font-family: var(--font-sans);
}
.wac-trace-toggle:hover { background: var(--ruleSoft); }
.wac-trace-toggle-icon { color: var(--inkMute); font-size: 11px; width: 10px; }
.wac-trace-toggle-label { font-size: 11px; color: var(--inkMute); flex: 1; }
.wac-trace-iters {
  font-size: 10px;
  color: var(--inkMute);
  padding: 1px 6px;
  background: var(--paperAlt);
  border: 1px solid var(--rule);
  border-radius: 2px;
}

/* Badge type de raisonnement */
.wac-trace-toggle-badge {
  font-size: 10.5px;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 2px;
  letter-spacing: .06em;
}
.badge-recherche     { background: var(--paperAlt); color: var(--inkMute); border: 1px solid var(--rule); }
.badge-clarification { background: var(--amberBg); color: #8A5700; border: 1px solid color-mix(in srgb, var(--amber) 50%, transparent); }
.badge-alerte        { background: var(--redBg); color: var(--red); border: 1px solid color-mix(in srgb, var(--red) 30%, transparent); }
.badge-ingestion     { background: color-mix(in srgb, var(--blue) 10%, transparent); color: var(--blue); border: 1px solid color-mix(in srgb, var(--blue) 30%, transparent); }

.wac-trace-body {
  padding: 4px 0 8px;
  border-top: 1px solid var(--ruleSoft);
}

/* Clarification — traitement spécial */
.wac-trace-clarif {
  margin: 6px 10px 4px;
  padding: 10px 14px;
  background: var(--amberBg);
  border: 1px solid color-mix(in srgb, var(--amber) 50%, transparent);
  border-radius: 4px;
}
.wac-trace-clarif-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}
.wac-trace-clarif-icon { font-size: 16px; }
.wac-trace-clarif-title {
  font-size: 12.5px;
  font-weight: 700;
  color: #8A5700;
}
.wac-trace-clarif-question {
  font-size: 13px;
  font-style: italic;
  color: var(--inkSoft);
  line-height: 1.4;
  padding-left: 26px;
}
.wac-trace-clarif-pending {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: var(--amber);
  padding-left: 26px;
  margin-top: 4px;
  font-family: var(--font-mono);
}

/* ─── Raisonnement — trace live (pendant streaming) ───────────────────────── */
.wac-reasoning-live {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.wac-trace-live {
  background: var(--paper);
  border: 1px solid var(--rule);
  border-radius: 6px;
  overflow: hidden;
  padding-bottom: 6px;
}
.wac-trace-live-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px 6px;
  border-bottom: 1px solid var(--ruleSoft);
  margin-bottom: 2px;
}
.wac-live-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--amber);
  display: inline-block;
}

/* ─── Étape de trace (partagée live + collapsé) ────────────────────────────── */
.wac-trace-step {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 5px 12px;
  transition: background .1s;
}
.wac-trace-step.live {
  background: color-mix(in srgb, var(--amber) 6%, transparent);
}
.wac-trace-step-icon {
  font-size: 13px;
  flex-shrink: 0;
  margin-top: 1px;
  width: 18px;
  text-align: center;
}
.wac-trace-step-info {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 4px;
  row-gap: 2px;
}
.wac-trace-tool {
  font-size: 11px;
  font-weight: 700;
  color: var(--inkSoft);
}
.wac-trace-args {
  font-size: 11.5px;
  color: var(--inkMute);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 260px;
}
.wac-trace-args::before { content: '·'; margin: 0 3px; color: var(--rule); }
.wac-trace-result {
  width: 100%;
  font-size: 11.5px;
  line-height: 1.4;
  display: flex;
  align-items: baseline;
  gap: 5px;
}
.wac-trace-result.ok { color: var(--teal); }
.wac-trace-result.err { color: var(--red); }
.wac-trace-result-icon { font-size: 10px; flex-shrink: 0; }
.wac-trace-pending {
  display: flex;
  align-items: center;
  gap: 5px;
  width: 100%;
}
.wac-mini-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--amber);
  display: inline-block;
}

/* ─── Clarification choices ────────────────────────────────────────────────── */
.wac-choices {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--rule);
}
.wac-choice-btn {
  padding: 6px 14px;
  background: var(--paper);
  border: 1px solid var(--rule);
  border-radius: 999px;
  cursor: pointer;
  font-family: var(--font-sans);
  font-size: 13px;
  font-weight: 550;
  color: var(--ink);
  transition: background .12s, border-color .12s;
}
.wac-choice-btn:hover { background: var(--ruleSoft); border-color: var(--inkMute); }

/* Meta footer */
.wac-msg-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px solid var(--ruleSoft);
}
.wac-see-sources {
  font-size: 11px;
  font-weight: 600;
  color: var(--teal);
  background: none;
  border: none;
  cursor: pointer;
  padding: 0;
}

/* Typing dots */
.wac-typing { display: flex; align-items: center; gap: 4px; }
.wac-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--inkMute);
  animation: wacDot 1.2s ease-in-out infinite;
}
@keyframes wacDot {
  0%, 80%, 100% { opacity: .3; transform: scale(.8); }
  40%           { opacity: 1;  transform: scale(1); }
}

/* ─── Input zone ───────────────────────────────────────────────────────────── */
.wac-input-wrap {
  padding: 14px 32px 18px;
  border-top: 1px solid var(--rule);
  background: var(--paper);
  flex-shrink: 0;
}
.wac-input-box {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  background: var(--paperAlt);
  border: 1px solid var(--rule);
  border-radius: 8px;
  padding: 8px 12px;
  transition: border-color .15s;
}
.wac-input-box.focused { border-color: var(--inkSoft); }
.wac-input {
  flex: 1;
  border: none;
  outline: none;
  resize: none;
  font-family: var(--font-sans);
  font-size: 14px;
  line-height: 1.5;
  background: transparent;
  color: var(--ink);
  max-height: 160px;
}
.wac-send {
  width: 34px;
  height: 34px;
  border-radius: 6px;
  border: none;
  background: var(--teal);
  color: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: background .12s;
}
.wac-send:hover:not(:disabled) { background: color-mix(in srgb, var(--teal) 80%, black); }
.wac-send:disabled { opacity: .4; cursor: not-allowed; }
.wac-input-hint { font-size: 10px; text-align: center; margin-top: 5px; }

/* ─── Panneau sources ──────────────────────────────────────────────────────── */
.wac-sources-panel {
  width: 0;
  overflow: hidden;
  border-left: 1px solid transparent;
  background: var(--paperAlt);
  display: flex;
  flex-direction: column;
  transition: width .2s ease, border-color .2s;
  flex-shrink: 0;
}
.wac-sources-panel.open {
  width: 260px;
  border-left-color: var(--rule);
}
.wac-sources-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px 10px;
  border-bottom: 1px solid var(--rule);
  flex-shrink: 0;
}
.wac-sources-close {
  width: 22px;
  height: 22px;
  border: none;
  background: transparent;
  cursor: pointer;
  color: var(--inkMute);
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 3px;
}
.wac-sources-close:hover { background: var(--ruleSoft); }
.wac-sources-empty { flex: 1; display: flex; align-items: center; justify-content: center; }
.wac-sources-list { flex: 1; overflow-y: auto; padding: 12px; display: flex; flex-direction: column; gap: 10px; }
.wac-source-item {
  padding: 10px 12px;
  background: var(--paper);
  border: 1px solid var(--rule);
  border-radius: 4px;
}
.wac-source-doc {
  font-size: 11px;
  font-weight: 600;
  color: var(--inkSoft);
  margin-bottom: 4px;
}
.wac-source-excerpt {
  font-size: 12px;
  color: var(--inkSoft);
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* ─── Utilitaires ──────────────────────────────────────────────────────────── */
.wac-mono { font-family: var(--font-mono); }
.wac-mute { color: var(--inkMute); }
</style>
