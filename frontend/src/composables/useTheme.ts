import { ref } from 'vue'

// 主题：纯开关控制（不跟随系统），存 localStorage，启动即应用到 <html data-theme>。
type Theme = 'light' | 'dark'
const KEY = 'ruc_theme'

const theme = ref<Theme>(localStorage.getItem(KEY) === 'dark' ? 'dark' : 'light')

function apply(t: Theme) {
  document.documentElement.setAttribute('data-theme', t)
}
apply(theme.value)   // 模块加载即应用，避免首帧闪一下浅色

export function useTheme() {
  function set(t: Theme) {
    theme.value = t
    localStorage.setItem(KEY, t)
    apply(t)
  }
  function toggle() { set(theme.value === 'dark' ? 'light' : 'dark') }
  return { theme, toggle, set }
}
