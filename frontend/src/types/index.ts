export interface Student {
  id: number
  student_id: string
  name: string
  email: string
  major: string
  grade: string
  is_active: boolean
  is_monitored: boolean
  token_expires_at: string | null
  grade_count: number
  last_change_at: string | null
  created_at: string | null
}

export interface StudentCreate {
  student_id: string
  password: string
  email: string
}

export interface GradeItem {
  id: number
  student_id: string
  cjgl016id: string
  course_code: string
  course_name: string
  score: string
  daily_score: string
  midterm_score: string
  final_score: string
  credit: number
  grade_point: number
  semester: string
  category: string
  course_module: string
  teacher: string
  dept: string
  exam_type: string
  grade_note: string
  cjfscode: string
  is_new: boolean
  first_seen_at: string | null
  last_updated_at: string | null
}

export interface GradeRefreshResult {
  student_id: string
  total: number
  new_count: number
  updated_count: number
  new_grades: GradeItem[]
  updated_grades: GradeItem[]
}

export interface MonitorStatus {
  running: boolean
  poll_interval: number
  active_students: number
}

export interface MonitorHistoryItem {
  id: number
  student_id: string
  change_type: string
  grade_ids: string[]
  sent_at: string
}

// ---- 预选课程表（待筛选志愿）----

export interface TimetableSlot {
  weeks: string
  day: number
  periods: number[]
  room: string
  start: string
  end: string
  campus: string
  building: string
}

export interface TimetableClass {
  pref: number
  class_name: string
  teacher: string
  slots: TimetableSlot[]
  /** 该备选班与第一志愿上课时间不同 —— 课表上画虚线"备选落点" */
  is_ghost: boolean
}

export interface TimetableCourse {
  name: string
  category: string
  cat_class: string
  credit: number
  dept: string
  /** 该门课报了几个志愿（平行班） */
  n_pref: number
  /** 各志愿上课时间是否一致 */
  same_time: boolean
  primary: TimetableClass
  alts: TimetableClass[]
}

export interface TimetablePeriod {
  name: string
  start: string
  end: string
  subs: number[]
}

export interface TimetableContext {
  name: string
  sid: string
  major: string
  hd_name: string
  xnxq: string
  mode: string
  ctrl: string
  xkkssj: string
  xkjssj: string
  now: string
  periods: TimetablePeriod[]
}

export interface TimetableConflict {
  day: number
  period: number
  names: string[]
}

export interface TimetableData {
  context: TimetableContext
  courses: TimetableCourse[]
  conflicts: TimetableConflict[]
  total_credit: number
  n_courses: number
  n_prefs: number
  nopass_count: number
}
