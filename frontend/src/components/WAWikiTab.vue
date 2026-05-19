<template>
  <div class="waw-root">

    <!-- ─── Sidebar (25%) ────────────────────────────────────────────────── -->
    <div class="waw-sidebar">
      <div class="waw-sidebar-head">
        <span class="waw-mono waw-mute" style="font-size:10px;letter-spacing:.18em;text-transform:uppercase">Machine Wiki</span>
        <span v-if="healthIssues > 0" class="waw-warn-badge" :title="`${healthIssues} problème(s) détecté(s)`">⚠️ {{ healthIssues }}</span>
      </div>

      <!-- Recherche -->
      <div class="waw-search-box">
        <input v-model="searchQuery" class="waw-search-input" placeholder="Rechercher dans le wiki…" />
      </div>

      <!-- Section Overview -->
      <button class="waw-nav-item" :class="{ active: selectedId === '__overview' }"
        @click="selectOverview">
        <span class="waw-nav-icon">📋</span>
        Vue d'ensemble
      </button>

      <div v-if="machinePages.length" class="waw-section-label waw-mono waw-mute">Machines</div>

      <!-- Dropdown ou liste machines -->
      <template v-if="machinePages.length > 6">
        <select v-model="selectedId" class="waw-machine-select" @change="loadSelectedPage">
          <option value="">Sélectionner une machine…</option>
          <option v-for="p in filteredMachines" :key="p.id" :value="String(p.id)">
            {{ p.title }}
          </option>
        </select>
      </template>
      <template v-else>
        <button v-for="p in filteredMachines" :key="p.id"
          class="waw-nav-item" :class="{ active: selectedId === String(p.id) }"
          @click="loadPage(p.id)">
          <span class="waw-nav-icon">🔧</span>
          <span class="waw-nav-label">{{ p.title }}</span>
          <span v-if="hasIssues(p)" class="waw-warn-dot" title="Contradictions/lacunes">⚠</span>
        </button>
      </template>

      <!-- Autres pages -->
      <template v-if="otherPages.length && !searchQuery">
        <div class="waw-section-label waw-mono waw-mute">Autres pages</div>
        <button v-for="p in otherPages.slice(0,8)" :key="p.id"
          class="waw-nav-item" :class="{ active: selectedId === String(p.id) }"
          @click="loadPage(p.id)">
          <span class="waw-nav-icon">{{ pageIcon(p.page_type) }}</span>
          <span class="waw-nav-label">{{ p.title }}</span>
        </button>
      </template>

      <div v-if="!pages.length && !loadingPages" class="waw-empty-nav">
        <span class="waw-mono waw-mute" style="font-size:12px">Aucune page wiki disponible</span>
        <button class="waw-btn-heal" @click="runHeal">Auto-réparer le wiki</button>
      </div>
    </div>

    <!-- ─── Contenu (75%) ───────────────────────────────────────────────── -->
    <div class="waw-content">

      <div v-if="loadingPage" class="waw-placeholder">
        <div class="waw-loading-dots">
          <span v-for="n in 3" :key="n" class="waw-dot" :style="{ animationDelay: (n-1)*200+'ms' }" />
        </div>
      </div>

      <div v-else-if="!selectedPage" class="waw-placeholder">
        <div style="font-size:44px;margin-bottom:16px">📚</div>
        <div style="font-size:18px;font-weight:600;margin-bottom:8px">Machine Wiki</div>
        <div class="waw-mono waw-mute" style="font-size:13px">Sélectionnez une page dans le panneau gauche</div>
      </div>

      <template v-else>
        <!-- En-tête page -->
        <div class="waw-page-head">
          <div class="waw-page-title-row">
            <h1 class="waw-page-title">{{ selectedPage.title }}</h1>
            <div class="waw-page-actions">
              <button class="waw-btn-action" @click="emit('go-graph')" title="Voir dans le graphe">
                ↗ Graphe
              </button>
            </div>
          </div>
          <div class="waw-page-meta waw-mono waw-mute">
            <span v-if="selectedPage.last_compiled_at">Mis à jour {{ formatDate(selectedPage.last_compiled_at) }}</span>
            <span v-if="selectedPage.page_type" class="waw-type-chip">{{ selectedPage.page_type }}</span>
          </div>
        </div>

        <!-- Bannière contradictions -->
        <div v-if="(selectedPage.contradictions || []).length" class="waw-banner waw-banner-warn">
          <strong>⚠️ {{ selectedPage.contradictions.length }} contradiction{{ selectedPage.contradictions.length !== 1 ? 's' : '' }}</strong>
          <div v-for="(c, i) in selectedPage.contradictions" :key="i" class="waw-contradiction">
            <span class="waw-mono" style="font-size:10px">{{ c.topic }}</span> —
            {{ c.src_a }} : <strong>{{ c.val_a }}</strong> vs {{ c.src_b }} : <strong>{{ c.val_b }}</strong>
          </div>
        </div>

        <!-- Bannière lacunes -->
        <div v-if="(selectedPage.gaps || []).length" class="waw-banner waw-banner-info">
          <strong>❓ {{ selectedPage.gaps.length }} lacune{{ selectedPage.gaps.length !== 1 ? 's' : '' }}</strong>
          <ul style="margin:6px 0 0;padding-left:16px">
            <li v-for="(g, i) in selectedPage.gaps" :key="i">{{ g }}</li>
          </ul>
        </div>

        <!-- Contenu markdown -->
        <div class="waw-md" v-html="renderedContent" />
      </template>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import api from '../services/api.js'

