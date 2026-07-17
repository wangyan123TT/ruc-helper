<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { getStudent, getGrades, refreshGrades, reloginStudent, getGpaSummary, getTimetable } from '../api'
import type { Student, GradeItem, GradeRefreshResult, GpaSummary, TimetableData } from '../types'
import GradeTable from '../components/GradeTable.vue'
import TimetableGrid from '../components/TimetableGrid.vue'

const props = defineProps<{ id: string }>()
const router = useRouter()

const student = ref<Student | null>(null)
const grades = ref<GradeItem[]>([])
const loading = ref(true)
const refreshing = ref(false)
const result = ref<GradeRefreshResult | null>(null)
const gpaSummary = ref<GpaSummary | null>(null)
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
  gpaSummary.value = null
  timetable.value = null
  ttError.value = ''
  tab.value = 'grades'
  try {
    const [s, g, summary] = await Promise.all([
      getStudent(props.id), getGrades(props.id),
      getGpaSummary(props.id).catch(() => null)
    ])
    if (gen !== _reqGen) return
    student.value = s
    grades.value = g
    gpaSummary.value = summary
  } catch (e) {
    if (gen !== _reqGen) return
    console.error(e)
  }
  if (gen === _reqGen) loading.value = false
}

let _retryLeft = 1
async function refresh() { _retryLeft = 1; await _doRefresh() }
async function _doRefresh() {
  const gen = ++_reqGen
  refreshing.value = true; result.value = null
  try {
    const r = await refreshGrades(props.id)
    if (gen !== _reqGen) return
    result.value = r
    grades.value = await getGrades(props.id)
  } catch (e: any) {
    if (gen !== _reqGen) return
    if (e.response?.status === 502 && _retryLeft > 0) {
      _retryLeft--; try { await reloginStudent(props.id) } catch (_) {}
      await _doRefresh(); return
    }
    alert('刷新失败: ' + (e.response?.data?.detail || e.message))
  } finally { refreshing.value = false }
}

function doPrint() { window.print() }
onMounted(load)
watch(() => props.id, () => { load() })
</script>

