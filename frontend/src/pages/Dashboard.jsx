import React, { useEffect, useState } from 'react'
import { api } from '../api'
import { useToast } from '../components/ui'
import Chart from '../components/Chart'

const MEDALS = ['🥇', '🥈', '🥉']

function fmt(d) {
  const y = d.getFullYear(), m = String(d.getMonth() + 1).padStart(2, '0'), dd = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${dd}`
}

function pieOption(data) {
  return {
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { orient: 'vertical', right: 6, top: 'center' },
    series: [{
      type: 'pie', radius: ['38%', '66%'], center: ['38%', '50%'],
      data: data.map(r => ({ name: r.name, value: r.value })),
      label: { formatter: '{b}\n{d}%' },
      itemStyle: { borderColor: '#fff', borderWidth: 2 },
    }],
  }
}

export default function Dashboard() {
  const { toast, showError } = useToast()
  const [s, setS] = useState(null)
  const [rank, setRank] = useState([])
  const [trend, setTrend] = useState([])
  const [pie1, setPie1] = useState([])
  const [pie2, setPie2] = useState([])
  const [pieChan, setPieChan] = useState([])
  const [view, setView] = useState('list')
  const [range, setRange] = useState('7')
  const [startD, setStartD] = useState('')
  const [endD, setEndD] = useState('')

  function loadCharts(start = '', end = '') {
    api.get(`/api/dashboard/trend?start=${start}&end=${end}`).then(r => setTrend(r.data)).catch(() => {})
    api.get(`/api/dashboard/category-pie?start=${start}&end=${end}`).then(r => setPie1(r.data)).catch(() => {})
    api.get(`/api/dashboard/category2-pie?start=${start}&end=${end}`).then(r => setPie2(r.data)).catch(() => {})
    api.get(`/api/dashboard/channel-pie?start=${start}&end=${end}`).then(r => setPieChan(r.data)).catch(() => {})
  }
  useEffect(() => {
    api.get('/api/dashboard/summary').then(r => setS(r.data)).catch(e => showError(e.message))
    api.get('/api/dashboard/rank').then(r => setRank(r.data)).catch(() => {})
    loadCharts()
  }, [])

  function pick7() { setRange('7'); loadCharts() }
  function pick30() {
    setRange('30')
    const e = new Date(), st = new Date()
    st.setDate(st.getDate() - 29)
    loadCharts(fmt(st), fmt(e))
  }
  function pickCustom() { setRange('custom') }
  function applyCustom() { loadCharts(startD, endD) }

  const trendOption = {
    tooltip: { trigger: 'axis' },
    legend: { data: ['交付量', '上游来量', '营业额', '利润'] },
    grid: { left: 60, right: 70, top: 36, bottom: 24 },
    xAxis: { type: 'category', data: trend.map(r => r.date) },
    yAxis: [{ type: 'value', name: '条' }, { type: 'value', name: '元', splitLine: { show: false } }],
    series: [
      { name: '交付量', type: 'bar', data: trend.map(r => r.out_qty), itemStyle: { color: '#93c5fd' } },
      { name: '上游来量', type: 'bar', data: trend.map(r => r.in_qty), itemStyle: { color: '#e2e8f0' } },
      { name: '营业额', type: 'line', yAxisIndex: 1, data: trend.map(r => r.sales), itemStyle: { color: '#059669' } },
      { name: '利润', type: 'line', yAxisIndex: 1, data: trend.map(r => r.profit), itemStyle: { color: '#dc2626' } },
    ],
  }

  const maxSales = Math.max(1, ...rank.map(r => r.sales))

  const kpis = [
    { icon: '📝', label: '在执订单量', value: s?.order_count ?? '-', bg: 'linear-gradient(135deg,#eff6ff,#dbeafe)', c: 'var(--blue)' },
    { icon: '📊', label: '日活总量', value: s?.daily_total ?? '-', bg: 'linear-gradient(135deg,#ecfdf5,#d1fae5)', c: 'var(--green)' },
    { icon: '🏦', label: '公积金总量', value: s?.fund_total ?? '-', bg: 'linear-gradient(135deg,#f5f3ff,#ede9fe)', c: 'var(--violet)' },
    { icon: '📦', label: '交付总量', value: s?.delivery_total ?? '-', bg: 'linear-gradient(135deg,#eff6ff,#dbeafe)', c: 'var(--blue)' },
    { icon: '💰', label: '利润', value: s?.profit_total !== undefined ? `¥${s.profit_total.toLocaleString()}` : '-', bg: 'linear-gradient(135deg,#fef2f2,#fee2e2)', c: 'var(--red)' },
    { icon: '🔔', label: '待处理预警', value: s?.alert_count ?? '-', bg: 'linear-gradient(135deg,#fffbeb,#fef3c7)', c: 'var(--amber)' },
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

      <div className="panel">
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

      <div className="row3">
        <div className="panel"><h3>一级品类占比</h3><Chart option={pieOption(pie1)} height={240} /></div>
        <div className="panel"><h3>二级品类占比</h3><Chart option={pieOption(pie2)} height={240} /></div>
        <div className="panel"><h3>渠道占比</h3><Chart option={pieOption(pieChan)} height={240} /></div>
      </div>

      <div className="panel">
        <h3 style={{ justifyContent: 'space-between' }}>
          下游客户排名
          <span>
            <button className={`btn small ${view === 'list' ? 'primary' : ''}`} onClick={() => setView('list')}>列表</button>{' '}
            <button className={`btn small ${view === 'bar' ? 'primary' : ''}`} onClick={() => setView('bar')}>柱状图</button>
          </span>
        </h3>
        {rank.length === 0 ? <div className="empty">暂无数据</div> : view === 'list' ? (
          <table>
            <thead><tr><th>排名</th><th>客户编号</th><th>客户名称</th><th className="num">业务量</th><th className="num">销售额</th><th className="num">余额</th></tr></thead>
            <tbody>
              {rank.map((r, i) => (
                <tr key={i}>
                  <td>{MEDALS[i] || i + 1}</td>
                  <td>{r.code}</td><td>{r.name}</td>
                  <td className="num">{r.qty}</td>
                  <td className="num">¥{r.sales.toLocaleString()}</td>
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
