<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import axios from 'axios'
import { getMonitorStatus, startMonitor, stopMonitor } from '../api'
import type { MonitorStatus } from '../types'

// 操作面：后台轮询 + 发件邮箱 + 运行日志。
// 首页只管认人，这些不该摆在那儿。
const emit = defineEmits<{ close: [] }>()

// ── 监控 ──
const status = ref<MonitorStatus>({ running: false, poll_interval: 30, active_students: 0 })
const interval = ref(30)
const busy = ref(false)

async function refreshStatus() {
  try {
    status.value = await getMonitorStatus()
    interval.value = status.value.poll_interval || 30
  } catch (_) { /* ignore */ }
}

async function toggleMonitor() {
  busy.value = true
  try {
    if (status.value.running) await stopMonitor()
    else await startMonitor(interval.value)
    await refreshStatus()
  } catch (e: any) {
    smtpMsg.value = { text: '操作失败：' + (e.response?.data?.detail || e.message), ok: false }
  }
  busy.value = false
}

// ── 日志 ──
interface LogEntry { id: number; student_id: string; status: string; message: string; created_at: string }
const logs = ref<LogEntry[]>([])
const showLogs = ref(false)
let timer: any = null

async function fetchLogs() {
  try {
    logs.value = (await axios.get('/api/monitor/logs')).data
  } catch (_) { /* ignore */ }
}

// ── 邮件 ──
const form = ref({
  smtpHost: 'smtp.qq.com',
  smtpPort: '587',
  smtpUsername: '',
  smtpPassword: '',
  fromAddress: '',
})
const saving = ref(false)
const smtpMsg = ref<{ text: string; ok: boolean } | null>(null)

async function loadSmtp() {
  try {
    form.value = (await axios.get('/api/settings/smtp')).data
  } catch (_) { /* 用默认值 */ }
}

async function saveSmtp() {
  saving.value = true
  smtpMsg.value = null
  try {
    const data: Record<string, string> = {}
    for (const [k, v] of Object.entries(form.value)) {
      if (k === 'smtpPassword' && v && v.includes('****')) continue  // 脱敏值不回传
      data[k] = v || ''
    }
    await axios.put(`/api/settings/smtp?${new URLSearchParams(data)}`)
    smtpMsg.value = { text: '已保存', ok: true }
  } catch (e: any) {
    smtpMsg.value = { text: '保存失败：' + (e.response?.data?.detail || e.message), ok: false }
  }
  saving.value = false
}

const intervalHint = computed(() => {
  const s = interval.value
  if (!s || s < 5) return ''
  return s >= 60 ? `每 ${(s / 60).toFixed(s % 60 ? 1 : 0)} 分钟查一次` : `每 ${s} 秒查一次`
})

onMounted(() => {
  refreshStatus()
  loadSmtp()
  fetchLogs()
  timer = setInterval(fetchLogs, 5000)
})
onUnmounted(() => clearInterval(timer))

function fmtTime(t: string) { return t ? t.substring(11, 19) : '' }
</script>

