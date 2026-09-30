import React, { useState } from 'react'
import MultiSelect from './MultiSelect'

const ENUM_COLS = {
  status: ['未提', '在执', '待停', '已停', '改单', '启用', '停用', '已停止', '未处理', '已处理'],
  type: ['停单提醒', '账单预警'],
  level: ['高', '中', '低'],
  gender: ['男', '女'],
  deposit_status: ['正常缴存', '封存'],
  wash_status: ['未加名', '已加名', '已拆分'],
  ctype: ['上游', '下游'],
  role: ['超级管理员', '运营', '财务', '只读'],
  coop: ['合作中', '暂停', '已终止', '洽谈中'],
}

const DATE_KEYS = ['start_date', 'end_date', 'order_date', 'biz_date', 'stop_date']
const MULTI_COLS = ['province', 'city']
const NON_FILTER = ['region', 'url', 'updated_at', 'created_at', 'last_login_at', 'time', 'id']

export default function FilterBar({ cols, filters, setFilters, onSearch, fieldOptions = {}, actions = true }) {
  const list = cols.filter(c => !NON_FILTER.includes(c.k))

  return (
    <>
      {list.map(c => {
        if (MULTI_COLS.includes(c.k)) {
          return <MultiSelect key={c.k} label={c.l} options={fieldOptions[c.k] || []} value={filters[c.k]} onChange={v => setFilters({ ...filters, [c.k]: v })} />
        }
        const opts = fieldOptions[c.k] || ENUM_COLS[c.k]
        if (opts) {
          return (
            <select key={c.k} value={filters[c.k] || ''} onChange={e => setFilters({ ...filters, [c.k]: e.target.value })}>
              <option value="">{c.l}</option>
              {opts.map(o => {
                const val = typeof o === 'object' ? o.value : o
                const label = typeof o === 'object' ? o.label : o
                return <option key={val} value={val}>{label}</option>
              })}
            </select>
          )
        }
        if (DATE_KEYS.includes(c.k)) {
          return <input key={c.k} type="date" value={filters[c.k] || ''} onChange={e => setFilters({ ...filters, [c.k]: e.target.value })} />
        }
        return <input key={c.k} placeholder={c.l} value={filters[c.k] || ''} onChange={e => setFilters({ ...filters, [c.k]: e.target.value })} />
      })}
      {actions && <button className="btn primary" onClick={() => onSearch()}>查询</button>}
      {actions && <button className="btn" onClick={() => { setFilters({}); onSearch({}) }}>重置</button>}
    </>
  )
}

export function buildQuery(filters) {
  const params = new URLSearchParams()
  Object.keys(filters).forEach(k => { if (filters[k] !== '' && filters[k] !== undefined && filters[k] !== null) params.set(k, filters[k]) })
  return params.toString()
}
