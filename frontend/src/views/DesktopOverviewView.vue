<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import TopBar from '../components/TopBar.vue'
import LeftRail from '../components/LeftRail.vue'
import ProgressTrack from '../components/ProgressTrack.vue'
import Avatar from '../components/Avatar.vue'
import CatChip from '../components/CatChip.vue'
import api from '../services/api.js'
import { useToast } from '../composables/useToast.js'

const { success: toastSuccess, error: toastError } = useToast()

async function deleteProject() {
  if (!confirm(`Supprimer le projet "${project.value?.name}" et toutes ses étapes ?`)) return
  try {
    await api.deleteProject(projectId.value)
    toastSuccess('Projet supprimé.')
    router.push('/')
  } catch {
    toastError('Erreur lors de la suppression.')
  }
}

const route  = useRoute()
const router = useRouter()
const projectId = computed(() => Number(route.params.id))

const project       = ref(null)
const steps         = ref([])
const otherProjects = ref([])
const loading       = ref(true)

onMounted(async () => {
  try {
    const [stepsRes, projectsRes] = await Promise.all([
      api.getSteps(projectId.value),
      api.getProjects(),
    ])
    steps.value = stepsRes.data
    const allProjects = projectsRes.data
    project.value = allProjects.find(p => p.id === projectId.value) || null
    otherProjects.value = allProjects.filter(p => p.id !== projectId.value)
  } finally {
    loading.value = false
  }
})

// Construit l'objet validations attendu par TopBar et ProgressTrack
const validations = computed(() => {
  const map = {}
  for (const s of steps.value) {
    if (s.status !== 'pending') {
      map[s.id] = {
        status:          s.status,
        technician_name: s.technician_name,
        note:            s.note,
        validated_at:    s.validated_at,
        started_at:      s.validated_at,
      }
    }
  }
  return map
})

const done   = computed(() => steps.value.filter(s => s.status === 'done').length)
const issues = computed(() => steps.value.filter(s => s.status === 'issue').length)

const activeStep = computed(() => steps.value.find(s => s.status === 'active') || null)

const techStats = computed(() => {
  const map = {}
  steps.value.forEach(s => {
    if (s.technician_name) map[s.technician_name] = (map[s.technician_name] || 0) + 1
  })
  return Object.entries(map).map(([name, count]) => ({ name, count })).sort((a, b) => b.count - a.count)
})

const activityFeed = computed(() => {
  return steps.value
    .filter(s => s.status !== 'pending' && s.validated_at)
    .sort((a, b) => new Date(b.validated_at) - new Date(a.validated_at))
    .slice(0, 6)
})

function fmtTime(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })
}
</script>

<template>
  <div class="overview-page">
    <TopBar :project="project" :validations="validations" :steps="steps" />

    <div v-if="loading" class="page-loading">Chargement…</div>

    <div v-else class="overview-body">
      <LeftRail
        :project-id="projectId"
        active="overview"
        :steps="steps"
        :validations="validations"
        :other-projects="otherProjects"
      />

      <main class="overview-main">
        <div class="ov-header">
          <div>
            <p class="ov-session">Aperçu · {{ new Date().toLocaleDateString('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' }) }}</p>
            <h1 class="ov-title">{{ project?.name }}</h1>
            <p class="ov-ref">{{ project?.pdf_filename }}</p>
          </div>
          <div style="display:flex;gap:8px;flex-wrap:wrap;">
            <button class="btn-resume" @click="router.push(`/project/${projectId}`)">
              Reprendre l'installation →
            </button>
            <button class="btn-resume" style="background:transparent;color:var(--ink);border:1px solid var(--rule)"
              @click="router.push(`/project/${projectId}/wiki-admin`)">
              📚 Machine Wiki
            </button>
            <button class="btn-delete" @click="deleteProject">Supprimer</button>
          </div>
        </div>

        <!-- KPIs -->
        <div class="kpi-grid">
          <div class="kpi" style="border-left-color: var(--teal)">
            <span class="kpi-num">{{ done }}<span class="kpi-total">/{{ steps.length }}</span></span>
            <span class="kpi-label">Validées</span>
            <span class="kpi-pct">{{ steps.length ? Math.round(done / steps.length * 100) : 0 }}%</span>
          </div>
          <div class="kpi" :style="{ borderLeftColor: issues > 0 ? 'var(--amber)' : 'var(--teal)' }">
            <span class="kpi-num" :style="{ color: issues > 0 ? 'var(--amber)' : 'var(--teal)' }">
              {{ issues > 0 ? issues : '—' }}
            </span>
            <span class="kpi-label">Problèmes</span>
            <span v-if="issues === 0" class="kpi-pct" style="color: var(--teal)">aucun</span>
          </div>
          <div class="kpi" style="border-left-color: var(--blue)">
            <span class="kpi-num">{{ techStats.length }}</span>
            <span class="kpi-label">Techniciens</span>
          </div>
          <div class="kpi" style="border-left-color: var(--amber)">
            <span class="kpi-num" style="font-size: 16px;">
              {{ activeStep ? '#' + String(activeStep.step_number).padStart(2, '0') : '—' }}
            </span>
            <span class="kpi-label">Étape active</span>
            <span v-if="activeStep" class="kpi-step-title">{{ activeStep.title }}</span>
          </div>
        </div>

        <div class="ov-grid">
          <div class="ov-card">
            <span class="ov-card-title">Progression par catégorie</span>
            <ProgressTrack :steps="steps" :validations="validations" />
          </div>

          <div class="ov-card">
            <span class="ov-card-title">Équipe</span>
            <div class="team-list">
              <div v-for="t in techStats" :key="t.name" class="team-row">
                <Avatar :name="t.name" :size="30" />
                <span class="team-name">{{ t.name }}</span>
                <span class="team-count">{{ t.count }} action{{ t.count > 1 ? 's' : '' }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Activité récente -->
        <div class="activity-section">
          <span class="ov-card-title">Activité récente</span>
          <div class="activity-list">
            <div v-for="s in activityFeed" :key="s.id" class="activity-row">
              <span class="activity-time">{{ fmtTime(s.validated_at) }}</span>
              <Avatar :name="s.technician_name" :size="22" />
              <span class="activity-tech">{{ s.technician_name }}</span>
              <CatChip :cat="s.category" />
              <span class="activity-step">#{{ String(s.step_number).padStart(2, '0') }}</span>
              <span class="activity-title">{{ s.title }}</span>
              <span
                class="activity-badge"
                :style="{
                  color:      s.status === 'done'  ? 'var(--teal)'  : s.status === 'issue' ? 'var(--amber)' : 'var(--inkMute)',
                  background: s.status === 'done'  ? 'var(--tealBg)': s.status === 'issue' ? 'var(--amberBg)': 'var(--ruleSoft)',
                }"
              >
                {{ s.status === 'done' ? '✓ Validé' : s.status === 'issue' ? '⚠ Problème' : '⟳ En cours' }}
              </span>
            </div>
          </div>
        </div>
      </main>
    </div>
  </div>
