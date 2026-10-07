import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, setAuth } from '../api'
import { ClearableInput } from '../components/ui'

const FLOAT_ITEMS = [
  { text: '订单管理', left: 5, top: 16, size: 16, delay: 0 },
  { text: '¥ 13787.25', left: 30, top: 62, size: 20, delay: 0.6, color: '#7dd3fc' },
  { text: '客户管理', left: 15, top: 44, size: 15, delay: 1.2 },
  { text: '0.06', left: 55, top: 12, size: 19, delay: 0.3, color: '#a5b4fc' },
  { text: '数据采集', left: 40, top: 76, size: 15, delay: 1.8 },
  { text: '240 万', left: 68, top: 50, size: 22, delay: 0.9, color: '#86efac' },
  { text: '账单结算', left: 78, top: 18, size: 15, delay: 2.4 },
  { text: '¥ 29234.59', left: 86, top: 42, size: 20, delay: 1.5, color: '#fde68a' },
  { text: '渠道分发', left: 8, top: 84, size: 15, delay: 3 },
  { text: '682241', left: 60, top: 88, size: 18, delay: 0.4, color: '#93c5fd' },
  { text: '品类分析', left: 22, top: 6, size: 15, delay: 2 },
  { text: '12%', left: 47, top: 32, size: 21, delay: 1, color: '#fca5a5' },
  { text: '预警监控', left: 90, top: 72, size: 15, delay: 2.8 },
  { text: '106', left: 73, top: 6, size: 19, delay: 0.2, color: '#a5b4fc' },
  { text: '$ 5000', left: 33, top: 56, size: 18, delay: 2.2, color: '#7dd3fc' },
  { text: '¥', left: 18, top: 68, size: 26, delay: 1.6, color: '#fde68a' },
  { text: '¥', left: 92, top: 10, size: 28, delay: 3.4, color: '#fde68a' },
  { text: '138****1234', left: 50, top: 20, size: 15, delay: 0.7, color: '#c4b5fd' },
]

export default function Login() {
  const nav = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [err, setErr] = useState('')

  async function submit(e) {
    e.preventDefault()
    setErr('')
    try {
      const r = await api.post('/api/auth/login', { username, password })
      setAuth(r.data.token, r.data.user)
      nav('/')
    } catch (e) {
      setErr(e.message)
    }
  }

  return (
    <div className="login-wrap">
      <img src="/lemon-bg.png" className="login-bg-img" alt="" />
      <div className="login-grid" />
      <div className="login-halo" />
      <div className="login-nodes">
        {[...Array(14)].map((_, i) => <span key={i} className="node" style={{ left: `${(i * 7 + 3) % 100}%`, top: `${(i * 13 + 8) % 100}%`, animationDelay: `${i * 0.4}s` }} />)}
      </div>
      <div className="login-words">
        {FLOAT_ITEMS.map((w, i) => (
          <span key={i} style={{ left: `${w.left}%`, top: `${w.top}%`, fontSize: w.size, animationDelay: `${w.delay}s`, color: w.color }}>{w.text}</span>
        ))}
      </div>
      <form className="login-box" onSubmit={submit}>
        <h1><img src="/logo.jpeg" alt="logo" />LM订单管理系统</h1>
        <div className="sub">订单 · 客户 · 数据 全流程管理</div>
        <label>用户名</label>
        <ClearableInput value={username} onChange={e => setUsername(e.target.value)} placeholder="用户名" />
        <label>密码</label>
        <input type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="密码" />
        {err && <div style={{ color: 'var(--red)', fontSize: 12, marginTop: 8 }}>{err}</div>}
        <button className="btn primary" type="submit">登 录</button>
      </form>
    </div>
  )
}
