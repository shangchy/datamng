import React, { useState, useRef, useEffect } from 'react'
import { createPortal } from 'react-dom'

export default function MultiSelect({ label, options, value, onChange, placeholder, full, disabled, searchable }) {
  const [open, setOpen] = useState(false)
  const [kw, setKw] = useState('')
  const [pos, setPos] = useState({ top: 0, left: 0, width: 0 })
  const btnRef = useRef(null)
  const items = (options || []).map(o => typeof o === 'object' && o !== null ? o : { value: o, label: String(o) })
  const selected = (value || '').split(',').filter(Boolean)
  const filtered = searchable && kw.trim()
    ? items.filter(it => String(it.label).toLowerCase().includes(kw.trim().toLowerCase()))
    : items
  function toggle(v) {
    const next = selected.includes(v) ? selected.filter(x => x !== v) : [...selected, v]
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
            {filtered.map(it => (
              <label key={it.value}><input type="checkbox" checked={selected.includes(it.value)} onChange={() => toggle(it.value)} /> {it.label}</label>
            ))}
            {filtered.length === 0 && <div className="ms-empty">无匹配结果</div>}
          </div>
        </div>,
        document.body
      )}
    </div>
  )
}
