import axios from 'axios'
import type {
  Student,
  StudentCreate,
  GradeItem,
  GradeRefreshResult,
  GpaSummary,
  MonitorStatus,
  MonitorHistoryItem,
  TimetableData,
  GrabCategoriesResp,
  GrabPoolResp,
  GrabTarget,
  GrabStatusResp,
} from '../types'

const api = axios.create({ baseURL: '/api' })

// Students
export const addStudent = (data: StudentCreate) =>
  api.post<Student>('/students/', data).then(r => r.data)

export const listStudents = () =>
  api.get<Student[]>('/students/').then(r => r.data)

export const getStudent = (id: string) =>
  api.get<Student>(`/students/${id}`).then(r => r.data)

export const deleteStudent = (id: string) =>
  api.delete(`/students/${id}`).then(r => r.data)

export const reloginStudent = (id: string) =>
  api.post(`/students/${id}/relogin`).then(r => r.data)

export const toggleMonitorStudent = (id: string) =>
  api.post<Student>(`/students/${id}/monitor`).then(r => r.data)

export const testEmailStudent = (id: string) =>
  api.post(`/students/${id}/test-email`).then(r => r.data)

export const updateStudentEmail = (id: string, email: string) =>
  api.put<Student>(`/students/${id}/email?email=${encodeURIComponent(email)}`).then(r => r.data)


// Grades
export const getGrades = (studentId: string) =>
  api.get<GradeItem[]>(`/grades/${studentId}`).then(r => r.data)

export const refreshGrades = (studentId: string) =>
  api.post<GradeRefreshResult>(`/grades/${studentId}/refresh`).then(r => r.data)

export const getGpaSummary = (studentId: string) =>
  api.get<GpaSummary>(`/grades/${studentId}/summary`).then(r => r.data)

// Monitor
export const getMonitorStatus = () =>
  api.get<MonitorStatus>('/monitor/status').then(r => r.data)

export const startMonitor = (interval = 30) =>
  api.post(`/monitor/start?poll_interval=${interval}`).then(r => r.data)

export const stopMonitor = () =>
  api.post('/monitor/stop').then(r => r.data)

export const getMonitorHistory = () =>
  api.get<MonitorHistoryItem[]>('/monitor/history').then(r => r.data)

// Timetable — 预选课程表（待筛选志愿）。实时抓取，不入库。
export const getTimetable = (studentId: string) =>
  api.get<TimetableData>(`/timetable/${studentId}`).then(r => r.data)

// 已选课程表 — 只含选课状态为「通过」的课
export const getEnrolledTimetable = (studentId: string) =>
  api.get<TimetableData>(`/timetable/${studentId}/enrolled`).then(r => r.data)

// Grab — 抢课（段1：浏览课程池 + 配目标 + 看状态；提交在后端隔离，尚未启用）
export const getGrabCategories = (studentId: string) =>
  api.get<GrabCategoriesResp>(`/grab/${studentId}/categories`).then(r => r.data)

export const getGrabPool = (studentId: string, kclbcode: string, params: Record<string, string> = {}) => {
  const qs = new URLSearchParams({ kclbcode, ...params }).toString()
  return api.get<GrabPoolResp>(`/grab/${studentId}/pool?${qs}`).then(r => r.data)
}

export const getGrabTargets = (studentId: string) =>
  api.get<GrabTarget[]>(`/grab/${studentId}/targets`).then(r => r.data)

export const addGrabTarget = (
  studentId: string,
  body: Partial<GrabTarget> & { course_key: string; kclbcode: string; pool_params?: Record<string, string> },
) => api.post<GrabTarget>(`/grab/${studentId}/targets`, body).then(r => r.data)

export const removeGrabTarget = (studentId: string, targetId: number) =>
  api.delete(`/grab/${studentId}/targets/${targetId}`).then(r => r.data)

export const getGrabStatus = () =>
  api.get<GrabStatusResp>('/grab/status').then(r => r.data)
