<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import {
  getGrabCategories, getGrabPool, getGrabTargets,
  addGrabTarget, removeGrabTarget,
} from '../api'
import type { GrabCategoriesResp, GrabCategory, GrabSubCategory, GrabPoolCourse, GrabTarget, GrabStatus } from '../types'

const props = defineProps<{ studentId: string }>()

const WEEK = '一二三四五六日'

const meta = ref<GrabCategoriesResp | null>(null)
const activeCat = ref<string>('')
const activeSubKey = ref<string>('')   // 当前子类别标识（params 的 JSON）
const pool = ref<GrabPoolCourse[]>([])
const targets = ref<GrabTarget[]>([])
const loading = ref(true)
const poolLoading = ref(false)
const err = ref('')
let timer: number | undefined

// 状态 -> 显示文案 + 语义色（用现有传统色变量）
const STATUS_META: Record<GrabStatus, { label: string; cls: string }> = {
  waiting: { label: '等待', cls: 's-wait' },
  grabbing: { label: '盯着', cls: 's-watch' },
  ready: { label: '有名额', cls: 's-ready' },
  success: { label: '抢到', cls: 's-ok' },
  conflict: { label: '冲突已停', cls: 's-conflict' },
  failed: { label: '失败', cls: 's-fail' },
}

const activeCount = computed(() =>
  targets.value.filter(t => ['waiting', 'grabbing', 'ready'].includes(t.status)).length)

async function loadMeta() {
  loading.value = true
  err.value = ''
  try {
    meta.value = await getGrabCategories(props.studentId)
    if (meta.value.categories.length && !activeCat.value) {
      await loadPool(meta.value.categories[0])
    }
    await refreshTargets()
  } catch (e: any) {
    err.value = e.response?.data?.detail || e.message || '加载失败'
  } finally {
    loading.value = false
  }
}

const currentCat = computed(() =>
  meta.value?.categories.find(c => c.kclbcode === activeCat.value) || null)

const subKey = (s: GrabSubCategory) => JSON.stringify(s.params)

// 子类别按 group 分组（跨学科有 27 学院 + 6 荣誉项目，需分组显示）
const subGroups = computed(() => {
  const cat = currentCat.value
  if (!cat || !cat.subs.length) return [] as { group: string; subs: GrabSubCategory[] }[]
  const map = new Map<string, GrabSubCategory[]>()
  for (const s of cat.subs) {
    if (!map.has(s.group)) map.set(s.group, [])
    map.get(s.group)!.push(s)
  }
  return [...map].map(([group, subs]) => ({ group, subs }))
})

async function loadPool(cat: GrabCategory, sub?: GrabSubCategory) {
  // 有子类别的类别永远只按子类别显示（默认第一个），绝不把整个类别的课全铺出来；
  // 跨学科专业选修必须选到具体子类别（学院/荣誉项目）才拉得到课。
  if (cat.subs.length && !sub) sub = cat.subs[0]
  activeCat.value = cat.kclbcode
  activeSubKey.value = sub ? subKey(sub) : ''
  poolLoading.value = true
  try {
    const r = await getGrabPool(props.studentId, cat.kclbcode, sub?.params || {})
    pool.value = r.courses
  } catch (e: any) {
    err.value = e.response?.data?.detail || e.message || '加载课程池失败'
  } finally {
    poolLoading.value = false
  }
}

async function refreshTargets() {
  try {
    targets.value = await getGrabTargets(props.studentId)
  } catch { /* 静默：轮询失败不打断 */ }
}

const targetKeys = computed(() => new Set(targets.value.map(t => t.course_key)))

// 当前选中子类别的 params（用于重拉池子时定位，如跨学科的 honerItemId/kkdwid）
const currentSubParams = computed(() => {
  const sub = currentCat.value?.subs.find(s => subKey(s) === activeSubKey.value)
  return sub?.params || {}
})

async function add(c: GrabPoolCourse) {
  if (c.conflict.length) return
  try {
    await addGrabTarget(props.studentId, {
      kclbcode: c.kclbcode, course_key: c.course_key,
      course_name: c.name, class_name: c.class_name, teacher: c.teacher,
      credit: c.credit, priority: targets.value.length + 1,
      pool_params: currentSubParams.value,
    })
    await refreshTargets()
  } catch (e: any) {
    alert(e.response?.data?.detail || '加入失败')
  }
}

