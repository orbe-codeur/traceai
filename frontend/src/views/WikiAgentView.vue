<template>
  <div class="wa-root">

    <!-- ═══════════════════ HEADER ═══════════════════ -->
    <header class="wa-header">
      <button class="wa-wm" @click="$router.push('/')">
        <span class="wa-wm-t">T</span>
        Trace<span class="wa-amber">AI</span>
        <span class="wa-badge">wiki · agent</span>
      </button>
      <span class="wa-vsep" />
      <div>
        <div class="wa-proj-name">{{ projectName }}</div>
        <div class="wa-proj-sub" v-if="wizardStep === null">
          {{ machineCount }} machine{{ machineCount !== 1 ? 's' : '' }} ·
          {{ docCount }} doc{{ docCount !== 1 ? 's' : '' }}
          <span v-if="alertCount > 0" class="wa-sub-alert">
            · {{ alertCount }} alerte{{ alertCount !== 1 ? 's' : '' }}
          </span>
        </div>
        <div class="wa-proj-sub" v-else>ingestion de documents</div>
      </div>

      <span style="flex:1" />

      <!-- Health pill -->
      <div v-if="wizardStep === null" class="wa-health-pill">
        <span class="wa-health-dot" :class="alertCount > 0 ? 'warn' : 'ok'" />
        {{ machineCount }} machines · {{ docCount }} docs
        <span v-if="alertCount > 0"> · {{ alertCount }} alertes</span>
      </div>

      <!-- Ajouter docs -->
      <button v-if="wizardStep === null" class="wa-btn-add" @click="startAddDocs">
        + Ajouter des documents
      </button>

      <!-- Tabs (état B) -->
      <nav v-if="wizardStep === null" class="wa-tabs">
        <button v-for="t in TABS" :key="t.id"
          :class="['wa-tab', { active: activeTab === t.id }]"
          @click="activeTab = t.id">
          {{ t.label }}
          <span v-if="t.badge" class="wa-tab-badge">{{ t.badge }}</span>
        </button>
      </nav>

      <!-- Retour onglets pendant ingestion -->
      <button v-if="wizardStep === 'A5'" class="wa-btn-outline-sm" @click="wizardStep = null">
        Voir les onglets
      </button>
    </header>

    <!-- ═══════════════════ WIZARD A1 — Drop zone ═══════════════════ -->
    <div v-if="wizardStep === 'A1'" class="wa-main wa-center">
      <div class="wa-wizard-inner">
        <div class="wa-eyebrow">Phase 2 · Machine Wiki Agentique</div>
        <h1 class="wa-h1">Alimenter la base de connaissances</h1>
        <p class="wa-lead">Déposez vos documents techniques. L'agent construit automatiquement un wiki interrogeable avec citations.</p>

        <div class="wa-dropzone" :class="{ dragging: isDragging }"
          @dragover.prevent="isDragging = true"
          @dragleave="isDragging = false"
          @drop.prevent="onDrop">
          <div class="wa-drop-stack">
            <div v-for="i in 3" :key="i" class="wa-doc-sheet" :style="{ left:(i-1)*6+'px', top:(i-1)*4+'px' }" />
          </div>
          <div class="wa-drop-text">
            <strong>Déposez vos documents techniques</strong>
            <span class="wa-drop-sub">PDF · Word · Excel — manuels, rapports, fiches techniques</span>
          </div>
          <label class="wa-btn-outline">
            Parcourir les fichiers
            <input type="file" multiple style="display:none" @change="onFileChange" />
          </label>
        </div>

        <div v-if="existingDocCount > 0" class="wa-existing-info">
          <span class="wa-mono wa-mute">{{ existingDocCount }} document{{ existingDocCount !== 1 ? 's' : '' }} déjà ingéré{{ existingDocCount !== 1 ? 's' : '' }}</span>
        </div>
      </div>
    </div>

    <!-- ═══════════════════ WIZARD A2 — Fichiers ═══════════════════ -->
    <div v-else-if="wizardStep === 'A2'" class="wa-main">
      <div class="wa-wizard-inner wa-wizard-inner--wide">
        <div class="wa-wizard-back-row">
          <button class="wa-btn-ghost" @click="wizardStep = 'A1'">← Retour</button>
          <span class="wa-eyebrow">{{ droppedFiles.length }} fichier{{ droppedFiles.length !== 1 ? 's' : '' }} sélectionné{{ droppedFiles.length !== 1 ? 's' : '' }}</span>
        </div>

        <div class="wa-filelist">
          <div v-for="(f, i) in droppedFiles" :key="i" class="wa-filerow">
            <div class="wa-file-icon" :style="{ color: fileColor(f) }">{{ fileExt(f) }}</div>
            <div class="wa-file-info">
              <div class="wa-file-name">{{ f.name }}</div>
              <div class="wa-file-meta">{{ formatSize(f.size) }}</div>
            </div>
            <span class="wa-file-type-badge">{{ classifyFile(f.name) }}</span>
            <button class="wa-file-remove" @click="droppedFiles.splice(i, 1)" title="Supprimer">✕</button>
          </div>
        </div>

        <div class="wa-add-more-row">
          <label class="wa-btn-ghost">
            + Ajouter des fichiers
            <input type="file" multiple style="display:none" @change="onFileChange" />
          </label>
        </div>

        <div class="wa-wizard-actions">
          <button class="wa-btn-primary wa-btn-lg" @click="wizardStep = 'A3'" :disabled="!droppedFiles.length">
            Analyser les documents →
          </button>
          <span class="wa-mono wa-mute" style="font-size:11px">Scan rapide · zéro LLM · &lt; 5 sec</span>
        </div>
      </div>
    </div>

    <!-- ═══════════════════ WIZARD A3 — Contexte ═══════════════════ -->
    <div v-else-if="wizardStep === 'A3'" class="wa-main wa-center">
      <div class="wa-wizard-inner">
        <div class="wa-a3-header">
          <div class="wa-a3-icon">🤖</div>
          <h2 class="wa-a3-title">Quelques informations avant de commencer</h2>
          <p class="wa-a3-sub">
            J'ai analysé <strong>{{ droppedFiles.length }} document{{ droppedFiles.length !== 1 ? 's' : '' }}</strong>.
            Ces informations aideront l'agent à mieux contextualiser le wiki.
          </p>
        </div>

        <!-- Résumé classification -->
        <div class="wa-classification-grid">
          <div v-for="(count, type) in classificationSummary" :key="type" class="wa-classif-item">
            <span class="wa-classif-icon">{{ classifIcon(type) }}</span>
            <span class="wa-classif-count wa-mono">{{ count }}</span>
            <span class="wa-classif-label">{{ type }}</span>
          </div>
        </div>

        <!-- Questions contexte -->
        <div class="wa-context-form">
          <div class="wa-field">
            <label class="wa-label">Site ou client (optionnel)</label>
            <input v-model="contextSite" class="wa-input" placeholder="ex: Metz B2, Client ABC…" />
          </div>
          <div class="wa-field">
            <label class="wa-label">Notes contextuelles (optionnel)</label>
            <textarea v-model="contextNotes" class="wa-textarea" rows="3"
              placeholder="Machine principale, période concernée, priorités…" />
          </div>
        </div>

        <div class="wa-wizard-actions">
          <button class="wa-btn-ghost" @click="wizardStep = 'A2'">← Retour</button>
          <button class="wa-btn-primary wa-btn-lg" @click="wizardStep = 'A4'">
            Voir le plan →
          </button>
        </div>
      </div>
    </div>

    <!-- ═══════════════════ WIZARD A4 — Plan ═══════════════════ -->
    <div v-else-if="wizardStep === 'A4'" class="wa-main">
      <div class="wa-wizard-inner wa-wizard-inner--wide">
        <div class="wa-a4-header">
          <h2 class="wa-a4-title">Voici comment je vais traiter vos documents</h2>
          <p class="wa-a4-sub">Vérifiez le plan avant de lancer l'ingestion.</p>
        </div>

        <div class="wa-plan-table-wrap">
          <table class="wa-plan-table">
            <thead>
              <tr>
                <th>Document</th>
                <th>Type détecté</th>
                <th>Stratégie</th>
                <th>Priorité</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(f, i) in droppedFiles" :key="i">
                <td class="wa-plan-name">{{ f.name }}</td>
                <td><span class="wa-plan-type">{{ classifyFile(f.name) }}</span></td>
                <td class="wa-plan-strategy">{{ strategyFor(f.name) }}</td>
                <td><span class="wa-plan-prio" :class="prioClass(f.name)">{{ prioLabel(f.name) }}</span></td>
              </tr>
            </tbody>
          </table>
        </div>

        <div v-if="contextSite" class="wa-plan-context">
          <span class="wa-mono wa-mute" style="font-size:11px">Contexte : {{ contextSite }}<span v-if="contextNotes"> — {{ contextNotes }}</span></span>
        </div>

        <div class="wa-plan-eta">
          <span class="wa-mono" style="font-size:12px; color: var(--inkSoft)">
            Durée estimée : ~{{ Math.max(2, Math.ceil(droppedFiles.length * 1.2)) }} minutes
          </span>
        </div>

        <div class="wa-wizard-actions">
          <button class="wa-btn-ghost" @click="wizardStep = 'A3'">← Modifier</button>
          <button class="wa-btn-primary wa-btn-lg wa-btn-launch" :disabled="launching" @click="launchIngestion">
            {{ launching ? 'Lancement…' : '⚡ Lancer l\'ingestion' }}
          </button>
        </div>
      </div>
    </div>

    <!-- ═══════════════════ WIZARD A5 — Progression ═══════════════════ -->
    <div v-else-if="wizardStep === 'A5'" class="wa-main wa-a5-wrap">
      <!-- Stats bar -->
      <div class="wa-stats-bar">
        <div class="wa-stat-main">
          <div class="wa-stat-title">
            <span class="wa-live-dot"
              :class="{ 'animate-trace-dot': !batchDone }"
              :style="{ background: batchDone ? 'var(--teal)' : 'var(--amber)' }" />
            <span class="wa-mono" style="font-size:10px;letter-spacing:.18em;text-transform:uppercase"
              :style="{ color: batchDone ? 'var(--teal)' : 'var(--amber)' }">
              {{ batchDone ? 'Ingestion terminée' : 'Ingestion en cours' }}
            </span>
          </div>
          <div class="wa-stat-name">{{ projectName }}</div>
          <div class="wa-mono wa-mute" style="font-size:11px;margin-top:4px">
            {{ batchDone ? `${docCount} documents ingérés` : `Agent actif : ${activeAgentName}` }}
          </div>
        </div>
        <div class="wa-stat-box">
          <div class="wa-mono wa-mute" style="font-size:9px;letter-spacing:.18em;text-transform:uppercase">Progression</div>
          <div class="wa-mono" style="font-size:28px;font-weight:600;margin-top:6px" :style="{ color: batchDone ? 'var(--teal)' : 'var(--ink)' }">{{ overallPct }}%</div>
          <div class="wa-mono wa-mute" style="font-size:10px">{{ doneAgents }}/{{ AGENTS.length }} agents</div>
        </div>
        <div class="wa-stat-box">
          <div class="wa-mono wa-mute" style="font-size:9px;letter-spacing:.18em;text-transform:uppercase">Fichiers</div>
          <div class="wa-mono" style="font-size:28px;font-weight:600;margin-top:6px">{{ batch.processedFiles }}/{{ batch.totalFiles || droppedFiles.length }}</div>
          <div class="wa-mono wa-mute" style="font-size:10px">traités</div>
        </div>
        <div class="wa-stat-box">
          <div class="wa-mono wa-mute" style="font-size:9px;letter-spacing:.18em;text-transform:uppercase">Erreurs</div>
          <div class="wa-mono" style="font-size:28px;font-weight:600;margin-top:6px"
            :style="{ color: batch.errorFiles > 0 ? 'var(--red)' : 'var(--inkMute)' }">
            {{ batch.errorFiles }}
          </div>
          <div class="wa-mono wa-mute" style="font-size:10px">à inspecter</div>
        </div>
      </div>

      <!-- Pipeline — itère sur pipelineNodes (computed réactif) -->
      <div class="wa-pipeline-wrap">
        <div class="wa-pipeline-label wa-mono wa-mute">
          Pipeline · {{ doneAgents }}/{{ AGENTS.length }} agents terminés
        </div>
        <div class="wa-pipeline">
          <div class="wa-pipeline-line" />
          <div class="wa-pipeline-fill" :style="{ width: pipelineWidth }" />
          <div v-for="node in pipelineNodes" :key="node.key" class="wa-node">
            <div class="wa-node-dot" :class="node.status">
              <span v-if="node.status === 'running'" class="wa-spin-ring animate-trace-spin" />
              <span v-else-if="node.status === 'done'" class="wa-check">✓</span>
              <span v-else-if="node.status === 'error'" style="color:var(--red);font-size:11px">✗</span>
              <span v-else>{{ node.icon }}</span>
            </div>
            <div class="wa-mono" style="font-size:9px;color:var(--inkMute)">{{ String(node.n).padStart(2,'0') }}</div>
            <div class="wa-node-name" :class="node.status">{{ node.name }}</div>
            <div v-if="node.counter" class="wa-node-counter wa-mono">{{ node.counter }}</div>
          </div>
        </div>
      </div>

      <!-- Log -->
      <div class="wa-log-wrap">
        <div class="wa-log-header">
          <span class="wa-mono wa-mute" style="font-size:10px;letter-spacing:.18em;text-transform:uppercase">Console · logs en direct</span>
          <div style="flex:1;height:1px;background:var(--ruleSoft);margin:0 12px" />
          <span class="wa-rec-badge wa-mono" style="font-size:9px">● REC</span>
        </div>
        <div class="wa-console" ref="consoleEl">
          <div v-if="!logLines.length" class="wa-log-line">
            <span class="wa-mono" style="color:var(--inkMute)">En attente des premiers logs…</span>
          </div>
          <div v-for="(line, i) in logLines" :key="i" class="wa-log-line">
            <span class="wa-log-time wa-mono">{{ line.t }}</span>
            <span class="wa-log-lvl wa-mono" :style="{ color: lvlColor(line.lvl) }">{{ line.lvl }}</span>
            <span class="wa-log-agent wa-mono">{{ line.agent ? '['+line.agent+']' : '' }}</span>
            <span class="wa-log-msg wa-mono" :style="{ color: line.lvl==='cur' ? '#F1ECE0' : '#C5C1B6' }">
              {{ line.msg }}<span v-if="line.lvl==='cur'" class="animate-trace-cursor" style="color:var(--amber)">_</span>
            </span>
          </div>
        </div>
        <div style="display:flex;gap:8px;margin-top:10px">
          <button v-if="!batchDone" class="wa-btn-cancel" @click="cancelIngestion">Annuler</button>
          <button v-if="batchDone" class="wa-btn-primary" @click="enterTabs">Voir la base de connaissances →</button>
        </div>
      </div>
    </div>

    <!-- ═══════════════════ ÉTAT B — 4 ONGLETS ═══════════════════ -->
    <template v-else-if="wizardStep === null">
      <WAChatTab
        v-if="activeTab === 'chat'"
        :project-id="projectId"
        @wikilink="openWikiPage"
      />
      <WAWikiTab
        v-else-if="activeTab === 'wiki'"
        :project-id="projectId"
        :initial-page="wikiJumpPage"
        @go-graph="activeTab = 'graph'"
      />
      <WAGraphTab
        v-else-if="activeTab === 'graph'"
        :project-id="projectId"
      />
      <WAAlertsTab
        v-else-if="activeTab === 'alerts'"
        :project-id="projectId"
        @update-count="alertCount = $event"
      />
    </template>

  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import api from '../services/api.js'
