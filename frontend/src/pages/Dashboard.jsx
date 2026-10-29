import React, { useEffect, useState } from 'react'
import { api } from '../api'
import { useToast } from '../components/ui'
import Chart from '../components/Chart'

const MEDALS = ['🥇', '🥈', '🥉']

function fmt(d) {
  const y = d.getFullYear(), m = String(d.getMonth() + 1).padStart(2, '0'), dd = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${dd}`
}

export default function Dashboard() {
  const { toast, showError } = useToast()
  const [s, setS] = useState(null)
  const [rank, setRank] = useState([])
  const [trend, setTrend] = useState([])
  const [view, setView] = useState('list')
  const [range, setRange] = useState('7')
  const [startD, setStartD] = useState('')
  const [endD, setEndD] = useState('')
  const [dailyBills, setDailyBills] = useState([])

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
  }, [])

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
    </div>
  )
}
