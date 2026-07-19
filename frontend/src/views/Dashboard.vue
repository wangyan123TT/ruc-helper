<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { logout, clearToken } from '../api'
import { useStudents } from '../composables/useStudents'
import SideNav from '../components/SideNav.vue'
import AccountsView from '../components/admin/AccountsView.vue'
import MonitorView from '../components/admin/MonitorView.vue'
import DataView from '../components/admin/DataView.vue'

// 管理台 = 薄外壳。三块各自成视图：账号管理 / 成绩监控 / 数据管理。
const router = useRouter()
const { students } = useStudents()

type Nav = 'accounts' | 'monitor' | 'data'
const nav = ref<Nav>('accounts')
const NAV_TITLE: Record<Nav, string> = { accounts: '账号管理', monitor: '成绩监控', data: '数据管理' }

const identity = { seal: '管', name: '管理员', sub: '微人大选课助手 · admin' }
const navGroups = computed(() => [
  {
    label: '管理台', items: [
      { key: 'accounts', label: '账号管理', icon: 'roster', count: students.value.length || null },
      { key: 'monitor', label: '成绩监控', icon: 'bell' },
      { key: 'data', label: '数据管理', icon: 'data' },
    ],
  },
])
const footer = [{ key: 'logout', label: '退出登录', icon: 'logout', danger: true }]

function switchNav(k: string) { nav.value = k as Nav }
function onFoot(k: string) { if (k === 'logout') doLogout() }
async function doLogout() { await logout(); clearToken(); router.replace('/login') }
</script>

<template>
  <div class="shell">
    <SideNav
      glyph="管" brand-title="管理台" brand-sub="微人大 · RUC"
      :identity="identity" :groups="navGroups" :active="nav" :footer="footer"
      @select="switchNav" @foot="onFoot" />

    <div class="main">
      <div class="main-head">
        <h1>{{ NAV_TITLE[nav] }}</h1>
        <span class="crumb">管理员</span>
      </div>
      <div class="body">
        <AccountsView v-if="nav === 'accounts'" />
        <MonitorView v-else-if="nav === 'monitor'" />
        <DataView v-else-if="nav === 'data'" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.shell { display: flex; min-height: 100vh; background: var(--paper); }
.main { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.main-head { position: sticky; top: 0; z-index: 20;
  background: color-mix(in srgb, var(--paper) 88%, transparent); backdrop-filter: blur(8px);
  border-bottom: 1px solid var(--ink-100); padding: 15px 38px; display: flex; align-items: baseline; gap: 12px; }
.main-head h1 { font-family: var(--serif); font-size: 21px; font-weight: 600; color: var(--ink-900); }
.main-head .crumb { font-size: 12px; color: var(--ink-300); }
.body { padding: 28px 40px 70px; max-width: 1280px; width: 100%; margin: 0 auto; }
@media (max-width: 820px) {
  .shell { flex-direction: column; }
  .main-head { padding: 12px 16px; }
  .body { padding: 20px 16px 60px; }
}
</style>
