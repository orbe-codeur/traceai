<script setup>
import { ref, computed, reactive, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import CatChip from '../../components/CatChip.vue'
import Avatar from '../../components/Avatar.vue'
import ProgressTrack from '../../components/ProgressTrack.vue'
import api from '../../services/api.js'
import { useToast } from '../../composables/useToast.js'

const route  = useRoute()
const router = useRouter()
const { success: toastSuccess, error: toastError, warn: toastWarn } = useToast()

const projectId = computed(() => Number(route.params.id))
const project   = ref(null)
const steps     = ref([])
const validations = reactive({})
const loading   = ref(true)
const filter    = ref('all')
const expandedId = ref(null)

// Formulaire de validation
const techName    = ref(localStorage.getItem('traceai_tech') || '')
const note        = ref('')
const witnessName = ref('')
const saving      = ref(false)

onMounted(async () => {
  try {
    const [stepsRes, projectsRes] = await Promise.all([api.getSteps(projectId.value), api.getProjects()])
    steps.value = stepsRes.data
    for (const s of steps.value) {
      if (s.status !== 'pending') {
        validations[s.id] = { status: s.status, technician_name: s.technician_name, note: s.note, witness_name: s.witness_name, validated_at: s.validated_at }
      }
    }
    project.value = projectsRes.data.find(p => p.id === projectId.value) || null
  } finally { loading.value = false }
})

const filterCounts = computed(() => ({
  all:     steps.value.length,
  pending: steps.value.filter(s => !validations[s.id]).length,
  done:    steps.value.filter(s => validations[s.id]?.status === 'done').length,
  issue:   steps.value.filter(s => validations[s.id]?.status === 'issue').length,
}))

const visibleSteps = computed(() => steps.value.filter(s => {
  const st = validations[s.id]?.status || 'pending'
  if (filter.value === 'pending' && st !== 'pending') return false
  if (filter.value === 'done'    && st !== 'done')    return false
  if (filter.value === 'issue'   && st !== 'issue')   return false
  return true
}))

function toggleExpand(id) {
  expandedId.value = expandedId.value === id ? null : id
  note.value = ''
  witnessName.value = ''
}

function fmtTime(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })
}

function stepColor(step) {
  const v = validations[step.id]
  if (!v) return step.is_critical ? 'var(--red)' : 'var(--ruleSoft)'
  if (v.status === 'done')   return 'var(--teal)'
  if (v.status === 'issue')  return 'var(--amber)'
  if (v.status === 'active') return 'var(--amber)'
  return 'var(--ruleSoft)'
}

async function validate(step, status) {
  if (!techName.value.trim()) return toastWarn('Veuillez renseigner votre nom.')
  if (status === 'issue' && !note.value.trim()) return toastWarn('Décrivez le problème dans la note.')
  if (step.requires_witness && status === 'done' && !witnessName.value.trim()) return toastWarn('Un témoin est requis.')
  localStorage.setItem('traceai_tech', techName.value.trim())
  saving.value = true
  try {
    const { data: updated } = await api.validateStep(step.id, { technician_name: techName.value.trim(), status, note: note.value || null, witness_name: witnessName.value || null })
    const idx = steps.value.findIndex(s => s.id === updated.id)
    if (idx !== -1) steps.value[idx] = updated
    validations[step.id] = { status: updated.status, technician_name: updated.technician_name, note: updated.note, witness_name: updated.witness_name, validated_at: updated.validated_at }
    if (project.value) project.value.completed_steps = Object.values(validations).filter(v => v.status === 'done').length
    expandedId.value = null
    note.value = ''
    toastSuccess(status === 'done' ? 'Étape validée ✓' : 'Problème signalé')
  } catch (e) {
    toastError(e?.response?.data?.detail || 'Erreur de validation.')
  } finally { saving.value = false }
}
</script>

