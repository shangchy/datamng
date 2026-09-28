import React, { useState, useRef, useEffect } from 'react'
import { createPortal } from 'react-dom'

export default function MultiSelect({ label, options, value, onChange, placeholder, full, disabled, searchable }) {
  const [open, setOpen] = useState(false)
  const [kw, setKw] = useState('')
  const [pos, setPos] = useState({ top: 0, left: 0, width: 0 })
  const btnRef = useRef(null)
  const selected = (value || '').split(',').filter(Boolean)
  const filtered = searchable && kw.trim()
    ? options.filter(o => String(o).toLowerCase().includes(kw.trim().toLowerCase()))
    : options
  function toggle(o) {
    const next = selected.includes(o) ? selected.filter(x => x !== o) : [...selected, o]
    onChange(next.join(','))
  }
  function openDropdown() {
    const r = btnRef.current.getBoundingClientRect()
    setPos({ top: r.bottom + 4, left: r.left, width: r.width })
    setKw('')
    setOpen(true)
  }
  useEffect(() => {
    if (!open) return
    function onDoc(e) {
      if (btnRef.current && !btnRef.current.contains(e.target) && !e.target.closest('.ms-dropdown')) setOpen(false)
    }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [open])
  return (
    <div className="multiselect" style={full ? { width: '100%' } : {}}>
      <button type="button" ref={btnRef} className="btn" disabled={disabled}
        style={full ? { width: '100%', textAlign: 'left' } : {}}
        onClick={() => (open ? setOpen(false) : openDropdown())}>
        {selected.length ? `${placeholder || label}(${selected.length})` : (placeholder || label)} ▾
      </button>
      {open && createPortal(
        <div className="ms-dropdown" style={{ position: 'fixed', top: pos.top, left: pos.left, width: pos.width, zIndex: 1000 }}>
          {searchable && (
            <input className="ms-search" placeholder="搜索..." value={kw} onChange={e => setKw(e.target.value)} />
          )}
          <div className="ms-list">
            {filtered.map(o => (
              <label key={o}><input type="checkbox" checked={selected.includes(o)} onChange={() => toggle(o)} /> {o}</label>
            ))}
            {filtered.length === 0 && <div className="ms-empty">无匹配结果</div>}
          </div>
        </div>,
        document.body
      )}
    </div>
  )
}
