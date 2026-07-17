<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import type { Student } from '../types'

const props = defineProps<{ student: Student }>()
const router = useRouter()

// 首页只负责认人。监控开关/邮件/删除都在学生详情页。
const seal = computed(() => (props.student.name || props.student.student_id).slice(0, 3))
const displayName = computed(() => props.student.name || props.student.student_id)

function open() {
  router.push(`/student/${props.student.student_id}`)
}
</script>

<template>
  <button class="card" type="button" @click="open" :aria-label="`打开 ${displayName} 的档案`">
    <span class="seal" :class="{ long: seal.length > 2 }" aria-hidden="true">{{ seal }}</span>

    <span class="identity">
      <span class="name">{{ displayName }}</span>
      <span class="sid">{{ student.student_id }}</span>
    </span>

    <span class="meta">
      <span v-if="student.major" class="major">{{ student.major }}</span>
      <span v-if="student.grade" class="year">{{ student.grade }} 级</span>
    </span>

    <span class="foot">
      <span class="count"><b>{{ student.grade_count }}</b> 门成绩</span>
      <span class="go" aria-hidden="true">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="9 18 15 12 9 6"/></svg>
      </span>
    </span>
  </button>
</template>

<style scoped>
.card {
  display: grid;
  grid-template-columns: auto 1fr;
  grid-template-areas:
    'seal identity'
    'seal meta'
    'foot foot';
  align-items: start;
  column-gap: 16px;
  row-gap: 4px;
  width: 100%;
  padding: 20px;
  text-align: left;
  background: var(--white);
  border: 1px solid var(--ink-100);
  border-radius: var(--radius-md);
  cursor: pointer;
  font-family: inherit;
  transition: border-color var(--transition), box-shadow var(--transition),
              transform var(--transition);
}
.card:hover {
  border-color: var(--ink-200);
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}
.card:focus-visible {
  outline: 2px solid var(--cinnabar);
  outline-offset: 2px;
}

/* 朱砂印 —— 中文文书用印章标识"这是谁的"，正是这一页的职责 */
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
  grid-area: foot;
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid var(--paper-dim);
  font-size: 12.5px;
  color: var(--ink-300);
}
.count b {
  font-family: var(--font-data);
  font-size: 15px;
  font-weight: 600;
  color: var(--ink-800);
  margin-right: 3px;
}
.go { color: var(--ink-200); display: flex; transition: color var(--transition), transform var(--transition); }
.card:hover .go { color: var(--cinnabar); transform: translateX(2px); }

@media (prefers-reduced-motion: reduce) {
  .card, .go { transition: none; }
  .card:hover { transform: none; }
  .card:hover .go { transform: none; }
}
</style>
