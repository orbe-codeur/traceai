import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 120000,
})

export default {
  uploadProject: (name, file) => {
    const form = new FormData()
    form.append('name', name)
    form.append('file', file)
    return api.post('/upload', form)
  },
  getProjects: () => api.get('/projects'),
  getSteps: (projectId) => api.get(`/projects/${projectId}/steps`),
  validateStep: (stepId, data) => api.post(`/steps/${stepId}/validate`, data),
  getTimeline: (projectId) => api.get(`/projects/${projectId}/timeline`),
  getPdfPage:     (projectId, page) => `/api/projects/${projectId}/pdf/${page}`,
  deleteProject:  (projectId) => api.delete(`/projects/${projectId}`),
  chat: (projectId, message, stepContext) => api.post(`/projects/${projectId}/chat`, {
    message,
    step_context: stepContext || null,
  }),
}
