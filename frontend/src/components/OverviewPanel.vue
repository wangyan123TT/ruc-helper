<script setup lang="ts">
import { computed } from 'vue'
import type { GradeItem, GpaSummary } from '../types'
import { groupBySemester, scoreClass } from '../utils/semester'

const props = defineProps<{ grades: GradeItem[]; gpa: GpaSummary | null }>()

// 学期分组（新学期在前）+ 走势，全部由 grades 直接聚合；
// 与「成绩」页共用 groupBySemester，口径一致（含正确的 学分绩点/学分 = GPA）
const semesters = computed(() => groupBySemester(props.grades))

const maxCredits = computed(() =>
  Math.max(1, ...semesters.value.map(s => s.credits)))

// ── 绩点走势（由旧到新）──
const trend = computed(() => {
  const pts = semesters.value.filter(s => s.gpa != null).slice().reverse()
  if (pts.length < 2) return null
  const gs = pts.map(s => s.gpa as number)
  const min = Math.min(...gs), max = Math.max(...gs)
  const span = max - min < 0.2 ? 0.2 : max - min
  const lo = min - span * 0.35, hi = max + span * 0.35
  const x0 = 20, x1 = 328, yTop = 18, yBot = 92, n = pts.length
  const X = (i: number) => n === 1 ? (x0 + x1) / 2 : x0 + (x1 - x0) * i / (n - 1)
  const Y = (v: number) => yBot - (yBot - yTop) * (v - lo) / (hi - lo)
  const co = pts.map((s, i) => ({
    x: +X(i).toFixed(1), y: +Y(s.gpa as number).toFixed(1),
    v: s.gpa as number, lab: s.short,
  }))
  const line = co.map((c, i) => (i ? 'L' : 'M') + c.x + ',' + c.y).join(' ')
  const area = line + ` L${co[co.length - 1].x},102 L${co[0].x},102 Z`
  return { line, area, co, last: co[co.length - 1] }
})

// 环比：最新学期 vs 上一学期 GPA
const gpaDelta = computed<number | null>(() => {
  const pts = semesters.value.filter(s => s.gpa != null)
  if (pts.length < 2) return null
  return Math.round(((pts[0].gpa as number) - (pts[1].gpa as number)) * 100) / 100
})

const vlabY = computed(() => trend.value ? Math.max(10, trend.value.last.y - 8) : 0)
</script>

