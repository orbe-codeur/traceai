<script setup>
import { ref, computed } from 'vue'
import CatChip from './CatChip.vue'
import Avatar from './Avatar.vue'

const props = defineProps({
  step: Object,
  validation: Object,
  active: Boolean,
  projectId: [String, Number],
})

const emit = defineEmits(['select'])

const showPdf = ref(false)
const pdfUrl  = computed(() =>
  props.step?.page_ref && props.projectId
    ? `/api/projects/${props.projectId}/pdf/${props.step.page_ref}`
    : null
)

const status = computed(() => props.validation?.status || 'pending')

const accentColor = computed(() => {
  if (status.value === 'done')   return 'var(--teal)'
  if (status.value === 'issue')  return 'var(--amber)'
  if (status.value === 'active') return 'var(--amber)'
  if (props.step?.is_critical)   return 'var(--red)'
  return 'var(--rule)'
})

const statusLabel = computed(() => ({
  done:    'VALIDÉE',
  issue:   'PROBLÈME',
  active:  'EN COURS',
  pending: 'À FAIRE',
}[status.value]))

function fmtTime(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })
}
</script>

<template>
  <div
    class="step-row"
    :class="[`s-${status}`, { selected: active }]"
    @click="emit('select', step.id)"
  >
    <!-- Rail unique gauche -->
    <div class="row-rail" :style="{ background: accentColor }" />

    <div class="row-body">
      <!-- Ligne principale -->
      <div class="row-top">
        <span class="row-num">{{ String(step.step_number).padStart(2, '0') }}</span>
        <CatChip :cat="step.category" />
        <span v-if="step.is_critical" class="crit-badge">▲ CRITIQUE</span>
        <span class="row-title">{{ step.title }}</span>
        <button
          v-if="step.page_ref && projectId"
          class="row-page"
          @click.stop="showPdf = true"
        >p.{{ step.page_ref }}</button>
        <span v-else-if="step.page_ref" class="row-page row-page-static">p.{{ step.page_ref }}</span>
        <span class="status-pill" :class="`pill-${status}`">{{ statusLabel }}</span>
      </div>

      <!-- Méta-ligne séparée par pointillé (visible si non pending) -->
      <div v-if="status !== 'pending'" class="row-meta">
        <Avatar :name="validation.technician_name" :size="14" />
        <span class="meta-name">{{ validation.technician_name }}</span>
        <template v-if="status === 'active'">
          <span class="meta-dot animate-trace-dot" />
          <span class="meta-active">en cours</span>
        </template>
        <template v-else-if="status === 'issue' && validation.note">
          <span class="meta-note">{{ validation.note }}</span>
        </template>
        <span v-if="validation.validated_at" class="meta-time">
          {{ fmtTime(validation.validated_at) }}
        </span>
      </div>
    </div>
  </div>

  <!-- Modal page PDF -->
  <Teleport to="body">
    <div v-if="showPdf" class="pdf-modal" @click="showPdf = false">
      <div class="pdf-modal-header" @click.stop>
        <span class="pdf-modal-label">{{ step.title }} — p.{{ step.page_ref }}</span>
        <button class="pdf-modal-close" @click="showPdf = false">✕</button>
      </div>
      <img :src="pdfUrl" alt="Page PDF" class="pdf-modal-img" @click.stop />
    </div>
  </Teleport>
</template>

<style scoped>
.step-row {
  position: relative;
  display: flex;
  align-items: stretch;
  border-bottom: 1px solid var(--ruleSoft);
  cursor: pointer;
  transition: background 0.1s;
}
.step-row:hover    { background: var(--paperAlt); }
.step-row.selected { background: var(--paperAlt); }

/* Rail gauche unique */
.row-rail { width: 3px; flex-shrink: 0; }

/* Corps */
.row-body {
  flex: 1;
  padding: 12px 12px 12px 10px;
  display: flex;
  flex-direction: column;
  gap: 0;
  overflow: hidden;
}

/* Ligne principale */
.row-top {
  display: flex;
  align-items: center;
  gap: 6px;
  overflow: hidden;
}

/* Numéro d'étape — noir bold mono */
.row-num {
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 700;
  color: var(--ink);
  letter-spacing: 0.02em;
  flex-shrink: 0;
}

/* Badge CRITIQUE */
.crit-badge {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-family: var(--font-mono);
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.05em;
  padding: 2px 6px;
  background: var(--redBg);
  color: var(--red);
  border-radius: 2px;
  flex-shrink: 0;
}

/* Titre */
.row-title {
  font-size: 12.5px;
  font-weight: 550;
  color: var(--ink);
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  letter-spacing: -0.005em;
}

/* Lien page PDF */
.row-page {
  font-family: var(--font-mono);
  font-size: 9.5px;
  color: var(--blue);
  flex-shrink: 0;
  background: none;
  border: none;
  cursor: pointer;
  padding: 1px 4px;
  border-radius: 2px;
  text-decoration: underline;
  letter-spacing: 0.03em;
}
.row-page:hover { background: var(--ruleSoft); }
.row-page-static { color: var(--inkMute); cursor: default; text-decoration: none; }

/* Pastille statut explicite */
.status-pill {
  flex-shrink: 0;
  font-family: var(--font-mono);
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.06em;
  padding: 2px 7px;
  border-radius: 2px;
}
.pill-done    { background: var(--tealBg);  color: var(--teal); }
.pill-issue   { background: var(--amberBg); color: #7A5410; }
.pill-active  { background: #FFF8EB;        color: var(--amber); border: 1px dashed var(--amber); }
.pill-pending { background: transparent;    color: var(--inkMute); border: 1px solid var(--ruleSoft); }

/* Méta-ligne — séparée par tirets */
.row-meta {
  display: flex;
  align-items: center;
  gap: 5px;
  margin-top: 7px;
  padding-top: 6px;
  border-top: 1px dashed var(--rule);
  overflow: hidden;
}
.meta-name   { font-size: 10.5px; font-weight: 550; color: var(--inkSoft); flex-shrink: 0; }
.meta-time   { font-family: var(--font-mono); font-size: 9.5px; color: var(--inkMute); margin-left: auto; flex-shrink: 0; }
.meta-note   { font-size: 10.5px; font-style: italic; color: #7A5410; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.meta-active { font-size: 10.5px; color: var(--amber); font-weight: 600; }
.meta-dot    { width: 6px; height: 6px; border-radius: 50%; background: var(--amber); flex-shrink: 0; }

/* Modal PDF */
.pdf-modal {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.85);
  z-index: 1000;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 20px;
  cursor: zoom-out;
  gap: 12px;
}
.pdf-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  max-width: 700px;
  cursor: default;
}
.pdf-modal-label { font-size: 13px; font-weight: 550; color: rgba(255,255,255,0.8); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pdf-modal-close {
  background: rgba(255,255,255,0.12); color: #fff; border: none;
  border-radius: 4px; width: 32px; height: 32px;
  font-size: 15px; cursor: pointer; flex-shrink: 0; margin-left: 12px;
}
.pdf-modal-close:hover { background: rgba(255,255,255,0.22); }
.pdf-modal-img {
  max-height: 82vh; max-width: min(700px, 90vw);
  object-fit: contain; border-radius: 3px;
  box-shadow: 0 20px 60px rgba(0,0,0,0.5); cursor: default;
}
</style>
