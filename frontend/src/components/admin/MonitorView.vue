<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import {
  getMonitorStatus, startMonitor, stopMonitor, getMonitorLogs,
  getSmtpSettings, saveSmtpSettings, toggleMonitorStudent, testEmailStudent, updateStudentEmail,
} from '../../api'
import type { MonitorLog } from '../../api'
import { useStudents } from '../../composables/useStudents'
import type { Student, MonitorStatus } from '../../types'

const { students, load } = useStudents()

// ── 引擎 ──
const status = ref<MonitorStatus>({ running: false, poll_interval: 300, active_students: 0 })
const interval = ref(300)
const engineBusy = ref(false)
async function loadStatus() {
  try { status.value = await getMonitorStatus(); interval.value = status.value.poll_interval || 300 } catch { /* ignore */ }
}
async function toggleEngine() {
  engineBusy.value = true
  try {
    if (status.value.running) await stopMonitor()
    else await startMonitor(interval.value)
    await loadStatus()
  } catch (e: any) { alert('操作失败：' + (e.response?.data?.detail || e.message)) }
  finally { engineBusy.value = false }
}
const intervalHint = computed(() => {
  const s = interval.value
  if (!s || s < 5) return ''
  return s >= 60 ? `每 ${(s / 60).toFixed(s % 60 ? 1 : 0)} 分钟一次` : `每 ${s} 秒一次`
})

// ── SMTP ──
const smtp = ref({ smtpHost: 'smtp.qq.com', smtpPort: '587', smtpUsername: '', smtpPassword: '', fromAddress: '' })
const saving = ref(false)
const smtpMsg = ref<{ text: string; ok: boolean } | null>(null)
async function loadSmtp() { try { smtp.value = await getSmtpSettings() } catch { /* 默认值 */ } }
async function saveSmtp() {
  saving.value = true; smtpMsg.value = null
  try {
    const data: Record<string, string> = {}
    for (const [k, v] of Object.entries(smtp.value)) {
      if (k === 'smtpPassword' && v && v.includes('****')) continue
      data[k] = v || ''
    }
    await saveSmtpSettings(data)
    smtpMsg.value = { text: '已保存', ok: true }
  } catch (e: any) { smtpMsg.value = { text: '保存失败：' + (e.response?.data?.detail || e.message), ok: false } }
  finally { saving.value = false }
}

// ── 日志 ──
const logs = ref<MonitorLog[]>([])
const showLogs = ref(false)
let timer: any = null
async function loadLogs() { try { logs.value = await getMonitorLogs() } catch { /* ignore */ } }
const fmtTime = (t: string) => (t ? t.substring(11, 19) : '')

// ── 每人监控 ──
const emailDraft = ref<Record<string, string>>({})
const rowBusy = ref<Record<string, string>>({})   // sid -> 'toggle'|'email'|'test'
const rowMsg = ref<Record<string, { text: string; ok: boolean }>>({})
const draftOf = (s: Student) => emailDraft.value[s.student_id] ?? (s.email || '')
const dirty = (s: Student) => draftOf(s) !== (s.email || '')

function apply(s: Student) {
  const i = students.value.findIndex(x => x.student_id === s.student_id)
  if (i >= 0) students.value[i] = s
}
async function toggleMon(s: Student) {
  if (rowBusy.value[s.student_id]) return
  rowBusy.value = { ...rowBusy.value, [s.student_id]: 'toggle' }
  try { apply(await toggleMonitorStudent(s.student_id)); loadStatus() }
  catch (e: any) { alert(e.response?.data?.detail || '切换失败') }
  finally { const m = { ...rowBusy.value }; delete m[s.student_id]; rowBusy.value = m }
}
async function saveEmail(s: Student) {
  rowBusy.value = { ...rowBusy.value, [s.student_id]: 'email' }
  rowMsg.value = { ...rowMsg.value, [s.student_id]: { text: '', ok: true } }
  try {
    apply(await updateStudentEmail(s.student_id, draftOf(s)))
    rowMsg.value = { ...rowMsg.value, [s.student_id]: { text: '邮箱已保存', ok: true } }
  } catch (e: any) {
    rowMsg.value = { ...rowMsg.value, [s.student_id]: { text: e.response?.data?.detail || '保存失败', ok: false } }
  } finally { const m = { ...rowBusy.value }; delete m[s.student_id]; rowBusy.value = m }
}
async function sendTest(s: Student) {
  if (!confirm(`向 ${s.name || s.student_id} 发送测试邮件？\n\n会临时删 1~3 条本地成绩 → 跑一遍完整监控（登录教务→拉取→比对）触发一封真实通知邮件 → 随后自动恢复。\n需已设通知邮箱且已配置 SMTP。`)) return
  rowBusy.value = { ...rowBusy.value, [s.student_id]: 'test' }
  rowMsg.value = { ...rowMsg.value, [s.student_id]: { text: '发送中，约需十几秒…', ok: true } }
  try {
    const r: any = await testEmailStudent(s.student_id)
    rowMsg.value = { ...rowMsg.value, [s.student_id]: { text: r?.message || '测试邮件已发送', ok: true } }
  } catch (e: any) {
    rowMsg.value = { ...rowMsg.value, [s.student_id]: { text: e.response?.data?.detail || '测试失败', ok: false } }
  } finally { const m = { ...rowBusy.value }; delete m[s.student_id]; rowBusy.value = m }
}

