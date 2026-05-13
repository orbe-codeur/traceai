<script setup>
import { computed } from 'vue'

const TECHS = [
  { name: 'Marie Tissier',  initials: 'MT', color: '#C8312D' },
  { name: 'Jean Mercier',   initials: 'JM', color: '#1F5F5B' },
  { name: 'Karim Belkacem', initials: 'KB', color: '#2E5C9E' },
  { name: 'M. Dubois',      initials: 'MD', color: '#56524A' },
]

const props = defineProps({
  name: String,
  size: { type: Number, default: 28 },
  ring: { type: Boolean, default: false },
  spinning: { type: Boolean, default: false },
})

const tech = computed(() => TECHS.find(t => t.name === props.name))

const initials = computed(() => {
  if (tech.value) return tech.value.initials
  if (!props.name) return '?'
  return props.name.split(' ').map(w => w[0]).slice(0, 2).join('').toUpperCase()
})

const color = computed(() => {
  if (tech.value) return tech.value.color
  const hash = [...(props.name || '')].reduce((a, c) => a + c.charCodeAt(0), 0)
  const palette = ['#C8312D', '#1F5F5B', '#2E5C9E', '#56524A', '#7A4F1D', '#3D3936']
  return palette[hash % palette.length]
})

const fontSize = computed(() => Math.max(10, Math.floor(props.size * 0.38)))
</script>

<template>
  <span class="avatar-wrap" :style="{ width: size + 'px', height: size + 'px' }">
    <span
      class="avatar"
      :style="{
        width: size + 'px',
        height: size + 'px',
        background: color,
        fontSize: fontSize + 'px',
      }"
    >{{ initials }}</span>
    <span v-if="ring || spinning" class="avatar-ring" :class="{ 'animate-trace-spin': spinning }" :style="{ borderColor: color }" />
  </span>
</template>

<style scoped>
.avatar-wrap {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.avatar {
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-family: var(--font-mono);
  font-weight: 600;
  letter-spacing: 0.02em;
  flex-shrink: 0;
}
.avatar-ring {
  position: absolute;
  inset: -3px;
  border-radius: 50%;
  border: 2px dashed;
  pointer-events: none;
}
</style>
