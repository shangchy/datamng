import React, { useEffect, useState } from 'react'
import { api } from '../api'
import { Badge, Modal, useToast } from '../components/ui'
import Pagination from '../components/Pagination'

const ACTION_LABEL = {
  login: '登录成功', login_failed: '登录失败', 'change-password': '修改密码',
  create_order: '创建提单', import_orders: '导入提单', update_order: '修改订单', generate_tidabiao: '生成提单表',
  confirm_tidabiao: '提单确认',
  batch_delete_orders: '批量删除订单',
}

const ACTION_OPTIONS = [
  { value: 'create_order', label: '创建提单' },
  { value: 'import_orders', label: '导入提单' },
  { value: 'update_order', label: '修改订单' },
  { value: 'generate_tidabiao', label: '生成提单表' },
  { value: 'change-password', label: '修改密码' },
]

function parseDetail(detail) {
  if (!detail) return null
  try {
    const obj = JSON.parse(detail)
    if (obj && typeof obj === 'object' && ('before' in obj || 'after' in obj)) return obj
  } catch { /* ignore */ }
  return null
}

function JsonBlock({ value }) {
  if (value === null || value === undefined) return <div className="readonly" style={{ height: 'auto', whiteSpace: 'pre-wrap', color: 'var(--sub)' }}>（无）</div>
  let text
  if (typeof value === 'object') {
    text = JSON.stringify(value, null, 2)
  } else {
    text = String(value)
  }
  return <div className="readonly" style={{ height: 'auto', whiteSpace: 'pre-wrap', textAlign: 'left', fontFamily: 'monospace', fontSize: 12 }}>{text}</div>
}

export default function Logs() {
  const toast = useToast()
  const [tab, setTab] = useState('login')
  const [rows, setRows] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [perPage, setPerPage] = useState(20)
  const [filters, setFilters] = useState({ username: '', action: '', start_date: '', end_date: '' })
  const [viewLog, setViewLog] = useState(null)

  async function load(p = page, pp = perPage, f = filters) {
    const params = new URLSearchParams()
    params.set('type', tab)
    Object.keys(f).forEach(k => { if (f[k]) params.set(k, f[k]) })
    params.set('page', p); params.set('per_page', pp)
    try {
      const r = await api.get('/api/logs?' + params.toString())
      setRows(r.data.rows); setTotal(r.data.total)
    } catch (e) { toast(e.message) }
  }

  useEffect(() => { setPage(1); setRows([]); load(1, perPage, filters) }, [tab])
  function search() { setPage(1); load(1, perPage, filters) }
  function reset() { setFilters({ username: '', action: '', start_date: '', end_date: '' }); setPage(1); load(1, perPage, {}) }
  function goPage(p) { setPage(p); load(p, perPage) }
  function changePerPage(pp) { setPerPage(pp); setPage(1); load(1, pp) }

  function detailCell(r) {
    const obj = parseDetail(r.detail)
    if (!obj) return <td>{r.detail || '—'}</td>
    return <td><a className="link" onClick={() => setViewLog(r)}>查看前后对比</a></td>
  }

  return (
    <div className="page">
      <div className="toolbar">
        <button className={`btn small ${tab === 'login' ? 'primary' : ''}`} onClick={() => setTab('login')}>登录日志</button>
        <button className={`btn small ${tab === 'operation' ? 'primary' : ''}`} onClick={() => setTab('operation')}>操作日志</button>
        <span className="spacer" />
        <input placeholder="用户名" style={{ width: 120 }} value={filters.username} onChange={e => setFilters({ ...filters, username: e.target.value })} />
        {tab === 'operation' && (
          <select value={filters.action} onChange={e => setFilters({ ...filters, action: e.target.value })}>
            <option value="">全部动作</option>
            {ACTION_OPTIONS.map(a => <option key={a.value} value={a.value}>{a.label}</option>)}
          </select>
        )}
        <input type="date" value={filters.start_date} onChange={e => setFilters({ ...filters, start_date: e.target.value })} />
        <input type="date" value={filters.end_date} onChange={e => setFilters({ ...filters, end_date: e.target.value })} />
        <button className="btn primary" onClick={search}>查询</button>
        <button className="btn" onClick={reset}>重置</button>
      </div>
      <div className="panel">
        <div className="table-scroll">
          <table>
            <thead>
              {tab === 'login' ? (
                <tr><th>时间</th><th>用户</th><th>动作</th><th>结果</th><th>IP</th></tr>
              ) : (
                <tr><th>时间</th><th>操作人</th><th>模块</th><th>动作</th><th>处理数据对象</th><th>操作前后数据</th><th>IP</th></tr>
              )}
            </thead>
            <tbody>
              {tab === 'login' ? rows.map(r => (
                <tr key={r.id}>
                  <td>{r.created_at}</td><td>{r.username}</td>
                  <td><Badge value={r.action === 'login' ? '登录' : '登录失败'} /></td>
                  <td>{r.action === 'login' ? '成功' : r.detail || '失败'}</td>
                  <td>{r.ip || '—'}</td>
                </tr>
              )) : rows.map(r => (
                <tr key={r.id}>
                  <td>{r.created_at}</td><td>{r.username}</td><td>{r.module}</td>
                  <td>{ACTION_LABEL[r.action] || r.action}</td><td>{r.target || '—'}</td>
                  {detailCell(r)}<td>{r.ip || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {rows.length === 0 && <div className="empty">暂无日志</div>}
        <Pagination total={total} page={page} perPage={perPage} setPage={setPage} setPerPage={changePerPage} goPage={goPage} />
      </div>

      {viewLog && (
        <Modal title={`操作前后数据对比 · ${ACTION_LABEL[viewLog.action] || viewLog.action}`} onClose={() => setViewLog(null)} wide>
          <div className="row" style={{ marginBottom: 8 }}>
            <div className="field"><label>操作时间</label><div className="readonly">{viewLog.created_at}</div></div>
            <div className="field"><label>操作人</label><div className="readonly">{viewLog.username || '—'}</div></div>
            <div className="field"><label>处理数据对象</label><div className="readonly">{viewLog.target || '—'}</div></div>
          </div>
          <div className="row">
            <div className="field" style={{ flex: 1 }}><label>操作前</label><JsonBlock value={parseDetail(viewLog.detail)?.before} /></div>
            <div className="field" style={{ flex: 1 }}><label>操作后</label><JsonBlock value={parseDetail(viewLog.detail)?.after} /></div>
          </div>
          <div className="foot"><button className="btn primary" onClick={() => setViewLog(null)}>关闭</button></div>
        </Modal>
      )}
    </div>
  )
}
