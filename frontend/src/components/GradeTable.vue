<script setup lang="ts">
import { computed } from 'vue'
import type { GradeItem } from '../types'

const props = defineProps<{ grades: GradeItem[]; newIds: string[] }>()

const summary = computed(() => {
  const isPf = (g: GradeItem) => g.cjfscode === '3'
  const allCredits = props.grades.reduce((s, g) => s + (Number(g.credit) || 0), 0)
  const allPoints = props.grades.reduce((s, g) => s + (Number(g.grade_point) || 0), 0)
  const gpaItems = props.grades.filter(g => !isPf(g))
  const gpaCredits = gpaItems.reduce((s, g) => s + (Number(g.credit) || 0), 0)
  const gpaPoints = gpaItems.reduce((s, g) => s + (Number(g.grade_point) || 0), 0)
  const gpa = gpaCredits > 0 ? (gpaPoints / gpaCredits).toFixed(2) : '0.00'
  return { allCredits, allPoints, gpaCredits, gpaPoints, gpa, pfCount: props.grades.length - gpaItems.length }
})
</script>

<template>
  <div class="grade-section" v-if="grades.length">
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th class="col-course">课程名称</th>
            <th class="col-teacher">教师</th>
            <th class="col-cat">类别</th>
            <th class="col-module">模块</th>
            <th class="col-num">学分</th>
            <th class="col-num">平时</th>
            <th class="col-num">期中</th>
            <th class="col-num">期末</th>
            <th class="col-num col-score">最终</th>
            <th class="col-num">绩点</th>
            <th class="col-note">备注</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="g in grades"
            :key="g.cjgl016id"
            :class="{ 'is-new': newIds.includes(g.cjgl016id), 'is-pf': g.cjfscode === '3' }"
          >
            <td class="col-course">
              <span v-if="newIds.includes(g.cjgl016id)" class="dot-new">NEW</span>
              {{ g.course_name }}
            </td>
            <td class="col-teacher">{{ g.teacher }}</td>
            <td class="col-cat">{{ g.category }}</td>
            <td class="col-module">{{ g.course_module }}</td>
            <td class="col-num">{{ g.credit }}</td>
            <td class="col-num">{{ g.daily_score }}</td>
            <td class="col-num">{{ g.midterm_score }}</td>
            <td class="col-num">{{ g.final_score }}</td>
            <td class="col-num col-score">{{ g.score }}</td>
            <td class="col-num">{{ g.grade_point }}</td>
            <td class="col-note">{{ g.grade_note }}</td>
          </tr>
        </tbody>
        <tfoot>
          <tr class="row-foot">
            <td :colspan="11">
              <div class="foot-inner">
                <span>共 <strong>{{ grades.length }}</strong> 门</span>
                <span class="foot-sep"></span>
                <span>总学分 <strong>{{ summary.allCredits }}</strong></span>
                <span class="foot-sep"></span>
                <span>总绩点 <strong>{{ summary.allPoints }}</strong></span>
                <span class="foot-sep"></span>
                <span>GPA <strong class="foot-gpa">{{ summary.gpa }}</strong></span>
                <span v-if="summary.pfCount > 0" class="foot-note">（已排除 {{ summary.pfCount }} 门 P/F）</span>
              </div>
            </td>
          </tr>
        </tfoot>
      </table>
    </div>

    <details class="gpa-legend">
      <summary>绩点核算规则</summary>
      <div class="legend-grid">
        <div class="legend-cell"><b>A</b><span>90–100</span><em>4.0</em></div>
        <div class="legend-cell"><b>A−</b><span>86–89</span><em>3.7</em></div>
        <div class="legend-cell"><b>B+</b><span>83–85</span><em>3.3</em></div>
        <div class="legend-cell"><b>B</b><span>80–82</span><em>3.0</em></div>
        <div class="legend-cell"><b>B−</b><span>76–79</span><em>2.7</em></div>
        <div class="legend-cell"><b>C+</b><span>73–75</span><em>2.3</em></div>
        <div class="legend-cell"><b>C</b><span>70–72</span><em>2.0</em></div>
        <div class="legend-cell"><b>C−</b><span>66–69</span><em>1.7</em></div>
        <div class="legend-cell"><b>D+</b><span>63–65</span><em>1.3</em></div>
        <div class="legend-cell"><b>D</b><span>60–62</span><em>1.0</em></div>
      </div>
      <p class="legend-formula">GPA = Σ(绩点 × 学分) ÷ Σ学分</p>
    </details>
  </div>

  <div v-else class="empty-box">暂无成绩数据</div>
</template>

<style scoped>
.grade-section {
  background: var(--white);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  overflow: hidden;
}

.table-wrap {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  min-width: 960px;
  table-layout: fixed;
}

th {
  text-align: left;
  padding: 11px 10px;
  background: #f8f8fb;
  color: var(--ink-400);
  font-weight: 600;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.4px;
  border-bottom: 2px solid var(--ink-100);
  white-space: nowrap;
}

td {
  padding: 10px;
  border-bottom: 1px solid #f3f3f6;
  color: var(--ink-700);
  vertical-align: middle;
}

tr:hover td { background: #fcfcfd; }

/* Column widths */
.col-course { width: 18%; }
.col-teacher { width: 10%; }
.col-cat { width: 10%; }
.col-module { width: 10%; }
.col-num { width: 7%; text-align: right; }
.col-score { width: 7%; text-align: right; }
.col-note { width: 7%; }

th.col-num, th.col-score { text-align: right; }

/* Cell styles */
.col-score { font-weight: 700; color: var(--ink-900); font-size: 14px; }
.col-note { color: var(--ink-300); font-size: 12px; }

.is-new td { background: linear-gradient(90deg, #f2faf5 0%, transparent 50%); }
.is-pf td { color: var(--ink-300); }
.is-pf .col-score { color: var(--ink-300); font-weight: 400; }

.dot-new {
  display: inline-block;
  background: var(--jade); color: #fff;
  font-size: 9px; font-weight: 700; padding: 1px 5px; border-radius: 3px;
  margin-right: 5px; vertical-align: middle;
  animation: pulse 2s ease-in-out infinite;
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* Footer */
.row-foot td {
  background: #f4f4f8;
  padding: 12px 16px;
}
.foot-inner {
  display: flex; align-items: center; gap: 0; flex-wrap: wrap;
  font-size: 13px; color: var(--ink-500);
}
.foot-inner strong { color: var(--ink-800); font-weight: 600; padding: 0 4px; }
.foot-sep {
  width: 1px; height: 14px; background: var(--ink-200); margin: 0 12px;
}
.foot-gpa { color: var(--cinnabar); font-size: 15px; }
.foot-note { font-size: 11px; color: var(--ink-300); margin-left: 8px; }

/* Legend */
.gpa-legend { padding: 0 16px 16px; border-top: 1px solid var(--ink-100); }
.gpa-legend summary { padding: 12px 0; font-size: 13px; color: var(--ink-500); cursor: pointer; font-weight: 500; }
.legend-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 2px; margin-bottom: 8px; }
.legend-cell { display: flex; align-items: center; gap: 8px; padding: 3px 8px; border-radius: 4px; font-size: 12px; }
.legend-cell b { width: 24px; color: var(--ink-700); font-size: 11px; }
.legend-cell span { color: var(--ink-300); flex: 1; }
.legend-cell em { color: var(--ink-600); font-style: normal; font-weight: 600; }
.legend-formula { font-size: 12px; color: var(--ink-300); padding: 0 8px; }

.empty-box { text-align: center; padding: 60px; color: var(--ink-300); font-size: 15px; }
</style>
