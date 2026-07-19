<script setup lang="ts">
import { useTheme } from './composables/useTheme'
useTheme()   // 启动即应用保存的主题（浅/深）
</script>

<template>
  <div class="app-shell">
    <router-view />
  </div>
</template>

<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;500;600;700&family=Noto+Serif+SC:wght@500;600;700&display=swap');

:root {
  --ink-900: #0f0f23;
  --ink-800: #1a1a35;
  --ink-700: #252542;
  --ink-600: #2d2d4a;
  --ink-500: #4a4a68;
  --ink-400: #6a6a88;
  --ink-300: #8b8ba8;
  --ink-200: #b8b8cc;
  --ink-100: #e4e4ee;
  --ink-50: #eeeef4;
  --paper: #faf9f6;
  --paper-dim: #f0eee9;
  --white: #ffffff;
  --cinnabar: #c41e3a;
  --cinnabar-light: #fde8ec;
  --jade: #1a7a5a;
  --jade-light: #e6f4ef;
  --gold: #b8860b;
  --gold-light: #fef7e6;
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 16px;
  --shadow-sm: 0 1px 3px rgba(15,15,35,0.06);
  --shadow-md: 0 4px 16px rgba(15,15,35,0.08);
  --shadow-lg: 0 12px 40px rgba(15,15,35,0.12);
  --font: 'Noto Sans SC', 'PingFang SC', 'Microsoft YaHei', sans-serif;
  /* 衬线 display：大号绩点/分数与栏目标题用，给数据以分量感（"大气"的关键） */
  --serif: 'Noto Serif SC', 'Songti SC', 'Source Han Serif SC', Georgia, 'Times New Roman', serif;
  /* 数据字面：学号/绩点/门数是数据不是正文，等宽+等距数字才对得齐 */
  --font-data: ui-monospace, 'SF Mono', 'JetBrains Mono', Menlo, Consolas,
               'Noto Sans SC', monospace;
  --transition: 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

/* 深色主题：墨阶反转（900→浅、100→深），宣纸底转墨底，传统色提亮以在深底上够醒目。
   由 useTheme 在 <html> 上打 data-theme="dark" 触发；纯开关控制，不跟随系统。 */
:root[data-theme="dark"] {
  --ink-900: #f3f2f8;
  --ink-800: #e4e3ee;
  --ink-700: #cfcede;
  --ink-600: #b4b3c9;
  --ink-500: #9a99b4;
  --ink-400: #83829e;
  --ink-300: #6c6b86;
  --ink-200: #45445c;
  --ink-100: #2a2a3a;
  --ink-50: #23222f;
  --paper: #0f0f17;
  --paper-dim: #191922;
  --white: #1b1b27;
  --cinnabar: #f0546e;
  --cinnabar-light: #38141f;
  --jade: #3fbf94;
  --jade-light: #123024;
  --gold: #d9a93a;
  --gold-light: #2c2411;
  --shadow-sm: 0 1px 3px rgba(0,0,0,0.45);
  --shadow-md: 0 4px 16px rgba(0,0,0,0.5);
  --shadow-lg: 0 12px 40px rgba(0,0,0,0.6);
}
:root[data-theme="dark"] body { background: var(--paper); }

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
  font-family: var(--font);
  background: var(--paper);
  color: var(--ink-900);
  -webkit-font-smoothing: antialiased;
  line-height: 1.6;
}

.app-shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

button {
  font-family: var(--font);
  cursor: pointer;
  border: none;
  outline: none;
  transition: all var(--transition);
}

input {
  font-family: var(--font);
  outline: none;
  transition: border-color var(--transition);
}
</style>
