<script setup>
import { useRouter } from 'vue-router'

const props = defineProps({
  projectId: [String, Number],
  active: String,
  steps: Array,
  validations: Object,
  otherProjects: Array,
})

const router = useRouter()

const navItems = [
  { key: 'overview',   label: 'Aperçu',    icon: '◻' },
  { key: 'checklist',  label: 'Checklist', icon: '☰' },
  { key: 'summary',    label: 'Journal',   icon: '◷' },
]

function navTo(key) {
  if (!props.projectId) return
  if (key === 'overview') router.push(`/project/${props.projectId}/overview`)
  else if (key === 'checklist') router.push(`/project/${props.projectId}`)
  else if (key === 'summary') router.push(`/project/${props.projectId}/summary`)
}

function projectStatus(p) {
  if (p.completed_steps >= p.total_steps) return 'completed'
  if (p.completed_steps > 0) return 'active'
  return 'pending'
}
</script>

<template>
  <aside class="left-rail">
    <nav class="nav-items">
      <button
        v-for="item in navItems"
        :key="item.key"
        class="nav-item"
        :class="{ active: active === item.key }"
        @click="navTo(item.key)"
      >
        <span class="nav-icon">{{ item.icon }}</span>
        <span class="nav-label">{{ item.label }}</span>
      </button>
    </nav>

    <div v-if="otherProjects?.length" class="other-projects">
      <span class="other-title">Autres projets</span>
      <div v-for="p in otherProjects" :key="p.id" class="other-item" @click="router.push(`/project/${p.id}`)">
        <span class="other-dot" :style="{ background: projectStatus(p) === 'completed' ? 'var(--teal)' : 'var(--amber)' }" />
        <div class="other-info">
          <span class="other-name">{{ p.name }}</span>
          <span class="other-ratio">{{ p.completed_steps }}/{{ p.total_steps }}</span>
        </div>
      </div>
    </div>

    <button class="btn-new" @click="router.push('/')">+ Nouveau projet</button>
  </aside>
</template>

<style scoped>
.left-rail {
  width: 220px;
  flex-shrink: 0;
  background: var(--paperAlt);
  border-right: 1px solid var(--rule);
  display: flex;
  flex-direction: column;
  padding: 16px 0;
  overflow-y: auto;
}

.nav-items { display: flex; flex-direction: column; gap: 2px; padding: 0 8px; }
.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: 3px;
  background: transparent;
  border: none;
  color: var(--inkSoft);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  text-align: left;
  width: 100%;
  transition: background 0.12s;
}
.nav-item:hover { background: var(--ruleSoft); }
.nav-item.active {
  background: var(--paper);
  color: var(--ink);
  font-weight: 600;
  border: 1px solid var(--rule);
}
.nav-icon { font-size: 14px; width: 16px; text-align: center; flex-shrink: 0; }
.nav-label { font-size: 13px; }

.other-projects {
  margin-top: 24px;
  padding: 0 12px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.other-title {
  font-family: var(--font-mono);
  font-size: 9px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--inkMute);
  margin-bottom: 6px;
}
.other-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 4px;
  border-radius: 3px;
  cursor: pointer;
}
.other-item:hover { background: var(--ruleSoft); }
.other-dot { width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0; }
.other-info { display: flex; flex-direction: column; }
.other-name { font-size: 12px; color: var(--inkSoft); line-height: 1.3; }
.other-ratio { font-family: var(--font-mono); font-size: 10px; color: var(--inkMute); }

.btn-new {
  margin: auto 12px 0;
  margin-top: auto;
  padding: 8px;
  border: 1px dashed var(--rule);
  border-radius: 3px;
  background: transparent;
  color: var(--inkSoft);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: border-color 0.15s;
}
.btn-new:hover { border-color: var(--ink); color: var(--ink); }
</style>
