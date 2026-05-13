<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '../../services/api.js'
import { useToast } from '../../composables/useToast.js'

const router = useRouter()
const { error: toastError } = useToast()

const projectName  = ref('')
const selectedFile = ref(null)
const loading      = ref(false)

function onFileChange(e) { selectedFile.value = e.target.files[0] || null }

async function handleSubmit() {
  if (!projectName.value.trim() || !selectedFile.value) return
  loading.value = true
  try {
    const { data } = await api.uploadProject(projectName.value.trim(), selectedFile.value)
    router.push(`/project/${data.project_id}`)
  } catch (err) {
    toastError(err?.response?.data?.detail || 'Erreur lors de l\'analyse du PDF.')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="mobile-page">
    <header class="m-topbar">
      <button class="m-back" @click="router.push('/')">←</button>
      <div class="m-wordmark">
        <span class="m-wt">T</span>
        <span>Trace<span style="color:var(--amber)">AI</span></span>
      </div>
    </header>

    <div class="m-body">
      <h1 class="m-title">Nouveau projet</h1>
      <p class="m-sub">L'IA extrait toutes les étapes de votre manuel PDF</p>

      <div class="m-field">
        <label>Nom du projet</label>
        <input v-model="projectName" type="text" placeholder="Installation ORC Enogia — Site Metz" class="m-input" />
      </div>

      <div class="m-field">
        <label>Manuel PDF</label>
        <div class="m-file-zone" @click="$refs.fileInput.click()">
          <input ref="fileInput" type="file" accept=".pdf" style="display:none" @change="onFileChange" />
          <template v-if="!selectedFile">
            <span class="m-file-icon">📄</span>
            <span class="m-file-text">Appuyer pour sélectionner</span>
          </template>
          <template v-else>
            <span class="m-file-icon">✓</span>
            <span class="m-file-name">{{ selectedFile.name }}</span>
          </template>
        </div>
      </div>

      <div v-if="loading" class="m-loading-block">
        <div class="m-spinner" />
        <div>
          <p class="m-loading-main">Extraction en cours…</p>
          <p class="m-loading-sub">Mistral large · 60–90 secondes</p>
        </div>
      </div>

      <button v-else class="m-btn-primary" :disabled="!projectName || !selectedFile" @click="handleSubmit">
        Analyser le manuel
      </button>
    </div>
  </div>
</template>

<style scoped>
.mobile-page { min-height: 100vh; background: var(--paper); display: flex; flex-direction: column; }
.m-topbar {
  height: 52px;
  background: var(--ink);
  display: flex;
  align-items: center;
  padding: 0 18px;
  gap: 12px;
}
.m-back { background: none; border: none; color: #fff; font-size: 20px; cursor: pointer; padding: 0; }
.m-wordmark { display: flex; align-items: center; gap: 6px; font-family: var(--font-mono); font-size: 15px; font-weight: 700; color: #fff; }
.m-wt { background: var(--amber); color: var(--ink); width: 20px; height: 20px; display: flex; align-items: center; justify-content: center; border-radius: 2px; font-size: 12px; }

.m-body { flex: 1; padding: 20px 16px; display: flex; flex-direction: column; gap: 18px; }
.m-title { font-size: 22px; font-weight: 600; color: var(--ink); }
.m-sub { font-size: 13px; color: var(--inkSoft); margin-top: -10px; }

.m-field { display: flex; flex-direction: column; gap: 6px; }
.m-field label { font-family: var(--font-mono); font-size: 10px; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; color: var(--inkMute); }

.m-input {
  border: 1px solid var(--rule);
  border-radius: 3px;
  padding: 12px 14px;
  font-size: 15px;
  color: var(--ink);
  background: var(--paperAlt);
  outline: none;
  width: 100%;
  -webkit-appearance: none;
}
.m-input:focus { border-color: var(--ink); }

.m-file-zone {
  border: 1.5px dashed var(--rule);
  border-radius: 3px;
  padding: 24px 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  background: var(--paperAlt);
}
.m-file-icon { font-size: 28px; }
.m-file-text { font-size: 14px; color: var(--inkSoft); }
.m-file-name { font-size: 13px; font-weight: 550; color: var(--teal); text-align: center; }

.m-loading-block {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px;
  background: var(--amberBg);
  border: 1px solid var(--amber);
  border-radius: 3px;
}
.m-spinner {
  width: 22px; height: 22px;
  border: 2.5px solid var(--ruleSoft);
  border-top-color: var(--amber);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  flex-shrink: 0;
}
@keyframes spin { to { transform: rotate(360deg); } }
.m-loading-main { font-size: 13px; font-weight: 550; color: var(--ink); }
.m-loading-sub { font-size: 11px; color: var(--inkSoft); font-family: var(--font-mono); margin-top: 2px; }

.m-btn-primary {
  width: 100%;
  height: 52px;
  background: var(--ink);
  color: var(--paper);
  border: none;
  border-radius: 3px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  margin-top: auto;
}
.m-btn-primary:disabled { opacity: 0.35; }
.m-btn-primary:not(:disabled):active { opacity: 0.85; }
</style>
