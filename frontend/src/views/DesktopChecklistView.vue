<script setup>
import { ref, computed, reactive, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import TopBar from '../components/TopBar.vue'
import LeftRail from '../components/LeftRail.vue'
import StepRow from '../components/StepRow.vue'
import StepDetailPane from '../components/StepDetailPane.vue'
import AssistantPanel from '../components/AssistantPanel.vue'
import api from '../services/api.js'
import { useToast } from '../composables/useToast.js'

const { success: toastSuccess, error: toastError } = useToast()

const route = useRoute()
const projectId = computed(() => Number(route.params.id))

const project = ref(null)
const steps = ref([])
const validations = reactive({})
const otherProjects = ref([])
const loading = ref(true)
const error = ref(null)

const filter = ref('all')
const searchQuery = ref('')
const activeStepId = ref(null)
const showAssistant = ref(false)
const pdfModalPage  = ref(null)

const filters = [
  { key: 'all',     label: 'Toutes' },
  { key: 'pending', label: 'À faire' },
  { key: 'done',    label: 'Validées' },
  { key: 'issue',   label: 'Problèmes' },
]

function buildValidations(stepsData) {
  for (const key of Object.keys(validations)) delete validations[key]
  for (const s of stepsData) {
    if (s.status !== 'pending') {
      validations[s.id] = {
        status:          s.status,
        technician_name: s.technician_name,
        note:            s.note,
        witness_name:    s.witness_name,
        validated_at:    s.validated_at,
        started_at:      s.validated_at,
      }
    }
  }
}

onMounted(async () => {
  try {
    const [stepsRes, projectsRes] = await Promise.all([
      api.getSteps(projectId.value),
      api.getProjects(),
    ])

    steps.value = stepsRes.data
    buildValidations(stepsRes.data)

    const allProjects = projectsRes.data
    project.value = allProjects.find(p => p.id === projectId.value) || null
    otherProjects.value = allProjects.filter(p => p.id !== projectId.value)

    // Sélectionner la première étape active ou pending
    const firstActive = steps.value.find(s => validations[s.id]?.status === 'active')
    const firstPending = steps.value.find(s => !validations[s.id])
    activeStepId.value = firstActive?.id ?? firstPending?.id ?? steps.value[0]?.id ?? null
  } catch (e) {
    error.value = 'Impossible de charger le projet.'
  } finally {
    loading.value = false
  }
})

const filterCounts = computed(() => ({
  all:     steps.value.length,
  pending: steps.value.filter(s => !validations[s.id] || validations[s.id].status === 'pending').length,
  done:    steps.value.filter(s => validations[s.id]?.status === 'done').length,
  issue:   steps.value.filter(s => validations[s.id]?.status === 'issue').length,
}))

const visibleSteps = computed(() => {
  return steps.value.filter(s => {
    const status = validations[s.id]?.status || 'pending'
    if (filter.value === 'pending' && status !== 'pending' && status !== 'active') return false
    if (filter.value === 'done'    && status !== 'done')   return false
    if (filter.value === 'issue'   && status !== 'issue')  return false
    if (searchQuery.value) {
      const q = searchQuery.value.toLowerCase()
      return s.title.toLowerCase().includes(q) || (s.description || '').toLowerCase().includes(q)
    }
    return true
  })
})

const activeStep       = computed(() => steps.value.find(s => s.id === activeStepId.value) || null)
const activeValidation = computed(() => validations[activeStepId.value] || null)

async function handleValidated(payload) {
  try {
    const { data: updated } = await api.validateStep(payload.step_id, {
      technician_name: payload.technician_name,
      status:          payload.status,
      note:            payload.note,
      witness_name:    payload.witness_name,
    })

    // Mettre à jour le step dans la liste
    const idx = steps.value.findIndex(s => s.id === updated.id)
    if (idx !== -1) steps.value[idx] = updated

    // Reconstruire les validations
    buildValidations(steps.value)

    // Mettre à jour le compteur du projet
    if (project.value) {
      project.value.completed_steps = Object.values(validations).filter(v => v.status === 'done').length
    }

    const label = payload.status === 'done' ? 'Étape validée ✓' : 'Problème signalé'
    toastSuccess(label)
  } catch (e) {
    toastError(e?.response?.data?.detail || 'Erreur lors de la validation.')
  }
}
</script>

<template>
  <div class="checklist-page">
    <TopBar :project="project" :validations="validations" :steps="steps" />

    <div v-if="loading" class="page-loading">Chargement…</div>
    <div v-else-if="error" class="page-error">{{ error }}</div>

    <div v-else class="checklist-body">
      <LeftRail
        :project-id="projectId"
        active="checklist"
        :steps="steps"
        :validations="validations"
        :other-projects="otherProjects"
      />

      <!-- Colonne étapes -->
      <div class="steps-col">
        <!-- Bouton assistant flottant -->
        <button class="assistant-fab" @click="showAssistant = true" title="Assistant IA">
          ✦ Assistant
        </button>
        <div class="steps-search">
          <span class="search-icon">🔍</span>
          <input v-model="searchQuery" placeholder="Rechercher une étape…" class="search-input" />
        </div>

        <div class="filter-row">
          <button
            v-for="f in filters"
            :key="f.key"
            class="filter-btn"
            :class="{ active: filter === f.key }"
            @click="filter = f.key"
          >
            {{ f.label }}
            <span class="filter-count">{{ filterCounts[f.key] }}</span>
          </button>
        </div>

        <div class="steps-list">
          <StepRow
            v-for="step in visibleSteps"
            :key="step.id"
            :step="step"
            :validation="validations[step.id]"
            :active="activeStepId === step.id"
            :project-id="projectId"
            @select="activeStepId = $event"
          />
          <div v-if="visibleSteps.length === 0" class="steps-empty">
            Aucune étape dans ce filtre
          </div>
        </div>
      </div>

      <!-- Volet détail -->
      <StepDetailPane
        :step="activeStep"
        :validation="activeValidation"
        :project-id="projectId"
        @validated="handleValidated"
      />
    </div>

    <!-- Assistant IA -->
    <AssistantPanel
      v-if="showAssistant"
      :project="project"
      :active-step="activeStep"
      :steps="steps"
      @close="showAssistant = false"
      @open-pdf="pdfModalPage = $event"
    />

    <!-- Modal PDF depuis l'assistant -->
    <Teleport to="body">
      <div v-if="pdfModalPage" class="pdf-overlay" @click="pdfModalPage = null">
        <div class="pdf-overlay-header" @click.stop>
          <span class="pdf-overlay-label">Page {{ pdfModalPage }}</span>
          <button class="pdf-overlay-close" @click="pdfModalPage = null">✕</button>
        </div>
        <img
          :src="`/api/projects/${projectId}/pdf/${pdfModalPage}`"
          alt="Page PDF"
          class="pdf-overlay-img"
          @click.stop
        />
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.checklist-page { height: 100vh; display: flex; flex-direction: column; background: var(--paper); }
.checklist-body { flex: 1; display: flex; overflow: hidden; }

.page-loading, .page-error {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  color: var(--inkMute);
}
.page-error { color: var(--red); }

/* Bouton assistant */
.assistant-fab {
  position: fixed;
  bottom: 28px;
  right: 28px;
  z-index: 100;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 18px;
  background: var(--ink);
  color: var(--paper);
  border: none;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 4px 20px rgba(0,0,0,0.3);
  font-family: inherit;
}
.assistant-fab:hover { opacity: 0.88; }

/* Modal PDF depuis assistant */
.pdf-overlay {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.85);
  z-index: 300;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  padding: 20px; gap: 12px; cursor: zoom-out;
}
.pdf-overlay-header {
  display: flex; align-items: center; justify-content: space-between;
  width: 100%; max-width: 700px; cursor: default;
}
.pdf-overlay-label { font-size: 13px; color: rgba(255,255,255,0.7); }
.pdf-overlay-close {
  background: rgba(255,255,255,0.12); color: #fff; border: none;
  border-radius: 4px; width: 32px; height: 32px; font-size: 15px;
  cursor: pointer; margin-left: 12px;
}
.pdf-overlay-img {
  max-height: 82vh; max-width: min(700px, 90vw);
  object-fit: contain; border-radius: 3px;
  box-shadow: 0 20px 60px rgba(0,0,0,0.5); cursor: default;
}

