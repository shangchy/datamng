import React, { useEffect, useState } from 'react'
import { api } from '../api'
import { useToast } from '../components/ui'

export default function ConfigCenter() {
  const { toast, showError } = useToast()
  const [items, setItems] = useState([])
  const [saving, setSaving] = useState(false)

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

  return (
    <div className="page">
      <div className="panel">
        <h3>配置中心</h3>
        <table>
          <thead><tr><th>配置项</th><th>值</th><th className="ops">操作</th></tr></thead>
          <tbody>
            {items.map(it => (
              <tr key={it.key}>
                <td>{it.label}</td>
                <td>
                  {it.type === 'time'
                    ? <input type="time" value={it.value} onChange={e => setValue(it.key, e.target.value)} />
                    : <input value={it.value} onChange={e => setValue(it.key, e.target.value)} />}
                </td>
                <td className="ops"><button className="btn small primary" disabled={saving} onClick={() => save(it)}>保存</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
