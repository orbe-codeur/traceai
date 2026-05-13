<script setup>
import { ref, computed, watch } from 'vue'
import CatChip from './CatChip.vue'
import Avatar from './Avatar.vue'
import { useToast } from '../composables/useToast.js'

const { error: toastError, warn: toastWarn } = useToast()

const props = defineProps({
  step: Object,
  validation: Object,
  projectId: [String, Number],
})

const pdfExpanded = ref(false)
const pdfUrl = computed(() =>
  props.step?.page_ref && props.projectId
    ? `/api/projects/${props.projectId}/pdf/${props.step.page_ref}`
    : null
)

const emit = defineEmits(['validated'])

const techName = ref(localStorage.getItem('traceai_tech') || '')
const witnessName = ref('')
const note = ref('')
const saving = ref(false)

const status = computed(() => props.validation?.status || 'pending')
const isPending = computed(() => status.value === 'pending' || status.value === 'active')

watch(() => props.step, () => {
  note.value = ''
  witnessName.value = ''
})

function fmtTime(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })
}

async function validate(actionStatus) {
  if (!techName.value.trim()) return toastWarn('Veuillez renseigner votre nom.')
  if (actionStatus === 'issue' && !note.value.trim()) return toastWarn('Décrivez le problème dans la note.')
  if (props.step.requires_witness && actionStatus === 'done' && !witnessName.value.trim()) {
    return toastWarn('Un témoin est requis pour cette étape critique.')
  }
  localStorage.setItem('traceai_tech', techName.value.trim())
  saving.value = true
  try {
    emit('validated', {
      step_id: props.step.id,
      technician_name: techName.value.trim(),
      status: actionStatus,
      note: note.value.trim() || null,
      witness_name: witnessName.value.trim() || null,
    })
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="detail-pane" v-if="step">
    <div class="detail-main">
      <!-- En-tête étape -->
      <div class="detail-header">
        <div class="detail-meta-row">
          <span class="detail-num">#{{ String(step.step_number).padStart(2, '0') }}</span>
          <span class="detail-total">/ {{ step.step_number }}</span>
          <CatChip :cat="step.category" />
          <span v-if="step.is_critical" class="badge-crit">CRITIQUE</span>
          <span v-if="step.requires_witness" class="badge-witness">2 signatures requises</span>
          <span class="detail-dur">⏱ {{ step.duration }}</span>
        </div>
        <h2 class="detail-title">{{ step.title }}</h2>
        <p class="detail-desc">{{ step.description }}</p>
      </div>

      <!-- Banner ACTIVE -->
      <div v-if="status === 'active'" class="banner-active">
        <span class="pulse-dot animate-trace-dot" />
        <Avatar :name="validation.technician_name" :size="24" />
        <div>
          <strong>{{ validation.technician_name }}</strong> travaille sur cette étape
          <span class="banner-time">depuis {{ fmtTime(validation.started_at) }}</span>
        </div>
      </div>

      <!-- Formulaire validation (pending / active) -->
      <div v-if="isPending" class="validation-form">
        <div class="form-section" :style="{ borderTopColor: 'var(--tealBg)' }">
          <div class="field">
            <label>Technicien</label>
            <div class="tech-row">
              <Avatar :name="techName || 'T'" :size="28" />
              <input v-model="techName" placeholder="Votre nom" class="input-field" />
            </div>
          </div>

          <div v-if="step.requires_witness" class="field witness-field">
            <label class="witness-label">
              <span class="witness-icon">★</span>
              Témoin requis (étape critique)
            </label>
            <input v-model="witnessName" placeholder="Nom du témoin" class="input-field" />
          </div>

          <div class="field">
            <div class="note-label-row">
              <label>Note <span class="optional">(optionnel)</span></label>
              <span class="mic-hint">🎤 Dicter</span>
            </div>
            <textarea v-model="note" rows="3" placeholder="Observations, mesures, remarques..." class="textarea-field" />
          </div>
        </div>

        <div class="form-actions">
          <button class="btn-validate" :disabled="saving" @click="validate('done')">
            {{ saving ? '...' : '✓ Signer & valider' }}
          </button>
          <button class="btn-issue" :disabled="saving" @click="validate('issue')">
            ⚠ Signaler un problème
          </button>
        </div>
      </div>

      <!-- Banner DONE -->
      <div v-else-if="status === 'done'" class="banner-done">
        <Avatar :name="validation.technician_name" :size="28" />
        <div>
          <div>Validé par <strong>{{ validation.technician_name }}</strong> à {{ fmtTime(validation.validated_at) }}</div>
          <div v-if="validation.witness_name" class="done-witness">Témoin : {{ validation.witness_name }}</div>
          <div v-if="validation.note" class="done-note">{{ validation.note }}</div>
        </div>
      </div>

      <!-- Banner ISSUE -->
      <div v-else-if="status === 'issue'" class="banner-issue">
        <Avatar :name="validation.technician_name" :size="28" />
        <div>
          <div>Problème signalé par <strong>{{ validation.technician_name }}</strong> · {{ fmtTime(validation.validated_at) }}</div>
          <div v-if="validation.note" class="issue-note">{{ validation.note }}</div>
        </div>
      </div>
    </div>

    <!-- Aperçu PDF réel -->
    <div class="pdf-preview">
      <div class="pdf-header">
        <span class="pdf-ref">Page source</span>
        <span class="pdf-page">p.{{ step.page_ref }}</span>
      </div>

      <div v-if="pdfUrl" class="pdf-img-wrap" @click="pdfExpanded = true" title="Cliquer pour agrandir">
        <img
          :src="pdfUrl"
          :key="pdfUrl"
          alt="Page PDF"
          class="pdf-img"
          loading="lazy"
        />
        <div class="pdf-img-overlay">
          <span class="pdf-zoom-icon">⤢</span>
        </div>
      </div>
      <div v-else class="pdf-no-page">
        <span>Aucune page source</span>
      </div>
    </div>

    <!-- Modal plein écran -->
    <Teleport to="body">
      <div v-if="pdfExpanded" class="pdf-modal" @click="pdfExpanded = false">
        <button class="pdf-modal-close" @click="pdfExpanded = false">✕</button>
        <img :src="pdfUrl" alt="Page PDF" class="pdf-modal-img" @click.stop />
      </div>
    </Teleport>
  </div>

  <div v-else class="detail-empty">
    <span>Sélectionnez une étape</span>
  </div>
</template>

<style scoped>
.detail-pane {
  flex: 1;
  display: flex;
  overflow: hidden;
}
.detail-main {
  flex: 1;
  overflow-y: auto;
  padding: 28px 32px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.detail-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--inkMute);
  font-size: 13px;
}

.detail-header { display: flex; flex-direction: column; gap: 10px; }
.detail-meta-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.detail-num {
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 600;
  color: var(--inkMute);
}
.detail-total { font-family: var(--font-mono); font-size: 10px; color: var(--inkMute); }
.detail-dur { font-family: var(--font-mono); font-size: 11px; color: var(--inkMute); margin-left: auto; }

.badge-crit {
  font-family: var(--font-mono);
  font-size: 9px;
  font-weight: 600;
  letter-spacing: 0.06em;
  color: var(--red);
  background: var(--redBg);
  padding: 2px 6px;
  border-radius: 2px;
}
.badge-witness {
  font-family: var(--font-mono);
  font-size: 9px;
  font-weight: 600;
  color: var(--inkSoft);
  background: var(--ruleSoft);
  padding: 2px 6px;
  border-radius: 2px;
}

.detail-title {
  font-size: 22px;
  font-weight: 600;
  letter-spacing: -0.02em;
  color: var(--ink);
  line-height: 1.3;
}
.detail-desc {
  font-size: 13.5px;
  color: var(--inkSoft);
  line-height: 1.6;
}

.banner-active {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 14px;
  background: var(--amberBg);
  border: 1px dashed var(--amber);
  border-radius: 3px;
  font-size: 13px;
  color: var(--inkSoft);
}
.banner-time { font-family: var(--font-mono); font-size: 11px; color: var(--amber); margin-left: 4px; }
.pulse-dot {
  width: 7px; height: 7px; border-radius: 50%; background: var(--amber); flex-shrink: 0;
}

.validation-form { display: flex; flex-direction: column; gap: 16px; }
.form-section {
  border-top: 4px solid;
  border-top-color: var(--tealBg);
  padding-top: 16px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.field { display: flex; flex-direction: column; gap: 5px; }
.field label {
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--inkMute);
}
.optional { font-weight: 400; text-transform: none; letter-spacing: 0; }
.tech-row { display: flex; align-items: center; gap: 8px; }
.witness-field { }
.witness-label { color: var(--red) !important; display: flex; align-items: center; gap: 4px; }
.witness-icon { font-size: 10px; }

.input-field, .textarea-field {
  border: 1px solid var(--rule);
  border-radius: 2px;
  padding: 8px 10px;
  font-family: var(--font-sans);
  font-size: 13px;
  color: var(--ink);
  background: var(--paper);
  outline: none;
  width: 100%;
}
.input-field:focus, .textarea-field:focus { border-color: var(--ink); }
.textarea-field { resize: vertical; font-family: var(--font-mono); font-size: 12px; }

.note-label-row { display: flex; align-items: center; justify-content: space-between; }
.mic-hint { font-size: 11px; color: var(--inkMute); }

.form-actions { display: flex; gap: 10px; }
.btn-validate {
  flex: 2;
  height: 40px;
  background: var(--teal);
  color: #fff;
  border: none;
  border-radius: 3px;
  font-size: 13.5px;
  font-weight: 600;
  cursor: pointer;
}
.btn-validate:hover { opacity: 0.88; }
.btn-validate:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-issue {
  flex: 1;
  height: 40px;
  background: transparent;
  color: var(--red);
  border: 1px solid var(--red);
  border-radius: 3px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}
.btn-issue:hover { background: var(--redBg); }
.btn-issue:disabled { opacity: 0.5; cursor: not-allowed; }

.banner-done {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 14px;
  background: var(--tealBg);
  border-radius: 3px;
  font-size: 13px;
  color: var(--teal);
}
.done-witness { font-family: var(--font-mono); font-size: 11px; margin-top: 3px; opacity: 0.8; }
.done-note { font-style: italic; margin-top: 4px; font-size: 12px; color: var(--inkSoft); }

.banner-issue {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 14px;
  background: var(--amberBg);
  border-left: 3px solid var(--amber);
  border-radius: 3px;
  font-size: 13px;
  color: var(--inkSoft);
}
.issue-note { font-style: italic; margin-top: 4px; font-size: 12px; color: var(--amber); }

/* --- Aperçu PDF réel --- */
.pdf-preview {
  width: 280px;
  flex-shrink: 0;
  border-left: 1px solid var(--rule);
  background: var(--paperAlt);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.pdf-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  border-bottom: 1px solid var(--rule);
  flex-shrink: 0;
}
.pdf-ref { font-size: 11px; color: var(--inkSoft); }
.pdf-page {
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 600;
  color: var(--teal);
}

.pdf-img-wrap {
  flex: 1;
  overflow-y: auto;
  position: relative;
  cursor: zoom-in;
}
.pdf-img {
  width: 100%;
  display: block;
}
.pdf-img-overlay {
  position: absolute;
  inset: 0;
  background: transparent;
  display: flex;
  align-items: flex-end;
  justify-content: flex-end;
  padding: 8px;
  opacity: 0;
  transition: opacity 0.15s;
}
.pdf-img-wrap:hover .pdf-img-overlay { opacity: 1; }
.pdf-zoom-icon {
  font-size: 18px;
  background: rgba(0,0,0,0.55);
  color: #fff;
  width: 28px;
  height: 28px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.pdf-no-page {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: var(--inkMute);
}

/* --- Modal plein écran --- */
.pdf-modal {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.82);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
  cursor: zoom-out;
}
.pdf-modal-img {
  max-height: 90vh;
  max-width: 90vw;
  object-fit: contain;
  border-radius: 3px;
  box-shadow: 0 20px 60px rgba(0,0,0,0.5);
  cursor: default;
}
.pdf-modal-close {
  position: fixed;
  top: 16px;
  right: 20px;
  background: rgba(255,255,255,0.12);
  color: #fff;
  border: none;
  border-radius: 4px;
  width: 36px;
  height: 36px;
  font-size: 16px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1001;
}
.pdf-modal-close:hover { background: rgba(255,255,255,0.22); }
</style>
