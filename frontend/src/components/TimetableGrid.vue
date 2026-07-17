<script setup lang="ts">
import { computed } from 'vue'
import type { TimetableData, TimetableCourse, TimetableClass, TimetableSlot } from '../types'

const props = defineProps<{ data: TimetableData }>()

const WEEK = '一二三四五六日'
const DAYS = [1, 2, 3, 4, 5]

type Block = {
  course: TimetableCourse
  cls: TimetableClass
  slot: TimetableSlot
  span: number
  ghost: boolean
}

/** 课表格子：按第一志愿排布，时间不同的备选班额外画一个虚线"备选落点" */
const layout = computed(() => {
  const starts = new Map<string, Block>()
  const covered = new Set<string>()

  const place = (course: TimetableCourse, cls: TimetableClass, ghost: boolean) => {
    for (const slot of cls.slots) {
      const ps = slot.periods
      if (!ps.length) continue
      const key = `${slot.day}-${ps[0]}`
      if (starts.has(key)) continue          // 已被占（幽灵块不抢第一志愿的位）
      starts.set(key, { course, cls, slot, span: ps.length, ghost })
      for (let i = 1; i < ps.length; i++) covered.add(`${slot.day}-${ps[i]}`)
    }
  }

  for (const c of props.data.courses) place(c, c.primary, false)
  for (const c of props.data.courses) {
    for (const a of c.alts) if (a.is_ghost) place(c, a, true)
  }

  let maxP = 1
  for (const k of [...starts.keys(), ...covered]) {
    const p = Number(k.split('-')[1])
    if (p > maxP) maxP = p
  }
  for (const b of starts.values()) {
    const last = b.slot.periods[b.slot.periods.length - 1]
    if (last > maxP) maxP = last
  }

  // 节次 -> 大节（取每大节第一小节显示起始时间）
  const pStart = new Map<number, string>()
  for (const blk of props.data.context.periods) {
    if (blk.subs.length) pStart.set(blk.subs[0], blk.start)
  }

  const rows = []
  for (let p = 1; p <= maxP; p++) {
    const cells: ({ kind: 'empty' } | ({ kind: 'block' } & Block))[] = []
    for (const d of DAYS) {
      const key = `${d}-${p}`
      if (covered.has(key)) continue          // 被上方 rowspan 覆盖，不渲染
      const b = starts.get(key)
      cells.push(b ? { kind: 'block', ...b } : { kind: 'empty' })
    }
    rows.push({ period: p, time: pStart.get(p) || '', cells })
  }
  return rows
})

const conflictSet = computed(() =>
  new Set(props.data.conflicts.map(c => `${c.day}-${c.period}`)))

const ghostNames = computed(() =>
  [...new Set(props.data.courses.filter(c => !c.same_time).map(c => c.name))])

const legend = computed(() => {
  const seen = new Map<string, string>()
  for (const c of props.data.courses) if (!seen.has(c.category)) seen.set(c.category, c.cat_class)
  return [...seen].map(([name, cls]) => ({ name, cls }))
})

const sortedCourses = computed(() =>
  [...props.data.courses].sort((a, b) => b.credit - a.credit || a.name.localeCompare(b.name)))

function slotText(cls: TimetableClass) {
  return cls.slots.map(s =>
    `周${WEEK[s.day - 1]}${Math.min(...s.periods)}–${Math.max(...s.periods)}节`).join(' / ')
}
function sameSlots(a: TimetableClass, b: TimetableClass) {
  const k = (c: TimetableClass) => c.slots.map(s => `${s.day}:${s.periods.join(',')}`).sort().join('|')
  return k(a) === k(b)
}
</script>

