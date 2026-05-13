<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import TopBar from '../components/TopBar.vue'
import LeftRail from '../components/LeftRail.vue'
import Avatar from '../components/Avatar.vue'
import CatChip from '../components/CatChip.vue'
import api from '../services/api.js'

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
    const all = projectsRes.data
    project.value = all.find(p => p.id === projectId.value) || null
    otherProjects.value = all.filter(p => p.id !== projectId.value)
  } finally {
    loading.value = false
  }
})

const validations = computed(() => {
  const map = {}
  for (const s of steps.value) {
    if (s.status !== 'pending') {
      map[s.id] = { status: s.status, technician_name: s.technician_name, validated_at: s.validated_at, started_at: s.validated_at }
    }
  }
  return map
})

const done      = computed(() => steps.value.filter(s => s.status === 'done').length)
const issues    = computed(() => steps.value.filter(s => s.status === 'issue').length)
const techNames = computed(() => [...new Set(steps.value.map(s => s.technician_name).filter(Boolean))])

// Timeline : steps non-pending triées par validated_at croissant
const timeline = computed(() =>
  steps.value
    .filter(s => s.status !== 'pending')
    .sort((a, b) => new Date(a.validated_at || 0) - new Date(b.validated_at || 0))
)

function fmtTime(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })
}
</script>

<template>
  <div class="summary-page">
    <TopBar :project="project" :validations="validations" :steps="steps" />

    <div v-if="loading" class="page-loading">Chargement…</div>

    <div v-else class="summary-body">
      <LeftRail
        :project-id="projectId"
        active="summary"
        :steps="steps"
        :validations="validations"
        :other-projects="otherProjects"
      />

      <main class="summary-main">
        <div class="summary-header">
          <div>
            <h1 class="summary-title">Journal d'installation</h1>
            <p class="summary-ref">{{ project?.pdf_filename }}</p>
          </div>
          <button class="btn-back" @click="router.push(`/project/${projectId}`)">← Checklist</button>
        </div>

        <!-- Stats -->
        <div class="stats-strip">
          <div class="stat">
            <span class="stat-num" style="color: var(--teal)">{{ done }}<span class="stat-total">/{{ steps.length }}</span></span>
            <span class="stat-label">Validées</span>
          </div>
          <div class="stat-sep" />
          <div class="stat">
            <span class="stat-num" :style="{ color: issues > 0 ? 'var(--amber)' : 'var(--inkMute)' }">{{ issues }}</span>
            <span class="stat-label">Problèmes</span>
          </div>
          <div class="stat-sep" />
          <div class="stat">
            <span class="stat-num">{{ techNames.length }}</span>
            <span class="stat-label">Techniciens</span>
          </div>
          <div class="stat-avatars">
            <Avatar v-for="name in techNames" :key="name" :name="name" :size="28" />
          </div>
        </div>

        <!-- Timeline -->
        <div class="timeline">
          <div v-for="(s, i) in timeline" :key="s.id" class="timeline-event">
            <div class="tl-left">
              <div class="tl-avatar-wrap">
                <Avatar :name="s.technician_name" :size="36" :spinning="s.status === 'active'" />
                <span v-if="s.status === 'issue'" class="tl-issue-badge">!</span>
              </div>
              <div v-if="i < timeline.length - 1" class="tl-spine" />
            </div>

            <div class="tl-content">
              <div class="tl-meta">
                <span class="tl-time">{{ fmtTime(s.validated_at) }}</span>
                <span class="tl-step">#{{ String(s.step_number).padStart(2, '0') }}</span>
                <CatChip :cat="s.category" />
              </div>

              <div
                class="tl-card"
                :class="{
                  'tl-card-done':   s.status === 'done',
                  'tl-card-issue':  s.status === 'issue',
                  'tl-card-active': s.status === 'active',
                }"
              >
                <div class="tl-card-title">{{ s.title }}</div>
                <div class="tl-card-tech">
                  <span>{{ s.technician_name }}</span>
                  <span v-if="s.witness_name" class="tl-witness"> · Témoin : {{ s.witness_name }}</span>
                </div>
                <p v-if="s.note" class="tl-note">{{ s.note }}</p>
                <div v-if="s.status === 'active'" class="tl-active-label">
                  <span class="pulse-dot animate-trace-dot" />
                  En cours
                </div>
              </div>
            </div>
          </div>

          <div v-if="timeline.length === 0" class="timeline-empty">
            Aucune action enregistrée pour le moment.
          </div>
        </div>
      </main>
    </div>
  </div>