async function remove(t: GrabTarget) {
  try {
    await removeGrabTarget(props.studentId, t.id)
    await refreshTargets()
  } catch (e: any) {
    alert(e.response?.data?.detail || '移除失败')
  }
}

function slotText(c: { slots: GrabPoolCourse['slots'] }) {
  return c.slots.map(s =>
    `周${WEEK[s.day - 1]}${Math.min(...s.periods)}–${Math.max(...s.periods)}节`).join(' / ')
}

onMounted(() => {
  loadMeta()
  timer = window.setInterval(refreshTargets, 3000)   // 每3秒刷新目标状态
})
onUnmounted(() => { if (timer) clearInterval(timer) })
</script>

<template>
  <div class="grab">
    <div v-if="loading" class="g-state"><div class="spinner"></div>
      <p class="hint">正在登录教务、读取选课信息…</p></div>

    <div v-else-if="err" class="g-banner err">{{ err }}</div>

    <template v-else-if="meta">
      <!-- 模式横幅：现在能不能真抢，一眼看清 -->
      <div class="g-mode" :class="meta.is_time_priority ? 'live' : 'wait'">
        <div>
          <b>{{ meta.hd_name }}</b>
          <span class="mode-tag">{{ meta.mode }}制</span>
        </div>
        <p v-if="meta.is_time_priority">
          时间优先窗口 — 抢课器每 2 秒争抢，抢到即停。
        </p>
        <p v-else>
          当前是<b>志愿筛选制</b>，不分先后、按规则筛选，抢课手速无效。
          抢课器会<b>持续盯着</b>，等 7/27 起的「时间优先」窗口自动进入争抢。
        </p>
        <p class="win">选课窗口 {{ meta.xkkssj }} – {{ meta.xkjssj }} ｜ 服务器 {{ meta.now }}</p>
      </div>

      <!-- 提交隔离提示 -->
      <div class="g-note">
        本页处于<b>监控阶段</b>：只盯余额、判冲突、排队。真正的提交尚未启用，
        任何操作都<b>不会改动选课状态</b>。冲突的课会自动停下并标出。
      </div>

      <div class="g-cols">
        <!-- 左：课程池 -->
        <section class="g-pool">
          <header class="g-head">课程池</header>
          <div class="cat-bar">
            <button v-for="c in meta.categories" :key="c.kclbcode"
                    class="cat" :class="{ on: activeCat === c.kclbcode }"
                    @click="loadPool(c)">
              {{ c.name }}<span class="cat-n">{{ c.count }}</span>
              <span v-if="c.subs.length" class="cat-sub-dot" title="含子类别">›</span>
            </button>
          </div>

          <!-- 子类别：通识按 xxklb；跨学科按「双选认证·学院」和「荣誉选课·项目」分组 -->
          <div v-if="subGroups.length" class="sub-wrap">
            <div v-for="g in subGroups" :key="g.group" class="sub-group">
              <span class="sub-glabel">{{ g.group }}</span>
              <div class="sub-bar">
                <button v-for="sc in g.subs" :key="subKey(sc)"
                        class="sub" :class="{ on: activeSubKey === subKey(sc) }"
                        @click="loadPool(currentCat!, sc)">
                  {{ sc.name }}
                </button>
              </div>
            </div>
          </div>

          <div v-if="poolLoading" class="g-state sm"><div class="spinner"></div></div>
          <ul v-else class="pool-list">
            <li v-for="c in pool" :key="c.course_key" class="pc"
                :class="{ conflicted: c.conflict.length, added: targetKeys.has(c.course_key) }">
              <div class="pc-main">
                <div class="pc-name">{{ c.name }}
                  <span class="pc-cls">{{ c.class_name }}</span></div>
                <div class="pc-meta">
                  {{ c.teacher.slice(0, 12) }} · {{ c.credit }}学分 · {{ slotText(c) }}
                </div>
                <div class="pc-num">
                  容量 {{ c.cap ?? '?' }} · 已选 {{ c.enrolled ?? '?' }}
                  <span v-if="meta.is_time_priority && c.surplus !== null"
                        :class="c.surplus > 0 ? 'surp-ok' : 'surp-no'">
                    · 余 {{ c.surplus }}
                  </span>
                </div>
              </div>
              <div class="pc-act">
                <span v-if="c.conflict.length" class="pc-conflict"
                      :title="c.conflict.map(x => `周${WEEK[x.day-1]}第${x.period}节`).join('、')">
                  ⚠ 与已选课冲突
                </span>
                <span v-else-if="targetKeys.has(c.course_key)" class="pc-done">已加入</span>
                <button v-else class="pc-add" @click="add(c)">＋ 加入</button>
              </div>
            </li>
            <li v-if="!pool.length" class="pc-empty">该类别下暂无课程</li>
          </ul>
        </section>

        <!-- 右：我的目标 + 实时状态 -->
        <section class="g-targets">
          <header class="g-head">
            抢课目标
            <span class="t-count" v-if="targets.length">
              {{ targets.length }} 门 · {{ activeCount }} 争取中
            </span>
          </header>

          <ul v-if="targets.length" class="t-list">
            <li v-for="t in targets" :key="t.id" class="tc"
                :class="STATUS_META[t.status]?.cls">
              <div class="tc-top">
                <span class="tc-badge">{{ STATUS_META[t.status]?.label || t.status }}</span>
                <span class="tc-name">{{ t.course_name }}</span>
                <button class="tc-x" @click="remove(t)" title="移除">✕</button>
              </div>
              <div class="tc-sub">{{ t.class_name }} · {{ t.teacher.slice(0, 12) }} · 优先级{{ t.priority }}</div>
              <div class="tc-msg">{{ t.message }}</div>
            </li>
          </ul>
          <div v-else class="t-empty">
            还没有目标。左边课程池里点「＋ 加入」把想抢的课加进来，<br>
            抢课器会自动盯着，一有名额就争抢。
          </div>
        </section>
      </div>
    </template>
  </div>
