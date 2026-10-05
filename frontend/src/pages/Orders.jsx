import React, { useEffect, useRef, useState } from 'react'
import { api, downloadFile, getToken, uploadFile } from '../api'
import { Modal, Badge, useToast, useConfirm, Loading } from '../components/ui'
import { useColumnConfig } from '../components/columns'
import FilterBar, { buildQuery } from '../components/FilterBar'
import Pagination from '../components/Pagination'
import MultiSelect from '../components/MultiSelect'

const IconChevronDown = (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><polyline points="6 9 12 15 18 9" /></svg>
)
const IconChevronUp = (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><polyline points="18 15 12 9 6 15" /></svg>
)
const IconColumns = (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2" /><line x1="12" y1="3" x2="12" y2="21" /><line x1="8" y1="3" x2="8" y2="21" /><line x1="16" y1="3" x2="16" y2="21" /></svg>
)
const IconEdit = (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z" /></svg>
)
const IconModify = (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="23 4 23 10 17 10" /><polyline points="1 20 1 14 7 14" /><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" /></svg>
)
const IconStop = (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10" /><line x1="4.93" y1="4.93" x2="19.07" y2="19.07" /></svg>
)
const IconDelete = (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="3 6 5 6 21 6" /><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" /></svg>
)

function IconBtn({ title, color, onClick, children }) {
  return (
    <button className="icon-btn" title={title} onClick={onClick} style={{ color }}>{children}</button>
  )
}

const COLS = [
  { k: 'status', l: '状态' }, { k: 'task_name', l: '任务名' }, { k: 'order_date', l: '更新日期' }, { k: 'upstream', l: '甲方' },
  { k: 'order_no', l: '订单号' }, { k: 'task_id', l: '工单号' }, { k: 'dup_order_nos', l: '重复订单' },
  { k: 'customer', l: '一级代理' }, { k: 'secondary_agent', l: '二级代理' }, { k: 'price', l: '定价' },
  { k: 'platform', l: '平台' }, { k: 'group_name', l: '小组' }, { k: 'tpl_code', l: '出数模版' },
  { k: 'add_name', l: '是否加名' }, { k: 'check_collision', l: '是否撞库' }, { k: 'channel', l: '渠道' }, { k: 'operator', l: '运营商' },
  { k: 'url', l: 'url' }, { k: 'qty', l: '数量' },
  { k: 'age_min', l: '年龄下限' }, { k: 'age_max', l: '年龄上限' }, { k: 'pv', l: 'pv' },
  { k: 'province', l: '省份' }, { k: 'excl_province', l: '排除省份' }, { k: 'city', l: '地市' },
  { k: 'excl_city', l: '排除地市' }, { k: 'start_date', l: '开始日期' }, { k: 'first_output_date', l: '初次出数日期' },
  { k: 'end_date', l: '截止日期' }, { k: 'last_output_date', l: '末次出数日期' }, { k: 'duration', l: '时长' },
  { k: 'created_at', l: '创建时间' }, { k: 'updated_at', l: '更新时间' },
]

const FILTER_COLS = [
  { k: 'status', l: '状态' }, { k: 'order_date', l: '更新日期' },
  { k: 'upstream', l: '甲方' }, { k: 'order_no', l: '订单号' }, { k: 'task_id', l: '工单号' }, { k: 'dup', l: '重复订单' },
  { k: 'customer', l: '一级代理' }, { k: 'secondary_agent', l: '二级代理' }, { k: 'price', l: '定价' },
  { k: 'platform', l: '平台' }, { k: 'group_name', l: '小组' }, { k: 'tpl_code', l: '出数模版' },
  { k: 'add_name', l: '是否加名' }, { k: 'check_collision', l: '是否撞库' }, { k: 'channel', l: '渠道' }, { k: 'operator', l: '运营商' },
  { k: 'task_name', l: '任务名' }, { k: 'url', l: 'url' }, { k: 'qty', l: '数量' }, { k: 'duration', l: '时长' },
  { k: 'age_min', l: '年龄下限' }, { k: 'age_max', l: '年龄上限' }, { k: 'pv', l: 'pv' },
  { k: 'province', l: '省份' }, { k: 'excl_province', l: '排除省份' }, { k: 'city', l: '地市' },
  { k: 'excl_city', l: '排除地市' }, { k: 'start_date', l: '开始日期' }, { k: 'end_date', l: '截止日期' },
]

const emptyForm = { order_no: '', customer_id: '', upstream_id: '', channel_id: '', operator_id: '', task_name: '', task_id: '', qty: '', duration: '', province: '', city: '', excl_province: '', excl_city: '', age_min: '', age_max: '', pv: '', start_date: '', end_date: '', order_date: '', price: '', secondary_agent: '', platform: '', tpl_id: '', group_name: '', add_name: false, check_collision: false, template_id: '', filename_rule: '', status: '未提', url: '' }

const REGION_SEP = /[|｜,，;；]/
function fmtRegion(val) {
  return (val || '').split(REGION_SEP).map(s => s.trim()).filter(Boolean).join('、')
}
function toComma(val) {
  return (val || '').split(REGION_SEP).map(s => s.trim()).filter(Boolean).join(',')
}