<template>
  <div class="detail-page">
    <header class="topbar">
      <div class="topbar-inner">
        <button class="btn-back" @click="router.push('/')">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="15 18 9 12 15 6"/></svg>
          返回
        </button>
        <span class="brand">RUC Helper</span>
      </div>
    </header>

    <main class="main">
      <div v-if="loading" class="state"><div class="spinner"></div></div>
      <div v-else-if="!student" class="state"><p>无法加载学生信息</p></div>

      <template v-else-if="student">
        <!-- Info bar -->
        <div class="info-bar">
          <span>{{ student.name || student.student_id }}</span>
          <span class="info-sep">·</span>
          <span>{{ student.student_id }}</span>
          <span class="info-sep">·</span>
          <span v-if="student.major">{{ student.major }}</span>
          <span class="info-sep" v-if="student.grade">·</span>
          <span v-if="student.grade">{{ student.grade }}级</span>
          <button class="btn-print" @click="doPrint">打印</button>
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
          <!-- GPA Card -->
          <div v-if="gpaSummary" class="gpa-card">
            <!-- Group 1: GPA -->
            <div class="group">
              <div class="group-head">
                <span class="group-title">平均学分绩点</span>
                <span class="group-sub">不含 P/F 课 · {{ gpaSummary.major_name }} {{ gpaSummary.dept_name }}</span>
              </div>
              <div class="group-body">
                <div class="score-block">
                  <span class="score-num">{{ gpaSummary.gpa }}</span>
                  <span class="score-rank" v-if="gpaSummary.class_rank">班级 <b>第{{ gpaSummary.class_rank }}</b></span>
                  <span class="score-rank" v-if="gpaSummary.major_rank">专业 <b>第{{ gpaSummary.major_rank }}</b></span>
                </div>
                <div class="score-block dim" v-if="gpaSummary.api_gpa !== null && gpaSummary.api_gpa !== gpaSummary.gpa">
                  <span class="score-num dim">{{ gpaSummary.api_gpa }}</span>
                  <span class="score-desc">含 P/F 课（按 1.0 绩点计入）</span>
                  <span class="score-rank" v-if="gpaSummary.gpa_rank">班级 <b>第{{ gpaSummary.gpa_rank }}</b></span>
                </div>
              </div>
            </div>

            <!-- Group 2: Weighted Average -->
            <div class="group" v-if="gpaSummary.weighted_avg">
              <div class="group-head">
                <span class="group-title">学分加权平均分</span>
              </div>
              <div class="group-body">
                <div class="score-block">
                  <span class="score-num">{{ gpaSummary.weighted_avg }}</span>
                  <span class="score-rank" v-if="gpaSummary.weighted_rank">班级 <b>第{{ gpaSummary.weighted_rank }}</b></span>
                </div>
              </div>
            </div>

            <!-- Group 3: Arithmetic Average -->
            <div class="group" v-if="gpaSummary.simple_avg">
              <div class="group-head">
                <span class="group-title">算术平均分</span>
              </div>
              <div class="group-body">
                <div class="score-block">
                  <span class="score-num">{{ gpaSummary.simple_avg }}</span>
                  <span class="score-rank" v-if="gpaSummary.avg_rank">班级 <b>第{{ gpaSummary.avg_rank }}</b></span>
                </div>
              </div>
            </div>

            <!-- Footer: credits + semester summary -->
            <div class="card-foot">
              <span>{{ gpaSummary.courses }} 门课 · {{ gpaSummary.credits }} 学分</span>
              <span class="foot-sep"></span>
              <details v-if="gpaSummary.semester_summary.length">
                <summary>各学期汇总</summary>
                <div class="sem-table">
                  <div class="sem-row sem-head">
                    <span class="sem-c1">学期</span><span>课程</span><span>学分</span><span>GPA</span><span>均分</span>
                  </div>
                  <div class="sem-row" v-for="s in gpaSummary.semester_summary" :key="s.jczy013id">
                    <span class="sem-c1">{{ s.jczy013id }}</span><span>{{ s.kcnum }}</span><span>{{ s.zxf }}</span><span>{{ s.pjxfjd }}</span><span>{{ s.pjxfj }}</span>
                  </div>
                </div>
              </details>
            </div>
          </div>

          <div class="actions">
            <span>{{ grades.length }} 门成绩</span>
            <button class="btn-refresh" :disabled="refreshing" @click="refresh">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" :class="{ spin: refreshing }"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
              {{ refreshing ? '刷新中' : '刷新成绩' }}
            </button>
          </div>

          <div v-if="result" class="banner">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
            刷新完成：共 {{ result.total }} 门，新增 {{ result.new_count }} 门，更新 {{ result.updated_count }} 门
          </div>

          <GradeTable :grades="grades" :newIds="result?.new_grades?.map(g => g.cjgl016id) || []" />
        </template>

        <!-- ===== 预选课表 ===== -->
        <template v-else>
          <div class="actions">
            <span>{{ timetable ? timetable.context.hd_name : '待筛选志愿课表' }}</span>
            <button class="btn-refresh" :disabled="ttLoading" @click="loadTimetable(true)">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" :class="{ spin: ttLoading }"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/></svg>
              {{ ttLoading ? '抓取中' : '重新抓取' }}
            </button>
          </div>

          <div v-if="ttLoading" class="state">
            <div class="spinner"></div>
            <p class="hint">正在登录教务系统抓取待筛选志愿，约需 5 秒…</p>
          </div>

          <div v-else-if="ttError" class="banner err">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
            {{ ttError }}
          </div>

          <TimetableGrid v-else-if="timetable" :data="timetable" />
        </template>
      </template>
    </main>
  </div>
</template>

<style scoped>
.detail-page { min-height: 100vh; background: var(--paper); }

