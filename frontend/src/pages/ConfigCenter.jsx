import React, { useEffect, useState } from 'react'
import { api } from '../api'
import { useToast, useConfirm } from '../components/ui'

export default function ConfigCenter() {
  const { toast, showError } = useToast()
  const [confirm, confirmEl] = useConfirm()
  const [items, setItems] = useState([])
  const [saving, setSaving] = useState(false)
  const [resetDate, setResetDate] = useState(() => {
    const d = new Date()
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
  })
  const [resetAll, setResetAll] = useState(false)

  function load() {
    api.get('/api/config-center').then(r => setItems(r.data || [])).catch(e => showError(e.message))
  }
  useEffect(() => { load() }, [])

  function setValue(key, value) {
    setItems(items.map(it => it.key === key ? { ...it, value } : it))
  }

  async function save(item) {
    setSaving(true)
    try {
      await api.put('/api/config-center', { key: item.key, value: item.value })
      toast('已保存')
    } catch (e) { showError(e.message) } finally { setSaving(false) }
  }

  async function doResetAlert() {
    if (!resetDate) { showError('请选择清除日期'); return }
    if (!(await confirm(`确认清除「${resetDate}」之前的${resetAll ? '所有' : '停单提醒'}预警数据，并重新扫描？此操作不可恢复。`))) return
    try {
      const r = await api.post('/api/alerts/reset', { date: resetDate, scope: resetAll ? 'all' : 'stop' })
      toast(r.msg || '重置完成')
    } catch (e) { showError(e.message) }
  }

  return (
    <div className="page">
      {confirmEl}
      <div className="panel" style={{ flex: '2 1 0' }}>
        <div className="table-scroll">
          <table>
            <thead><tr><th>配置项</th><th>值</th><th className="ops">操作</th></tr></thead>
            <tbody>
              {items.map(it => (
                <tr key={it.key}>
                  <td>{it.label}</td>
                  <td>
                    {it.type === 'time'
                      ? <input type="time" value={it.value} onChange={e => setValue(it.key, e.target.value)} />
                      : it.type === 'number'
                        ? <input type="number" value={it.value} onChange={e => setValue(it.key, e.target.value)} />
                        : <input value={it.value} onChange={e => setValue(it.key, e.target.value)} />}
                  </td>
                  <td className="ops"><button className="btn small primary" disabled={saving} onClick={() => save(it)}>保存</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="panel" style={{ flex: 'none' }}>
        <h3>预警数据重置</h3>
        <div className="row" style={{ alignItems: 'center', gap: 12 }}>
          <div className="field" style={{ flex: 'none' }}><label>清除日期（此日期之前的预警）</label>
            <input type="date" value={resetDate} onChange={e => setResetDate(e.target.value)} /></div>
          <label style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 13, color: 'var(--sub)' }}>
            <input type="checkbox" checked={resetAll} onChange={e => setResetAll(e.target.checked)} />
            同时清除账单预警
          </label>
          <button className="btn danger" onClick={doResetAlert}>重置预警</button>
        </div>
        <div className="note" style={{ marginTop: 10 }}>将按指定日期清除预警数据（默认仅停单提醒），然后立即重新扫描生成新预警。</div>
      </div>
    </div>
  )
}
