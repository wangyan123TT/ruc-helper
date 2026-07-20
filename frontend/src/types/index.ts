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

export interface GpaSummary {
  student_id: string
  gpa: number
  weighted_avg: number
  simple_avg: number
  credits: number
  courses: number
  api_gpa: number | null
  major_name: string
  dept_name: string
  class_rank: string
  major_rank: string
  gpa_rank: string
  avg_rank: string
  weighted_rank: string
  semester_summary: SemesterSummaryItem[]
}

export interface SemesterSummaryItem {
  jczy013id: string
  zxf: number
  kcnum: number
  pjxfjd: number
  pjxfj: number
  sumjd: number
}

// ---- 抢课（段1：只监控/配置，提交在后端隔离） ----

export interface GrabSlot {
  weeks: string
  day: number
  periods: number[]
  room: string
  start: string
  end: string
}

export interface GrabSubCategory {
  name: string
  group: string                        // '子类别' | '双选认证·按学院' | '荣誉选课'
  params: Record<string, string>       // 透传给课程池的维度参数
}

export interface GrabCategory {
  kclbcode: string
  name: string
  count: number
  subs: GrabSubCategory[]
}

export interface GrabCategoriesResp {
  mode: string
  mode_code: string
  ctrl: string
  hd_name: string
  xkkssj: string
  xkjssj: string
  now: string
  is_time_priority: boolean
  categories: GrabCategory[]
}

// 历年给分 —— 一门课/一个老师合并跨年后的占比
export interface GradeRatio {
  pass_fail: boolean
  n: number                            // 有效数字成绩人数
  n_pass?: number
  p86?: number                         // ≥86 占比 %
  p90?: number                         // ≥90 占比 %（经验上被优秀率卡在~30%）
  small?: boolean                      // n<15 小样本
}

export interface GradeYear extends GradeRatio {
  year: string
}

// 挂在课程池每门课上的给分数据
export interface GradeStats {
  match: 'exact' | 'course' | 'teacher' | 'none'   // 此课此师 / 全课程 / 该师全部课 / 无数据
  teacher?: string
  headline?: GradeRatio
  by_year?: GradeYear[]
  n_teachers?: number                  // match=course 时该课共几位老师
  pass_fail?: boolean
}

// 「对比老师」弹层里每一行
export interface CourseTeacherRow extends GradeRatio {
  teacher: string
  by_year: GradeYear[]
}

export interface CourseTeachersResp {
  course: string
  teachers: CourseTeacherRow[]
}

// 给分查询（独立搜索页）：模糊搜索聚合到 (课, 师) 一行
export interface GradeSearchRow extends GradeRatio {
  course: string
  teacher: string
  by_year: GradeYear[]
}
export interface GradeSearchResp {
  rows: GradeSearchRow[]
  total: number
}

// 「查老师」弹层里每一行（该老师的一门课）
export interface TeacherCourseRow extends GradeRatio {
  course: string
  teacher: string
  by_year: GradeYear[]
}

export interface TeacherCoursesResp {
  teachers: string[]                   // 匹配到的老师名（合上课可能多个）
  courses: TeacherCourseRow[]
}

export interface GrabPoolCourse {
  course_key: string
  kclbcode: string
  name: string
  class_name: string
  teacher: string
  credit: number
  dept: string
  cap: number | null
  enrolled: number | null
  surplus: number | null
  slots: GrabSlot[]
  conflict: { day: number; period: number }[]
  already_target: boolean
  grade_stats: GradeStats
}

export interface GrabPoolResp {
  mode_code: string
  courses: GrabPoolCourse[]
}

// waiting 等待 | grabbing 盯着 | ready 有名额 | success 抢到 | conflict 冲突已停 | failed 失败
export type GrabStatus = 'waiting' | 'grabbing' | 'ready' | 'success' | 'conflict' | 'failed'

export interface GrabTarget {
  id: number
  student_id: string
  course_key: string
  kclbcode: string
  course_name: string
  class_name: string
  teacher: string
  credit: number
  priority: number
  status: GrabStatus
  message: string
  attempts: number
  updated_at: string | null
}

export interface GrabStatusResp {
  running: boolean
  armed: boolean
  total_targets: number
  by_status: Record<string, number>
}
