import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import { useToast, useConfirm } from '../components/ui'
import { PERM_TREE } from '../permTree'

export default function RolePerms() {
  const { toast, showError } = useToast()
  const [confirm, confirmEl] = useConfirm()
  const nav = useNavigate()
  const [roles, setRoles] = useState([])
  const [rid, setRid] = useState(null)
  const [codes, setCodes] = useState([])
  const [saving, setSaving] = useState(false)

  async function loadRoles() {
    const r = await api.get('/api/roles')
    const editable = (r.data || []).filter(x => x.code !== 'admin')
    setRoles(editable)
    if (editable.length) await selectRole(editable[0].id)
  }

  async function selectRole(id) {
    setRid(id)
    try {
      const pr = await api.get(`/api/roles/${id}/permissions`)
      setCodes(pr.data?.codes || [])
    } catch (e) { showError(e.message) }
  }

  useEffect(() => { loadRoles().catch(e => showError(e.message)) }, [])

  function toggle(code) {
    setCodes(c => c.includes(code) ? c.filter(x => x !== code) : [...c, code])
  }

  function toggleMenu(menu) {
    const allCodes = [menu.perm, ...menu.buttons.map(b => b.code)]
    const allOn = allCodes.every(c => codes.includes(c))
    setCodes(allOn ? codes.filter(c => !allCodes.includes(c)) : [...new Set([...codes, ...allCodes])])
  }

  async function save() {
    if (!rid) return
    setSaving(true)
    try {
      await api.put(`/api/roles/${rid}/permissions`, { codes })
      toast('权限已保存')
    } catch (e) { showError(e.message) } finally { setSaving(false) }
  }

  async function deleteRole() {
    if (!rid) return
    if (!(await confirm('确认删除该角色？该角色下不能有账户。', true))) return
    try {
      await api.del(`/api/roles/${rid}`)
      toast('角色已删除')
      await loadRoles()
    } catch (e) { showError(e.message) }
  }

  return (
    <div className="page">
      {confirmEl}
      <div className="toolbar">
        <div className="field" style={{ display: 'flex', alignItems: 'center', gap: 8, flex: 'none' }}>
          <label>角色</label>
          <select value={rid || ''} onChange={e => selectRole(Number(e.target.value))}>
            {roles.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
          </select>
        </div>
        <div className="toolbar-actions">
          <button className="btn" onClick={() => nav('/accounts')}>返回</button>
          <button className="btn danger" onClick={deleteRole}>删除角色</button>
          <button className="btn primary" disabled={saving} onClick={save}>保存</button>
        </div>
      </div>
      <div className="note" style={{ marginBottom: 10 }}>勾选菜单即拥有该菜单访问权；菜单下的按钮可单独勾选。超级管理员拥有全部权限，无需配置；修改后该角色用户需重新登录生效。</div>
      <div className="panel" style={{ flex: 1, overflow: 'auto' }}>
        {PERM_TREE.map(menu => {
          const allCodes = [menu.perm, ...menu.buttons.map(b => b.code)]
          const allOn = allCodes.every(c => codes.includes(c))
          const anyOn = allCodes.some(c => codes.includes(c))
          return (
            <div key={menu.module} style={{ border: '1px solid var(--line)', borderRadius: 8, marginBottom: 10, padding: '10px 14px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <input type="checkbox" checked={allOn} ref={el => el && (el.indeterminate = anyOn && !allOn)} onChange={() => toggleMenu(menu)} />
                <b>{menu.label}</b>
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px 18px', paddingLeft: 26, marginTop: 8 }}>
                {menu.buttons.map(b => (
                  <label key={b.code} style={{ display: 'inline-flex', alignItems: 'center', gap: 5, fontSize: 13 }}>
                    <input type="checkbox" checked={codes.includes(b.code)} onChange={() => toggle(b.code)} />
                    {b.label}
                  </label>
                ))}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