import { useToast } from '../composables/useToast.js'
import WAChatTab from '../components/WAChatTab.vue'
import WAWikiTab from '../components/WAWikiTab.vue'
import WAGraphTab from '../components/WAGraphTab.vue'
import WAAlertsTab from '../components/WAAlertsTab.vue'

const route = useRoute()
const projectId = parseInt(route.params.id)
const { success, error: toastError } = useToast()

// ── État général ──────────────────────────────────────────────────────────────
const projectName = ref('Chargement…')
const docCount = ref(0)
const machineCount = ref(0)
const alertCount = ref(0)
const existingDocCount = ref(0)
const wizardStep = ref(null) // null | 'A1' | 'A2' | 'A3' | 'A4' | 'A5'
const activeTab = ref('chat')
const wikiJumpPage = ref(null)

// ── Wizard files ──────────────────────────────────────────────────────────────
const isDragging = ref(false)
const droppedFiles = ref([])
const contextSite = ref('')
const contextNotes = ref('')
const launching = ref(false)

// ── Batch / A5 ─────────────────────────────────────────────────────────────────
// reactive() : Vue tracke chaque propriété individuellement → mise à jour
// garantie même si on mute en place (sans remplacer l'objet entier)
const batch = reactive({
  status:         'idle',   // 'idle'|'running'|'done'|'error'
  jobId:          null,
  processedFiles: 0,
  totalFiles:     0,
  errorFiles:     0,
  agents:         {},       // { arbo:{status,counter,progress}, tri:{...}, ... }
})
const logLines = ref([])
const consoleEl = ref(null)
let pollTimer = null

