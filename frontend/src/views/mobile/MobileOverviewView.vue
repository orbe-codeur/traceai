<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Avatar from '../../components/Avatar.vue'
import CatChip from '../../components/CatChip.vue'
import ProgressTrack from '../../components/ProgressTrack.vue'
import api from '../../services/api.js'
import { useToast } from '../../composables/useToast.js'

const route   = useRoute()
const router  = useRouter()
const { success: toastSuccess, error: toastError } = useToast()

const projectId = computed(() => Number(route.params.id))
const project   = ref(null)
const steps     = ref([])
const loading   = ref(true)
const showDeleteConfirm = ref(false)

onMounted(async () => {
  try {
    const [stepsRes, projRes] = await Promise.all([api.getSteps(projectId.value), api.getProjects()])
    steps.value   = stepsRes.data
    project.value = projRes.data.find(p => p.id === projectId.value) || null
  } finally { loading.value = false }
})

const validations = computed(() => {
  const map = {}
  for (const s of steps.value) {
    if (s.status !== 'pending') {
      map[s.id] = { status: s.status, technician_name: s.technician_name, note: s.note, validated_at: s.validated_at }
    }
  }
  return map
})

const done       = computed(() => steps.value.filter(s => s.status === 'done').length)
const issues     = computed(() => steps.value.filter(s => s.status === 'issue').length)
const activeStep = computed(() => steps.value.find(s => s.status === 'active') || null)

const techStats = computed(() => {
  const map = {}
  steps.value.forEach(s => {
    if (s.technician_name) map[s.technician_name] = (map[s.technician_name] || 0) + 1
  })
  return Object.entries(map).map(([name, count]) => ({ name, count })).sort((a, b) => b.count - a.count)
})

const activityFeed = computed(() =>
  steps.value
    .filter(s => s.status !== 'pending' && s.validated_at)
    .sort((a, b) => new Date(b.validated_at) - new Date(a.validated_at))
    .slice(0, 8)
)

const pct = computed(() => steps.value.length ? Math.round(done.value / steps.value.length * 100) : 0)

function fmtTime(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })
}

async function deleteProject() {
  try {
    await api.deleteProject(projectId.value)
    toastSuccess('Projet supprimé.')
    router.push('/')
  } catch {
    toastError('Erreur lors de la suppression.')
  }
}
</script>