const monitoredCount = computed(() => students.value.filter(s => s.is_monitored).length)

onMounted(() => {
  loadStatus(); loadSmtp(); loadLogs(); load()
  timer = setInterval(() => { loadLogs(); loadStatus() }, 6000)
})
onUnmounted(() => clearInterval(timer))
</script>

<template>
  <!-- 引擎 -->
  <section class="panel">
    <div class="p-head"><h3>监控引擎</h3><span class="p-sub">定时查成绩，有变动就发邮件</span></div>
    <div class="engine">
      <span class="state">
        <span class="dot" :class="{ live: status.running }"></span>
        {{ status.running ? '运行中' : '已停止' }}
        <span class="n">{{ status.active_students }} 人在监控</span>
      </span>
      <div class="ei">
        <label>间隔</label>
        <input v-model.number="interval" type="number" min="5" max="3600" class="num" />
        <span class="unit">秒</span>
        <span class="hint">{{ intervalHint }}</span>
      </div>
      <button class="btn" :class="status.running ? 'stop' : 'go'" :disabled="engineBusy" @click="toggleEngine">
        {{ engineBusy ? '处理中' : (status.running ? '停止' : '开启') }}
      </button>
    </div>
    <p class="foot-hint">改完间隔要停止再开启才生效。</p>
  </section>

  <!-- SMTP -->
  <section class="panel">
    <div class="p-head"><h3>发件邮箱 · SMTP</h3><span class="p-sub">通知从这个邮箱发出</span></div>
    <div class="grid">
      <div class="field"><label>SMTP 服务器</label><input v-model="smtp.smtpHost" placeholder="smtp.qq.com" /></div>
      <div class="field"><label>端口</label><input v-model="smtp.smtpPort" class="num" placeholder="587" /></div>
      <div class="field"><label>发件邮箱</label><input v-model="smtp.fromAddress" placeholder="123@qq.com" @change="smtp.smtpUsername = smtp.fromAddress" /></div>
      <div class="field"><label>登录账号</label><input v-model="smtp.smtpUsername" placeholder="同发件邮箱" /></div>
      <div class="field span2"><label>授权码（不是邮箱密码）</label><input v-model="smtp.smtpPassword" type="password" placeholder="SMTP 授权码" /></div>
    </div>
    <div class="save-row">
      <span v-if="smtpMsg" class="msg" :class="{ ok: smtpMsg.ok }">{{ smtpMsg.text }}</span>
      <button class="btn primary" :disabled="saving" @click="saveSmtp">{{ saving ? '保存中' : '保存 SMTP' }}</button>
    </div>
  </section>

  <!-- 每人监控 -->
  <section class="panel">
    <div class="p-head"><h3>每人监控</h3><span class="p-sub">{{ monitoredCount }}/{{ students.length }} 人开启 · 邮箱与测试邮件在此</span></div>
    <div v-if="!students.length" class="muted">暂无学生。到「账号管理」添加。</div>
    <div v-for="s in students" :key="s.student_id" class="mrow">
      <div class="mid">
        <span class="seal" :class="{ long: (s.name||s.student_id).slice(0,3).length > 2 }">{{ (s.name || s.student_id).slice(0, 3) }}</span>
        <div class="who"><div class="nm">{{ s.name || s.student_id }}</div><div class="sub2">{{ s.student_id }} · {{ s.grade_count }} 门</div></div>
      </div>
      <div class="mmail">
        <input :value="draftOf(s)" @input="emailDraft[s.student_id] = ($event.target as HTMLInputElement).value"
               placeholder="通知邮箱" />
        <button class="mini" :disabled="!dirty(s) || rowBusy[s.student_id] === 'email'" @click="saveEmail(s)">
          {{ rowBusy[s.student_id] === 'email' ? '…' : '保存' }}
        </button>
      </div>
      <button class="mini test" :disabled="!!rowBusy[s.student_id]" @click="sendTest(s)">
        {{ rowBusy[s.student_id] === 'test' ? '发送中' : '测试邮件' }}
      </button>
      <button class="switch" type="button" role="switch" :aria-checked="s.is_monitored"
              :class="{ on: s.is_monitored }" :disabled="!!rowBusy[s.student_id]" @click="toggleMon(s)">
        <span class="track"><span class="knob"></span></span>
        <span class="sl">{{ s.is_monitored ? '监控中' : '未监控' }}</span>
      </button>
      <p v-if="rowMsg[s.student_id]?.text" class="rowmsg" :class="{ ok: rowMsg[s.student_id]?.ok }">{{ rowMsg[s.student_id]?.text }}</p>
    </div>
  </section>

  <!-- 日志 -->
  <section class="panel">
    <button class="disc" @click="showLogs = !showLogs" :aria-expanded="showLogs">
      <svg class="caret" :class="{ open: showLogs }" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="9 18 15 12 9 6"/></svg>
      运行日志<span class="n">最近 {{ logs.length }} 条</span>
    </button>
    <div v-if="showLogs" class="log-body">
      <p v-if="!logs.length" class="muted pad">还没有记录。开启监控后每次查询都会记在这里。</p>
      <ol v-else>
        <li v-for="l in logs" :key="l.id" :class="l.status">
          <span class="tick"></span><span class="t">{{ fmtTime(l.created_at) }}</span>
          <span class="lsid">{{ l.student_id }}</span><span class="m">{{ l.message }}</span>
        </li>
      </ol>
    </div>
  </section>
