<script setup>
import { ref, computed, nextTick, watch } from 'vue'
import api from '../services/api.js'

const props = defineProps({
  project:   Object,
  activeStep: Object,   // étape actuellement sélectionnée
  steps:     Array,
})

const emit = defineEmits(['close', 'open-pdf', 'goto-step'])

// ── État chat ──
const messages  = ref([{
  role: 'assistant',
  text: `Bonjour ! Je peux t'aider sur n'importe quelle étape du manuel **${props.project?.pdf_filename || 'PDF'}**.\n\nPose-moi une question ou clique une suggestion.`,
  sources: [],
}])
const input     = ref('')
const loading   = ref(false)
const messagesEl = ref(null)

// ── Suggestions contextuelles selon la catégorie de l'étape active ──
const SUGGESTIONS = {
  hydraulique:  ["Quel est le couple de serrage ?", "Comment purger l'air du circuit ?", "Que faire si la fuite persiste ?"],
  électrique:   ["Quelle norme s'applique ?", "Comment vérifier l'isolation ?", "Procédure de consignation ?"],
  mécanique:    ["Quels outils sont nécessaires ?", "Quel jeu fonctionnel appliquer ?", "Ordre de serrage des vis ?"],
  sécurité:     ["Quels EPI sont requis ?", "Procédure de consignation complète ?", "Qui doit être présent ?"],
  test:         ["Comment interpréter les valeurs ?", "Quelles tolérances acceptables ?", "Que faire en cas d'écart ?"],
  vérification: ["Quelle fréquence de vérification ?", "Valeurs de référence à noter ?", "Outillage de mesure requis ?"],
  default:      ["Résume cette étape", "Quelles précautions prendre ?", "Quels matériaux sont nécessaires ?"],
}

const suggestions = computed(() => {
  const cat = props.activeStep?.category?.toLowerCase() || ''
  return SUGGESTIONS[cat] || SUGGESTIONS.default
})

const stepContext = computed(() => {
  if (!props.activeStep) return null
  return `Étape ${props.activeStep.step_number} — ${props.activeStep.title}. ${props.activeStep.description || ''}`
})

// ── Sections du manuel (catégories uniques présentes dans les étapes) ──
const sections = computed(() => {
  if (!props.steps?.length) return []
  const cats = [...new Set(props.steps.map(s => s.category).filter(Boolean))]
  return cats
})

// ── Envoi ──
async function send(text) {
  const q = (text || input.value).trim()
  if (!q || loading.value) return
  input.value = ''

  messages.value.push({ role: 'user', text: q, sources: [] })
  loading.value = true
  scrollToBottom()

  try {
    const { data } = await api.chat(props.project.id, q, stepContext.value)
    messages.value.push({
      role: 'assistant',
      text: data.answer,
      sources: data.sources || [],
    })
  } catch {
    messages.value.push({
      role: 'assistant',
      text: 'Désolé, une erreur est survenue. Réessaie dans un instant.',
      sources: [],
      error: true,
    })
  } finally {
    loading.value = false
    scrollToBottom()
  }
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesEl.value) {
      messagesEl.value.scrollTop = messagesEl.value.scrollHeight
    }
  })
}

// Échappe le HTML brut avant de formater (protection XSS)
function escapeHtml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
}

// Formatte le texte : **gras** et [p.X] → badges cliquables
// L'échappement est fait EN PREMIER pour éviter le XSS
function formatText(text) {
  return escapeHtml(text)
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\[p\.(\d+)\]/g, '<button class="src-inline" data-page="$1">p.$1</button>')
}

function handleInlineClick(e) {
  const btn = e.target.closest('[data-page]')
  if (btn) emit('open-pdf', Number(btn.dataset.page))
}
</script>

