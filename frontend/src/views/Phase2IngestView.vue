<template>
  <div class="p2-root">
    <!-- Header -->
    <header class="p2-header">
      <div class="p2-wm">
        <span class="p2-wm-box">T</span>
        Trace<span class="p2-wm-accent">AI</span>
        <span class="p2-wm-badge">back office</span>
      </div>
      <span class="p2-sep"/>
      <div>
        <div class="p2-proj-name">{{ projectName }}</div>
        <div class="p2-proj-sub">{{ docCount }} document{{ docCount !== 1 ? 's' : '' }} · {{ machineCount }} machine{{ machineCount !== 1 ? 's' : '' }}</div>
      </div>
      <div style="flex:1"/>
      <!-- Tabs -->
      <nav class="p2-tabs">
        <button v-for="t in TABS" :key="t.id"
          :class="['p2-tab', { active: activeTab === t.id }]"
          @click="activeTab = t.id">
          {{ t.label }}
          <span v-if="t.count != null" class="p2-tab-count">{{ t.count }}</span>
        </button>
      </nav>
      <span v-if="batchRunning" class="p2-live-badge">
        <span class="p2-live-dot"/>
        batch en cours
      </span>
    </header>

    <!-- Upload screen (no active batch or completed) -->
    <div v-if="activeTab === 'ingest' && !batchRunning" class="p2-upload-wrap">
      <div class="p2-upload-inner">
        <div class="p2-eyebrow">Phase 2 · Machine Wiki Agentique</div>
        <h1 class="p2-h1">Alimenter la base de connaissances</h1>
        <p class="p2-lead">
          Dépose manuels constructeur, rapports d'intervention, plans, photos, URLs.
          Les 10 agents compilent automatiquement un Machine Wiki interrogeable.
        </p>

        <div class="p2-upload-grid">
          <!-- Drop zone -->
          <div class="p2-dropzone"
               :class="{ dragging: isDragging }"
               @dragover.prevent="isDragging = true"
               @dragleave="isDragging = false"
               @drop.prevent="onDrop">
            <div class="p2-doc-stack">
              <div v-for="i in 3" :key="i" class="p2-doc-sheet" :style="{ left: (i-1)*6+'px', top: (i-1)*4+'px' }"/>
            </div>
            <div class="p2-drop-text">
              <strong>Glisse un ZIP, un dossier, des fichiers</strong>
              <span class="p2-drop-sub">PDF · DOCX · XLSX · images · ZIP — max 500 Mo par lot</span>
            </div>
            <label class="p2-btn-outline">
              Parcourir le poste
              <input type="file" multiple style="display:none" @change="onFileChange"/>
            </label>
          </div>

          <!-- URL ingestion -->
          <div class="p2-url-panel">
            <div class="p2-eyebrow">Depuis le web</div>
            <div class="p2-url-title">Catalogue, doc constructeur, wiki interne</div>
            <div class="p2-url-hint">Une URL par ligne.</div>
            <textarea v-model="urlsText" class="p2-url-input"
              placeholder="https://www.dmgmori.com/products/&#10;https://intranet/wiki/atelier3"
              rows="5"/>
            <button class="p2-btn-primary" @click="addUrls" style="margin-top:8px">
              Ajouter au lot
            </button>
          </div>
        </div>

        <!-- File list -->
        <div v-if="droppedFiles.length > 0" class="p2-filelist-wrap">
          <div class="p2-filelist-header">
            <span class="p2-eyebrow">À traiter · {{ droppedFiles.length }} fichier{{ droppedFiles.length !== 1 ? 's' : '' }}</span>
            <div class="p2-rule"/>
          </div>
          <div class="p2-filelist">
            <div v-for="(f, i) in droppedFiles" :key="i" class="p2-filerow">
              <div class="p2-file-icon" :style="{ color: fileColor(f) }">
                {{ fileExt(f).toUpperCase() }}
              </div>
              <div class="p2-file-info">
                <div class="p2-file-name">{{ f.name }}</div>
                <div class="p2-file-meta">{{ formatSize(f.size) }}</div>
              </div>
              <span class="p2-file-status">Prêt</span>
              <button class="p2-remove" @click="droppedFiles.splice(i, 1)">✕</button>
            </div>
          </div>
          <div style="margin-top:18px; display:flex; align-items:center; gap:12px">
            <button class="p2-btn-launch" :disabled="launching" @click="launchBatch">
              {{ launching ? 'Lancement…' : '⚡ Lancer le batch · 10 agents' }}
            </button>
            <span class="p2-eta">temps estimé ≈ 8–12 min</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Batch running screen -->
    <div v-else-if="activeTab === 'ingest' && batchRunning && !batchDone" class="p2-batch-wrap">
      <!-- Stats header -->
      <div class="p2-stats-bar">
        <div class="p2-stat-main">
          <div class="p2-stat-title">
            <span class="p2-live-dot" style="background:#E89A2D"/>
            <span class="p2-mono p2-accent">Batch en cours</span>
          </div>
          <div class="p2-stat-name">Compilation du Machine Wiki — {{ projectName }}</div>
          <div class="p2-mono p2-mute" style="font-size:11px;margin-top:4px">
            Agent actif : <strong style="color:#E89A2D">{{ activeAgentIdx + 1 }}/10 — {{ activeAgentName }}</strong>
            <span v-if="etaText" style="margin-left:10px">· ETA {{ etaText }}</span>
          </div>
        </div>
        <div class="p2-stat-box">
          <div class="p2-mono p2-mute" style="font-size:9px;letter-spacing:.18em;text-transform:uppercase">Progression</div>
          <div class="p2-mono p2-ink" style="font-size:28px;font-weight:600;margin-top:6px">{{ overallPct }}%</div>
          <div class="p2-mono p2-soft" style="font-size:10px">{{ doneAgents }}/10 agents</div>
        </div>
        <div class="p2-stat-box">
          <div class="p2-mono p2-mute" style="font-size:9px;letter-spacing:.18em;text-transform:uppercase">Fichiers</div>
          <div class="p2-mono p2-ink" style="font-size:28px;font-weight:600;margin-top:6px">{{ job.processed_files }}/{{ job.total_files }}</div>
          <div class="p2-mono p2-soft" style="font-size:10px">traités</div>
        </div>
        <div class="p2-stat-box">
          <div class="p2-mono p2-mute" style="font-size:9px;letter-spacing:.18em;text-transform:uppercase">Erreurs</div>
          <div class="p2-mono" :style="{ fontSize:'28px', fontWeight:600, marginTop:'6px', color: job.error_files ? '#C8482D' : '#7C7B73' }">{{ job.error_files }}</div>
          <div class="p2-mono p2-soft" style="font-size:10px">à inspecter</div>
        </div>
      </div>

      <!-- Pipeline visualization -->
      <div class="p2-pipeline-wrap">
        <div class="p2-pipeline-label">Pipeline · 10 agents PydanticAI</div>
        <div class="p2-pipeline">
          <div class="p2-pipeline-line"/>
          <div class="p2-pipeline-progress" :style="{ width: pipelineProgressWidth }"/>
          <div v-for="(agent, i) in AGENTS" :key="agent.key" class="p2-node">
            <div class="p2-node-dot" :class="agentStatus(agent.key)">
              <span v-if="agentStatus(agent.key) === 'spinning'" class="p2-spin-ring"/>
              <span v-if="agentStatus(agent.key) === 'done'" class="p2-check">✓</span>
              <span v-else class="p2-node-icon">{{ agent.icon }}</span>
              <span v-if="agent.hero && agentStatus(agent.key) === 'pending'" class="p2-hero-badge">★ WIKI</span>
            </div>
            <div class="p2-node-n">{{ String(agent.n).padStart(2,'0') }}</div>
            <div class="p2-node-name" :class="agentStatus(agent.key)">{{ agent.name }}</div>
            <div class="p2-node-counter">
              <template v-if="agentCounter(agent.key)">
                <span class="p2-mono" :style="{ fontSize: agentStatus(agent.key)==='running' ? '14px' : '11px', fontWeight:600, color: agentStatus(agent.key)==='running' ? '#E89A2D' : agentStatus(agent.key)==='done' ? '#1F6B5E' : '#0E0E0C' }">
                  {{ agentCounterValue(agent.key) }}
                </span>
                <span class="p2-mono p2-mute" style="font-size:9px;display:block;margin-top:1px">{{ agentCounterSub(agent.key) }}</span>
              </template>
              <span v-else class="p2-mono p2-faint" style="font-size:9px;text-transform:uppercase">{{ agent.short }}</span>
            </div>
            <div v-if="agentStatus(agent.key)==='running' && agentProgress(agent.key) != null" class="p2-node-bar">
              <div class="p2-node-bar-fill" :style="{ width: (agentProgress(agent.key)*100)+'%' }"/>
            </div>
          </div>
        </div>
      </div>

      <!-- Log console -->
      <div class="p2-log-wrap">
        <div class="p2-log-header">
          <span class="p2-mono p2-mute" style="font-size:10px;letter-spacing:.18em;text-transform:uppercase">Console batch · logs en direct</span>
          <div style="flex:1;height:1px;background:#F2EFE6;margin:0 12px"/>
          <span class="p2-rec-badge">
            <span style="width:5px;height:5px;border-radius:50%;background:#C8482D"/>
            <span class="p2-mono" style="font-size:9px;letter-spacing:.08em">REC</span>
          </span>
        </div>
        <div class="p2-console">
          <div v-if="!logLines.length" class="p2-log-line">
            <span class="p2-log-msg" style="color:#615E55">En attente des premiers logs…</span>
          </div>
          <div v-for="(line, i) in logLines" :key="i" class="p2-log-line">
            <span class="p2-log-time">{{ line.t }}</span>
            <span class="p2-log-lvl" :style="{ color: lvlColor(line.lvl) }">{{ line.lvl }}</span>
            <span class="p2-log-agent">[{{ line.agent }}]</span>
            <span class="p2-log-msg" :style="{ color: line.lvl === 'cur' ? '#F1ECE0' : '#C5C1B6' }">
              {{ line.msg }}<span v-if="line.lvl==='cur'" class="p2-cursor">_</span>
            </span>
          </div>
        </div>
        <div style="display:flex;gap:8px;margin-top:10px">
          <button class="p2-btn-cancel" @click="cancelBatch">Annuler le batch</button>
        </div>
      </div>
    </div>

    <!-- Completed screen -->
    <div v-else-if="activeTab === 'ingest' && batchDone" class="p2-done-wrap">
      <div class="p2-stats-bar">
        <div class="p2-stat-main">
          <div class="p2-stat-title">
            <span style="width:8px;height:8px;border-radius:50%;background:#1F6B5E;display:inline-block"/>
            <span class="p2-mono" style="color:#1F6B5E;letter-spacing:.18em;text-transform:uppercase;font-size:10px;font-weight:700">Batch terminé</span>
          </div>
          <div class="p2-stat-name">Machine Wiki prêt · {{ wikiMachineCount }} machines compilées</div>
          <div class="p2-mono p2-mute" style="font-size:11px;margin-top:4px">Les techniciens peuvent maintenant interroger le chatbot.</div>
        </div>
        <div class="p2-stat-box">
          <div class="p2-mono p2-mute" style="font-size:9px;letter-spacing:.18em;text-transform:uppercase">Couverture</div>
          <div class="p2-mono" style="font-size:28px;font-weight:600;margin-top:6px;color:#1F6B5E">{{ qualityScore }}%</div>
          <div class="p2-mono p2-soft" style="font-size:10px">RAGAS · ≥ 85% requis</div>
        </div>
        <div class="p2-stat-box">
          <div class="p2-mono p2-mute" style="font-size:9px;letter-spacing:.18em;text-transform:uppercase">Pages wiki</div>
          <div class="p2-mono p2-ink" style="font-size:28px;font-weight:600;margin-top:6px">{{ wikiMachineCount }}</div>
          <div class="p2-mono p2-soft" style="font-size:10px">machines</div>
        </div>
        <div class="p2-stat-box">
          <div class="p2-mono p2-mute" style="font-size:9px;letter-spacing:.18em;text-transform:uppercase">Alertes</div>
          <div class="p2-mono" style="font-size:28px;font-weight:600;margin-top:6px;color:#C8482D">{{ alertCount }}</div>
          <div class="p2-mono p2-soft" style="font-size:10px">à traiter</div>
        </div>
      </div>

      <!-- Pipeline terminé -->
      <div class="p2-pipeline-wrap">
        <div class="p2-pipeline-label">Pipeline · 10 agents · terminé</div>
        <div class="p2-pipeline">
          <div class="p2-pipeline-line"/>
          <div class="p2-pipeline-progress" style="width:calc(100% - 36px)"/>
          <div v-for="agent in AGENTS" :key="agent.key" class="p2-node">
            <div class="p2-node-dot done">
              <span class="p2-check">✓</span>
            </div>
            <div class="p2-node-n">{{ String(agent.n).padStart(2,'0') }}</div>
            <div class="p2-node-name done">{{ agent.name }}</div>
            <div class="p2-node-counter">
              <span class="p2-mono" style="font-size:11px;font-weight:600;color:#1F6B5E">
                {{ agentCounter(agent.key) || '✓' }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- Cards résultats -->
      <div class="p2-results-grid">
        <div class="p2-card">
          <div class="p2-card-head"><span>Pages générées</span><span class="p2-mono p2-mute" style="font-size:10px">{{ wikiMachineCount }} machines</span></div>
          <div v-for="p in wikiPages.slice(0,6)" :key="p.id" class="p2-wiki-row" @click="$router.push(`/project/${projectId}/wiki/${p.id}`)">
            <span class="p2-wiki-icon">📄</span>
            <span class="p2-wiki-name">{{ p.title }}</span>
            <span class="p2-mono p2-mute" style="font-size:10px">→</span>
          </div>
        </div>

        <div class="p2-card">
          <div class="p2-card-head"><span>Contradictions détectées</span><span class="p2-mono" style="font-size:10px;color:#E89A2D">par le Compilateur</span></div>
          <div v-for="(c, i) in contradictions.slice(0,3)" :key="i" class="p2-contradiction">
            <div class="p2-contradiction-topic">{{ c.topic || 'Valeur divergente' }}</div>
            <div class="p2-contradiction-detail">
              <strong>{{ c.src_a }}</strong> : {{ c.val_a }} · <strong>{{ c.src_b }}</strong> : {{ c.val_b }}
            </div>
          </div>
          <div v-if="!contradictions.length" class="p2-mono p2-mute" style="font-size:11px">Aucune contradiction détectée ✓</div>
        </div>

        <div class="p2-card">
          <div class="p2-card-head"><span>Lacunes</span><span class="p2-mono" style="font-size:10px;color:#C8482D">documents à fournir</span></div>
          <div v-for="(g, i) in gaps.slice(0,4)" :key="i" class="p2-gap">{{ g }}</div>
          <div v-if="!gaps.length" class="p2-mono p2-mute" style="font-size:11px">Aucune lacune identifiée ✓</div>
        </div>
      </div>
    </div>

    <!-- Other tabs placeholder -->
    <div v-else-if="activeTab === 'wiki'" class="p2-tab-content">
      <Phase2WikiTab :project-id="projectId"/>
    </div>
    <div v-else-if="activeTab === 'chat'" class="p2-tab-content">
      <Phase2ChatTab :project-id="projectId"/>
    </div>
    <div v-else-if="activeTab === 'alerts'" class="p2-tab-content">
      <Phase2AlertsTab :project-id="projectId" :count="alertCount" @dismissed="loadAlerts"/>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import api from '../services/api.js'
import Phase2WikiTab from '../components/Phase2WikiTab.vue'
import Phase2ChatTab from '../components/Phase2ChatTab.vue'
import Phase2AlertsTab from '../components/Phase2AlertsTab.vue'

const route = useRoute()
const projectId = parseInt(route.params.id)

const activeTab = ref('ingest')
const projectName = ref('Chargement…')
const docCount = ref(0)
const machineCount = ref(0)
const isDragging = ref(false)
const droppedFiles = ref([])
const urlsText = ref('')
const launching = ref(false)
const job = ref(null)
const wikiPages = ref([])
const alertCount = ref(0)
const logLines = ref([])
let pollTimer = null

const TABS = computed(() => [
  { id: 'ingest', label: 'Ingestion', count: null },
  { id: 'wiki',   label: 'Wiki',      count: wikiPages.value.length || null },
  { id: 'chat',   label: 'Chatbot',   count: null },
  { id: 'alerts', label: 'Alertes',   count: alertCount.value || null },
])

const AGENTS = [
  { n:1,  key:'arbo',  name:'Arborescence',  short:'Structure',    icon:'🌲', hero:false },
  { n:2,  key:'tri',   name:'Tri & Dédoubl.', short:'Hash·classe', icon:'⚖️', hero:false },
  { n:3,  key:'parse', name:'Parser',         short:'PDF·OCR',     icon:'📄', hero:false },
  { n:4,  key:'chunk', name:'Chunker',        short:'Sections',    icon:'✂️', hero:false },
  { n:5,  key:'enrch', name:'Enrichisseur',   short:'Keywords',    icon:'✨', hero:false },
  { n:6,  key:'index', name:'Indexeur',       short:'BGE-M3',      icon:'🗄️', hero:false },
  { n:7,  key:'compl', name:'Compilateur',    short:'Machine Wiki', icon:'📚', hero:true  },
  { n:8,  key:'qual',  name:'Qualité',        short:'RAGAS',       icon:'✅', hero:false },
  { n:9,  key:'rep',   name:'Répondeur',      short:'RAG hybride', icon:'💬', hero:false },
  { n:10, key:'alert', name:'Alertes',        short:'Patterns',    icon:'🔔', hero:false },
]

const batchRunning = computed(() => job.value && ['running'].includes(job.value.status))
const batchDone    = computed(() => job.value && job.value.status === 'done')

const agents = computed(() => job.value?.agents || {})
const doneAgents = computed(() => Object.values(agents.value).filter(a => a?.status === 'done').length)

const activeAgentIdx = computed(() => {
  const idx = AGENTS.findIndex(a => agents.value[a.key]?.status === 'running')
  return idx >= 0 ? idx : doneAgents.value
})
const activeAgentName = computed(() => AGENTS[activeAgentIdx.value]?.name || '')

const overallPct = computed(() => {
  const done = doneAgents.value
  const active = AGENTS[activeAgentIdx.value]
  const progress = active ? (agents.value[active.key]?.progress || 0) : 0
  return Math.round(((done + progress) / AGENTS.length) * 100)
})

const pipelineProgressWidth = computed(() => {
  const frac = (doneAgents.value + (agents.value[AGENTS[activeAgentIdx.value]?.key]?.progress || 0)) / (AGENTS.length - 1)
  return `calc((100% - 36px) * ${Math.min(frac, 1)})`
})

const contradictions = computed(() => wikiPages.value.flatMap(p => p.contradictions || []))
const gaps = computed(() => wikiPages.value.flatMap(p => p.gaps || []))
const wikiMachineCount = computed(() => wikiPages.value.filter(p => p.page_type === 'machine').length)
const qualityScore = ref(90)
const batchStartTime = ref(null)

const etaText = computed(() => {
  const enrch = agents.value['enrch']
  if (!enrch || enrch.status !== 'running') return ''
  const progress = enrch.progress || 0
  if (progress <= 0 || !batchStartTime.value) return ''
  const elapsed = (Date.now() - batchStartTime.value) / 1000
  const total = elapsed / progress
  const remaining = Math.round(total - elapsed)
  if (remaining < 60) return `${remaining}s`
  return `${Math.round(remaining / 60)} min`
})

function agentStatus(key) {
  const s = agents.value[key]?.status
  if (!s || s === 'pending') return 'pending'
  if (s === 'done') return 'done'
  if (s === 'running') return 'running'
  if (s === 'error') return 'error'
  return 'pending'
}
function agentCounter(key) { return agents.value[key]?.counter || '' }
function agentCounterValue(key) {
  const c = agentCounter(key)
  return c.split('·')[0].trim()
}
function agentCounterSub(key) {
  const c = agentCounter(key)
  const parts = c.split('·')
  return parts.slice(1).join('·').trim()
}
function agentProgress(key) { return agents.value[key]?.progress ?? null }

function lvlColor(lvl) {
  return lvl === 'ok' ? '#1F6B5E' : lvl === 'warn' ? '#E89A2D' : lvl === 'err' ? '#C8482D' : lvl === 'cur' ? '#E89A2D' : '#7C7B73'
}

function fileExt(f) { return f.name.split('.').pop()?.toUpperCase()?.slice(0,4) || 'FILE' }
function fileColor(f) {
  const ext = f.name.split('.').pop()?.toLowerCase()
  const map = { pdf:'#C8482D', docx:'#2A5DB0', xlsx:'#1F6B5E', zip:'#7C3F92', dwg:'#7C5A1B' }
  return map[ext] || '#7C7B73'
}
function formatSize(bytes) {
  if (bytes > 1024*1024) return (bytes/1024/1024).toFixed(1)+' Mo'
  return (bytes/1024).toFixed(0)+' ko'
}

function onDrop(e) {
  isDragging.value = false
  const files = Array.from(e.dataTransfer.files)
  droppedFiles.value = [...droppedFiles.value, ...files]
}
function onFileChange(e) {
  droppedFiles.value = [...droppedFiles.value, ...Array.from(e.target.files)]
}
function addUrls() {
  // URLs handled at launch time
}

async function launchBatch() {
  if (!droppedFiles.value.length && !urlsText.value.trim()) return
  launching.value = true
  try {
    const fd = new FormData()
    droppedFiles.value.forEach(f => fd.append('files', f))
    if (urlsText.value.trim()) {
      const urls = urlsText.value.trim().split('\n').filter(Boolean)
      fd.append('urls', JSON.stringify(urls))
    }
    const res = await api.ingest(projectId, fd)
    job.value = { ...res.data, agents: {} }
    batchStartTime.value = Date.now()
    localStorage.setItem(`traceai_job_${projectId}`, String(res.data.job_id))
    startPolling()
  } finally {
    launching.value = false
  }
}

function startPolling() {
  if (pollTimer) clearInterval(pollTimer)
  pollTimer = setInterval(async () => {
    if (!job.value?.job_id) return
    try {
      const res = await api.getJobStatus(job.value.job_id)
      job.value = res.data
      // Logs réels depuis le backend
      if (res.data.logs && res.data.logs.length) {
        logLines.value = res.data.logs
      }
      if (res.data.status === 'done' || res.data.status === 'error') {
        clearInterval(pollTimer)
        pollTimer = null
        localStorage.removeItem(`traceai_job_${projectId}`)
        await loadWikiAndAlerts()
      }
    } catch (e) { /* ignore */ }
  }, 2000)
}

async function loadWikiAndAlerts() {
  try {
    const [wRes, aRes] = await Promise.all([
      api.getWikiIndex(projectId),
      api.getAlerts(projectId),
    ])
    const pages = await Promise.all(
      wRes.data.filter(p => p.page_type === 'machine').map(p => api.getWikiPage(p.id))
    )
    wikiPages.value = pages.map(r => r.data)
    alertCount.value = aRes.data.length
  } catch (e) { /* ignore */ }
}

async function loadAlerts() {
  try {
    const res = await api.getAlerts(projectId)
    alertCount.value = res.data.length
  } catch (e) { /* ignore */ }
}

onMounted(async () => {
  try {
    const res = await api.getProjects()
    const proj = res.data.find(p => p.id === projectId)
    if (proj) projectName.value = proj.name
    const docRes = await api.getDocuments(projectId)
    docCount.value = docRes.data.length
    await loadWikiAndAlerts()
    machineCount.value = wikiPages.value.filter(p => p.page_type === 'machine').length
  } catch (e) { /* ignore */ }

  // Reprendre un batch en cours si on revient sur la page
  const savedJobId = localStorage.getItem(`traceai_job_${projectId}`)
  if (savedJobId) {
    try {
      const res = await api.getJobStatus(parseInt(savedJobId))
      if (res.data.status === 'running') {
        job.value = res.data
        batchStartTime.value = Date.now()
        startPolling()
      } else if (res.data.status === 'done') {
        job.value = res.data
      } else {
        localStorage.removeItem(`traceai_job_${projectId}`)
      }
    } catch (e) {
      localStorage.removeItem(`traceai_job_${projectId}`)
    }
  }
})

async function cancelBatch() {
  if (!job.value?.job_id) return
  try {
    await api.cancelJob(job.value.job_id)
    if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
    job.value = { ...job.value, status: 'cancelled' }
  } catch (e) { /* ignore */ }
}

onUnmounted(() => { if (pollTimer) clearInterval(pollTimer) })
</script>

<style scoped>
.p2-root { display:flex; flex-direction:column; height:100vh; background:#FAFAF7; color:#0E0E0C; font-family:'Geist',system-ui,sans-serif; }

/* Header */
.p2-header { height:56px; display:flex; align-items:center; gap:20px; padding:0 28px; border-bottom:1px solid #EAE7DD; background:#FAFAF7; flex-shrink:0; }
.p2-wm { display:flex; align-items:center; gap:7px; font-family:'Geist Mono',monospace; font-weight:700; font-size:14px; }
.p2-wm-box { display:inline-flex; align-items:center; justify-content:center; width:18px; height:18px; border-radius:3px; background:#0E0E0C; color:#FAFAF7; font-size:10px; font-weight:800; }
.p2-wm-accent { color:#E89A2D; }
.p2-wm-badge { margin-left:6px; padding:2px 6px; border:1px solid #EAE7DD; border-radius:2px; font-size:9.5px; font-weight:600; letter-spacing:.16em; color:#3D3D38; text-transform:uppercase; }
.p2-sep { width:1px; height:20px; background:#EAE7DD; }
.p2-proj-name { font-size:14px; font-weight:600; }
.p2-proj-sub { font-family:'Geist Mono',monospace; font-size:10px; color:#7C7B73; }
.p2-tabs { display:flex; }
.p2-tab { padding:8px 14px; background:transparent; border:none; border-bottom:2px solid transparent; cursor:pointer; font-family:inherit; font-size:13px; font-weight:550; color:#7C7B73; display:inline-flex; align-items:center; gap:7px; margin-bottom:-1px; }
.p2-tab.active { color:#0E0E0C; border-bottom-color:#0E0E0C; }
.p2-tab-count { padding:1px 5px; background:#fff; border:1px solid #EAE7DD; border-radius:999px; font-family:'Geist Mono',monospace; font-size:10px; color:#7C7B73; }
.p2-live-badge { display:inline-flex; align-items:center; gap:6px; padding:4px 10px; background:#fff; border:1px solid #EAE7DD; border-radius:999px; font-family:'Geist Mono',monospace; font-size:10px; color:#3D3D38; }
.p2-live-dot { width:6px; height:6px; border-radius:50%; background:#E89A2D; animation:tracePulseDot 1.4s ease-in-out infinite; display:inline-block; }

/* Mono utility */
.p2-mono { font-family:'Geist Mono',monospace; }
.p2-ink { color:#0E0E0C; }
.p2-soft { color:#3D3D38; }
.p2-mute { color:#7C7B73; }
.p2-faint { color:#B5B3A8; }
.p2-accent { color:#E89A2D; }

/* Upload */
.p2-upload-wrap { flex:1; padding:32px 48px; overflow:auto; }
.p2-upload-inner { max-width:1100px; margin:0 auto; }
.p2-eyebrow { font-family:'Geist Mono',monospace; font-size:10px; color:#7C7B73; letter-spacing:.18em; text-transform:uppercase; }
.p2-h1 { margin:8px 0 0; font-size:32px; font-weight:600; letter-spacing:-.025em; }
.p2-lead { margin:10px 0 0; font-size:15px; color:#3D3D38; line-height:1.55; max-width:680px; }
.p2-upload-grid { display:grid; grid-template-columns:1.4fr 1fr; gap:22px; margin-top:28px; }
.p2-dropzone { background:#fff; border:2px dashed #EAE7DD; border-radius:4px; padding:36px 28px; display:flex; flex-direction:column; align-items:center; gap:14px; cursor:pointer; transition:border-color .15s; }
.p2-dropzone.dragging { border-color:#E89A2D; background:#FFF8EB; }
.p2-doc-stack { position:relative; width:70px; height:80px; }
.p2-doc-sheet { position:absolute; width:56px; height:70px; border-radius:3px; background:#fff; border:1px solid #EAE7DD; }
.p2-drop-text { text-align:center; }
.p2-drop-text strong { font-size:16px; font-weight:600; display:block; }
.p2-drop-sub { font-family:'Geist Mono',monospace; font-size:11px; color:#7C7B73; margin-top:6px; display:block; }
.p2-btn-outline { padding:8px 14px; background:transparent; color:#0E0E0C; border:1px solid #EAE7DD; border-radius:3px; cursor:pointer; font-family:inherit; font-size:12.5px; font-weight:550; }
.p2-url-panel { background:#fff; border:1px solid #EAE7DD; border-radius:4px; padding:22px; display:flex; flex-direction:column; gap:10px; }
.p2-url-title { font-size:14px; font-weight:600; }
.p2-url-hint { font-family:'Geist Mono',monospace; font-size:11px; color:#3D3D38; }
.p2-url-input { width:100%; padding:10px 12px; box-sizing:border-box; background:#FAFAF7; border:1px solid #EAE7DD; border-radius:3px; font-family:'Geist Mono',monospace; font-size:11.5px; color:#0E0E0C; outline:none; resize:vertical; line-height:1.6; }
.p2-btn-primary { padding:9px 14px; background:#0E0E0C; color:#FAFAF7; border:none; border-radius:3px; cursor:pointer; font-family:inherit; font-size:13px; font-weight:600; }
.p2-filelist-wrap { margin-top:26px; }
.p2-filelist-header { display:flex; align-items:center; gap:10px; margin-bottom:12px; }
.p2-rule { flex:1; height:1px; background:#F2EFE6; }
.p2-filelist { background:#fff; border:1px solid #EAE7DD; border-radius:4px; overflow:hidden; }
.p2-filerow { display:flex; align-items:center; gap:14px; padding:11px 16px; border-bottom:1px solid #F2EFE6; }
.p2-filerow:last-child { border-bottom:none; }
.p2-file-icon { font-family:'Geist Mono',monospace; font-size:8px; font-weight:700; width:28px; height:36px; border:1px solid #EAE7DD; border-radius:2px; background:#FAFAF7; display:flex; align-items:flex-end; padding:0 4px 4px; flex-shrink:0; }
.p2-file-info { flex:1; min-width:0; }
.p2-file-name { font-size:13px; font-weight:550; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.p2-file-meta { font-family:'Geist Mono',monospace; font-size:10px; color:#7C7B73; }
.p2-file-status { font-family:'Geist Mono',monospace; font-size:10px; color:#3D3D38; letter-spacing:.12em; text-transform:uppercase; }
.p2-remove { width:26px; height:26px; border:none; background:transparent; cursor:pointer; color:#7C7B73; border-radius:3px; display:inline-flex; align-items:center; justify-content:center; }
.p2-btn-launch { padding:11px 18px; background:#0E0E0C; color:#FAFAF7; border:none; border-radius:3px; cursor:pointer; font-family:inherit; font-size:14px; font-weight:600; display:inline-flex; align-items:center; gap:7px; }
.p2-btn-launch:disabled { opacity:.5; cursor:not-allowed; }
.p2-eta { font-family:'Geist Mono',monospace; font-size:11px; color:#7C7B73; }
.p2-btn-cancel { padding:8px 14px; background:transparent; color:#C8482D; border:1px solid #C8482D55; border-radius:3px; cursor:pointer; font-family:inherit; font-size:12.5px; font-weight:550; }

/* Batch running */
.p2-batch-wrap { flex:1; display:flex; flex-direction:column; overflow:hidden; }
.p2-stats-bar { padding:20px 32px; display:grid; grid-template-columns:1.5fr 1fr 1fr 1fr; gap:28px; border-bottom:1px solid #EAE7DD; flex-shrink:0; }
.p2-stat-main { }
.p2-stat-title { display:flex; align-items:center; gap:8px; margin-bottom:6px; }
.p2-stat-name { font-size:19px; font-weight:600; letter-spacing:-.015em; }
.p2-stat-box { border-left:1px solid #EAE7DD; padding-left:18px; }
.p2-pipeline-wrap { padding:24px 32px 16px; flex-shrink:0; }
.p2-pipeline-label { font-family:'Geist Mono',monospace; font-size:10px; color:#7C7B73; letter-spacing:.18em; text-transform:uppercase; margin-bottom:14px; }
.p2-pipeline { position:relative; display:grid; grid-template-columns:repeat(10,1fr); gap:0; }
.p2-pipeline-line { position:absolute; top:18px; left:18px; right:18px; height:2px; background:#F2EFE6; z-index:0; }
.p2-pipeline-progress { position:absolute; top:18px; left:18px; height:2px; background:#1F6B5E; z-index:1; transition:width 600ms; }
.p2-node { display:flex; flex-direction:column; align-items:center; gap:4px; padding:0 4px; position:relative; z-index:2; }
.p2-node-dot { width:36px; height:36px; border-radius:50%; background:#fff; border:2px solid #B5B3A8; display:inline-flex; align-items:center; justify-content:center; font-size:14px; position:relative; }
.p2-node-dot.done { background:#1F6B5E; border-color:#1F6B5E; }
.p2-node-dot.running { background:#E89A2D; border-color:#E89A2D; box-shadow:0 0 0 5px #E89A2D22; }
.p2-node-dot.error { border-color:#C8482D; }
.p2-check { color:#fff; font-size:14px; font-weight:700; }
.p2-spin-ring { position:absolute; inset:-8px; border-radius:50%; border:1.5px dashed #E89A2D; animation:traceSpin 6s linear infinite; }
.p2-hero-badge { position:absolute; top:-12px; left:50%; transform:translateX(-50%); padding:1px 5px; background:#0E0E0C; color:#FAFAF7; font-family:'Geist Mono',monospace; font-size:8px; font-weight:700; letter-spacing:.12em; border-radius:2px; white-space:nowrap; }
.p2-node-n { font-family:'Geist Mono',monospace; font-size:9px; color:#7C7B73; font-weight:600; }
.p2-node-name { font-size:11.5px; font-weight:600; text-align:center; line-height:1.2; color:#7C7B73; }
.p2-node-name.done { color:#3D3D38; }
.p2-node-name.running { color:#0E0E0C; }
.p2-node-counter { text-align:center; min-height:32px; }
.p2-node-bar { width:70%; height:2px; background:#F2EFE6; border-radius:1px; overflow:hidden; }
.p2-node-bar-fill { height:100%; background:#E89A2D; transition:width 400ms; }

/* Log */
.p2-log-wrap { flex:1; padding:20px 32px; display:flex; flex-direction:column; gap:10px; min-height:0; }
.p2-log-header { display:flex; align-items:center; gap:10px; }
.p2-rec-badge { display:inline-flex; align-items:center; gap:5px; padding:2px 9px; background:#fff; border:1px solid #EAE7DD; border-radius:999px; }
.p2-console { flex:1; background:#0E0E0C; border-radius:4px; padding:16px 18px; overflow:auto; font-family:'Geist Mono',monospace; font-size:11.5px; line-height:1.7; }
.p2-log-line { display:flex; gap:10px; }
.p2-log-time { color:#615E55; flex-shrink:0; }
.p2-log-lvl { flex-shrink:0; font-weight:700; width:36px; text-transform:uppercase; letter-spacing:.06em; font-size:10px; }
.p2-log-agent { color:#7C7B73; flex-shrink:0; width:56px; }
.p2-log-msg { flex:1; color:#C5C1B6; }
.p2-cursor { color:#E89A2D; animation:traceCursor 1s steps(2) infinite; }

/* Done */
.p2-done-wrap { flex:1; display:flex; flex-direction:column; overflow:auto; }
.p2-results-grid { flex:1; padding:20px 32px 28px; display:grid; grid-template-columns:1fr 1fr 1fr; gap:22px; }
.p2-card { background:#fff; border:1px solid #EAE7DD; border-radius:4px; padding:16px 18px; display:flex; flex-direction:column; overflow:hidden; }
.p2-card-head { display:flex; align-items:baseline; gap:8px; margin-bottom:12px; }
.p2-card-head > span:first-child { font-size:14px; font-weight:600; }
.p2-card-head > span:last-child { margin-left:auto; }
.p2-wiki-row { display:flex; align-items:center; gap:10px; padding:7px 0; border-bottom:1px dashed #F2EFE6; cursor:pointer; }
.p2-wiki-row:hover { background:#F2EFE6; border-radius:3px; }
.p2-wiki-icon { font-size:14px; }
.p2-wiki-name { flex:1; font-size:12.5px; }
.p2-contradiction { padding:10px 12px; background:#FFF8EB; border:1px solid #E89A2D55; border-left:2px solid #E89A2D; border-radius:3px; margin-bottom:8px; }
.p2-contradiction-topic { font-family:'Geist Mono',monospace; font-size:9px; color:#E89A2D; font-weight:700; letter-spacing:.16em; text-transform:uppercase; }
.p2-contradiction-detail { font-size:12.5px; color:#0E0E0C; margin-top:5px; line-height:1.5; }
.p2-gap { padding:10px 12px; background:#fff; border:1px solid #EAE7DD; border-left:2px solid #C8482D; border-radius:3px; margin-bottom:8px; font-size:12.5px; }

/* Tab content */
.p2-tab-content { flex:1; overflow:auto; }

@keyframes tracePulseDot { 0%,100% { transform:scale(1); opacity:1; } 50% { transform:scale(1.6); opacity:.4; } }
@keyframes traceSpin { 0% { transform:rotate(0); } 100% { transform:rotate(360deg); } }
@keyframes traceCursor { 0%,100% { opacity:1; } 50% { opacity:0; } }
</style>