</template>

<style scoped>
.panel { background: var(--white); border: 1px solid var(--ink-100); border-radius: var(--radius-md); padding: 18px 20px; margin-bottom: 16px; box-shadow: var(--shadow-sm); }
.p-head { display: flex; align-items: baseline; gap: 10px; margin-bottom: 14px; }
.p-head h3 { font-family: var(--serif); font-size: 15px; font-weight: 600; color: var(--ink-900); }
.p-sub { font-size: 12px; color: var(--ink-300); }
.muted { font-size: 13px; color: var(--ink-300); }
.muted.pad { padding: 14px 0; text-align: center; }

/* 引擎 */
.engine { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; padding: 12px 14px; background: var(--paper); border: 1px solid var(--ink-100); border-radius: var(--radius-sm); }
.state { display: flex; align-items: center; gap: 8px; font-size: 13.5px; color: var(--ink-800); }
.dot { width: 8px; height: 8px; border-radius: 50%; background: var(--ink-200); }
.dot.live { background: var(--jade); animation: breathe 2.6s ease-in-out infinite; }
@keyframes breathe { 0%,100% { box-shadow: 0 0 0 0 rgba(63,191,148,.45); } 50% { box-shadow: 0 0 0 4px rgba(63,191,148,0); } }
.n { font-size: 12px; color: var(--ink-300); font-family: var(--font-data); }
.ei { display: flex; align-items: center; gap: 7px; font-size: 13px; color: var(--ink-600); }
.ei label { font-size: 12px; color: var(--ink-500); }
.hint { font-size: 11.5px; color: var(--ink-300); }
.unit { font-size: 12.5px; color: var(--ink-300); }
.foot-hint { font-size: 11.5px; color: var(--ink-300); margin-top: 10px; }
.engine .btn { margin-left: auto; }

/* 表单 */
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.field { display: flex; flex-direction: column; gap: 5px; }
.field.span2 { grid-column: 1 / -1; }
label { font-size: 12px; color: var(--ink-600); font-weight: 500; }
input { padding: 8px 10px; border: 1px solid var(--ink-100); border-radius: var(--radius-sm); font-size: 13px; font-family: inherit; color: var(--ink-900); background: var(--white); outline: none; transition: border-color var(--transition); }
input:focus { border-color: var(--ink-600); }
input.num { font-family: var(--font-data); width: 76px; text-align: center; }
.save-row { display: flex; align-items: center; justify-content: flex-end; gap: 12px; margin-top: 14px; }
.msg { font-size: 12.5px; color: var(--cinnabar); }
.msg.ok { color: var(--jade); }

