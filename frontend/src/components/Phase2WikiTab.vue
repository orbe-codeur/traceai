<template>
  <div class="wiki-wrap">
    <div class="wiki-sidebar">
      <div class="wiki-sidebar-head">
        <span class="wiki-mono wiki-mute" style="font-size:10px;letter-spacing:.18em;text-transform:uppercase">Machine Wiki</span>
      </div>
      <div v-if="!pages.length" class="wiki-empty">
        <span class="wiki-mono wiki-mute" style="font-size:12px">Aucune page wiki générée</span>
      </div>
      <button v-for="p in pages" :key="p.id"
        class="wiki-page-btn" :class="{ active: selected?.id === p.id }"
        @click="loadPage(p.id)">
        <span class="wiki-page-icon">📄</span>
        <span class="wiki-page-name">{{ p.title }}</span>
        <span v-if="hasAlerts(p)" class="wiki-warn-dot" title="Contradictions ou lacunes">⚠️</span>
      </button>
    </div>

    <div class="wiki-content">
      <div v-if="!selected" class="wiki-placeholder">
        <div style="font-size:48px;margin-bottom:16px">📚</div>
        <div style="font-size:18px;font-weight:600;margin-bottom:8px">Machine Wiki</div>
        <div class="wiki-mono wiki-mute" style="font-size:13px">Sélectionne une machine dans le panneau de gauche</div>
      </div>

      <template v-else>
        <div class="wiki-content-head">
          <h1 class="wiki-title">{{ selected.title }}</h1>
          <div class="wiki-meta">
            <span class="wiki-mono wiki-mute" style="font-size:11px">
              Compilé {{ formatDate(selected.last_compiled_at) }}
            </span>
          </div>
        </div>

        <!-- Contradictions banner -->
        <div v-if="contradictions.length" class="wiki-banner wiki-banner-warn">
          <strong>⚠️ {{ contradictions.length }} contradiction{{ contradictions.length > 1 ? 's' : '' }} détectée{{ contradictions.length > 1 ? 's' : '' }}</strong>
          <div v-for="(c, i) in contradictions" :key="i" class="wiki-contradiction">
            <span class="wiki-mono" style="font-size:10px">{{ c.topic }}</span> —
            {{ c.src_a }} : <strong>{{ c.val_a }}</strong> vs {{ c.src_b }} : <strong>{{ c.val_b }}</strong>
          </div>
        </div>

        <!-- Lacunes banner -->
        <div v-if="gaps.length" class="wiki-banner wiki-banner-info">
          <strong>❓ {{ gaps.length }} lacune{{ gaps.length > 1 ? 's' : '' }} identifiée{{ gaps.length > 1 ? 's' : '' }}</strong>
          <ul style="margin:6px 0 0;padding-left:16px">
            <li v-for="(g, i) in gaps" :key="i" style="font-size:13px">{{ g }}</li>
          </ul>
        </div>

        <!-- Markdown content -->
        <div class="wiki-md" v-html="renderedMd"/>
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import api from '../services/api.js'

const props = defineProps({ projectId: { type: Number, required: true } })

const pages = ref([])
const selected = ref(null)

const contradictions = computed(() => selected.value?.contradictions || [])
const gaps = computed(() => selected.value?.gaps || [])

function hasAlerts(p) {
  return (p.contradictions_count > 0) || (p.gaps_count > 0)
}

function formatDate(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString('fr-FR', { day:'2-digit', month:'short', hour:'2-digit', minute:'2-digit' })
}