<template>
  <div class="eyebrow">学业概览</div>

  <div class="overview" v-if="gpa">
    <!-- 绩点 hero -->
    <div class="card hero">
      <div class="lab">平均学分绩点 <span class="sub">GPA · 不含 P/F</span></div>
      <div class="big tnum">{{ gpa.gpa }}</div>
      <div class="delta" v-if="gpaDelta != null" :class="{ down: gpaDelta < 0 }">
        {{ gpaDelta >= 0 ? '▲' : '▼' }} 较上学期 {{ gpaDelta >= 0 ? '+' : '' }}{{ gpaDelta }}
      </div>
      <div class="ranks">
        <div class="rankchip" v-if="gpa.class_rank"><span>班级</span><b class="tnum">第{{ gpa.class_rank }}</b></div>
        <div class="rankchip" v-if="gpa.major_rank"><span>专业</span><b class="tnum">第{{ gpa.major_rank }}</b></div>
      </div>
    </div>

    <!-- 绩点走势 -->
    <div class="card trend">
      <div class="head">
        <span class="t">学期绩点走势</span>
        <span class="r" v-if="trend">近 {{ trend.co.length }} 学期</span>
      </div>
      <svg v-if="trend" viewBox="0 0 340 120" preserveAspectRatio="none" aria-label="学期绩点走势图">
        <defs>
          <linearGradient id="ov-grad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stop-color="var(--cinnabar)" stop-opacity=".16" />
            <stop offset="1" stop-color="var(--cinnabar)" stop-opacity="0" />
          </linearGradient>
        </defs>
        <line class="gline" x1="0" y1="20" x2="340" y2="20" />
        <line class="gline" x1="0" y1="54" x2="340" y2="54" />
        <line class="gline" x1="0" y1="88" x2="340" y2="88" />
        <path :d="trend.area" fill="url(#ov-grad)" />
        <path class="line" :d="trend.line" />
        <template v-for="(c, i) in trend.co" :key="i">
          <circle class="dot" :class="{ end: i === trend.co.length - 1 }"
                  :cx="c.x" :cy="c.y" :r="i === trend.co.length - 1 ? 4.5 : 3" />
          <text class="xlab" :x="c.x" y="114" text-anchor="middle">{{ c.lab }}</text>
        </template>
        <text class="vlab" :x="trend.last.x" :y="vlabY" text-anchor="end">{{ trend.last.v }}</text>
      </svg>
      <div v-else class="trend-empty">学期数不足，暂无走势</div>
    </div>

    <!-- 指标块 -->
    <div class="card stats">
      <div class="stat" v-if="gpa.weighted_avg">
        <div class="k">学分加权均分<small>weighted avg</small></div>
        <div class="v tnum">{{ gpa.weighted_avg }}</div>
        <div class="rk" v-if="gpa.weighted_rank">班级第 {{ gpa.weighted_rank }}</div>
      </div>
      <div class="stat">
        <div class="k">已修学分<small>累计通过</small></div>
        <div class="v tnum">{{ gpa.credits }}<u>分</u></div>
        <div class="rk">共 {{ gpa.courses }} 门</div>
      </div>
      <div class="stat" v-if="gpa.simple_avg">
        <div class="k">算术平均分<small>simple avg</small></div>
        <div class="v tnum">{{ gpa.simple_avg }}</div>
        <div class="rk" v-if="gpa.avg_rank">班级第 {{ gpa.avg_rank }}</div>
      </div>
    </div>
  </div>
  <div v-else class="muted">暂无绩点汇总数据</div>

  <!-- 成绩明细 · 按学期分带 -->
  <h2 class="sec">成绩明细 · 按学期</h2>
  <div v-if="!semesters.length" class="muted">暂无成绩记录</div>

  <div v-for="s in semesters" :key="s.id" class="sem">
    <div class="sem-head">
      <span class="name">{{ s.id }}</span>
      <span class="m"><b class="tnum">{{ s.credits }}</b>学分</span>
      <div class="cbar"><i :style="{ width: (s.credits / maxCredits * 100) + '%' }"></i></div>
      <span class="spacer"></span>
      <div class="gpa" v-if="s.gpa != null"><small>学期绩点</small><b class="tnum">{{ s.gpa }}</b></div>
      <div class="gpa avg" v-else-if="s.avg != null"><small>学期均分</small><b class="tnum">{{ s.avg }}</b></div>
    </div>
    <div v-for="c in s.courses" :key="c.id" class="crow">
      <div class="ci">
        <div class="cn">{{ c.course_name }}</div>
        <div class="ct" v-if="c.teacher || c.dept">{{ c.teacher }}<template v-if="c.teacher && c.dept"> · </template>{{ c.dept }}</div>
      </div>
      <span class="cat" v-if="c.category">{{ c.category }}</span><span v-else class="cat-none"></span>
      <span class="cr tnum">{{ c.credit }} <small>学分</small></span>
      <span class="sc tnum" :class="scoreClass(c.score)">{{ c.score }}</span>
    </div>
  </div>
</template>

<style scoped>
.eyebrow { font-size: 11px; font-weight: 600; letter-spacing: .16em; text-transform: uppercase; color: var(--ink-300); margin: 0 0 14px; }
.muted { font-size: 13px; color: var(--ink-300); padding: 20px 4px; }
.card { background: var(--white); border: 1px solid var(--ink-100); border-radius: var(--radius-lg); box-shadow: var(--shadow-sm); }

/* 概览指挥中心 */
.overview { display: grid; grid-template-columns: 1.1fr 1.35fr 1fr; gap: 15px; margin-bottom: 34px; }

.hero { padding: 22px 24px; display: flex; flex-direction: column; position: relative; overflow: hidden; }
.hero::after { content: '绩'; position: absolute; right: -12px; bottom: -30px; font-family: var(--serif); font-size: 150px; color: var(--ink-900); opacity: .03; line-height: 1; pointer-events: none; }
.hero .lab { font-size: 12.5px; color: var(--ink-400); font-weight: 500; }
.hero .lab .sub { color: var(--ink-300); font-weight: 400; }
.hero .big { font-family: var(--serif); font-size: 62px; font-weight: 600; line-height: 1; letter-spacing: -.01em; margin: 8px 0 2px; color: var(--ink-900); }
.hero .delta { font-size: 12.5px; color: var(--jade); font-weight: 600; }
.hero .delta.down { color: var(--cinnabar); }
.hero .ranks { display: flex; gap: 8px; margin-top: 16px; flex-wrap: wrap; }
.rankchip { background: var(--paper-dim); border: 1px solid var(--ink-100); border-radius: 9px; padding: 6px 12px; font-size: 12px; color: var(--ink-400); display: flex; flex-direction: column; gap: 1px; }
.rankchip b { font-family: var(--serif); font-size: 18px; font-weight: 600; color: var(--cinnabar); line-height: 1.05; }