const props = defineProps({
  projectId: { type: Number, required: true },
  initialPage: { type: String, default: null },
})

const emit = defineEmits(['go-graph'])

// ── État ──────────────────────────────────────────────────────────────────────
const pages = ref([])
const selectedId = ref('')
const selectedPage = ref(null)
const overviewContent = ref('')
const loadingPages = ref(false)
const loadingPage = ref(false)
const searchQuery = ref('')
const healthIssues = ref(0)

// ── Computed ──────────────────────────────────────────────────────────────────
const machinePages = computed(() =>
  pages.value.filter(p => p.page_type === 'machine' || !p.page_type)
)

const otherPages = computed(() =>
  pages.value.filter(p => p.page_type && p.page_type !== 'machine')
)

const filteredMachines = computed(() => {
  if (!searchQuery.value) return machinePages.value
  const q = searchQuery.value.toLowerCase()
  return machinePages.value.filter(p => p.title?.toLowerCase().includes(q))
})

const renderedContent = computed(() => {
  if (!selectedPage.value) return ''
  if (selectedId.value === '__overview') return renderMarkdown(overviewContent.value)
  return renderMarkdown(selectedPage.value.content_md || selectedPage.value.content || '')
})

// ── Chargement ────────────────────────────────────────────────────────────────
async function loadPages() {
  loadingPages.value = true
  try {
    const res = await api.getWikiIndex(props.projectId)
    pages.value = res.data || []
  } catch { /* ignore */ } finally {
    loadingPages.value = false
  }
}

async function loadHealth() {
  try {
    const res = await api.wikiHealth(props.projectId)
    healthIssues.value = res.data?.total_issues || 0
  } catch { /* ignore */ }
}

async function loadPage(id) {
  selectedId.value = String(id)
  selectedPage.value = null
  loadingPage.value = true
  try {
    const res = await api.getWikiPage(id)
    selectedPage.value = res.data
  } catch { /* ignore */ } finally {
    loadingPage.value = false
  }
}

async function selectOverview() {
  selectedId.value = '__overview'
  selectedPage.value = null
  loadingPage.value = true
  try {
    const res = await api.wikiOverview(props.projectId)
    overviewContent.value = res.data?.content || ''
    selectedPage.value = {
      title: 'Vue d\'ensemble',
      page_type: 'overview',
      content_md: overviewContent.value,
      last_compiled_at: null,
    }
  } catch { /* ignore */ } finally {
    loadingPage.value = false
  }
}

function loadSelectedPage() {
  if (!selectedId.value || selectedId.value === '__overview') return
  const id = parseInt(selectedId.value)
  if (!isNaN(id)) loadPage(id)
}

