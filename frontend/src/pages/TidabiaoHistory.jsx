import React, { useEffect, useState } from 'react'
import { api } from '../api'
import { Badge, useToast } from '../components/ui'
import { useColumnConfig, downloadCsv } from '../components/columns'
import FilterBar, { buildQuery } from '../components/FilterBar'
import Pagination from '../components/Pagination'

const COLS = [
  { k: 'batch_no', l: '提单批次' }, { k: 'status', l: '状态' }, { k: 'order_date', l: '更新日期' },
  { k: 'upstream', l: '甲方' }, { k: 'order_no', l: '订单号' }, { k: 'task_id', l: '工单号' },
  { k: 'customer', l: '一级代理' }, { k: 'secondary_agent', l: '二级代理' }, { k: 'price', l: '定价' },
  { k: 'platform', l: '平台' }, { k: 'group_name', l: '小组' }, { k: 'tpl_code', l: '出数模版' },
  { k: 'add_name', l: '是否加名' }, { k: 'channel', l: '渠道' }, { k: 'operator', l: '运营商' },
  { k: 'task_name', l: '任务名' }, { k: 'url', l: 'url' }, { k: 'qty', l: '数量' },
  { k: 'duration', l: '时长' }, { k: 'age_min', l: '年龄下限' }, { k: 'age_max', l: '年龄上限' }, { k: 'pv', l: 'pv' },
  { k: 'province', l: '省份' }, { k: 'excl_province', l: '排除省份' }, { k: 'city', l: '地市' },
  { k: 'excl_city', l: '排除地市' }, { k: 'start_date', l: '开始日期' }, { k: 'end_date', l: '截止日期' },
  { k: 'created_at', l: '生成时间' },
]

const FILTER_COLS = [
  { k: 'batch_no', l: '提单批次' }, { k: 'status', l: '状态' }, { k: 'order_date', l: '更新日期' },
  { k: 'upstream', l: '甲方' }, { k: 'order_no', l: '订单号' }, { k: 'task_id', l: '工单号' },
  { k: 'customer', l: '一级代理' }, { k: 'channel', l: '渠道' }, { k: 'task_name', l: '任务名' },
]

export default function TidabiaoHistory() {
  const { toast, showError } = useToast()
  const { visible: cols, picker, openPicker } = useColumnConfig(COLS, 'cols_tidabiao_history')
  const [rows, setRows] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [perPage, setPerPage] = useState(100)
  const [filters, setFilters] = useState({})
  const [sort, setSort] = useState(null)

  async function load(p = page, pp = perPage, f) {
    const qs = buildQuery(f === undefined ? filters : f)
    const params = qs ? qs + `&page=${p}&per_page=${pp}` : `page=${p}&per_page=${pp}`
    const r = await api.get('/api/orders/tidabiao-history?' + params)
    setRows(r.data.rows); setTotal(r.data.total)
  }
  function search(f) { setPage(1); load(1, perPage, f) }
  function goPage(p) { setPage(p); load(p, perPage) }
  function changePerPage(pp) { setPerPage(pp); setPage(1); load(1, pp) }
  useEffect(() => { load() }, [])

  function sorted() {
    const list = [...rows]
    if (sort) list.sort((a, b) => (a[sort.k] > b[sort.k] ? 1 : -1) * (sort.dir === 'asc' ? 1 : -1))
    return list
  }

  function cell(o, c) {
    const num = ['qty', 'pv', 'age_min', 'age_max'].includes(c.k)
    if (c.k === 'status') return <td><Badge value={o.status} /></td>
    if (c.k === 'url') return <td style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: 220 }} title={o.url || ''}>{o.url || '—'}</td>
    if (c.k === 'add_name') return <td><Badge value={o.add_name === '是' ? '是' : '否'} /></td>
    if (['province', 'city', 'excl_province', 'excl_city'].includes(c.k)) {
      const val = o[c.k] || ''
      const parts = val.split(/[|｜,，;；]/).map(s => s.trim()).filter(Boolean)
      if (parts.length > 3) return <td title={val}>{parts[0]} 等{parts.length}个</td>
      return <td title={val}>{parts.join(',') || '—'}</td>
    }
    if (c.k === 'price') return <td className="num">{o.price != null && o.price !== '' ? o.price : '—'}</td>
    return <td className={num ? 'num' : ''}>{o[c.k] || '—'}</td>
  }

  function exportCsv() {
    const qs = buildQuery(filters)
    api.get('/api/orders/tidabiao-history?' + qs + '&page=1&per_page=500').then(r => {
      downloadCsv('提单历史.csv', cols, r.data.rows)
      toast('已导出')
    }).catch(e => showError(e.message))
  }

  return (
    <div className="page">
      {picker}
      <div className="toolbar">
        <FilterBar cols={FILTER_COLS} filters={filters} setFilters={setFilters} onSearch={search} fieldOptions={{ status: ['未提', '在执', '待停', '已停', '改单'] }} />
        <span className="spacer" />
        <button className="btn green" onClick={exportCsv}>导出 CSV</button>
        <button className="btn" onClick={openPicker}>自定义表头</button>
      </div>
      <div className="panel">
        <div className="table-scroll">
          <table>
            <thead><tr>
              {cols.map(c => (
                <th key={c.k} className={['qty', 'pv', 'age_min', 'age_max'].includes(c.k) ? 'num' : ''} onClick={() => setSort(sort?.k === c.k ? (sort.dir === 'asc' ? { k: c.k, dir: 'desc' } : null) : { k: c.k, dir: 'asc' })}>
                  {c.l}{sort?.k === c.k ? <span className="arr">{sort.dir === 'asc' ? '▲' : '▼'}</span> : ''}
                </th>
              ))}
            </tr></thead>
            <tbody>
              {sorted().map(o => (
                <tr key={o.id}>
                  {cols.map(c => <React.Fragment key={c.k}>{cell(o, c)}</React.Fragment>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {rows.length === 0 && <div className="empty">暂无数据</div>}
        <Pagination total={total} page={page} perPage={perPage} setPage={setPage} setPerPage={changePerPage} goPage={goPage} />
      </div>
    </div>
  )
}
