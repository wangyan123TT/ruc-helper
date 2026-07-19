<script setup lang="ts">
// 预选课表 / 已选课表 合并成一个组件，kind 区分文案与空状态。
// 数据由外壳的 useTimetable 传入（保缓存），本组件只负责呈现 + 抛「重新抓取」。
import type { TimetableData } from '../types'
import TimetableGrid from './TimetableGrid.vue'

const props = defineProps<{
  kind: 'preselect' | 'enrolled'
  data: TimetableData | null
  loading: boolean
  error: string
}>()
defineEmits<{ (e: 'refresh'): void }>()

const LABEL = {
  preselect: { title: '待筛选志愿课表', hint: '正在登录教务系统抓取待筛选志愿，约需 5 秒…' },
  enrolled: { title: '已选课程表 · 只含选课状态为「通过」的课', hint: '正在查询选课结果，约需 5 秒…' },
}
const meta = () => LABEL[props.kind]
</script>

<template>
  <div class="tt-actions">
    <span class="tt-title">{{ data ? (data.context.hd_name || meta().title) : meta().title }}</span>
    <button class="btn-dark" :disabled="loading" @click="$emit('refresh')">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" :class="{ spin: loading }">
        <polyline points="23 4 23 10 17 10" /><path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
      </svg>
      {{ loading ? '抓取中' : '重新抓取' }}
    </button>
  </div>

  <div v-if="loading" class="state">
    <div class="spinner"></div>
    <p class="hint">{{ meta().hint }}</p>
  </div>

  <div v-else-if="error" class="banner err">
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" /></svg>
    {{ error }}
  </div>

  <div v-else-if="kind === 'enrolled' && data && data.n_courses === 0" class="banner">
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10" /><path d="M12 8v4M12 16h.01" /></svg>
    暂无已选上的课。当前志愿仍在「待筛选」，筛选结果公布后通过的课会出现在这里。
  </div>

  <TimetableGrid v-else-if="data" :data="data" />
</template>

<style scoped>
.tt-actions { display: flex; align-items: center; gap: 12px; margin-bottom: 18px; font-size: 13px; color: var(--ink-500); }
.tt-title { flex: 1; }
.btn-dark { display: flex; align-items: center; gap: 5px; padding: 8px 15px; background: var(--ink-900); color: var(--paper); border-radius: var(--radius-sm); font-size: 13px; }
.btn-dark:hover:not(:disabled) { background: var(--ink-700); }
.btn-dark:disabled { opacity: .6; cursor: not-allowed; }
.spin { animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

.state { text-align: center; padding: 70px 20px; }
.spinner { width: 28px; height: 28px; border: 3px solid var(--ink-100); border-top-color: var(--ink-600); border-radius: 50%; animation: spin .8s linear infinite; margin: 0 auto; }
.hint { margin-top: 12px; font-size: 13px; color: var(--ink-300); }

.banner { display: flex; align-items: center; gap: 8px; padding: 11px 16px; background: var(--jade-light); border: 1px solid var(--jade); border-radius: var(--radius-sm); font-size: 13px; color: var(--ink-700); }
.banner svg { color: var(--jade); flex-shrink: 0; }
.banner.err { background: var(--cinnabar-light); border-color: var(--cinnabar); }
.banner.err svg { color: var(--cinnabar); }

@media (prefers-reduced-motion: reduce) { .spin, .spinner { animation-duration: 2s; } }
</style>