<template>
  <div class="overlay" @click.self="emit('close')">
    <div class="dialog" role="dialog" aria-labelledby="settings-title">
      <header class="head">
        <h2 id="settings-title">设置</h2>
        <button class="btn-close" @click="emit('close')" aria-label="关闭">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
        </button>
      </header>

      <div class="body">
        <!-- ── 后台监控 ── -->
        <section>
          <h3>后台监控</h3>
          <p class="sub">开启后定时查询成绩，发现变动就发邮件通知。</p>

          <div class="row">
            <span class="state">
              <span class="dot" :class="{ live: status.running }"></span>
              {{ status.running ? '运行中' : '已停止' }}
              <span class="n">{{ status.active_students }} 人在监控</span>
            </span>
            <button class="btn" :class="status.running ? 'stop' : 'go'"
                    :disabled="busy" @click="toggleMonitor">
              {{ busy ? '处理中' : (status.running ? '停止监控' : '开启监控') }}
            </button>
          </div>

          <div class="field inline">
            <label for="iv">查询间隔</label>
            <input id="iv" v-model.number="interval" type="number" min="5" max="3600" class="num" />
            <span class="unit">秒</span>
            <span class="hint-inline">{{ intervalHint }}</span>
          </div>
          <p class="hint">改完间隔要停止再开启才生效。</p>
        </section>

        <!-- ── 发件邮箱 ── -->
        <section>
          <h3>发件邮箱</h3>
          <p class="sub">成绩变动通知从这个邮箱发出。每个学生的收件地址在各自的档案里设。</p>

          <div class="grid">
            <div class="field">
              <label for="h">SMTP 服务器</label>
              <input id="h" v-model="form.smtpHost" placeholder="smtp.qq.com" />
            </div>
            <div class="field">
              <label for="p">端口</label>
              <input id="p" v-model="form.smtpPort" class="num" placeholder="587" />
            </div>
            <div class="field">
              <label for="f">发件邮箱</label>
              <input id="f" v-model="form.fromAddress" placeholder="123@qq.com"
                     @change="form.smtpUsername = form.fromAddress" />
            </div>
            <div class="field">
              <label for="u">登录账号</label>
              <input id="u" v-model="form.smtpUsername" placeholder="同发件邮箱" />
            </div>
            <div class="field span2">
              <label for="pw">授权码</label>
              <input id="pw" v-model="form.smtpPassword" type="password" placeholder="不是邮箱密码" />
            </div>
          </div>
          <p class="hint">QQ 邮箱的授权码在：设置 → 账户 → POP3/SMTP 服务 → 生成授权码。</p>

          <p v-if="smtpMsg" class="msg" :class="{ ok: smtpMsg.ok }">{{ smtpMsg.text }}</p>
          <button class="btn primary wide" :disabled="saving" @click="saveSmtp">
            {{ saving ? '保存中' : '保存邮箱设置' }}
          </button>
        </section>

        <!-- ── 运行日志 ── -->
        <section class="logs">
          <button class="disclosure" @click="showLogs = !showLogs" :aria-expanded="showLogs">
            <svg class="caret" :class="{ open: showLogs }" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="9 18 15 12 9 6"/></svg>
            运行日志
            <span class="n">最近 {{ logs.length }} 条</span>
          </button>

          <div v-if="showLogs" class="log-body">
            <p v-if="!logs.length" class="hint pad">还没有记录。开启监控后，每次查询都会记在这里。</p>
            <ol v-else>
              <li v-for="l in logs" :key="l.id" :class="l.status">
                <span class="tick" aria-hidden="true"></span>
                <span class="t">{{ fmtTime(l.created_at) }}</span>
                <span class="sid">{{ l.student_id }}</span>
                <span class="m">{{ l.message }}</span>
              </li>
            </ol>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>

<style scoped>
.overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 15, 35, 0.5);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  padding: 20px;
}
.dialog {
  background: var(--white);
  border-radius: var(--radius-lg);
  width: 480px;
  max-width: 100%;
  max-height: 88vh;
  display: flex;
  flex-direction: column;
  box-shadow: var(--shadow-lg);
}

.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 22px;
  border-bottom: 1px solid var(--ink-100);
  flex-shrink: 0;
}
.head h2 { font-size: 16px; font-weight: 600; color: var(--ink-900); }
.btn-close {
  display: flex;
  padding: 5px;
  background: none;
  color: var(--ink-300);
  border-radius: var(--radius-sm);
  cursor: pointer;
}
.btn-close:hover { background: var(--paper-dim); color: var(--ink-800); }

.body { overflow-y: auto; padding: 4px 22px 22px; }
section { padding: 18px 0; border-bottom: 1px solid var(--paper-dim); }
section:last-child { border-bottom: 0; padding-bottom: 4px; }
h3 { font-size: 14px; font-weight: 600; color: var(--ink-900); }
.sub { font-size: 12.5px; color: var(--ink-300); margin: 3px 0 14px; line-height: 1.5; }

