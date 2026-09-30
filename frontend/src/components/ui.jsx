import React, { createContext, useContext, useState, useCallback } from 'react'

const ToastCtx = createContext({ toast: () => {}, showError: () => {} })
export const useToast = () => useContext(ToastCtx)

export function ErrorModal({ message, onClose }) {
  return (
    <div className="mask" style={{ zIndex: 400 }}>
      <div className="modal" style={{ width: 480 }}>
        <h3>
          <span className="modal-title" style={{ color: 'var(--red)' }}>提示</span>
          <button className="modal-close" title="关闭" onClick={onClose}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
          </button>
        </h3>
        <div className="modal-body">
          <div style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all', color: 'var(--red)' }}>{message}</div>
          <div className="foot">
            <button className="btn primary" onClick={onClose}>知道了</button>
          </div>
        </div>
      </div>
    </div>
  )
}

export function ToastProvider({ children }) {
  const [toast, setToast] = useState('')
  const [error, setError] = useState('')
  const show = useCallback((msg) => {
    setToast(msg)
    setTimeout(() => setToast(''), 2000)
  }, [])
  const showError = useCallback((msg) => setError(msg), [])
  return (
    <ToastCtx.Provider value={{ toast: show, showError }}>
      {children}
      {toast && <div className="toast">{toast}</div>}
      {error && <ErrorModal message={error} onClose={() => setError('')} />}
    </ToastCtx.Provider>
  )
}

export function Modal({ title, children, onClose, wide }) {
  return (
    <div className="mask" onClick={onClose}>
      <div className={`modal ${wide ? 'wide' : ''}`} onClick={e => e.stopPropagation()}>
        <h3>
          <span className="modal-title">{title}</span>
          <button className="modal-close" title="关闭" onClick={onClose}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
          </button>
        </h3>
        <div className="modal-body">{children}</div>
      </div>
    </div>
  )
}

export function ConfirmModal({ message, onConfirm, onCancel }) {
  return (
    <div className="mask" style={{ zIndex: 200 }}>
      <div className="modal" style={{ width: 440 }}>
        <h3>
          <span className="modal-title">操作确认</span>
          <button className="modal-close" title="关闭" onClick={onCancel}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
          </button>
        </h3>
        <div className="modal-body">
          <div style={{ marginBottom: 6, whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>{message}</div>
          <div className="foot">
            <button className="btn" onClick={onCancel}>取消</button>
            <button className="btn primary" onClick={onConfirm}>确认</button>
          </div>
        </div>
      </div>
    </div>
  )
}

export function useConfirm() {
  const [state, setState] = useState(null)
  const confirm = useCallback((message) => new Promise((resolve) => {
    setState({ message, resolve })
  }), [])
  const element = state ? (
    <ConfirmModal
      message={state.message}
      onConfirm={() => { state.resolve(true); setState(null) }}
      onCancel={() => { state.resolve(false); setState(null) }}
    />
  ) : null
  return [confirm, element]
}

export const BADGE = {
  '在执': 'blue', '已提交': 'green', '已停': 'red', '待停': 'amber', '未提': 'gray', '改单': 'violet',
  '启用': 'green', '停用': 'gray',
  '已处理': 'green', '未处理': 'red', '提醒': 'amber', '预警': 'red',
  '停单提醒': 'amber', '账单预警': 'red',
  '高': 'green', '中': 'amber', '低': 'gray', '上游': 'violet', '下游': 'blue',
  '已洗名': 'green', '只分': 'gray', '未命中': 'amber', '正常缴存': 'green', '封存': 'gray',
  '合作中': 'green', '已终止': 'gray', '男': 'blue', '女': 'violet',
  '订单': 'blue', '出数': 'violet', '账单': 'green', '其他': 'gray',
}

export function Badge({ value }) {
  return <span className={`badge ${BADGE[value] || 'gray'}`}>{value}</span>
}

export function Loading({ text = '处理中，请稍候…', progress }) {
  return (
    <div className="mask" style={{ zIndex: 300 }}>
      <div className={`loading-box${progress != null ? ' has-progress' : ''}`}>
        <span className="loading-spin" />
        <span>{text}</span>
        {progress != null && (
          <div className="progress-track">
            <div className="progress-fill" style={{ width: `${Math.min(100, Math.max(0, progress))}%` }} />
          </div>
        )}
        {progress != null && <span className="progress-num">{Math.round(progress)}%</span>}
      </div>
    </div>
  )
}
