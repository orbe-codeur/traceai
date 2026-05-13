<script setup>
import { ref, computed } from 'vue'
import CatChip from './CatChip.vue'
import Avatar from './Avatar.vue'

const props = defineProps({
  step: Object,
  validation: Object,
  expanded: Boolean,
})

const emit = defineEmits(['expand', 'action'])

const status = computed(() => props.validation?.status || 'pending')
const isDone = computed(() => status.value === 'done')
const isIssue = computed(() => status.value === 'issue')
const isActive = computed(() => status.value === 'active')
const isPending = computed(() => status.value === 'pending')

const accentColor = computed(() => {
  if (isActive.value) return 'var(--amber)'
  if (isDone.value) return 'var(--teal)'
  if (isIssue.value) return 'var(--amber)'
  if (props.step?.is_critical) return 'var(--red)'
  return 'var(--ruleSoft)'
})

const cardBg = computed(() => {
  if (isDone.value) return 'var(--paperAlt)'
  if (isIssue.value) return '#FCF1DD'
  if (isActive.value) return '#FFF8EB'
  return 'var(--paperAlt)'
})

function fmtTime(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })
}

function handleClick() {
  if (isPending.value) emit('expand')
}
</script>

<template>
  <div class="step-card" :style="{ background: cardBg }" @click="handleClick">
    <div class="step-rail" :style="{ background: accentColor }" :class="{ 'animate-trace-pulse': isActive }" />
    <div class="step-body">
      <div class="step-header">
        <span class="step-num">{{ String(step.step_number).padStart(2, '0') }}</span>
        <span class="step-title">{{ step.title }}</span>
        <div class="step-meta">
          <CatChip :cat="step.category" />
          <span class="step-page">p.{{ step.page_ref }}</span>
          <span v-if="step.duration" class="step-dur">{{ step.duration }}</span>
        </div>
      </div>

      <div class="step-badges">
        <span v-if="step.is_critical && !isDone" class="badge-critical">CRITIQUE</span>
        <span v-if="step.requires_witness && !isDone" class="badge-witness">2 signatures</span>
      </div>

      <template v-if="expanded || !isPending">
        <p class="step-desc">{{ step.description }}</p>

        <!-- Strip DONE -->
        <div v-if="isDone" class="strip strip-done">
          <Avatar :name="validation.technician_name" :size="22" />
          <span>Validé par <strong>{{ validation.technician_name }}</strong> à {{ fmtTime(validation.validated_at) }}</span>
          <span v-if="validation.witness_name" class="witness-tag">Témoin : {{ validation.witness_name }}</span>
          <span v-if="validation.note" class="strip-note">{{ validation.note }}</span>
        </div>

        <!-- Strip ISSUE -->
        <div v-else-if="isIssue" class="strip strip-issue">
          <Avatar :name="validation.technician_name" :size="22" />
          <div>
            <span>Problème signalé par <strong>{{ validation.technician_name }}</strong> à {{ fmtTime(validation.validated_at) }}</span>
            <p v-if="validation.note" class="strip-note">{{ validation.note }}</p>
          </div>
        </div>

        <!-- Strip ACTIVE -->
        <div v-else-if="isActive" class="strip strip-active">
          <span class="pulse-dot animate-trace-dot" />
          <Avatar :name="validation.technician_name" :size="22" />
          <span><strong>{{ validation.technician_name }}</strong> — en cours depuis {{ fmtTime(validation.started_at) }}</span>
        </div>

        <!-- Actions (pending / active) -->
        <div v-if="(isPending || isActive) && expanded" class="action-row">
          <button class="btn-validate" @click.stop="emit('action', 'done')">✓ Valider</button>
          <button class="btn-issue"    @click.stop="emit('action', 'issue')">⚠ Signaler</button>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.step-card {
  display: flex;
  border: 1px solid var(--rule);
  border-radius: 3px;
  overflow: hidden;
  cursor: default;
  transition: box-shadow 0.15s;
}
.step-card:hover { box-shadow: 0 1px 4px rgba(0,0,0,0.06); }

.step-rail {
  width: 3px;
  flex-shrink: 0;
}

.step-body {
  flex: 1;
  padding: 11px 13px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.step-header {
  display: flex;
  align-items: baseline;
  gap: 8px;
  flex-wrap: wrap;
}
.step-num {
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 600;
  color: var(--inkMute);
  flex-shrink: 0;
}
.step-title {
  font-size: 13.5px;
  font-weight: 550;
  color: var(--ink);
  flex: 1;
  line-height: 1.4;
}
.step-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
.step-page, .step-dur {
  font-family: var(--font-mono);
  font-size: 10px;
  color: var(--inkMute);
}

.step-badges {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.badge-critical {
  font-family: var(--font-mono);
  font-size: 9px;
  font-weight: 600;
  letter-spacing: 0.06em;
  color: var(--red);
  background: var(--redBg);
  padding: 1px 5px;
  border-radius: 2px;
}
.badge-witness {
  font-family: var(--font-mono);
  font-size: 9px;
  font-weight: 600;
  color: var(--inkSoft);
  background: var(--ruleSoft);
  padding: 1px 5px;
  border-radius: 2px;
}

.step-desc {
  font-size: 12.5px;
  color: var(--inkSoft);
  line-height: 1.55;
}

.strip {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 3px;
  font-size: 12px;
}
.strip-done  { background: var(--tealBg); color: var(--teal); }
.strip-issue { background: var(--amberBg); color: var(--inkSoft); border-left: 3px solid var(--amber); }
.strip-active { background: var(--amberBg); color: var(--inkSoft); border: 1px dashed var(--amber); }

.strip-note {
  display: block;
  font-style: italic;
  margin-top: 3px;
  font-size: 11.5px;
}
.witness-tag {
  font-family: var(--font-mono);
  font-size: 10px;
  opacity: 0.8;
}
.pulse-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--amber);
  flex-shrink: 0;
  margin-top: 3px;
}

.action-row {
  display: flex;
  gap: 8px;
  margin-top: 4px;
}
.btn-validate, .btn-issue {
  flex: 1;
  height: 36px;
  border-radius: 3px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  border: none;
  transition: opacity 0.15s;
}
.btn-validate { background: var(--teal); color: #fff; }
.btn-issue    { background: transparent; color: var(--red); border: 1px solid var(--red); }
.btn-validate:hover { opacity: 0.88; }
.btn-issue:hover    { background: var(--redBg); }
</style>
