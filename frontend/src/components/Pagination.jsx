import React from 'react'

export default function Pagination({ total, page, perPage, setPage, setPerPage, goPage }) {
  const pages = Math.max(1, Math.ceil(total / perPage))

  function pageNumbers() {
    const set = new Set([1, pages, page - 1, page, page + 1])
    const arr = [...set].filter(n => n >= 1 && n <= pages).sort((a, b) => a - b)
    const result = []
    let prev = 0
    for (const n of arr) {
      if (n - prev > 1) result.push('...')
      result.push(n)
      prev = n
    }
    return result
  }

  return (
    <div className="pager">
      <span>共 {total} 条</span>
      <select value={perPage} onChange={e => setPerPage(Number(e.target.value))}>
        <option value={10}>10 条/页</option>
        <option value={20}>20 条/页</option>
        <option value={50}>50 条/页</option>
        <option value={100}>100 条/页</option>
        <option value={500}>500 条/页</option>
      </select>
      <button className="btn small" disabled={page <= 1} onClick={() => goPage(1)}>«</button>
      <button className="btn small" disabled={page <= 10} onClick={() => goPage(page - 10)}>‹‹</button>
      <button className="btn small" disabled={page <= 1} onClick={() => goPage(page - 1)}>‹</button>
      {pageNumbers().map((n, i) => n === '...'
        ? <span key={`e${i}`}>…</span>
        : <button key={n} className={`btn small ${n === page ? 'primary' : ''}`} onClick={() => goPage(n)}>{n}</button>
      )}
      <button className="btn small" disabled={page >= pages} onClick={() => goPage(page + 1)}>›</button>
      <button className="btn small" disabled={page + 10 > pages} onClick={() => goPage(page + 10)}>››</button>
      <button className="btn small" disabled={page >= pages} onClick={() => goPage(pages)}>»</button>
    </div>
  )
}
