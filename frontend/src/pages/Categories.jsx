import React, { useEffect, useRef, useState } from 'react'
import { api, getToken } from '../api'
import { Modal, useToast, useConfirm, Loading } from '../components/ui'

export default function Categories() {
  const toast = useToast()
  const [confirm, confirmEl] = useConfirm()
  const [rows, setRows] = useState([])
  const [platforms, setPlatforms] = useState([])
  const [modal, setModal] = useState(null) // {type:'cat1'|'cat2'|'platform', name, status, parentId, catId}
  const [q, setQ] = useState({ cat1: '', cat2: '', platform: '' })
  const fileRef = useRef(null)
  const [busy, setBusy] = useState(false)

  async function load() {
    const r = await api.get('/api/categories'); setRows(r.data)
    const p = await api.get('/api/platforms'); setPlatforms(p.data || [])
  }
  useEffect(() => { load() }, [])

  async function importCategories(file) {
    setBusy(true)
    try {
      const fd = new FormData()
      fd.append('file', file)
      const res = await fetch('/api/categories/import', { method: 'POST', headers: { Authorization: 'Bearer ' + getToken() }, body: fd })
      const data = await res.json()
      if (!res.ok) throw new Error(data.msg || data.detail || '导入失败')
      toast(data.msg); load()
    } finally {
      setBusy(false)
    }
  }

  async function save() {
    if (!modal.name.trim()) { toast('请输入名称'); return }
    if (modal.id) {
      if (modal.type === 'platform') await api.put(`/api/platforms/${modal.id}`, { name: modal.name, cat_id: modal.catId, status: 1 })
      else await api.put(`/api/categories/${modal.id}`, { name: modal.name, status: 1 })
      toast('已保存')
    } else if (modal.type === 'cat1') {
      await api.post('/api/categories', { name: modal.name, level: 1, status: 1 })
      toast('已新增')
    } else if (modal.type === 'cat2') {
      await api.post('/api/categories', { name: modal.name, parent_id: modal.parentId, level: 2, status: 1 })
      toast('已新增')
    } else {
      await api.post('/api/platforms', { name: modal.name, cat_id: modal.catId, status: 1 })
      toast('已新增')
    }
    setModal(null); load()
  }
  async function del(id) {
    if (await confirm('确认删除？')) { try { await api.del(`/api/categories/${id}`); toast('已删除'); load() } catch (e) { toast(e.message) } }
  }
  async function delPlatform(id) {
    if (await confirm('确认删除该平台？')) { try { await api.del(`/api/platforms/${id}`); toast('已删除'); load() } catch (e) { toast(e.message) } }
  }
  function platformsOf(catId) { return visPlats.filter(p => p.cat_id === catId) }

  const kw = v => (v || '').trim().toLowerCase()
  const has = (name, k) => !k || (name || '').toLowerCase().includes(k)
  const qCat1 = kw(q.cat1), qCat2 = kw(q.cat2), qPlat = kw(q.platform)
  const visPlats = platforms.filter(p => has(p.name, qPlat))
  const visRows = rows
    .filter(c => has(c.name, qCat1))
    .map(c => ({
      ...c,
      children: (c.children || [])
        .filter(ch => has(ch.name, qCat2))
        .filter(ch => !qPlat || visPlats.some(p => p.cat_id === ch.id)),
    }))
    .filter(c => (c.children || []).length > 0 || (!qCat2 && !qPlat))

  return (
    <div className="page">
      {confirmEl}
      {busy && <Loading text="正在导入品类，请稍候…" />}
      <input type="file" accept=".xlsx,.xls" style={{ display: 'none' }} ref={fileRef} onChange={e => { if (e.target.files[0]) importCategories(e.target.files[0]).catch(err => toast(err.message)); e.target.value = '' }} />
      <div className="toolbar">
        <input list="cat1-list" placeholder="一级品类" style={{ width: 130 }} value={q.cat1} onChange={e => setQ({ ...q, cat1: e.target.value })} />
        <datalist id="cat1-list">{rows.map(c => <option key={c.id} value={c.name} />)}</datalist>
        <input list="cat2-list" placeholder="二级品类" style={{ width: 130 }} value={q.cat2} onChange={e => setQ({ ...q, cat2: e.target.value })} />
        <datalist id="cat2-list">{rows.flatMap(c => (c.children || []).map(x => <option key={x.id} value={x.name} />))}</datalist>
        <input placeholder="平台" style={{ width: 120 }} value={q.platform} onChange={e => setQ({ ...q, platform: e.target.value })} />
        <button className="btn" onClick={() => setQ({ cat1: '', cat2: '', platform: '' })}>重置</button>
        <span className="spacer" />
        <button className="btn" onClick={() => fileRef.current.click()}>导入 Excel</button>
        <button className="btn primary" onClick={() => setModal({ type: 'cat1', name: '', status: 1 })}>+ 新增一级品类</button>
      </div>
      <div className="panel">
        <div className="table-scroll">
        <table>
          <thead><tr><th>名称</th><th>层级</th><th>平台</th><th className="ops">操作</th></tr></thead>
          <tbody>
            {visRows.map(c => (
              <React.Fragment key={c.id}>
                <tr>
                  <td><b>{c.name}</b></td><td>一级品类</td><td></td>
                  <td className="ops">
                    <button className="btn small" onClick={() => setModal({ type: 'cat1', id: c.id, name: c.name, status: 1 })}>编辑</button>{' '}
                    <button className="btn small danger" onClick={() => del(c.id)}>删除</button>{' '}
                    <button className="btn small primary" onClick={() => setModal({ type: 'cat2', name: '', status: 1, parentId: c.id })}>+ 二级</button>
                  </td>
                </tr>
                {(c.children || []).map(ch => (
                  <tr key={ch.id}>
                    <td style={{ paddingLeft: 40 }}>└ {ch.name}</td><td>二级品类</td>
                    <td>
                      <div className="tag-row">
                        {platformsOf(ch.id).map(p => (
                          <span key={p.id} className="tag">{p.name}<a className="tag-x" onClick={() => delPlatform(p.id)}>×</a></span>
                        ))}
                        <button className="btn tiny" onClick={() => setModal({ type: 'platform', name: '', status: 1, catId: ch.id })}>+ 平台</button>
                      </div>
                    </td>
                    <td className="ops">
                      <button className="btn small" onClick={() => setModal({ type: 'cat2', id: ch.id, name: ch.name, status: 1, parentId: c.id })}>编辑</button>{' '}
                      <button className="btn small danger" onClick={() => del(ch.id)}>删除</button>
                    </td>
                  </tr>
                ))}
              </React.Fragment>
            ))}
          </tbody>
        </table>
        </div>
        {visRows.length === 0 && <div className="empty">暂无数据</div>}
      </div>

      {modal && (
        <Modal title={(modal.id ? '编辑' : '新增') + (modal.type === 'cat1' ? '一级品类' : modal.type === 'cat2' ? '二级品类' : '平台')} onClose={() => setModal(null)}>
          <div className="field"><label>名称</label><input value={modal.name} onChange={e => setModal({ ...modal, name: e.target.value })} style={{ width: '100%' }} /></div>
          <div className="foot"><button className="btn" onClick={() => setModal(null)}>取消</button><button className="btn primary" onClick={save}>保存</button></div>
        </Modal>
      )}
    </div>
  )
}
