import React, { useEffect, useRef, useState } from 'react'
import { api, getToken } from '../api'

const CHIPS = ['今日经营', '最近7天趋势', '代理排行', '客户余额', '在执订单', '停单提醒', '账单预警']

function clamp(v, min, max) { return Math.min(Math.max(v, min), max) }

function inline(s) {
  const parts = String(s).split(/(\*\*[^*]+\*\*|`[^`]+`)/g)
  return parts.map((p, i) => {
    if (p.startsWith('**') && p.endsWith('**')) return <b key={i}>{p.slice(2, -2)}</b>
    if (p.startsWith('`') && p.endsWith('`')) return <code key={i}>{p.slice(1, -1)}</code>
    return <React.Fragment key={i}>{p}</React.Fragment>
  })
}

function markdown(text) {
  if (!text) return null
  return String(text).split('\n').map((line, i) => {
    if (/^#{1,4}\s+/.test(line)) {
      return <div key={i} className="ai-md-h">{inline(line.replace(/^#{1,4}\s+/, ''))}</div>
    }
    if (/^[-*]\s+/.test(line)) {
      return <div key={i} className="ai-md-li"><span className="ai-md-bullet">•</span>{inline(line.replace(/^[-*]\s+/, ''))}</div>
    }
    if (/^\d+[.、]\s*/.test(line)) {
      const m = line.match(/^(\d+)[.、]\s*/)
      return <div key={i} className="ai-md-li"><span className="ai-md-bullet">{m[1]}.</span>{inline(line.slice(m[0].length))}</div>
    }
    if (line.trim() === '') return <div key={i} style={{ height: 4 }} />
    return <div key={i}>{inline(line)}</div>
  })
}

function Card({ card }) {
  if (!card) return null
  return (
    <div className="ai-card">
      <div className="ai-card-title">{card.title}</div>
      {card.type === 'table' && card.columns && (
        <div className="ai-card-table">
          <table>
            <thead><tr>{card.columns.map(c => <th key={c}>{c}</th>)}</tr></thead>
            <tbody>
              {(card.rows || []).map((r, i) => (
                <tr key={i}>{card.columns.map(c => <td key={c}>{r[c] ?? '—'}</td>)}</tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {(card.caliber || card.source) && (
        <div className="ai-card-foot">口径：{card.caliber || '—'} ｜ 来源：{card.source || '—'}</div>
      )}
    </div>
  )
}

export default function AiChat() {
  const [open, setOpen] = useState(false)
  const [sessions, setSessions] = useState([])
  const [sessionId, setSessionId] = useState(0)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [showSessions, setShowSessions] = useState(false)
  const boxRef = useRef(null)
  const fabRef = useRef(null)
  const drawerRef = useRef(null)
  const [fabPos, setFabPos] = useState(null)
  const [drawerPos, setDrawerPos] = useState(null)
  const fabDrag = useRef({ dragging: false, moved: false, sx: 0, sy: 0, lx: 0, ly: 0 })
  const drawerDrag = useRef({ dragging: false, sx: 0, sy: 0, lx: 0, ly: 0 })

  function loadSessions() {
    api.get('/api/ai/sessions').then(r => setSessions(r.data || [])).catch(() => {})
  }

  useEffect(() => { if (open) loadSessions() }, [open])

  useEffect(() => {
    if (boxRef.current) boxRef.current.scrollTop = boxRef.current.scrollHeight
  }, [messages])

  function newChat() {
    setSessionId(0); setMessages([]); setShowSessions(false)
  }

  function openSession(s) {
    setSessionId(s.id)
    setShowSessions(false)
    api.get(`/api/ai/sessions/${s.id}/messages`).then(r => {
      setMessages((r.data || []).filter(m => m.role !== 'system').map(m => ({ role: m.role, content: m.content })))
    }).catch(() => {})
  }

  async function delSession(id) {
    try {
      await api.del(`/api/ai/sessions/${id}`)
      if (id === sessionId) newChat()
      loadSessions()
    } catch (e) { /* ignore */ }
  }

  async function send(text) {
    const t = (text ?? input).trim()
    if (!t || sending) return
    setInput('')
    setMessages(m => [...m, { role: 'user', content: t }, { role: 'assistant', content: '', cards: [] }])
    setSending(true)
    try {
      const resp = await fetch('/api/ai/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + getToken() },
        body: JSON.stringify({ session_id: sessionId, message: t }),
      })
      if (!resp.ok || !resp.body) {
        const err = await resp.json().catch(() => ({}))
        appendAssistant(null, err.msg || err.detail || '请求失败')
        return
      }
      const reader = resp.body.getReader()
      const decoder = new TextDecoder()
      let buf = ''
      let newSessionId = sessionId
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buf += decoder.decode(value, { stream: true })
        const parts = buf.split('\n\n')
        buf = parts.pop()
        for (const part of parts) {
          for (const line of part.split('\n')) {
            if (!line.startsWith('data: ')) continue
            let ev
            try { ev = JSON.parse(line.slice(6)) } catch { continue }
            if (ev.type === 'token' || ev.type === 'text') appendAssistant(null, ev.data, true)
            else if (ev.type === 'card') appendAssistant(ev.data, null, false)
            else if (ev.type === 'error') appendAssistant(null, ev.data, false)
            else if (ev.type === 'done' && ev.data && ev.data.session_id) newSessionId = ev.data.session_id
          }
        }
      }
      if (newSessionId && newSessionId !== sessionId) {
        setSessionId(newSessionId)
        loadSessions()
      }
    } catch (e) {
      appendAssistant(null, '网络错误：' + e.message)
    } finally {
      setSending(false)
    }
  }

  function appendAssistant(card, text, appendText) {
    setMessages(m => {
      const copy = [...m]
      const last = copy[copy.length - 1]
      if (!last || last.role !== 'assistant') return copy
      const next = { ...last }
      if (card) next.cards = [...(next.cards || []), card]
      if (text != null) next.content = appendText ? (next.content || '') + text : (next.content || '') + (next.content ? '\n' : '') + text
      copy[copy.length - 1] = next
      return copy
    })
  }

  function onFabPointerDown(e) {
    const r = fabRef.current.getBoundingClientRect()
    fabDrag.current = { dragging: true, moved: false, sx: e.clientX, sy: e.clientY, lx: r.left, ly: r.top }
    fabRef.current.setPointerCapture(e.pointerId)
    document.body.style.userSelect = 'none'
  }
  function onFabPointerMove(e) {
    const d = fabDrag.current
    if (!d.dragging) return
    if (Math.abs(e.clientX - d.sx) + Math.abs(e.clientY - d.sy) > 4) d.moved = true
    setFabPos({ x: clamp(d.lx + e.clientX - d.sx, 8, window.innerWidth - 60), y: clamp(d.ly + e.clientY - d.sy, 8, window.innerHeight - 60) })
  }
  function onFabPointerUp() {
    fabDrag.current.dragging = false
    document.body.style.userSelect = ''
  }
  function onFabClick() {
    if (fabDrag.current.moved) { fabDrag.current.moved = false; return }
    setOpen(!open)
  }

  function onDrawerPointerDown(e) {
    if (e.target.closest('button')) return
    const r = drawerRef.current.getBoundingClientRect()
    drawerDrag.current = { dragging: true, sx: e.clientX, sy: e.clientY, lx: r.left, ly: r.top }
    e.currentTarget.setPointerCapture(e.pointerId)
    document.body.style.userSelect = 'none'
  }
  function onDrawerPointerMove(e) {
    const d = drawerDrag.current
    if (!d.dragging) return
    setDrawerPos({ x: clamp(d.lx + e.clientX - d.sx, 8, window.innerWidth - 200), y: clamp(d.ly + e.clientY - d.sy, 8, window.innerHeight - 100) })
  }
  function onDrawerPointerUp() {
    drawerDrag.current.dragging = false
    document.body.style.userSelect = ''
  }

  return (
    <>
      <button
        ref={fabRef}
        className="ai-fab"
        style={fabPos ? { left: fabPos.x, top: fabPos.y, right: 'auto', bottom: 'auto' } : undefined}
        onPointerDown={onFabPointerDown}
        onPointerMove={onFabPointerMove}
        onPointerUp={onFabPointerUp}
        onClick={onFabClick}
        title="小护卫 AI 助手（可拖动）"
      >🛡️</button>
      {open && (
        <div
          ref={drawerRef}
          className="ai-drawer"
          style={drawerPos ? { left: drawerPos.x, top: drawerPos.y, right: 'auto' } : undefined}
        >
          <div
            className="ai-head"
            onPointerDown={onDrawerPointerDown}
            onPointerMove={onDrawerPointerMove}
            onPointerUp={onDrawerPointerUp}
          >
            <span>🛡️ 小护卫 AI 助手</span>
            <div>
              <button className="btn small" onClick={() => setShowSessions(!showSessions)}>会话</button>
              <button className="btn small" onClick={newChat}>新对话</button>
              <button className="btn small" onClick={() => setOpen(false)}>✕</button>
            </div>
          </div>
          {showSessions && (
            <div className="ai-sessions">
              {sessions.length === 0 && <div className="ai-empty">暂无历史会话</div>}
              {sessions.map(s => (
                <div key={s.id} className="ai-session-item" onClick={() => openSession(s)}>
                  <span className="ai-session-title">{s.title || '未命名'}</span>
                  <button className="ai-session-del" onClick={e => { e.stopPropagation(); delSession(s.id) }}>删</button>
                </div>
              ))}
            </div>
          )}
          <div className="ai-body" ref={boxRef}>
            {messages.length === 0 && (
              <div className="ai-welcome">
                <div className="ai-welcome-title">你好，我是小护卫 🛡️</div>
                <div className="ai-welcome-sub">可以直接问我：今天经营怎么样、代理排行、客户余额、在执订单等</div>
                <div className="ai-chips">
                  {CHIPS.map(c => <button key={c} className="ai-chip" onClick={() => send(c)}>{c}</button>)}
                </div>
              </div>
            )}
            {messages.map((m, i) => (
              <div key={i} className={`ai-msg ${m.role}`}>
                {m.role === 'assistant' && (m.cards || []).map((c, j) => <Card key={j} card={c} />)}
                {m.content && <div className="ai-text">{markdown(m.content)}</div>}
                {m.role === 'assistant' && sending && i === messages.length - 1 && !m.content && (m.cards || []).length === 0 && (
                  <div className="ai-text ai-typing">小护卫思考中…</div>
                )}
              </div>
            ))}
          </div>
          <div className="ai-input">
            <input
              value={input}
              placeholder="问点什么…（Enter 发送）"
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') send() }}
              disabled={sending}
            />
            <button className="btn primary" onClick={() => send()} disabled={sending}>{sending ? '…' : '发送'}</button>
          </div>
        </div>
      )}
    </>
  )
}
