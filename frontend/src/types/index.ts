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
