import { createRouter, createWebHistory } from 'vue-router'
import { defineComponent, h } from 'vue'
import { useBreakpoint } from '../composables/useBreakpoint.js'

// Desktop views
import DesktopUploadView    from '../views/DesktopUploadView.vue'
import DesktopChecklistView from '../views/DesktopChecklistView.vue'
import DesktopOverviewView  from '../views/DesktopOverviewView.vue'
import SummaryView          from '../views/SummaryView.vue'

// Phase 2 — Wiki Agent (nouvelle vue)
import WikiAgentView from '../views/WikiAgentView.vue'

// Mobile views
import MobileProjectListView from '../views/mobile/MobileProjectListView.vue'
import MobileUploadView      from '../views/mobile/MobileUploadView.vue'
import MobileChecklistView   from '../views/mobile/MobileChecklistView.vue'
import MobileSummaryView     from '../views/mobile/MobileSummaryView.vue'
import MobileOverviewView    from '../views/mobile/MobileOverviewView.vue'

function adaptive(Desktop, Mobile) {
  return defineComponent({
    setup() {
      const { isMobile } = useBreakpoint()
      return () => h(isMobile.value ? Mobile : Desktop)
    }
  })
}

const routes = [
  { path: '/',                         component: adaptive(DesktopUploadView, MobileProjectListView) },
  { path: '/upload',                   component: adaptive(DesktopUploadView, MobileUploadView) },
  { path: '/project/:id',              component: adaptive(DesktopChecklistView, MobileChecklistView) },
  { path: '/project/:id/overview',     component: adaptive(DesktopOverviewView, MobileOverviewView) },
  { path: '/project/:id/summary',      component: adaptive(SummaryView, MobileSummaryView) },
  // Phase 2 — Wiki Agent (remplace l'ancienne Phase2IngestView)
  { path: '/project/:id/wiki-admin',   component: WikiAgentView },
  { path: '/project/:id/wiki-agent',   component: WikiAgentView },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
