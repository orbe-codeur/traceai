<template>
  <div class="wag-root">

    <!-- Barre contrôle -->
    <div class="wag-bar">
      <span class="wag-mono wag-mute" style="font-size:10px;letter-spacing:.18em;text-transform:uppercase">Knowledge Graph</span>
      <div style="flex:1" />
      <span v-if="building" class="wag-building wag-mono">
        <span class="wag-build-dot animate-trace-dot" />
        Construction en cours…
      </span>
      <button v-if="graphReady && !building" class="wag-btn" @click="rebuild" :disabled="building">
        ↻ Regénérer
      </button>
      <button v-if="graphReady" class="wag-btn" @click="fullscreen">
        ⛶ Plein écran
      </button>
    </div>

    <!-- État vide — graph non construit -->
    <div v-if="!graphReady && !building" class="wag-empty">
      <div style="font-size:52px;margin-bottom:16px">🕸️</div>
      <h2 class="wag-empty-title">Graphe de connaissances</h2>
      <p class="wag-empty-sub">
        Visualisez les relations entre machines, entités et concepts extraits de votre wiki.
      </p>
      <button class="wag-btn-primary" @click="build">
        Construire le graphe
      </button>
    </div>

    <!-- Construction en cours -->
    <div v-else-if="building" class="wag-empty">
      <div style="font-size:48px;margin-bottom:16px">⚙️</div>
      <h2 class="wag-empty-title">Construction du graphe…</h2>
      <p class="wag-empty-sub wag-mono" style="font-size:13px">Pass 1 : extraction des liens explicites · Pass 2 : inférence sémantique</p>
      <div class="wag-spinner" />
    </div>

    <!-- iframe graph.html -->
    <iframe v-else ref="iframeEl" class="wag-iframe" :src="graphUrl" />

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '../services/api.js'
import { useToast } from '../composables/useToast.js'

const props = defineProps({ projectId: { type: Number, required: true } })
const { success, error: toastError } = useToast()

const graphReady = ref(false)
const building = ref(false)
const iframeEl = ref(null)

const graphUrl = computed(() => api.graphHtmlUrl(props.projectId))

async function checkGraph() {
  try {
    await api.getGraph(props.projectId)
    graphReady.value = true
  } catch {
    graphReady.value = false
  }
}

async function build() {
  building.value = true
  try {
    await api.buildGraph(props.projectId)
    graphReady.value = true
    success('Graphe construit avec succès.')
  } catch (e) {
    toastError('Erreur lors de la construction du graphe.')
  } finally {
    building.value = false
  }
}

async function rebuild() {
  building.value = true
  try {
    await api.buildGraph(props.projectId)
    // Recharger l'iframe
    if (iframeEl.value) {
      iframeEl.value.src = graphUrl.value + '?t=' + Date.now()
    }
    success('Graphe regénéré.')
  } catch {
    toastError('Erreur lors de la regénération.')
  } finally {
    building.value = false
  }
}

function fullscreen() {
  if (iframeEl.value?.requestFullscreen) {
    iframeEl.value.requestFullscreen()
  }
}

onMounted(checkGraph)
</script>

<style scoped>
.wag-root { display: flex; flex-direction: column; height: 100%; overflow: hidden; }

.wag-bar {
  height: 44px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 24px;
  border-bottom: 1px solid var(--rule);
  background: var(--paper);
  flex-shrink: 0;
}
.wag-btn {
  padding: 5px 11px;
  background: transparent;
  border: 1px solid var(--rule);
  border-radius: 3px;
  cursor: pointer;
  font-family: var(--font-sans);
  font-size: 12.5px;
  font-weight: 550;
  color: var(--inkSoft);
}
.wag-btn:hover:not(:disabled) { background: var(--ruleSoft); }
.wag-btn:disabled { opacity: .5; cursor: not-allowed; }
.wag-btn-primary {
  padding: 10px 20px;
  background: var(--ink);
  color: var(--paper);
  border: none;
  border-radius: 3px;
  cursor: pointer;
  font-family: var(--font-sans);
  font-size: 14px;
  font-weight: 600;
}
.wag-btn-primary:hover { opacity: .88; }
.wag-building {
  display: flex;
  align-items: center;
  gap: 7px;
  font-size: 12px;
  color: var(--amber);
}
.wag-build-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--amber);
  display: inline-block;
}

.wag-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  text-align: center;
}
.wag-empty-title { font-size: 22px; font-weight: 700; margin: 0 0 10px; }
.wag-empty-sub { font-size: 14px; color: var(--inkSoft); max-width: 460px; line-height: 1.6; margin: 0 0 24px; }

.wag-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--rule);
  border-top-color: var(--ink);
  border-radius: 50%;
  animation: wagSpin .8s linear infinite;
  margin-top: 16px;
}
@keyframes wagSpin { to { transform: rotate(360deg); } }

.wag-iframe { flex: 1; border: none; width: 100%; }

.wag-mono { font-family: var(--font-mono); }
.wag-mute { color: var(--inkMute); }
</style>
