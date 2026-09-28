import React, { useState } from 'react'
import { Modal } from './ui'

// 自定义表头列（显隐），localStorage 持久化
export function useColumnConfig(cols, storageKey) {
  const [hidden, setHidden] = useState(() => {
    try { return JSON.parse(localStorage.getItem(storageKey) || '[]') } catch { return [] }
  })
  const [open, setOpen] = useState(false)

  const visible = cols.filter(c => !hidden.includes(c.k))
  const picker = open ? (
    <Modal title="自定义表头列" onClose={() => setOpen(false)}>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 6 }}>
        {cols.map(c => (
          <label key={c.k} style={{ fontSize: 13 }}>
            <input type="checkbox" checked={!hidden.includes(c.k)} onChange={() => setHidden(h => h.includes(c.k) ? h.filter(x => x !== c.k) : [...h, c.k])} /> {c.l}
          </label>
        ))}
      </div>
      <div className="foot">
        <button className="btn" onClick={() => { setHidden([]); localStorage.removeItem(storageKey); setOpen(false) }}>恢复默认</button>
        <button className="btn primary" onClick={() => { localStorage.setItem(storageKey, JSON.stringify(hidden)); setOpen(false) }}>应用</button>
      </div>
    </Modal>
  ) : null

  return { visible, picker, openPicker: () => setOpen(true) }
}

// 导出当前数据为 CSV（客户端生成，带 BOM 防中文乱码）
export function downloadCsv(filename, cols, rows) {
  const header = cols.map(c => c.l).join(',')
  const lines = rows.map(r => cols.map(c => {
    let v = r[c.k]
    if (v === null || v === undefined) v = ''
    v = String(v).replace(/"/g, '""')
    return /[",\n]/.test(v) ? `"${v}"` : v
  }).join(','))
  const csv = '\uFEFF' + [header, ...lines].join('\n')
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = filename
  a.click()
  URL.revokeObjectURL(a.href)
}
