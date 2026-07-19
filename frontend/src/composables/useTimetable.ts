import { ref, type Ref } from 'vue'
import { getTimetable, getEnrolledTimetable } from '../api'
import type { TimetableData } from '../types'

export type TtKind = 'preselect' | 'enrolled'

/**
 * 课表数据（预选=待筛选志愿 / 已选=通过的课）。实时抓取需现场登教务(约5s)，
 * 故带缓存：非强制且已有数据就不重复抓。在外壳里各建一个实例，切视图不丢缓存。
 */
export function useTimetable(sid: Ref<string>, kind: TtKind) {
  const data = ref<TimetableData | null>(null)
  const loading = ref(false)
  const error = ref('')
  let gen = 0
  const fetcher = kind === 'enrolled' ? getEnrolledTimetable : getTimetable

  async function load(force = false) {
    if (loading.value) return
    if (data.value && !force) return
    const g = ++gen
    loading.value = true; error.value = ''
    try {
      const d = await fetcher(sid.value)
      if (g !== gen) return
      data.value = d
    } catch (e: any) {
      if (g !== gen) return
      data.value = null
      error.value = e.response?.data?.detail || e.message || '加载失败'
    } finally {
      if (g === gen) loading.value = false
    }
  }

  function reset() { data.value = null; error.value = ''; gen++ }

  return { data, loading, error, load, reset }
}
