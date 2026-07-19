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
  GradeStats,
  GrabTarget,
  GrabStatusResp,
  CourseTeachersResp,
  TeacherCoursesResp,
} from '../types'

const api = axios.create({ baseURL: '/api' })

// ---- 登录会话 ----
const TOKEN_KEY = 'ruc_session_token'
export const getToken = () => localStorage.getItem(TOKEN_KEY) || ''
export const setToken = (t: string) => localStorage.setItem(TOKEN_KEY, t)
export const clearToken = () => localStorage.removeItem(TOKEN_KEY)

// 每次请求带上令牌
api.interceptors.request.use(cfg => {
  const t = getToken()
  if (t) cfg.headers['X-Session-Token'] = t
  return cfg
})

// 401 = 登录失效 -> 清令牌回登录页
api.interceptors.response.use(
  r => r,
  err => {
    if (err.response?.status === 401) {
      clearToken()
      if (location.pathname !== '/login') location.href = '/login'
    }
    return Promise.reject(err)
  },
)

export interface LoginResp { token: string; student_id: string; name: string; is_admin?: boolean; expires_hours: number }
export const login = (student_id: string, password: string) =>
  api.post<LoginResp>('/auth/login', { student_id, password }).then(r => r.data)
export const logout = () => api.post('/auth/logout').then(r => r.data).catch(() => {})
export const getMe = () =>
  api.get<{ student_id: string; name: string; is_admin: boolean; major: string; grade: string }>('/auth/me').then(r => r.data)

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

export const startMonitor = (interval = 300) =>
  api.post(`/monitor/start?poll_interval=${interval}`).then(r => r.data)

export const stopMonitor = () =>
  api.post('/monitor/stop').then(r => r.data)

export const getMonitorHistory = () =>
  api.get<MonitorHistoryItem[]>('/monitor/history').then(r => r.data)

export interface MonitorLog { id: number; student_id: string; status: string; message: string; created_at: string }
export const getMonitorLogs = () =>
  api.get<MonitorLog[]>('/monitor/logs').then(r => r.data)

// SMTP 发件设置（带会话令牌，管理员用）
export interface SmtpSettings { smtpHost: string; smtpPort: string; smtpUsername: string; smtpPassword: string; fromAddress: string }
export const getSmtpSettings = () =>
  api.get<SmtpSettings>('/settings/smtp').then(r => r.data)
export const saveSmtpSettings = (params: Record<string, string>) =>
  api.put('/settings/smtp?' + new URLSearchParams(params).toString()).then(r => r.data)

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

// 历年给分 —— 一门课全部老师排名（「对比老师」弹层）。years 跟课程池的年份选项一致
export const getCourseTeachers = (course: string, years: string[] = []) =>
  api.get<CourseTeachersResp>(`/coursestats/course?course=${encodeURIComponent(course)}` +
    (years.length ? `&years=${years.join(',')}` : '')).then(r => r.data)

// 历年给分 —— 一个老师所有课（「查老师」弹层）
export const getTeacherCourses = (teacher: string, years: string[] = []) =>
  api.get<TeacherCoursesResp>(`/coursestats/teacher?teacher=${encodeURIComponent(teacher)}` +
    (years.length ? `&years=${years.join(',')}` : '')).then(r => r.data)

// 历年给分 —— 已导入的年份
export const getGradeYears = () =>
  api.get<{ years: { year: string; teacher_rows: number; graded: number }[] }>('/coursestats/years')
    .then(r => r.data)

// 批量按 (范围+年份) 算给分，供课程池徽章实时重算
export const batchGradeStats = (
  items: { course: string; teacher: string }[],
  scope: 'course' | 'teacher',
  years: string[],
) => api.post<{ results: GradeStats[] }>('/coursestats/batch', { items, scope, years }).then(r => r.data)

// 历年给分 —— 导入某年宽表 CSV / 删除某年（仅管理员）。
// 直接传原始 File（不在前端解码），后端读原始字节自行试 utf-8/gb18030，避免 GBK 乱码。
export const importGradeCsv = (year: string, data: File | string) =>
  api.post(`/coursestats/import?year=${encodeURIComponent(year)}`, data, {
    headers: { 'Content-Type': 'text/plain' },
  }).then(r => r.data as { year: string; teacher_rows: number; courses: number; graded: number })

export const deleteGradeYear = (year: string) =>
  api.delete(`/coursestats/${encodeURIComponent(year)}`).then(r => r.data)