<template>
  <div class="ap-overlay" @click.self="emit('close')">
    <div class="ap-panel">

      <!-- Header -->
      <div class="ap-header">
        <div class="ap-header-left">
          <span class="ap-logo">
            <span class="ap-logo-t">T</span>
            Assistant TraceAI
          </span>
          <span class="ap-source">Sourcé sur {{ project?.pdf_filename }}</span>
        </div>
        <button class="ap-close" @click="emit('close')">✕</button>
      </div>

      <div class="ap-body">

        <!-- Colonne gauche : contexte + suggestions + sections -->
        <div class="ap-sidebar">
          <!-- Contexte actif -->
          <div v-if="activeStep" class="ap-context">
            <span class="ap-ctx-label">Contexte actif</span>
            <span class="ap-ctx-step">Étape {{ activeStep.step_number }} — {{ activeStep.title }}</span>
          </div>

          <!-- Suggestions -->
          <div class="ap-section">
            <span class="ap-section-title">Suggestions</span>
            <div class="ap-suggestions">
              <button
                v-for="s in suggestions"
                :key="s"
                class="ap-suggest-btn"
                @click="send(s)"
              >{{ s }}</button>
            </div>
          </div>

          <!-- Sections du manuel -->
          <div class="ap-section" v-if="sections.length">
            <span class="ap-section-title">Sections du manuel</span>
            <div class="ap-sections-list">
              <button
                v-for="cat in sections"
                :key="cat"
                class="ap-section-btn"
                @click="send(`Explique la section ${cat} du manuel`)"
              >{{ cat }}</button>
            </div>
          </div>

          <div class="ap-disclaimer">
            Les réponses citent la page source — vérifiables dans le PDF.
          </div>
        </div>

        <!-- Colonne droite : chat -->
        <div class="ap-chat">
          <div class="ap-messages" ref="messagesEl">
            <div
              v-for="(msg, i) in messages"
              :key="i"
              class="ap-msg"
              :class="msg.role"
            >
              <div
                v-if="msg.role === 'assistant'"
                class="ap-bubble"
                :class="{ error: msg.error }"
                v-html="formatText(msg.text)"
                @click="handleInlineClick"
              />
              <div v-else class="ap-bubble user-bubble">{{ msg.text }}</div>

              <!-- Sources -->
              <div v-if="msg.sources?.length" class="ap-sources">
                <span class="ap-sources-label">Sources</span>
                <div class="ap-source-chips">
                  <button
                    v-for="src in msg.sources"
                    :key="src.page"
                    class="ap-source-chip"
                    @click="emit('open-pdf', src.page)"
                  >
                    p.{{ src.page }} · {{ src.label }}
                  </button>
                </div>
              </div>
            </div>

            <!-- Indicateur de chargement -->
            <div v-if="loading" class="ap-msg assistant">
              <div class="ap-bubble ap-typing">
                <span class="ap-dot" /><span class="ap-dot" /><span class="ap-dot" />
              </div>
            </div>
          </div>

          <!-- Input -->
          <div class="ap-input-bar">
            <textarea
              v-model="input"
              class="ap-input"
              placeholder="Pose ta question sur le manuel…"
              rows="2"
              @keydown.enter.prevent="send()"
            />
            <button
              class="ap-send-btn"
              :disabled="!input.trim() || loading"
              @click="send()"
            >Envoyer ↵</button>
          </div>
        </div>

      </div>
    </div>
  </div>
</template>

<style scoped>
.ap-overlay {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.45);
  z-index: 200;
  display: flex;
  align-items: stretch;
  justify-content: flex-end;
}

.ap-panel {
  width: min(860px, 96vw);
  background: var(--paper);
  display: flex;
  flex-direction: column;
  height: 100vh;
  box-shadow: -8px 0 40px rgba(0,0,0,0.2);
}

/* Header */
.ap-header {
  height: 52px;
  background: var(--ink);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 18px;
  flex-shrink: 0;
}
.ap-header-left { display: flex; flex-direction: column; gap: 1px; }
.ap-logo {
  display: flex; align-items: center; gap: 7px;
  font-family: var(--font-mono); font-size: 13px; font-weight: 700; color: #fff;
}
.ap-logo-t {
  background: var(--amber); color: var(--ink);
  width: 18px; height: 18px;
  display: flex; align-items: center; justify-content: center;
  border-radius: 2px; font-size: 11px;
}
.ap-source { font-family: var(--font-mono); font-size: 9px; color: rgba(255,255,255,0.4); }
.ap-close {
  background: rgba(255,255,255,0.1); border: none; color: #fff;
  width: 28px; height: 28px; border-radius: 3px; cursor: pointer; font-size: 13px;
}
.ap-close:hover { background: rgba(255,255,255,0.2); }

/* Body layout */
.ap-body {
  flex: 1;
  display: flex;
  overflow: hidden;
}

/* Sidebar */
.ap-sidebar {
  width: 220px;
  flex-shrink: 0;
  border-right: 1px solid var(--rule);
  background: var(--paperAlt);
  display: flex;
  flex-direction: column;
  gap: 0;
  overflow-y: auto;
  padding: 14px 0;
}

.ap-context {
  margin: 0 12px 14px;
  padding: 10px 12px;
  background: var(--tealBg);
  border: 1px solid var(--teal);
  border-radius: 3px;
  display: flex; flex-direction: column; gap: 3px;
}
.ap-ctx-label { font-family: var(--font-mono); font-size: 9px; font-weight: 600; text-transform: uppercase; letter-spacing: .08em; color: var(--teal); }
.ap-ctx-step { font-size: 11px; color: var(--teal); font-weight: 550; line-height: 1.3; }

.ap-section { padding: 0 12px 14px; display: flex; flex-direction: column; gap: 7px; }
.ap-section-title { font-family: var(--font-mono); font-size: 9px; font-weight: 600; text-transform: uppercase; letter-spacing: .08em; color: var(--inkMute); }

