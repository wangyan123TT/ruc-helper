import type { GradeItem } from '../types'

// 按学期聚合成绩 —— 概览分带 / 走势 / 「成绩」页共用同一套算法，保证口径一致。
// 关键：grade_point 后端存的已是「绩点 × 学分」(学分绩点 jd)，
//       所以学期 GPA = Σ(grade_point) / Σ学分，不能再乘一次学分。

export interface Sem {
  id: string
  short: string
  courses: GradeItem[]
  credits: number
  gpa: number | null    // 学期 GPA，排除 P/F
  avg: number | null    // 学期均分（数字成绩算术平均）
}

const isPf = (g: GradeItem) => g.cjfscode === '3'

// 学期字段 -> 短标签「年+季」，按自然年（秋=学年首年，春/夏=次年），供走势 x 轴
export function semShort(s: string): string {
  const ys = s.match(/20\d{2}/g) || []
  const y1 = ys[0] ? ys[0].slice(2) : ''
  const y2 = ys[1] ? ys[1].slice(2)
    : (ys[0] ? String((Number(ys[0]) + 1) % 100).padStart(2, '0') : '')
  if (/秋|第?一学期/.test(s)) return y1 + '秋'
  if (/春|第?二学期/.test(s)) return y2 + '春'
  if (/夏|第?三学期/.test(s)) return y2 + '夏'
  return (s || '').slice(-4)
}

// 学期时间序键：学年首年 * 10 + 学期序（秋=1 春=2 夏=3）。越大越新，同学年内 秋<春<夏。
export function semKey(s: string): number {
  const y = Number((s.match(/20\d{2}/) || [])[0] || 0)
  const term = /秋|第?一学期/.test(s) ? 1 : /春|第?二学期/.test(s) ? 2 : /夏|第?三学期/.test(s) ? 3 : 0
  return y * 10 + term
}

// 分数 -> 档：90+ 玉 / 85-89 墨 / <85 金；非数字(P 等)按墨
export function scoreClass(raw: string): 'hi' | 'mid' | 'lo' {
  const n = Number(raw)
  if (isNaN(n)) return 'mid'
  return n >= 90 ? 'hi' : n >= 85 ? 'mid' : 'lo'
}

export function groupBySemester(grades: GradeItem[]): Sem[] {
  const map = new Map<string, GradeItem[]>()
  for (const g of grades) {
    const k = g.semester || '其他'
    let a = map.get(k)
    if (!a) { a = []; map.set(k, a) }
    a.push(g)
  }
  const arr: Sem[] = [...map].map(([id, courses]) => {
    let jd = 0, cr = 0, sc = 0, scn = 0, credits = 0
    for (const c of courses) {
      const credit = Number(c.credit) || 0
      credits += credit
      const s = Number(c.score)
      if (!isNaN(s)) { sc += s; scn++ }
      if (!isPf(c) && credit > 0) { jd += Number(c.grade_point) || 0; cr += credit }
    }
    return {
      id, short: semShort(id), courses,
      credits: Math.round(credits * 10) / 10,
      gpa: cr ? Math.round(jd / cr * 100) / 100 : null,
      avg: scn ? Math.round(sc / scn * 10) / 10 : null,
    }
  })
  arr.sort((a, b) => semKey(b.id) - semKey(a.id))   // 时间序：新学期在前（同学年内 秋<春<夏）
  return arr
}