</template>

<style scoped>
.overview-page { height: 100vh; display: flex; flex-direction: column; background: var(--paper); }
.overview-body { flex: 1; display: flex; overflow: hidden; }
.page-loading { flex: 1; display: flex; align-items: center; justify-content: center; font-size: 13px; color: var(--inkMute); }

.overview-main { flex: 1; overflow-y: auto; padding: 28px 32px; display: flex; flex-direction: column; gap: 24px; }

.ov-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; }
.ov-session { font-family: var(--font-mono); font-size: 11px; color: var(--inkMute); margin-bottom: 4px; }
.ov-title { font-size: 26px; font-weight: 600; letter-spacing: -0.02em; color: var(--ink); margin-bottom: 4px; }
.ov-ref { font-family: var(--font-mono); font-size: 11px; color: var(--inkSoft); }
.btn-resume {
  padding: 10px 18px;
  background: var(--ink);
  color: var(--paper);
  border: none;
  border-radius: 3px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  flex-shrink: 0;
  margin-top: 4px;
}
.btn-resume:hover { opacity: 0.88; }
.btn-delete {
  padding: 10px 14px;
  background: transparent;
  color: var(--red);
  border: 1px solid var(--red);
  border-radius: 3px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}
.btn-delete:hover { background: var(--redBg); }

.kpi-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.kpi {
  background: var(--paperAlt);
  border: 1px solid var(--rule);
  border-left-width: 3px;
  border-radius: 3px;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.kpi-num { font-family: var(--font-mono); font-size: 26px; font-weight: 600; letter-spacing: -0.02em; color: var(--ink); line-height: 1; }
.kpi-total { font-size: 14px; color: var(--inkMute); }
.kpi-label { font-family: var(--font-mono); font-size: 9px; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; color: var(--inkMute); }
.kpi-pct { font-family: var(--font-mono); font-size: 11px; color: var(--teal); }
.kpi-step-title { font-size: 11px; color: var(--inkSoft); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.ov-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.ov-card {
  background: var(--paperAlt);
  border: 1px solid var(--rule);
  border-radius: 3px;
  padding: 16px 18px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.ov-card-title { font-family: var(--font-mono); font-size: 9px; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; color: var(--inkMute); }

.team-list { display: flex; flex-direction: column; gap: 10px; }
.team-row { display: flex; align-items: center; gap: 10px; }
.team-name { flex: 1; font-size: 13px; font-weight: 550; color: var(--ink); }
.team-count { font-family: var(--font-mono); font-size: 11px; color: var(--inkMute); }

.activity-section { display: flex; flex-direction: column; gap: 10px; }
.activity-list { display: flex; flex-direction: column; gap: 1px; }
.activity-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  background: var(--paperAlt);
  border: 1px solid var(--ruleSoft);
  border-radius: 2px;
}
.activity-time { font-family: var(--font-mono); font-size: 11px; color: var(--inkMute); width: 38px; flex-shrink: 0; }
.activity-tech { font-size: 12px; font-weight: 550; color: var(--inkSoft); flex-shrink: 0; }
.activity-step { font-family: var(--font-mono); font-size: 11px; color: var(--inkMute); flex-shrink: 0; }
.activity-title { font-size: 12.5px; color: var(--ink); flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.activity-badge {
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 600;
  padding: 2px 7px;
  border-radius: 2px;
  flex-shrink: 0;
}
</style>