const TABS = computed(() => [
  { id: 'chat',   label: 'Chat',    badge: null },
  { id: 'wiki',   label: 'Wiki',    badge: null },
  { id: 'graph',  label: 'Graph',   badge: null },
  { id: 'alerts', label: 'Alertes', badge: alertCount.value > 0 ? alertCount.value : null },
])

const AGENTS = [
  { n:1,  key:'arbo',  name:'Arborescence', icon:'🌲' },
  { n:2,  key:'tri',   name:'Tri',          icon:'⚖️' },
  { n:3,  key:'parse', name:'Parser',       icon:'📄' },
  { n:4,  key:'chunk', name:'Chunker',      icon:'✂️' },
  { n:5,  key:'enrch', name:'Enrichisseur', icon:'✨' },
  { n:6,  key:'index', name:'Indexeur',     icon:'🗄️' },
  { n:7,  key:'compl', name:'Compilateur',  icon:'📚' },
  { n:8,  key:'qual',  name:'Qualité',      icon:'✅' },
  { n:9,  key:'rep',   name:'Répondeur',    icon:'💬' },
  { n:10, key:'alert', name:'Alertes',      icon:'🔔' },
]

// pipelineNodes : computed qui combine AGENTS (statique) + batch.agents (réactif)
// → Vue tracke batch.agents[key] directement dans la computed, pas via une fonction
const pipelineNodes = computed(() =>
  AGENTS.map(ag => ({
    ...ag,
    status:   batch.agents[ag.key]?.status   || 'pending',
    counter:  batch.agents[ag.key]?.counter  || '',
    progress: batch.agents[ag.key]?.progress ?? null,
  }))
)

