<template>
  <div class="waa-root">

    <!-- ─── Section Alertes ──────────────────────────────────────────────── -->
    <section class="waa-section">
      <div class="waa-section-head">
        <h2 class="waa-section-title">Alertes actives</h2>
        <span class="waa-mono waa-mute" style="font-size:11px">
          {{ alerts.length }} alerte{{ alerts.length !== 1 ? 's' : '' }} active{{ alerts.length !== 1 ? 's' : '' }}
        </span>
      </div>

      <div v-if="!alerts.length" class="waa-empty">
        <div style="font-size:36px;margin-bottom:10px">✅</div>
        <div style="font-size:16px;font-weight:600;margin-bottom:6px">Aucune alerte active</div>
        <div class="waa-mono waa-mute" style="font-size:13px">Votre wiki est cohérent — aucun problème détecté.</div>
      </div>

      <div v-else class="waa-alerts-list">
        <div v-for="alert in alerts" :key="alert.id" class="waa-alert-card" :class="severityClass(alert.severity)">
          <span class="waa-alert-sev">{{ severityIcon(alert.severity) }}</span>
          <div class="waa-alert-body">
            <div class="waa-alert-header">
              <span class="waa-mono" style="font-size:10px;font-weight:700;letter-spacing:.14em;text-transform:uppercase"
                :style="{ color: severityColor(alert.severity) }">
                {{ alert.alert_type?.replace('_', ' ') || alert.severity }}
              </span>
              <span v-if="alert.machine_ref" class="waa-mono waa-mute" style="font-size:10px"> · {{ alert.machine_ref }}</span>
              <span class="waa-mono waa-mute" style="font-size:10px;margin-left:auto">{{ formatDate(alert.created_at) }}</span>
            </div>
            <div class="waa-alert-title">{{ alert.title || alert.message }}</div>
            <div v-if="alert.description && alert.description !== alert.title" class="waa-alert-desc">{{ alert.description }}</div>
          </div>
          <button class="waa-dismiss" @click="dismiss(alert.id)" title="Ignorer">✕</button>
        </div>
      </div>
    </section>

    <!-- ─── Section Cron ─────────────────────────────────────────────────── -->
    <section class="waa-section waa-section--cron">
      <div class="waa-section-head">
        <h2 class="waa-section-title">Jobs planifiés</h2>
        <button class="waa-btn-new" @click="openModal">+ Nouveau job</button>
      </div>

      <div v-if="!cronJobs.length" class="waa-empty waa-empty--sm">
        <div class="waa-mono waa-mute" style="font-size:13px">Aucun job planifié. L'agent peut analyser votre wiki en arrière-plan.</div>
      </div>

      <div v-else class="waa-cron-list">
        <div v-for="job in cronJobs" :key="job.id" class="waa-cron-card">
          <div class="waa-cron-info">
            <div class="waa-cron-name-row">
              <span class="waa-cron-name">{{ job.name }}</span>
              <span class="waa-mode-badge" :class="'mode-'+job.mode">{{ job.mode }}</span>
              <span v-if="!job.enabled" class="waa-paused-badge waa-mono">En pause</span>
            </div>
            <div class="waa-cron-meta waa-mono waa-mute">
              {{ job.schedule?.display || '–' }}
              <span v-if="job.next_run_at"> · Prochain run : {{ formatDate(job.next_run_at) }}</span>
            </div>
            <div v-if="job.last_output" class="waa-cron-output">{{ job.last_output.slice(0,120) }}{{ job.last_output.length > 120 ? '…' : '' }}</div>
          </div>
          <div class="waa-cron-actions">
            <button class="waa-cron-btn" @click="trigger(job.id)" title="Lancer maintenant">▶</button>
            <button class="waa-cron-btn" @click="togglePause(job)" :title="job.enabled ? 'Mettre en pause' : 'Réactiver'">
              {{ job.enabled ? '⏸' : '▶▶' }}
            </button>
            <button class="waa-cron-btn waa-cron-btn--del" @click="confirmDelete(job)" title="Supprimer">🗑</button>
          </div>
        </div>
      </div>
    </section>

    <!-- ─── Modal création cron ──────────────────────────────────────────── -->
    <Teleport to="body">
      <div v-if="showModal" class="waa-modal-backdrop" @click.self="closeModal">
        <div class="waa-modal">
          <div class="waa-modal-head">
            <h3 class="waa-modal-title">Nouveau job planifié</h3>
            <button class="waa-modal-close" @click="closeModal">✕</button>
          </div>

          <div class="waa-modal-body">
            <div class="waa-field">
              <label class="waa-label">Nom du job</label>
              <input v-model="form.name" class="waa-input" placeholder="ex: Vérification hebdomadaire contradictions" />
            </div>

            <div class="waa-field">
              <label class="waa-label">Mode</label>
              <div class="waa-mode-btns">
                <button v-for="m in MODES" :key="m.value"
                  :class="['waa-mode-btn', { active: form.mode === m.value }]"
                  @click="form.mode = m.value">
                  {{ m.label }}
                </button>
              </div>
            </div>

            <div class="waa-field">
              <label class="waa-label">Instruction pour l'agent</label>
              <textarea v-model="form.prompt" class="waa-textarea" rows="4"
                placeholder="ex: Cherche les contradictions dans le wiki et crée une alerte si tu en trouves." />
              <span class="waa-mono waa-mute" style="font-size:11px">L'agent exécutera cette instruction de façon autonome.</span>
            </div>

            <div class="waa-field">
              <label class="waa-label">Fréquence</label>
              <div class="waa-freq-btns">
                <button v-for="f in FREQUENCIES" :key="f.value"
                  :class="['waa-freq-btn', { active: form.schedulePreset === f.value }]"
                  @click="selectFreq(f.value)">
                  {{ f.label }}
                </button>
              </div>
              <input v-if="form.schedulePreset === 'custom'" v-model="form.customSchedule"
                class="waa-input" style="margin-top:8px"
                placeholder="ex: every 30 minutes · every 2 hours · 0 9 * * 1" />
            </div>

            <div v-if="formError" class="waa-form-error">{{ formError }}</div>
          </div>

          <div class="waa-modal-foot">
            <button class="waa-btn-ghost" @click="closeModal">Annuler</button>
            <button class="waa-btn-primary" :disabled="submitting || !form.name || !form.prompt"
              @click="submitJob">
              {{ submitting ? 'Création…' : 'Créer le job' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- ─── Modal confirmation suppression ──────────────────────────────── -->
    <Teleport to="body">
      <div v-if="deleteTarget" class="waa-modal-backdrop" @click.self="deleteTarget = null">
        <div class="waa-modal waa-modal--sm">
          <div class="waa-modal-head">
            <h3 class="waa-modal-title">Supprimer ce job ?</h3>
            <button class="waa-modal-close" @click="deleteTarget = null">✕</button>
          </div>
          <div class="waa-modal-body">
            <p style="font-size:14px;color:var(--inkSoft)">
              Le job <strong>{{ deleteTarget.name }}</strong> sera supprimé définitivement.
            </p>
          </div>
          <div class="waa-modal-foot">
            <button class="waa-btn-ghost" @click="deleteTarget = null">Annuler</button>
            <button class="waa-btn-danger" @click="doDelete">Supprimer</button>
          </div>
        </div>
      </div>
    </Teleport>

  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../services/api.js'
import { useToast } from '../composables/useToast.js'

const props = defineProps({ projectId: { type: Number, required: true } })
const emit = defineEmits(['update-count'])
const { success, error: toastError, warn } = useToast()

// ── État ──────────────────────────────────────────────────────────────────────
const alerts = ref([])
const cronJobs = ref([])
const showModal = ref(false)
const submitting = ref(false)
const formError = ref('')
const deleteTarget = ref(null)

const form = ref({
  name: '',
  mode: 'alerte',
  prompt: '',
  schedulePreset: 'every night',
  customSchedule: '',
})

const MODES = [
  { value: 'alerte',    label: '🔔 Alerte' },
  { value: 'chat',      label: '💬 Analyse' },
  { value: 'ingestion', label: '📥 Ingestion' },
]

const FREQUENCIES = [
  { value: 'every night',  label: 'Toutes les nuits' },
  { value: 'every week',   label: 'Hebdomadaire' },
  { value: 'every hour',   label: 'Toutes les heures' },
  { value: 'custom',       label: 'Personnalisé' },
]

// ── Alertes ───────────────────────────────────────────────────────────────────
function severityIcon(s) {
  return s === 'critical' ? '🔴' : s === 'high' ? '🟠' : s === 'medium' ? '🟡' : 'ℹ️'
}
function severityColor(s) {
  return s === 'critical' ? 'var(--red)' : s === 'high' ? '#D4691A' : s === 'medium' ? 'var(--amber)' : 'var(--blue)'
}
function severityClass(s) {
  return `sev-${s || 'info'}`
}
function formatDate(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString('fr-FR', { day:'2-digit', month:'short', hour:'2-digit', minute:'2-digit' })
}

async function dismiss(id) {
  try {
    await api.dismissAlert(id)
    alerts.value = alerts.value.filter(a => a.id !== id)
    emit('update-count', alerts.value.length)
  } catch { /* ignore */ }
}

async function loadAlerts() {
  try {
    const res = await api.getAlerts(props.projectId)
    alerts.value = res.data || []
    emit('update-count', alerts.value.length)
  } catch { /* ignore */ }
}

// ── Cron ──────────────────────────────────────────────────────────────────────
async function loadCron() {
  try {
    const res = await api.getCronJobs(props.projectId)
    cronJobs.value = res.data || []
  } catch { /* ignore */ }
}

async function trigger(jobId) {
  try {
    await api.triggerCronJob(jobId)
    success('Job lancé.')
    setTimeout(loadCron, 2000)
  } catch { toastError('Impossible de déclencher le job.') }
}

async function togglePause(job) {
  try {
    if (job.enabled) {
      await api.pauseCronJob(job.id)
      warn(`Job "${job.name}" mis en pause.`)
    } else {
      await api.resumeCronJob(job.id)
      success(`Job "${job.name}" réactivé.`)
    }
    await loadCron()
  } catch { toastError('Impossible de modifier le job.') }
}

function confirmDelete(job) {
  deleteTarget.value = job
}

async function doDelete() {
  if (!deleteTarget.value) return
  try {
    await api.deleteCronJob(deleteTarget.value.id)
    success(`Job "${deleteTarget.value.name}" supprimé.`)
    deleteTarget.value = null
    await loadCron()
  } catch { toastError('Impossible de supprimer le job.') }
}

// ── Modal ─────────────────────────────────────────────────────────────────────
function openModal() {
  form.value = { name: '', mode: 'alerte', prompt: '', schedulePreset: 'every night', customSchedule: '' }
  formError.value = ''
  showModal.value = true
}

function closeModal() {
  showModal.value = false
}

function selectFreq(val) {
  form.value.schedulePreset = val
}

async function submitJob() {
  formError.value = ''
  if (!form.value.name.trim() || !form.value.prompt.trim()) return

  const schedule = form.value.schedulePreset === 'custom'
    ? form.value.customSchedule.trim()
    : form.value.schedulePreset

  if (!schedule) { formError.value = 'Veuillez préciser la fréquence.'; return }

  submitting.value = true
  try {
    await api.createCronJob(props.projectId, {
      name: form.value.name.trim(),
      mode: form.value.mode,
      prompt: form.value.prompt.trim(),
      schedule,
    })
    success(`Job "${form.value.name}" créé.`)
    closeModal()
    await loadCron()
  } catch (e) {
    const detail = e.response?.data?.detail
    formError.value = detail || 'Erreur lors de la création du job.'
  } finally {
    submitting.value = false
  }
}

// ── Mount ─────────────────────────────────────────────────────────────────────
onMounted(() => Promise.all([loadAlerts(), loadCron()]))
</script>

<style scoped>
.waa-root {
  padding: 28px 36px;
  overflow-y: auto;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 32px;
}

/* ─── Section ──────────────────────────────────────────────────────────────── */
.waa-section { }
.waa-section--cron { }
.waa-section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.waa-section-title { font-size: 18px; font-weight: 700; margin: 0; }

/* ─── Alertes ──────────────────────────────────────────────────────────────── */
.waa-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 32px;
  background: var(--paperAlt);
  border: 1px solid var(--rule);
  border-radius: 4px;
}
.waa-empty--sm { padding: 20px; }

.waa-alerts-list { display: flex; flex-direction: column; gap: 8px; }
.waa-alert-card {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 16px;
  background: var(--paperAlt);
  border: 1px solid var(--rule);
  border-radius: 4px;
}
.waa-alert-card.sev-critical { background: var(--redBg); border-left: 3px solid var(--red); }
.waa-alert-card.sev-high     { background: #FDF0E8; border-left: 3px solid #D4691A; }
.waa-alert-card.sev-medium   { background: var(--amberBg); border-left: 3px solid var(--amber); }
.waa-alert-card.sev-info     { background: var(--paperAlt); border-left: 3px solid var(--blue); }
.waa-alert-sev { font-size: 18px; flex-shrink: 0; margin-top: 2px; }
.waa-alert-body { flex: 1; min-width: 0; }
.waa-alert-header { display: flex; align-items: center; gap: 6px; margin-bottom: 5px; }
.waa-alert-title { font-size: 13.5px; font-weight: 600; color: var(--ink); line-height: 1.4; }
.waa-alert-desc { font-size: 12.5px; color: var(--inkSoft); line-height: 1.5; margin-top: 4px; }
.waa-dismiss {
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  border: none;
  background: transparent;
  cursor: pointer;
  color: var(--inkMute);
  border-radius: 3px;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.waa-dismiss:hover { background: var(--ruleSoft); color: var(--ink); }

/* ─── Cron list ────────────────────────────────────────────────────────────── */
.waa-cron-list { display: flex; flex-direction: column; gap: 8px; }
.waa-cron-card {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 14px 16px;
  background: var(--paperAlt);
  border: 1px solid var(--rule);
  border-radius: 4px;
}
.waa-cron-info { flex: 1; min-width: 0; }
.waa-cron-name-row { display: flex; align-items: center; gap: 8px; margin-bottom: 5px; flex-wrap: wrap; }
.waa-cron-name { font-size: 14px; font-weight: 600; }
.waa-mode-badge {
  padding: 2px 7px;
  border-radius: 2px;
  font-family: var(--font-mono);
  font-size: 9.5px;
  font-weight: 700;
  letter-spacing: .1em;
  text-transform: uppercase;
}
.mode-alerte    { background: var(--redBg);   color: var(--red); }
.mode-chat      { background: var(--tealBg);  color: var(--teal); }
.mode-ingestion { background: var(--amberBg); color: #A06414; }
.waa-paused-badge {
  padding: 2px 7px;
  background: var(--paper);
  border: 1px solid var(--rule);
  border-radius: 2px;
  font-size: 9.5px;
  font-weight: 600;
  color: var(--inkMute);
  letter-spacing: .1em;
  text-transform: uppercase;
}
.waa-cron-meta { font-size: 11px; margin-bottom: 4px; }
.waa-cron-output {
  font-size: 12px;
  color: var(--inkSoft);
  line-height: 1.45;
  font-style: italic;
}
.waa-cron-actions { display: flex; gap: 6px; flex-shrink: 0; }
.waa-cron-btn {
  width: 30px;
  height: 30px;
  border: 1px solid var(--rule);
  background: var(--paper);
  border-radius: 3px;
  cursor: pointer;
  font-size: 13px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--inkSoft);
}
.waa-cron-btn:hover { background: var(--ruleSoft); }
.waa-cron-btn--del:hover { background: var(--redBg); border-color: var(--red); }

/* ─── Bouton nouveau job ───────────────────────────────────────────────────── */
.waa-btn-new {
  padding: 6px 12px;
  background: var(--ink);
  color: var(--paper);
  border: none;
  border-radius: 3px;
  cursor: pointer;
  font-family: var(--font-sans);
  font-size: 12.5px;
  font-weight: 600;
}
.waa-btn-new:hover { opacity: .88; }

/* ─── Modal ────────────────────────────────────────────────────────────────── */
.waa-modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,.35);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.waa-modal {
  background: var(--paper);
  border: 1px solid var(--rule);
  border-radius: 6px;
  width: 520px;
  max-width: calc(100vw - 40px);
  box-shadow: 0 8px 40px rgba(0,0,0,.18);
  display: flex;
  flex-direction: column;
  max-height: calc(100vh - 80px);
}
.waa-modal--sm { width: 400px; }
.waa-modal-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 20px 14px;
  border-bottom: 1px solid var(--rule);
}
.waa-modal-title { font-size: 16px; font-weight: 700; margin: 0; }
.waa-modal-close {
  width: 24px;
  height: 24px;
  border: none;
  background: transparent;
  cursor: pointer;
  color: var(--inkMute);
  font-size: 14px;
  border-radius: 3px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.waa-modal-close:hover { background: var(--ruleSoft); }
.waa-modal-body { padding: 20px; display: flex; flex-direction: column; gap: 16px; overflow-y: auto; }
.waa-modal-foot {
  padding: 14px 20px;
  border-top: 1px solid var(--rule);
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

/* ─── Formulaire ───────────────────────────────────────────────────────────── */
.waa-field { display: flex; flex-direction: column; gap: 6px; }
.waa-label { font-size: 13px; font-weight: 550; color: var(--ink); }
.waa-input {
  padding: 8px 11px;
  background: var(--paperAlt);
  border: 1px solid var(--rule);
  border-radius: 3px;
  font-family: var(--font-sans);
  font-size: 13.5px;
  color: var(--ink);
  outline: none;
}
.waa-input:focus { border-color: var(--inkMute); }
.waa-textarea {
  padding: 8px 11px;
  background: var(--paperAlt);
  border: 1px solid var(--rule);
  border-radius: 3px;
  font-family: var(--font-sans);
  font-size: 13.5px;
  color: var(--ink);
  outline: none;
  resize: vertical;
  line-height: 1.5;
}
.waa-textarea:focus { border-color: var(--inkMute); }

.waa-mode-btns { display: flex; gap: 8px; }
.waa-mode-btn {
  flex: 1;
  padding: 7px 10px;
  background: var(--paperAlt);
  border: 1px solid var(--rule);
  border-radius: 3px;
  cursor: pointer;
  font-family: var(--font-sans);
  font-size: 12.5px;
  font-weight: 550;
  color: var(--inkSoft);
  text-align: center;
}
.waa-mode-btn:hover { background: var(--ruleSoft); }
.waa-mode-btn.active { background: var(--ink); color: var(--paper); border-color: var(--ink); }

.waa-freq-btns { display: flex; flex-wrap: wrap; gap: 6px; }
.waa-freq-btn {
  padding: 6px 12px;
  background: var(--paperAlt);
  border: 1px solid var(--rule);
  border-radius: 3px;
  cursor: pointer;
  font-family: var(--font-sans);
  font-size: 12.5px;
  font-weight: 550;
  color: var(--inkSoft);
}
.waa-freq-btn:hover { background: var(--ruleSoft); }
.waa-freq-btn.active { background: var(--ink); color: var(--paper); border-color: var(--ink); }

.waa-form-error {
  padding: 8px 12px;
  background: var(--redBg);
  border: 1px solid color-mix(in srgb, var(--red) 30%, transparent);
  border-radius: 3px;
  font-size: 13px;
  color: var(--red);
}

/* ─── Boutons ──────────────────────────────────────────────────────────────── */
.waa-btn-primary {
  padding: 8px 16px;
  background: var(--ink);
  color: var(--paper);
  border: none;
  border-radius: 3px;
  cursor: pointer;
  font-family: var(--font-sans);
  font-size: 13.5px;
  font-weight: 600;
}
.waa-btn-primary:hover:not(:disabled) { opacity: .88; }
.waa-btn-primary:disabled { opacity: .45; cursor: not-allowed; }
.waa-btn-ghost {
  padding: 8px 14px;
  background: transparent;
  border: 1px solid var(--rule);
  border-radius: 3px;
  cursor: pointer;
  font-family: var(--font-sans);
  font-size: 13.5px;
  font-weight: 550;
  color: var(--inkSoft);
}
.waa-btn-ghost:hover { background: var(--ruleSoft); }
.waa-btn-danger {
  padding: 8px 16px;
  background: var(--red);
  color: #fff;
  border: none;
  border-radius: 3px;
  cursor: pointer;
  font-family: var(--font-sans);
  font-size: 13.5px;
  font-weight: 600;
}
.waa-btn-danger:hover { opacity: .88; }

/* ─── Utilitaires ──────────────────────────────────────────────────────────── */
.waa-mono { font-family: var(--font-mono); }
.waa-mute { color: var(--inkMute); }
</style>