.trend { padding: 18px 20px 14px; display: flex; flex-direction: column; }
.trend .head { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 4px; }
.trend .head .t { font-size: 13px; font-weight: 600; color: var(--ink-700); }
.trend .head .r { font-size: 11.5px; color: var(--ink-300); }
.trend svg { width: 100%; height: 120px; display: block; }
.trend .gline { stroke: var(--ink-100); stroke-width: 1; }
.trend .line { fill: none; stroke: var(--cinnabar); stroke-width: 2.2; stroke-linecap: round; stroke-linejoin: round; }
.trend .dot { fill: var(--white); stroke: var(--cinnabar); stroke-width: 2; }
.trend .dot.end { fill: var(--cinnabar); }
.trend .xlab { font-size: 9.5px; fill: var(--ink-300); }
.trend .vlab { font-size: 10px; fill: var(--cinnabar); font-weight: 700; font-family: var(--font-data); }
.trend-empty { flex: 1; display: flex; align-items: center; justify-content: center; height: 120px; font-size: 12.5px; color: var(--ink-300); }

.stats { padding: 6px 8px; display: grid; grid-template-rows: 1fr 1fr 1fr; }
.stat { display: flex; align-items: center; gap: 12px; padding: 0 14px; border-bottom: 1px solid var(--ink-50); }
.stat:last-child { border-bottom: none; }
.stat .k { font-size: 12px; color: var(--ink-400); flex: 1; }
.stat .k small { display: block; color: var(--ink-300); font-size: 10.5px; }
.stat .v { font-family: var(--serif); font-size: 25px; font-weight: 600; color: var(--ink-900); line-height: 1; }
.stat .v u { font-size: 12px; text-decoration: none; color: var(--ink-300); font-family: var(--font); margin-left: 1px; }
.stat .rk { font-size: 11px; color: var(--jade); font-weight: 600; white-space: nowrap; }

/* 栏目标题 */
h2.sec { font-family: var(--serif); font-size: 15px; font-weight: 600; color: var(--ink-700); margin: 0 0 15px; display: flex; align-items: center; gap: 9px; }
h2.sec::before { content: ''; width: 3px; height: 15px; background: var(--cinnabar); border-radius: 2px; }

/* 学期分带 */
.sem { margin-bottom: 15px; background: var(--white); border: 1px solid var(--ink-100); border-radius: var(--radius-lg); overflow: hidden; box-shadow: var(--shadow-sm); }
.sem-head { display: flex; align-items: center; gap: 15px; padding: 14px 22px; background: linear-gradient(var(--paper-dim), var(--white)); border-bottom: 1px solid var(--ink-50); }
.sem-head .name { font-family: var(--serif); font-size: 16.5px; font-weight: 600; color: var(--ink-900); }
.sem-head .m { font-size: 12px; color: var(--ink-400); white-space: nowrap; }
.sem-head .m b { color: var(--ink-800); font-family: var(--serif); font-size: 15px; margin-right: 2px; }
.sem-head .cbar { width: 150px; max-width: 22vw; height: 7px; border-radius: 4px; background: var(--ink-100); position: relative; overflow: hidden; }
.sem-head .cbar i { position: absolute; inset: 0 auto 0 0; background: var(--ink-700); border-radius: 4px; }
.sem-head .spacer { flex: 1; }
.sem-head .gpa { text-align: right; }
.sem-head .gpa small { display: block; font-size: 10.5px; color: var(--ink-300); }
.sem-head .gpa b { font-family: var(--serif); font-size: 20px; font-weight: 600; color: var(--jade); }
.sem-head .gpa.avg b { color: var(--ink-700); }

.crow { display: grid; grid-template-columns: 1fr auto 80px 52px; align-items: center; gap: 16px; padding: 11px 22px; border-bottom: 1px solid var(--ink-50); font-size: 13.5px; }
.crow:last-child { border-bottom: none; }
.crow:hover { background: var(--paper-dim); }
.crow .cn { font-weight: 500; color: var(--ink-900); }
.crow .ct { font-size: 11.5px; color: var(--ink-300); margin-top: 1px; }
.crow .cat { font-size: 10.5px; color: var(--ink-400); background: var(--ink-50); padding: 2px 8px; border-radius: 5px; white-space: nowrap; justify-self: start; }
.crow .cr { font-family: var(--font-data); font-size: 12.5px; color: var(--ink-500); text-align: right; }
.crow .cr small { color: var(--ink-300); }
.crow .sc { font-family: var(--serif); font-size: 19px; font-weight: 600; text-align: right; }
.sc.hi { color: var(--jade); }
.sc.mid { color: var(--ink-800); }
.sc.lo { color: var(--gold); }

@media (max-width: 1000px) { .overview { grid-template-columns: 1fr; } }
@media (max-width: 640px) {
  .crow { grid-template-columns: 1fr 52px; }
  .crow .cat-none, .crow .cat, .crow .cr { display: none; }
  .sem-head .cbar { display: none; }
}
</style>
