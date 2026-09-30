import React, { useEffect, useRef, useState } from 'react'
import { api, getToken, downloadFile } from '../api'
import { Modal, Badge, useToast, useConfirm, Loading } from '../components/ui'

function RichTextEditor({ value, onChange }) {
  const ref = useRef(null)
  const initialized = useRef(false)
  useEffect(() => {
    if (!initialized.current && ref.current) {
      ref.current.innerHTML = value || ''
      initialized.current = true
    }
  }, [])
  function exec(cmd) {
    document.execCommand(cmd, false, null)
    onChange(ref.current.innerHTML)
    ref.current.focus()
  }
  return (
    <div className="richtext">
      <div className="richtext-toolbar">
        <button type="button" title="加粗" onMouseDown={e => e.preventDefault()} onClick={() => exec('bold')}><b>B</b></button>
        <button type="button" title="斜体" onMouseDown={e => e.preventDefault()} onClick={() => exec('italic')}><i>I</i></button>
        <button type="button" title="下划线" onMouseDown={e => e.preventDefault()} onClick={() => exec('underline')}><u>U</u></button>
        <button type="button" title="无序列表" onMouseDown={e => e.preventDefault()} onClick={() => exec('insertUnorderedList')}>• 列表</button>
        <button type="button" title="有序列表" onMouseDown={e => e.preventDefault()} onClick={() => exec('insertOrderedList')}>1. 列表</button>
      </div>
      <div ref={ref} className="richtext-content" contentEditable suppressContentEditableWarning
        data-placeholder="填写模版用途、填写注意事项等"
        onInput={e => onChange(e.target.innerHTML)} />
    </div>
  )
}

