<template>
  <div class="chat-wrap">
    <!-- Sidebar: conversations -->
    <div class="chat-sidebar">
      <div class="chat-sidebar-head">
        <span class="chat-mono chat-mute" style="font-size:10px;letter-spacing:.18em;text-transform:uppercase">Conversations</span>
        <button class="chat-new-btn" @click="newConversation" title="Nouvelle conversation">+</button>
      </div>
      <button v-for="c in conversations" :key="c.id"
        class="chat-conv-btn" :class="{ active: currentConvId === c.id }"
        @click="loadConversation(c.id)">
        <span class="chat-conv-icon">💬</span>
        <span class="chat-conv-title">{{ c.title || 'Conversation' }}</span>
      </button>
    </div>

    <!-- Main chat -->
    <div class="chat-main">
      <!-- Welcome state -->
      <div v-if="!messages.length" class="chat-welcome">
        <div class="chat-welcome-icon">🤖</div>
        <h2 class="chat-welcome-title">Machine Wiki Chatbot</h2>
        <p class="chat-welcome-sub">
          Posez une question sur vos machines. Je consulte le Machine Wiki compilé
          et les documents sources pour vous donner une réponse précise avec citations.
        </p>
        <!-- Suggestions -->
        <div class="chat-suggestions">
          <button v-for="s in suggestions" :key="s" class="chat-suggest" @click="sendSuggestion(s)">
            {{ s }}
          </button>
        </div>
      </div>

      <!-- Messages -->
      <div v-else ref="messagesEl" class="chat-messages">
        <div v-for="(msg, i) in messages" :key="i"
          class="chat-msg" :class="msg.role">
          <div class="chat-bubble">
            <div class="chat-bubble-content" v-html="formatMessage(msg.content)"/>
            <!-- Sources -->
            <div v-if="msg.role === 'assistant' && parseSources(msg.sources_json).length" class="chat-sources">
              <span class="chat-mono chat-mute" style="font-size:10px;letter-spacing:.1em">SOURCES</span>
              <div v-for="(s, si) in parseSources(msg.sources_json)" :key="si" class="chat-source-badge">
                {{ s.label || s.filename }}<span v-if="s.page"> · p.{{ s.page }}</span>
              </div>
            </div>
          </div>
        </div>
        <div v-if="loading" class="chat-msg assistant">
          <div class="chat-bubble chat-typing">
            <span class="chat-dot" v-for="n in 3" :key="n" :style="{ animationDelay: (n-1)*200+'ms' }"/>
          </div>
        </div>
      </div>

      <!-- Input -->
      <div class="chat-input-wrap">
        <div class="chat-input-box">
          <textarea
            v-model="question"
            class="chat-input"
            placeholder="Quel est le couple de serrage de la broche ?"
            rows="1"
            @keydown.enter.exact.prevent="send"
            @input="autoResize"
            ref="inputEl"
          />
          <button class="chat-send" :disabled="!question.trim() || loading" @click="send">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M22 2L11 13M22 2L15 22l-4-9-9-4 20-7z"/></svg>
          </button>
        </div>
        <div class="chat-mono chat-mute" style="font-size:10px;text-align:center;margin-top:6px">
          Entrée pour envoyer · Shift+Entrée pour nouvelle ligne
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted } from 'vue'
import api from '../services/api.js'

const props = defineProps({ projectId: { type: Number, required: true } })

const conversations = ref([])
const currentConvId = ref(null)
const messages = ref([])
const question = ref('')
const loading = ref(false)
const messagesEl = ref(null)
const inputEl = ref(null)

const suggestions = [
  'Quel est le couple de serrage recommandé pour la broche ?',
  'Quelle est la procédure de maintenance préventive à 500h ?',
  'Quels sont les pièces de rechange critiques ?',
]

function parseSources(json) {
  try { return JSON.parse(json || '[]') } catch { return [] }
}

function formatMessage(text) {
  if (!text) return ''
  return text
    .replace(/\[([^\]]+)\]/g, '<cite>[$1]</cite>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>')
}

function autoResize(e) {
  e.target.style.height = 'auto'
  e.target.style.height = Math.min(e.target.scrollHeight, 160) + 'px'
}

async function send() {
  const q = question.value.trim()
  if (!q || loading.value) return
  question.value = ''
  if (inputEl.value) inputEl.value.style.height = 'auto'

  messages.value.push({ role: 'user', content: q, sources_json: '[]' })
  loading.value = true
  await nextTick()
  scrollBottom()

  try {
    const res = await api.wikiChat(props.projectId, q, currentConvId.value)
    currentConvId.value = res.data.conversation_id
    messages.value.push({
      role: 'assistant',
      content: res.data.answer,
      sources_json: JSON.stringify(res.data.sources),
    })
    loadConversationList()
  } catch (e) {
    messages.value.push({ role: 'assistant', content: "Erreur — réessaie dans quelques instants.", sources_json: '[]' })
  } finally {
    loading.value = false
    await nextTick()
    scrollBottom()
  }
}

async function sendSuggestion(s) {
  question.value = s
  await send()
}

function scrollBottom() {
  if (messagesEl.value) messagesEl.value.scrollTop = messagesEl.value.scrollHeight
}

