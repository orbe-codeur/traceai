<script setup>
import { useToast } from '../composables/useToast.js'
const { toasts, dismiss } = useToast()
</script>

<template>
  <Teleport to="body">
    <div class="toast-container">
      <TransitionGroup name="toast">
        <div
          v-for="t in toasts"
          :key="t.id"
          class="toast"
          :class="`toast-${t.type}`"
          @click="dismiss(t.id)"
        >
          <span class="toast-icon">
            {{ t.type === 'success' ? '✓' : t.type === 'error' ? '✕' : t.type === 'warn' ? '⚠' : 'ℹ' }}
          </span>
          <span class="toast-msg">{{ t.message }}</span>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<style scoped>
.toast-container {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: 8px;
  pointer-events: none;
}

.toast {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px 16px;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 500;
  font-family: var(--font-sans);
  box-shadow: 0 4px 16px rgba(0,0,0,0.18);
  cursor: pointer;
  pointer-events: all;
  max-width: 360px;
  line-height: 1.4;
}

.toast-success { background: var(--teal);   color: #fff; }
.toast-error   { background: var(--red);    color: #fff; }
.toast-warn    { background: var(--amber);  color: var(--ink); }
.toast-info    { background: var(--ink);    color: var(--paper); }

.toast-icon {
  font-size: 14px;
  flex-shrink: 0;
  width: 18px;
  text-align: center;
}

/* Transitions */
.toast-enter-active { transition: all 0.22s ease; }
.toast-leave-active { transition: all 0.18s ease; }
.toast-enter-from   { opacity: 0; transform: translateX(40px); }
.toast-leave-to     { opacity: 0; transform: translateX(40px); }
</style>
