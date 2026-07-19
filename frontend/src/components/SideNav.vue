<script setup lang="ts">
import { useTheme } from '../composables/useTheme'
// 配置驱动的通用左侧栏 —— 学生档案页与管理台共用一套骨架。
// 只负责「呈现导航 + 抛出点击事件」，不含任何业务逻辑。
interface NavItem { key: string; label: string; count?: number | null; badge?: boolean; icon: string }
interface NavGroup { label?: string; items: NavItem[] }
interface FootAction { key: string; label: string; icon: string; danger?: boolean }

defineProps<{
  glyph?: string                                    // 品牌小字块，如「选」「管」
  brandTitle: string
  brandSub?: string
  identity?: { seal: string; name: string; sub?: string } | null
  groups: NavGroup[]
  active: string
  footer: FootAction[]
}>()
defineEmits<{ (e: 'select', key: string): void; (e: 'foot', key: string): void }>()

const { theme, toggle } = useTheme()

// 图标全部表示为一组 path 的 d 串，渲染统一
const ICONS: Record<string, string[]> = {
  overview: ['M3 3v18h18', 'M7 14l4-4 3 3 5-6'],
  grades: ['M4 5h16M4 12h16M4 19h10'],
  preselect: ['M4 5a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2z', 'M4 9h16M9 2v4M15 2v4'],
  enrolled: ['M4 5a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2z', 'M4 9h16', 'M8.5 14l2.2 2.2L15 12.5'],
  grab: ['M13 2L4.5 13H11l-1 9 8.5-11H12l1-9z'],
  roster: ['M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2', 'M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8', 'M22 21v-2a4 4 0 0 0-3-3.87', 'M16 3.13a4 4 0 0 1 0 7.75'],
  data: ['M12 3c4.97 0 9 1.34 9 3s-4.03 3-9 3-9-1.34-9-3 4.03-3 9-3z', 'M3 6v6c0 1.66 4.03 3 9 3s9-1.34 9-3V6', 'M3 12v6c0 1.66 4.03 3 9 3s9-1.34 9-3v-6'],
  print: ['M6 9V2h12v7', 'M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2', 'M6 14h12v8H6z'],
  settings: ['M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z', 'M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z'],
  add: ['M12 5v14M5 12h14'],
  logout: ['M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4', 'M16 17l5-5-5-5', 'M21 12H9'],
  back: ['M19 12H5', 'M12 19l-7-7 7-7'],
  bell: ['M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9', 'M13.73 21a2 2 0 0 1-3.46 0'],
  moon: ['M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z'],
  sun: ['M12 17a5 5 0 1 0 0-10 5 5 0 0 0 0 10z', 'M12 1v2M12 21v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M1 12h2M21 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4'],
}
</script>

<template>
  <aside class="side">
    <div class="brand">
      <span class="g" v-if="glyph">{{ glyph }}</span>
      <span class="t">{{ brandTitle }}<small v-if="brandSub">{{ brandSub }}</small></span>
    </div>

    <div class="who" v-if="identity">
      <span class="seal" :class="{ long: identity.seal.length > 2 }">{{ identity.seal }}</span>
      <div class="wm">
        <div class="nm">{{ identity.name }}</div>
        <div class="mj" v-if="identity.sub">{{ identity.sub }}</div>
      </div>
    </div>

    <nav class="nav">
      <template v-for="(grp, gi) in groups" :key="gi">
        <div class="lbl" v-if="grp.label">{{ grp.label }}</div>
        <button v-for="it in grp.items" :key="it.key" class="ni" :class="{ on: active === it.key }"
                @click="$emit('select', it.key)">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path v-for="(d, di) in (ICONS[it.icon] || [])" :key="di" :d="d" />
          </svg>
          <span class="nl">{{ it.label }}</span>
          <span class="cnt" :class="{ hot: it.badge }" v-if="it.count != null">{{ it.count }}</span>
        </button>
      </template>
    </nav>

    <div class="foot">
      <button class="fb" @click="toggle">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
          <path v-for="(d, di) in (theme === 'dark' ? ICONS.sun : ICONS.moon)" :key="di" :d="d" />
        </svg>
        <span>{{ theme === 'dark' ? '浅色模式' : '深色模式' }}</span>
      </button>
      <button v-for="f in footer" :key="f.key" class="fb" :class="{ danger: f.danger }"
              @click="$emit('foot', f.key)">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
          <path v-for="(d, di) in (ICONS[f.icon] || [])" :key="di" :d="d" />
        </svg>
        <span>{{ f.label }}</span>
      </button>
    </div>
  </aside>
</template>

