import React, { useEffect, useState } from 'react'
import { NavLink, Outlet, useNavigate, useLocation } from 'react-router-dom'
import { getUser, clearAuth, api } from '../api'
import AiChat from './AiChat'

const TITLE_MAP = {
  '/': '工作台', '/orders': '订单管理', '/daily': '日活数据', '/fund': '公积金',
  '/wash-names': '洗名库',
  '/customers': '客户管理', '/parts': '配件管理', '/categories': '品类管理',
  '/channels': '渠道管理', '/operators': '运营商管理', '/bills': '账单管理',
  '/source-files': '源头文件',
  '/alerts': '预警中心', '/accounts': '账户管理', '/templates': '模版管理',
  '/tidabiao-history': '提单历史',
  '/logs': '日志管理',
}

const MENUS = [
  { key: '/', name: '工作台', icon: '📊' },
  { key: '/orders', name: '订单管理', icon: '📝', perm: 'order:view' },
  { key: '/tidabiao-history', name: '提单历史', icon: '🗂️', perm: 'order:view' },
  { key: 'data', name: '数据管理', icon: '📋', perm: 'data:view', children: [
    { key: '/daily', name: '日活数据' },
    { key: '/wash-names', name: '洗名库' },
    { key: '/fund', name: '公积金' },
    { key: '/source-files', name: '源头文件' },
  ] },
  { key: '/bills', name: '账单管理', icon: '💰', perm: 'bill:view' },
  { key: 'master', name: '基础数据', icon: '🗄️', perm: 'master:view', children: [
    { key: '/parts', name: '配件管理' },
    { key: '/categories', name: '品类管理' },
    { key: '/channels', name: '渠道管理' },
    { key: '/operators', name: '运营商管理' },
    { key: '/templates', name: '模版管理' },
  ] },
  { key: '/customers', name: '客户管理', icon: '👤', perm: 'customer:view' },
  { key: '/accounts', name: '账户管理', icon: '⚙️', admin: true },
  { key: '/logs', name: '日志管理', icon: '📜', admin: true },
]

export default function Layout() {
  const user = getUser() || {}
  const nav = useNavigate()
  const location = useLocation()
  const [openSub, setOpenSub] = useState({})
  const [alertCounts, setAlertCounts] = useState({ stop: 0, bill: 0 })

  useEffect(() => {
    const refresh = () => api.get('/api/dashboard/alerts-count').then(r => setAlertCounts(r.data)).catch(() => {})
    refresh()
    window.addEventListener('alert-count-refresh', refresh)
    return () => window.removeEventListener('alert-count-refresh', refresh)
  }, [])

  function logout() { clearAuth(); nav('/login') }

  function badgeOf(key) {
    if (key === '/orders') return alertCounts.stop
    if (key === '/customers') return alertCounts.bill
    return 0
  }

  function renderMenus() {
    const perms = user.permissions || []
    const isAdmin = user.role_code === 'admin' || perms.includes('*')
    return MENUS.filter(m => {
      if (m.admin && !isAdmin) return false
      if (m.perm && !isAdmin && !perms.includes(m.perm)) return false
      return true
    }).map(m => {
      if (m.children) {
        const open = openSub[m.key]
        return (
          <React.Fragment key={m.key}>
            <a onClick={() => setOpenSub({ ...openSub, [m.key]: !open })}>
              <span>{m.icon}</span>{m.name}<span className="toggle">{open ? '▼' : '▶'}</span>
            </a>
            {open && m.children.map(c => (
              <NavLink key={c.key} to={c.key} className="sub">
                <span></span>{c.name}
              </NavLink>
            ))}
          </React.Fragment>
        )
      }
      return (
        <NavLink key={m.key} to={m.key} end={m.key === '/'} className={({ isActive }) => isActive ? 'active' : ''}>
          <span>{m.icon}</span>{m.name}{badgeOf(m.key) > 0 && <span className="nav-badge">{badgeOf(m.key)}</span>}
        </NavLink>
      )
    })
  }

  return (
    <div className="layout">
      <aside className="side">
        <div className="logo"><img src="/logo.jpeg" alt="logo" />LM<span>订单管理系统</span></div>
        <nav>{renderMenus()}</nav>
        <div className="foot">
          <div className="foot-user">
            <span className="foot-name">{user.nickname || user.username}</span>
            <span className="badge">{user.role}</span>
          </div>
          <button className="btn small" onClick={logout}>退出</button>
        </div>
      </aside>
      <div className="main">
        {location.pathname !== '/' && <div className="page-title">{TITLE_MAP[location.pathname] || '工作台'}</div>}
        <div className="content"><Outlet /></div>
      </div>
      <AiChat />
    </div>
  )
}
