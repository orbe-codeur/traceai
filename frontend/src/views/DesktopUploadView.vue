<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../services/api.js'
import { useToast } from '../composables/useToast.js'

const { error: toastError } = useToast()

const router = useRouter()

const projectName    = ref('')
const selectedFile   = ref(null)
const loading        = ref(false)
const dragOver       = ref(false)
const recentProjects = ref([])
const search         = ref('')

// Extraction live
const extractProgress = ref(0)      // 0-100
const extractStepCount = ref(0)
const extractCategories = ref({})
const CATEGORIES_META = {
  'sécurité':     { short: 'SEC',   color: '#C8312D' },
  'mécanique':    { short: 'MEC',   color: '#56524A' },
  'électrique':   { short: 'ELEC',  color: '#2E5C9E' },
  'hydraulique':  { short: 'HYD',   color: '#1F5F5B' },
  'test':         { short: 'TEST',  color: '#7A4F1D' },
  'vérification': { short: 'VERIF', color: '#3D3936' },
}
let progressTimer = null

function startFakeProgress() {
  extractProgress.value   = 0
  extractStepCount.value  = 0
  extractCategories.value = {}
  let elapsed = 0
  progressTimer = setInterval(() => {
    elapsed += 1
    // Progression logarithmique : rapide au début, ralentit vers 90%
    extractProgress.value = Math.min(90, Math.round(90 * (1 - Math.exp(-elapsed / 25))))
    // Simuler des steps trouvées
    extractStepCount.value = Math.floor(extractProgress.value * 0.6)
    // Simuler catégories qui apparaissent progressivement
    const cats = Object.keys(CATEGORIES_META)
    const visibleCount = Math.ceil((extractProgress.value / 90) * cats.length)
    cats.slice(0, visibleCount).forEach(cat => {
      if (!extractCategories.value[cat]) {
        extractCategories.value[cat] = Math.floor(Math.random() * 8) + 2
      }
    })
  }, 1000)
}

function stopFakeProgress(realStepCount) {
  clearInterval(progressTimer)
  extractStepCount.value = realStepCount
  extractProgress.value  = 100
}

onMounted(async () => {
  try {
    const { data } = await api.getProjects()
    recentProjects.value = data
  } catch {
    // pas de backend encore — silencieux
  }
})

function onFileChange(e) {
  selectedFile.value = e.target.files[0] || null
}
function onDrop(e) {
  dragOver.value = false
  selectedFile.value = e.dataTransfer.files[0] || null
}

const filteredProjects = computed(() => {
  const q = search.value.trim().toLowerCase()
  if (!q) return recentProjects.value
  return recentProjects.value.filter(p =>
    p.name.toLowerCase().includes(q) || (p.pdf_filename || '').toLowerCase().includes(q)
  )
})