<style scoped>
.side {
  --side-bg: #14142a; --side-fg: #edecf4; --side-dim: #8888a6;
  --side-line: rgba(255, 255, 255, .08); --side-hover: rgba(255, 255, 255, .05); --side-active: rgba(255, 255, 255, .09);
  width: 238px; flex-shrink: 0; background: var(--side-bg); color: var(--side-fg);
  position: sticky; top: 0; height: 100vh; align-self: flex-start;
  display: flex; flex-direction: column; padding: 20px 14px; overflow-y: auto;
}
/* 深色下侧栏作抬起面板：略提亮 + 右侧发丝线，与墨底主区分层 */
:root[data-theme="dark"] .side { --side-bg: #171721; border-right: 1px solid rgba(255,255,255,.05); }
.brand { display: flex; align-items: center; gap: 10px; padding: 6px 10px 18px; }
.brand .g { width: 30px; height: 30px; border-radius: 7px; background: var(--cinnabar); color: #fff;
  display: flex; align-items: center; justify-content: center; font-family: var(--serif); font-weight: 600; font-size: 17px; flex-shrink: 0; }
.brand .t { font-size: 14.5px; font-weight: 600; letter-spacing: .02em; line-height: 1.2; }
.brand .t small { display: block; font-size: 10.5px; color: var(--side-dim); font-weight: 400; letter-spacing: .08em; }

.who { display: flex; align-items: center; gap: 11px; padding: 12px 10px; margin-bottom: 8px;
  border-top: 1px solid var(--side-line); border-bottom: 1px solid var(--side-line); }
.who .seal { width: 38px; height: 38px; border-radius: 5px; background: var(--cinnabar); color: #fff;
  display: flex; align-items: center; justify-content: center; font-family: var(--serif); font-size: 15px; font-weight: 600;
  letter-spacing: .04em; text-indent: .04em; flex-shrink: 0; box-shadow: inset 0 0 0 1.2px rgba(255, 255, 255, .3); }
.who .seal.long { font-size: 12.5px; letter-spacing: 0; text-indent: 0; }
.who .wm { min-width: 0; }
.who .nm { font-size: 14px; font-weight: 600; line-height: 1.25; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.who .mj { font-size: 11px; color: var(--side-dim); margin-top: 1px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

.nav { display: flex; flex-direction: column; gap: 2px; margin-top: 6px; }
.nav .lbl { font-size: 10px; font-weight: 600; letter-spacing: .16em; color: var(--side-dim); padding: 12px 10px 6px; text-transform: uppercase; }
.ni { display: flex; align-items: center; gap: 11px; padding: 9px 11px; border-radius: 9px; color: var(--side-dim);
  font-size: 13.5px; font-family: var(--font); background: none; border: none; cursor: pointer; position: relative; text-align: left; transition: background .16s, color .16s; }
.ni svg { width: 17px; height: 17px; flex-shrink: 0; }
.ni .nl { flex: 1; }
.ni .cnt { font-size: 11px; font-variant-numeric: tabular-nums; background: rgba(255, 255, 255, .08); color: var(--side-dim); padding: 0 7px; border-radius: 9px; line-height: 18px; }
.ni .cnt.hot { background: var(--cinnabar); color: #fff; }
.ni:hover { background: var(--side-hover); color: var(--side-fg); }
.ni.on { background: var(--side-active); color: #fff; }
.ni.on::before { content: ''; position: absolute; left: -14px; top: 50%; transform: translateY(-50%); width: 3px; height: 20px; background: var(--cinnabar); border-radius: 0 3px 3px 0; }
.ni.on .cnt { background: var(--cinnabar); color: #fff; }

.foot { margin-top: auto; display: flex; flex-direction: column; gap: 2px; padding-top: 12px; border-top: 1px solid var(--side-line); }
.fb { display: flex; align-items: center; gap: 10px; padding: 9px 11px; border-radius: 9px; color: var(--side-dim);
  font-size: 13px; font-family: var(--font); background: none; border: none; cursor: pointer; text-align: left; transition: background .16s, color .16s; }
.fb svg { width: 16px; height: 16px; flex-shrink: 0; }
.fb:hover { background: var(--side-hover); color: var(--side-fg); }
.fb.danger:hover { background: rgba(196, 30, 58, .16); color: #ff8098; }

.ni:focus-visible, .fb:focus-visible { outline: 2px solid var(--cinnabar); outline-offset: 1px; }
@media (prefers-reduced-motion: reduce) { .ni, .fb { transition: none; } }

/* 窄屏：侧栏收成顶部横条 */
@media (max-width: 820px) {
  .side { width: auto; height: auto; position: sticky; top: 0; z-index: 40; flex-direction: row; flex-wrap: wrap;
    align-items: center; padding: 8px 12px; gap: 6px; }
  .brand { padding: 4px 6px; }
  .who { border: none; margin: 0; padding: 4px 8px; }
  .who .mj { display: none; }
  .nav { flex: 1 1 100%; flex-direction: row; overflow-x: auto; gap: 2px; margin: 0; }
  .nav .lbl { display: none; }
  .ni.on::before { display: none; }
  .foot { margin: 0; flex-direction: row; border: none; padding: 0; }
  .fb span { display: none; }
}
@media print { .side { display: none; } }
</style>
