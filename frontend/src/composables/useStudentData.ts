import { ref, type Ref } from 'vue'
import {
  getStudent, getGrades, getGpaSummary, refreshGrades, reloginStudent,
} from '../api'
import type { Student, GradeItem, GpaSummary, GradeRefreshResult } from '../types'

/**
 * 学生档案数据：学生信息 + 成绩 + 绩点汇总 + 刷新。
 * 从 StudentDetail 抽出，外壳只需 load()/refresh()，视图拿到只读结果。
 * 单一 gen 计数器：切学生 / 再次刷新会作废在途的旧请求。
 */
export function useStudentData(sid: Ref<string>) {
  const student = ref<Student | null>(null)
  const grades = ref<GradeItem[]>([])
  const gpa = ref<GpaSummary | null>(null)
  const loading = ref(true)
  const refreshing = ref(false)
  const result = ref<GradeRefreshResult | null>(null)
  let gen = 0

  async function load() {
    const g = ++gen
    loading.value = true
    student.value = null; grades.value = []; gpa.value = null; result.value = null
    try {
      const [s, gr, sm] = await Promise.all([
        getStudent(sid.value),
        getGrades(sid.value),
        getGpaSummary(sid.value).catch(() => null),
      ])
      if (g !== gen) return
      student.value = s; grades.value = gr; gpa.value = sm
    } catch (e) {
      if (g !== gen) return
      console.error(e)
    } finally {
      if (g === gen) loading.value = false
    }
  }

  // 教务偶发 502：先静默重登一次再重试
  let retryLeft = 1
  async function refresh() { retryLeft = 1; await runRefresh() }
  async function runRefresh() {
    const g = ++gen
    refreshing.value = true; result.value = null
    try {
      const r = await refreshGrades(sid.value)
      if (g !== gen) return
      result.value = r
      grades.value = await getGrades(sid.value)
      gpa.value = await getGpaSummary(sid.value).catch(() => gpa.value)
    } catch (e: any) {
      if (g !== gen) return
      if (e.response?.status === 502 && retryLeft > 0) {
        retryLeft--
        try { await reloginStudent(sid.value) } catch { /* 重登失败也继续报错 */ }
        await runRefresh(); return
      }
      alert('刷新失败: ' + (e.response?.data?.detail || e.message))
    } finally {
      refreshing.value = false
    }
  }

  return { student, grades, gpa, loading, refreshing, result, load, refresh }
}
