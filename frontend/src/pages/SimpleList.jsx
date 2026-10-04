import React, { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, getToken, getUser, downloadFile, uploadFile } from '../api'
import { Modal, Badge, useToast, useConfirm, Loading } from '../components/ui'
import { useColumnConfig, downloadCsv } from '../components/columns'
import FilterBar, { buildQuery } from '../components/FilterBar'
import Pagination from '../components/Pagination'
import { MENU_PERMS } from '../menuPerms'

const IconChevronDown = (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><polyline points="6 9 12 15 18 9" /></svg>
)
const IconChevronUp = (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><polyline points="18 15 12 9 6 15" /></svg>
)
const IconColumns = (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2" /><line x1="12" y1="3" x2="12" y2="21" /><line x1="8" y1="3" x2="8" y2="21" /><line x1="16" y1="3" x2="16" y2="21" /></svg>
)

const KINDS = {
  daily: {
    title: '日活数据', endpoint: '/api/daily-data',
    cols: [
      { k: 'biz_date', l: '数据日期' }, { k: 'upstream', l: '甲方' }, { k: 'task_id', l: '任务id' },
      { k: 'task_name', l: '任务名' }, { k: 'phone', l: '手机号' }, { k: 'name', l: '姓名' }, { k: 'province', l: '省' },
      { k: 'city', l: '市' }, { k: 'operator', l: '运营商' }, { k: 'cat1', l: '一级品类' }, { k: 'cat2', l: '二级品类' }, { k: 'platform', l: '平台' },
      { k: 'customer', l: '一级代理' }, { k: 'secondary_agent', l: '二级代理' }, { k: 'channel', l: '渠道' },
      { k: 'source_file', l: '来源文件名' }, { k: 'created_at', l: '创建时间' }, { k: 'updated_at', l: '更新时间' },
    ], export: true, dailyImp: true, csvImp: true, batchDel: true, dist: true, check: true,
  },
  sourcefiles: {
    title: '元文件管理', endpoint: '/api/source-files',
    cols: [
      { k: 'filename', l: '文件名' }, { k: 'file_type', l: '类型' }, { k: 'biz_date', l: '数据日期' },
      { k: 'size', l: '大小' }, { k: 'created_at', l: '上传时间' },
    ], dl: true, del: true,
  },
  washnames: {
    title: '洗名库', endpoint: '/api/wash-names',
    cols: [
      { k: 'phone', l: '手机号' }, { k: 'name', l: '姓名' },
      { k: 'province', l: '省' }, { k: 'city', l: '市' }, { k: 'operator', l: '运营商' },
      { k: 'created_at', l: '创建日期' }, { k: 'updated_at', l: '更新日期' },
    ], batchDel: true, imp: true, impEndpoint: '/api/wash-names/import',
  },
  fund: {
    title: '公积金', endpoint: '/api/fund',
    cols: [
      { k: 'phone', l: '手机号' }, { k: 'name', l: '姓名' }, { k: 'id_card', l: '身份证号' }, { k: 'gender', l: '性别' },
      { k: 'province', l: '省份' }, { k: 'city', l: '地市' }, { k: 'company', l: '单位名称' }, { k: 'company_type', l: '单位性质' },
      { k: 'base', l: '缴存基数', num: true }, { k: 'ratio', l: '缴存比例' }, { k: 'monthly', l: '月缴存额', num: true },
      { k: 'balance', l: '账户余额', num: true }, { k: 'deposit_status', l: '缴存状态' }, { k: 'open_date', l: '开户日期' },
      { k: 'pay_to', l: '缴至年月' }, { k: 'operator', l: '运营商' },
    ], del: true, imp: true, exp: true,
  },
  channels: {
    title: '渠道', endpoint: '/api/channels',
    cols: [{ k: 'name', l: '渠道名' }, { k: 'status', l: '状态' }], simple: true,
  },
  operators: {
    title: '运营商', endpoint: '/api/operators',
    cols: [{ k: 'name', l: '运营商组合' }, { k: 'status', l: '状态' }], simple: true,
  },
  urls: {
    title: '配件管理', endpoint: '/api/urls',
    cols: [
      { k: 'name', l: '名称' }, { k: 'owner', l: '归属' }, { k: 'cat1', l: '一级品类' }, { k: 'cat2', l: '二级品类' },
      { k: 'platform', l: '平台' }, { k: 'channel', l: '渠道' }, { k: 'url', l: 'URL', multiline: true }, { k: 'level', l: '等级' }, { k: 'updated_at', l: '更新时间' },
    ], addUrl: true, del: true, editUrl: true, imp: true, impEndpoint: '/api/urls/import', clear: true,
  },
  bills: {
    title: '账单', endpoint: '/api/bills',
    cols: [
      { k: 'customer', l: '客户' }, { k: 'biz_date', l: '业务日期' }, { k: 'purchase_qty', l: '进货量', num: true },
      { k: 'sales', l: '销售金额', num: true }, { k: 'balance', l: '余额', num: true }, { k: 'profit', l: '利润', num: true }, { k: 'created_at', l: '创建日期' },
    ], batchDel: true, batchDelAdmin: true, detail: true, imp: true, impEndpoint: '/api/bills/import', billExp: true,
  },
  alerts: {
    title: '预警中心', endpoint: '/api/alerts',
    cols: [
      { k: 'type', l: '类型' }, { k: 'customer_name', l: '客户名' },
      { k: 'task_name', l: '任务名' }, { k: 'content', l: '内容' }, { k: 'time', l: '触发时间' }, { k: 'status', l: '状态' },
    ], handle: true,
  },
  users: {
    title: '账户管理', endpoint: '/api/users',
    cols: [
      { k: 'username', l: '用户名' }, { k: 'nickname', l: '昵称' }, { k: 'role', l: '角色' },
      { k: 'status', l: '状态' }, { k: 'last_login_at', l: '最后登录' },
    ], reset: true, pwd: true,
  },
}

