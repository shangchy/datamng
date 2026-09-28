const TOKEN_KEY = 'lm_token'
const USER_KEY = 'lm_user'

export function getToken() { return localStorage.getItem(TOKEN_KEY) }
export function setAuth(token, user) { localStorage.setItem(TOKEN_KEY, token); localStorage.setItem(USER_KEY, JSON.stringify(user)) }
export function clearAuth() { localStorage.removeItem(TOKEN_KEY); localStorage.removeItem(USER_KEY) }
export function getUser() { try { return JSON.parse(localStorage.getItem(USER_KEY) || 'null') } catch { return null } }

async function request(method, url, body) {
  const headers = { 'Content-Type': 'application/json' }
  const token = getToken()
  if (token) headers.Authorization = 'Bearer ' + token
  const res = await fetch(url, { method, headers, body: body ? JSON.stringify(body) : undefined })
  let data = {}
  try { data = await res.json() } catch {}
  if (!res.ok) {
    if (res.status === 401) { clearAuth(); window.location.href = '/login' }
    throw new Error(data.msg || data.detail || '请求失败')
  }
  return data
}

export const api = {
  get: (url) => request('GET', url),
  post: (url, body) => request('POST', url, body),
  put: (url, body) => request('PUT', url, body),
  del: (url) => request('DELETE', url),
}

export async function downloadFile(url) {
  const res = await fetch(url, { headers: { Authorization: 'Bearer ' + getToken() } })
  if (!res.ok) throw new Error('导出失败')
  const blob = await res.blob()
  const cd = res.headers.get('Content-Disposition') || ''
  const m = cd.match(/filename\*=UTF-8''(.+)/)
  const filename = m ? decodeURIComponent(m[1]) : 'download.xlsx'
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = filename
  a.click()
  URL.revokeObjectURL(a.href)
}

// 带上传进度的文件上传（返回 { status, data }）
export function uploadFile(url, formData, onProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('POST', url)
    const token = getToken()
    if (token) xhr.setRequestHeader('Authorization', 'Bearer ' + token)
    if (onProgress) {
      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) onProgress(Math.round((e.loaded / e.total) * 100))
      }
    }
    xhr.onload = () => {
      let data = {}
      try { data = JSON.parse(xhr.responseText) } catch {}
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(data)
      } else {
        if (xhr.status === 401) { clearAuth(); window.location.href = '/login' }
        reject(new Error(data.msg || data.detail || '请求失败'))
      }
    }
    xhr.onerror = () => reject(new Error('网络错误'))
    xhr.send(formData)
  })
}