export default function TemplateManager() {
  const { toast, showError } = useToast()
  const [confirm, confirmEl] = useConfirm()
  const [rows, setRows] = useState([])
  const [modal, setModal] = useState(null) // {isNew, form}
  const [q, setQ] = useState('')
  const [busy, setBusy] = useState(false)
  const [preview, setPreview] = useState(null) // {filename, sheets}
  const [detail, setDetail] = useState(null)
  const fileRef = useRef(null)

  async function load() {
    const r = await api.get('/api/templates')
    setRows(r.data || [])
  }
  useEffect(() => { load() }, [])

  async function search() {
    const r = await api.get('/api/templates?q=' + encodeURIComponent(q))
    setRows(r.data || [])
  }

  function openCreate() { setModal({ isNew: true, form: { ttype: '', tpl_type: '其他', code: '', description: '', status: 1, has_file: false, file_name: '' } }) }
  function openEdit(t) { setModal({ isNew: false, form: { id: t.id, ttype: t.ttype, tpl_type: t.tpl_type || '其他', code: t.code, description: t.description || '', status: t.status, has_file: t.has_file, file_name: t.file_name || t.name } }) }
  function setF(k, v) { setModal({ ...modal, form: { ...modal.form, [k]: v } }) }

  async function save() {
    const f = modal.form
    try {
      if (modal.isNew) {
        const r = await api.post('/api/templates', { ttype: f.ttype, tpl_type: f.tpl_type, description: f.description, status: f.status })
        toast(`已创建，模版编号 ${r.data.code}`)
      } else {
        await api.put(`/api/templates/${f.id}`, { ttype: f.ttype, tpl_type: f.tpl_type, description: f.description, status: f.status })
        toast('已保存')
      }
      setModal(null); load()
    } catch (e) { showError(e.message) }
  }

  async function del(t) {
    if (!(await confirm(`确认删除模版「${t.code}」？`))) return
    try { await api.del(`/api/templates/${t.id}`); toast('已删除'); load() } catch (e) { showError(e.message) }
  }

  async function upload(file) {
    setBusy(true)
    try {
      const fd = new FormData()
      fd.append('file', file)
      const res = await fetch(`/api/templates/${modal.form.id}/upload`, { method: 'POST', headers: { Authorization: 'Bearer ' + getToken() }, body: fd })
      const data = await res.json()
      if (!res.ok) throw new Error(data.msg || data.detail || '上传失败')
      setModal({ ...modal, form: { ...modal.form, file_name: data.data.filename, has_file: true } })
      toast('模版文件已上传'); load()
    } finally {
      setBusy(false)
    }
  }

  async function showPreview(t) {
    try {
      const r = await api.get(`/api/templates/${t.id}/preview`)
      setPreview(r.data)
    } catch (e) { showError(e.message) }
  }

  async function deleteFile() {
    if (!(await confirm('确认删除该模版文件？'))) return
    try {
      await api.del(`/api/templates/${modal.form.id}/file`)
      setModal({ ...modal, form: { ...modal.form, has_file: false, file_name: '' } })
      toast('模版文件已删除'); load()
    } catch (e) { showError(e.message) }
  }

  return (
    <div className="page">
      {confirmEl}
      {busy && <Loading text="正在上传模版，请稍候…" />}
      <input type="file" accept=".xlsx,.xls,.csv" style={{ display: 'none' }} ref={fileRef}
        onChange={e => { if (e.target.files[0]) upload(e.target.files[0]).catch(err => showError(err.message)); e.target.value = '' }} />
      <div className="toolbar">
        <input placeholder="名称 / 编号 / 文件名" style={{ width: 220 }} value={q} onChange={e => setQ(e.target.value)} onKeyDown={e => { if (e.key === 'Enter') search() }} />
        <button className="btn" onClick={search}>查询</button>
        <span className="spacer" />
        <button className="btn primary" onClick={openCreate}>+ 新增模版</button>
      </div>
      <div className="panel">
        <div className="table-scroll">
          <table>
            <thead><tr><th>模版类型</th><th>模版名称</th><th>模版编号</th><th>文件名</th><th>创建时间</th><th>更新时间</th><th className="ops">操作</th></tr></thead>
            <tbody>
              {rows.map(t => (
                <tr key={t.id} className="clickable" onDoubleClick={() => setDetail(t)}>
                  <td><Badge value={t.tpl_type || '其他'} /></td>
                  <td>{t.ttype || '—'}</td>
                  <td><code>{t.code}</code></td>
                  <td>{t.has_file ? <a className="link" onClick={() => showPreview(t)}>{t.file_name || t.name}</a> : <Badge value="未上传" />}</td>
                  <td>{t.created_at || '—'}</td>
                  <td>{t.updated_at || '—'}</td>
                  <td className="ops">
                    <button className="btn small" onClick={() => openEdit(t)}>编辑</button>{' '}
                    {t.has_file && <button className="btn small green" onClick={() => downloadFile(`/api/templates/${t.id}/download`).catch(e => showError(e.message))}>下载</button>}{' '}
                    <button className="btn small danger" onClick={() => del(t)}>删除</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {rows.length === 0 && <div className="empty">暂无模版</div>}
      </div>

      {modal && (
        <Modal title={modal.isNew ? '新增模版' : '编辑模版'} onClose={() => setModal(null)} wide>
          <div className="field" style={{ marginBottom: 10 }}><label>模版类型</label>
            <select value={modal.form.tpl_type} onChange={e => setF('tpl_type', e.target.value)}>
              <option value="订单">订单</option><option value="出数">出数</option><option value="账单">账单</option><option value="其他">其他</option>
            </select></div>
          <div className="field" style={{ marginBottom: 10 }}><label>模版名称</label>
            <input value={modal.form.ttype} onChange={e => setF('ttype', e.target.value)} placeholder="如 提单表 / 出数模版A" /></div>
          <div className="field" style={{ marginBottom: 14 }}><label>模版编号</label>
            <input value={modal.form.code} disabled placeholder={modal.isNew ? '保存后自动生成' : ''} /></div>
          <div className="field" style={{ marginBottom: 14 }}><label>说明（模版用途、填写注意事项等）</label>
            <RichTextEditor value={modal.form.description} onChange={v => setF('description', v)} /></div>
          {!modal.isNew && (
            <div className="field" style={{ marginBottom: 14 }}>
              <label>模版文件</label>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, minHeight: 32 }}>
                {modal.form.has_file
                  ? <span style={{ fontSize: 13 }}><a className="link" onClick={() => showPreview(modal.form)}>{modal.form.file_name}</a></span>
                  : <span style={{ fontSize: 13, color: 'var(--sub)' }}>未上传</span>}
                <button className="btn small" onClick={() => fileRef.current.click()}>上传</button>
                {modal.form.has_file && <button className="btn small green" onClick={() => downloadFile(`/api/templates/${modal.form.id}/download`).catch(e => showError(e.message))}>下载</button>}
                {modal.form.has_file && <button className="btn small danger" onClick={deleteFile}>删除文件</button>}
              </div>
            </div>
          )}
          <div className="foot">
            <button className="btn" onClick={() => setModal(null)}>取消</button>
            <button className="btn primary" onClick={save}>保存</button>
          </div>
        </Modal>
      )}

      {preview && (
        <Modal title={`模版预览 · ${preview.filename}`} onClose={() => setPreview(null)} wide>
          {preview.sheets.map((s, si) => (
            <div key={si} style={{ marginBottom: 12 }}>
              <div className="note" style={{ marginBottom: 6 }}>工作表：{s.name}</div>
              <div className="table-scroll" style={{ maxHeight: 360 }}>
                <table>
                  <tbody>
                    {s.rows.map((r, ri) => (
                      <tr key={ri}>
                        {r.map((c, ci) => <td key={ci}>{c}</td>)}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ))}
          <div className="foot"><button className="btn primary" onClick={() => setPreview(null)}>关闭</button></div>
        </Modal>
      )}

      {detail && (
        <Modal title={`模版详情 · ${detail.code}`} onClose={() => setDetail(null)} wide>
          <table className="kv"><tbody>
            <tr><td>模版类型</td><td><Badge value={detail.tpl_type || '其他'} /></td></tr>
            <tr><td>模版名称</td><td>{detail.ttype || '—'}</td></tr>
            <tr><td>模版编号</td><td>{detail.code}</td></tr>
            <tr><td>文件名</td><td>{detail.has_file ? (detail.file_name || detail.name) : '未上传'}</td></tr>
            <tr><td>创建时间</td><td>{detail.created_at || '—'}</td></tr>
            <tr><td>更新时间</td><td>{detail.updated_at || '—'}</td></tr>
          </tbody></table>
          <div className="field" style={{ marginTop: 14 }}><label>说明</label>
            <div className="richtext-view" dangerouslySetInnerHTML={{ __html: detail.description || '<span style="color:var(--sub)">—</span>' }} /></div>
          <div className="foot"><button className="btn primary" onClick={() => setDetail(null)}>关闭</button></div>
        </Modal>
      )}
    </div>
  )
}