const batchDone      = computed(() => batch.status === 'done')
const doneAgents     = computed(() => pipelineNodes.value.filter(n => n.status === 'done').length)
const activeAgentIdx = computed(() => {
  const i = pipelineNodes.value.findIndex(n => n.status === 'running')
  return i >= 0 ? i : doneAgents.value
})
const activeAgentName = computed(() => pipelineNodes.value[activeAgentIdx.value]?.name || '')
const overallPct = computed(() => {
  const done = doneAgents.value
  const prog = pipelineNodes.value[activeAgentIdx.value]?.progress || 0
  return Math.round(((done + prog) / AGENTS.length) * 100)
})
const pipelineWidth = computed(() => {
  const prog = pipelineNodes.value[activeAgentIdx.value]?.progress || 0
  const frac = (doneAgents.value + prog) / (AGENTS.length - 1)
  return `calc((100% - 36px) * ${Math.min(frac, 1)})`
})

// ── Classification fichiers ───────────────────────────────────────────────────
function classifyFile(name) {
  const n = name.toLowerCase()
  if (/manuel|manual|notice|guide|instruction/i.test(n)) return 'Manuel constructeur'
  if (/rapport|report|intervention|compte.rendu|cr[_-]/i.test(n)) return 'Rapport d\'intervention'
  if (/inventaire|inventory|stock|pieces|parts|spare/i.test(n)) return 'Inventaire pièces'
  if (/schema|plan|drawing|dwg|dxf|blueprint/i.test(n)) return 'Plan technique'
  return 'Document non identifié'
}

const classificationSummary = computed(() => {
  const counts = {}
  droppedFiles.value.forEach(f => {
    const t = classifyFile(f.name)
    counts[t] = (counts[t] || 0) + 1
  })
  return counts
})

function classifIcon(type) {
  const m = { 'Manuel constructeur':'📁', 'Rapport d\'intervention':'📋', 'Inventaire pièces':'📊', 'Plan technique':'📐', 'Document non identifié':'❓' }
  return m[type] || '📄'
}

function strategyFor(name) {
  const t = classifyFile(name)
  const m = {
    'Manuel constructeur': 'Source principale',
    'Rapport d\'intervention': 'Extraction date + technicien',
    'Inventaire pièces': 'Extraction références',
    'Plan technique': 'Indexation visuelle',
    'Document non identifié': 'Analyse automatique',
  }
  return m[t] || 'Analyse automatique'
}

function prioLabel(name) {
  const t = classifyFile(name)
  return t === 'Manuel constructeur' ? '🔴 Élevée' : t === 'Document non identifié' ? '🟢 Basse' : '🟡 Moyenne'
}

function prioClass(name) {
  const t = classifyFile(name)
  return t === 'Manuel constructeur' ? 'prio-high' : t === 'Document non identifié' ? 'prio-low' : 'prio-mid'
}

// ── Drag & drop ───────────────────────────────────────────────────────────────
function onDrop(e) {
  isDragging.value = false
  const files = Array.from(e.dataTransfer.files)
  droppedFiles.value = [...droppedFiles.value, ...files]
  if (droppedFiles.value.length) wizardStep.value = 'A2'
}

