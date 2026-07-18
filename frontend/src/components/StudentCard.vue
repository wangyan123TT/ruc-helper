<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import type { Student } from '../types'

const props = defineProps<{ student: Student; busy?: boolean }>()
const emit = defineEmits<{ (e: 'toggle-monitor', s: Student): void }>()
const router = useRouter()

const seal = computed(() => (props.student.name || props.student.student_id).slice(0, 3))
const displayName = computed(() => props.student.name || props.student.student_id)

function open() {
  router.push(`/student/${props.student.student_id}`)
}
</script>

<template>
  <div class="card">
    <div class="main" role="button" tabindex="0" @click="open" @keydown.enter="open"
         :aria-label="`打开 ${displayName} 的档案`">
      <span class="seal" :class="{ long: seal.length > 2 }" aria-hidden="true">{{ seal }}</span>
      <span class="identity">
        <span class="name">{{ displayName }}</span>
        <span class="sid">{{ student.student_id }}</span>
      </span>
      <span class="meta">
        <span v-if="student.major" class="major">{{ student.major }}</span>
        <span v-if="student.grade" class="year">{{ student.grade }} 级</span>
      </span>
    </div>

    <div class="foot">
      <span class="count"><b>{{ student.grade_count }}</b> 门成绩</span>

      <!-- 监控开关：管理员切换该学生是否被后台监控 -->
      <button class="switch" type="button" role="switch"
              :aria-checked="student.is_monitored" :class="{ on: student.is_monitored }"
              :disabled="busy" @click.stop="emit('toggle-monitor', student)">
        <span class="track"><span class="knob"></span></span>
        <span class="switch-label">{{ student.is_monitored ? '监控中' : '未监控' }}</span>
      </button>

      <button class="go-btn" type="button" @click="open" aria-label="查看档案">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="9 18 15 12 9 6"/></svg>
      </button>
    </div>
  </div>
</template>

<style scoped>
.card {
  width: 100%;
  padding: 20px;
  text-align: left;
  background: var(--white);
  border: 1px solid var(--ink-100);
  border-radius: var(--radius-md);
  font-family: inherit;
  transition: border-color var(--transition), box-shadow var(--transition);
}
.card:hover {
  border-color: var(--ink-200);
  box-shadow: var(--shadow-md);
}
.main {
  display: grid;
  grid-template-columns: auto 1fr;
  grid-template-areas: 'seal identity' 'seal meta';
  align-items: start;
  column-gap: 16px;
  row-gap: 4px;
  cursor: pointer;
  border-radius: var(--radius-sm);
}
.main:focus-visible {
  outline: 2px solid var(--cinnabar);
  outline-offset: 2px;
}

/* 朱砂印 —— 中文文书用印章标识"这是谁的" */
.seal {
  grid-area: seal;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  border-radius: 3px;
  background: var(--cinnabar);
  color: #fff;
  font-size: 15px;
  font-weight: 500;
  letter-spacing: 0.08em;
  text-indent: 0.08em;          /* 抵消末字右侧字距，视觉居中 */
  /* 内圈细框，模仿印章的边阑 */
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.35);
  flex-shrink: 0;
}
.seal.long { font-size: 13px; letter-spacing: 0.02em; text-indent: 0.02em; }

.identity { grid-area: identity; display: flex; flex-direction: column; gap: 2px; }
.name {
  font-size: 17px;
  font-weight: 600;
  color: var(--ink-900);
  line-height: 1.3;
}
.sid {
  font-family: var(--font-data);
  font-size: 12px;
  color: var(--ink-300);
  letter-spacing: 0.02em;
}

.meta {
  grid-area: meta;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  font-size: 12.5px;
  color: var(--ink-600);
}
.year {
  font-family: var(--font-data);
  color: var(--ink-300);
}
.major + .year::before {
  content: '·';
  margin-right: 8px;
  color: var(--ink-200);
}

.foot {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid var(--paper-dim);
  font-size: 12.5px;
  color: var(--ink-300);
}
.count { flex-shrink: 0; }
.count b {
  font-family: var(--font-data);
  font-size: 15px;
  font-weight: 600;
  color: var(--ink-800);
  margin-right: 3px;
}

/* 监控开关 */
.switch {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 7px;
  background: none;
  cursor: pointer;
  font-family: inherit;
  font-size: 12px;
  color: var(--ink-300);
}
.switch:disabled { opacity: .5; cursor: progress; }
.track {
  position: relative;
  width: 34px;
  height: 18px;
  border-radius: 9px;
  background: var(--ink-100);
  transition: background var(--transition);
  flex-shrink: 0;
}
.knob {
  position: absolute;
  top: 2px; left: 2px;
  width: 14px; height: 14px;
  border-radius: 50%;
  background: #fff;
  box-shadow: var(--shadow-sm);
  transition: transform var(--transition);
}
.switch.on .track { background: var(--jade); }
.switch.on .knob { transform: translateX(16px); }
.switch.on .switch-label { color: var(--jade); font-weight: 500; }

.go-btn {
  background: none;
  cursor: pointer;
  color: var(--ink-200);
  display: flex;
  padding: 2px;
  transition: color var(--transition);
}
.go-btn:hover { color: var(--cinnabar); }

@media (prefers-reduced-motion: reduce) {
  .card, .knob { transition: none; }
}
</style>