.ap-suggestions { display: flex; flex-direction: column; gap: 4px; }
.ap-suggest-btn {
  text-align: left; background: var(--paper); border: 1px solid var(--rule);
  border-radius: 2px; padding: 7px 9px; font-size: 11.5px; color: var(--ink);
  cursor: pointer; line-height: 1.35; font-family: inherit;
}
.ap-suggest-btn:hover { border-color: var(--ink); background: var(--paperAlt); }

.ap-sections-list { display: flex; flex-direction: column; gap: 2px; }
.ap-section-btn {
  text-align: left; background: transparent; border: none;
  padding: 5px 8px; font-size: 11.5px; color: var(--inkSoft);
  cursor: pointer; border-radius: 2px; font-family: inherit;
  text-transform: capitalize;
}
.ap-section-btn:hover { background: var(--ruleSoft); color: var(--ink); }

.ap-disclaimer {
  margin-top: auto;
  padding: 12px 14px;
  font-size: 10px;
  color: var(--inkMute);
  font-style: italic;
  line-height: 1.4;
  border-top: 1px solid var(--ruleSoft);
}

/* Chat */
.ap-chat {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.ap-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.ap-msg { display: flex; flex-direction: column; gap: 6px; }
.ap-msg.user { align-items: flex-end; }
.ap-msg.assistant { align-items: flex-start; }

.ap-bubble {
  max-width: 88%;
  padding: 11px 14px;
  border-radius: 3px;
  font-size: 13px;
  line-height: 1.55;
  color: var(--ink);
  background: var(--paperAlt);
  border: 1px solid var(--ruleSoft);
}
.ap-bubble.user-bubble {
  background: var(--ink);
  color: var(--paper);
  border-color: var(--ink);
}
.ap-bubble.error { background: var(--redBg); border-color: var(--red); color: var(--red); }

/* Styles inline pour les références [p.X] */
:deep(.src-inline) {
  display: inline-flex; align-items: center;
  font-family: var(--font-mono); font-size: 10px; font-weight: 600;
  padding: 1px 5px; border-radius: 2px;
  background: var(--tealBg); color: var(--teal);
  border: 1px solid var(--teal); cursor: pointer;
  vertical-align: middle; margin: 0 1px;
}
:deep(.src-inline:hover) { background: var(--teal); color: #fff; }

/* Typing indicator */
.ap-typing { display: flex; align-items: center; gap: 5px; padding: 12px 14px; }
.ap-dot {
  width: 6px; height: 6px; border-radius: 50%; background: var(--inkMute);
  animation: ap-bounce 1.2s ease-in-out infinite;
}
.ap-dot:nth-child(2) { animation-delay: .2s; }
.ap-dot:nth-child(3) { animation-delay: .4s; }
@keyframes ap-bounce {
  0%, 80%, 100% { transform: translateY(0); opacity: .5; }
  40%            { transform: translateY(-5px); opacity: 1; }
}

/* Sources */
.ap-sources { display: flex; flex-direction: column; gap: 5px; max-width: 88%; }
.ap-sources-label { font-family: var(--font-mono); font-size: 9px; text-transform: uppercase; letter-spacing: .08em; color: var(--inkMute); font-weight: 600; }
.ap-source-chips { display: flex; flex-wrap: wrap; gap: 5px; }
.ap-source-chip {
  font-family: var(--font-mono); font-size: 10px; padding: 3px 8px;
  background: var(--paperAlt); border: 1px solid var(--rule);
  border-radius: 2px; color: var(--inkSoft); cursor: pointer;
  white-space: nowrap;
}
.ap-source-chip:hover { border-color: var(--teal); color: var(--teal); background: var(--tealBg); }

/* Input bar */
.ap-input-bar {
  padding: 12px 16px;
  border-top: 1px solid var(--rule);
  background: var(--paperAlt);
  display: flex;
  gap: 10px;
  align-items: flex-end;
}
.ap-input {
  flex: 1;
  border: 1px solid var(--rule);
  border-radius: 3px;
  padding: 9px 12px;
  font-family: inherit;
  font-size: 13.5px;
  color: var(--ink);
  background: var(--paper);
  resize: none;
  outline: none;
  line-height: 1.4;
}
.ap-input:focus { border-color: var(--ink); }
.ap-send-btn {
  padding: 10px 16px;
  background: var(--ink); color: var(--paper);
  border: none; border-radius: 3px;
  font-size: 13px; font-weight: 600; cursor: pointer;
  white-space: nowrap; flex-shrink: 0;
  font-family: var(--font-mono);
}
.ap-send-btn:disabled { opacity: 0.35; cursor: not-allowed; }
.ap-send-btn:not(:disabled):hover { opacity: 0.88; }
</style>