</template>

<style scoped>
.summary-page { height: 100vh; display: flex; flex-direction: column; background: var(--paper); }
.summary-body { flex: 1; display: flex; overflow: hidden; }
.page-loading { flex: 1; display: flex; align-items: center; justify-content: center; font-size: 13px; color: var(--inkMute); }

.summary-main { flex: 1; overflow-y: auto; padding: 28px 32px; display: flex; flex-direction: column; gap: 24px; }

.summary-header { display: flex; align-items: flex-start; justify-content: space-between; }
.summary-title { font-size: 24px; font-weight: 600; letter-spacing: -0.02em; color: var(--ink); }
.summary-ref { font-family: var(--font-mono); font-size: 11px; color: var(--inkSoft); margin-top: 4px; }
.btn-back {
  padding: 8px 14px;
  border: 1px solid var(--rule);
  border-radius: 3px;
  background: transparent;
  font-size: 12.5px;
  color: var(--inkSoft);
  cursor: pointer;
}
.btn-back:hover { background: var(--ruleSoft); }

.stats-strip {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 16px 20px;
  background: var(--paperAlt);
  border: 1px solid var(--rule);
  border-radius: 3px;
}
.stat { display: flex; flex-direction: column; gap: 3px; }
.stat-num { font-family: var(--font-mono); font-size: 24px; font-weight: 600; color: var(--ink); line-height: 1; }
.stat-total { font-size: 14px; color: var(--inkMute); }
.stat-label { font-family: var(--font-mono); font-size: 9px; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; color: var(--inkMute); }
.stat-sep { width: 1px; height: 36px; background: var(--rule); }
.stat-avatars { display: flex; margin-left: auto; }
.stat-avatars > * + * { margin-left: -6px; }

.timeline { display: flex; flex-direction: column; }
.timeline-empty { padding: 32px; text-align: center; font-size: 13px; color: var(--inkMute); }
.timeline-event { display: flex; gap: 16px; }

.tl-left { display: flex; flex-direction: column; align-items: center; flex-shrink: 0; width: 36px; }
.tl-avatar-wrap { position: relative; }
.tl-issue-badge {
  position: absolute;
  bottom: -2px; right: -2px;
  width: 14px; height: 14px;
  border-radius: 50%;
  background: var(--amber);
  color: #fff;
  font-size: 9px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}
.tl-spine { flex: 1; width: 1px; background: var(--rule); margin: 6px 0; min-height: 20px; }

.tl-content { flex: 1; padding-bottom: 20px; display: flex; flex-direction: column; gap: 6px; max-width: 640px; }
.tl-meta { display: flex; align-items: center; gap: 8px; }
.tl-time { font-family: var(--font-mono); font-size: 11px; color: var(--inkMute); }
.tl-step { font-family: var(--font-mono); font-size: 11px; color: var(--inkMute); }

.tl-card {
  background: var(--paperAlt);
  border: 1px solid var(--ruleSoft);
  border-radius: 3px;
  padding: 11px 13px;
  display: flex;
  flex-direction: column;
  gap: 5px;
}
.tl-card-issue  { background: var(--amberBg); border-color: var(--amber); }
.tl-card-active { background: #FFF8EB; border: 1px dashed var(--amber); }
.tl-card-title { font-size: 13.5px; font-weight: 550; color: var(--ink); }
.tl-card-tech { font-size: 12px; color: var(--inkSoft); }
.tl-witness { font-family: var(--font-mono); font-size: 10px; }
.tl-note {
  font-size: 12px;
  font-style: italic;
  color: var(--inkSoft);
  background: rgba(0,0,0,0.03);
  border-left: 2px solid var(--rule);
  padding: 4px 8px;
  border-radius: 0 2px 2px 0;
}
.tl-active-label { display: flex; align-items: center; gap: 6px; font-family: var(--font-mono); font-size: 10px; font-weight: 600; color: var(--amber); }
.pulse-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--amber); }
</style>
