import { getUser } from './api'

// 按钮权限：按「菜单:动作」编码判断（如 order:delete / customer:edit）
export function useButtonPerm() {
  const user = getUser() || {}
  const perms = user.permissions || []
  const isAdmin = user.role_code === 'admin' || perms.includes('*')
  return { isAdmin, can: code => isAdmin || perms.includes(code) }
}