<template>
  <div class="mobile-page">
    <header class="m-topbar">
      <button class="m-back" @click="router.push('/')">←</button>
      <div class="m-proj-title">
        <span class="m-proj-name">{{ project?.name || '…' }}</span>
      </div>
      <button class="m-journal-btn" @click="router.push(`/project/${projectId}/summary`)">📋</button>
    </header>

    <div v-if="!loading && project" class="m-progress-wrap">
      <ProgressTrack :steps="steps" :validations="validations" />
    </div>

    <div v-if="loading" class="m-loading">Chargement…</div>

    <template v-else>
      <!-- Filtres -->
      <div class="m-filters">
        <button v-for="f in [['all','Toutes'],['pending','À faire'],['done','Validées'],['issue','Problèmes']]" :key="f[0]"
          class="m-filter" :class="{ active: filter === f[0] }" @click="filter = f[0]">
          {{ f[1] }}
          <span class="m-filter-count">{{ filterCounts[f[0]] }}</span>
        </button>
      </div>

      <!-- Liste steps -->
      <div class="m-steps">
        <div v-for="step in visibleSteps" :key="step.id" class="m-step-card">
          <!-- En-tête card -->
          <div class="m-step-header" @click="toggleExpand(step.id)">
            <div class="m-step-rail" :style="{ background: stepColor(step) }" />
            <div class="m-step-info">
              <div class="m-step-top">
                <span class="m-step-num">{{ String(step.step_number).padStart(2,'0') }}</span>
                <CatChip :cat="step.category" />
                <span v-if="step.is_critical" class="m-crit">●</span>
                <span class="m-step-page">p.{{ step.page_ref }}</span>
              </div>
              <span class="m-step-title">{{ step.title }}</span>
            </div>
            <!-- Statut badge -->
            <div class="m-step-status">
              <template v-if="validations[step.id]?.status === 'done'">
                <span class="m-status-badge done">✓</span>
              </template>
              <template v-else-if="validations[step.id]?.status === 'issue'">
                <span class="m-status-badge issue">!</span>
              </template>
              <template v-else>
                <span class="m-chevron">{{ expandedId === step.id ? '▲' : '▼' }}</span>
              </template>
            </div>
          </div>

          <!-- Strip done/issue -->
          <div v-if="validations[step.id]?.status === 'done'" class="m-strip done">
            <Avatar :name="validations[step.id].technician_name" :size="20" />
            <span>{{ validations[step.id].technician_name }} · {{ fmtTime(validations[step.id].validated_at) }}</span>
          </div>
          <div v-if="validations[step.id]?.status === 'issue'" class="m-strip issue">
            <Avatar :name="validations[step.id].technician_name" :size="20" />
            <span style="font-style:italic">{{ validations[step.id].note }}</span>
          </div>

          <!-- Corps expanded -->
          <div v-if="expandedId === step.id" class="m-step-body">
            <p class="m-step-desc">{{ step.description }}</p>

            <div class="m-form">
              <div class="m-field">
                <label>Votre nom</label>
                <input v-model="techName" class="m-input" placeholder="Prénom Nom" />
              </div>
              <div v-if="step.requires_witness" class="m-field">
                <label style="color:var(--red)">★ Témoin requis</label>
                <input v-model="witnessName" class="m-input" placeholder="Nom du témoin" />
              </div>
              <div class="m-field">
                <label>Note <span style="opacity:.5">(optionnel)</span></label>
                <textarea v-model="note" class="m-textarea" rows="2" placeholder="Observations…" />
              </div>
              <div class="m-actions">
                <button class="m-btn-validate" :disabled="saving" @click="validate(step, 'done')">
                  {{ saving ? '…' : '✓ Valider' }}
                </button>
                <button class="m-btn-issue" :disabled="saving" @click="validate(step, 'issue')">
                  ⚠ Problème
                </button>
              </div>
            </div>
          </div>
        </div>

        <div v-if="!visibleSteps.length" class="m-empty">Aucune étape dans ce filtre.</div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.mobile-page { min-height: 100vh; background: var(--paper); display: flex; flex-direction: column; }
