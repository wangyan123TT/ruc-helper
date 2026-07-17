<script setup lang="ts">
</script>

<template>
  <div class="app-shell">
    <router-view />
  </div>
</template>

<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;500;600;700&display=swap');

:root {
  --ink-900: #0f0f23;
  --ink-800: #1a1a35;
  --ink-700: #252542;
  --ink-600: #2d2d4a;
  --ink-300: #8b8ba8;
  --ink-200: #b8b8cc;
  --ink-100: #e4e4ee;
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
  /* 数据字面：学号/绩点/门数是数据不是正文，等宽+等距数字才对得齐 */
  --font-data: ui-monospace, 'SF Mono', 'JetBrains Mono', Menlo, Consolas,
               'Noto Sans SC', monospace;
  --transition: 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

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