export default function SimpleList({ kind }) {
  const cfg = KINDS[kind]
  const user = getUser() || {}
  const isAdmin = user.role_code === 'admin' || (user.permissions || []).includes('*')
  const showBatchDel = !!cfg.batchDel && (!cfg.batchDelAdmin || isAdmin)
  const hasRowOps = !!(cfg.simple || cfg.editUrl || cfg.del || cfg.dl || cfg.handle || cfg.reset || cfg.pwd || cfg.detail)
  const { toast, showError } = useToast()
  const nav = useNavigate()
  const [confirm, confirmEl] = useConfirm()
  const { visible: cols, picker, openPicker } = useColumnConfig(cfg.cols, `cols_${kind}`)
  const fileRef = useRef(null)
  const [rows, setRows] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [perPage, setPerPage] = useState(10)
  const [filters, setFilters] = useState({})
  const [filterCollapsed, setFilterCollapsed] = useState(false)
  const [fieldOptions, setFieldOptions] = useState({})
  const [customers, setCustomers] = useState([])
  const [simpleModal, setSimpleModal] = useState(null) // {name, status}
  const [urlModal, setUrlModal] = useState(null) // {mode, id?, name, level, owner_id, channel_id, platform_id, urls:[string]}
  const [urlOptions, setUrlOptions] = useState({ channels: [], platforms: [] })
  const [pwdModal, setPwdModal] = useState(null)
  const [rolePermModal, setRolePermModal] = useState(null)
  const [sort, setSort] = useState(null)
  const [alertTrigger, setAlertTrigger] = useState('00:00')
  const [alertDays, setAlertDays] = useState(0)
  const [busy, setBusy] = useState(false)
  const [busyMsg, setBusyMsg] = useState('正在导入，请稍候…')
  const [busyProgress, setBusyProgress] = useState(null)
  const [selected, setSelected] = useState([])
  const [dailyModal, setDailyModal] = useState(false)
  const [orderDetail, setOrderDetail] = useState(null)
  const [distModal, setDistModal] = useState(false)
  const [distDate, setDistDate] = useState(() => {
    const d = new Date()
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
  })
  const [billDetail, setBillDetail] = useState(null)
  const [dailyDate, setDailyDate] = useState(() => {
    const d = new Date()
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
  })
  const dailyFileRef = useRef(null)
  const [csvModal, setCsvModal] = useState(false)
  const [csvFile, setCsvFile] = useState(null)
  const csvFileRef = useRef(null)
  const [washModal, setWashModal] = useState(false)
  const [washDate, setWashDate] = useState(() => {
    const d = new Date()
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
  })
  const washFileRef = useRef(null)
  const [billExpModal, setBillExpModal] = useState(false)
  const [billExpStart, setBillExpStart] = useState('')
  const [billExpEnd, setBillExpEnd] = useState('')
  const [billExpCustId, setBillExpCustId] = useState(0)
  const [checkModal, setCheckModal] = useState(false)
  const [checkDate, setCheckDate] = useState(() => {
    const d = new Date()
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
  })
  const [checkResult, setCheckResult] = useState(null)

  useEffect(() => {
    if (kind === 'alerts') api.get('/api/alert-config').then(r => { setAlertTrigger(r.data.trigger_time); setAlertDays(r.data.alert_days ?? 0) }).catch(() => {})
  }, [kind])
  async function saveAlertConfig() {
    await api.put('/api/alert-config', { trigger_time: alertTrigger, alert_days: Number(alertDays) || 0 })
    toast('预警配置已保存')
  }
  async function manualScan() {
    if (!(await confirm('确认立即执行预警扫描？'))) return
    const r = await api.post('/api/alerts/scan')
    toast(`扫描完成，未处理预警 ${r.data.unhandled} 条`); load()
  }

  function toggleSort(k) {
    setSort(s => (s && s.k === k) ? (s.dir === 'asc' ? { k, dir: 'desc' } : null) : { k, dir: 'asc' })
  }
  function sortedRows() {
    if (!sort) return rows
    return [...rows].sort((a, b) => {
      const va = a[sort.k], vb = b[sort.k]
      const na = typeof va === 'number' ? va : (va == null ? '' : String(va))
      const nb = typeof vb === 'number' ? vb : (vb == null ? '' : String(vb))
      if (na < nb) return sort.dir === 'asc' ? -1 : 1
      if (na > nb) return sort.dir === 'asc' ? 1 : -1
      return 0
    })
  }

  async function load(p = page, pp = perPage, f) {
    const qs = buildQuery(f === undefined ? filters : f)
    const params = qs ? qs + `&page=${p}&per_page=${pp}` : `page=${p}&per_page=${pp}`
    const r = await api.get(`${cfg.endpoint}?${params}`)
    setRows(r.data.rows); setTotal(r.data.total)
  }
  function search(f) { setPage(1); load(1, perPage, f) }
  function goPage(p) { setPage(p); load(p, perPage) }
  function changePerPage(pp) { setPerPage(pp); setPage(1); load(1, pp) }
  useEffect(() => { setFilters({}); setPage(1); load(1, perPage, {}) }, [kind])

  // 加载下拉选项（渠道/客户/品类/省市等）
  useEffect(() => {
    const setOpt = (k, arr) => setFieldOptions(o => ({ ...o, [k]: arr }))
    api.get('/api/customers?per_page=1000').then(r => setCustomers(r.data.rows)).catch(() => {})
    const need = {
      fund: [],
      bills: ['customer'],
      urls: ['channel', 'cat1', 'cat2'],
    }[kind] || []
    if (need.includes('channel')) api.get('/api/channels?per_page=1000').then(r => setOpt('channel', r.data.rows.map(c => c.name))).catch(() => {})
    if (need.includes('customer')) api.get('/api/customers?per_page=1000').then(r => setOpt('customer', r.data.rows.map(c => c.code))).catch(() => {})
    if (kind === 'urls') {
      api.get('/api/channels?per_page=1000').then(r => setUrlOptions(o => ({ ...o, channels: r.data.rows }))).catch(() => {})
      api.get('/api/platforms').then(r => setUrlOptions(o => ({ ...o, platforms: r.data }))).catch(() => {})
      api.get('/api/customers?per_page=1000').then(r => setOpt('owner', r.data.rows.map(c => ({ value: c.code, label: `${c.code} ${c.name}` })))).catch(() => {})
    }
    if (need.includes('cat1') || need.includes('cat2')) {
      api.get('/api/categories').then(r => {
        const cat1 = [], cat2 = []
        r.data.forEach(c => { cat1.push(c.name); (c.children || []).forEach(x => cat2.push(x.name)) })
        setOpt('cat1', cat1); setOpt('cat2', cat2)
      }).catch(() => {})
    }
    // 日活数据：甲方/运营商/渠道/一级代理/平台/省市
    if (kind === 'daily') {
      api.get('/api/customers?per_page=1000').then(r => {
        setOpt('upstream', r.data.rows.filter(c => c.ctype === 'upstream').map(c => c.name))
        setOpt('customer', r.data.rows.filter(c => c.ctype === 'downstream').map(c => c.code))
      }).catch(() => {})
      api.get('/api/operators?per_page=1000').then(r => setOpt('operator', r.data.rows.map(o => o.name))).catch(() => {})
      api.get('/api/channels?per_page=1000').then(r => setOpt('channel', r.data.rows.map(c => c.name))).catch(() => {})
      api.get('/api/distinct?model=daily_data&field=platform').then(r => setOpt('platform', r.data)).catch(() => {})
      api.get('/api/regions').then(r => {
        const allCities = []
        Object.values(r.data.cities).forEach(list => allCities.push(...list))
        setOpt('province', r.data.provinces); setOpt('city', allCities)
      }).catch(() => {})
    }
    // 省份/地市来自基础数据（多选）
    if (kind === 'fund') {
      api.get('/api/regions').then(r => {
        const allCities = []
        Object.values(r.data.cities).forEach(list => allCities.push(...list))
        setOpt('province', r.data.provinces); setOpt('city', allCities)
      }).catch(() => {})
    }
    if (kind === 'washnames') {
      api.get('/api/regions').then(r => {
        const allCities = []
        Object.values(r.data.cities).forEach(list => allCities.push(...list))
        setOpt('province', r.data.provinces); setOpt('city', allCities)
      }).catch(() => {})
    }
    // 其他去重字段
    const distinctFields = { fund: ['company_type', 'operator'] }[kind] || []
    const distinctModel = kind === 'fund' ? 'fund' : 'daily_data'
    distinctFields.forEach(f => api.get(`/api/distinct?model=${distinctModel}&field=${f}`).then(r => setOpt(f, r.data)).catch(() => {}))
  }, [kind])

  async function addSimple() {
    if (await confirm('确认新增该记录？')) {
      await api.post(cfg.endpoint, { name: simpleModal.name, status: 1 })
      toast('已新增'); setSimpleModal(null); load()
    }
  }
  async function del(id) {
    if (await confirm('确认删除该记录？')) { await api.del(`${cfg.endpoint}/${id}`); toast('已删除'); load() }
  }
  function toggleSelect(id) {
    setSelected(s => s.includes(id) ? s.filter(x => x !== id) : [...s, id])
  }
  function toggleAll() {
    const ids = sortedRows().map(o => o.id)
    setSelected(selected.length === ids.length ? [] : ids)
  }
  async function batchDelete() {
    if (!selected.length) { showError('请先勾选要删除的数据'); return }
    if (!(await confirm(`确认删除选中的 ${selected.length} 条数据？此操作不可恢复。`))) return
    try {
      await api.post(`${cfg.endpoint}/batch-delete`, { ids: selected })
      toast('已删除'); setSelected([]); load()
    } catch (e) { showError(e.message) }
  }
  function openAddUrl() {
    setUrlModal({ mode: 'add', name: '', level: '高', owner_id: '', channel_id: '', platform_id: '', urls: [''] })
  }
  function openEditUrl(r) {
    setUrlModal({ mode: 'edit', id: r.id, name: r.name || '', level: r.level || '中',
      owner_id: r.owner_id || '', channel_id: r.channel_id || '', platform_id: r.platform_id || '',
      urls: (r.url || '').split('\n') })
  }
  function setUrlField(k, v) { setUrlModal({ ...urlModal, [k]: v }) }
  function setUrlRow(i, v) { const urls = [...urlModal.urls]; urls[i] = v; setUrlModal({ ...urlModal, urls }) }
  function addUrlRow() { setUrlModal({ ...urlModal, urls: [...urlModal.urls, ''] }) }
  function delUrlRow(i) { setUrlModal({ ...urlModal, urls: urlModal.urls.filter((_, j) => j !== i) }) }
  async function saveUrlModal() {
    const m = urlModal
    const url = m.urls.map(s => (s || '').trim()).filter(Boolean).join('\n')
    const payload = {
      name: m.name,
      owner_id: m.owner_id ? Number(m.owner_id) : null,
      platform_id: m.platform_id ? Number(m.platform_id) : null,
      channel_id: m.channel_id ? Number(m.channel_id) : null,
      urls: [{ url, level: m.level }],
    }
    if (m.mode === 'edit') await api.put(`/api/urls/${m.id}`, payload)
    else await api.post(cfg.endpoint, payload)
    toast(m.mode === 'edit' ? '已保存' : '已新增'); setUrlModal(null); load()
  }
  async function handleAlert(r) {
    try {
      await api.put(`/api/alerts/${r.id}`)
      load()
      window.dispatchEvent(new Event('alert-count-refresh'))
    } catch (e) { showError(e.message) }
    if (r.type === '账单预警') {
      nav(`/customers?recharge=${r.customer_id}`)
      return
    }
    nav('/orders')
  }
  async function resetPwd(id) {
    if (await confirm('确认重置该账户密码？')) { await api.post(`/api/users/${id}/reset-password`); toast('密码已重置') }
  }
  async function savePwd() {
    if (!pwdModal.password || pwdModal.password.length < 6) { showError('密码长度至少 6 位'); return }
    if (pwdModal.password !== pwdModal.confirm) { showError('两次输入的新密码不一致'); return }
    try {
      await api.post(`/api/users/${pwdModal.id}/set-password`, { password: pwdModal.password })
      toast('密码已修改'); setPwdModal(null)
    } catch (e) { showError(e.message) }
  }

  async function openRolePerms() {
    try {
      const r = await api.get('/api/roles')
      const roles = r.data || []
      const editable = roles.filter(x => x.code !== 'admin')
      if (!editable.length) { showError('无可配置角色'); return }
      const pr = await api.get(`/api/roles/${editable[0].id}/permissions`)
      setRolePermModal({ roles, rid: editable[0].id, codes: pr.data.codes || [] })
    } catch (e) { showError(e.message) }
  }
  async function selectRolePerms(rid) {
    try {
      const pr = await api.get(`/api/roles/${rid}/permissions`)
      setRolePermModal({ ...rolePermModal, rid, codes: pr.data.codes || [] })
    } catch (e) { showError(e.message) }
  }
  function togglePerm(code) {
    const codes = rolePermModal.codes.includes(code)
      ? rolePermModal.codes.filter(c => c !== code)
      : [...rolePermModal.codes, code]
    setRolePermModal({ ...rolePermModal, codes })
  }
  async function saveRolePerms() {
    try {
      await api.put(`/api/roles/${rolePermModal.rid}/permissions`, { codes: rolePermModal.codes })
      toast('权限已保存'); setRolePermModal(null)
    } catch (e) { showError(e.message) }
  }

  function cell(c, r) {
    const v = r[c.k]
    if (kind === 'bills' && c.k === 'customer') {
      return <a className="link" onClick={() => nav(`/customers?detail=${r.customer_id}`)}>{v}</a>
    }
    if (kind === 'daily' && c.k === 'task_id' && v) {
      return <a className="link" onClick={() => openOrderByTaskId(v)}>{v}</a>
    }
    if (kind === 'daily' && c.k === 'source_file' && r.source_file_id) {
      return <a className="link" onClick={() => downloadFile(`/api/source-files/${r.source_file_id}/download`).catch(e => showError(e.message))}>{v || '—'}</a>
    }
    if (c.k === 'size') {
      if (v == null) return '—'
      if (v < 1024) return `${v} B`
      if (v < 1024 * 1024) return `${(v / 1024).toFixed(1)} KB`
      return `${(v / 1024 / 1024).toFixed(1)} MB`
    }
    if (['status'].includes(c.k)) return <Badge value={v === 1 ? '启用' : v === 0 ? '停用' : v} />
    if (['level', 'gender', 'deposit_status', 'wash_status', 'type'].includes(c.k)) return <Badge value={v} />
    if (c.num && typeof v === 'number') return v.toLocaleString()
    if (c.multiline) return <div style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all', textAlign: 'left' }}>{v || '—'}</div>
    return v ?? '—'
  }

  function exportExcel() {
    const qs = buildQuery(filters)
    if (kind === 'fund') { downloadFile('/api/fund/export?' + qs).catch(e => showError(e.message)); toast('正在导出...'); return }
    if (kind === 'daily') { downloadFile('/api/daily-data/export?' + qs).catch(e => showError(e.message)); toast('正在导出...'); return }
    downloadCsv(`${cfg.title}.csv`, cfg.cols, rows)
    toast('已导出')
  }

  async function importFile(file) {
    setBusy(true); setBusyMsg('正在上传文件…'); setBusyProgress(0)
    try {
      const fd = new FormData()
      fd.append('file', file)
      const data = await uploadFile(cfg.impEndpoint || '/api/fund/import', fd, p => setBusyProgress(p))
      setBusyMsg('正在处理数据，请稍候…'); setBusyProgress(100)
      toast(data.msg); load()
    } finally {
      setBusy(false); setBusyProgress(null)
    }
  }

  async function importDaily() {
    const fs = dailyFileRef.current?.files
    if (!fs || !fs.length) { showError('请选择文件'); return }
    if (!dailyDate) { showError('请选择数据日期'); return }
    setDailyModal(false)
    const files = Array.from(fs)
    const buildFd = (confirmFlag) => {
      const fd = new FormData()
      for (const f of files) fd.append('files', f)
      fd.append('biz_date', dailyDate)
      if (confirmFlag) fd.append('confirm', 'true')
      return fd
    }
    try {
      setBusy(true); setBusyMsg('正在上传文件…'); setBusyProgress(0)
      let data = await uploadFile('/api/daily-data/import', buildFd(false), p => setBusyProgress(p))
      if (data.data && data.data.needs_confirm) {
        setBusy(false); setBusyProgress(null)
        const n = data.data.unmatched || 0
        const tids = data.data.unmatched_tids || []
        const sn = data.data.stopped_abnormal || 0
        const stids = data.data.stopped_tids || []
        let msg = ''
        if (n > 0) {
          const tidsStr = tids.length ? `\n未匹配工单号：${tids.join('、')}` : ''
          msg += `有 ${n} 条数据未匹配到订单${tidsStr}\n`
        }
        if (sn > 0) {
          const stidsStr = stids.length ? `\n已停订单工单号：${stids.join('、')}` : ''
          msg += `\n有 ${sn} 条数据关联到已停订单（异常）${stidsStr}`
        }
        if (!(await confirm(`${msg}\n\n是否继续导入？`))) return
        setBusy(true); setBusyMsg('正在导入…'); setBusyProgress(0)
        data = await uploadFile('/api/daily-data/import', buildFd(true), p => setBusyProgress(p))
      }
      setBusyMsg('正在处理数据，请稍候…'); setBusyProgress(100)
      const inactive = (data.data && data.data.inactive_tids) || []
      toast(data.msg); load()
      if (inactive.length) {
        showError(`以下在执任务未匹配到数据：\n${inactive.join('、')}`)
      }
    } catch (e) { showError(e.message) } finally { setBusy(false); setBusyProgress(null) }
  }

  async function importDailyCsv() {
    if (!csvFile) { showError('请选择 csv 文件'); return }
    setCsvModal(false)
    try {
      setBusy(true); setBusyMsg('正在导入 CSV…'); setBusyProgress(0)
      const fd = new FormData()
      fd.append('files', csvFile)
      const data = await uploadFile('/api/daily-data/import-csv', fd, p => setBusyProgress(p))
      setBusyMsg('正在入库，请稍候…'); setBusyProgress(100)
      toast(data.msg); load()
    } catch (e) { showError(e.message) } finally { setBusy(false); setBusyProgress(null) }
  }

  async function doDistribute() {
    if (!distDate) { showError('请选择数据日期'); return }
    setDistModal(false)
    try {
      let r = await api.post('/api/daily-data/distribute', { date: distDate })
      if (r.data.needs_confirm) {
        const issues = r.data.issues || []
        const detail = issues.map(i => `「${i.group_name}」${i.unset_count} 个订单未设定出数模版（将按 ${i.tpl_code} 出数）`).join('、')
        if (!(await confirm(`以下小组存在未设定出数模版的订单：${detail}。\n\n是否继续分数据（未设定的订单将按小组已设定的出数模版处理）？`))) return
        r = await api.post('/api/daily-data/distribute', { date: distDate, confirm: true })
      }
      setBusy(true); setBusyMsg('正在分数据…'); setBusyProgress(0)
      const taskId = r.data.task_id
      const total = r.data.total
      while (true) {
        const p = await api.get(`/api/daily-data/distribute/progress/${taskId}`)
        const { done, status, error } = p.data
        setBusyProgress(total > 0 ? Math.round((done / total) * 100) : 100)
        if (status === 'done') {
          setBusyMsg('分数据完成，正在下载…')
          await downloadFile(`/api/daily-data/distribute/download/${taskId}`)
          toast('分数据完成，请查看下载')
          break
        } else if (status === 'error') {
          throw new Error(error || '分数据失败')
        }
        await new Promise(res => setTimeout(res, 500))
      }
    } catch (e) { showError(e.message || '分数据失败') } finally { setBusy(false); setBusyProgress(null) }
  }

  async function doWashExport() {
    if (!washDate) { showError('请选择数据日期'); return }
    setWashModal(false)
    try {
      const r = await api.get(`/api/daily-data/wash-stats?date=${encodeURIComponent(washDate)}`)
      const s = r.data || {}
      await downloadFile(`/api/daily-data/wash-export?date=${encodeURIComponent(washDate)}`)
      showError(`洗名导出完成\n\n一共要导出：${s.total ?? 0} 条\n已匹配洗名库：${s.matched ?? 0} 条\n需要去小逸洗名：${s.need_wash ?? 0} 条`)
    } catch (e) { showError(e.message) }
  }

  async function doBillExport() {
    if (!billExpStart || !billExpEnd) { showError('请选择开始和结束日期'); return }
    setBillExpModal(false)
    try {
      const p = new URLSearchParams()
      p.set('start_date', billExpStart)
      p.set('end_date', billExpEnd)
      if (billExpCustId) p.set('customer_id', billExpCustId)
      await downloadFile(`/api/bills/export?${p.toString()}`)
      toast('账单已导出')
    } catch (e) { showError(e.message) }
  }

  async function doCheck() {
    if (!checkDate) { showError('请选择数据日期'); return }
    try {
      const r = await api.get(`/api/daily-data/check?date=${encodeURIComponent(checkDate)}`)
      setCheckResult(r.data || [])
    } catch (e) { showError(e.message) }
  }

  async function doCheckExport() {
    if (!checkDate) { showError('请选择数据日期'); return }
    try {
      await downloadFile(`/api/daily-data/check-export?date=${encodeURIComponent(checkDate)}`)
      toast('检查结果已导出')
    } catch (e) { showError(e.message) }
  }

  async function importWash() {
    const f = washFileRef.current?.files?.[0]
    if (!f) { showError('请选择洗名文件'); return }
    setBusy(true); setBusyMsg('正在导入洗名…'); setBusyProgress(null)
    try {
      const fd = new FormData()
      fd.append('file', f)
      const data = await uploadFile('/api/daily-data/import-wash', fd)
      toast(data.msg); load()
    } catch (e) { showError(e.message) } finally { setBusy(false); setBusyProgress(null) }
  }

  function downloadSourceFile(r) {
    downloadFile(`/api/source-files/${r.id}/download`).catch(e => showError(e.message))
  }

  async function viewBillDetail(id) {
    try {
      const r = await api.get(`/api/bills/${id}`)
      setBillDetail(r.data)
    } catch (e) { showError(e.message) }
  }

  async function openOrderByTaskId(taskId) {
    if (!taskId) return
    try {
      const r = await api.get('/api/orders?task_id=' + encodeURIComponent(taskId) + '&per_page=1')
      if (r.data.rows.length) setOrderDetail(r.data.rows[0])
      else showError('未找到订单 ' + taskId)
    } catch (e) { showError(e.message) }
  }

  async function clearData() {
    if (!(await confirm(`确认清空「${cfg.title}」的全部数据？此操作不可恢复。`))) return
    try {
      await api.del(cfg.endpoint)
      toast('已清空'); load()
    } catch (e) { showError(e.message) }
  }

  return (
    <div className="page">
      {confirmEl}
      {picker}
      {busy && <Loading text={busyMsg} progress={busyProgress} />}
      <input type="file" accept=".csv,.xlsx,.xls" style={{ display: 'none' }} ref={fileRef} onChange={e => { if (e.target.files[0]) importFile(e.target.files[0]).catch(err => showError(err.message)); e.target.value = '' }} />
      <input type="file" accept=".csv,.xlsx,.xls" style={{ display: 'none' }} ref={washFileRef} onChange={e => { if (e.target.files[0]) importWash().catch(err => showError(err.message)); e.target.value = '' }} />
      <div className="toolbar">
        <div className={`filter-wrap ${filterCollapsed ? 'collapsed' : ''}`}>
          <FilterBar cols={cfg.cols} filters={filters} setFilters={setFilters} onSearch={search} fieldOptions={fieldOptions} actions={false} />
        </div>
        <div className="toolbar-actions">
        <button className="btn primary" onClick={() => search()}>查询</button>
        <button className="btn" onClick={() => { setFilters({}); search({}) }}>重置</button>
        {kind === 'washnames' && (
          <label style={{ fontSize: 12, color: 'var(--sub)', display: 'inline-flex', alignItems: 'center', gap: 4, cursor: 'pointer' }}>
            <input type="checkbox" checked={filters.name_empty === '1'} onChange={e => setFilters({ ...filters, name_empty: e.target.checked ? '1' : '' })} />
            仅看空姓名
          </label>
        )}
        <button className="btn icon" title={filterCollapsed ? '展开查询条件' : '隐藏查询条件'} onClick={() => setFilterCollapsed(!filterCollapsed)}>{filterCollapsed ? IconChevronDown : IconChevronUp}</button>
        {cfg.exp && <button className="btn green" onClick={exportExcel}>导出 Excel</button>}
        {cfg.dailyImp && <button className="btn primary" onClick={() => setDailyModal(true)}>① 导入日活</button>}
        {cfg.csvImp && isAdmin && <button className="btn" onClick={() => { setCsvFile(null); setCsvModal(true) }}>导入CSV</button>}
        {cfg.dist && <button className="btn" onClick={() => setWashModal(true)}>② 导出洗名</button>}
        {cfg.dist && <button className="btn" onClick={() => washFileRef.current.click()}>③ 导入洗名</button>}
        {cfg.dist && <button className="btn green" onClick={() => setDistModal(true)}>④ 分发数据</button>}
        {cfg.check && <button className="btn" onClick={() => { setCheckResult(null); setCheckModal(true) }}>工单检查</button>}
        {showBatchDel && selected.length > 0 && <button className="btn danger" onClick={batchDelete}>批量删除({selected.length})</button>}
        {cfg.imp && <button className="btn" onClick={() => fileRef.current.click()}>导入 Excel</button>}
        {cfg.export && <button className="btn green" onClick={exportExcel}>导出 Excel</button>}
        {cfg.billExp && <button className="btn green" onClick={() => setBillExpModal(true)}>导出账单</button>}
        {cfg.simple && <button className="btn primary" onClick={() => setSimpleModal({ name: '', status: 1 })}>+ 新增</button>}
        {cfg.addUrl && <button className="btn primary" onClick={openAddUrl}>+ 新增 URL</button>}
        {cfg.clear && <button className="btn danger" onClick={clearData}>清空数据</button>}
        {kind === 'users' && <button className="btn" onClick={openRolePerms}>角色权限</button>}
        {kind === 'alerts' && (
          <>
            <label style={{ fontSize: 12, color: 'var(--sub)' }}>触发时间</label>
            <input type="time" value={alertTrigger} onChange={e => setAlertTrigger(e.target.value)} />
            <label style={{ fontSize: 12, color: 'var(--sub)' }}>提前预警天数</label>
            <input type="number" style={{ width: 70 }} value={alertDays} onChange={e => setAlertDays(e.target.value)} />
            <button className="btn small" onClick={saveAlertConfig}>保存</button>
            <button className="btn" onClick={manualScan}>立即执行</button>
          </>
        )}
        <button className="btn icon" title="自定义表头" onClick={openPicker}>{IconColumns}</button>
        </div>
      </div>
      <div className="panel">
        <div className="table-scroll">
          <table>
            <thead><tr>{showBatchDel && <th style={{ width: 32 }}><input type="checkbox" checked={rows.length > 0 && selected.length === sortedRows().length} onChange={toggleAll} /></th>}{cols.map(c => <th key={c.k} className={c.num ? 'num' : ''} onClick={() => toggleSort(c.k)}>{c.l}{sort?.k === c.k ? <span className="arr">{sort.dir === 'asc' ? '▲' : '▼'}</span> : ''}</th>)}{hasRowOps && <th className="ops">操作</th>}</tr></thead>
            <tbody>
              {sortedRows().map(r => (
                <tr key={r.id}>
                  {showBatchDel && <td><input type="checkbox" checked={selected.includes(r.id)} onChange={() => toggleSelect(r.id)} /></td>}
                  {cols.map(c => <td key={c.k} className={c.num ? 'num' : ''}>{cell(c, r)}</td>)}
                  {hasRowOps && <td className="ops">
                    {cfg.detail && <button className="btn small" onClick={() => viewBillDetail(r.id)}>详情</button>}
                    {cfg.simple && <button className="btn small" onClick={() => toast('编辑')}>编辑</button>}
                    {cfg.editUrl && <button className="btn small" onClick={() => openEditUrl(r)}>编辑</button>}
                    {cfg.del && <button className="btn small danger" onClick={() => del(r.id)}>删除</button>}
                    {cfg.dl && <button className="btn small" onClick={() => downloadSourceFile(r)}>下载</button>}
                    {cfg.handle && <button className="btn small primary" onClick={() => handleAlert(r)}>处理</button>}
                    {cfg.reset && <button className="btn small" onClick={() => resetPwd(r.id)}>重置密码</button>}
                    {cfg.pwd && <button className="btn small primary" onClick={() => setPwdModal({ id: r.id, username: r.username, password: '', confirm: '' })}>修改密码</button>}
                  </td>}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {rows.length === 0 && <div className="empty">暂无数据</div>}
        <Pagination total={total} page={page} perPage={perPage} setPage={setPage} setPerPage={changePerPage} goPage={goPage} />
      </div>

      {simpleModal && (
        <Modal title="新增" onClose={() => setSimpleModal(null)}>
          <div className="row">
            <div className="field"><label>名称</label><input value={simpleModal.name} onChange={e => setSimpleModal({ ...simpleModal, name: e.target.value })} /></div>
            <div className="field"><label>状态</label><select value={simpleModal.status} onChange={e => setSimpleModal({ ...simpleModal, status: Number(e.target.value) })}><option value={1}>启用</option><option value={0}>停用</option></select></div>
          </div>
          <div className="foot"><button className="btn" onClick={() => setSimpleModal(null)}>取消</button><button className="btn primary" onClick={addSimple}>保存</button></div>
        </Modal>
      )}

      {dailyModal && (
        <Modal title="导入日活数据" onClose={() => setDailyModal(false)}>
          <div className="note">支持上传 zip（牛的数据包）或 excel（新的数据文件）。文件会先保存到「元文件管理」，再解析导入。</div>
          <div className="field" style={{ marginBottom: 12 }}><label className="required">数据日期</label>
            <input type="date" value={dailyDate} onChange={e => setDailyDate(e.target.value)} /></div>
          <div className="field" style={{ marginBottom: 14 }}><label className="required">文件（zip / xlsx / xls，可多选）</label>
            <input type="file" accept=".zip,.xlsx,.xls" multiple ref={dailyFileRef} /></div>
          <div className="foot">
            <button className="btn" onClick={() => setDailyModal(false)}>取消</button>
            <button className="btn primary" onClick={() => importDaily().catch(e => showError(e.message))}>开始导入</button>
          </div>
        </Modal>
      )}

      {csvModal && (
        <Modal title="导入 CSV（原样入库）" onClose={() => setCsvModal(false)}>
          <div className="note">按「日活数据」表结构逐行原样写入（不做订单关联/洗名补全/去重之外的加工）。表头需含：数据日期、甲方、任务id、任务名、手机号、姓名、省、市、运营商等。按（数据日期+任务id+手机号）自动去重。</div>
          <div className="field" style={{ marginBottom: 14 }}><label className="required">CSV 文件</label>
            <input type="file" accept=".csv" ref={csvFileRef} onChange={e => setCsvFile(e.target.files[0] || null)} /></div>
          <div className="foot">
            <button className="btn" onClick={() => setCsvModal(false)}>取消</button>
            <button className="btn primary" onClick={() => importDailyCsv().catch(e => showError(e.message))}>开始导入</button>
          </div>
        </Modal>
      )}

      {distModal && (
        <Modal title="分数据" onClose={() => setDistModal(false)}>
          <div className="note">选择数据日期，将该日期下的日活数据按订单的小组分组，用对应订单的出数模版生成文件打包下载。</div>
          <div className="field" style={{ marginBottom: 14 }}><label className="required">数据日期</label>
            <input type="date" value={distDate} onChange={e => setDistDate(e.target.value)} /></div>
          <div className="foot">
            <button className="btn" onClick={() => setDistModal(false)}>取消</button>
            <button className="btn primary" onClick={() => doDistribute().catch(e => showError(e.message))}>分数据</button>
          </div>
        </Modal>
      )}

      {washModal && (
        <Modal title="洗名" onClose={() => setWashModal(false)}>
          <div className="note">导出所选日期下，姓名为空且关联订单「是否加名=是」的手机号。</div>
          <div className="field" style={{ marginBottom: 14 }}><label className="required">数据日期</label>
            <input type="date" value={washDate} onChange={e => setWashDate(e.target.value)} /></div>
          <div className="foot">
            <button className="btn" onClick={() => setWashModal(false)}>取消</button>
            <button className="btn primary" onClick={() => doWashExport().catch(e => showError(e.message))}>导出</button>
          </div>
        </Modal>
      )}

      {billExpModal && (
        <Modal title="导出账单明细" onClose={() => setBillExpModal(false)}>
          <div className="note">按日期期间导出账单明细（含充值记录和余额）；不选代理则导出全部代理。</div>
          <div className="row">
            <div className="field"><label className="required">开始日期</label>
              <input type="date" value={billExpStart} onChange={e => setBillExpStart(e.target.value)} /></div>
            <div className="field"><label className="required">结束日期</label>
              <input type="date" value={billExpEnd} onChange={e => setBillExpEnd(e.target.value)} /></div>
          </div>
          <div className="field" style={{ marginBottom: 14 }}><label>代理</label>
            <select value={billExpCustId} onChange={e => setBillExpCustId(Number(e.target.value))}>
              <option value={0}>全部代理</option>
              {customers.map(c => <option key={c.id} value={c.id}>{c.code} {c.name}</option>)}
            </select></div>
          <div className="foot">
            <button className="btn" onClick={() => setBillExpModal(false)}>取消</button>
            <button className="btn primary" onClick={() => doBillExport().catch(e => showError(e.message))}>导出</button>
          </div>
        </Modal>
      )}

      {checkModal && (
        <Modal title="工单检查" onClose={() => setCheckModal(false)} wide>
          <div className="note">统计所有「在执」工单在所选数据日期的数据量情况（按数据量降序）。</div>
          <div className="row">
            <div className="field"><label className="required">数据日期</label>
              <input type="date" value={checkDate} onChange={e => setCheckDate(e.target.value)} /></div>
            <div className="field" style={{ display: 'flex', alignItems: 'flex-end' }}>
              <button className="btn primary" onClick={() => doCheck().catch(e => showError(e.message))}>检查</button>
            </div>
          </div>
          {checkResult && (
            <div className="table-scroll" style={{ maxHeight: 420 }}>
              <table>
                <thead><tr><th>工单号</th><th>任务名</th><th className="num">数据量</th></tr></thead>
                <tbody>
                  {checkResult.map((r, i) => (
                    <tr key={i}>
                      <td>{r.task_id || '—'}</td>
                      <td>{r.task_name || '—'}</td>
                      <td className="num">{r.count}</td>
                    </tr>
                  ))}
                  {checkResult.length === 0 && <tr><td colSpan={3} className="empty">无匹配的在执工单</td></tr>}
                </tbody>
              </table>
            </div>
          )}
          <div className="foot">
            {checkResult && checkResult.length > 0 && <button className="btn green" onClick={() => doCheckExport().catch(e => showError(e.message))}>导出检查结果</button>}
            <button className="btn primary" onClick={() => setCheckModal(false)}>关闭</button>
          </div>
        </Modal>
      )}

      {billDetail && (
        <Modal title="账单详情" onClose={() => setBillDetail(null)} wide>
          <div className="row">
            <div className="field"><label>代理</label><div className="readonly">{billDetail.customer || '—'}</div></div>
            <div className="field"><label>业务日期</label><div className="readonly">{billDetail.biz_date || '—'}</div></div>
            <div className="field"><label>进货量</label><div className="readonly">{billDetail.purchase_qty ?? '—'}</div></div>
            <div className="field"><label>销售金额</label><div className="readonly">{billDetail.sales != null ? billDetail.sales : '—'}</div></div>
          </div>
          <div className="row">
            <div className="field"><label>余额</label><div className="readonly">{billDetail.balance != null ? billDetail.balance : '—'}</div></div>
            <div className="field"><label>利润</label><div className="readonly">{billDetail.profit != null ? billDetail.profit : '—'}</div></div>
          </div>
          <div className="panel" style={{ marginTop: 8 }}>
            <div className="table-scroll">
              <table>
                <thead><tr><th>任务名</th><th className="num">手机号数量</th><th className="num">金额(元)</th></tr></thead>
                <tbody>
                  {(billDetail.groups || []).map(g => (
                    <tr key={g.task_name}>
                      <td>{g.task_name}</td>
                      <td className="num">{g.qty}</td>
                      <td className="num">{g.amount}</td>
                    </tr>
                  ))}
                  {(billDetail.groups || []).length === 0 && <tr><td colSpan={3} className="empty">暂无明细</td></tr>}
                </tbody>
              </table>
            </div>
          </div>
          <div className="foot"><button className="btn primary" onClick={() => setBillDetail(null)}>关闭</button></div>
        </Modal>
      )}

      {orderDetail && (
        <Modal title={`订单 ${orderDetail.order_no} 详情`} onClose={() => setOrderDetail(null)} wide>
          <div className="row">
            <div className="field"><label>订单号</label><div className="readonly">{orderDetail.order_no || '—'}</div></div>
            <div className="field"><label>状态</label><div className="readonly">{orderDetail.status || '—'}</div></div>
            <div className="field"><label>任务名</label><div className="readonly">{orderDetail.task_name || '—'}</div></div>
            <div className="field"><label>工单号</label><div className="readonly">{orderDetail.task_id || '—'}</div></div>
          </div>
          <div className="row">
            <div className="field"><label>更新日期</label><div className="readonly">{orderDetail.order_date || '—'}</div></div>
            <div className="field"><label>甲方</label><div className="readonly">{orderDetail.upstream || '—'}</div></div>
            <div className="field"><label>一级代理</label><div className="readonly">{orderDetail.customer || '—'}</div></div>
            <div className="field"><label>二级代理</label><div className="readonly">{orderDetail.secondary_agent || '—'}</div></div>
          </div>
          <div className="row">
            <div className="field"><label>渠道</label><div className="readonly">{orderDetail.channel || '—'}</div></div>
            <div className="field"><label>运营商</label><div className="readonly">{orderDetail.operator || '—'}</div></div>
            <div className="field"><label>平台</label><div className="readonly">{orderDetail.platform || '—'}</div></div>
            <div className="field"><label>定价</label><div className="readonly">{orderDetail.price != null ? orderDetail.price : '—'}</div></div>
          </div>
          <div className="row">
            <div className="field"><label>数量</label><div className="readonly">{orderDetail.qty ?? '—'}</div></div>
            <div className="field"><label>年龄下限</label><div className="readonly">{orderDetail.age_min ?? '—'}</div></div>
            <div className="field"><label>年龄上限</label><div className="readonly">{orderDetail.age_max ?? '—'}</div></div>
            <div className="field"><label>pv</label><div className="readonly">{orderDetail.pv ?? '—'}</div></div>
          </div>
          <div className="row">
            <div className="field"><label>省份</label><div className="readonly">{orderDetail.province || '—'}</div></div>
            <div className="field"><label>地市</label><div className="readonly">{orderDetail.city || '—'}</div></div>
            <div className="field"><label>排除省份</label><div className="readonly">{orderDetail.excl_province || '—'}</div></div>
            <div className="field"><label>排除地市</label><div className="readonly">{orderDetail.excl_city || '—'}</div></div>
          </div>
          <div className="row">
            <div className="field"><label>开始日期</label><div className="readonly">{orderDetail.start_date || '—'}</div></div>
            <div className="field"><label>截止日期</label><div className="readonly">{orderDetail.end_date || '—'}</div></div>
            <div className="field"><label>小组</label><div className="readonly">{orderDetail.group_name || '—'}</div></div>
            <div className="field"><label>是否加名</label><div className="readonly">{orderDetail.add_name ? '是' : '否'}</div></div>
          </div>
          <div className="row">
            <div className="field">
              <label>URL 列表</label>
              <div className="readonly" style={{ height: 'auto', minHeight: 32, whiteSpace: 'pre-wrap', padding: '6px 13px' }}>{(orderDetail.urls || []).join('\n') || '—'}</div>
            </div>
          </div>
          <div className="foot"><button className="btn primary" onClick={() => setOrderDetail(null)}>关闭</button></div>
        </Modal>
      )}

      {urlModal && (
        <Modal title={urlModal.mode === 'edit' ? '编辑配件' : '新增配件'} onClose={() => setUrlModal(null)} wide>
          <div className="row">
            <div className="field"><label>名称</label><input value={urlModal.name} onChange={e => setUrlField('name', e.target.value)} /></div>
            <div className="field"><label>等级</label><select value={urlModal.level} onChange={e => setUrlField('level', e.target.value)}><option>高</option><option>中</option><option>低</option></select></div>
          </div>
          <div className="row">
            <div className="field"><label>归属</label>
              <select value={urlModal.owner_id} onChange={e => setUrlField('owner_id', e.target.value)}>
                <option value="">请选择</option>{customers.map(c => <option key={c.id} value={c.id}>{c.code} {c.name}</option>)}
              </select></div>
            <div className="field"><label>渠道</label>
              <select value={urlModal.channel_id} onChange={e => setUrlField('channel_id', e.target.value)}>
                <option value="">请选择</option>{urlOptions.channels.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select></div>
            <div className="field"><label>平台</label>
              <select value={urlModal.platform_id} onChange={e => setUrlField('platform_id', e.target.value)}>
                <option value="">请选择</option>{urlOptions.platforms.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select></div>
          </div>
          <div className="field" style={{ marginBottom: 8 }}><label>URL（每行一个）</label></div>
          {urlModal.urls.map((u, i) => (
            <div className="row" key={i}>
              <div className="field" style={{ flex: 1 }}><input placeholder="https://..." value={u} onChange={e => setUrlRow(i, e.target.value)} /></div>
              <button className="btn small danger" style={{ alignSelf: 'center' }} onClick={() => delUrlRow(i)}>删除</button>
            </div>
          ))}
          <button className="btn small" onClick={addUrlRow}>+ 添加 URL</button>
          <div className="foot"><button className="btn" onClick={() => setUrlModal(null)}>取消</button><button className="btn primary" onClick={saveUrlModal}>保存</button></div>
        </Modal>
      )}

      {pwdModal && (
        <Modal title={`修改密码 · ${pwdModal.username}`} onClose={() => setPwdModal(null)}>
          <div className="field" style={{ marginBottom: 10 }}><label>新密码</label><input type="password" value={pwdModal.password} onChange={e => setPwdModal({ ...pwdModal, password: e.target.value })} placeholder="至少 6 位" /></div>
          <div className="field" style={{ marginBottom: 14 }}><label>确认新密码</label><input type="password" value={pwdModal.confirm} onChange={e => setPwdModal({ ...pwdModal, confirm: e.target.value })} /></div>
          <div className="foot">
            <button className="btn" onClick={() => setPwdModal(null)}>取消</button>
            <button className="btn primary" onClick={savePwd}>确认修改</button>
          </div>
        </Modal>
      )}

      {rolePermModal && (
        <Modal title="角色菜单权限" onClose={() => setRolePermModal(null)}>
          <div className="field"><label>角色</label>
            <select value={rolePermModal.rid} onChange={e => selectRolePerms(Number(e.target.value))}>
              {rolePermModal.roles.filter(r => r.code !== 'admin').map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
            </select>
          </div>
          <div className="note" style={{ marginTop: 8 }}>超级管理员拥有全部权限，无需配置；修改后该角色用户需重新登录生效。</div>
          <table style={{ marginTop: 10 }}>
            <thead><tr><th>菜单</th><th style={{ width: 60 }}>可访问</th></tr></thead>
            <tbody>
              {MENU_PERMS.map(m => (
                <tr key={m.perm}>
                  <td>{m.label}</td>
                  <td className="ops"><input type="checkbox" checked={rolePermModal.codes.includes(m.perm)} onChange={() => togglePerm(m.perm)} /></td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="foot">
            <button className="btn" onClick={() => setRolePermModal(null)}>取消</button>
            <button className="btn primary" onClick={saveRolePerms}>保存</button>
          </div>
        </Modal>
      )}
    </div>
  )
}