<template>
  <div class="mobile-page">
    <!-- TopBar -->
    <header class="m-topbar">
      <button class="m-back" @click="router.push(`/project/${projectId}`)">←</button>
      <span class="m-title">Aperçu</span>
      <button class="m-delete-btn" @click="showDeleteConfirm = true">Supprimer</button>
    </header>

    <div v-if="loading" class="m-loading">Chargement…</div>

    <template v-else>
      <!-- Nom du projet -->
      <div class="m-project-header">
        <p class="m-project-date">{{ new Date().toLocaleDateString('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' }) }}</p>
        <h1 class="m-project-name">{{ project?.name }}</h1>
        <p class="m-project-file">{{ project?.pdf_filename }}</p>
      </div>

      <!-- Barre de progression globale -->
      <div class="m-progress-bar-wrap">
        <div class="m-progress-track">
          <div
            class="m-progress-fill"
            :style="{
              width: pct + '%',
              background: pct >= 80 ? 'var(--teal)' : pct >= 30 ? 'var(--amber)' : 'var(--red)'
            }"
          />
        </div>
        <span class="m-progress-label">{{ done }} / {{ steps.length }} étapes — {{ pct }}%</span>
      </div>

      <!-- KPIs -->
      <div class="m-stats">
        <div class="m-stat">
          <span class="m-stat-num" style="color:var(--teal)">
            {{ done }}<span class="m-stat-total">/{{ steps.length }}</span>
          </span>
          <span class="m-stat-label">Validées</span>
        </div>
        <div class="m-stat-sep" />
        <div class="m-stat">
          <span class="m-stat-num" :style="{ color: issues > 0 ? 'var(--amber)' : 'var(--inkMute)' }">
            {{ issues }}
          </span>
          <span class="m-stat-label">Problèmes</span>
        </div>
        <div class="m-stat-sep" />
        <div class="m-stat">
          <span class="m-stat-num">{{ techStats.length }}</span>
          <span class="m-stat-label">Techniciens</span>
        </div>
        <div class="m-stat-sep" />
        <div class="m-stat">
          <span class="m-stat-num" style="font-size:15px">
            {{ activeStep ? '#' + String(activeStep.step_number).padStart(2,'0') : '—' }}
          </span>
          <span class="m-stat-label">En cours</span>
        </div>
      </div>

      <!-- Progression par catégorie -->
      <div class="m-section">
        <span class="m-section-title">Par catégorie</span>
        <ProgressTrack :steps="steps" :validations="validations" />
      </div>

      <!-- Équipe -->
      <div class="m-section" v-if="techStats.length">
        <span class="m-section-title">Équipe</span>
        <div class="m-team-list">
          <div v-for="t in techStats" :key="t.name" class="m-team-row">
            <Avatar :name="t.name" :size="32" />
            <span class="m-team-name">{{ t.name }}</span>
            <span class="m-team-count">{{ t.count }} action{{ t.count > 1 ? 's' : '' }}</span>
          </div>
        </div>
      </div>

      <!-- Activité récente -->
      <div class="m-section" v-if="activityFeed.length">
        <span class="m-section-title">Activité récente</span>
        <div class="m-activity-list">
          <div v-for="s in activityFeed" :key="s.id" class="m-activity-row">
            <div class="m-act-left">
              <Avatar :name="s.technician_name" :size="28" />
            </div>
            <div class="m-act-body">
              <div class="m-act-meta">
                <span class="m-act-time">{{ fmtTime(s.validated_at) }}</span>
                <CatChip :cat="s.category" />
                <span class="m-act-step">#{{ String(s.step_number).padStart(2,'0') }}</span>
              </div>
              <span class="m-act-title">{{ s.title }}</span>
              <span class="m-act-tech">{{ s.technician_name }}</span>
            </div>
            <span
              class="m-act-badge"
              :class="s.status"
            >
              {{ s.status === 'done' ? '✓' : s.status === 'issue' ? '!' : '⟳' }}
            </span>
          </div>
        </div>
      </div>

      <div v-else class="m-empty-activity">Aucune action enregistrée.</div>

      <!-- Bouton reprendre -->
      <div class="m-footer">
        <button class="m-btn-resume" @click="router.push(`/project/${projectId}`)">
          Reprendre l'installation →
        </button>
      </div>
    </template>

    <!-- Modal confirmation suppression -->
    <div v-if="showDeleteConfirm" class="m-overlay" @click.self="showDeleteConfirm = false">
      <div class="m-modal">
        <p class="m-modal-title">Supprimer ce projet ?</p>
        <p class="m-modal-body">Cette action est irréversible. Toutes les étapes et le PDF seront supprimés.</p>
        <div class="m-modal-actions">
          <button class="m-modal-cancel" @click="showDeleteConfirm = false">Annuler</button>
          <button class="m-modal-confirm" @click="deleteProject">Supprimer</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.mobile-page { min-height: 100vh; background: var(--paper); display: flex; flex-direction: column; padding-bottom: 24px; }

