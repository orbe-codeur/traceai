<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../../services/api.js'

const router   = useRouter()
const projects = ref([])
const loading  = ref(true)
const search   = ref('')

onMounted(async () => {
  try { const { data } = await api.getProjects(); projects.value = data }
  finally { loading.value = false }
})

const active    = p => p.completed_steps < p.total_steps && p.completed_steps > 0
const completed = p => p.completed_steps >= p.total_steps && p.total_steps > 0
const pct       = p => p.total_steps ? Math.round(p.completed_steps / p.total_steps * 100) : 0

const filteredProjects = computed(() => {
  const q = search.value.trim().toLowerCase()
  if (!q) return projects.value
  return projects.value.filter(p =>
    p.name.toLowerCase().includes(q) || (p.pdf_filename || '').toLowerCase().includes(q)
  )
})
</script>

<template>
  <div class="mobile-page">
    <header class="m-topbar">
      <div class="m-wordmark">
        <span class="m-wt">T</span>
        <span>Trace<span style="color:var(--amber)">AI</span></span>
      </div>
    </header>

    <!-- Barre de recherche -->
    <div class="m-search-bar">
      <input
        v-model="search"
        type="text"
        class="m-search-input"
        placeholder="Rechercher un projet…"
      />
      <button v-if="search" class="m-search-clear" @click="search = ''">✕</button>
    </div>

    <div class="m-body">
      <div v-if="loading" class="m-loading">Chargement…</div>

      <template v-else>
        <!-- Projets en cours -->
        <template v-if="filteredProjects.filter(active).length">
          <p class="m-section-label">En cours</p>
          <div
            v-for="p in filteredProjects.filter(active)"
            :key="p.id"
            class="m-project-card active"
            @click="router.push(`/project/${p.id}`)"
          >
            <div class="m-proj-top">
              <span class="m-proj-name">{{ p.name }}</span>
              <span class="m-proj-ratio" style="color:var(--amber)">{{ p.completed_steps }}/{{ p.total_steps }}</span>
            </div>
            <div class="m-prog-bar">
              <div class="m-prog-fill" :style="{ width: pct(p) + '%', background: 'var(--amber)' }" />
            </div>
            <span class="m-proj-file">{{ p.pdf_filename }}</span>
          </div>
        </template>

        <!-- Bouton nouveau -->
        <button class="m-btn-new" @click="router.push('/upload')">
          + Importer un manuel PDF
        </button>

        <!-- Historique -->
        <template v-if="filteredProjects.filter(p => !active(p)).length">
          <p class="m-section-label">Historique</p>
          <div
            v-for="p in filteredProjects.filter(p => !active(p))"
            :key="p.id"
            class="m-project-card"
            @click="router.push(`/project/${p.id}`)"
          >
            <div class="m-proj-top">
              <span class="m-proj-name">{{ p.name }}</span>
              <span class="m-proj-ratio" :style="{ color: completed(p) ? 'var(--teal)' : 'var(--inkMute)' }">
                {{ p.completed_steps }}/{{ p.total_steps }}
              </span>
            </div>
            <span class="m-proj-file">{{ p.pdf_filename }}</span>
          </div>
        </template>

        <div v-if="!projects.length" class="m-empty">
          Aucun projet. Importez votre premier manuel.
        </div>
        <div v-else-if="!filteredProjects.length" class="m-empty">
          Aucun résultat pour "{{ search }}".
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.mobile-page { min-height: 100vh; background: var(--paper); display: flex; flex-direction: column; }

.m-search-bar {
  position: relative;
  padding: 10px 16px;
  background: var(--paperAlt);
  border-bottom: 1px solid var(--rule);
}
.m-search-input {
  width: 100%;
  border: 1px solid var(--rule);
  border-radius: 20px;
  padding: 9px 32px 9px 14px;
  font-size: 14px;
  color: var(--ink);
  background: var(--paper);
  outline: none;
}
.m-search-input:focus { border-color: var(--ink); }
.m-search-clear {
  position: absolute; right: 24px; top: 50%; transform: translateY(-50%);
  background: none; border: none; font-size: 12px; color: var(--inkMute); cursor: pointer; padding: 0;
}
.m-topbar {
  height: 52px;
  background: var(--ink);
  display: flex;
  align-items: center;
  padding: 0 18px;
}
.m-wordmark { display: flex; align-items: center; gap: 6px; font-family: var(--font-mono); font-size: 15px; font-weight: 700; color: #fff; }
.m-wt { background: var(--amber); color: var(--ink); width: 20px; height: 20px; display: flex; align-items: center; justify-content: center; border-radius: 2px; font-size: 12px; }

.m-body { flex: 1; padding: 16px; display: flex; flex-direction: column; gap: 8px; }
.m-loading { text-align: center; padding: 32px; font-size: 13px; color: var(--inkMute); }
.m-section-label { font-family: var(--font-mono); font-size: 9px; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; color: var(--inkMute); padding: 8px 0 4px; }
.m-empty { text-align: center; padding: 32px 16px; font-size: 13px; color: var(--inkMute); }

.m-project-card {
  background: var(--paperAlt);
  border: 1px solid var(--rule);
  border-radius: 3px;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  cursor: pointer;
}
.m-project-card.active { border-left: 3px solid var(--amber); }
.m-project-card:active { opacity: 0.85; }

.m-proj-top { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.m-proj-name { font-size: 14px; font-weight: 600; color: var(--ink); }
.m-proj-ratio { font-family: var(--font-mono); font-size: 12px; flex-shrink: 0; }
.m-proj-file { font-family: var(--font-mono); font-size: 10px; color: var(--inkMute); }

.m-prog-bar { height: 4px; background: var(--ruleSoft); border-radius: 2px; overflow: hidden; }
.m-prog-fill { height: 100%; border-radius: 2px; transition: width 0.5s; }

.m-btn-new {
  width: 100%;
  padding: 14px;
  border: 1.5px dashed var(--rule);
  border-radius: 3px;
  background: transparent;
  font-size: 14px;
  font-weight: 600;
  color: var(--inkSoft);
  cursor: pointer;
  margin: 4px 0;
}
.m-btn-new:active { background: var(--ruleSoft); }
</style>
