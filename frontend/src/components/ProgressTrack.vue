<script setup>
import { computed } from 'vue'

const CATEGORIES = {
  'sécurité':     { short: 'SEC',   color: '#C8312D' },
  'mécanique':    { short: 'MEC',   color: '#56524A' },
  'électrique':   { short: 'ELEC',  color: '#2E5C9E' },
  'hydraulique':  { short: 'HYD',   color: '#1F5F5B' },
  'test':         { short: 'TEST',  color: '#7A4F1D' },
  'vérification': { short: 'VERIF', color: '#3D3936' },
}
const CAT_ORDER = ['sécurité', 'mécanique', 'hydraulique', 'électrique', 'test', 'vérification']

const props = defineProps({
  steps: Array,
  validations: Object,
})

const totalDone = computed(() => Object.values(props.validations || {}).filter(v => v.status === 'done').length)
const totalSteps = computed(() => (props.steps || []).length)
const pct = computed(() => totalSteps.value ? Math.round(totalDone.value / totalSteps.value * 100) : 0)

const rows = computed(() => {
  return CAT_ORDER.map(cat => {
    const catSteps = (props.steps || []).filter(s => s.category === cat)
    return {
      cat,
      meta: CATEGORIES[cat],
      steps: catSteps,
    }
  }).filter(r => r.steps.length > 0)
})

function segColor(step, meta) {
  const v = (props.validations || {})[step.id]
  if (!v || v.status === 'pending') return 'var(--ruleSoft)'
  if (v.status === 'done') return meta.color
  if (v.status === 'issue') return 'var(--amber)'
  if (v.status === 'active') return meta.color + '88'
  return 'var(--ruleSoft)'
}
</script>

<template>
  <div class="progress-track">
    <div class="track-header">
      <span class="track-count">{{ String(totalDone).padStart(2, '0') }} / {{ String(totalSteps).padStart(2, '0') }}</span>
      <span class="track-pct">{{ pct }}%</span>
    </div>
    <div class="track-rows">
      <div v-for="row in rows" :key="row.cat" class="track-row">
        <span class="track-label" :style="{ color: row.meta.color }">{{ row.meta.short }}</span>
        <div class="track-segs">
          <span
            v-for="step in row.steps"
            :key="step.id"
            class="track-seg"
            :style="{ background: segColor(step, row.meta) }"
          />
        </div>
        <span class="track-sub">{{ row.steps.filter(s => (validations?.[s.id]?.status === 'done')).length }}/{{ row.steps.length }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.progress-track { display: flex; flex-direction: column; gap: 6px; }
.track-header {
  display: flex;
  justify-content: space-between;
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 600;
  color: var(--inkSoft);
}
.track-pct { color: var(--teal); }
.track-rows { display: flex; flex-direction: column; gap: 4px; }
.track-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.track-label {
  font-family: var(--font-mono);
  font-size: 9px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  width: 36px;
  flex-shrink: 0;
}
.track-segs {
  display: flex;
  gap: 2px;
  flex: 1;
}
.track-seg {
  height: 6px;
  flex: 1;
  border-radius: 1px;
  transition: background 0.3s;
}
.track-sub {
  font-family: var(--font-mono);
  font-size: 9px;
  color: var(--inkMute);
  width: 28px;
  text-align: right;
  flex-shrink: 0;
}
</style>
