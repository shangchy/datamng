import React, { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api } from '../api'
import { Modal, Badge, useToast, useConfirm } from '../components/ui'
import FilterBar, { buildQuery } from '../components/FilterBar'
import Pagination from '../components/Pagination'

const emptyForm = { code: '', name: '', ctype: 'downstream', tg_id: '', wash_mode: '只分', is_accounted: true, discount: 1, warn_amount: 0, start_date: '', end_date: '', note: '', status: 1 }

const CUST_COLS = [
  { k: 'code', l: '客户编号' }, { k: 'name', l: '客户名称' }, { k: 'ctype', l: '类型' },
  { k: 'tg_id', l: '飞机账号ID' }, { k: 'wash_mode', l: '加工方式' }, { k: 'status', l: '状态' },
  { k: 'note', l: '备注' },
]

export default function Customers() {
  const toast = useToast()
  const [confirm, confirmEl] = useConfirm()
  const [searchParams] = useSearchParams()
  const [rows, setRows] = useState([])
  const [detail, setDetail] = useState(null)
  const [tab, setTab] = useState('orders')
  const [recharge, setRecharge] = useState(null)
  const [modal, setModal] = useState(null)
  const [form, setForm] = useState(emptyForm)
  const [formTab, setFormTab] = useState('prices')
  const [filters, setFilters] = useState({})
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [perPage, setPerPage] = useState(10)
  const [sort, setSort] = useState({ k: 'code', dir: 'asc' })

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
    const r = await api.get('/api/customers?' + params)
    setRows(r.data.rows); setTotal(r.data.total)
  }
  function search(f) { setPage(1); load(1, perPage, f) }
  function goPage(p) { setPage(p); load(p, perPage) }
  function changePerPage(pp) { setPerPage(pp); setPage(1); load(1, pp) }
  useEffect(() => {
    load()
    const cid = searchParams.get('detail')
    if (cid) openDetail({ id: cid })
    const rid = searchParams.get('recharge')
    if (rid) setRecharge({ customer_id: Number(rid), amount_u: '', recharge_date: new Date().toISOString().slice(0, 10), note: '', from_detail: false })
  }, [searchParams])

  async function openDetail(c) {
    const r = await api.get(`/api/customers/${c.id}`)
    setDetail(r.data); setTab('orders')
  }

  async function saveRecharge() {
    if (!recharge.amount_u || !recharge.recharge_date) { toast('请填写充值金额和日期'); return }
    try {
      await api.post(`/api/customers/${recharge.customer_id}/recharges`, { amount_u: Number(recharge.amount_u), recharge_date: recharge.recharge_date, note: recharge.note || '' })
      const cid = recharge.customer_id, fromDetail = recharge.from_detail
      toast('充值成功'); setRecharge(null)
      if (fromDetail) openDetail({ id: cid }); else load()
    } catch (e) { toast(e.message) }
  }

  async function save() {
    if (!(await confirm('确认保存客户信息？'))) return
    try {
      const body = { ...form, warn_amount: Number(form.warn_amount) || 0, discount: Number(form.discount) || 1, is_accounted: !!form.is_accounted }
      if (modal === 'create') await api.post('/api/customers', body)
      else await api.put(`/api/customers/${form.id}`, body)
      toast('已保存'); setModal(null); load()
    } catch (e) { toast(e.message) }
  }

  function openEdit(c) {
    setForm({ ...emptyForm, ...c, tg_id: c.tg_id || '', note: c.note || '', start_date: c.start_date || '', end_date: c.end_date || '', discount: c.discount ?? 1, is_accounted: c.is_accounted ?? true })
    setFormTab('orders')
    setModal('edit')
  }

  return (
    <div className="page">
      {confirmEl}
      <div className="toolbar">
        <FilterBar cols={CUST_COLS} filters={filters} setFilters={setFilters} onSearch={search} />
        <span className="spacer" />
        <button className="btn primary" onClick={() => { setForm(emptyForm); setFormTab('prices'); setModal('create') }}>+ 新增客户</button>
      </div>
      <div className="panel">
        <div className="table-scroll">
        <table>
          <thead><tr>
            <th onClick={() => toggleSort('code')}>客户编号{sort?.k === 'code' ? <span className="arr">{sort.dir === 'asc' ? '▲' : '▼'}</span> : ''}</th>
            <th onClick={() => toggleSort('name')}>客户名称{sort?.k === 'name' ? <span className="arr">{sort.dir === 'asc' ? '▲' : '▼'}</span> : ''}</th>
            <th onClick={() => toggleSort('ctype')}>类型{sort?.k === 'ctype' ? <span className="arr">{sort.dir === 'asc' ? '▲' : '▼'}</span> : ''}</th>
            <th onClick={() => toggleSort('tg_id')}>飞机账号ID{sort?.k === 'tg_id' ? <span className="arr">{sort.dir === 'asc' ? '▲' : '▼'}</span> : ''}</th>
            <th onClick={() => toggleSort('wash_mode')}>加工方式{sort?.k === 'wash_mode' ? <span className="arr">{sort.dir === 'asc' ? '▲' : '▼'}</span> : ''}</th>
            <th className="num" onClick={() => toggleSort('balance')}>余额{sort?.k === 'balance' ? <span className="arr">{sort.dir === 'asc' ? '▲' : '▼'}</span> : ''}</th>
            <th className="num" onClick={() => toggleSort('warn_amount')}>预警额度{sort?.k === 'warn_amount' ? <span className="arr">{sort.dir === 'asc' ? '▲' : '▼'}</span> : ''}</th>
            <th onClick={() => toggleSort('note')}>备注{sort?.k === 'note' ? <span className="arr">{sort.dir === 'asc' ? '▲' : '▼'}</span> : ''}</th>
            <th onClick={() => toggleSort('status')}>状态{sort?.k === 'status' ? <span className="arr">{sort.dir === 'asc' ? '▲' : '▼'}</span> : ''}</th>
            <th className="ops">操作</th>
          </tr></thead>
          <tbody>
            {sortedRows().map(c => (
              <tr key={c.id} className={c.has_alert ? 'row-alert' : 'clickable'} onDoubleClick={() => openDetail(c)}>
                <td>{c.code}</td><td>{c.name}</td><td><Badge value={c.ctype === 'upstream' ? '上游' : '下游'} /></td>
                <td>{c.tg_id || '—'}</td><td>{c.wash_mode}</td><td className="num">¥{c.balance}</td><td className="num">¥{c.warn_amount}</td>
                <td style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>{c.note || '—'}</td><td><Badge value={c.status === 1 ? '启用' : '停用'} /></td>
                <td className="ops">
                  <button className="btn small" onClick={() => openDetail(c)}>详情</button>{' '}
                  <button className="btn small primary" onClick={() => { setRecharge({ customer_id: c.id, amount_u: '', recharge_date: '', note: '', from_detail: false }) }}>充值</button>{' '}
                  <button className="btn small" onClick={() => openEdit(c)}>编辑</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        </div>
        {rows.length === 0 && <div className="empty">暂无数据</div>}
        <Pagination total={total} page={page} perPage={perPage} setPage={setPage} setPerPage={changePerPage} goPage={goPage} />
      </div>

      {detail && !recharge && (
        <Modal title={`客户详情 · ${detail.name}`} onClose={() => setDetail(null)} wide>
          <div className="sticky-head">
            <div className="cards" style={{ gridTemplateColumns: 'repeat(4,1fr)' }}>
              <div className="card"><div className="t">总供货量</div><div className="v">{detail.total_supply}</div></div>
              <div className="card"><div className="t">总销售额</div><div className="v">¥{detail.total_sales}</div></div>
              <div className="card"><div className="t">总利润</div><div className="v" style={{ color: 'var(--green)' }}>¥{detail.total_profit}</div></div>
              <div className="card"><div className="t">余额</div><div className="v">¥{detail.balance}</div></div>
            </div>
            <table className="kv"><tbody>
              <tr><td>客户编号</td><td>{detail.code}</td><td>客户名称</td><td>{detail.name}</td></tr>
              <tr><td>类型</td><td>{detail.ctype}</td><td>飞机账号ID</td><td>{detail.tg_id || '—'}</td></tr>
              <tr><td>加工方式</td><td>{detail.wash_mode}</td><td>预警额度</td><td>¥{detail.warn_amount}</td></tr>
              <tr><td>开始日期</td><td>{detail.start_date || '—'}</td><td>结束日期</td><td>{detail.end_date || '—'}</td></tr>
              <tr><td>状态</td><td>{detail.status === 1 ? '启用' : '停用'}</td><td>备注</td><td style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>{detail.note || '—'}</td></tr>
            </tbody></table>
          </div>
          <div className="toolbar" style={{ marginTop: 14, marginBottom: 8 }}>
            {['orders', 'recharges', 'prices'].map(t => (
              <button key={t} className={`btn small ${tab === t ? 'primary' : ''}`} onClick={() => setTab(t)}>
                {t === 'orders' ? '订单记录' : t === 'recharges' ? '充值记录' : '设定单价'}
              </button>
            ))}
          </div>
          <TabContent tab={tab} customerId={detail.id} />
          <div className="foot">
            <button className="btn primary" onClick={() => { setRecharge({ customer_id: detail.id, amount_u: '', recharge_date: '', note: '', from_detail: true }) }}>+ 充值</button>
            <button className="btn" onClick={() => setDetail(null)}>关闭</button>
          </div>
        </Modal>
      )}

      {recharge && (
        <Modal title="账户充值" onClose={() => setRecharge(null)}>
          <div className="row">
            <div className="field"><label>充值金额 (U)</label><input type="number" value={recharge.amount_u} onChange={e => setRecharge({ ...recharge, amount_u: e.target.value })} /></div>
            <div className="field"><label>折算 RMB</label><input value={recharge.amount_u ? (recharge.amount_u * 6.7).toFixed(2) : ''} readOnly /></div>
          </div>
          <div className="row">
            <div className="field"><label>充值日期</label><input type="date" value={recharge.recharge_date} onChange={e => setRecharge({ ...recharge, recharge_date: e.target.value })} /></div>
            <div className="field"><label>备注</label><input value={recharge.note} onChange={e => setRecharge({ ...recharge, note: e.target.value })} /></div>
          </div>
          <div className="foot">
            <button className="btn" onClick={() => setRecharge(null)}>取消</button>
            <button className="btn primary" onClick={saveRecharge}>确认充值</button>
          </div>
        </Modal>
      )}

      {modal && (
        <Modal title={modal === 'create' ? '新增客户' : '编辑客户'} onClose={() => setModal(null)}>
          <div className="sticky-head">
            <div className="row">
              <div className="field"><label>客户编号</label><input value={form.code} onChange={e => setForm({ ...form, code: e.target.value })} /></div>
              <div className="field"><label>客户名称</label><input value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} /></div>
            </div>
            <div className="row">
              <div className="field"><label>类型</label><select value={form.ctype} onChange={e => setForm({ ...form, ctype: e.target.value })}><option value="downstream">下游</option><option value="upstream">上游</option></select></div>
              <div className="field"><label>飞机账号ID</label><input value={form.tg_id} onChange={e => setForm({ ...form, tg_id: e.target.value })} /></div>
            </div>
            <div className="row">
              <div className="field"><label>预警额度</label><input type="number" value={form.warn_amount} onChange={e => setForm({ ...form, warn_amount: e.target.value })} /></div>
              <div className="field"><label>加工方式</label><select value={form.wash_mode} onChange={e => setForm({ ...form, wash_mode: e.target.value })}><option>洗名</option><option>只分</option><option>合并</option><option>跳过</option></select></div>
            </div>
            <div className="row">
              <div className="field"><label>是否记账</label><select value={form.is_accounted ? 1 : 0} onChange={e => setForm({ ...form, is_accounted: e.target.value === '1' })}><option value={1}>是</option><option value={0}>否</option></select></div>
              <div className="field"><label>结算折扣</label><input type="number" step="0.1" value={form.discount} onChange={e => setForm({ ...form, discount: e.target.value })} /></div>
            </div>
            <div className="row">
              <div className="field"><label>开始日期</label><input type="date" value={form.start_date} onChange={e => setForm({ ...form, start_date: e.target.value })} /></div>
              <div className="field"><label>结束日期</label><input type="date" value={form.end_date} onChange={e => setForm({ ...form, end_date: e.target.value })} /></div>
            </div>
            <div className="row">
              <div className="field"><label>状态</label><select value={form.status} onChange={e => setForm({ ...form, status: Number(e.target.value) })}><option value={1}>启用</option><option value={0}>停用</option></select></div>
              <div className="field" />
            </div>
            <div className="row">
              <div className="field"><label>备注</label><textarea rows={3} value={form.note} onChange={e => setForm({ ...form, note: e.target.value })} /></div>
            </div>
          </div>
          <div className="toolbar" style={{ marginTop: 14, marginBottom: 8 }}>
            {(modal === 'create' ? ['prices'] : ['orders', 'recharges', 'prices']).map(t => (
              <button key={t} className={`btn small ${formTab === t ? 'primary' : ''}`} onClick={() => setFormTab(t)}>
                {t === 'orders' ? '订单记录' : t === 'recharges' ? '充值记录' : '设定单价'}
              </button>
            ))}
          </div>
          {formTab === 'prices' && !form.id ? (
            <div className="note">保存客户后即可设定渠道单价。</div>
          ) : (
            <TabContent tab={formTab} customerId={form.id} />
          )}
          <div className="foot">
            <button className="btn" onClick={() => setModal(null)}>取消</button>
            <button className="btn primary" onClick={save}>保存</button>
          </div>
        </Modal>
      )}
    </div>
  )
}

function TabContent({ tab, customerId }) {
  const [data, setData] = useState([])
  const [prices, setPrices] = useState([])
  const toast = useToast()
  const [confirm, confirmEl] = useConfirm()
  useEffect(() => {
    if (tab === 'orders') api.get(`/api/customers/${customerId}/orders`).then(r => setData(r.data)).catch(() => {})
    if (tab === 'recharges') api.get(`/api/customers/${customerId}/recharges`).then(r => setData(r.data)).catch(() => {})
    if (tab === 'prices') api.get(`/api/customers/${customerId}/prices`).then(r => { setData(r.data); setPrices(r.data.map(x => ({ channel_id: x.channel_id, price: x.price ?? '' }))) }).catch(() => {})
  }, [tab, customerId])

  async function savePrices() {
    if (!(await confirm('确认保存客户渠道单价？'))) return
    const body = { prices: prices.filter(p => p.price !== '').map(p => ({ channel_id: p.channel_id, price: Number(p.price) })) }
    await api.put(`/api/customers/${customerId}/prices`, body)
    toast('单价已保存')
  }

  if (tab === 'orders') return (
    <table><thead><tr><th>订单号</th><th>状态</th><th>开始日期</th><th>截止日期</th><th>上游</th><th>渠道</th><th>任务名</th><th>URL</th><th className="num">数量</th></tr></thead>
      <tbody>{data.map((o, i) => <tr key={i}><td>{o.order_no}</td><td><Badge value={o.status} /></td><td>{o.start_date}</td><td>{o.end_date || '—'}</td><td>{o.upstream}</td><td>{o.channel}</td><td>{o.task_name}</td><td>{o.url}</td><td className="num">{o.qty}</td></tr>)}</tbody></table>
  )
  if (tab === 'recharges') return (
    <table><thead><tr><th>日期</th><th className="num">充值(U)</th><th className="num">折算RMB</th><th>备注</th></tr></thead>
      <tbody>{data.map((r, i) => <tr key={i}><td>{r.recharge_date}</td><td className="num">{r.amount_u}</td><td className="num">¥{r.amount_rmb}</td><td>{r.note || '—'}</td></tr>)}</tbody></table>
  )
  return (
    <div>
      {confirmEl}
      <div className="note">数据来源于渠道，为当前客户维护每个渠道单价。</div>
      <table><thead><tr><th>渠道</th><th>单价(元/条)</th></tr></thead>
        <tbody>{data.map((c, i) => (
          <tr key={i}>
            <td>{c.channel}</td>
            <td><input type="number" step="0.01" value={prices[i]?.price ?? ''} onChange={e => { const arr = [...prices]; arr[i] = { ...arr[i], price: e.target.value }; setPrices(arr) }} /></td>
          </tr>
        ))}</tbody></table>
      <div className="foot"><button className="btn primary" onClick={savePrices}>保存单价</button></div>
    </div>
  )
}
