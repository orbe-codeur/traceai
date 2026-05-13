<script setup>
const CATEGORIES = {
  'sécurité':     { short: 'SEC',   color: '#C8312D' },
  'mécanique':    { short: 'MEC',   color: '#56524A' },
  'électrique':   { short: 'ELEC',  color: '#2E5C9E' },
  'hydraulique':  { short: 'HYD',   color: '#1F5F5B' },
  'test':         { short: 'TEST',  color: '#7A4F1D' },
  'vérification': { short: 'VERIF', color: '#3D3936' },
}

const props = defineProps({ cat: String })
const meta = computed(() => CATEGORIES[props.cat] || { short: props.cat?.slice(0,4).toUpperCase(), color: '#8A8478' })
</script>

<script>
import { computed } from 'vue'
</script>

<template>
  <span class="cat-chip" :style="{ color: meta.color }">
    <span class="cat-dot" :style="{ background: meta.color }" />
    {{ meta.short }}
  </span>
</template>

<style scoped>
.cat-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.cat-dot {
  width: 6px;
  height: 6px;
  border-radius: 1px;
  flex-shrink: 0;
}
</style>