async function runHeal() {
  try {
    await api.wikiHeal(props.projectId)
    await loadPages()
  } catch { /* ignore */ }
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function hasIssues(p) {
  return (p.contradictions_count > 0) || (p.gaps_count > 0)
}

function pageIcon(type) {
  const m = { machine:'🔧', entity:'🏭', concept:'💡', source:'📄', synthesis:'📝' }
  return m[type] || '📄'
}

function formatDate(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString('fr-FR', { day:'2-digit', month:'short', hour:'2-digit', minute:'2-digit' })
}

// ── Rendu Markdown ─────────────────────────────────────────────────────────
function renderMarkdown(text) {
  if (!text) return ''
  let html = text

  // Wikilinks [[name]] → chip
  html = html.replace(/\[\[([^\]]+?)\]\]/g, (_, name) =>
    `<span class="waw-wikilink">🔧 ${name}</span>`
  )

  // Source badges [doc p.N]
  html = html.replace(/\[([^\]]{1,60}?)\s+p\.(\d+)\]/g, (_, doc, page) =>
    `<span class="waw-src-badge">📄 ${doc} p.${page}</span>`
  )

  // Tableaux markdown
  html = renderTables(html)

  // Bold / italic
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>')

  // Titres
  html = html.replace(/^#### (.+)$/gm, '<h5 class="waw-h5">$1</h5>')
  html = html.replace(/^### (.+)$/gm, '<h4 class="waw-h4">$1</h4>')
  html = html.replace(/^## (.+)$/gm, '<h3 class="waw-h3">$1</h3>')
  html = html.replace(/^# (.+)$/gm, '<h2 class="waw-h2">$1</h2>')

  // Listes
  html = html.replace(/^- (.+)$/gm, '<li>$1</li>')

  // Sauts de ligne (hors blocs déjà traités)
  html = html.replace(/\n/g, '<br>')

  return html
}

function renderTables(text) {
  // Détecte bloc de tableau markdown | col | col |
  return text.replace(/((?:\|[^\n]+\|\n)+)/g, (match) => {
    const rows = match.trim().split('\n').filter(Boolean)
    if (rows.length < 2) return match
    let html = '<div class="waw-table-wrap"><table class="waw-table">'
    rows.forEach((row, i) => {
      // Ligne séparatrice |---|---| → skip
      if (/^\|[\s\-:]+\|/.test(row)) return
      const cells = row.split('|').filter((_, ci) => ci > 0 && ci < row.split('|').length - 1)
      const tag = i === 0 ? 'th' : 'td'
      html += `<tr>${cells.map(c => `<${tag}>${c.trim()}</${tag}>`).join('')}</tr>`
    })
    html += '</table></div>'
    return html
  })
}

// ── Mount & watch ─────────────────────────────────────────────────────────────
onMounted(async () => {
  await Promise.all([loadPages(), loadHealth()])
  if (props.initialPage) {
    const found = pages.value.find(p =>
      p.title?.toLowerCase() === props.initialPage.toLowerCase()
    )
    if (found) loadPage(found.id)
    else selectOverview()
  } else {
    selectOverview()
  }
})

watch(() => props.initialPage, (name) => {
  if (!name) return
  const found = pages.value.find(p => p.title?.toLowerCase() === name.toLowerCase())
  if (found) loadPage(found.id)
})
</script>

<style scoped>
.waw-root { display: flex; height: 100%; overflow: hidden; }

/* ─── Sidebar ──────────────────────────────────────────────────────────────── */
.waw-sidebar {
  width: 240px;
  border-right: 1px solid var(--rule);
  background: var(--paper);
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.waw-sidebar-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px 10px;
  border-bottom: 1px solid var(--rule);
  flex-shrink: 0;
}
.waw-warn-badge {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--amber);
  background: var(--amberBg);
  border: 1px solid var(--amber);
  border-radius: 2px;
  padding: 1px 5px;
  font-weight: 600;
}

.waw-search-box { padding: 10px 12px; border-bottom: 1px solid var(--ruleSoft); flex-shrink: 0; }
.waw-search-input {
  width: 100%;
  padding: 7px 10px;
  background: var(--paperAlt);
  border: 1px solid var(--rule);
  border-radius: 3px;
  font-family: var(--font-sans);
  font-size: 12.5px;
  color: var(--ink);
  outline: none;
}
.waw-search-input:focus { border-color: var(--inkMute); }

.waw-section-label {
  padding: 8px 16px 4px;
  font-size: 9.5px;
  letter-spacing: .14em;
  text-transform: uppercase;
  flex-shrink: 0;
}

.waw-nav-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  border: none;
  background: transparent;
  cursor: pointer;
  font-family: var(--font-sans);
  font-size: 13px;
  color: var(--inkSoft);
  text-align: left;
  width: 100%;
  flex-shrink: 0;
}
.waw-nav-item:hover { background: var(--ruleSoft); }
.waw-nav-item.active { background: var(--ruleSoft); color: var(--ink); font-weight: 600; }
.waw-nav-icon { font-size: 13px; flex-shrink: 0; }
.waw-nav-label { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.waw-warn-dot { color: var(--amber); font-size: 11px; flex-shrink: 0; }

.waw-machine-select {
  margin: 6px 12px;
  width: calc(100% - 24px);
  padding: 7px 10px;
  background: var(--paperAlt);
  border: 1px solid var(--rule);
  border-radius: 3px;
  font-family: var(--font-sans);
  font-size: 13px;
  color: var(--ink);
  outline: none;
  cursor: pointer;
  flex-shrink: 0;
}

.waw-empty-nav {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 20px;
}
.waw-btn-heal {
  padding: 7px 12px;
  background: transparent;
  border: 1px solid var(--rule);
  border-radius: 3px;
  cursor: pointer;
  font-family: var(--font-sans);
  font-size: 12px;
  color: var(--inkSoft);
}
.waw-btn-heal:hover { background: var(--ruleSoft); }

/* ─── Contenu ──────────────────────────────────────────────────────────────── */
.waw-content {
  flex: 1;
  overflow-y: auto;
  padding: 28px 36px;
  min-width: 0;
}
.waw-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  text-align: center;
  padding: 40px;
}
.waw-loading-dots { display: flex; gap: 6px; }
.waw-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--inkMute);
  animation: wawDot 1.2s ease-in-out infinite;
}
@keyframes wawDot {
  0%, 80%, 100% { opacity: .3; transform: scale(.8); }
  40%           { opacity: 1;  transform: scale(1); }
}

