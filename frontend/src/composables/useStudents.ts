import { ref } from 'vue'
import { listStudents } from '../api'
import type { Student } from '../types'

// 管理台的学生名册（模块级单例）：账号管理 / 成绩监控 两个视图共享同一份，
// 一处改动（改邮箱、切监控、删除）立即反映到另一处，切视图不重复拉取。
const students = ref<Student[]>([])
const loading = ref(false)
let loaded = false

async function load(force = false) {
  if (loaded && !force) return
  loading.value = true
  try {
    students.value = await listStudents()
    loaded = true
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

// 原地替换一条（接口返回更新后的 Student 时用）
function replace(s: Student) {
  const i = students.value.findIndex(x => x.student_id === s.student_id)
  if (i >= 0) students.value[i] = s
}

function removeById(id: string) {
  students.value = students.value.filter(x => x.student_id !== id)
}

export function useStudents() {
  return { students, loading, load, replace, removeById }
}
