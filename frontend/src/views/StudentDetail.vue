<script setup lang="ts">
import { ref, onMounted, watch, computed } from 'vue'
import { useRouter } from 'vue-router'
import { getStudent, getGrades, refreshGrades, reloginStudent, getTimetable } from '../api'
import type { Student, GradeItem, GradeRefreshResult, TimetableData } from '../types'
import GradeTable from '../components/GradeTable.vue'
import TimetableGrid from '../components/TimetableGrid.vue'

const props = defineProps<{ id: string }>()
const router = useRouter()

const student = ref<Student | null>(null)
const grades = ref<GradeItem[]>([])
const loading = ref(true)
const refreshing = ref(false)
const result = ref<GradeRefreshResult | null>(null)
let _reqGen = 0

const tab = ref<'grades' | 'timetable'>('grades')

// 预选课表：实时抓（需重新登录教务，约 5 秒），点到才加载
const timetable = ref<TimetableData | null>(null)
const ttLoading = ref(false)
const ttError = ref('')
let _ttGen = 0

async function loadTimetable(force = false) {
  if (ttLoading.value) return
  if (timetable.value && !force) return
  const gen = ++_ttGen
  ttLoading.value = true
  ttError.value = ''
  try {
    const d = await getTimetable(props.id)
    if (gen !== _ttGen) return
    timetable.value = d
  } catch (e: any) {
    if (gen !== _ttGen) return
    timetable.value = null
    ttError.value = e.response?.data?.detail || e.message || '加载失败'
  } finally {
    if (gen === _ttGen) ttLoading.value = false
  }
}

function switchTab(t: 'grades' | 'timetable') {
  tab.value = t
  if (t === 'timetable') loadTimetable()
}

async function load() {
  const gen = ++_reqGen
  loading.value = true
  student.value = null
  grades.value = []
  timetable.value = null
  ttError.value = ''
  tab.value = 'grades'
  try {
    const [s, g] = await Promise.all([getStudent(props.id), getGrades(props.id)])
    if (gen !== _reqGen) return
    student.value = s
    grades.value = g
  } catch (e) {
    if (gen !== _reqGen) return
    console.error(e)
  }
  if (gen === _reqGen) loading.value = false
}

let _retryLeft = 1

async function refresh() {
  _retryLeft = 1
  await _doRefresh()
}

