import React, { useEffect, useMemo, useState } from 'react'
import { api } from '../api'
import { Modal, useToast, useConfirm, ClearableInput, Badge } from '../components/ui'
import { useColumnConfig } from '../components/columns'
import FilterBar from '../components/FilterBar'
import Pagination from '../components/Pagination'
import { useButtonPerm } from '../buttonPerms'

const SOURCES = ['日活', '采购', '其他']
const COLS = [
  { k: 'name', l: '产品名' },
  { k: 'category', l: '类别' },
  { k: 'source', l: '来源' },
  { k: 'purchase_price', l: '进货单价（元）', num: true },
  { k: 'default_sales_price', l: '默认出货单价（元）', num: true },
  { k: 'status', l: '状态' },
  { k: 'created_at', l: '创建时间' },
  { k: 'created_by', l: '创建人' },
  { k: 'updated_at', l: '更新时间' },
  { k: 'updated_by', l: '更新人' },
]
const FILTER_COLS = [
  { k: 'q', l: '产品名' },
  { k: 'category', l: '类别' },
  { k: 'source', l: '来源' },
]
const empty = { name: '', category: '', source: '', purchase_price: '', default_sales_price: '', note: '', status: 1 }

const IconColumns = (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2" /><line x1="12" y1="3" x2="12" y2="21" /><line x1="8" y1="3" x2="8" y2="21" /><line x1="16" y1="3" x2="16" y2="21" /></svg>
)