async function handleSubmit() {
  if (!projectName.value.trim() || !selectedFile.value) return
  loading.value = true
  startFakeProgress()
  try {
    const { data } = await api.uploadProject(projectName.value.trim(), selectedFile.value)
    stopFakeProgress(data.total_steps)
    await new Promise(r => setTimeout(r, 600)) // laisser voir 100%
    router.push(`/project/${data.project_id}`)
  } catch (err) {
    stopFakeProgress(0)
    toastError(err?.response?.data?.detail || 'Erreur lors de l\'analyse du PDF.')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="upload-page">
    <header class="upload-topbar">
      <div class="wordmark">
        <span class="wordmark-t">T</span>
        <span>Trace<span style="color:var(--amber)">AI</span></span>
      </div>
    </header>

    <div class="upload-body">
      <!-- Formulaire principal -->
      <div class="upload-card">
        <div class="upload-card-header">
          <h1>Nouveau projet</h1>
          <p>Importer un manuel d'installation PDF pour générer la checklist</p>
        </div>

        <div class="upload-card-body">
          <div class="field">
            <label>Nom du projet</label>
            <input
              v-model="projectName"
              type="text"
              placeholder="Installation ORC Enogia — Site Metz"
              class="input-field"
            />
          </div>

          <div class="field">
            <label>Manuel PDF</label>
            <div
              class="drop-zone"
              :class="{ 'drag-over': dragOver, 'has-file': !!selectedFile }"
              @dragover.prevent="dragOver = true"
              @dragleave="dragOver = false"
              @drop.prevent="onDrop"
              @click="$refs.fileInput.click()"
            >
              <input ref="fileInput" type="file" accept=".pdf" class="hidden-input" @change="onFileChange" />

              <template v-if="!selectedFile">
                <div class="drop-icon">
                  <svg width="40" height="48" viewBox="0 0 40 48" fill="none">
                    <rect x="1" y="1" width="30" height="46" rx="2" fill="var(--paperAlt)" stroke="var(--rule)" stroke-width="1.5"/>
                    <path d="M31 1L39 9H31V1Z" fill="var(--ruleSoft)" stroke="var(--rule)" stroke-width="1.5"/>
                    <rect x="7" y="18" width="16" height="2" rx="1" fill="var(--rule)"/>
                    <rect x="7" y="23" width="20" height="2" rx="1" fill="var(--rule)"/>
                    <rect x="7" y="28" width="12" height="2" rx="1" fill="var(--rule)"/>
                  </svg>
                </div>
                <p class="drop-main">Glisser le PDF ici</p>
                <p class="drop-sub">ou <span class="drop-browse">parcourir</span> · max 50 Mo</p>
              </template>

              <template v-else>
                <div class="file-info">
                  <span class="file-name">{{ selectedFile.name }}</span>
                  <span class="file-size">{{ (selectedFile.size / 1024 / 1024).toFixed(1) }} Mo</span>
                </div>
                <button class="btn-change" @click.stop="$refs.fileInput.click()">Changer</button>
              </template>
            </div>
          </div>

          <div v-if="loading" class="extraction-screen">
            <div class="ext-header">
              <span class="ext-pulse animate-trace-dot" />
              <span class="ext-label">Extraction en cours</span>
              <span class="ext-model">Mistral large</span>
            </div>

            <div class="ext-progress-wrap">
              <div class="ext-progress-bar" :style="{ width: extractProgress + '%' }" />
            </div>

            <div class="ext-count">
              <span class="ext-count-num">{{ extractStepCount }}</span>
              <span class="ext-count-label">étapes trouvées</span>
            </div>

            <div class="ext-categories">
              <div
                v-for="(count, cat) in extractCategories"
                :key="cat"
                class="ext-cat"
                :style="{ borderLeftColor: CATEGORIES_META[cat]?.color || '#8A8478' }"
              >
                <span class="ext-cat-short" :style="{ color: CATEGORIES_META[cat]?.color }">
                  {{ CATEGORIES_META[cat]?.short || cat }}
                </span>
                <span class="ext-cat-name">{{ cat }}</span>
                <span class="ext-cat-count">{{ count }}</span>
              </div>
            </div>
          </div>

          <button v-else class="btn-submit" :disabled="!projectName || !selectedFile" @click="handleSubmit">
            Analyser le manuel
          </button>
        </div>
      </div>

      <!-- Projets récents -->
      <div v-if="recentProjects.length" class="recent-section">
        <span class="recent-title">Projets récents</span>
        <div class="recent-search-wrap">
          <input
            v-model="search"
            type="text"
            class="recent-search"
            placeholder="Rechercher…"
          />
          <button v-if="search" class="recent-search-clear" @click="search = ''">✕</button>
        </div>
        <div class="recent-list">
          <div
            v-for="p in filteredProjects"
            :key="p.id"
            class="recent-card"
            @click="router.push(`/project/${p.id}`)"
          >
            <div class="recent-card-top">
              <span class="recent-name">{{ p.name }}</span>
              <span class="recent-ratio" :style="{ color: p.completed_steps >= p.total_steps ? 'var(--teal)' : 'var(--amber)' }">
                {{ p.completed_steps }}/{{ p.total_steps }}
              </span>
            </div>
            <span class="recent-ref">{{ p.pdf_filename }}</span>
          </div>
          <div v-if="!filteredProjects.length" class="recent-empty">Aucun résultat.</div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.upload-page { min-height: 100vh; background: var(--paper); display: flex; flex-direction: column; }

.upload-topbar {
  height: 56px;
  background: var(--ink);
  display: flex;
  align-items: center;
  padding: 0 28px;
}
.wordmark {
  display: flex;
  align-items: center;
  gap: 6px;
  font-family: var(--font-mono);
  font-size: 16px;
  font-weight: 700;
  color: #fff;
}
.wordmark-t {
  background: var(--amber);
  color: var(--ink);
  width: 22px;
  height: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 2px;
  font-size: 13px;
}

.upload-body {
  flex: 1;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  gap: 32px;
  padding: 48px 32px;
}

.upload-card {
  width: 480px;
  background: var(--paperAlt);
  border: 1px solid var(--rule);
  border-radius: 4px;
  overflow: hidden;
  flex-shrink: 0;
}
.upload-card-header {
  padding: 24px 28px 20px;
  border-bottom: 1px solid var(--ruleSoft);
}
.upload-card-header h1 {
  font-size: 22px;
  font-weight: 600;
  letter-spacing: -0.02em;
  color: var(--ink);
  margin-bottom: 4px;
}
.upload-card-header p { font-size: 13px; color: var(--inkSoft); }
.upload-card-body { padding: 24px 28px; display: flex; flex-direction: column; gap: 18px; }

.field { display: flex; flex-direction: column; gap: 6px; }
.field label {
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--inkMute);
}
.input-field {
  border: 1px solid var(--rule);
  border-radius: 2px;
  padding: 9px 12px;
  font-family: var(--font-sans);
  font-size: 13.5px;
  color: var(--ink);
  background: var(--paper);
  outline: none;
  width: 100%;
}
.input-field:focus { border-color: var(--ink); }

.drop-zone {
  border: 1.5px dashed var(--rule);
  border-radius: 3px;
  padding: 28px 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
  background-image: linear-gradient(var(--ruleSoft) 1px, transparent 1px),
                    linear-gradient(90deg, var(--ruleSoft) 1px, transparent 1px);
  background-size: 24px 24px;
  background-color: var(--paper);
}
.drop-zone:hover, .drop-zone.drag-over { border-color: var(--ink); background-color: var(--paperAlt); }
.drop-zone.has-file { border-style: solid; border-color: var(--teal); background-image: none; }
.hidden-input { display: none; }
.drop-icon { margin-bottom: 4px; }
.drop-main { font-size: 14px; font-weight: 500; color: var(--ink); }
.drop-sub { font-size: 12px; color: var(--inkMute); }
.drop-browse { color: var(--blue); text-decoration: underline; }
.file-info { display: flex; flex-direction: column; align-items: center; gap: 3px; }
.file-name { font-size: 13px; font-weight: 550; color: var(--teal); }
.file-size { font-family: var(--font-mono); font-size: 11px; color: var(--inkMute); }
.btn-change {
  font-size: 11px;
  color: var(--inkSoft);
  background: none;
  border: 1px solid var(--rule);
  border-radius: 2px;
  padding: 3px 10px;
  cursor: pointer;
  margin-top: 4px;
}

.extraction-screen {
  background: var(--ink);
  border-radius: 3px;
  padding: 18px 16px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.ext-header {
  display: flex;
  align-items: center;
  gap: 8px;
}
.ext-pulse {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--amber);
  flex-shrink: 0;
}
.ext-label { font-size: 13px; font-weight: 600; color: var(--amber); flex: 1; }
.ext-model { font-family: var(--font-mono); font-size: 10px; color: #666; }

.ext-progress-wrap {
  height: 3px;
  background: #333;
  border-radius: 2px;
  overflow: hidden;
}
.ext-progress-bar {
  height: 100%;
  background: var(--amber);
  border-radius: 2px;
  transition: width 0.8s ease;
}

.ext-count {
  display: flex;
  align-items: baseline;
  gap: 6px;
}
.ext-count-num {
  font-family: var(--font-mono);
  font-size: 28px;
  font-weight: 700;
  color: #fff;
  line-height: 1;
}
.ext-count-label {
  font-family: var(--font-mono);
  font-size: 10px;
  color: #666;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.ext-categories {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
}
.ext-cat {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 5px 8px;
  background: #1a1a17;
  border-radius: 2px;
  border-left: 2px solid;
}
.ext-cat-short {
  font-family: var(--font-mono);
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.06em;
  width: 32px;
  flex-shrink: 0;
}
.ext-cat-name { font-size: 11px; color: #888; flex: 1; }
.ext-cat-count {
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 600;
  color: #ccc;
}

.btn-submit {
  width: 100%;
  height: 42px;
  background: var(--ink);
  color: var(--paper);
  border: none;
  border-radius: 3px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.15s;
}
.btn-submit:disabled { opacity: 0.35; cursor: not-allowed; }
.btn-submit:not(:disabled):hover { opacity: 0.88; }

.recent-section { width: 280px; flex-shrink: 0; }
.recent-title {
  font-family: var(--font-mono);
  font-size: 9px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--inkMute);
  display: block;
  margin-bottom: 10px;
}
.recent-search-wrap { position: relative; margin-bottom: 8px; }
.recent-search {
  width: 100%;
  border: 1px solid var(--rule);
  border-radius: 2px;
  padding: 7px 28px 7px 10px;
  font-family: var(--font-sans);
  font-size: 12.5px;
  color: var(--ink);
  background: var(--paper);
  outline: none;
}
.recent-search:focus { border-color: var(--ink); }
.recent-search-clear {
  position: absolute; right: 8px; top: 50%; transform: translateY(-50%);
  background: none; border: none; font-size: 11px; color: var(--inkMute); cursor: pointer; padding: 0;
}
.recent-search-clear:hover { color: var(--ink); }
.recent-empty { font-size: 12px; color: var(--inkMute); text-align: center; padding: 16px 0; }
.recent-list { display: flex; flex-direction: column; gap: 6px; }
.recent-card {
  background: var(--paperAlt);
  border: 1px solid var(--rule);
  border-radius: 3px;
  padding: 12px 14px;
  cursor: pointer;
  transition: border-color 0.12s;
}
.recent-card:hover { border-color: var(--ink); }
.recent-card-top { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.recent-name { font-size: 13px; font-weight: 550; color: var(--ink); }
.recent-ratio { font-family: var(--font-mono); font-size: 11px; flex-shrink: 0; }
.recent-ref { font-family: var(--font-mono); font-size: 10px; color: var(--inkMute); margin-top: 3px; display: block; }
</style>
