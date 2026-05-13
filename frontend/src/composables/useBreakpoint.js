import { ref, onMounted, onUnmounted } from 'vue'

export function useBreakpoint() {
  const isMobile = ref(typeof window !== 'undefined' ? window.innerWidth < 768 : false)

  function update() { isMobile.value = window.innerWidth < 768 }

  onMounted(() => window.addEventListener('resize', update))
  onUnmounted(() => window.removeEventListener('resize', update))

  return { isMobile }
}
