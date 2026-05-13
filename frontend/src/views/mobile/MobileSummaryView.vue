<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Avatar from '../../components/Avatar.vue'
import CatChip from '../../components/CatChip.vue'
import api from '../../services/api.js'

const route   = useRoute()
const router  = useRouter()
const projectId = computed(() => Number(route.params.id))

const project = ref(null)
const steps   = ref([])
const loading = ref(true)

onMounted(async () => {
  try {
    const [stepsRes, projRes] = await Promise.all([api.getSteps(projectId.value), api.getProjects()])
    steps.value   = stepsRes.data
    project.value = projRes.data.find(p => p.id === projectId.value) || null
  } finally { loading.value = false }
})

const done      = computed(() => steps.value.filter(s => s.status === 'done').length)
const issues    = computed(() => steps.value.filter(s => s.status === 'issue').length)
const techNames = computed(() => [...new Set(steps.value.map(s => s.technician_name).filter(Boolean))])
const timeline  = computed(() =>
  steps.value.filter(s => s.status !== 'pending')
    .sort((a,b) => new Date(a.validated_at||0) - new Date(b.validated_at||0))
)

function fmtTime(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })
}
</script>

<template>
  <div class="mobile-page">
    <header class="m-topbar">
      <button class="m-back" @click="router.push(`/project/${projectId}`)">←</button>
      <span class="m-title">Journal</span>
    </header>

    <div v-if="loading" class="m-loading">Chargement…</div>

    <template v-else>
      <!-- Stats -->
      <div class="m-stats">
        <div class="m-stat">
          <span class="m-stat-num" style="color:var(--teal)">{{ done }}<span class="m-stat-total">/{{ steps.length }}</span></span>
          <span class="m-stat-label">Validées</span>
        </div>
        <div class="m-stat-sep" />
        <div class="m-stat">
          <span class="m-stat-num" :style="{ color: issues > 0 ? 'var(--amber)' : 'var(--inkMute)' }">{{ issues }}</span>
          <span class="m-stat-label">Problèmes</span>
        </div>
        <div class="m-stat-sep" />
        <div class="m-stat">
          <span class="m-stat-num">{{ techNames.length }}</span>
          <span class="m-stat-label">Techniciens</span>
        </div>
      </div>

      <!-- Avatars équipe -->
      <div class="m-team">
        <Avatar v-for="n in techNames" :key="n" :name="n" :size="32" />
      </div>

      <!-- Timeline -->
      <div class="m-timeline">
        <div v-for="(s, i) in timeline" :key="s.id" class="m-event">
          <div class="m-ev-left">
            <div class="m-av-wrap">
              <Avatar :name="s.technician_name" :size="32" :spinning="s.status === 'active'" />
              <span v-if="s.status === 'issue'" class="m-issue-dot">!</span>
            </div>
            <div v-if="i < timeline.length-1" class="m-spine" />
          </div>
          <div class="m-ev-content">
            <div class="m-ev-meta">
              <span class="m-ev-time">{{ fmtTime(s.validated_at) }}</span>
              <span class="m-ev-step">#{{ String(s.step_number).padStart(2,'0') }}</span>
              <CatChip :cat="s.category" />
            </div>
            <div class="m-ev-card" :class="{ issue: s.status==='issue', active: s.status==='active' }">
              <span class="m-ev-title">{{ s.title }}</span>
              <span class="m-ev-tech">{{ s.technician_name }}<span v-if="s.witness_name"> · Témoin : {{ s.witness_name }}</span></span>
              <p v-if="s.note" class="m-ev-note">{{ s.note }}</p>
            </div>
          </div>
        </div>
        <div v-if="!timeline.length" class="m-empty">Aucune action enregistrée.</div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.mobile-page { min-height: 100vh; background: var(--paper); display: flex; flex-direction: column; }
.m-topbar {
  height: 52px; background: var(--ink); display: flex; align-items: center;
  padding: 0 14px; gap: 12px; position: sticky; top: 0; z-index: 10;
}
.m-back { background: none; border: none; color: #fff; font-size: 20px; cursor: pointer; padding: 0; }
.m-title { font-size: 15px; font-weight: 600; color: #fff; }
.m-loading { flex: 1; display: flex; align-items: center; justify-content: center; font-size: 13px; color: var(--inkMute); }

.m-stats {
  display: flex; align-items: center; gap: 16px;
  padding: 14px 16px; background: var(--paperAlt); border-bottom: 1px solid var(--rule);
}
.m-stat { display: flex; flex-direction: column; gap: 2px; }
.m-stat-num { font-family: var(--font-mono); font-size: 22px; font-weight: 700; color: var(--ink); line-height: 1; }
.m-stat-total { font-size: 13px; color: var(--inkMute); }
.m-stat-label { font-family: var(--font-mono); font-size: 9px; font-weight: 600; text-transform: uppercase; letter-spacing: .08em; color: var(--inkMute); }
.m-stat-sep { width: 1px; height: 30px; background: var(--rule); }

.m-team { display: flex; padding: 10px 16px; gap: 0; border-bottom: 1px solid var(--ruleSoft); }
.m-team > * + * { margin-left: -8px; }

.m-timeline { flex: 1; padding: 12px 16px; display: flex; flex-direction: column; }
.m-empty { text-align: center; padding: 32px; font-size: 13px; color: var(--inkMute); }

.m-event { display: flex; gap: 12px; }
.m-ev-left { display: flex; flex-direction: column; align-items: center; flex-shrink: 0; width: 32px; }
.m-av-wrap { position: relative; }
.m-issue-dot {
  position: absolute; bottom: -2px; right: -2px; width: 13px; height: 13px;
  border-radius: 50%; background: var(--amber); color: #fff;
  font-size: 8px; font-weight: 700; display: flex; align-items: center; justify-content: center;
}
.m-spine { flex: 1; width: 1px; background: var(--rule); margin: 5px 0; min-height: 16px; }

.m-ev-content { flex: 1; padding-bottom: 16px; display: flex; flex-direction: column; gap: 5px; }
.m-ev-meta { display: flex; align-items: center; gap: 6px; }
.m-ev-time { font-family: var(--font-mono); font-size: 10px; color: var(--inkMute); }
.m-ev-step { font-family: var(--font-mono); font-size: 10px; color: var(--inkMute); }

.m-ev-card {
  background: var(--paperAlt); border: 1px solid var(--ruleSoft); border-radius: 3px;
  padding: 10px 12px; display: flex; flex-direction: column; gap: 4px;
}
.m-ev-card.issue { background: var(--amberBg); border-color: var(--amber); }
.m-ev-card.active { border: 1px dashed var(--amber); background: #FFF8EB; }
.m-ev-title { font-size: 13px; font-weight: 550; color: var(--ink); }
.m-ev-tech { font-size: 11px; color: var(--inkSoft); }
.m-ev-note { font-size: 11.5px; font-style: italic; color: var(--inkSoft); padding: 4px 8px; background: rgba(0,0,0,.03); border-left: 2px solid var(--rule); border-radius: 0 2px 2px 0; }
</style>
