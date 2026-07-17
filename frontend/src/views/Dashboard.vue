<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { listStudents, getMonitorStatus } from '../api'
import type { Student, MonitorStatus } from '../types'
import StudentCard from '../components/StudentCard.vue'
import AddStudentDialog from '../components/AddStudentDialog.vue'
import SettingsDialog from '../components/SettingsDialog.vue'

// 这一页只干一件事：认出并选中一个学生。
// 监控开关/轮询间隔/监控日志 → 设置面板；单个学生的监控状态 → 学生详情页。
const students = ref<Student[]>([])
const status = ref<MonitorStatus>({ running: false, poll_interval: 30, active_students: 0 })
const showAdd = ref(false)
const showSettings = ref(false)
const loading = ref(true)

async function load() {
  loading.value = true
  try {
    const [s, st] = await Promise.all([listStudents(), getMonitorStatus()])
    students.value = s
    status.value = st
  } catch (e) {
    console.error(e)
    students.value = []
  }
  loading.value = false
}

function onAdded() {
  showAdd.value = false
  load()
}

function onSettingsClose() {
  showSettings.value = false
  getMonitorStatus().then(st => { status.value = st }).catch(() => {})
}

onMounted(load)
</script>

<template>
  <div class="dashboard">
    <header class="topbar">
      <div class="topbar-inner">
        <div class="brand">
          <span class="brand-icon">◈</span>
          <h1>RUC Helper</h1>
        </div>

        <div class="controls">
          <!-- 只读状态：后台轮询还活着吗。开关和日志在设置里。 -->
          <button class="status" @click="showSettings = true"
                  :title="status.running ? '后台监控运行中，点击查看设置' : '后台监控已停止，点击前往开启'">
            <span class="dot" :class="{ live: status.running }"></span>
            {{ status.running ? '监控中' : '已停止' }}
          </button>

          <button class="btn-icon" @click="showSettings = true" title="设置">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
          </button>

          <button class="btn-add" @click="showAdd = true">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
            添加学生
          </button>
        </div>
      </div>
    </header>

    <main class="main">
      <div v-if="loading" class="state">
        <div class="spinner"></div>
      </div>

      <div v-else-if="students.length === 0" class="state empty">
        <span class="empty-seal">◈</span>
        <h2>还没有学生</h2>
        <p>添加一个学号，就能查看他的成绩和预选课表。</p>
        <button class="btn-add" @click="showAdd = true">添加学生</button>
      </div>

      <div v-else class="roster">
        <StudentCard v-for="s in students" :key="s.student_id" :student="s" />
      </div>
    </main>

    <AddStudentDialog v-if="showAdd" @close="showAdd = false" @added="onAdded" />
    <SettingsDialog v-if="showSettings" @close="onSettingsClose" />
  </div>
</template>

<style scoped>
.dashboard { min-height: 100vh; background: var(--paper); }

/* ── 顶栏 ── */
.topbar {
  background: var(--ink-900);
  position: sticky;
  top: 0;
  z-index: 50;
}
.topbar-inner {
  max-width: 1320px;
  margin: 0 auto;
  padding: 0 28px;
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
}
.brand { display: flex; align-items: center; gap: 10px; }
.brand-icon { font-size: 22px; color: var(--gold); }
.brand h1 { font-size: 17px; font-weight: 600; color: #fff; letter-spacing: 0.5px; }

.controls { display: flex; align-items: center; gap: 10px; }

.status {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 5px 12px;
  background: none;
  border-radius: var(--radius-sm);
  font-size: 13px;
  color: var(--ink-200);
  font-family: inherit;
  cursor: pointer;
}
.status:hover { background: rgba(255, 255, 255, 0.08); color: #fff; }
.dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--ink-300);
  flex-shrink: 0;
}
.dot.live {
  background: var(--jade);
  box-shadow: 0 0 0 0 rgba(26, 122, 90, 0.5);
  animation: breathe 2.6s ease-in-out infinite;
}
@keyframes breathe {
  50% { box-shadow: 0 0 0 4px rgba(26, 122, 90, 0); }
}

.btn-icon {
  display: flex;
  padding: 7px;
  background: none;
  color: var(--ink-200);
  border-radius: var(--radius-sm);
  cursor: pointer;
}
.btn-icon:hover { background: rgba(255, 255, 255, 0.08); color: #fff; }

.btn-add {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 14px;
  background: rgba(255, 255, 255, 0.12);
  color: #fff;
  border-radius: var(--radius-sm);
  font-size: 13px;
  font-weight: 500;
  font-family: inherit;
  white-space: nowrap;
  cursor: pointer;
}
.btn-add:hover { background: rgba(255, 255, 255, 0.22); }

/* ── 名册 ── */
.main { max-width: 1320px; margin: 0 auto; padding: 32px 28px; }
.roster {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}

.state { text-align: center; padding: 90px 20px; color: var(--ink-300); }
.empty-seal {
  display: inline-block;
  font-size: 34px;
  color: var(--ink-200);
  margin-bottom: 14px;
}
.empty h2 { font-size: 17px; font-weight: 600; color: var(--ink-800); margin-bottom: 6px; }
.empty p { font-size: 13.5px; margin-bottom: 20px; }
.empty .btn-add {
  display: inline-flex;
  background: var(--ink-900);
  padding: 9px 20px;
  font-size: 14px;
}
.empty .btn-add:hover { background: var(--ink-700); }

.spinner {
  width: 30px;
  height: 30px;
  border: 3px solid var(--ink-100);
  border-top-color: var(--ink-600);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto;
}
@keyframes spin { to { transform: rotate(360deg); } }

@media (prefers-reduced-motion: reduce) {
  .dot.live { animation: none; }
  .spinner { animation-duration: 2s; }
}
@media (max-width: 640px) {
  .topbar-inner { padding: 0 14px; gap: 10px; }
  .main { padding: 18px 14px; }
  .status { display: none; }
}
</style>
