<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { deleteStudent, reloginStudent } from '../../api'
import { useStudents } from '../../composables/useStudents'
import type { Student } from '../../types'
import AddStudentDialog from '../AddStudentDialog.vue'

const router = useRouter()
const { students, loading, load, removeById } = useStudents()
const showAdd = ref(false)
const busyId = ref('')

load()

const seal = (s: Student) => (s.name || s.student_id).slice(0, 3)
function tokenExpired(s: Student) {
  return !s.token_expires_at || new Date(s.token_expires_at).getTime() < Date.now()
}

async function relogin(s: Student) {
  if (busyId.value) return
  busyId.value = s.student_id
  try { await reloginStudent(s.student_id); await load(true) }
  catch (e: any) { alert(e.response?.data?.detail || '重登失败') }
  finally { busyId.value = '' }
}

async function remove(s: Student) {
  if (!confirm(`确定删除 ${s.name || s.student_id}？其成绩/监控记录一并移除。`)) return
  busyId.value = s.student_id
  try { await deleteStudent(s.student_id); removeById(s.student_id) }
  catch (e: any) { alert(e.response?.data?.detail || '删除失败') }
  finally { busyId.value = '' }
}

function onAdded() { showAdd.value = false; load(true) }
const count = computed(() => students.value.length)
</script>

<template>
  <div class="head-row">
    <p class="lead">系统内的学生账号 · 身份与教务登录。共 <b>{{ count }}</b> 人。</p>
    <button class="btn-dark" @click="showAdd = true">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
      添加学生
    </button>
  </div>

  <div v-if="loading && !students.length" class="state"><div class="spinner"></div></div>
  <div v-else-if="!students.length" class="state empty">
    <p>还没有学生。添加一个学号即可开始。</p>
    <button class="btn-dark solo" @click="showAdd = true">添加学生</button>
  </div>

  <div v-else class="grid">
    <div v-for="s in students" :key="s.student_id" class="acard" :class="{ busy: busyId === s.student_id }">
      <div class="top">
        <span class="seal" :class="{ long: seal(s).length > 2 }">{{ seal(s) }}</span>
        <div class="who">
          <div class="nm">{{ s.name || s.student_id }}</div>
          <div class="sid">{{ s.student_id }}</div>
        </div>
        <span class="tk" :class="tokenExpired(s) ? 'off' : 'on'">
          {{ tokenExpired(s) ? '需重登' : '已登录' }}
        </span>
      </div>
      <div class="meta">
        <span v-if="s.major">{{ s.major }}</span>
        <span v-if="s.grade" class="yr">{{ s.grade }} 级</span>
        <span class="gc">{{ s.grade_count }} 门成绩</span>
      </div>
      <div class="ops">
        <button class="op" @click="router.push(`/student/${s.student_id}`)">查看档案</button>
        <button class="op" :disabled="busyId === s.student_id" @click="relogin(s)">
          {{ busyId === s.student_id ? '处理中' : '重登教务' }}
        </button>
        <button class="op danger" :disabled="busyId === s.student_id" @click="remove(s)">删除</button>
      </div>
    </div>
  </div>

  <AddStudentDialog v-if="showAdd" @close="showAdd = false" @added="onAdded" />
</template>

<style scoped>
.head-row { display: flex; align-items: center; gap: 14px; margin-bottom: 20px; }
.lead { flex: 1; font-size: 13px; color: var(--ink-400); }
.lead b { color: var(--ink-800); font-family: var(--font-data); }
.btn-dark { display: flex; align-items: center; gap: 5px; padding: 8px 15px; background: var(--ink-900); color: var(--paper); border-radius: var(--radius-sm); font-size: 13px; white-space: nowrap; }
.btn-dark:hover { background: var(--ink-700); }
.btn-dark.solo { display: inline-flex; margin-top: 14px; }

.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 14px; }
.acard { background: var(--white); border: 1px solid var(--ink-100); border-radius: var(--radius-md); padding: 16px 18px; box-shadow: var(--shadow-sm); transition: border-color var(--transition); }
.acard:hover { border-color: var(--ink-200); }
.acard.busy { opacity: .6; }

.top { display: flex; align-items: center; gap: 12px; }
.seal { width: 42px; height: 42px; flex-shrink: 0; border-radius: 4px; background: var(--cinnabar); color: #fff; display: flex; align-items: center; justify-content: center; font-family: var(--serif); font-size: 15px; font-weight: 600; letter-spacing: .06em; text-indent: .06em; box-shadow: inset 0 0 0 1px rgba(255,255,255,.32); }
.seal.long { font-size: 12.5px; letter-spacing: 0; text-indent: 0; }
.who { flex: 1; min-width: 0; }
.nm { font-size: 15.5px; font-weight: 600; color: var(--ink-900); }
.sid { font-family: var(--font-data); font-size: 12px; color: var(--ink-300); }
.tk { font-size: 11px; font-weight: 600; padding: 3px 9px; border-radius: 10px; white-space: nowrap; }
.tk.on { color: var(--jade); background: var(--jade-light); }
.tk.off { color: var(--gold); background: var(--gold-light); }

.meta { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; margin: 12px 0; font-size: 12.5px; color: var(--ink-500); }
.meta .yr { font-family: var(--font-data); color: var(--ink-300); }
.meta .gc { margin-left: auto; color: var(--ink-400); }

.ops { display: flex; gap: 8px; padding-top: 12px; border-top: 1px solid var(--paper-dim); }
.op { flex: 1; padding: 7px; font-size: 12.5px; background: var(--paper-dim); color: var(--ink-700); border: 1px solid var(--ink-100); border-radius: var(--radius-sm); cursor: pointer; transition: border-color var(--transition), color var(--transition); }
.op:hover:not(:disabled) { border-color: var(--ink-300); color: var(--ink-900); }
.op:disabled { opacity: .5; cursor: progress; }
.op.danger { flex: 0 0 auto; }
.op.danger:hover:not(:disabled) { border-color: var(--cinnabar); color: var(--cinnabar); background: var(--cinnabar-light); }

.state { text-align: center; padding: 70px 20px; color: var(--ink-300); font-size: 13.5px; }
.spinner { width: 28px; height: 28px; border: 3px solid var(--ink-100); border-top-color: var(--ink-600); border-radius: 50%; animation: spin .8s linear infinite; margin: 0 auto; }
@keyframes spin { to { transform: rotate(360deg); } }
@media (prefers-reduced-motion: reduce) { .spinner { animation-duration: 2s; } }
</style>
