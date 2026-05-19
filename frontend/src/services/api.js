import axios from 'axios'

const http = axios.create({
  baseURL: '/api',
  timeout: 120000,
})

export default {
  // V1
  uploadProject: (name, file) => {
    const form = new FormData()
    form.append('name', name)
    form.append('file', file)
    return http.post('/upload', form)
  },
  getProjects:   () => http.get('/projects'),
  getSteps:      (projectId) => http.get(`/projects/${projectId}/steps`),
  validateStep:  (stepId, data) => http.post(`/steps/${stepId}/validate`, data),
  getTimeline:   (projectId) => http.get(`/projects/${projectId}/timeline`),
  getPdfPage:    (projectId, page) => `/api/projects/${projectId}/pdf/${page}`,
  deleteProject: (projectId) => http.delete(`/projects/${projectId}`),
  chat:          (projectId, message, stepContext) => http.post(`/projects/${projectId}/chat`, { message, step_context: stepContext || null }),

  // Phase 2 — accès direct à l'instance axios
  get:   (...args) => http.get(...args),
  post:  (...args) => http.post(...args),
  patch: (...args) => http.patch(...args),
  delete: (...args) => http.delete(...args),

  // Phase 2 — méthodes nommées
  ingest:           (projectId, formData) => http.post(`/projects/${projectId}/ingest`, formData, { headers: { 'Content-Type': 'multipart/form-data' }, timeout: 600000 }),
  getJobStatus:     (jobId) => http.get(`/jobs/${jobId}/status`),
  cancelJob:        (jobId) => http.patch(`/jobs/${jobId}/cancel`),
  getDocuments:     (projectId) => http.get(`/projects/${projectId}/documents`),
  getWikiIndex:     (projectId) => http.get(`/projects/${projectId}/wiki`),
  getWikiPage:      (wikiId) => http.get(`/wiki/${wikiId}`),
  wikiChat:         (projectId, message, conversationId) => http.post(`/projects/${projectId}/wiki-chat`, { message, conversation_id: conversationId || null }),
  getConversations: (projectId) => http.get(`/projects/${projectId}/conversations`),
  getMessages:      (convId) => http.get(`/conversations/${convId}/messages`),
  getAlerts:        (projectId) => http.get(`/projects/${projectId}/alerts`),
  dismissAlert:     (alertId) => http.patch(`/alerts/${alertId}/dismiss`),

  // Phase B — Agent autonome
  agentChat:           (projectId, data) => http.post(`/projects/${projectId}/agent-chat`, data),
  getAgentChatHistory: (projectId, limit = 40) => http.get(`/projects/${projectId}/agent-chat/history`, { params: { limit } }),
  getMemory:           (projectId) => http.get(`/projects/${projectId}/memory`),
  getSkills:           (projectId) => http.get(`/projects/${projectId}/skills`),

  // Phase B — Wiki LLM
  wikiIngestLLM:   (projectId, data) => http.post(`/projects/${projectId}/wiki-ingest`, data),
  wikiHealth:      (projectId) => http.get(`/projects/${projectId}/wiki-health`),
  wikiLint:        (projectId) => http.get(`/projects/${projectId}/wiki-lint`),
  wikiOverview:    (projectId) => http.get(`/projects/${projectId}/wiki-overview`),
  wikiHeal:        (projectId) => http.post(`/projects/${projectId}/wiki-heal`),

  // Phase B — Knowledge Graph
  buildGraph:      (projectId) => http.post(`/projects/${projectId}/build-graph`),
  getGraph:        (projectId) => http.get(`/projects/${projectId}/graph`),
  graphHtmlUrl:    (projectId) => `/api/projects/${projectId}/graph.html`,

  // Phase B+ — Cron
  getCronJobs:     (projectId) => http.get(`/projects/${projectId}/cron`),
  createCronJob:   (projectId, data) => http.post(`/projects/${projectId}/cron`, data),
  deleteCronJob:   (jobId) => http.delete(`/cron/${jobId}`),
  pauseCronJob:    (jobId) => http.post(`/cron/${jobId}/pause`),
  resumeCronJob:   (jobId) => http.post(`/cron/${jobId}/resume`),
  triggerCronJob:  (jobId) => http.post(`/cron/${jobId}/trigger`),
}