.m-topbar {
  height: 52px; background: var(--ink); display: flex; align-items: center;
  padding: 0 14px; gap: 10px; position: sticky; top: 0; z-index: 10; flex-shrink: 0;
}
.m-back { background: none; border: none; color: #fff; font-size: 20px; cursor: pointer; padding: 0; flex-shrink: 0; }
.m-proj-title { flex: 1; overflow: hidden; }
.m-proj-name { font-size: 14px; font-weight: 600; color: #fff; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; display: block; }
.m-journal-btn { background: none; border: none; font-size: 18px; cursor: pointer; flex-shrink: 0; }

.m-progress-wrap { padding: 12px 16px 8px; background: var(--paperAlt); border-bottom: 1px solid var(--rule); }
.m-loading { flex: 1; display: flex; align-items: center; justify-content: center; font-size: 13px; color: var(--inkMute); }

.m-filters {
  display: flex; gap: 4px; padding: 8px 12px;
  overflow-x: auto; border-bottom: 1px solid var(--ruleSoft); flex-shrink: 0;
}
.m-filter {
  padding: 5px 11px; border-radius: 20px; font-size: 12px; font-weight: 500;
  background: transparent; border: 1px solid var(--rule); color: var(--inkSoft);
  cursor: pointer; white-space: nowrap; display: flex; align-items: center; gap: 4px;
}
.m-filter.active { background: var(--ink); color: var(--paper); border-color: var(--ink); }
.m-filter-count { font-family: var(--font-mono); font-size: 10px; opacity: .6; }

.m-steps { flex: 1; overflow-y: auto; padding: 8px 12px; display: flex; flex-direction: column; gap: 6px; }
.m-empty { text-align: center; padding: 32px; font-size: 13px; color: var(--inkMute); }

.m-step-card { background: var(--paperAlt); border: 1px solid var(--rule); border-radius: 3px; overflow: hidden; }
.m-step-header { display: flex; align-items: stretch; cursor: pointer; min-height: 56px; }
.m-step-rail { width: 3px; flex-shrink: 0; }
.m-step-info { flex: 1; padding: 10px 10px 10px 8px; display: flex; flex-direction: column; gap: 4px; }
.m-step-top { display: flex; align-items: center; gap: 6px; }
.m-step-num { font-family: var(--font-mono); font-size: 10px; color: var(--inkMute); font-weight: 600; }
.m-crit { color: var(--red); font-size: 6px; }
.m-step-page { font-family: var(--font-mono); font-size: 10px; color: var(--inkMute); margin-left: auto; }
.m-step-title { font-size: 13.5px; font-weight: 550; color: var(--ink); line-height: 1.35; }
.m-step-status { display: flex; align-items: center; justify-content: center; padding: 0 12px; flex-shrink: 0; }
.m-status-badge { width: 20px; height: 20px; border-radius: 3px; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 700; }
.m-status-badge.done  { background: var(--teal); color: #fff; }
.m-status-badge.issue { background: var(--amber); color: #fff; }
.m-chevron { font-size: 10px; color: var(--inkMute); }

.m-strip {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 12px; font-size: 12px;
}
.m-strip.done  { background: var(--tealBg); color: var(--teal); border-top: 1px solid var(--ruleSoft); }
.m-strip.issue { background: var(--amberBg); color: var(--inkSoft); border-top: 1px solid var(--ruleSoft); border-left: 3px solid var(--amber); }

.m-step-body { padding: 12px; border-top: 1px solid var(--ruleSoft); }
.m-step-desc { font-size: 12.5px; color: var(--inkSoft); line-height: 1.5; margin-bottom: 14px; }

.m-form { display: flex; flex-direction: column; gap: 10px; }
.m-field { display: flex; flex-direction: column; gap: 4px; }
.m-field label { font-family: var(--font-mono); font-size: 9px; font-weight: 600; text-transform: uppercase; letter-spacing: .06em; color: var(--inkMute); }
.m-input {
  border: 1px solid var(--rule); border-radius: 2px; padding: 9px 11px;
  font-size: 14px; color: var(--ink); background: var(--paper); outline: none; width: 100%;
  -webkit-appearance: none;
}
.m-input:focus { border-color: var(--ink); }
.m-textarea {
  border: 1px solid var(--rule); border-radius: 2px; padding: 9px 11px;
  font-size: 13px; color: var(--ink); background: var(--paper); outline: none;
  width: 100%; resize: none; font-family: var(--font-mono);
}
.m-actions { display: flex; gap: 8px; }
.m-btn-validate {
  flex: 2; height: 44px; background: var(--teal); color: #fff; border: none;
  border-radius: 3px; font-size: 14px; font-weight: 600; cursor: pointer;
}
.m-btn-validate:disabled { opacity: .5; }
.m-btn-issue {
  flex: 1; height: 44px; background: transparent; color: var(--red);
  border: 1px solid var(--red); border-radius: 3px; font-size: 13px; font-weight: 600; cursor: pointer;
}
.m-btn-issue:disabled { opacity: .5; }
</style>