async function _doRefresh() {
  const gen = ++_reqGen
  refreshing.value = true
  result.value = null
  try {
    const r = await refreshGrades(props.id)
    if (gen !== _reqGen) return
    result.value = r
    const g = await getGrades(props.id)
    if (gen !== _reqGen) return
    grades.value = g
  } catch (e: any) {
    if (gen !== _reqGen) return
    if (e.response?.status === 502 && _retryLeft > 0) {
      _retryLeft--
      try { await reloginStudent(props.id) } catch (_) { /* ignore */ }
      await _doRefresh()
      return
    }
    alert('刷新失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    refreshing.value = false
  }
}

function doPrint() { window.print() }

onMounted(load)
watch(() => props.id, () => { load() })
</script>

<template>
  <div class="detail-page">
    <!-- Top Bar -->
    <header class="detail-topbar">
      <div class="topbar-inner">
        <button class="btn-back" @click="router.push('/')">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="15 18 9 12 15 6"/></svg>
          返回
        </button>
        <div class="brand-sm">◈ RUC Helper</div>
      </div>
    </header>

    <main class="detail-main">
      <div v-if="loading" class="state-box">
        <div class="spinner"></div>
      </div>

      <div v-else-if="!student" class="state-box empty-state">
        <p>无法加载学生信息</p>
        <button class="btn-back" @click="router.push('/')">← 返回首页</button>
      </div>

      <template v-else-if="student">
        <!-- Student Info Bar (matching real page) -->
        <div class="student-info-bar">
          <span>学号：<strong>{{ student.student_id }}</strong></span>
          <span>姓名：<strong>{{ student.name || student.student_id }}</strong></span>
          <span v-if="student.major">院系：<strong>{{ student.major }}</strong></span>
          <span v-if="student.grade">年级：<strong>{{ student.grade }}</strong></span>
          <button class="btn-print" @click="doPrint">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 6 2 18 2 18 9"/><path d="M6 12H4a2 2 0 0 0-2 2v4a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-4a2 2 0 0 0-2-2h-2"/><rect x="6" y="14" width="12" height="8"/></svg>
            打印
          </button>
        </div>

        <!-- Tabs -->
        <div class="tabs">
          <button class="tab" :class="{ active: tab === 'grades' }" @click="switchTab('grades')">
            成绩<span class="tab-n">{{ grades.length }}</span>
          </button>
          <button class="tab" :class="{ active: tab === 'timetable' }" @click="switchTab('timetable')">
            预选课表<span v-if="timetable" class="tab-n">{{ timetable.n_courses }}</span>
          </button>
        </div>

        <!-- ===== 成绩 ===== -->
        <template v-if="tab === 'grades'">
          <div class="action-bar">
            <span class="grade-count-badge">{{ grades.length }} 门成绩</span>
            <button class="btn-refresh" :disabled="refreshing" @click="refresh">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" :class="{ spinning: refreshing }"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
              {{ refreshing ? '刷新中...' : '刷新成绩' }}
            </button>
          </div>

          <div v-if="result" class="result-banner">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
            <span>刷新完成：共 {{ result.total }} 门，新增 <strong>{{ result.new_count }}</strong> 门，更新 <strong>{{ result.updated_count }}</strong> 门</span>
          </div>

          <GradeTable :grades="grades" :newIds="result?.new_grades?.map(g => g.cjgl016id) || []" />
        </template>

        <!-- ===== 预选课表 ===== -->
        <template v-else>
          <div class="action-bar">
            <span class="grade-count-badge" v-if="timetable">
              {{ timetable.context.hd_name }}
            </span>
            <button class="btn-refresh" :disabled="ttLoading" @click="loadTimetable(true)">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" :class="{ spinning: ttLoading }"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
              {{ ttLoading ? '抓取中...' : '重新抓取' }}
            </button>
          </div>

          <div v-if="ttLoading" class="state-box">
            <div class="spinner"></div>
            <p class="hint">正在登录教务系统抓取待筛选志愿，约需 5 秒…</p>
          </div>

          <div v-else-if="ttError" class="err-banner">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
            <span>{{ ttError }}</span>
          </div>

          <TimetableGrid v-else-if="timetable" :data="timetable" />
        </template>
      </template>
    </main>
  </div>
</template>

<style scoped>
.detail-page {
  min-height: 100vh;
  background: var(--paper);
}
.detail-topbar {
  background: var(--ink-900);
  position: sticky;
  top: 0;
  z-index: 50;
}
.detail-topbar .topbar-inner {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 28px;
  height: 52px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.btn-back {
  background: none;
  color: #ccc;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  border-radius: var(--radius-sm);
}
.btn-back:hover { color: #fff; background: rgba(255,255,255,0.08); }
.brand-sm {
  font-size: 14px;
  color: var(--ink-300);
}

.detail-main {
  max-width: 1400px;
  margin: 0 auto;
  padding: 28px;
}

.state-box { text-align: center; padding: 80px; }
.spinner {
  width: 32px; height: 32px;
  border: 3px solid var(--ink-100);
  border-top-color: var(--ink-600);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* Student Info Bar */
.student-info-bar {
  background: var(--white);
  border-radius: var(--radius-md);
  padding: 14px 20px;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 24px;
  flex-wrap: wrap;
  font-size: 14px;
  color: var(--ink-600);
  box-shadow: var(--shadow-sm);
}
.student-info-bar strong {
  color: var(--ink-900);
}
.btn-print {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 4px;
  background: var(--ink-900);
  color: #fff;
  padding: 5px 14px;
  border-radius: var(--radius-sm);
  font-size: 13px;
}

/* Action Bar */
.action-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}
.grade-count-badge {
  font-size: 14px;
  font-weight: 500;
  color: var(--ink-600);
  background: var(--white);
  padding: 6px 14px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--ink-100);
}
.btn-refresh {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 18px;
  background: var(--ink-900);
  color: #fff;
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-weight: 500;
}
.btn-refresh:hover { background: var(--ink-800); }
.btn-refresh:disabled { opacity: 0.6; cursor: not-allowed; }
.spinning { animation: spin 1s linear infinite; }

/* Tabs */
.tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 16px;
  border-bottom: 1px solid var(--ink-100);
}
.tab {
  background: none;
  padding: 9px 16px;
  font-size: 14px;
  font-weight: 500;
  color: var(--ink-300);
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: color var(--transition);
}
.tab:hover { color: var(--ink-600); }
.tab.active {
  color: var(--ink-900);
  border-bottom-color: var(--ink-900);
}
.tab-n {
  font-size: 11px;
  background: var(--ink-100);
  color: var(--ink-600);
  padding: 1px 6px;
  border-radius: 10px;
  font-variant-numeric: tabular-nums;
}
.tab.active .tab-n { background: var(--ink-900); color: #fff; }

.hint {
  margin-top: 12px;
  font-size: 13px;
  color: var(--ink-300);
}

/* Error Banner */
.err-banner {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 18px;
  background: var(--cinnabar-light);
  border: 1px solid var(--cinnabar);
  border-radius: var(--radius-sm);
  font-size: 14px;
  color: var(--ink-800);
}
.err-banner svg { color: var(--cinnabar); flex-shrink: 0; }

/* Result Banner */
.result-banner {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 18px;
  background: var(--jade-light);
  border: 1px solid var(--jade);
  border-radius: var(--radius-sm);
  margin-bottom: 16px;
  font-size: 14px;
  color: var(--ink-800);
}
.result-banner svg { color: var(--jade); flex-shrink: 0; }
</style>
