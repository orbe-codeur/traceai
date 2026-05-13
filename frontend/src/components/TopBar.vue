<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import Avatar from './Avatar.vue'
import { useExport } from '../composables/useExport.js'

const props = defineProps({
  project: Object,
  validations: Object,
  steps: Array,
})

const { exportPV } = useExport()

const router = useRouter()

const done = computed(() => Object.values(props.validations || {}).filter(v => v.status === 'done').length)
const total = computed(() => (props.steps || []).length)
const pct = computed(() => total.value ? Math.round(done.value / total.value * 100) : 0)
const issues = computed(() => Object.values(props.validations || {}).filter(v => v.status === 'issue').length)

const techs = computed(() => {
  const names = [...new Set(Object.values(props.validations || {}).map(v => v.technician_name).filter(Boolean))]
  return names.slice(0, 4)
})
</script>

<template>
  <header class="topbar">
    <div class="topbar-left">
      <button class="wordmark" @click="router.push('/')">
        <span class="wordmark-t">T</span>
        <span>Trace<span style="color:var(--amber)">AI</span></span>
      </button>
      <template v-if="project">
        <span class="breadcrumb-sep">/</span>
        <span class="breadcrumb-proj">{{ project.name }}</span>
        <span class="breadcrumb-ref">{{ project.ref || project.pdf_filename }}</span>
      </template>
    </div>

    <div v-if="project" class="topbar-center">
      <div class="topbar-prog">
        <div class="topbar-bar">
          <div class="topbar-fill" :style="{ width: pct + '%' }" />
        </div>
        <span class="topbar-ratio">{{ done }}/{{ total }}</span>
      </div>
      <span v-if="issues > 0" class="topbar-alert">{{ issues }} problème{{ issues > 1 ? 's' : '' }}</span>
    </div>

    <div class="topbar-right">
      <div v-if="project" class="topbar-avatars">
        <Avatar v-for="name in techs" :key="name" :name="name" :size="26" />
      </div>
      <button v-if="project" class="btn-export" @click="exportPV(project, steps)">Exporter PV</button>
    </div>
  </header>
</template>

<style scoped>
.topbar {
  height: 56px;
  background: var(--ink);
  display: flex;
  align-items: center;
  padding: 0 20px;
  gap: 16px;
  flex-shrink: 0;
  position: sticky;
  top: 0;
  z-index: 20;
}
.topbar-left { display: flex; align-items: center; gap: 10px; flex-shrink: 0; }

.wordmark {
  display: flex;
  align-items: center;
  gap: 5px;
  font-family: var(--font-mono);
  font-size: 14px;
  font-weight: 700;
  color: #fff;
  background: none;
  border: none;
  cursor: pointer;
  padding: 0;
}
.wordmark-t {
  background: var(--amber);
  color: var(--ink);
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 2px;
  font-size: 12px;
}
.breadcrumb-sep { color: #555; font-size: 13px; }
.breadcrumb-proj { color: #ddd; font-size: 13px; font-weight: 500; }
.breadcrumb-ref {
  color: #888;
  font-family: var(--font-mono);
  font-size: 11px;
}

.topbar-center { flex: 1; display: flex; align-items: center; gap: 12px; max-width: 280px; }
.topbar-prog { display: flex; align-items: center; gap: 8px; flex: 1; }
.topbar-bar {
  flex: 1;
  height: 4px;
  background: #333;
  border-radius: 2px;
  overflow: hidden;
}
.topbar-fill {
  height: 100%;
  background: var(--teal);
  border-radius: 2px;
  transition: width 0.5s;
}
.topbar-ratio {
  font-family: var(--font-mono);
  font-size: 11px;
  color: #aaa;
  flex-shrink: 0;
}
.topbar-alert {
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 600;
  color: var(--amber);
  background: rgba(232,154,45,0.15);
  padding: 2px 7px;
  border-radius: 2px;
  flex-shrink: 0;
}

.topbar-right { display: flex; align-items: center; gap: 12px; margin-left: auto; }
.topbar-avatars { display: flex; }
.topbar-avatars > * + * { margin-left: -6px; }

.btn-export {
  font-size: 12px;
  font-weight: 600;
  color: var(--ink);
  background: var(--paper);
  border: none;
  border-radius: 3px;
  padding: 5px 12px;
  cursor: pointer;
  flex-shrink: 0;
}
.btn-export:hover { opacity: 0.88; }
</style>