</template>

<style scoped>
.grab { display: flex; flex-direction: column; gap: 14px; }

.g-state { text-align: center; padding: 40px; }
.g-state.sm { padding: 24px; }
.g-state .hint { margin-top: 10px; font-size: 13px; color: var(--ink-300); }
.spinner { width: 28px; height: 28px; border: 3px solid var(--ink-100);
  border-top-color: var(--ink-600); border-radius: 50%; margin: 0 auto;
  animation: spin .8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.g-banner.err { padding: 12px 16px; background: var(--cinnabar-light);
  border: 1px solid var(--cinnabar); border-radius: var(--radius-sm);
  font-size: 14px; color: var(--ink-800); }

/* 模式横幅 */
.g-mode { padding: 14px 16px; border-radius: var(--radius-md); border: 1px solid;
  font-size: 13px; line-height: 1.6; }
.g-mode.live { background: var(--jade-light); border-color: var(--jade); }
.g-mode.wait { background: var(--gold-light); border-color: var(--gold); }
.g-mode b { color: var(--ink-900); }
.g-mode p { margin: 6px 0 0; color: var(--ink-700); }
.g-mode .win { font-size: 11px; color: var(--ink-300); margin-top: 8px; }
.mode-tag { margin-left: 8px; font-size: 11px; padding: 2px 8px; border-radius: 12px;
  background: var(--white); color: var(--ink-600); }

.g-note { padding: 10px 14px; background: var(--paper-dim);
  border-radius: var(--radius-sm); font-size: 12px; color: var(--ink-600); line-height: 1.6; }
.g-note b { color: var(--ink-800); }

/* 两栏 */
.g-cols { display: grid; grid-template-columns: 1fr 380px; gap: 14px; align-items: start; }
@media (max-width: 900px) { .g-cols { grid-template-columns: 1fr; } }

.g-head { font-size: 14px; font-weight: 600; color: var(--ink-800);
  padding-bottom: 8px; border-bottom: 1px solid var(--ink-100); margin-bottom: 10px;
  display: flex; justify-content: space-between; align-items: baseline; }

/* 课程池 */
.g-pool, .g-targets { background: var(--white); border: 1px solid var(--ink-100);
  border-radius: var(--radius-md); padding: 14px; box-shadow: var(--shadow-sm); }
.cat-bar { display: flex; flex-wrap: wrap; gap: 5px; margin-bottom: 12px; }
.cat { font-size: 12px; padding: 4px 11px; border-radius: 14px; background: var(--paper-dim);
  color: var(--ink-600); display: flex; align-items: center; gap: 5px; }
.cat:hover { background: var(--ink-100); }
.cat.on { background: var(--ink-900); color: #fff; }
.cat-n { font-size: 10px; opacity: .7; }
.cat-sub-dot { font-size: 12px; opacity: .5; margin-left: 1px; }

/* 子类别（可多组：通识子类别 / 跨学科双选按学院 / 荣誉项目） */
.sub-wrap { margin-bottom: 12px; padding: 8px 10px; background: var(--paper-dim);
  border-radius: var(--radius-sm); display: flex; flex-direction: column; gap: 8px;
  max-height: 200px; overflow-y: auto; }
.sub-group { display: flex; flex-direction: column; gap: 5px; }
.sub-glabel { font-size: 10.5px; font-weight: 600; color: var(--ink-300);
  letter-spacing: .04em; }
.sub-bar { display: flex; flex-wrap: wrap; gap: 5px; }
.sub { font-size: 11.5px; padding: 3px 10px; border-radius: 12px; background: var(--white);
  color: var(--ink-600); border: 1px solid var(--ink-100); }
.sub:hover { border-color: var(--gold); }
.sub.on { background: var(--gold); color: #fff; border-color: var(--gold); }

.pool-list { list-style: none; margin: 0; padding: 0; display: flex;
  flex-direction: column; gap: 6px; max-height: 480px; overflow-y: auto; }
.pc { display: flex; justify-content: space-between; align-items: center; gap: 10px;
  padding: 9px 11px; border: 1px solid var(--ink-100); border-radius: var(--radius-sm); }
.pc.conflicted { background: var(--cinnabar-light); border-color: color-mix(in srgb, var(--cinnabar) 30%, transparent); }
.pc.added { background: var(--jade-light); border-color: color-mix(in srgb, var(--jade) 30%, transparent); }
.pc-name { font-size: 13px; font-weight: 600; color: var(--ink-900); }
.pc-cls { font-weight: 400; font-size: 11px; color: var(--ink-300); margin-left: 5px; }
.pc-meta { font-size: 11px; color: var(--ink-300); margin-top: 2px; }
.pc-num { font-size: 11px; color: var(--ink-600); margin-top: 3px; font-variant-numeric: tabular-nums; }
.surp-ok { color: var(--jade); font-weight: 600; }
.surp-no { color: var(--ink-300); }
.pc-act { flex-shrink: 0; }
.pc-add { font-size: 12px; padding: 5px 12px; background: var(--ink-900); color: #fff;
  border-radius: var(--radius-sm); }
.pc-add:hover { background: var(--ink-700); }
.pc-conflict { font-size: 11px; color: var(--cinnabar); font-weight: 600; }
.pc-done { font-size: 12px; color: var(--jade); font-weight: 600; }
.pc-empty { text-align: center; padding: 30px; color: var(--ink-300); font-size: 13px; }

/* 目标列表 */
.t-count { font-size: 11px; color: var(--ink-300); font-weight: 400; }
.t-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }
.tc { padding: 10px 12px; border: 1px solid var(--ink-100); border-left: 3px solid var(--ink-200);
  border-radius: var(--radius-sm); }
.tc-top { display: flex; align-items: center; gap: 8px; }
.tc-badge { font-size: 10px; font-weight: 700; padding: 2px 7px; border-radius: 4px;
  color: #fff; flex-shrink: 0; }
.tc-name { font-size: 13px; font-weight: 600; color: var(--ink-900); flex: 1;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.tc-x { color: var(--ink-300); font-size: 13px; padding: 2px 5px; }
.tc-x:hover { color: var(--cinnabar); }
.tc-sub { font-size: 11px; color: var(--ink-300); margin-top: 3px; }
.tc-msg { font-size: 11.5px; color: var(--ink-600); margin-top: 4px; line-height: 1.5; }
.t-empty { padding: 30px 16px; text-align: center; font-size: 12.5px; color: var(--ink-300);
  line-height: 1.7; }

/* 状态语义色（复用传统色） */
.s-wait { border-left-color: var(--ink-200); }
.s-wait .tc-badge { background: var(--ink-300); }
.s-watch { border-left-color: var(--gold); }
.s-watch .tc-badge { background: var(--gold); }
.s-ready { border-left-color: var(--cinnabar); }
.s-ready .tc-badge { background: var(--cinnabar); }
.s-ok { border-left-color: var(--jade); background: var(--jade-light); }
.s-ok .tc-badge { background: var(--jade); }
.s-conflict { border-left-color: var(--cinnabar); background: var(--cinnabar-light); }
.s-conflict .tc-badge { background: var(--cinnabar); }
.s-fail { border-left-color: var(--ink-400, #6b6b80); }
.s-fail .tc-badge { background: var(--ink-400, #6b6b80); }
</style>