function onFileChange(e) {
  droppedFiles.value = [...droppedFiles.value, ...Array.from(e.target.files)]
  if (droppedFiles.value.length) wizardStep.value = 'A2'
}

// ── Helpers fichier ───────────────────────────────────────────────────────────
function fileExt(f) { return f.name.split('.').pop()?.toUpperCase()?.slice(0,4) || 'FILE' }
function fileColor(f) {
  const ext = f.name.split('.').pop()?.toLowerCase()
  const m = { pdf:'#C8312D', docx:'#2A5DB0', doc:'#2A5DB0', xlsx:'#1F6B5E', xls:'#1F6B5E', zip:'#7C3F92', dwg:'#7C5A1B', dxf:'#7C5A1B' }
  return m[ext] || 'var(--inkMute)'
}
function formatSize(bytes) {
  if (bytes > 1024*1024) return (bytes/1024/1024).toFixed(1)+' Mo'
  return (bytes/1024).toFixed(0)+' ko'
}

// ── Lancement ingestion ───────────────────────────────────────────────────────
async function launchIngestion() {
  if (!droppedFiles.value.length || launching.value) return
  launching.value = true
  try {
    const fd = new FormData()
    droppedFiles.value.forEach(f => fd.append('files', f))
    if (contextSite.value || contextNotes.value) {
      const notes = [contextSite.value, contextNotes.value].filter(Boolean).join(' — ')
      fd.append('context', notes)
    }
    const res = await api.ingest(projectId, fd)
    const jId = res.data.job_id
    applyJobData({ ...res.data, agents: {}, logs: [] }, jId)
    localStorage.setItem(`traceai_job_${projectId}`, String(jId))
    wizardStep.value = 'A5'
    startPolling()
  } catch (e) {
    toastError('Erreur lors du lancement de l\'ingestion.')
  } finally {
    launching.value = false
  }
}

// ── applyJobData — met à jour batch en mutant les propriétés (reactive) ──────
function applyJobData(data, jId) {
  batch.jobId          = jId ?? data.id ?? batch.jobId
  batch.status         = data.status || 'running'
  batch.processedFiles = data.processed_files || 0
  batch.totalFiles     = data.total_files     || 0
  batch.errorFiles     = data.error_files     || 0

  // Muter batch.agents en place : Vue tracke chaque clé individuellement
  const agts = data.agents || parseJson(data.agents_json) || {}
  // Supprimer les clés disparues
  Object.keys(batch.agents).forEach(k => { if (!(k in agts)) delete batch.agents[k] })
  // Ajouter / mettre à jour
  Object.entries(agts).forEach(([k, v]) => {
    if (!batch.agents[k]) {
      batch.agents[k] = v                          // nouvelle clé → Vue détecte l'ajout
    } else {
      batch.agents[k].status   = v.status          // mutation → re-render immédiat
      batch.agents[k].counter  = v.counter  ?? ''
      batch.agents[k].progress = v.progress ?? null
    }
  })

  // Logs
  const logs = data.logs || parseJson(data.logs_json) || []
  if (logs.length) logLines.value = logs
}

function parseJson(str) {
  try { return typeof str === 'string' ? JSON.parse(str) : str } catch { return null }
}

function startPolling() {
  if (pollTimer) clearInterval(pollTimer)
  pollTimer = setInterval(async () => {
    if (!batch.jobId) return
    try {
      const res = await api.getJobStatus(batch.jobId)
      applyJobData(res.data)

      nextTick(() => {
        if (consoleEl.value) consoleEl.value.scrollTop = consoleEl.value.scrollHeight
      })

      if (res.data.status === 'done' || res.data.status === 'error') {
        clearInterval(pollTimer)
        pollTimer = null
        localStorage.removeItem(`traceai_job_${projectId}`)
        await loadStats()
        if (res.data.status === 'done') {
          success('Ingestion terminée ! La base de connaissances est prête.')
        } else {
          toastError('Ingestion terminée avec des erreurs.')
        }
      }
    } catch (e) {
      console.warn('[polling]', e)
    }
  }, 2000)
}

async function cancelIngestion() {
  if (!batch.jobId) return
  try {
    await api.cancelJob(batch.jobId)
    if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
    batch.status = 'cancelled'
  } catch { /* ignore */ }
}

function enterTabs() {
  wizardStep.value = null
  activeTab.value = 'chat'
  droppedFiles.value = []
}


function lvlColor(lvl) {
  const m = { ok:'var(--teal)', warn:'var(--amber)', err:'var(--red)', cur:'var(--amber)' }
  return m[lvl] || 'var(--inkMute)'
}

// ── Chargement stats ──────────────────────────────────────────────────────────
async function loadStats() {
  try {
    const [projRes, docRes, alertRes, wikiRes] = await Promise.allSettled([
      api.getProjects(),
      api.getDocuments(projectId),
      api.getAlerts(projectId),
      api.getWikiIndex(projectId),
    ])
    if (projRes.status === 'fulfilled') {
      const p = projRes.value.data.find(p => p.id === projectId)
      if (p) projectName.value = p.name
    }
    if (docRes.status === 'fulfilled') {
      docCount.value = docRes.value.data.length
      existingDocCount.value = docRes.value.data.length
    }
    if (alertRes.status === 'fulfilled') alertCount.value = alertRes.value.data.length
    if (wikiRes.status === 'fulfilled') {
      machineCount.value = wikiRes.value.data.filter(p => p.page_type === 'machine').length
    }
  } catch { /* ignore */ }
}

// ── Navigation helpers ────────────────────────────────────────────────────────
function startAddDocs() {
  droppedFiles.value = []
  wizardStep.value = 'A1'
}