function newConversation() {
  currentConvId.value = null
  messages.value = []
}

async function loadConversation(id) {
  currentConvId.value = id
  try {
    const res = await api.getMessages(id)
    messages.value = res.data
    await nextTick()
    scrollBottom()
  } catch (e) { /* ignore */ }
}

async function loadConversationList() {
  try {
    const res = await api.getConversations(props.projectId)
    conversations.value = res.data
  } catch (e) { /* ignore */ }
}

onMounted(loadConversationList)
</script>

<style scoped>
.chat-wrap { display:flex; height:100%; }
.chat-sidebar { width:220px; border-right:1px solid #EAE7DD; padding:16px 12px; flex-shrink:0; overflow:auto; }
.chat-sidebar-head { display:flex; align-items:center; justify-content:space-between; padding:0 4px 12px; border-bottom:1px solid #EAE7DD; margin-bottom:8px; }
.chat-new-btn { width:22px; height:22px; border:none; background:transparent; cursor:pointer; font-size:18px; color:#0E0E0C; line-height:1; border-radius:3px; display:flex; align-items:center; justify-content:center; }
.chat-new-btn:hover { background:#F2EFE6; }
.chat-conv-btn { width:100%; display:flex; align-items:center; gap:8px; padding:8px 10px; border:none; background:transparent; cursor:pointer; border-radius:4px; text-align:left; font-family:inherit; font-size:13px; color:#0E0E0C; }
.chat-conv-btn:hover { background:#F2EFE6; }
.chat-conv-btn.active { background:#EAE7DD; font-weight:600; }
.chat-conv-icon { font-size:13px; flex-shrink:0; }
.chat-conv-title { flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; font-size:12.5px; }
.chat-main { flex:1; display:flex; flex-direction:column; min-height:0; }
.chat-welcome { flex:1; display:flex; flex-direction:column; align-items:center; justify-content:center; padding:40px; text-align:center; }
.chat-welcome-icon { font-size:52px; margin-bottom:16px; }
.chat-welcome-title { font-size:22px; font-weight:700; margin:0 0 10px; }
.chat-welcome-sub { font-size:14px; color:#3D3D38; max-width:480px; line-height:1.6; margin:0 0 24px; }
.chat-suggestions { display:flex; flex-direction:column; gap:8px; width:100%; max-width:520px; }
.chat-suggest { padding:10px 16px; background:#fff; border:1px solid #EAE7DD; border-radius:4px; cursor:pointer; font-family:inherit; font-size:13px; color:#0E0E0C; text-align:left; transition:background .12s; }
.chat-suggest:hover { background:#F2EFE6; }
.chat-messages { flex:1; overflow:auto; padding:24px 32px; display:flex; flex-direction:column; gap:16px; }
.chat-msg { display:flex; }
.chat-msg.user { justify-content:flex-end; }
.chat-msg.assistant { justify-content:flex-start; }
.chat-bubble { max-width:70%; padding:12px 16px; border-radius:8px; font-size:14px; line-height:1.6; }
.chat-msg.user .chat-bubble { background:#1F6B5E; color:#fff; }
.chat-msg.assistant .chat-bubble { background:#fff; border:1px solid #EAE7DD; color:#0E0E0C; }
.chat-bubble-content :deep(cite) { font-family:'Geist Mono',monospace; font-size:11px; color:#7C7B73; font-style:normal; background:#F2EFE6; padding:0 3px; border-radius:2px; }
.chat-bubble-content :deep(strong) { font-weight:700; }
.chat-sources { margin-top:10px; padding-top:10px; border-top:1px solid #EAE7DD; display:flex; flex-wrap:wrap; gap:4px; align-items:center; }
.chat-source-badge { font-family:'Geist Mono',monospace; font-size:10px; color:#3D3D38; background:#F2EFE6; border:1px solid #EAE7DD; border-radius:2px; padding:1px 6px; }
.chat-typing { display:flex; align-items:center; gap:4px; padding:14px 18px; }
.chat-dot { width:6px; height:6px; border-radius:50%; background:#7C7B73; animation:chatDot 1.2s ease-in-out infinite; }
.chat-input-wrap { padding:16px 32px 20px; border-top:1px solid #EAE7DD; background:#FAFAF7; }
.chat-input-box { display:flex; align-items:flex-end; gap:10px; background:#fff; border:1px solid #EAE7DD; border-radius:8px; padding:8px 12px; }
.chat-input { flex:1; border:none; outline:none; resize:none; font-family:inherit; font-size:14px; line-height:1.5; background:transparent; color:#0E0E0C; max-height:160px; }
.chat-send { width:36px; height:36px; border-radius:6px; border:none; background:#1F6B5E; color:#fff; cursor:pointer; display:flex; align-items:center; justify-content:center; flex-shrink:0; transition:background .12s; }
.chat-send:hover:not(:disabled) { background:#1a5750; }
.chat-send:disabled { opacity:.4; cursor:not-allowed; }
.chat-mono { font-family:'Geist Mono',monospace; }
.chat-mute { color:#7C7B73; }
@keyframes chatDot { 0%,80%,100% { opacity:.3; transform:scale(.8); } 40% { opacity:1; transform:scale(1); } }
</style>
