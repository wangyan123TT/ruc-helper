<script setup lang="ts">
import { ref } from 'vue'
import { addStudent } from '../api'

const emit = defineEmits<{ close: []; added: [] }>()

const studentId = ref('')
const password = ref('')
const email = ref('')
const error = ref('')
const submitting = ref(false)

async function submit() {
  error.value = ''
  if (!studentId.value || !password.value) {
    error.value = '请填写学号和密码'
    return
  }
  submitting.value = true
  try {
    await addStudent({
      student_id: studentId.value,
      password: password.value,
      email: email.value,
    })
    emit('added')
  } catch (e: any) {
    error.value = e.response?.data?.detail || '添加失败，请检查学号密码是否正确'
  }
  submitting.value = false
}
</script>

<template>
  <div class="overlay" @click.self="emit('close')">
    <div class="dialog">
      <button class="btn-close" @click="emit('close')">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
      </button>

      <div class="dialog-icon">◈</div>
      <h3>添加学生</h3>
      <p class="subtitle">输入学号和微人大密码，系统将自动验证登录</p>

      <div class="field">
        <label>学号</label>
        <input
          v-model="studentId"
          placeholder="10 位学号"
          @keyup.enter="submit"
          autofocus
        />
      </div>

      <div class="field">
        <label>微人大密码</label>
        <input
          v-model="password"
          type="password"
          placeholder="输入密码"
          @keyup.enter="submit"
        />
      </div>

      <div class="field">
        <label>通知邮箱（选填）</label>
        <input
          v-model="email"
          type="email"
          placeholder="成绩变动通知，如 123@qq.com"
          @keyup.enter="submit"
        />
      </div>

      <div class="field hint">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
        <span>密码仅用于获取成绩查询凭证，加密存储</span>
      </div>

      <p v-if="error" class="error-msg">{{ error }}</p>

      <button
        class="btn-submit"
        :disabled="submitting"
        @click="submit"
      >
        <span v-if="submitting" class="btn-spinner"></span>
        {{ submitting ? '验证中...' : '验证并添加' }}
      </button>
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
  animation: fadeIn 0.2s ease;
}
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }

.dialog {
  background: var(--white);
  border-radius: var(--radius-lg);
  padding: 36px 32px 28px;
  width: 420px;
  position: relative;
  box-shadow: var(--shadow-lg);
  animation: slideUp 0.3s ease;
}
@keyframes slideUp {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

.btn-close {
  position: absolute;
  top: 14px;
  right: 14px;
  background: none;
  color: var(--ink-300);
  padding: 4px;
  border-radius: var(--radius-sm);
}
.btn-close:hover { color: var(--ink-600); background: var(--paper-dim); }

.dialog-icon {
  font-size: 28px;
  color: var(--gold);
  margin-bottom: 8px;
}
.dialog h3 {
  font-size: 20px;
  font-weight: 600;
  color: var(--ink-900);
  margin-bottom: 4px;
}
.subtitle {
  font-size: 13px;
  color: var(--ink-300);
  margin-bottom: 24px;
}

.field {
  margin-bottom: 16px;
}
.field label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: var(--ink-600);
  margin-bottom: 6px;
}
.field input {
  width: 100%;
  padding: 10px 14px;
  border: 1.5px solid var(--ink-100);
  border-radius: var(--radius-sm);
  font-size: 14px;
  color: var(--ink-900);
  background: var(--paper);
}
.field input:focus {
  border-color: var(--ink-600);
  background: var(--white);
}
.field input::placeholder {
  color: var(--ink-200);
}

.field.hint {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--ink-300);
  margin-bottom: 20px;
}
.field.hint svg {
  flex-shrink: 0;
  color: var(--ink-200);
}

.error-msg {
  color: var(--cinnabar);
  font-size: 13px;
  margin-bottom: 12px;
  padding: 8px 12px;
  background: var(--cinnabar-light);
  border-radius: var(--radius-sm);
}

.btn-submit {
  width: 100%;
  padding: 11px;
  background: var(--ink-900);
  color: var(--paper);
  border-radius: var(--radius-sm);
  font-size: 15px;
  font-weight: 500;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}
.btn-submit:hover { background: var(--ink-800); }
.btn-submit:disabled { opacity: 0.6; cursor: not-allowed; }

.btn-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