/* Top bar */
.topbar { background: var(--ink-900); position: sticky; top: 0; z-index: 50; }
.topbar-inner { max-width: 1100px; margin: 0 auto; padding: 0 24px; height: 48px; display: flex; align-items: center; justify-content: space-between; }
.btn-back { background: none; color: #ccc; font-size: 13px; display: flex; align-items: center; gap: 4px; padding: 4px 8px; border-radius: var(--radius-sm); }
.btn-back:hover { color: #fff; background: rgba(255,255,255,0.08); }
.brand { font-size: 13px; color: var(--ink-300); }

.main { max-width: 1100px; margin: 0 auto; padding: 20px 24px; }
.state { text-align: center; padding: 80px; }
.spinner { width: 28px; height: 28px; border: 3px solid var(--ink-100); border-top-color: var(--ink-600); border-radius: 50%; animation: spin 0.8s linear infinite; margin: 0 auto; }
@keyframes spin { to { transform: rotate(360deg); } }

/* Info bar */
.info-bar { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; background: var(--white); border-radius: var(--radius-md); padding: 10px 18px; margin-bottom: 16px; font-size: 13px; color: var(--ink-600); box-shadow: var(--shadow-sm); }
.info-sep { color: var(--ink-200); }
.btn-print { margin-left: auto; background: var(--ink-900); color: #fff; padding: 4px 12px; border-radius: var(--radius-sm); font-size: 12px; }

/* GPA Card */
.gpa-card { background: var(--white); border-radius: var(--radius-lg); box-shadow: var(--shadow-md); margin-bottom: 16px; overflow: hidden; }

.group { border-bottom: 1px solid var(--ink-100); }
.group:last-of-type { border-bottom: none; }
.group-head { padding: 14px 24px 0; display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap; }
.group-title { font-size: 14px; font-weight: 600; color: var(--ink-700); }
.group-sub { font-size: 12px; color: var(--ink-300); }
.group-body { display: flex; gap: 0; padding: 8px 24px 16px; flex-wrap: wrap; }

.score-block { display: flex; flex-direction: column; align-items: flex-start; min-width: 140px; padding: 8px 0; }
.score-block.dim { opacity: 0.6; }
.score-num { font-size: 36px; font-weight: 700; color: var(--ink-900); line-height: 1.1; }
.score-num.dim { color: var(--ink-300); font-size: 26px; }
.score-desc { font-size: 11px; color: var(--ink-400); margin-top: 2px; }
.score-rank { font-size: 13px; color: var(--ink-500); margin-top: 2px; }
.score-rank b { color: var(--ink-800); font-size: 15px; }

/* Footer */
.card-foot { display: flex; align-items: center; gap: 0; flex-wrap: wrap; padding: 10px 24px 14px; font-size: 12px; color: var(--ink-400); background: #f8f8fb; }
.card-foot details { margin-left: 0; }
.card-foot summary { cursor: pointer; color: var(--ink-500); font-size: 12px; padding: 2px 0; }
.foot-sep { width: 1px; height: 12px; background: var(--ink-200); margin: 0 12px; }
.sem-table { margin-top: 8px; border: 1px solid var(--ink-100); border-radius: var(--radius-sm); overflow: hidden; width: 100%; }
.sem-row { display: flex; font-size: 12px; }
.sem-row span { flex: 1; padding: 5px 8px; text-align: center; }
.sem-row span.sem-c1 { flex: 2; text-align: left; }
.sem-head { background: var(--white); font-weight: 600; }
.sem-row:not(.sem-head) { border-top: 1px solid var(--ink-100); }

/* Actions */
.actions { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; font-size: 13px; color: var(--ink-500); }
.btn-refresh { display: flex; align-items: center; gap: 4px; padding: 7px 16px; background: var(--ink-900); color: #fff; border-radius: var(--radius-sm); font-size: 13px; }
.btn-refresh:hover { background: var(--ink-800); }
.btn-refresh:disabled { opacity: 0.6; cursor: not-allowed; }
.spin { animation: spin 1s linear infinite; }

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
.tab.active { color: var(--ink-900); border-bottom-color: var(--ink-900); }
.tab-n {
  font-size: 11px;
  background: var(--ink-100);
  color: var(--ink-600);
  padding: 1px 6px;
  border-radius: 10px;
  font-variant-numeric: tabular-nums;
}
.tab.active .tab-n { background: var(--ink-900); color: #fff; }

.hint { margin-top: 12px; font-size: 13px; color: var(--ink-300); }

.banner { display: flex; align-items: center; gap: 8px; padding: 10px 16px; background: var(--jade-light); border: 1px solid var(--jade); border-radius: var(--radius-sm); margin-bottom: 16px; font-size: 13px; color: var(--ink-700); }
.banner svg { color: var(--jade); flex-shrink: 0; }
/* 课表抓取失败 —— 复用 banner，换成警示色 */
.banner.err { background: var(--cinnabar-light); border-color: var(--cinnabar); }
.banner.err svg { color: var(--cinnabar); }

@media (max-width: 768px) {
  .main { padding: 12px; }
  .group-body { flex-direction: column; gap: 4px; }
  .score-num { font-size: 30px; }
  .score-num.dim { font-size: 22px; }
}
</style>