function openWikiPage(pageName) {
  wikiJumpPage.value = pageName
  activeTab.value = 'wiki'
}

// ── Mount ─────────────────────────────────────────────────────────────────────
onMounted(async () => {
  await loadStats()

  // Si docs existants → onglets B directement
  if (docCount.value > 0 || machineCount.value > 0) {
    wizardStep.value = null
  } else {
    wizardStep.value = 'A1'
  }

  // Reprendre un batch en cours
  const savedJobId = localStorage.getItem(`traceai_job_${projectId}`)
  if (savedJobId) {
    try {
      const id = parseInt(savedJobId)
      const res = await api.getJobStatus(id)
      applyJobData(res.data, id)
      if (res.data.status === 'running') {
        wizardStep.value = 'A5'
        startPolling()
      } else if (res.data.status === 'done') {
        wizardStep.value = 'A5'   // montrer l'écran terminé avant redirection manuelle
        localStorage.removeItem(`traceai_job_${projectId}`)
      } else {
        localStorage.removeItem(`traceai_job_${projectId}`)
      }
    } catch {
      localStorage.removeItem(`traceai_job_${projectId}`)
    }
  }
})

onUnmounted(() => { if (pollTimer) clearInterval(pollTimer) })
</script>

<style scoped>
/* ─── Root ─────────────────────────────────────────────────────────────────── */
.wa-root {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--paper);
  color: var(--ink);
  font-family: var(--font-sans);
}

/* ─── Header ───────────────────────────────────────────────────────────────── */
.wa-header {
  height: 56px;
  display: flex;
  align-items: center;
  gap: 18px;
  padding: 0 24px;
  border-bottom: 1px solid var(--rule);
  background: var(--paper);
  flex-shrink: 0;
}
.wa-wm {
  display: flex;
  align-items: center;
  gap: 6px;
  font-family: var(--font-mono);
  font-weight: 700;
  font-size: 14px;
  background: none;
  border: none;
  cursor: pointer;
  color: var(--ink);
  padding: 0;
  flex-shrink: 0;
}
.wa-wm-t {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  border-radius: 3px;
  background: var(--ink);
  color: var(--paper);
  font-size: 10px;
  font-weight: 800;
}
.wa-amber { color: var(--amber); }
.wa-badge {
  margin-left: 4px;
  padding: 2px 6px;
  border: 1px solid var(--rule);
  border-radius: 2px;
  font-size: 9px;
  font-weight: 600;
  letter-spacing: .16em;
  color: var(--inkSoft);
  text-transform: uppercase;
}
.wa-vsep { width: 1px; height: 20px; background: var(--rule); flex-shrink: 0; }
.wa-proj-name { font-size: 14px; font-weight: 600; }
.wa-proj-sub { font-family: var(--font-mono); font-size: 10px; color: var(--inkMute); }
.wa-sub-alert { color: var(--amber); }

.wa-health-pill {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 4px 12px;
  background: var(--paperAlt);
  border: 1px solid var(--rule);
  border-radius: 999px;
  font-family: var(--font-mono);
  font-size: 11px;
  color: var(--inkSoft);
  flex-shrink: 0;
}
.wa-health-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}
.wa-health-dot.ok   { background: var(--teal); }
.wa-health-dot.warn { background: var(--amber); animation: tracePulseDot 1.4s ease-in-out infinite; }

.wa-btn-add {
  padding: 6px 12px;
  background: var(--ink);
  color: var(--paper);
  border: none;
  border-radius: 3px;
  cursor: pointer;
  font-family: var(--font-sans);
  font-size: 12.5px;
  font-weight: 600;
  flex-shrink: 0;
}
.wa-btn-add:hover { opacity: .88; }

/* ─── Tabs ─────────────────────────────────────────────────────────────────── */
.wa-tabs { display: flex; }
.wa-tab {
  padding: 8px 14px;
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  font-family: var(--font-sans);
  font-size: 13px;
  font-weight: 550;
  color: var(--inkMute);
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-bottom: -1px;
}
.wa-tab.active { color: var(--ink); border-bottom-color: var(--ink); }
.wa-tab-badge {
  padding: 1px 5px;
  background: var(--amberBg);
  border: 1px solid var(--amber);
  border-radius: 999px;
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--amber);
}

.wa-btn-outline-sm {
  padding: 5px 11px;
  background: transparent;
  border: 1px solid var(--rule);
  border-radius: 3px;
  cursor: pointer;
  font-family: var(--font-sans);
  font-size: 12px;
  font-weight: 550;
  color: var(--inkSoft);
}

/* ─── Wizard layout ────────────────────────────────────────────────────────── */
.wa-main { flex: 1; overflow: auto; }
.wa-center { display: flex; align-items: flex-start; justify-content: center; padding: 40px 24px; }
.wa-wizard-inner { width: 100%; max-width: 620px; }
.wa-wizard-inner--wide { max-width: 900px; margin: 0 auto; padding: 32px 40px; }
.wa-eyebrow { font-family: var(--font-mono); font-size: 10px; color: var(--inkMute); letter-spacing: .18em; text-transform: uppercase; }
.wa-h1 { margin: 10px 0 0; font-size: 28px; font-weight: 700; letter-spacing: -.02em; }
.wa-lead { margin: 10px 0 0; font-size: 14px; color: var(--inkSoft); line-height: 1.6; max-width: 520px; }

