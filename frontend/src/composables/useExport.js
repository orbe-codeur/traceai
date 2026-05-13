export function useExport() {
  function exportPV(project, steps) {
    const done   = steps.filter(s => s.status === 'done')
    const issues = steps.filter(s => s.status === 'issue')
    const techs  = [...new Set(steps.map(s => s.technician_name).filter(Boolean))]

    const rows = steps
      .filter(s => s.status !== 'pending')
      .sort((a, b) => new Date(a.validated_at || 0) - new Date(b.validated_at || 0))
      .map(s => {
        const statusLabel = s.status === 'done' ? '✓ Validé' : s.status === 'issue' ? '⚠ Problème' : '⟳ En cours'
        const statusColor = s.status === 'done' ? '#1F5F5B' : s.status === 'issue' ? '#E89A2D' : '#56524A'
        const time = s.validated_at ? new Date(s.validated_at).toLocaleString('fr-FR') : '—'
        return `
          <tr>
            <td style="font-family:monospace;font-size:12px;color:#8A8478;padding:8px 10px;">${String(s.step_number).padStart(2,'0')}</td>
            <td style="padding:8px 10px;font-size:13px;">${s.title}</td>
            <td style="padding:8px 10px;font-size:12px;color:#56524A;">${s.category}</td>
            <td style="padding:8px 10px;">
              <span style="color:${statusColor};font-weight:600;font-size:12px;">${statusLabel}</span>
            </td>
            <td style="padding:8px 10px;font-size:12px;color:#56524A;">${s.technician_name || '—'}</td>
            <td style="padding:8px 10px;font-size:12px;color:#56524A;">${s.witness_name || '—'}</td>
            <td style="padding:8px 10px;font-family:monospace;font-size:11px;color:#8A8478;">${time}</td>
            <td style="padding:8px 10px;font-size:12px;color:#56524A;font-style:italic;">${s.note || ''}</td>
          </tr>`
      }).join('')

    const html = `<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8"/>
<title>PV — ${project.name}</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Helvetica Neue', Arial, sans-serif; background: #fff; color: #161513; padding: 40px; }
  h1 { font-size: 24px; font-weight: 700; letter-spacing: -0.02em; margin-bottom: 4px; }
  .meta { font-size: 12px; color: #8A8478; font-family: monospace; margin-bottom: 28px; }
  .stats { display: flex; gap: 32px; margin-bottom: 28px; padding: 16px 20px; background: #F4F0E8; border-radius: 4px; }
  .stat-num { font-size: 22px; font-weight: 700; font-family: monospace; }
  .stat-label { font-size: 10px; text-transform: uppercase; letter-spacing: 0.08em; color: #8A8478; margin-top: 2px; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  th { text-align: left; padding: 8px 10px; font-size: 10px; text-transform: uppercase; letter-spacing: 0.06em; color: #8A8478; border-bottom: 2px solid #D9D2C2; font-family: monospace; }
  tr:nth-child(even) { background: #F4F0E8; }
  tr:last-child td { border-bottom: none; }
  td { border-bottom: 1px solid #E8E2D4; vertical-align: top; }
  .footer { margin-top: 40px; padding-top: 16px; border-top: 1px solid #D9D2C2; font-size: 11px; color: #8A8478; display: flex; justify-content: space-between; }
  @media print { body { padding: 20px; } }
</style>
</head>
<body>
  <h1>${project.name}</h1>
  <div class="meta">${project.pdf_filename} · Généré le ${new Date().toLocaleDateString('fr-FR', { day:'numeric', month:'long', year:'numeric' })}</div>

  <div class="stats">
    <div><div class="stat-num" style="color:#1F5F5B">${done.length}/${steps.length}</div><div class="stat-label">Étapes validées</div></div>
    <div><div class="stat-num" style="color:${issues.length > 0 ? '#E89A2D' : '#8A8478'}">${issues.length}</div><div class="stat-label">Problèmes</div></div>
    <div><div class="stat-num">${techs.length}</div><div class="stat-label">Techniciens</div></div>
    <div style="margin-left:auto;text-align:right;"><div class="stat-label">Équipe</div><div style="font-size:13px;margin-top:4px;">${techs.join(', ') || '—'}</div></div>
  </div>

  <table>
    <thead>
      <tr>
        <th>#</th><th>Étape</th><th>Catégorie</th><th>Statut</th>
        <th>Technicien</th><th>Témoin</th><th>Horodatage</th><th>Note</th>
      </tr>
    </thead>
    <tbody>${rows}</tbody>
  </table>

  <div class="footer">
    <span>TraceAI — Procès-verbal d'installation</span>
    <span>${project.name}</span>
  </div>
</body>
</html>`

    const win = window.open('', '_blank')
    win.document.write(html)
    win.document.close()
    win.focus()
    setTimeout(() => win.print(), 400)
  }

  return { exportPV }
}