// Simple Markdown renderer (headers, bold, links, wikilinks, lists, tables)
const renderedMd = computed(() => {
  if (!selected.value?.content_md) return ''
  let md = selected.value.content_md

  // Wikilinks [[Machine]] → links
  md = md.replace(/\[\[([^\]]+)\]\]/g, '<a class="wiki-link">$1</a>')
  // Headers
  md = md.replace(/^### (.+)$/gm, '<h3>$1</h3>')
  md = md.replace(/^## (.+)$/gm, '<h2>$1</h2>')
  md = md.replace(/^# (.+)$/gm, '<h1>$1</h1>')
  // Bold
  md = md.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  // Italic
  md = md.replace(/\*(.+?)\*/g, '<em>$1</em>')
  // Citations [source]
  md = md.replace(/\[([^\]]+)\]/g, '<cite>[$1]</cite>')
  // Lists
  md = md.replace(/^- (.+)$/gm, '<li>$1</li>')
  md = md.replace(/(<li>.*<\/li>(\n|$))+/g, '<ul>$&</ul>')
  // Paragraphs (double newline)
  md = md.split('\n\n').map(p => {
    if (p.trim().startsWith('<h') || p.trim().startsWith('<ul') || p.trim().startsWith('<li')) return p
    return `<p>${p.trim()}</p>`
  }).join('\n')

  return md
})

async function loadPage(id) {
  try {
    const res = await api.getWikiPage(id)
    selected.value = res.data
  } catch (e) { /* ignore */ }
}

onMounted(async () => {
  try {
    const res = await api.getWikiIndex(props.projectId)
    pages.value = res.data.filter(p => p.page_type === 'machine')
    if (pages.value.length) loadPage(pages.value[0].id)
  } catch (e) { /* ignore */ }
})
</script>

<style scoped>
.wiki-wrap { display:flex; height:100%; }
.wiki-sidebar { width:240px; border-right:1px solid #EAE7DD; padding:16px 12px; flex-shrink:0; overflow:auto; }
.wiki-sidebar-head { padding:0 4px 12px; border-bottom:1px solid #EAE7DD; margin-bottom:8px; }
.wiki-empty { padding:20px 8px; text-align:center; }
.wiki-page-btn { width:100%; display:flex; align-items:center; gap:8px; padding:8px 10px; border:none; background:transparent; cursor:pointer; border-radius:4px; text-align:left; font-family:inherit; font-size:13px; color:#0E0E0C; }
.wiki-page-btn:hover { background:#F2EFE6; }
.wiki-page-btn.active { background:#EAE7DD; font-weight:600; }
.wiki-page-icon { font-size:14px; flex-shrink:0; }
.wiki-page-name { flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.wiki-warn-dot { flex-shrink:0; }
.wiki-content { flex:1; padding:32px 40px; overflow:auto; }
.wiki-placeholder { display:flex; flex-direction:column; align-items:center; justify-content:center; height:100%; color:#7C7B73; text-align:center; }
.wiki-content-head { margin-bottom:24px; border-bottom:1px solid #EAE7DD; padding-bottom:16px; }
.wiki-title { margin:0 0 8px; font-size:28px; font-weight:700; letter-spacing:-.02em; }
.wiki-meta { display:flex; gap:12px; }
.wiki-banner { padding:12px 16px; border-radius:4px; margin-bottom:16px; font-size:13.5px; }
.wiki-banner-warn { background:#FBE9C7; border:1px solid #E89A2D55; border-left:3px solid #E89A2D; }
.wiki-banner-info { background:#EDF5F2; border:1px solid #1F6B5E44; border-left:3px solid #1F6B5E; }
.wiki-contradiction { margin-top:6px; font-size:12.5px; color:#0E0E0C; }
.wiki-md :deep(h1) { font-size:22px; font-weight:700; margin:24px 0 8px; border-bottom:1px solid #EAE7DD; padding-bottom:6px; }
.wiki-md :deep(h2) { font-size:18px; font-weight:600; margin:20px 0 6px; }
.wiki-md :deep(h3) { font-size:15px; font-weight:600; margin:16px 0 4px; color:#3D3D38; }
.wiki-md :deep(p) { margin:8px 0; font-size:14px; line-height:1.65; color:#0E0E0C; }
.wiki-md :deep(ul) { margin:8px 0; padding-left:20px; }
.wiki-md :deep(li) { font-size:14px; line-height:1.6; margin:2px 0; }
.wiki-md :deep(strong) { font-weight:700; color:#0E0E0C; }
.wiki-md :deep(cite) { font-family:'Geist Mono',monospace; font-size:11px; color:#7C7B73; font-style:normal; }
.wiki-md :deep(.wiki-link) { color:#1F6B5E; text-decoration:underline; cursor:pointer; font-weight:600; }
.wiki-mono { font-family:'Geist Mono',monospace; }
.wiki-mute { color:#7C7B73; }
</style>