/* ─── Drop zone A1 ─────────────────────────────────────────────────────────── */
.wa-dropzone {
  margin-top: 28px;
  background: var(--paperAlt);
  border: 2px dashed var(--rule);
  border-radius: 6px;
  padding: 40px 32px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  cursor: pointer;
  transition: border-color .15s, background .15s;
}
.wa-dropzone.dragging { border-color: var(--amber); background: var(--amberBg); }
.wa-drop-stack { position: relative; width: 64px; height: 76px; }
.wa-doc-sheet {
  position: absolute;
  width: 52px;
  height: 66px;
  border-radius: 3px;
  background: var(--paperAlt);
  border: 1px solid var(--rule);
}
.wa-drop-text { text-align: center; }
.wa-drop-text strong { font-size: 16px; font-weight: 600; display: block; }
.wa-drop-sub { font-family: var(--font-mono); font-size: 11px; color: var(--inkMute); margin-top: 6px; display: block; }
.wa-btn-outline {
  padding: 8px 14px;
  background: transparent;
  color: var(--ink);
  border: 1px solid var(--rule);
  border-radius: 3px;
  cursor: pointer;
  font-family: var(--font-sans);
  font-size: 12.5px;
  font-weight: 550;
}
.wa-existing-info { margin-top: 12px; text-align: center; }

/* ─── File list A2 ─────────────────────────────────────────────────────────── */
.wa-wizard-back-row {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
}
.wa-filelist {
  background: var(--paperAlt);
  border: 1px solid var(--rule);
  border-radius: 4px;
  overflow: hidden;
}
.wa-filerow {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 11px 16px;
  border-bottom: 1px solid var(--ruleSoft);
}
.wa-filerow:last-child { border-bottom: none; }
.wa-file-icon {
  font-family: var(--font-mono);
  font-size: 8px;
  font-weight: 700;
  width: 28px;
  height: 36px;
  border: 1px solid var(--rule);
  border-radius: 2px;
  background: var(--paper);
  display: flex;
  align-items: flex-end;
  padding: 0 4px 4px;
  flex-shrink: 0;
}
.wa-file-info { flex: 1; min-width: 0; }
.wa-file-name { font-size: 13px; font-weight: 550; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.wa-file-meta { font-family: var(--font-mono); font-size: 10px; color: var(--inkMute); }
.wa-file-type-badge {
  padding: 2px 8px;
  background: var(--paper);
  border: 1px solid var(--rule);
  border-radius: 2px;
  font-family: var(--font-mono);
  font-size: 9.5px;
  font-weight: 600;
  color: var(--inkSoft);
  letter-spacing: .06em;
  flex-shrink: 0;
}
.wa-file-remove {
  width: 24px;
  height: 24px;
  border: none;
  background: transparent;
  cursor: pointer;
  color: var(--inkMute);
  border-radius: 3px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
}
.wa-file-remove:hover { background: var(--ruleSoft); color: var(--ink); }
.wa-add-more-row { margin-top: 12px; }

/* ─── A3 Context ───────────────────────────────────────────────────────────── */
.wa-a3-header { text-align: center; margin-bottom: 24px; }
.wa-a3-icon { font-size: 40px; margin-bottom: 12px; }
.wa-a3-title { font-size: 20px; font-weight: 700; margin: 0 0 8px; }
.wa-a3-sub { font-size: 14px; color: var(--inkSoft); line-height: 1.6; }
.wa-classification-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 24px;
  justify-content: center;
}
.wa-classif-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  background: var(--paperAlt);
  border: 1px solid var(--rule);
  border-radius: 4px;
}
.wa-classif-icon { font-size: 16px; }
.wa-classif-count { font-size: 16px; font-weight: 700; color: var(--ink); }
.wa-classif-label { font-size: 12px; color: var(--inkSoft); }

.wa-context-form { display: flex; flex-direction: column; gap: 16px; }
.wa-field { display: flex; flex-direction: column; gap: 6px; }
.wa-label { font-size: 13px; font-weight: 550; color: var(--ink); }
.wa-input {
  padding: 9px 12px;
  background: var(--paperAlt);
  border: 1px solid var(--rule);
  border-radius: 3px;
  font-family: var(--font-sans);
  font-size: 13.5px;
  color: var(--ink);
  outline: none;
}
.wa-input:focus { border-color: var(--ink); }
.wa-textarea {
  padding: 9px 12px;
  background: var(--paperAlt);
  border: 1px solid var(--rule);
  border-radius: 3px;
  font-family: var(--font-sans);
  font-size: 13.5px;
  color: var(--ink);
  outline: none;
  resize: vertical;
  line-height: 1.5;
}
.wa-textarea:focus { border-color: var(--ink); }

/* ─── A4 Plan ──────────────────────────────────────────────────────────────── */
.wa-a4-header { margin-bottom: 20px; }
.wa-a4-title { font-size: 22px; font-weight: 700; margin: 0 0 6px; }
.wa-a4-sub { font-size: 14px; color: var(--inkSoft); }
.wa-plan-table-wrap {
  overflow-x: auto;
  border: 1px solid var(--rule);
  border-radius: 4px;
}
.wa-plan-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.wa-plan-table th {
  padding: 10px 14px;
  text-align: left;
  font-family: var(--font-mono);
  font-size: 9.5px;
  font-weight: 700;
  letter-spacing: .12em;
  text-transform: uppercase;
  color: var(--inkMute);
  background: var(--paper);
  border-bottom: 1px solid var(--rule);
}
.wa-plan-table td {
  padding: 10px 14px;
  border-bottom: 1px solid var(--ruleSoft);
  vertical-align: middle;
}
.wa-plan-table tr:last-child td { border-bottom: none; }
.wa-plan-name { font-family: var(--font-mono); font-size: 12px; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 260px; }
.wa-plan-type {
  padding: 2px 8px;
  background: var(--paper);
  border: 1px solid var(--rule);
  border-radius: 2px;
  font-size: 11.5px;
  color: var(--inkSoft);
}
.wa-plan-strategy { font-size: 12.5px; color: var(--inkSoft); }
.wa-plan-prio { font-family: var(--font-mono); font-size: 11px; font-weight: 600; }
.wa-plan-context { margin-top: 14px; padding: 10px 14px; background: var(--paperAlt); border: 1px solid var(--rule); border-radius: 3px; }
.wa-plan-eta { margin-top: 10px; }