.m-topbar {
  height: 52px; background: var(--ink); display: flex; align-items: center;
  padding: 0 14px; gap: 12px; position: sticky; top: 0; z-index: 10;
}
.m-back { background: none; border: none; color: #fff; font-size: 20px; cursor: pointer; padding: 0; }
.m-title { font-size: 15px; font-weight: 600; color: #fff; flex: 1; }
.m-delete-btn {
  background: none; border: 1px solid rgba(255,255,255,0.3); color: rgba(255,255,255,0.8);
  font-size: 12px; padding: 4px 10px; border-radius: 3px; cursor: pointer;
}
.m-loading { flex: 1; display: flex; align-items: center; justify-content: center; font-size: 13px; color: var(--inkMute); }

.m-project-header { padding: 16px 16px 10px; }
.m-project-date { font-family: var(--font-mono); font-size: 10px; color: var(--inkMute); margin-bottom: 4px; }
.m-project-name { font-size: 18px; font-weight: 600; color: var(--ink); letter-spacing: -0.01em; margin-bottom: 3px; }
.m-project-file { font-family: var(--font-mono); font-size: 10px; color: var(--inkSoft); }

.m-progress-bar-wrap { padding: 0 16px 12px; display: flex; flex-direction: column; gap: 6px; }
.m-progress-track { height: 5px; background: var(--rule); border-radius: 99px; overflow: hidden; }
.m-progress-fill { height: 100%; border-radius: 99px; transition: width .4s ease; }
.m-progress-label { font-family: var(--font-mono); font-size: 10px; color: var(--inkMute); }

.m-stats {
  display: flex; align-items: center; gap: 12px;
  padding: 12px 16px; background: var(--paperAlt); border-top: 1px solid var(--rule); border-bottom: 1px solid var(--rule);
}
.m-stat { display: flex; flex-direction: column; gap: 2px; flex: 1; }
.m-stat-num { font-family: var(--font-mono); font-size: 20px; font-weight: 700; color: var(--ink); line-height: 1; }
.m-stat-total { font-size: 12px; color: var(--inkMute); }
.m-stat-label { font-family: var(--font-mono); font-size: 9px; font-weight: 600; text-transform: uppercase; letter-spacing: .08em; color: var(--inkMute); }
.m-stat-sep { width: 1px; height: 30px; background: var(--rule); flex-shrink: 0; }

.m-section { padding: 16px 16px 0; display: flex; flex-direction: column; gap: 10px; }
.m-section-title { font-family: var(--font-mono); font-size: 9px; font-weight: 600; letter-spacing: .08em; text-transform: uppercase; color: var(--inkMute); }

.m-team-list { display: flex; flex-direction: column; gap: 8px; }
.m-team-row { display: flex; align-items: center; gap: 10px; padding: 8px 12px; background: var(--paperAlt); border: 1px solid var(--ruleSoft); border-radius: 3px; }
.m-team-name { flex: 1; font-size: 13px; font-weight: 550; color: var(--ink); }
.m-team-count { font-family: var(--font-mono); font-size: 11px; color: var(--inkMute); }

.m-activity-list { display: flex; flex-direction: column; gap: 1px; }
.m-activity-row {
  display: flex; align-items: flex-start; gap: 10px;
  padding: 10px 12px; background: var(--paperAlt); border: 1px solid var(--ruleSoft); border-radius: 2px;
}
.m-act-left { flex-shrink: 0; padding-top: 2px; }
.m-act-body { flex: 1; display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.m-act-meta { display: flex; align-items: center; gap: 6px; margin-bottom: 2px; }
.m-act-time { font-family: var(--font-mono); font-size: 10px; color: var(--inkMute); }
.m-act-step { font-family: var(--font-mono); font-size: 10px; color: var(--inkMute); }
.m-act-title { font-size: 12.5px; font-weight: 550; color: var(--ink); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.m-act-tech { font-size: 11px; color: var(--inkSoft); }
.m-act-badge {
  flex-shrink: 0; width: 22px; height: 22px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: 700; margin-top: 2px;
}
.m-act-badge.done { background: var(--tealBg); color: var(--teal); }
.m-act-badge.issue { background: var(--amberBg); color: var(--amber); }
.m-act-badge.active { background: #FFF8EB; color: var(--amber); border: 1px dashed var(--amber); }

.m-empty-activity { text-align: center; padding: 32px 16px; font-size: 13px; color: var(--inkMute); }

.m-footer { padding: 20px 16px 0; }
.m-btn-resume {
  width: 100%; padding: 14px;
  background: var(--ink); color: var(--paper);
  border: none; border-radius: 3px;
  font-size: 14px; font-weight: 600; cursor: pointer;
}
.m-btn-resume:active { opacity: 0.88; }

/* Modal suppression */
.m-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,.5);
  display: flex; align-items: flex-end; z-index: 100;
}
.m-modal {
  width: 100%; background: var(--paper); border-radius: 12px 12px 0 0;
  padding: 24px 20px 40px; display: flex; flex-direction: column; gap: 12px;
}
.m-modal-title { font-size: 17px; font-weight: 700; color: var(--ink); }
.m-modal-body { font-size: 13px; color: var(--inkSoft); line-height: 1.5; }
.m-modal-actions { display: flex; gap: 10px; margin-top: 8px; }
.m-modal-cancel {
  flex: 1; padding: 13px; border: 1px solid var(--rule); background: transparent;
  border-radius: 3px; font-size: 14px; font-weight: 600; color: var(--inkSoft); cursor: pointer;
}
.m-modal-confirm {
  flex: 1; padding: 13px; border: none; background: var(--red);
  border-radius: 3px; font-size: 14px; font-weight: 600; color: #fff; cursor: pointer;
}
</style>
