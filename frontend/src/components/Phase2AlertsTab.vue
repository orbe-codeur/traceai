<template>
  <div class="alerts-wrap">
    <div class="alerts-head">
      <h2 class="alerts-title">Alertes proactives</h2>
      <span class="alerts-mono alerts-mute" style="font-size:11px">Générées par l'agent Alertes · {{ alerts.length }} active{{ alerts.length !== 1 ? 's' : '' }}</span>
    </div>

    <div v-if="!alerts.length" class="alerts-empty">
      <div style="font-size:40px;margin-bottom:12px">✅</div>
      <div style="font-size:16px;font-weight:600;margin-bottom:6px">Aucune alerte active</div>
      <div class="alerts-mono alerts-mute" style="font-size:13px">Le Machine Wiki ne signale pas de problème critique.</div>
    </div>

    <div v-else class="alerts-list">
      <div v-for="alert in alerts" :key="alert.id" class="alert-card" :class="alert.severity">
        <div class="alert-left">
          <span class="alert-icon">{{ severityIcon(alert.severity) }}</span>
        </div>
        <div class="alert-body">
          <div class="alert-header">
            <span class="alerts-mono" style="font-size:10px;font-weight:700;letter-spacing:.16em;text-transform:uppercase" :style="{ color: severityColor(alert.severity) }">
              {{ alert.alert_type?.replace('_', ' ') || alert.severity }}
            </span>
            <span v-if="alert.machine_ref" class="alerts-mono" style="font-size:10px;color:#7C7B73">
              · {{ alert.machine_ref }}
            </span>
            <span class="alerts-mono alerts-mute" style="font-size:10px;margin-left:auto">
              {{ formatDate(alert.created_at) }}
            </span>
          </div>
          <div class="alert-msg">{{ alert.message }}</div>
        </div>
        <button class="alert-dismiss" @click="dismiss(alert.id)" title="Ignorer">✕</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../services/api.js'

const props = defineProps({
  projectId: { type: Number, required: true },
  count: { type: Number, default: 0 },
})
const emit = defineEmits(['dismissed'])

const alerts = ref([])

function severityIcon(s) {
  return s === 'critical' ? '🔴' : s === 'warning' ? '🟡' : 'ℹ️'
}
function severityColor(s) {
  return s === 'critical' ? '#C8482D' : s === 'warning' ? '#E89A2D' : '#2E5C9E'
}
function formatDate(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString('fr-FR', { day:'2-digit', month:'short', hour:'2-digit', minute:'2-digit' })
}

async function dismiss(id) {
  try {
    await api.dismissAlert(id)
    alerts.value = alerts.value.filter(a => a.id !== id)
    emit('dismissed')
  } catch (e) { /* ignore */ }
}

onMounted(async () => {
  try {
    const res = await api.getAlerts(props.projectId)
    alerts.value = res.data
  } catch (e) { /* ignore */ }
})
</script>

<style scoped>
.alerts-wrap { padding:32px 40px; }
.alerts-head { margin-bottom:24px; }
.alerts-title { margin:0 0 4px; font-size:24px; font-weight:700; }
.alerts-list { display:flex; flex-direction:column; gap:10px; }
.alert-card { display:flex; align-items:flex-start; gap:14px; padding:14px 16px; background:#fff; border:1px solid #EAE7DD; border-radius:4px; }
.alert-card.critical { border-left:3px solid #C8482D; background:#FDF5F4; }
.alert-card.warning { border-left:3px solid #E89A2D; background:#FFF8EB; }
.alert-card.info { border-left:3px solid #2E5C9E; background:#EEF2FA; }
.alert-left { flex-shrink:0; font-size:20px; }
.alert-body { flex:1; min-width:0; }
.alert-header { display:flex; align-items:center; gap:6px; margin-bottom:6px; }
.alert-msg { font-size:13.5px; color:#0E0E0C; line-height:1.5; }
.alert-dismiss { flex-shrink:0; width:24px; height:24px; border:none; background:transparent; cursor:pointer; color:#7C7B73; border-radius:3px; font-size:12px; display:flex; align-items:center; justify-content:center; }
.alert-dismiss:hover { background:#F2EFE6; }
.alerts-empty { display:flex; flex-direction:column; align-items:center; justify-content:center; padding:60px; text-align:center; }
.alerts-mono { font-family:'Geist Mono',monospace; }
.alerts-mute { color:#7C7B73; }
</style>