export default function Products() {
  const { toast, showError } = useToast()
  const [confirm, confirmEl] = useConfirm()
  const { can } = useButtonPerm()
  const { visible: cols, picker, openPicker } = useColumnConfig(COLS, 'cols_products_v2', [])
  const [rows, setRows] = useState([])
  const [filters, setFilters] = useState({})
  const [page, setPage] = useState(1)
  const [perPage, setPerPage] = useState(20)
  const [modal, setModal] = useState(null) // null | {id?, ...form}
  const [sort, setSort] = useState(null)
  const [categories, setCategories] = useState([])

  function load() {
    api.get('/api/products?per_page=1000').then(r => setRows(r.data?.rows || [])).catch(e => showError(e.message))
  }
  useEffect(() => {
    load()
    api.get('/api/categories').then(r => setCategories((r.data || []).map(c => c.name))).catch(() => {})
  }, [])

  const filtered = useMemo(() => {
    return rows.filter(p => {
      if (filters.q && !((p.name || '').includes(filters.q) || (p.category || '').includes(filters.q))) return false
      if (filters.category && p.category !== filters.category) return false
      if (filters.source && p.source !== filters.source) return false
      return true
    })
  }, [rows, filters])

  const sorted = useMemo(() => {
    const list = [...filtered]
    if (sort) list.sort((a, b) => (a[sort.k] > b[sort.k] ? 1 : -1) * (sort.dir === 'asc' ? 1 : -1))
    return list
  }, [filtered, sort])

  const paged = sorted.slice((page - 1) * perPage, page * perPage)

  function search() { setPage(1) }
  function changePerPage(pp) { setPerPage(pp); setPage(1) }
  function goPage(p) { setPage(p) }

  function toggleSort(k) {
    setSort(s => (s && s.k === k) ? (s.dir === 'asc' ? { k, dir: 'desc' } : null) : { k, dir: 'asc' })
  }

  function openCreate() { setModal({ ...empty }) }
  function openEdit(p) {
    setModal({ id: p.id, name: p.name, category: p.category || '', source: p.source || '',
      purchase_price: p.purchase_price ?? '', default_sales_price: p.default_sales_price ?? '',
      note: p.note || '', status: p.status })
  }
  function copyProduct(p) {
    setModal({ name: `${p.name}-复制`, category: p.category || '', source: p.source || '',
      purchase_price: p.purchase_price ?? '', default_sales_price: p.default_sales_price ?? '',
      note: p.note || '', status: p.status })
  }
  async function save() {
    const name = (modal.name || '').trim()
    if (!name) { showError('请填写产品名称'); return }
    try {
      if (modal.id) await api.put(`/api/products/${modal.id}`, modal)
      else await api.post('/api/products', modal)
      toast('已保存'); setModal(null); load()
    } catch (e) { showError(e.message) }
  }
  async function del(p) {
    if (!(await confirm(`确认删除产品「${p.name}」？`))) return
    try { await api.del(`/api/products/${p.id}`); toast('已删除'); load() } catch (e) { showError(e.message) }
  }

  function cell(c, r) {
    const v = r[c.k]
    if (c.k === 'status') return <Badge value={v === 1 ? '启用' : '停用'} />
    return v != null ? v : '—'
  }

  const fieldOptions = { category: categories, source: SOURCES }

  return (
    <div className="page">
      {confirmEl}
      {picker}
      <div className="toolbar">
        <div className="filter-wrap">
          <FilterBar cols={FILTER_COLS} filters={filters} setFilters={setFilters} onSearch={search} fieldOptions={fieldOptions} actions={true} />
        </div>
        <div className="toolbar-actions">
          {can('products:create') && <button className="btn primary" onClick={openCreate}>+ 新增产品</button>}
          <button className="btn icon" title="自定义表头" onClick={openPicker}>{IconColumns}</button>
        </div>
      </div>
      <div className="panel">
        <div className="table-scroll">
          <table>
            <thead><tr>
              <th className="ops">操作</th>
              {cols.map(c => (
                <th key={c.k} className={c.num ? 'num' : ''} onClick={() => toggleSort(c.k)}>
                  {c.l}{sort?.k === c.k ? <span className="arr">{sort.dir === 'asc' ? '▲' : '▼'}</span> : ''}
                </th>
              ))}
            </tr></thead>
            <tbody>
              {paged.map(p => (
                <tr key={p.id} onDoubleClick={() => openEdit(p)}>
                  <td className="ops">
                    {can('products:edit') && <button className="btn small" onClick={() => openEdit(p)}>编辑</button>}
                    {can('products:copy') && <button className="btn small" onClick={() => copyProduct(p)}>复制</button>}
                    {can('products:delete') && <button className="btn small danger" onClick={() => del(p)}>删除</button>}
                  </td>
                  {cols.map(c => (
                    <td key={c.k} className={c.num ? 'num' : ''}>{cell(c, p)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {sorted.length === 0 && <div className="empty">暂无产品</div>}
        <Pagination total={sorted.length} page={page} perPage={perPage} setPage={setPage} setPerPage={changePerPage} goPage={goPage} />
      </div>

      {modal && (
        <Modal title={modal.id ? '编辑产品' : '新增产品'} onClose={() => setModal(null)} wide>
          <div className="row">
            <div className="field"><label className="required">产品名称</label>
              <ClearableInput value={modal.name} onChange={e => setModal({ ...modal, name: e.target.value })} /></div>
            <div className="field"><label>产品类别</label>
              <select value={modal.category} onChange={e => setModal({ ...modal, category: e.target.value })}>
                <option value="">请选择</option>{categories.map(c => <option key={c} value={c}>{c}</option>)}
              </select></div>
            <div className="field"><label>产品来源</label>
              <select value={modal.source} onChange={e => setModal({ ...modal, source: e.target.value })}>
                <option value="">请选择</option>{SOURCES.map(s => <option key={s} value={s}>{s}</option>)}
              </select></div>
          </div>
          <div className="row">
            <div className="field"><label>进货单价（元）</label>
              <input type="number" step="0.0001" value={modal.purchase_price} onChange={e => setModal({ ...modal, purchase_price: e.target.value })} /></div>
            <div className="field"><label>默认出货单价（元）</label>
              <input type="number" step="0.0001" value={modal.default_sales_price} onChange={e => setModal({ ...modal, default_sales_price: e.target.value })} /></div>
          </div>
          <div className="field" style={{ marginBottom: 14 }}><label>说明</label>
            <textarea rows={3} value={modal.note} onChange={e => setModal({ ...modal, note: e.target.value })} /></div>
          <div className="foot">
            <button className="btn" onClick={() => setModal(null)}>取消</button>
            <button className="btn primary" onClick={save}>保存</button>
          </div>
        </Modal>
      )}
    </div>
  )
}
