import React, { useEffect, useState } from 'react'
import { api } from '../api'
import { Modal, useToast, useConfirm } from '../components/ui'

const SOURCE_LABELS = {
  party: '甲方', task_id: '工单号', task_name: '任务名', type: '类型', operator: '运营商',
  url: 'URL', qty: '数量', duration: '时长', duration_mode: '单次/持续/暂停',
  age_min: '年龄下限', age_max: '年龄上限', pv: 'PV', region: '地区(派生)',
  province: '省份', excl_province: '排除省份', city: '地市', excl_city: '排除地市',
}

const emptyStyle = { zebra: 'FFFFFF', border: true, font: '宋体', font_size: 11, row_height: 20, center: true }

export default function Templates() {
  const toast = useToast()
  const [confirm, confirmEl] = useConfirm()
  const [rows, setRows] = useState([])
  const [modal, setModal] = useState(null) // {isNew, form}

  async function load() {
    const r = await api.get('/api/order-templates')
    setRows(r.data || [])
  }
  useEffect(() => { load() }, [])

  function openCreate() {
    setModal({ isNew: true, form: { code: '', name: '', party: '通用', filename_rule: '', columns: [{ name: '', source: '', fixed: '', width: '', split_url: false, merge: true }], style: { ...emptyStyle }, match_rule: {} } })
  }
  function openEdit(t) {
    setModal({ isNew: false, form: { id: t.id, code: t.code, name: t.name, party: t.party, filename_rule: t.filename_rule, columns: t.columns || [], style: { ...emptyStyle, ...(t.style || {}) }, match_rule: t.match_rule || {} } })
  }

  function setF(k, v) { setModal({ ...modal, form: { ...modal.form, [k]: v } }) }
  function setStyle(k, v) { setModal({ ...modal, form: { ...modal.form, style: { ...modal.form.style, [k]: v } } }) }
  function setRule(k, v) { setModal({ ...modal, form: { ...modal.form, match_rule: { ...modal.form.match_rule, [k]: v } } }) }
  function setCol(i, k, v) { const cols = [...modal.form.columns]; cols[i] = { ...cols[i], [k]: v }; setF('columns', cols) }
  function addCol() { setF('columns', [...modal.form.columns, { name: '', source: '', fixed: '', width: '', split_url: false, merge: true }]) }
  function delCol(i) { setF('columns', modal.form.columns.filter((_, j) => j !== i)) }
  function moveCol(i, d) { const cols = [...modal.form.columns]; const j = i + d; if (j < 0 || j >= cols.length) return; [cols[i], cols[j]] = [cols[j], cols[i]]; setF('columns', cols) }

  async function save() {
    const f = modal.form
    if (!f.code || !f.name) { toast('请填写编码和名称'); return }
    const cols = f.columns.filter(c => c.name || c.source || c.fixed)
    try {
      if (modal.isNew) await api.post('/api/order-templates', { ...f, columns: cols })
      else await api.put(`/api/order-templates/${f.id}`, { ...f, columns: cols })
      toast('已保存'); setModal(null); load()
    } catch (e) { toast(e.message) }
  }

  async function del(t) {
    if (!(await confirm(`确认删除模版「${t.name}」？`))) return
    try { await api.del(`/api/order-templates/${t.id}`); toast('已删除'); load() } catch (e) { toast(e.message) }
  }

  return (
    <div className="page">
      {confirmEl}
      <div className="toolbar">
        <span className="spacer" />
        <button className="btn primary" onClick={openCreate}>+ 新增模版</button>
      </div>
      <div className="panel">
        <div className="table-scroll">
          <table>
            <thead><tr><th>模版</th><th>编码</th><th>甲方</th><th>文件名规则</th><th>列数</th><th className="ops">操作</th></tr></thead>
            <tbody>
              {rows.map(t => (
                <tr key={t.id}>
                  <td>{t.name}</td><td>{t.code}</td><td>{t.party}</td>
                  <td><code>{t.filename_rule}</code></td><td>{(t.columns || []).length}</td>
                  <td className="ops">
                    <button className="btn small" onClick={() => openEdit(t)}>编辑</button>{' '}
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
        <Modal title={modal.isNew ? '新增自定义模版' : '编辑自定义模版'} onClose={() => setModal(null)} wide>
          <div className="row">
            <div className="field"><label>模版名称</label><input value={modal.form.name} onChange={e => setF('name', e.target.value)} /></div>
            <div className="field"><label>编码</label><input value={modal.form.code} onChange={e => setF('code', e.target.value)} /></div>
          </div>
          <div className="row">
            <div className="field"><label>甲方</label>
              <select value={modal.form.party} onChange={e => setF('party', e.target.value)}><option>牛</option><option>新</option><option>通用</option></select></div>
            <div className="field"><label>文件名规则</label><input value={modal.form.filename_rule} onChange={e => setF('filename_rule', e.target.value)} placeholder="{MMdd}-LM牛-提单表.xlsx" /></div>
          </div>
          <div className="note" style={{ marginTop: 4 }}>占位符：<code>{'{MMdd}'}</code>日期 <code>{'{party}'}</code>牛/新 <code>{'{type}'}</code>类型 <code>{'{region}'}</code>国省直辖市/地级市 <code>{'{gray}'}</code>灰</div>

          <h3 style={{ margin: '10px 0 6px' }}>列定义（表头 ↔ 来源字段）</h3>
          <div className="table-scroll" style={{ maxHeight: 280 }}>
            <table>
              <thead><tr><th style={{ width: 30 }}></th><th>表头名</th><th>来源字段</th><th>固定值</th><th style={{ width: 60 }}>列宽</th><th style={{ width: 60 }}>URL拆行</th><th style={{ width: 60 }}>跨行合并</th><th className="ops">操作</th></tr></thead>
              <tbody>
                {modal.form.columns.map((c, i) => (
                  <tr key={i}>
                    <td className="ops">
                      <button className="btn small" onClick={() => moveCol(i, -1)}>↑</button>{' '}
                      <button className="btn small" onClick={() => moveCol(i, 1)}>↓</button>
                    </td>
                    <td><input value={c.name} onChange={e => setCol(i, 'name', e.target.value)} placeholder="列名" /></td>
                    <td>
                      <select value={c.source} onChange={e => setCol(i, 'source', e.target.value)}>
                        <option value="">(固定值)</option>
                        {Object.keys(SOURCE_LABELS).map(k => <option key={k} value={k}>{SOURCE_LABELS[k]}</option>)}
                      </select>
                    </td>
                    <td><input value={c.fixed || ''} onChange={e => setCol(i, 'fixed', e.target.value)} placeholder="固定值" disabled={!!c.source} /></td>
                    <td><input type="number" style={{ width: 60 }} value={c.width || ''} onChange={e => setCol(i, 'width', e.target.value === '' ? '' : Number(e.target.value))} placeholder="自动" /></td>
                    <td className="ops"><input type="checkbox" checked={!!c.split_url} onChange={e => setCol(i, 'split_url', e.target.checked)} /></td>
                    <td className="ops"><input type="checkbox" checked={!!c.merge} onChange={e => setCol(i, 'merge', e.target.checked)} /></td>
                    <td className="ops"><button className="btn small danger" onClick={() => delCol(i)}>删</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <button className="btn small" style={{ marginTop: 6 }} onClick={addCol}>+ 添加列</button>

          <h3 style={{ margin: '14px 0 6px' }}>版式 & 匹配规则</h3>
          <div className="row">
            <div className="field"><label>斑马纹色</label>
              <input type="color" style={{ height: 32, padding: 2 }}
                value={modal.form.style.zebra?.startsWith('#') ? modal.form.style.zebra : '#' + (modal.form.style.zebra || 'FFFFFF')}
                onChange={e => setStyle('zebra', e.target.value)} />
            </div>
            <div className="field"><label>字体</label><input value={modal.form.style.font} onChange={e => setStyle('font', e.target.value)} /></div>
            <div className="field"><label>字号</label><input type="number" value={modal.form.style.font_size} onChange={e => setStyle('font_size', Number(e.target.value))} /></div>
            <div className="field"><label>行高</label><input type="number" value={modal.form.style.row_height} onChange={e => setStyle('row_height', Number(e.target.value))} /></div>
          </div>
          <div className="row">
            <label style={{ display: 'flex', alignItems: 'center', gap: 6 }}><input type="checkbox" checked={!!modal.form.style.border} onChange={e => setStyle('border', e.target.checked)} /> 边框</label>
            <label style={{ display: 'flex', alignItems: 'center', gap: 6 }}><input type="checkbox" checked={!!modal.form.style.center} onChange={e => setStyle('center', e.target.checked)} /> 居中</label>
          </div>
          <div className="row" style={{ marginTop: 8 }}>
            <div className="field"><label>匹配-类型</label>
              <select value={modal.form.match_rule.type || ''} onChange={e => setRule('type', e.target.value)}><option value="">不限</option><option value="106">106</option><option value="dpi">dpi</option><option value="小程序">小程序</option></select></div>
            <div className="field"><label>匹配-地区粒度</label>
              <select value={modal.form.match_rule.region || ''} onChange={e => setRule('region', e.target.value)}><option value="">不限</option><option value="国省">国省直辖市</option><option value="地级市">地级市</option></select></div>
          </div>

          <div className="foot">
            <button className="btn" onClick={() => setModal(null)}>取消</button>
            <button className="btn primary" onClick={save}>保存</button>
          </div>
        </Modal>
      )}
    </div>
  )
}