/* 按钮 */
.btn { padding: 7px 16px; border-radius: var(--radius-sm); font-size: 13px; font-weight: 500; font-family: inherit; cursor: pointer; white-space: nowrap; transition: background var(--transition), opacity var(--transition); }
.btn:disabled { opacity: .55; cursor: progress; }
.btn.go { background: var(--jade); color: #fff; }
.btn.stop { background: var(--white); color: var(--cinnabar); border: 1px solid var(--cinnabar); }
.btn.primary { background: var(--ink-900); color: var(--paper); }
.btn.primary:hover:not(:disabled) { background: var(--ink-700); }

/* 每人一行 */
.mrow { display: grid; grid-template-columns: minmax(150px, 1fr) minmax(220px, 1.4fr) auto auto; align-items: center; gap: 14px; padding: 12px 2px; border-top: 1px solid var(--ink-50); }
.mrow:first-of-type { border-top: none; }
.mid { display: flex; align-items: center; gap: 10px; min-width: 0; }
.seal { width: 34px; height: 34px; flex-shrink: 0; border-radius: 4px; background: var(--cinnabar); color: #fff; display: flex; align-items: center; justify-content: center; font-family: var(--serif); font-size: 13px; font-weight: 600; box-shadow: inset 0 0 0 1px rgba(255,255,255,.3); }
.seal.long { font-size: 11px; }
.who { min-width: 0; }
.nm { font-size: 14px; font-weight: 600; color: var(--ink-900); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.sub2 { font-size: 11.5px; color: var(--ink-300); font-family: var(--font-data); }
.mmail { display: flex; gap: 7px; }
.mmail input { flex: 1; min-width: 0; }
.mini { padding: 7px 12px; font-size: 12px; background: var(--paper-dim); color: var(--ink-700); border: 1px solid var(--ink-100); border-radius: var(--radius-sm); cursor: pointer; white-space: nowrap; }
.mini:hover:not(:disabled) { border-color: var(--ink-300); color: var(--ink-900); }
.mini:disabled { opacity: .45; cursor: not-allowed; }
.mini.test:hover:not(:disabled) { border-color: var(--gold); color: var(--gold); }
.rowmsg { grid-column: 1 / -1; font-size: 12px; color: var(--cinnabar); margin: -2px 0 2px; }
.rowmsg.ok { color: var(--jade); }

/* 开关 */
.switch { display: flex; align-items: center; gap: 7px; background: none; border: none; cursor: pointer; font-family: inherit; font-size: 12px; color: var(--ink-300); }
.switch:disabled { opacity: .5; cursor: progress; }
.track { position: relative; width: 34px; height: 18px; border-radius: 9px; background: var(--ink-100); transition: background var(--transition); flex-shrink: 0; }
.knob { position: absolute; top: 2px; left: 2px; width: 14px; height: 14px; border-radius: 50%; background: #fff; box-shadow: var(--shadow-sm); transition: transform var(--transition); }
.switch.on .track { background: var(--jade); }
.switch.on .knob { transform: translateX(16px); }
.switch.on .sl { color: var(--jade); font-weight: 500; }

/* 日志 */
.disc { display: flex; align-items: center; gap: 7px; width: 100%; padding: 0; background: none; border: none; font-family: var(--serif); font-size: 15px; font-weight: 600; color: var(--ink-900); cursor: pointer; }
.caret { color: var(--ink-300); transition: transform var(--transition); }
.caret.open { transform: rotate(90deg); }
.disc .n { margin-left: auto; font-weight: 400; font-family: var(--font-data); }
.log-body { max-height: 220px; overflow-y: auto; margin-top: 12px; }
.log-body ol { list-style: none; }
.log-body li { display: flex; align-items: baseline; gap: 9px; padding: 5px 0; border-bottom: 1px solid var(--paper-dim); font-size: 12px; color: var(--ink-600); }
.log-body li:last-child { border-bottom: 0; }
.tick { width: 3px; height: 12px; border-radius: 2px; background: var(--ink-200); flex-shrink: 0; }
li.ok .tick { background: var(--jade); }
li.fail .tick { background: var(--cinnabar); }
li.fail .m { color: var(--cinnabar); }
.t { font-family: var(--font-data); color: var(--ink-300); flex-shrink: 0; }
.lsid { font-family: var(--font-data); color: var(--ink-600); flex-shrink: 0; }
.m { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

@media (prefers-reduced-motion: reduce) { .dot.live { animation: none; } .caret, .knob, .track { transition: none; } }
@media (max-width: 760px) {
  .mrow { grid-template-columns: 1fr; gap: 8px; }
  .engine { gap: 12px; } .engine .btn { margin-left: 0; }
}
</style>
