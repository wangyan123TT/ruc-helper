<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { getMe, logout, clearToken } from '../api'
import { useStudentData } from '../composables/useStudentData'
import { useTimetable } from '../composables/useTimetable'
import SideNav from '../components/SideNav.vue'
import OverviewPanel from '../components/OverviewPanel.vue'
import GradeTable from '../components/GradeTable.vue'
import TimetablePanel from '../components/TimetablePanel.vue'
import GrabPanel from '../components/GrabPanel.vue'

// self=true 时从 /me 解析自己的学号；否则用路由传入的 id（管理台点进来）
const props = defineProps<{ id?: string; self?: boolean }>()
const router = useRouter()

const sid = ref(props.id || '')
const { student, grades, gpa, loading, refreshing, result, load, refresh } = useStudentData(sid)
const { data: preData, loading: preLoading, error: preError, load: loadPre, reset: resetPre } = useTimetable(sid, 'preselect')
const { data: enrData, loading: enrLoading, error: enrError, load: loadEnr, reset: resetEnr } = useTimetable(sid, 'enrolled')

type Nav = 'overview' | 'grades' | 'timetable' | 'enrolled' | 'grab'
const nav = ref<Nav>('overview')
const NAV_TITLE: Record<Nav, string> = {
  overview: '学业概览', grades: '成绩明细',
  timetable: '预选课表', enrolled: '已选课表', grab: '抢课',
}

const seal = computed(() => (student.value?.name || student.value?.student_id || '').slice(0, 3))
const identity = computed(() => student.value ? {
  seal: seal.value,
  name: student.value.name || student.value.student_id,
  sub: [student.value.major, student.value.grade ? student.value.grade + ' 级' : '']
    .filter(Boolean).join(' · '),
} : null)

const navGroups = computed(() => [
  {
    label: '我的学业', items: [
      { key: 'overview', label: '概览', icon: 'overview' },
      { key: 'grades', label: '成绩', icon: 'grades', count: grades.value.length || null },
    ],
  },
  {
    label: '选课', items: [
      { key: 'timetable', label: '预选课表', icon: 'preselect', count: preData.value?.n_courses ?? null },
      { key: 'enrolled', label: '已选课表', icon: 'enrolled', count: enrData.value?.n_courses ?? null },
      { key: 'grab', label: '抢课', icon: 'grab' },
    ],
  },
])

const footer = computed(() => [
  { key: 'print', label: '打印档案', icon: 'print' },
  props.self
    ? { key: 'logout', label: '退出登录', icon: 'logout', danger: true }
    : { key: 'back', label: '返回管理台', icon: 'back' },
])

function switchNav(k: string) {
  nav.value = k as Nav
  if (k === 'timetable') loadPre()
  if (k === 'enrolled') loadEnr()
}

async function onFoot(k: string) {
  if (k === 'print') window.print()
  else if (k === 'logout') { await logout(); clearToken(); router.replace('/login') }
  else if (k === 'back') router.push('/admin')
}

async function boot() {
  if (props.self && !sid.value) sid.value = (await getMe()).student_id
  nav.value = 'overview'
  resetPre(); resetEnr()
  await load()
}

onMounted(boot)
watch(() => props.id, () => { if (props.id) { sid.value = props.id; boot() } })
</script>

<template>
  <div class="shell">
    <SideNav
      glyph="选" brand-title="选课助手" brand-sub="微人大 · RUC"
      :identity="identity" :groups="navGroups" :active="nav" :footer="footer"
      @select="switchNav" @foot="onFoot" />

    <div class="main">
      <div class="main-head">
        <h1>{{ NAV_TITLE[nav] }}</h1>
        <span class="crumb" v-if="student">{{ student.name || student.student_id }}</span>
        <span class="spacer"></span>
        <button v-if="nav === 'overview' || nav === 'grades'" class="btn-dark" :disabled="refreshing" @click="refresh">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" :class="{ spin: refreshing }"><polyline points="23 4 23 10 17 10" /><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" /></svg>
          {{ refreshing ? '刷新中' : '刷新成绩' }}
        </button>
      </div>

      <div class="body">
        <div v-if="loading" class="state"><div class="spinner"></div></div>
        <div v-else-if="!student" class="state"><p class="muted">无法加载学生信息</p></div>

        <template v-else>
          <div v-if="result && (nav === 'overview' || nav === 'grades')" class="banner">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" /><polyline points="22 4 12 14.01 9 11.01" /></svg>
            刷新完成：共 {{ result.total }} 门，新增 {{ result.new_count }} 门，更新 {{ result.updated_count }} 门
          </div>

          <OverviewPanel v-if="nav === 'overview'" :grades="grades" :gpa="gpa" />
          <GradeTable v-else-if="nav === 'grades'" :grades="grades" :new-ids="result?.new_grades?.map(g => g.cjgl016id) || []" />
          <TimetablePanel v-else-if="nav === 'timetable'" kind="preselect" :data="preData" :loading="preLoading" :error="preError" @refresh="loadPre(true)" />
          <TimetablePanel v-else-if="nav === 'enrolled'" kind="enrolled" :data="enrData" :loading="enrLoading" :error="enrError" @refresh="loadEnr(true)" />
          <GrabPanel v-else-if="nav === 'grab'" :student-id="sid" />
        </template>
      </div>
    </div>
  </div>
</template>

<style scoped>
.shell { display: flex; min-height: 100vh; background: var(--paper); }
.main { flex: 1; min-width: 0; display: flex; flex-direction: column; }

.main-head { position: sticky; top: 0; z-index: 20;
  background: color-mix(in srgb, var(--paper) 88%, transparent); backdrop-filter: blur(8px);
  border-bottom: 1px solid var(--ink-100); padding: 15px 38px; display: flex; align-items: center; gap: 14px; }
.main-head h1 { font-family: var(--serif); font-size: 21px; font-weight: 600; color: var(--ink-900); }
.main-head .crumb { font-size: 12px; color: var(--ink-300); }
.main-head .spacer { flex: 1; }

.btn-dark { display: flex; align-items: center; gap: 5px; padding: 8px 15px; background: var(--ink-900); color: var(--paper); border-radius: var(--radius-sm); font-size: 13px; }
.btn-dark:hover:not(:disabled) { background: var(--ink-700); }
.btn-dark:disabled { opacity: .6; cursor: not-allowed; }
.spin { animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* 正文居中在主区：易读宽度，宽屏两侧留白平衡，不紧贴左边 */
.body { padding: 28px 40px 70px; max-width: 1280px; width: 100%; margin: 0 auto; }
.state { text-align: center; padding: 80px 20px; }
.spinner { width: 28px; height: 28px; border: 3px solid var(--ink-100); border-top-color: var(--ink-600); border-radius: 50%; animation: spin .8s linear infinite; margin: 0 auto; }
.muted { font-size: 14px; color: var(--ink-300); }

.banner { display: flex; align-items: center; gap: 8px; padding: 11px 16px; background: var(--jade-light); border: 1px solid var(--jade); border-radius: var(--radius-sm); margin-bottom: 18px; font-size: 13px; color: var(--ink-700); }
.banner svg { color: var(--jade); flex-shrink: 0; }

@media (max-width: 820px) {
  .shell { flex-direction: column; }
  .main-head { padding: 12px 16px; }
  .body { padding: 18px 16px 60px; }
}
@media (prefers-reduced-motion: reduce) { .spin, .spinner { animation-duration: 2s; } }
@media print { .main-head { display: none; } .body { padding: 0; } }
</style>