/* 监控状态 */
.row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 11px 14px;
  background: var(--paper);
  border: 1px solid var(--ink-100);
  border-radius: var(--radius-sm);
  margin-bottom: 14px;
}
.state { display: flex; align-items: center; gap: 8px; font-size: 13.5px; color: var(--ink-800); }
.dot { width: 7px; height: 7px; border-radius: 50%; background: var(--ink-200); flex-shrink: 0; }
.dot.live {
  background: var(--jade);
  animation: breathe 2.6s ease-in-out infinite;
}
@keyframes breathe {
  0%, 100% { box-shadow: 0 0 0 0 rgba(26, 122, 90, 0.45); }
  50% { box-shadow: 0 0 0 4px rgba(26, 122, 90, 0); }
}
.n { font-size: 12px; color: var(--ink-300); font-family: var(--font-data); }

/* 表单 */
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.field { display: flex; flex-direction: column; gap: 5px; }
.field.span2 { grid-column: 1 / -1; }
.field.inline { flex-direction: row; align-items: center; gap: 8px; }
label { font-size: 12px; color: var(--ink-600); font-weight: 500; }
input {
  padding: 8px 10px;
  border: 1px solid var(--ink-100);
  border-radius: var(--radius-sm);
  font-size: 13px;
  font-family: inherit;
  color: var(--ink-900);
  background: var(--white);
  outline: none;
  transition: border-color var(--transition);
}
input:focus { border-color: var(--ink-600); }
input.num { font-family: var(--font-data); }
.field.inline .num { width: 72px; text-align: center; }
.unit { font-size: 12.5px; color: var(--ink-300); }
.hint-inline { font-size: 12px; color: var(--ink-300); margin-left: 2px; }
.hint { font-size: 11.5px; color: var(--ink-300); margin-top: 10px; line-height: 1.5; }
.hint.pad { padding: 16px 0; text-align: center; }

/* 按钮 */
.btn {
  padding: 7px 15px;
  border-radius: var(--radius-sm);
  font-size: 13px;
  font-weight: 500;
  font-family: inherit;
  cursor: pointer;
  white-space: nowrap;
  transition: background var(--transition), opacity var(--transition);
}
.btn:disabled { opacity: 0.55; cursor: progress; }
.btn.go { background: var(--jade); color: #fff; }
.btn.go:hover:not(:disabled) { background: #16704f; }
.btn.stop { background: var(--white); color: var(--cinnabar); border: 1px solid var(--cinnabar); }
.btn.stop:hover:not(:disabled) { background: var(--cinnabar-light); }
.btn.primary { background: var(--ink-900); color: #fff; }
.btn.primary:hover:not(:disabled) { background: var(--ink-700); }
.btn.wide { width: 100%; padding: 10px; margin-top: 12px; }

.msg { margin-top: 12px; font-size: 12.5px; color: var(--cinnabar); }
.msg.ok { color: var(--jade); }

/* 日志 */
.disclosure {
  display: flex;
  align-items: center;
  gap: 7px;
  width: 100%;
  padding: 0;
  background: none;
  font-size: 14px;
  font-weight: 600;
  font-family: inherit;
  color: var(--ink-900);
  cursor: pointer;
}
.caret { color: var(--ink-300); transition: transform var(--transition); flex-shrink: 0; }
.caret.open { transform: rotate(90deg); }
.disclosure .n { margin-left: auto; font-weight: 400; }

.log-body { max-height: 190px; overflow-y: auto; margin-top: 10px; }
.log-body ol { list-style: none; }
.log-body li {
  display: flex;
  align-items: baseline;
  gap: 9px;
  padding: 5px 0;
  border-bottom: 1px solid var(--paper-dim);
  font-size: 12px;
  color: var(--ink-600);
}
.log-body li:last-child { border-bottom: 0; }
/* 状态用色条编码，不用 emoji */
.tick { width: 3px; height: 12px; border-radius: 2px; background: var(--ink-200); flex-shrink: 0; }
li.ok .tick { background: var(--jade); }
li.fail .tick { background: var(--cinnabar); }
li.fail .m { color: var(--cinnabar); }
.t { font-family: var(--font-data); color: var(--ink-300); flex-shrink: 0; }
.sid { font-family: var(--font-data); color: var(--ink-600); flex-shrink: 0; }
.m { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

@media (prefers-reduced-motion: reduce) {
  .dot.live { animation: none; }
  .caret { transition: none; }
}
@media (max-width: 520px) {
  .grid { grid-template-columns: 1fr; }
}
</style>
