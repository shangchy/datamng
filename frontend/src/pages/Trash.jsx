import React, { useEffect, useState } from 'react'
import { api } from '../api'
import { useToast, useConfirm } from '../components/ui'

const TYPE_ICON = {
  order: '📝', bill: '💰', customer: '👤', product: '📦', product_sale: '🛒',
  channel: '🔗', operator: '📡', platform: '🖥️', category: '🗂️',
}

export default function Trash() {
  const { toast, showError } = useToast()
  const [confirm, confirmEl] = useConfirm()
  const [groups, setGroups] = useState([])
  const [loading, setLoading] = useState(false)

  async function load() {
    setLoading(true)
    try {
      const r = await api.get('/api/trash')
      setGroups(r.data || [])
    } catch (e) { showError(e.message) } finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  async function restore(type, id) {
    try {
      await api.post('/api/trash/restore', { type, id })
      toast('已恢复')
      load()
    } catch (e) { showError(e.message) }
  }

  async function purge(type, id, label) {
    if (!(await confirm(`确定彻底删除「${label}」？此操作不可恢复。`, true))) return
    try {
      await api.del(`/api/trash/${type}/${id}`)
      toast('已彻底删除')
      load()
    } catch (e) { showError(e.message) }
  }

  return (
    <div className="page">
      {confirmEl}
      <div className="toolbar">
        <span className="note" style={{ color: 'var(--sub)' }}>垃圾箱收纳被删除的订单/账单/客户/产品/产品销售/渠道/运营商/平台/品类，可恢复或彻底删除。</span>
        <span className="spacer" />
        <button className="btn" onClick={load}>刷新</button>
      </div>

      {loading && <div className="empty">加载中…</div>}
      {!loading && groups.length === 0 && <div className="empty">垃圾箱为空</div>}

      {groups.map(g => (
        <div className="panel" key={g.type}>
          <h3>{TYPE_ICON[g.type] || '🗑️'} {g.type_label}（{g.count}）</h3>
          <div className="table-scroll">
            <table>
              <thead><tr><th>名称</th><th>删除时间</th><th className="ops">操作</th></tr></thead>
              <tbody>
                {g.items.map(it => (
                  <tr key={it.id}>
                    <td>{it.label}</td>
                    <td style={{ color: 'var(--sub)' }}>{it.deleted_at}</td>
                    <td className="ops">
                      <button className="btn small" onClick={() => restore(g.type, it.id)}>恢复</button>{' '}
                      <button className="btn small danger" onClick={() => purge(g.type, it.id, it.label)}>彻底删除</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}
    </div>
  )
}