/* ─── Actions communes wizard ──────────────────────────────────────────────── */
.wa-wizard-actions { display: flex; align-items: center; gap: 14px; margin-top: 28px; }
.wa-btn-primary {
  padding: 9px 16px;
  background: var(--ink);
  color: var(--paper);
  border: none;
  border-radius: 3px;
  cursor: pointer;
  font-family: var(--font-sans);
  font-size: 13.5px;
  font-weight: 600;
}
.wa-btn-primary:hover:not(:disabled) { opacity: .88; }
.wa-btn-primary:disabled { opacity: .45; cursor: not-allowed; }
.wa-btn-lg { padding: 11px 20px; font-size: 14.5px; }
.wa-btn-launch { display: inline-flex; align-items: center; gap: 7px; }
.wa-btn-ghost {
  padding: 8px 12px;
  background: transparent;
  border: 1px solid var(--rule);
  border-radius: 3px;
  cursor: pointer;
  font-family: var(--font-sans);
  font-size: 13px;
  font-weight: 550;
  color: var(--inkSoft);
}
.wa-btn-ghost:hover { background: var(--ruleSoft); }
.wa-btn-cancel {
  padding: 7px 13px;
  background: transparent;
  color: var(--red);
  border: 1px solid color-mix(in srgb, var(--red) 40%, transparent);
  border-radius: 3px;
  cursor: pointer;
  font-family: var(--font-sans);
  font-size: 12.5px;
  font-weight: 550;
}

/* ─── A5 Progress ──────────────────────────────────────────────────────────── */
.wa-a5-wrap { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
.wa-stats-bar {
  padding: 18px 28px;
  display: grid;
  grid-template-columns: 1.5fr 1fr 1fr 1fr;
  gap: 24px;
  border-bottom: 1px solid var(--rule);
  flex-shrink: 0;
  background: var(--paperAlt);
}
.wa-stat-main { }
.wa-stat-title { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.wa-live-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--amber); display: inline-block; }
.wa-stat-name { font-size: 17px; font-weight: 600; letter-spacing: -.015em; }
.wa-stat-box { border-left: 1px solid var(--rule); padding-left: 16px; }

.wa-pipeline-wrap { padding: 20px 28px 14px; flex-shrink: 0; }
.wa-pipeline-label { font-size: 10px; letter-spacing: .18em; text-transform: uppercase; margin-bottom: 14px; }
.wa-pipeline {
  position: relative;
  display: grid;
  grid-template-columns: repeat(10, 1fr);
}
.wa-pipeline-line { position: absolute; top: 17px; left: 18px; right: 18px; height: 2px; background: var(--ruleSoft); z-index: 0; }
.wa-pipeline-fill { position: absolute; top: 17px; left: 18px; height: 2px; background: var(--teal); z-index: 1; transition: width 600ms; }
.wa-node { display: flex; flex-direction: column; align-items: center; gap: 4px; z-index: 2; position: relative; }
.wa-node-dot {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: var(--paper);
  border: 2px solid var(--rule);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  position: relative;
}
.wa-node-dot.done { background: var(--teal); border-color: var(--teal); }
.wa-node-dot.running { background: var(--amber); border-color: var(--amber); box-shadow: 0 0 0 4px color-mix(in srgb, var(--amber) 20%, transparent); }
.wa-node-dot.error { border-color: var(--red); }
.wa-check { color: #fff; font-size: 13px; font-weight: 700; }
.wa-spin-ring {
  position: absolute;
  inset: -8px;
  border-radius: 50%;
  border: 1.5px dashed var(--amber);
}
.wa-node-name { font-size: 10.5px; font-weight: 600; text-align: center; color: var(--inkMute); }
.wa-node-name.done    { color: var(--inkSoft); }
.wa-node-name.running { color: var(--ink); }
.wa-node-counter {
  font-size: 9px;
  text-align: center;
  color: var(--teal);
  margin-top: 2px;
  max-width: 80px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.wa-log-wrap { flex: 1; padding: 16px 28px 20px; display: flex; flex-direction: column; gap: 10px; min-height: 0; }
.wa-log-header { display: flex; align-items: center; gap: 10px; }
.wa-rec-badge { color: var(--red); }
.wa-console {
  flex: 1;
  background: var(--ink);
  border-radius: 4px;
  padding: 14px 16px;
  overflow: auto;
  font-size: 11.5px;
  line-height: 1.7;
}
.wa-log-line { display: flex; gap: 10px; }
.wa-log-time { color: #615E55; flex-shrink: 0; }
.wa-log-lvl { flex-shrink: 0; font-weight: 700; width: 36px; text-transform: uppercase; letter-spacing: .06em; font-size: 10px; }
.wa-log-agent { color: var(--inkMute); flex-shrink: 0; width: 56px; }
.wa-log-msg { flex: 1; color: #C5C1B6; }

/* ─── Utilitaires ──────────────────────────────────────────────────────────── */
.wa-mono { font-family: var(--font-mono); }
.wa-mute { color: var(--inkMute); }
</style>