export default function Orders({ variant = 'orders' }) {
  const { toast, showError } = useToast()
  const [confirm, confirmEl] = useConfirm()
  const isStop = variant === 'stop'
  const BASE_COLS = isStop ? [{ k: 'batch_no', l: '提单批次' }, ...COLS] : COLS
  const { visible: cols, picker, openPicker } = useColumnConfig(BASE_COLS, isStop ? 'cols_stop_manage' : 'cols_order')
  const [rows, setRows] = useState([])
  const [customers, setCustomers] = useState([])
  const [upstreams, setUpstreams] = useState([])
  const [channels, setChannels] = useState([])
  const [operators, setOperators] = useState([])
  const [filters, setFilters] = useState({})
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [perPage, setPerPage] = useState(10)
  const [sort, setSort] = useState(null)
  const [modal, setModal] = useState(null) // null | 'create' | 'edit' | 'modify'
  const [form, setForm] = useState(emptyForm)
  const [detail, setDetail] = useState(null)
  const [stopTarget, setStopTarget] = useState(null)
  const [stopDate, setStopDate] = useState('')
  const [stopReason, setStopReason] = useState('业务调整')
  const [urlDetail, setUrlDetail] = useState(null)
  const [regionDetail, setRegionDetail] = useState(null)
  const [geo, setGeo] = useState({ provinces: [], citiesMap: {} })
  const [tpls, setTpls] = useState([])
  const [platforms, setPlatforms] = useState([])
  const [tplDetail, setTplDetail] = useState(null)
  const [importModal, setImportModal] = useState(false)
  const [importResult, setImportResult] = useState(null)
  const importFileRef = useRef(null)
  const [receiptModal, setReceiptModal] = useState(false)
  const [receiptResult, setReceiptResult] = useState(null)
  const [receiptParty, setReceiptParty] = useState('牛')
  const receiptFileRef = useRef(null)
  const [selected, setSelected] = useState([])
  const [groupModal, setGroupModal] = useState(false)
  const [groupVal, setGroupVal] = useState('')
  const [busy, setBusy] = useState(false)
  const [busyMsg, setBusyMsg] = useState('')
  const [busyProgress, setBusyProgress] = useState(null)
  const [genModal, setGenModal] = useState(false)
  const [genDate, setGenDate] = useState(() => {
    const d = new Date()
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
  })
  const [confirmModal, setConfirmModal] = useState(false)
  const [confirmDate, setConfirmDate] = useState(() => {
    const d = new Date()
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
  })
  const [filterCollapsed, setFilterCollapsed] = useState(false)

  async function load(p = page, pp = perPage, f) {
    const qs = buildQuery(f === undefined ? filters : f)
    const params = qs ? qs + `&page=${p}&per_page=${pp}` : `page=${p}&per_page=${pp}`
    const r = await api.get('/api/orders?' + params)
    setRows(r.data.rows); setTotal(r.data.total)
  }
  function search(f) { setPage(1); load(1, perPage, f) }
  function goPage(p) { setPage(p); load(p, perPage) }
  function changePerPage(pp) { setPerPage(pp); setPage(1); load(1, pp) }
  useEffect(() => { load() }, [])
  useEffect(() => {
    api.get('/api/customers?per_page=1000').then(r => {
      setCustomers(r.data.rows.filter(c => c.ctype === 'downstream'))
      setUpstreams(r.data.rows.filter(c => c.ctype === 'upstream'))
    }).catch(() => {})
    api.get('/api/channels?per_page=1000').then(r => setChannels(r.data.rows)).catch(() => {})
    api.get('/api/operators?per_page=1000').then(r => setOperators(r.data.rows)).catch(() => {})
    api.get('/api/regions').then(r => {
      setGeo({ provinces: r.data.provinces, citiesMap: r.data.cities })
    }).catch(() => {})
    api.get('/api/templates').then(r => setTpls(r.data || [])).catch(() => {})
    api.get('/api/platforms').then(r => setPlatforms(r.data || [])).catch(() => {})
  }, [])

  const allCities = [...new Set(Object.values(geo.citiesMap).flat())]
  const fieldOptions = {
    status: ['未提', '在执', '待停', '已停', '改单'],
    upstream: upstreams.map(u => u.name),
    customer: customers.map(c => c.code),
    channel: channels.map(c => c.name),
    platform: platforms.map(p => p.name),
    add_name: ['是', '否'],
    check_collision: ['是', '否'],
    operator: operators.map(o => o.name),
    dup: ['有', '无'],
    province: geo.provinces,
    city: allCities,
  }

  const provinceOptions = ['全国', ...geo.provinces]
  const selectedProvinces = (form.province || '').split(',').filter(Boolean)
  const isNational = selectedProvinces.includes('全国')
  const exclCityOptions = isNational
    ? [...new Set(Object.values(geo.citiesMap).flat())]
    : [...new Set(selectedProvinces.filter(p => p !== '全国').flatMap(p => geo.citiesMap[p] || []))]
  const computedDuration = (form.start_date && form.end_date)
    ? String(Math.round((new Date(form.end_date + 'T00:00:00') - new Date(form.start_date + 'T00:00:00')) / 86400000))
    : ''

  function sorted() {
    const list = [...rows]
    if (sort) list.sort((a, b) => (a[sort.k] > b[sort.k] ? 1 : -1) * (sort.dir === 'asc' ? 1 : -1))
    return list
  }

  function openCreate() { setForm(emptyForm); setModal('create') }

  function toggleSelect(id) {
    setSelected(s => s.includes(id) ? s.filter(x => x !== id) : [...s, id])
  }
  function toggleAll() {
    const ids = sorted().map(o => o.id)
    setSelected(selected.length === ids.length ? [] : ids)
  }
  function batchStop() {
    if (!selected.length) { showError('请先勾选要停单的订单'); return }
    const d = new Date()
    setStopDate(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`)
    setStopReason('业务调整')
    setStopTarget({ ids: selected, batch: true })
  }

  async function batchDelete() {
    if (!selected.length) { showError('请先勾选要删除的订单'); return }
    if (!(await confirm(`确认删除选中的 ${selected.length} 个订单？此操作不可恢复。`))) return
    try {
      await api.post('/api/orders/batch-delete', { ids: selected })
      toast('已批量删除'); setSelected([]); load()
    } catch (e) { showError(e.message) }
  }

  async function batchGroup() {
    try {
      await api.post('/api/orders/batch-group', { ids: selected, group_name: groupVal })
      toast('小组已批量修改'); setGroupModal(false); setSelected([]); load()
    } catch (e) { showError(e.message) }
  }

  function openEdit(o) {
    setForm({
      id: o.id,
      order_no: o.order_no || '',
      customer_id: o.customer_id, upstream_id: o.upstream_id, channel_id: o.channel_id, operator_id: o.operator_id ?? '', task_name: o.task_name,
      task_id: o.task_id || '', qty: o.qty ?? '', duration: o.duration || '',
      province: toComma(o.province), city: toComma(o.city), excl_province: toComma(o.excl_province),
      excl_city: toComma(o.excl_city), age_min: o.age_min ?? '', age_max: o.age_max ?? '', pv: o.pv ?? '',
      start_date: o.start_date || '', end_date: o.end_date || '',
      order_date: o.order_date || '', price: o.price ?? '', secondary_agent: o.secondary_agent || '',
      platform: o.platform || '', tpl_id: o.tpl_id ?? '', group_name: o.group_name || '',
      export_filename: o.export_filename || '', add_name: !!o.add_name, check_collision: !!o.check_collision,
      template_id: o.template_id ?? '', filename_rule: o.filename_rule || '', dist_config: o.dist_config || null,
      status: o.status || '未提',
      url: (o.urls || []).join('\n'),
    })
    setModal(o.status === '未提' ? 'edit' : 'modify')
  }

  async function save() {
    const missing = []
    if (!form.order_date) missing.push('更新日期')
    if (!(form.task_name || '').trim()) missing.push('任务名')
    if (form.qty === '' || form.qty == null) missing.push('数量')
    if (!form.start_date) missing.push('开始日期')
    if (!form.end_date) missing.push('截止日期')
    if (!form.upstream_id) missing.push('上游')
    if (!form.customer_id) missing.push('一级代理')
    if (missing.length) { showError('缺少必填字段：' + missing.join('、')); return }
    if (!(await confirm('确认保存该订单？'))) return
    try {
      const body = { ...form, qty: form.qty === '' ? null : Number(form.qty), age_min: form.age_min === '' ? null : Number(form.age_min), age_max: form.age_max === '' ? null : Number(form.age_max), pv: form.pv === '' ? null : Number(form.pv), customer_id: Number(form.customer_id), upstream_id: form.upstream_id ? Number(form.upstream_id) : null, channel_id: form.channel_id ? Number(form.channel_id) : null, operator_id: form.operator_id ? Number(form.operator_id) : null, template_id: form.template_id === '' || form.template_id == null ? null : Number(form.template_id), tpl_id: form.tpl_id === '' || form.tpl_id == null ? null : Number(form.tpl_id), price: form.price === '' || form.price == null ? null : Number(form.price), order_date: form.order_date || null, duration: computedDuration, urls: (form.url || '').split('\n').map(s => s.trim()).filter(Boolean).map(u => ({ url: u, level: '高' })) }
      if (modal === 'create') await api.post('/api/orders', body)
      else await api.put(`/api/orders/${form.id}`, body)
      toast(modal === 'modify' ? '改单已保存（状态：改单）' : '已保存（状态：未提）'); setModal(null); load()
    } catch (e) { showError(e.message) }
  }

  async function stop() {
    if (!stopDate) { showError('请选择更新日期'); return }
    const isBatch = stopTarget && stopTarget.batch
    if (!(await confirm(isBatch ? `确认停单选中的 ${stopTarget.ids.length} 个订单？` : '确认停单？'))) return
    try {
      if (isBatch) {
        await api.post('/api/orders/batch-stop', { ids: stopTarget.ids, reason: stopReason, note: '', order_date: stopDate })
        toast('已批量停单'); setSelected([])
      } else {
        await api.post(`/api/orders/${stopTarget.id}/stop`, { reason: stopReason, note: '', order_date: stopDate })
        toast('已停')
      }
      setStopTarget(null); setStopDate(''); load(); window.dispatchEvent(new Event('alert-count-refresh'))
    } catch (e) { showError(e.message) }
  }

  async function delOrder(o) {
    if (!(await confirm(`确认删除订单 ${o.order_no}？此操作不可恢复。`))) return
    try {
      await api.del(`/api/orders/${o.id}`)
      toast('已删除'); setSelected(s => s.filter(x => x !== o.id)); load()
    } catch (e) { showError(e.message) }
  }

  async function importOrders(file) {
    setBusy(true); setBusyMsg('正在上传导入文件…'); setBusyProgress(0)
    try {
      const fd = new FormData()
      fd.append('file', file)
      const data = await uploadFile('/api/orders/import', fd, p => setBusyProgress(p))
      setBusyMsg('正在处理导入数据，请稍候…'); setBusyProgress(100)
      setImportResult(data.data)
      load()
    } finally {
      setBusy(false); setBusyProgress(null)
    }
  }

  async function importReceipt(file) {
    setBusy(true); setBusyMsg('正在上传回执文件…'); setBusyProgress(0)
    try {
      const fd = new FormData()
      fd.append('file', file)
      fd.append('party', receiptParty)
      const data = await uploadFile('/api/orders/import-receipt', fd, p => setBusyProgress(p))
      setBusyMsg('正在处理回执数据，请稍候…'); setBusyProgress(100)
      setReceiptResult(data.data)
      load()
    } finally {
      setBusy(false); setBusyProgress(null)
    }
  }

  async function doGenerate() {
    setGenModal(false)
    setBusy(true); setBusyMsg('正在生成提单表，请稍候…')
    try {
      const body = { date: genDate, order_ids: selected.length ? selected : [] }
      const res = await fetch('/api/orders/generate-tidabiao', { method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + getToken() }, body: JSON.stringify(body) })
      if (!res.ok) { const d = await res.json().catch(() => ({})); throw new Error(d.msg || d.detail || '生成失败') }
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      const mmdd = genDate.replace('-', '').slice(4)
      a.href = url
      a.download = `提单表-${mmdd}.zip`
      a.click()
      URL.revokeObjectURL(url)
      toast('已生成提单表，请查看下载')
    } finally {
      setBusy(false)
    }
  }

  async function doConfirm() {
    setConfirmModal(false)
    setBusy(true); setBusyMsg('正在提单确认，请稍候…')
    try {
      const body = { date: confirmDate, order_ids: selected.length ? selected : [] }
      const r = await api.post('/api/orders/confirm-tidabiao', body)
      toast(r.msg || '提单确认完成'); setSelected([]); load()
    } catch (e) { showError(e.message) } finally { setBusy(false) }
  }

  function showTpl(o) {
    const t = tpls.find(x => x.id === o.tpl_id)
    setTplDetail(t || { code: o.tpl_code, name: o.tpl_name })
  }

  async function openOrderByNo(no) {
    try {
      const r = await api.get('/api/orders?order_no=' + encodeURIComponent(no) + '&per_page=1')
      if (r.data.rows.length) setDetail(r.data.rows[0])
      else showError('未找到订单 ' + no)
    } catch (e) { showError(e.message) }
  }

  async function checkDuplicates() {
    setBusy(true); setBusyMsg('正在验重，请稍候…')
    try {
      const r = await api.post('/api/orders/check-duplicates')
      toast(r.msg || '验重完成'); load()
    } catch (e) { showError(e.message) } finally { setBusy(false) }
  }

  function orderCell(o, c) {
    const num = ['qty', 'pv', 'age_min', 'age_max'].includes(c.k)
    if (c.k === 'status') return <td className={num ? 'num' : ''}><Badge value={o.status} /></td>
    if (c.k === 'url') return <td><a className="link" onClick={e => { e.stopPropagation(); setUrlDetail(o) }}>{o.url}</a></td>
    if (c.k === 'tpl_code') return <td>{o.tpl_code ? <a className="link" onClick={e => { e.stopPropagation(); showTpl(o) }}>{o.tpl_code}</a> : '—'}</td>
    if (c.k === 'add_name') return <td><Badge value={o.add_name ? '是' : '否'} /></td>
    if (c.k === 'check_collision') return <td><Badge value={o.check_collision ? '是' : '否'} /></td>
    if (c.k === 'region') return <td><a className="link" onClick={e => { e.stopPropagation(); setRegionDetail(o) }}>{o.region || '—'}</a></td>
    if (c.k === 'dup_order_nos') {
      const nos = (o.dup_order_nos || '').split('\n').filter(Boolean)
      if (!nos.length) return <td>—</td>
      return <td style={{ whiteSpace: 'nowrap' }}>{nos.map((no, i) => (
        <React.Fragment key={no}>
          {i > 0 && <br />}
          <a className="link" onClick={e => { e.stopPropagation(); openOrderByNo(no) }}>{no}</a>
        </React.Fragment>
      ))}</td>
    }
    if (c.k === 'price') return <td className="num">{o.price != null ? o.price : '—'}</td>
    if (['province', 'city', 'excl_province', 'excl_city'].includes(c.k)) {
      const val = o[c.k] || ''
      const parts = val.split(/[|｜,，;；]/).map(s => s.trim()).filter(Boolean)
      if (parts.length > 3) return <td title={val}>{parts[0]} 等{parts.length}个</td>
      return <td title={val}>{parts.join(',') || '—'}</td>
    }
    return <td className={num ? 'num' : ''}>{o[c.k] ?? '—'}</td>
  }

  function summarizeFilters() {
    const parts = []
    FILTER_COLS.forEach(c => {
      const v = filters[c.k]
      if (v !== undefined && v !== null && v !== '') {
        parts.push(`${c.l}：${Array.isArray(v) ? v.join('、') : v}`)
      }
    })
    return parts.length ? parts.join('\n') : '无筛选条件（导出全部订单）'
  }

  async function exportExcel() {
    const summary = summarizeFilters()
    if (!(await confirm(`确认按以下筛选条件导出订单数据？\n\n${summary}`))) return
    const qs = buildQuery(filters)
    downloadFile('/api/orders/export?' + qs).catch(e => showError(e.message))
    toast('正在导出订单...')
  }

  return (
    <div className="page">
      {confirmEl}
      {picker}
      {busy && <Loading text={busyMsg} progress={busyProgress} />}
      <div className="toolbar">
        <div className={`filter-wrap ${filterCollapsed ? 'collapsed' : ''}`}>
          <FilterBar cols={FILTER_COLS} filters={filters} setFilters={setFilters} onSearch={search} fieldOptions={fieldOptions} actions={false} />
        </div>
        <div className="toolbar-actions">
          <button className="btn primary" onClick={() => search()}>查询</button>
          <button className="btn" onClick={() => { setFilters({}); search({}) }}>重置</button>
          <button className="btn icon" title={filterCollapsed ? '展开查询条件' : '隐藏查询条件'} onClick={() => setFilterCollapsed(!filterCollapsed)}>{filterCollapsed ? IconChevronDown : IconChevronUp}</button>
          {!isStop && <button className="btn" onClick={() => { setImportResult(null); setImportModal(true) }}>导入订单</button>}
          {!isStop && <button className="btn" onClick={() => { setReceiptResult(null); setReceiptModal(true) }}>导入回执</button>}
          {!isStop && <button className="btn green" onClick={() => setGenModal(true)}>生成提单表</button>}
          {!isStop && <button className="btn primary" onClick={() => setConfirmModal(true)}>提单确认</button>}
          {!isStop && <button className="btn" onClick={checkDuplicates}>订单验重</button>}
          <button className="btn green" onClick={exportExcel}>导出订单</button>
          {!isStop && <button className="btn" onClick={() => downloadFile('/api/orders/export-template').catch(e => showError(e.message))}>导出模版</button>}
          {!isStop && selected.length > 0 && <button className="btn danger" onClick={batchStop}>批量停单({selected.length})</button>}
          {!isStop && selected.length > 0 && <button className="btn danger" onClick={batchDelete}>批量删除({selected.length})</button>}
          {!isStop && selected.length > 0 && <button className="btn" onClick={() => { setGroupVal(''); setGroupModal(true) }}>批量修改小组({selected.length})</button>}
          {!isStop && <button className="btn primary" onClick={openCreate}>+ 新建提单</button>}
          <button className="btn icon" title="自定义表头" onClick={openPicker}>{IconColumns}</button>
        </div>
      </div>

      <div className="panel">
        <div className="table-scroll">
        <table>
          <thead><tr>
            {!isStop && <th style={{ width: 32 }}><input type="checkbox" checked={rows.length > 0 && selected.length === sorted().length} onChange={toggleAll} /></th>}
            {!isStop && <th className="ops">操作</th>}
            {cols.map(c => (
              <th key={c.k} className={['qty', 'pv', 'age_min', 'age_max'].includes(c.k) ? 'num' : ''} onClick={() => setSort(sort?.k === c.k ? (sort.dir === 'asc' ? { k: c.k, dir: 'desc' } : null) : { k: c.k, dir: 'asc' })}>
                {c.l}{sort?.k === c.k ? <span className="arr">{sort.dir === 'asc' ? '▲' : '▼'}</span> : ''}
              </th>
            ))}
          </tr></thead>
          <tbody>
            {sorted().map(o => (
              <tr key={o.id} className={o.has_alert ? 'row-alert' : 'clickable'} onDoubleClick={() => setDetail(o)}>
                {!isStop && <td><input type="checkbox" checked={selected.includes(o.id)} onChange={() => toggleSelect(o.id)} onClick={e => e.stopPropagation()} /></td>}
                {!isStop && (
                <td className="ops">
                  {o.status === '未提' && <IconBtn title="编辑" color="#2563eb" onClick={e => { e.stopPropagation(); openEdit(o) }}>{IconEdit}</IconBtn>}
                  {['在执', '已停', '改单'].includes(o.status) && <IconBtn title="改单" color="#7c3aed" onClick={e => { e.stopPropagation(); openEdit(o) }}>{IconModify}</IconBtn>}
                  {['在执', '改单'].includes(o.status) && <IconBtn title="停单" color="#d97706" onClick={e => { e.stopPropagation(); const d = new Date(); setStopDate(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`); setStopReason('业务调整'); setStopTarget(o) }}>{IconStop}</IconBtn>}
                  <IconBtn title="删除" color="#dc2626" onClick={e => { e.stopPropagation(); delOrder(o) }}>{IconDelete}</IconBtn>
                </td>
                )}
                {cols.map(c => <React.Fragment key={c.k}>{orderCell(o, c)}</React.Fragment>)}
              </tr>
            ))}
          </tbody>
        </table>
        </div>
        {rows.length === 0 && <div className="empty">暂无数据</div>}
        <Pagination total={total} page={page} perPage={perPage} setPage={setPage} setPerPage={changePerPage} goPage={goPage} />
      </div>

      {modal && (
        <Modal title={modal === 'create' ? '新建提单' : (modal === 'edit' ? '编辑提单' : '改单')} onClose={() => setModal(null)} wide>
          <div className="row">
            <div className="field"><label>订单编号</label><input value={form.order_no} disabled placeholder="自动生成" /></div>
            <div className="field"><label>工单号</label><input value={form.task_id} disabled placeholder="自动生成" /></div>
            <div className="field"><label className="required">上游</label>
              <select value={form.upstream_id} onChange={e => setForm({ ...form, upstream_id: e.target.value })}>
                <option value="">请选择</option>{upstreams.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select></div>
            <div className="field"><label className="required">任务名</label><input value={form.task_name} onChange={e => setForm({ ...form, task_name: e.target.value })} /></div>
          </div>
          <div className="row">
            <div className="field"><label className="required">更新日期</label><input type="date" value={form.order_date} onChange={e => setForm({ ...form, order_date: e.target.value })} /></div>
            <div className="field"><label>状态</label>
              <div className="readonly">{modal === 'modify' ? '改单' : '未提'}</div>
            </div>
            <div className="field"><label className="required">一级代理</label>
              <select value={form.customer_id} onChange={e => setForm({ ...form, customer_id: e.target.value })}>
                <option value="">请选择</option>{customers.map(c => <option key={c.id} value={c.id}>{c.code} {c.name}</option>)}
              </select></div>
            <div className="field"><label>二级代理</label><input value={form.secondary_agent} onChange={e => setForm({ ...form, secondary_agent: e.target.value })} placeholder="如 罗/无" /></div>
          </div>
          <div className="row">
            <div className="field"><label>渠道</label>
              <select value={form.channel_id} disabled={modal === 'modify'} onChange={e => setForm({ ...form, channel_id: e.target.value })}>
                <option value="">请选择</option>{channels.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select></div>
            <div className="field"><label>运营商</label>
              <select value={form.operator_id} disabled={modal === 'modify'} onChange={e => setForm({ ...form, operator_id: e.target.value })}>
                <option value="">请选择</option>{operators.map(o => <option key={o.id} value={o.id}>{o.name}</option>)}
              </select></div>
            <div className="field"><label>平台</label>
              <select value={form.platform} onChange={e => setForm({ ...form, platform: e.target.value })}>
                <option value="">请选择</option>{platforms.map(p => <option key={p.id} value={p.name}>{p.name}</option>)}
              </select></div>
          </div>
          <div className="row">
            <div className="field"><label>分组</label><input value={form.group_name} onChange={e => setForm({ ...form, group_name: e.target.value })} placeholder="分组文本" /></div>
            <div className="field"><label>模版编号</label>
              <select value={form.tpl_id} onChange={e => setForm({ ...form, tpl_id: e.target.value })}>
                <option value="">请选择模版</option>
                {tpls.map(t => <option key={t.id} value={t.id}>{t.code} {t.name}</option>)}
              </select></div>
            <div className="field"><label>是否加名</label>
              <select value={form.add_name ? '是' : '否'} onChange={e => setForm({ ...form, add_name: e.target.value === '是' })}>
                <option>否</option><option>是</option>
              </select></div>
            <div className="field"><label>是否撞库</label>
              <select value={form.check_collision ? '是' : '否'} onChange={e => setForm({ ...form, check_collision: e.target.value === '是' })}>
                <option>否</option><option>是</option>
              </select></div>
            <div className="field"><label>定价</label><input type="number" step="0.0001" value={form.price} onChange={e => setForm({ ...form, price: e.target.value })} placeholder="元/条" /></div>
          </div>
          <div className="row">
            <div className="field"><label className="required">数量</label><input type="number" value={form.qty} onChange={e => setForm({ ...form, qty: e.target.value })} /></div>
            <div className="field"><label>PV</label><input type="number" value={form.pv} onChange={e => setForm({ ...form, pv: e.target.value })} /></div>
            <div className="field"><label>年龄下限</label><input type="number" value={form.age_min} onChange={e => setForm({ ...form, age_min: e.target.value })} /></div>
            <div className="field"><label>年龄上限</label><input type="number" value={form.age_max} onChange={e => setForm({ ...form, age_max: e.target.value })} /></div>
          </div>
          <div className="field" style={{ marginBottom: 12 }}><label>URL（多行，一行一个）</label>
            <textarea rows={3} value={form.url} onChange={e => setForm({ ...form, url: e.target.value })} placeholder="https://..." /></div>
          <div className="row">
            <div className="field"><label>省份（含全国）</label><MultiSelect full searchable options={provinceOptions} value={form.province} onChange={v => {
              const provs = v.split(',').filter(Boolean)
              const national = provs.includes('全国')
              setForm({ ...form, province: v, city: '', excl_city: '', excl_province: national ? form.excl_province : '' })
            }} placeholder="选择省份" /></div>
            <div className="field"><label>地市（全量，可搜索）</label><MultiSelect full searchable options={allCities} value={form.city} onChange={v => setForm({ ...form, city: v })} placeholder="选择地市" /></div>
          </div>
          <div className="row">
            <div className="field"><label>排除省（仅全国）</label><MultiSelect full searchable disabled={!isNational} options={geo.provinces} value={form.excl_province} onChange={v => setForm({ ...form, excl_province: v })} placeholder={isNational ? '选择排除省' : '省份非全国不可选'} /></div>
            <div className="field"><label>排除市（随省份联动）</label><MultiSelect full searchable disabled={!exclCityOptions.length} options={exclCityOptions} value={form.excl_city} onChange={v => setForm({ ...form, excl_city: v })} placeholder={exclCityOptions.length ? '选择排除市' : '请先选择省份'} /></div>
          </div>
          <div className="row">
            <div className="field"><label className="required">开始日期</label><input type="date" value={form.start_date} onChange={e => setForm({ ...form, start_date: e.target.value })} /></div>
            <div className="field"><label className="required">截止日期</label><input type="date" value={form.end_date} onChange={e => setForm({ ...form, end_date: e.target.value })} /></div>
            <div className="field"><label>时长（自动）</label><input value={computedDuration} disabled placeholder="自动计算" /></div>
          </div>
          <div className="foot">
            <button className="btn" onClick={() => setModal(null)}>取消</button>
            <button className="btn primary" onClick={save}>保存</button>
          </div>
        </Modal>
      )}

      {detail && (
        <Modal title={`订单 ${detail.order_no} 详情`} onClose={() => setDetail(null)} wide>
          {Array.from({ length: Math.ceil(BASE_COLS.length / 4) }, (_, ri) => (
            <div className="row" key={ri}>
              {BASE_COLS.slice(ri * 4, ri * 4 + 4).map(c => {
                const isRegion = ['province', 'city', 'excl_province', 'excl_city'].includes(c.k)
                const isBool = ['add_name', 'check_collision'].includes(c.k)
                const val = isRegion ? fmtRegion(detail[c.k]) : isBool ? (detail[c.k] ? '是' : '否') : (detail[c.k] ?? '—')
                return (
                  <div className="field" key={c.k}>
                    <label>{c.l}</label>
                    <div className="readonly" title={val} style={isRegion ? { height: 'auto', minHeight: 32, whiteSpace: 'pre-wrap' } : {}}>{val || '—'}</div>
                  </div>
                )
              })}
            </div>
          ))}
          <div className="row">
            <div className="field">
              <label>URL 列表</label>
              <div className="readonly" style={{ height: 'auto', minHeight: 32, whiteSpace: 'pre-wrap', padding: '6px 13px' }}>{(detail.urls || []).join('\n') || '—'}</div>
            </div>
          </div>
          <div className="foot"><button className="btn primary" onClick={() => setDetail(null)}>关闭</button></div>
        </Modal>
      )}

      {stopTarget && (
        <Modal title={stopTarget.batch ? '批量停单确认' : '停单确认'} onClose={() => setStopTarget(null)}>
          <div className="note">{stopTarget.batch ? `停单选中的 ${stopTarget.ids.length} 个订单，停单后将停止采集，并将更新日期更新为所选日期。` : '停单后该订单将停止采集，并将更新日期更新为所选日期。'}</div>
          <div className="field" style={{ marginBottom: 12 }}><label className="required">更新日期</label>
            <input type="date" value={stopDate} onChange={e => setStopDate(e.target.value)} /></div>
          <div className="field" style={{ marginBottom: 12 }}><label>停单原因</label>
            <select style={{ width: '100%' }} value={stopReason} onChange={e => setStopReason(e.target.value)}><option>业务调整</option><option>数据质量不达标</option><option>合同到期</option><option>其他</option></select></div>
          <div className="foot">
            <button className="btn" onClick={() => setStopTarget(null)}>取消</button>
            <button className="btn danger" onClick={stop}>确认停单</button>
          </div>
        </Modal>
      )}

      {urlDetail && (
        <Modal title={`订单 ${urlDetail.order_no} · URL 详情`} onClose={() => setUrlDetail(null)}>
          <table><thead><tr><th>URL</th></tr></thead>
            <tbody>{(urlDetail.urls || []).map((u, i) => <tr key={i}><td>{u}</td></tr>)}</tbody></table>
          {(urlDetail.urls || []).length === 0 && <div className="empty">暂无 URL</div>}
          <div className="foot"><button className="btn primary" onClick={() => setUrlDetail(null)}>关闭</button></div>
        </Modal>
      )}

      {regionDetail && (
        <Modal title={`订单 ${regionDetail.order_no} · 地区详情`} onClose={() => setRegionDetail(null)}>
          <table className="kv"><tbody>
            <tr><td>省份</td><td style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>{fmtRegion(regionDetail.province) || '—'}</td></tr>
            <tr><td>地市</td><td style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>{fmtRegion(regionDetail.city) || '—'}</td></tr>
            <tr><td>排除省份</td><td style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>{fmtRegion(regionDetail.excl_province) || '—'}</td></tr>
            <tr><td>排除地市</td><td style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>{fmtRegion(regionDetail.excl_city) || '—'}</td></tr>
          </tbody></table>
          <div className="foot"><button className="btn primary" onClick={() => setRegionDetail(null)}>关闭</button></div>
        </Modal>
      )}

      {tplDetail && (
        <Modal title={`模版信息 · ${tplDetail.code}`} onClose={() => setTplDetail(null)}>
          <table className="kv"><tbody>
            <tr><td>模版类型</td><td>{tplDetail.ttype || '—'}</td></tr>
            <tr><td>模版编号</td><td>{tplDetail.code || '—'}</td></tr>
            <tr><td>模版文件名</td><td>{tplDetail.name || '—'}</td></tr>
          </tbody></table>
          <div className="foot"><button className="btn primary" onClick={() => setTplDetail(null)}>关闭</button></div>
        </Modal>
      )}

      {importModal && (
        <Modal title="批量导入原始订单" onClose={() => setImportModal(false)}>
          <div className="note">支持 csv / xlsx。表头参考【模版】提单表.xlsx：提单日、甲方、一级代理、二级代理、订单号、定价、分组、平台、任务名、类型/渠道、url、数量、开始日期、截止日期、时长、年龄上下限、PV、省份、排除省、地市、排除地等。</div>
          <input type="file" accept=".csv,.xlsx,.xls" ref={importFileRef} />
          {importResult && (
            <div className="note" style={{ background: importResult.errors.length ? '#fef2f2' : '#ecfdf5', border: '1px solid ' + (importResult.errors.length ? '#fecaca' : '#a7f3d0') }}>
              导入 {importResult.imported} 条，更新 {importResult.updated || 0} 条，失败 {importResult.errors.length} 条
              {importResult.errors.slice(0, 10).map((e, i) => <div key={i}>第 {e.row} 行：{e.reason}</div>)}
            </div>
          )}
          <div className="foot">
            <button className="btn" onClick={() => setImportModal(false)}>关闭</button>
            <button className="btn primary" disabled={importResult !== null} onClick={() => {
              const f = importFileRef.current?.files?.[0]
              if (!f) { showError('请选择文件'); return }
              importOrders(f).then(() => toast('导入完成')).catch(e => showError(e.message))
            }}>{importResult !== null ? '已导入' : '开始导入'}</button>
          </div>
        </Modal>
      )}

      {receiptModal && (
        <Modal title="导入回执（按任务名更新工单号）" onClose={() => setReceiptModal(false)}>
          <div className="note">回执文件需包含「任务名」「任务ID/工单号」「运营商」「渠道（类型）」列，将按 甲方 + 任务名 + 运营商 + 渠道 且工单号为空 匹配订单并更新工单号；未匹配或多匹配会提示且不更新。</div>
          <div className="row">
            <div className="field"><label>甲方</label>
              <select value={receiptParty} onChange={e => setReceiptParty(e.target.value)}>
                {upstreams.map(c => <option key={c.id} value={c.name}>{c.name}</option>)}
              </select></div>
          </div>
          <input type="file" accept=".xlsx,.xls" ref={receiptFileRef} />
          {receiptResult && (
            <div className="note" style={{ background: '#ecfdf5', border: '1px solid #a7f3d0' }}>
              更新 {receiptResult.updated} 条
              <table style={{ marginTop: 6, width: '100%' }}>
                <thead><tr><th>甲方</th><th>工单号</th><th>任务名</th><th>运营商</th><th>类型</th></tr></thead>
                <tbody>
                  {(receiptResult.updated_list || []).map((e, i) => (
                    <tr key={i}><td>{e.party}</td><td>{e.task_id}</td><td>{e.task_name}</td><td>{e.operator}</td><td>{e.channel}</td></tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <div className="foot">
            <button className="btn" onClick={() => setReceiptModal(false)}>关闭</button>
            <button className="btn primary" disabled={receiptResult !== null} onClick={() => {
              const f = receiptFileRef.current?.files?.[0]
              if (!f) { showError('请选择文件'); return }
              importReceipt(f).then(() => toast('回执导入完成')).catch(e => showError(e.message))
            }}>{receiptResult !== null ? '已导入' : '开始导入'}</button>
          </div>
        </Modal>
      )}

      {genModal && (
        <Modal title="生成提单表" onClose={() => setGenModal(false)}>
          <div className="note">按勾选的订单生成文件（不改变订单状态）。勾选订单的更新日期必须与所选日期一致。状态规则：未提→提单表，改单→改单表，待停→停单表。</div>
          <div className="field" style={{ marginBottom: 14 }}><label>更新日期</label>
            <input type="date" value={genDate} onChange={e => setGenDate(e.target.value)} /></div>
          <div className="foot">
            <button className="btn" onClick={() => setGenModal(false)}>取消</button>
            <button className="btn primary" onClick={() => doGenerate().catch(e => showError(e.message))}>生成</button>
          </div>
        </Modal>
      )}

      {confirmModal && (
        <Modal title="提单确认" onClose={() => setConfirmModal(false)}>
          <div className="note">选择提单日期，对更新日期与提单日期一致的订单更新状态：未提/改单→在执，待停→已停；并同步写入提单历史。</div>
          <div className="field" style={{ marginBottom: 14 }}><label>提单日期</label>
            <input type="date" value={confirmDate} onChange={e => setConfirmDate(e.target.value)} /></div>
          <div className="foot">
            <button className="btn" onClick={() => setConfirmModal(false)}>取消</button>
            <button className="btn primary" onClick={() => doConfirm().catch(e => showError(e.message))}>确认</button>
          </div>
        </Modal>
      )}

      {groupModal && (
        <Modal title={`批量修改小组（${selected.length} 单）`} onClose={() => setGroupModal(false)}>
          <div className="field" style={{ marginBottom: 14 }}><label>小组</label>
            <input value={groupVal} onChange={e => setGroupVal(e.target.value)} placeholder="留空则清空小组" /></div>
          <div className="foot">
            <button className="btn" onClick={() => setGroupModal(false)}>取消</button>
            <button className="btn primary" onClick={batchGroup}>保存</button>
          </div>
        </Modal>
      )}
    </div>
  )
}