.waw-page-head { margin-bottom: 20px; }
.waw-page-title-row { display: flex; align-items: flex-start; gap: 16px; margin-bottom: 8px; }
.waw-page-title { flex: 1; font-size: 24px; font-weight: 700; letter-spacing: -.02em; margin: 0; }
.waw-page-actions { display: flex; gap: 8px; flex-shrink: 0; }
.waw-btn-action {
  padding: 6px 12px;
  background: transparent;
  border: 1px solid var(--rule);
  border-radius: 3px;
  cursor: pointer;
  font-size: 12px;
  font-weight: 550;
  color: var(--inkSoft);
  white-space: nowrap;
}
.waw-btn-action:hover { background: var(--ruleSoft); }
.waw-page-meta { display: flex; align-items: center; gap: 10px; font-size: 11px; }
.waw-type-chip {
  padding: 2px 7px;
  background: var(--paper);
  border: 1px solid var(--rule);
  border-radius: 2px;
  font-size: 10px;
  font-weight: 600;
  letter-spacing: .1em;
  text-transform: uppercase;
  color: var(--inkMute);
}

/* Bannières */
.waw-banner {
  padding: 12px 16px;
  border-radius: 4px;
  margin-bottom: 16px;
  font-size: 13px;
  line-height: 1.55;
}
.waw-banner-warn { background: var(--amberBg); border: 1px solid color-mix(in srgb, var(--amber) 40%, transparent); border-left: 3px solid var(--amber); }
.waw-banner-info { background: var(--tealBg); border: 1px solid color-mix(in srgb, var(--teal) 30%, transparent); border-left: 3px solid var(--teal); }
.waw-contradiction { margin-top: 6px; font-size: 12px; }

/* Markdown content */
.waw-md { font-size: 14px; line-height: 1.7; color: var(--ink); }
.waw-md :deep(.waw-h2) { font-size: 20px; font-weight: 700; margin: 24px 0 10px; letter-spacing: -.01em; }
.waw-md :deep(.waw-h3) { font-size: 17px; font-weight: 700; margin: 18px 0 8px; }
.waw-md :deep(.waw-h4) { font-size: 15px; font-weight: 700; margin: 14px 0 6px; }
.waw-md :deep(.waw-h5) { font-size: 13.5px; font-weight: 700; margin: 10px 0 5px; }
.waw-md :deep(strong) { font-weight: 700; }
.waw-md :deep(em) { font-style: italic; }
.waw-md :deep(ul) { padding-left: 20px; margin: 8px 0; }
.waw-md :deep(li) { margin: 4px 0; }

.waw-md :deep(.waw-wikilink) {
  display: inline-block;
  font-size: 12px;
  font-weight: 600;
  padding: 2px 8px;
  background: color-mix(in srgb, var(--blue) 10%, transparent);
  border: 1px solid color-mix(in srgb, var(--blue) 30%, transparent);
  color: var(--blue);
  border-radius: 3px;
  margin: 0 2px;
  cursor: default;
}
.waw-md :deep(.waw-src-badge) {
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

/* Tableau specs */
.waw-md :deep(.waw-table-wrap) { overflow-x: auto; margin: 16px 0; }
.waw-md :deep(.waw-table) { width: 100%; border-collapse: collapse; font-size: 13px; }
.waw-md :deep(.waw-table th) {
  padding: 8px 12px;
  text-align: left;
  font-family: var(--font-mono);
  font-size: 9.5px;
  font-weight: 700;
  letter-spacing: .12em;
  text-transform: uppercase;
  color: var(--inkMute);
  background: var(--paper);
  border-bottom: 2px solid var(--rule);
}
.waw-md :deep(.waw-table td) {
  padding: 8px 12px;
  border-bottom: 1px solid var(--ruleSoft);
  vertical-align: top;
}
.waw-md :deep(.waw-table tr:last-child td) { border-bottom: none; }
.waw-md :deep(.waw-table tr:hover td) { background: var(--paperAlt); }

/* Utilitaires */
.waw-mono { font-family: var(--font-mono); }
.waw-mute { color: var(--inkMute); }
</style>