.steps-col {
  width: 380px;
  flex-shrink: 0;
  border-right: 1px solid var(--rule);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
  background: var(--paperAlt);
}

.steps-search {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-bottom: 1px solid var(--ruleSoft);
}
.search-icon { font-size: 13px; color: var(--inkMute); }
.search-input {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  font-size: 13px;
  color: var(--ink);
  font-family: var(--font-sans);
}
.search-input::placeholder { color: var(--inkMute); }

.filter-row {
  display: flex;
  padding: 8px 10px;
  gap: 4px;
  border-bottom: 1px solid var(--ruleSoft);
  overflow-x: auto;
}
.filter-btn {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 4px 10px;
  border-radius: 2px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  background: transparent;
  border: 1px solid transparent;
  color: var(--inkSoft);
  white-space: nowrap;
  transition: all 0.12s;
}
.filter-btn:hover { background: var(--ruleSoft); }
.filter-btn.active { background: var(--ink); color: var(--paper); border-color: var(--ink); }
.filter-count { font-family: var(--font-mono); font-size: 10px; opacity: 0.6; }
.filter-btn.active .filter-count { opacity: 0.8; }

.steps-list { flex: 1; overflow-y: auto; }
.steps-empty { padding: 32px 16px; text-align: center; font-size: 13px; color: var(--inkMute); }
</style>
