<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { login, setToken, getToken } from '../api'

const router = useRouter()
const sid = ref('')
const pwd = ref('')
const loading = ref(false)
const err = ref('')

onMounted(() => {
  if (getToken()) router.replace('/')   // 已登录直接进
})

async function submit() {
  err.value = ''
  if (!sid.value.trim() || !pwd.value) { err.value = '请输入学号和密码'; return }
  loading.value = true
  try {
    const r = await login(sid.value.trim(), pwd.value)
    setToken(r.token)
    router.replace(r.is_admin ? '/admin' : '/me')
  } catch (e: any) {
    err.value = e.response?.data?.detail || e.message || '登录失败'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-box">
      <div class="brand">
        <div class="seal">RUC</div>
        <h1>微人大选课助手</h1>
        <p>用学号和密码登录，只查看你自己的内容</p>
      </div>

      <form @submit.prevent="submit" autocomplete="off">
        <label>
          <span>学号</span>
          <input v-model="sid" inputmode="numeric" placeholder="10 位学号"
                 autocomplete="username" autofocus>
        </label>
        <label>
          <span>密码</span>
          <input v-model="pwd" type="password" placeholder="微人大密码"
                 autocomplete="current-password">
        </label>
        <div v-if="err" class="err">{{ err }}</div>
        <button type="submit" :disabled="loading">
          {{ loading ? '登录教务验证中…（约 5 秒）' : '登录' }}
        </button>
      </form>

      <p class="note">
        登录会用你的密码在教务系统验证一次。仅限已开通的账号；密码不会展示给他人，
        每人只能看到自己的成绩、课表与抢课。
      </p>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--paper);
  padding: 20px;
}
.login-box {
  width: 100%;
  max-width: 380px;
  background: var(--white);
  border: 1px solid var(--ink-100);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  padding: 32px 28px;
}
.brand { text-align: center; margin-bottom: 24px; }
.seal {
  width: 52px; height: 52px; margin: 0 auto 12px;
  background: var(--cinnabar); color: #fff;
  border-radius: 8px; display: flex; align-items: center; justify-content: center;
  font-weight: 700; font-size: 16px; letter-spacing: 1px;
  box-shadow: inset 0 0 0 2px rgba(255,255,255,.35);
}
.brand h1 { font-size: 19px; font-weight: 600; color: var(--ink-900); }
.brand p { font-size: 12.5px; color: var(--ink-300); margin-top: 6px; }

form { display: flex; flex-direction: column; gap: 14px; }
label { display: flex; flex-direction: column; gap: 5px; }
label span { font-size: 12.5px; color: var(--ink-600); font-weight: 500; }
input {
  padding: 10px 12px; font-size: 15px; font-family: var(--font);
  border: 1px solid var(--ink-100); border-radius: var(--radius-sm);
  background: var(--paper); color: var(--ink-900);
}
input:focus { outline: 2px solid var(--jade); outline-offset: 1px; border-color: transparent; }
.err {
  font-size: 12.5px; color: var(--cinnabar);
  background: var(--cinnabar-light); border-radius: var(--radius-sm);
  padding: 8px 11px;
}
button {
  margin-top: 4px; padding: 11px; font-size: 15px; font-weight: 500;
  background: var(--ink-900); color: var(--paper); border-radius: var(--radius-sm);
  cursor: pointer;
}
button:hover { background: var(--ink-700); }
button:disabled { opacity: .6; cursor: progress; }
.note {
  margin-top: 18px; font-size: 11.5px; color: var(--ink-300); line-height: 1.7;
}
</style>
