import React, { useEffect, useRef, useState } from 'react'
import { api, uploadFile, downloadFile } from '../api'
import { useToast, useConfirm, Modal } from '../components/ui'
import Chart from '../components/Chart'

const MEDALS = ['🥇', '🥈', '🥉']

function fmt(d) {
  const y = d.getFullYear(), m = String(d.getMonth() + 1).padStart(2, '0'), dd = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${dd}`
}

export default function Dashboard() {
  const { toast, showError } = useToast()
  const [confirm, confirmEl] = useConfirm()
  const [s, setS] = useState(null)
  const [rank, setRank] = useState([])
  const [trend, setTrend] = useState([])
  const [view, setView] = useState('list')
  const [range, setRange] = useState('7')
  const [startD, setStartD] = useState('')
  const [endD, setEndD] = useState('')
  const [dailyBills, setDailyBills] = useState([])
  const [productSales, setProductSales] = useState([])
  const [products, setProducts] = useState([])
  const [customers, setCustomers] = useState([])
  const [psImportResult, setPsImportResult] = useState(null)
  const [psExportModal, setPsExportModal] = useState(false)
  const [psDate, setPsDate] = useState(() => fmt(new Date()))
  const psFileRef = useRef(null)

  function loadCharts(start = '', end = '') {
    api.get(`/api/dashboard/trend?start=${start}&end=${end}`).then(r => setTrend(r.data)).catch(() => {})
  }
  function loadSummary() {
    api.get('/api/dashboard/summary').then(r => setS(r.data)).catch(e => showError(e.message))
  }
  function loadDailyBills() {
    api.get('/api/dashboard/daily-bills').then(r => setDailyBills(r.data || [])).catch(() => {})
  }
  useEffect(() => {
    loadSummary()
    api.get('/api/dashboard/rank').then(r => setRank(r.data)).catch(() => {})
    loadCharts()
    loadDailyBills()
    loadProductSales()
    api.get('/api/products?per_page=1000').then(r => setProducts(r.data?.rows || [])).catch(() => {})
    api.get('/api/customers?per_page=1000').then(r => setCustomers(r.data?.rows?.filter(c => c.ctype === 'downstream').sort((a, b) => (parseInt(a.code, 10) || 0) - (parseInt(b.code, 10) || 0)) || [])).catch(() => {})
  }, [])

  function loadProductSales() {
    api.get('/api/product-sales?per_page=1000').then(r => {
      const rows = (r.data?.rows || []).slice().sort((a, b) => (a.sale_date < b.sale_date ? 1 : a.sale_date > b.sale_date ? -1 : (b.id - a.id)))
      setProductSales(rows)
    }).catch(() => {})
  }

  async function saveWallet(row, val) {
    const v = val === '' ? null : val
    try {
      await api.put('/api/dashboard/daily-bills/wallet', { date: row.date, wallet_balance: v })
      setDailyBills(list => list.map(r => r.date === row.date ? { ...r, wallet_balance: v === null ? null : Number(v) } : r))
      toast('已保存')
      loadSummary()
      reloadTrend()
    } catch (e) { showError(e.message) }
  }

  function updatePs(id, patch) {
    setProductSales(list => list.map(r => r.id === id ? { ...r, ...patch } : r))
  }
  function addPsRow() {
    setProductSales(list => [{ id: 'new_' + Date.now(), isNew: true, sale_date: psDate, customer_id: '', customer: '', product_id: '', product: '', qty: '', purchase_price: '', sales_price: '', note: '' }, ...list])
  }
  function onPickPsCustomer(row, text) {
    const c = customers.find(x => `${x.code} ${x.name}` === text) || customers.find(x => x.code === text) || customers.find(x => x.name === text)
    updatePs(row.id, { customer: text, customer_id: c ? c.id : '' })
  }
  function onPickPsProduct(row, text) {
    const prod = products.find(x => x.name === text)
    updatePs(row.id, { product: text, product_id: prod ? prod.id : '', sales_price: prod ? prod.default_sales_price : row.sales_price })
  }
  function psCalc(p) {
    const qty = Number(p.qty) || 0
    const sp = Number(p.sales_price) || 0
    const pp = Number(p.purchase_price) || 0
    return { sales_amount: qty * sp, profit: qty * (sp - pp) }
  }
  const filteredSales = productSales.filter(p => !psDate || p.sale_date === psDate)

  async function saveAll() {
    const rows = filteredSales
    if (rows.length === 0) { showError('当前日期下暂无数据可保存'); return }
    const invalid = []
    rows.forEach((p, i) => {
      if (!p.customer_id) invalid.push(`第 ${i + 1} 行：请选择客户`)
      if (!p.product_id) invalid.push(`第 ${i + 1} 行：请选择产品`)
      if (p.qty === '' || p.qty == null || !(Number(p.qty) > 0)) invalid.push(`第 ${i + 1} 行：请填写有效的数量`)
    })
    if (invalid.length) { showError(invalid.join('；')); return }
    if (!(await confirm(`确认批量保存当前 ${rows.length} 条产品销售数据？`))) return
    try {
      for (const p of rows) {
        const body = { sale_date: psDate, customer_id: Number(p.customer_id), product_id: Number(p.product_id), qty: Number(p.qty), purchase_price: p.purchase_price === '' ? null : Number(p.purchase_price), sales_price: p.sales_price === '' ? null : Number(p.sales_price), note: p.note || '' }
        if (p.isNew) await api.post('/api/product-sales', body)
        else await api.put(`/api/product-sales/${p.id}`, body)
      }
      toast('已保存'); loadProductSales()
    } catch (e) { showError(e.message) }
  }
  async function delPs(p) {
    if (p.isNew) { setProductSales(list => list.filter(r => r.id !== p.id)); return }
    if (!window.confirm(`确认删除该产品销售记录？`)) return
    try { await api.del(`/api/product-sales/${p.id}`); toast('已删除'); loadProductSales() } catch (e) { showError(e.message) }
  }

  async function importProductSales(file) {
    try {
      const fd = new FormData()
      fd.append('file', file)
      const data = await uploadFile('/api/product-sales/import', fd)
      loadProductSales()
      const dates = data.data?.dates || []
      if (dates.length === 1) setPsDate(dates[0])
      const errors = data.data?.errors || []
      if (errors.length > 0) {
        setPsImportResult({ imported: data.data?.imported || 0, errors })
      } else {
        toast(data.msg || '导入完成')
      }
    } catch (e) { showError(e.message) }
  }

  function exportPsTemplate() {
    downloadFile('/api/product-sales/template').catch(e => showError(e.message))
  }

  function exportPs(scope) {
    const url = scope === 'all' ? '/api/product-sales/export' : `/api/product-sales/export?date=${psDate}`
    downloadFile(url).catch(e => showError(e.message))
    setPsExportModal(false)
  }

  function pick7() { setRange('7'); loadCharts() }
  function pick30() {
    setRange('30')
    const e = new Date(), st = new Date()
    st.setDate(st.getDate() - 29)
    loadCharts(fmt(st), fmt(e))
  }
  function pickCustom() { setRange('custom') }
  function applyCustom() { loadCharts(startD, endD) }

  function reloadTrend() {
    if (range === '30') {
      const e = new Date(), st = new Date()
      st.setDate(st.getDate() - 29)
      loadCharts(fmt(st), fmt(e))
    } else if (range === 'custom') {
      loadCharts(startD, endD)
    } else {
      loadCharts()
    }
  }

  const trendOption = {
    tooltip: { trigger: 'axis' },
    legend: { data: ['日活进货量', '日活交付量', '利润', '总余额'] },
    grid: { left: 60, right: 70, top: 36, bottom: 24 },
    xAxis: { type: 'category', data: trend.map(r => r.date) },
    yAxis: [{ type: 'value', name: '条' }, { type: 'value', name: '元', splitLine: { show: false } }],
    series: [
      { name: '日活进货量', type: 'bar', data: trend.map(r => r.in_qty), itemStyle: { color: '#e2e8f0' } },
      { name: '日活交付量', type: 'bar', data: trend.map(r => r.out_qty), itemStyle: { color: '#93c5fd' } },
      { name: '利润', type: 'line', yAxisIndex: 1, data: trend.map(r => r.profit), itemStyle: { color: '#dc2626' } },
      { name: '总余额', type: 'line', yAxisIndex: 1, data: trend.map(r => r.total_balance), itemStyle: { color: '#000000' } },
    ],
  }

  const maxSales = Math.max(1, ...rank.map(r => r.sales))

  const kpis = [
    { icon: '📝', label: '在执订单量', value: s?.order_count ?? '-', bg: 'linear-gradient(135deg,#eff6ff,#dbeafe)', c: 'var(--blue)' },
    { icon: '📊', label: '日活总量', value: s?.daily_total ?? '-', bg: 'linear-gradient(135deg,#ecfdf5,#d1fae5)', c: 'var(--green)' },
    { icon: '💰', label: '总余额（元）', value: s?.total_balance != null ? s.total_balance : '-', bg: 'linear-gradient(135deg,#fefce8,#fef9c3)', c: 'var(--amber)' },
    { icon: '💹', label: '本月利润（元）', value: s?.month_profit != null ? s.month_profit : '-', bg: 'linear-gradient(135deg,#f5f3ff,#ede9fe)', c: 'var(--violet)' },
  ]

  return (
    <div className="page-scroll">
      {confirmEl}
      <div className="cards">
        {kpis.map((k, i) => (
          <div className="card kpi" key={i}>
            <div className="kpi-icon" style={{ background: k.bg, color: k.c }}>{k.icon}</div>
            <div className="kpi-body">
              <div className="t">{k.label}</div>
              <div className="v" style={{ color: k.c }}>{k.value}</div>
            </div>
          </div>
        ))}
      </div>

      <div className="row-trend">
        <div className="panel trend-panel">
          <h3 style={{ justifyContent: 'space-between' }}>
            <span>入出与利润趋势</span>
            <span>
              <button className={`btn small ${range === '7' ? 'primary' : ''}`} onClick={pick7}>7天</button>{' '}
              <button className={`btn small ${range === '30' ? 'primary' : ''}`} onClick={pick30}>30天</button>{' '}
              <button className={`btn small ${range === 'custom' ? 'primary' : ''}`} onClick={pickCustom}>自定义</button>
              {range === 'custom' && (
                <>
                  <input type="date" value={startD} onChange={e => setStartD(e.target.value)} />
                  <span>~</span>
                  <input type="date" value={endD} onChange={e => setEndD(e.target.value)} />
                  <button className="btn primary small" onClick={applyCustom}>统计</button>
                </>
              )}
            </span>
          </h3>
          <Chart option={trendOption} height={300} />
        </div>
        <div className="panel daily-bill-panel">
          <div className="notif-head">
            <span className="notif-title">📒 每日账单</span>
          </div>
          {dailyBills.length === 0 ? <div className="empty">暂无数据</div> : (
            <div style={{ maxHeight: 320, overflowY: 'auto' }}>
              <table>
                <thead><tr><th>日期</th><th className="num">利润（元）</th><th className="num">账单余额（元）</th><th className="num">钱包余额（U）</th></tr></thead>
                <tbody>
                  {dailyBills.map(r => (
                    <tr key={r.date}>
                      <td>{r.date}</td>
                      <td className="num" style={{ color: r.profit < 0 ? 'var(--red)' : 'inherit' }}>{r.profit != null ? r.profit.toLocaleString() : '—'}</td>
                      <td className="num">{r.bill_balance != null ? r.bill_balance.toLocaleString() : '—'}</td>
                      <td className="num">
                        <input
                          type="number" step="0.0001"
                          key={r.date + '_' + (r.wallet_balance ?? '')}
                          defaultValue={r.wallet_balance ?? ''}
                          placeholder="录入"
                          className="wallet-input"
                          onBlur={e => { if (e.target.value !== String(r.wallet_balance ?? '')) saveWallet(r, e.target.value) }}
                          onKeyDown={e => { if (e.key === 'Enter') e.target.blur() }}
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      <div className="panel">
        <h3 style={{ justifyContent: 'space-between' }}>
          <span>
            产品销售
            <input type="date" value={psDate} onChange={e => setPsDate(e.target.value)} style={{ marginLeft: 10, height: 30 }} />
          </span>
          <span>
            <input type="file" accept=".xlsx,.xls" style={{ display: 'none' }} ref={psFileRef} onChange={e => { if (e.target.files[0]) importProductSales(e.target.files[0]).catch(err => showError(err.message)); e.target.value = '' }} />
            <button className="btn small" onClick={() => setPsExportModal(true)}>导出 Excel</button>{' '}
            <button className="btn small" onClick={exportPsTemplate}>导出模版</button>{' '}
            <button className="btn small" onClick={() => psFileRef.current.click()}>导入 Excel</button>{' '}
            <button className="btn primary small" onClick={addPsRow}>+ 新增</button>{' '}
            <button className="btn primary small" onClick={saveAll}>保存</button>
          </span>
        </h3>
        <datalist id="ps-customers">{customers.map(c => <option key={c.id} value={`${c.code} ${c.name}`} />)}</datalist>
        <datalist id="ps-products">{products.map(p => <option key={p.id} value={p.name} />)}</datalist>
        <div style={{ maxHeight: 205, overflowY: 'auto', overflowX: 'auto' }}>
          <table className="ps-table">
            <colgroup>
              <col style={{ width: '14%' }} />
              <col style={{ width: '16%' }} />
              <col style={{ width: '7%' }} />
              <col style={{ width: '7%' }} />
              <col style={{ width: '7%' }} />
              <col style={{ width: '7%' }} />
              <col style={{ width: '6%' }} />
              <col style={{ width: '13%' }} />
              <col style={{ width: '8%' }} />
              <col style={{ width: '15%' }} />
            </colgroup>
            <thead><tr><th>客户</th><th>产品</th><th className="num">数量</th><th className="center">进货单价<br/>（元）</th><th className="center">出货单价<br/>（元）</th><th className="center">销售金额<br/>（元）</th><th className="center">利润<br/>（元）</th><th>更新时间</th><th>更新人</th><th className="ops">操作</th></tr></thead>
            <tbody>
              {filteredSales.map(p => {
                const calc = psCalc(p)
                return (
                  <tr key={p.id}>
                    <td>
                      <input list="ps-customers" value={p.customer || ''} placeholder="输入或选择客户" onChange={e => onPickPsCustomer(p, e.target.value)} />
                    </td>
                    <td>
                      <input list="ps-products" value={p.product || ''} placeholder="输入或选择产品" onChange={e => onPickPsProduct(p, e.target.value)} />
                    </td>
                    <td className="num"><input type="number" value={p.qty} onChange={e => updatePs(p.id, { qty: e.target.value })} /></td>
                    <td className="num"><input type="number" step="0.0001" value={p.purchase_price} onChange={e => updatePs(p.id, { purchase_price: e.target.value })} /></td>
                    <td className="num"><input type="number" step="0.0001" value={p.sales_price} onChange={e => updatePs(p.id, { sales_price: e.target.value })} /></td>
                    <td className="num">¥{calc.sales_amount.toFixed(2)}</td>
                    <td className="num" style={{ color: calc.profit < 0 ? 'var(--red)' : 'inherit' }}>¥{calc.profit.toFixed(2)}</td>
                    <td className="audit-time">{p.updated_at || '—'}</td>
                    <td className="audit-who">{p.updated_by || '—'}</td>
                    <td className="ops">
                      <button className="btn small danger" onClick={() => delPs(p)}>删除</button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
        {filteredSales.length === 0 && <div className="empty">该日期暂无产品销售</div>}
      </div>

      <div className="panel">
        <h3 style={{ justifyContent: 'space-between' }}>
          日活分析
          <span>
            <button className={`btn small ${view === 'list' ? 'primary' : ''}`} onClick={() => setView('list')}>列表</button>{' '}
            <button className={`btn small ${view === 'bar' ? 'primary' : ''}`} onClick={() => setView('bar')}>柱状图</button>
          </span>
        </h3>
        {rank.length === 0 ? <div className="empty">暂无数据</div> : view === 'list' ? (
          <table>
            <thead><tr><th>排名</th><th>客户</th><th className="num">业务量</th><th className="num">销售额（元）</th><th className="num">利润（元）</th><th className="num">余额（元）</th></tr></thead>
            <tbody>
              {rank.map((r, i) => (
                <tr key={i}>
                  <td>{MEDALS[i] || i + 1}</td>
                  <td>{r.code} {r.name}</td>
                  <td className="num">{r.qty}</td>
                  <td className="num">¥{r.sales.toLocaleString()}</td>
                  <td className="num" style={{ color: r.profit < 0 ? 'var(--red)' : 'inherit' }}>¥{r.profit.toLocaleString()}</td>
                  <td className="num" style={{ color: r.balance < 0 ? 'var(--red)' : 'var(--green)' }}>¥{r.balance.toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="bars">
            {rank.map((r, i) => (
              <div className="bar" key={i} title={`${r.code} ${r.name}: ¥${r.sales}`}>
                <span>¥{r.sales}</span>
                <div className="col" style={{ height: `${(r.sales / maxSales) * 100}%` }}></div>
                <span className="blabel">{MEDALS[i] || i + 1} {r.name}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {psImportResult && (
        <Modal title="导入结果" onClose={() => setPsImportResult(null)} wide>
          <div style={{ marginBottom: 12, fontSize: 14 }}>
            成功导入 <b style={{ color: 'var(--green)' }}>{psImportResult.imported}</b> 条，
            失败 <b style={{ color: 'var(--red)' }}>{psImportResult.errors.length}</b> 条，请修改后重新导入：
          </div>
          <div style={{ maxHeight: 340, overflowY: 'auto', border: '1px solid var(--line)', borderRadius: 6, padding: '10px 14px', background: '#fafbfd' }}>
            {psImportResult.errors.map((e, i) => (
              <div key={i} style={{ padding: '3px 0', fontSize: 13, color: 'var(--red)', wordBreak: 'break-all' }}>
                {i + 1}. {e}
              </div>
            ))}
          </div>
          <div className="foot">
            <button className="btn primary" onClick={() => setPsImportResult(null)}>关闭</button>
          </div>
        </Modal>
      )}

      {psExportModal && (
        <Modal title="导出产品销售" onClose={() => setPsExportModal(false)}>
          <div style={{ marginBottom: 16, fontSize: 14 }}>请选择导出范围：</div>
          <div className="foot">
            <button className="btn" onClick={() => exportPs('current')}>导出当前日期数据</button>
            <button className="btn primary" onClick={() => exportPs('all')}>导出全部数据</button>
          </div>
        </Modal>
      )}
    </div>
  )
}
