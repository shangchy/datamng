import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { getToken } from './api'
import Layout from './components/Layout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Orders from './pages/Orders'
import Customers from './pages/Customers'
import SimpleList from './pages/SimpleList'
import Categories from './pages/Categories'
import TemplateManager from './pages/TemplateManager'
import TidabiaoHistory from './pages/TidabiaoHistory'
import Logs from './pages/Logs'

function RequireAuth({ children }) {
  if (!getToken()) return <Navigate to="/login" replace />
  return children
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/" element={<RequireAuth><Layout /></RequireAuth>}>
        <Route index element={<Dashboard />} />
        <Route path="orders" element={<Orders />} />
        <Route path="tidabiao-history" element={<TidabiaoHistory />} />
        <Route path="daily" element={<SimpleList kind="daily" />} />
        <Route path="source-files" element={<SimpleList kind="sourcefiles" />} />
        <Route path="wash-names" element={<SimpleList kind="washnames" />} />
        <Route path="fund" element={<SimpleList kind="fund" />} />
        <Route path="customers" element={<Customers />} />
        <Route path="parts" element={<SimpleList kind="urls" />} />
        <Route path="categories" element={<Categories />} />
        <Route path="templates" element={<TemplateManager />} />
        <Route path="channels" element={<SimpleList kind="channels" />} />
        <Route path="operators" element={<SimpleList kind="operators" />} />
        <Route path="bills" element={<SimpleList kind="bills" />} />
        <Route path="alerts" element={<SimpleList kind="alerts" />} />
        <Route path="accounts" element={<SimpleList kind="users" />} />
        <Route path="logs" element={<Logs />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}