<template>
  <div class="tt">
    <!-- 概览 -->
    <div class="tt-stats">
      <div class="tt-st"><b>{{ data.n_courses }}</b><span>门课</span></div>
      <div class="tt-st"><b>{{ data.n_prefs }}</b><span>个志愿</span></div>
      <div class="tt-st"><b>{{ data.total_credit }}</b><span>学分</span></div>
      <div class="tt-st"><b class="sm">{{ data.context.mode }}制</b><span>{{ data.context.ctrl }}</span></div>
      <div class="tt-st"><b class="sm">{{ data.context.xkjssj }}</b><span>选课截止</span></div>
    </div>

    <!-- 冲突警示 -->
    <div v-if="data.conflicts.length" class="tt-alert">
      <strong>第一志愿有 {{ data.conflicts.length }} 处时间冲突：</strong>
      <span v-for="(c, i) in data.conflicts" :key="i">
        周{{ WEEK[c.day - 1] }}第{{ c.period }}节 {{ c.names.join(' × ') }}<template v-if="i < data.conflicts.length - 1">；</template>
      </span>
    </div>

    <!-- 图例 -->
    <div class="tt-legend">
      <span class="tt-lb">课程类别</span>
      <span v-for="l in legend" :key="l.name" class="tt-lg" :class="l.cls">{{ l.name }}</span>
    </div>

    <!-- 课表 -->
    <div class="tt-scroll">
      <table class="tt-table">
        <caption>按<strong>第一志愿</strong>排布 · 虚线块 = 备选志愿的另一个落点</caption>
        <thead>
          <tr>
            <th class="tt-ph">节</th>
            <th v-for="d in DAYS" :key="d">周{{ WEEK[d - 1] }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in layout" :key="row.period">
            <th class="tt-ph" scope="row">
              <span class="tt-pn">{{ row.period }}</span>
              <span v-if="row.time" class="tt-pt">{{ row.time }}</span>
            </th>
            <template v-for="(cell, i) in row.cells" :key="i">
              <td v-if="cell.kind === 'empty'" class="tt-empty"></td>
              <td
                v-else
                class="tt-slot"
                :class="[cell.course.cat_class, { ghost: cell.ghost,
                         clash: conflictSet.has(`${cell.slot.day}-${row.period}`) }]"
                :rowspan="cell.span"
              >
                <span v-if="cell.ghost" class="tt-gh">志愿{{ cell.cls.pref }} · 备选落点</span>
                <span class="tt-cn">{{ cell.course.name }}</span>
                <span class="tt-meta">{{ cell.slot.room }}</span>
                <span class="tt-meta">{{ cell.cls.teacher.slice(0, 14) }}</span>
                <span class="tt-meta">{{ cell.slot.start }}–{{ cell.slot.end }} · 周{{ cell.slot.weeks }}</span>
                <span v-if="!cell.ghost && cell.course.n_pref > 1" class="tt-badges">
                  <span class="tt-pref">志愿{{ cell.cls.pref }}</span>
                  <span class="tt-vs">/{{ cell.course.n_pref }}班竞争</span>
                </span>
              </td>
            </template>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 志愿明细 -->
    <h3 class="tt-h">志愿明细</h3>
    <p class="tt-sub">同一门课报多个平行班 = 多个志愿，筛选后每门只会中一个</p>
    <div class="tt-cards">
      <article v-for="c in sortedCourses" :key="c.name" class="tt-card" :class="c.cat_class">
        <header>
          <h4>{{ c.name }}</h4>
          <span class="tt-cr">{{ c.credit }} 学分</span>
        </header>
        <p class="tt-ct">{{ c.category }} · {{ c.dept }}</p>
        <ol>
          <li v-for="cls in [c.primary, ...c.alts]" :key="cls.pref"
              :class="{ diff: !sameSlots(cls, c.primary) }">
            <b>志愿{{ cls.pref }}</b>
            <span class="tt-cls">{{ cls.class_name }}</span>
            <span class="tt-tc">{{ cls.teacher.slice(0, 20) }}</span>
            <span class="tt-rm">{{ cls.slots[0]?.room || '—' }}</span>
            <em v-if="!sameSlots(cls, c.primary)">时间不同 · {{ slotText(cls) }}</em>
          </li>
        </ol>
      </article>
    </div>

    <!-- 说明 -->
    <div class="tt-note">
      <strong>这是志愿，不是结果。</strong>
      全部 {{ data.n_prefs }} 个志愿状态均为「待筛选」——志愿制下人人可报，超额由系统筛选。
      课表按第一志愿排布：平行班上课时间通常相同，所以筛上哪个班一般不改变格子位置。
      <template v-if="ghostNames.length">
        <strong>其中 {{ ghostNames.join('、') }}</strong> 的各志愿上课时间完全不同，图中已用虚线块标出备选落点。
      </template>
      <template v-else>所有课程的平行班时间都一致，筛选结果不会改变课表布局。</template>
      <div class="tt-stamp">
        数据抓取于 {{ data.context.now }} · 选课窗口 {{ data.context.xkkssj }} – {{ data.context.xkjssj }}
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 课程类别配色 —— 沿用 App.vue 的中国传统色系统 */
.pol  { --c: var(--cinnabar); }      /* 思想政治理论课 — 朱砂 */
.core { --c: #2d5f8a; }              /* 专业核心课 — 靛青 */
.elec { --c: var(--jade); }          /* 专业选修课 — 玉 */
.gen  { --c: var(--gold); }          /* 通识核心课 — 金 */
.lang { --c: #6b4c7a; }              /* 公共外语 — 紫檀 */
.pe   { --c: #4a7c3f; }              /* 公共体育 — 竹青 */
.misc { --c: var(--ink-600); }

.tt { display: flex; flex-direction: column; gap: 16px; }

/* 概览条 */
.tt-stats {
  display: flex; flex-wrap: wrap;
  background: var(--white); border: 1px solid var(--ink-100);
  border-radius: var(--radius-md); overflow: hidden; box-shadow: var(--shadow-sm);
}
.tt-st {
  flex: 1 1 120px; padding: 12px 16px;
  border-right: 1px solid var(--ink-100);
  display: flex; flex-direction: column; gap: 1px;
}
.tt-st:last-child { border-right: 0; }
.tt-st b { font-size: 21px; font-weight: 600; color: var(--ink-900); font-variant-numeric: tabular-nums; }
.tt-st b.sm { font-size: 14px; font-weight: 500; }
.tt-st span { font-size: 12px; color: var(--ink-300); }

/* 冲突 */
.tt-alert {
  padding: 11px 16px; background: var(--cinnabar-light);
  border: 1px solid var(--cinnabar); border-radius: var(--radius-sm);
  font-size: 13px; color: var(--ink-800);
}
.tt-alert strong { color: var(--cinnabar); }

/* 图例 */
.tt-legend { display: flex; gap: 7px; flex-wrap: wrap; align-items: center; }
.tt-lb { font-size: 12px; color: var(--ink-300); }
.tt-lg {
  font-size: 12px; padding: 3px 10px; border-radius: 20px; font-weight: 500;
  color: var(--c); border: 1px solid color-mix(in srgb, var(--c) 30%, transparent);
  background: color-mix(in srgb, var(--c) 8%, var(--white));
}

/* 表格 */
.tt-scroll {
  overflow-x: auto; background: var(--white);
  border: 1px solid var(--ink-100); border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
}
.tt-table { width: 100%; min-width: 680px; border-collapse: collapse; table-layout: fixed; }
.tt-table caption {
  caption-side: top; text-align: left; padding: 12px 16px 10px;
  font-size: 12.5px; color: var(--ink-300); border-bottom: 1px solid var(--ink-100);
}
.tt-table thead th {
  background: var(--paper-dim); padding: 9px; font-size: 13px; font-weight: 500;
  color: var(--ink-600); border-bottom: 1px solid var(--ink-100);
  border-right: 1px solid var(--ink-100);
}
.tt-table thead th:last-child { border-right: 0; }
.tt-table td, .tt-table tbody th {
  border-right: 1px solid var(--ink-100); border-bottom: 1px solid var(--ink-100);
  vertical-align: top;
}
.tt-table td:last-child { border-right: 0; }
.tt-ph { width: 48px; background: var(--paper-dim); text-align: center; padding: 5px 2px; }
.tt-pn { display: block; font-size: 12px; color: var(--ink-300); font-weight: 500;
  font-variant-numeric: tabular-nums; }
.tt-pt { display: block; font-size: 10px; color: var(--ink-200); }
.tt-empty { height: 34px; }

.tt-slot {
  padding: 7px 9px;
  background: color-mix(in srgb, var(--c) 7%, var(--white));
  border-left: 3px solid var(--c);
}
.tt-cn { display: block; font-weight: 600; color: var(--c); font-size: 13px;
  line-height: 1.35; margin-bottom: 3px; }
.tt-meta { display: block; font-size: 11px; color: var(--ink-300); line-height: 1.45; }
.tt-badges { display: flex; gap: 4px; align-items: center; margin-top: 4px; flex-wrap: wrap; }
.tt-pref { font-size: 10px; font-weight: 600; background: var(--c); color: #fff;
  padding: 1px 5px; border-radius: 3px; }
.tt-vs { font-size: 10px; color: var(--ink-300); }
.tt-slot.ghost {
  background: repeating-linear-gradient(135deg, transparent 0 6px,
    color-mix(in srgb, var(--c) 7%, transparent) 6px 12px);
  border-left: 3px dashed var(--c);
}
.tt-slot.ghost .tt-cn { font-weight: 500; }
.tt-gh { display: block; font-size: 10px; font-weight: 600; color: var(--c);
  margin-bottom: 2px; opacity: 0.85; }
.tt-slot.clash { outline: 2px solid var(--cinnabar); outline-offset: -2px; }

/* 明细卡片 */
.tt-h { font-size: 15px; font-weight: 600; margin-top: 6px; }
.tt-sub { font-size: 12.5px; color: var(--ink-300); margin-top: -12px; }
.tt-cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(272px, 1fr)); gap: 10px; }
.tt-card {
  background: var(--white); border: 1px solid var(--ink-100);
  border-left: 3px solid var(--c); border-radius: var(--radius-sm);
  padding: 11px 13px; box-shadow: var(--shadow-sm);
}
.tt-card header { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; }
.tt-card h4 { font-size: 13.5px; font-weight: 600; color: var(--c); }
.tt-cr { font-size: 11px; color: var(--ink-300); flex-shrink: 0; }
.tt-ct { font-size: 11px; color: var(--ink-300); margin: 2px 0 7px; }
.tt-card ol { margin: 0; padding: 0; list-style: none; display: flex;
  flex-direction: column; gap: 3px; }
.tt-card li { display: flex; gap: 6px; align-items: baseline; font-size: 11.5px;
  color: var(--ink-600); flex-wrap: wrap; }
.tt-card li b {
  font-size: 10px; font-weight: 600; color: var(--c); flex-shrink: 0;
  background: color-mix(in srgb, var(--c) 10%, transparent);
  padding: 1px 4px; border-radius: 3px;
}
.tt-cls { flex: 1; min-width: 0; }
.tt-tc, .tt-rm { color: var(--ink-300); font-size: 10.5px; }
.tt-card li.diff em {
  flex-basis: 100%; font-style: normal; font-size: 10.5px;
  color: var(--cinnabar); font-weight: 500;
}
.tt-card li.diff em::before { content: '↳ '; }

/* 说明 */
.tt-note {
  background: var(--gold-light); border: 1px solid var(--gold);
  border-radius: var(--radius-sm); padding: 12px 15px;
  font-size: 12.5px; color: var(--ink-700); line-height: 1.7;
}
.tt-note strong { color: var(--ink-900); }
.tt-stamp { margin-top: 6px; font-size: 11px; color: var(--ink-300); }
</style>
