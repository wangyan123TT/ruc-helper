# Auto Choose Course — 人大教务系统自动选课

## 项目目标
自动选课脚本，用于人大暑期学校（jw.ruc.edu.cn）的课程选择和退课操作。

## 系统信息
- **系统**: 人大国际小学期 (RUC ISS)
- **开发商**: 湖南强智科技
- **网关**: `https://jw.ruc.edu.cn` → `gateway-service:8001`
- **前端**: Vue.js SPA (Element UI)

---

## API 架构（已验证）

### 鉴权
- `Authorization: Bearer <JWT>` + Cookie
- JWT 有效期约 4 小时，过期需重新登录

### 两套 Content-Type

| 接口类型 | Content-Type | Body 格式 |
|----------|-------------|-----------|
| 查询类 (列表、信息) | `application/json` | `{"page": {...}}` 或 `{}` |
| 操作类 (选课、退课、检查) | **`text/plain`** | 纯字符串 |

### 已确认可用的 API

| 端点 | 用途 | Content-Type | Body |
|------|------|-------------|------|
| `/qsmart/common/sessionUserInfo` (GET) | 用户信息 | - | - |
| `/minJwxt/mgmt/public/service/querySemesterListBySelect` (POST) | 学期列表 | JSON | `{}` |
| `/minJwxt/mgmt/student/course/getStuInfo` (POST) | 学生信息 | JSON | `{}` |
| `/minJwxt/mgmt/student/course/checkSelectCourseTime` (POST) | 检查选课时间 | JSON | `{}` |
| `/minJwxt/mgmt/student/course/queryCourseOfferListByPage` (POST) | 可选课程列表 | JSON | `{"page": {...}}` |
| `/minJwxt/mgmt/student/course/queryStuCourseOfferListByPage` (POST) | 已选课程列表 | JSON | `{"page": {...}}` |
| `/minJwxt/mgmt/student/course/selectCourse` (POST) | **选课** | **text/plain** | `crs_id` |
| `/minJwxt/mgmt/student/course/selectCourseByInner` (POST) | **校内选课** | **text/plain** | `crs_id` |
| `/minJwxt/mgmt/student/course/deleteStuCourseInfo` (POST) | **退课** | **text/plain** | **`crs_stu_id`** |
| `/minJwxt/mgmt/student/course/cancelSelectCourse` (POST) | 退课(废弃) | text/plain | ❌ 403 |
| `/minJwxt/mgmt/student/course/checkCourseSurplusCapacity` (POST) | 检查剩余名额 | **text/plain** | `crs_id` |
| `/minJwxt/mgmt/student/course/checkCourseSettleTime` (POST) | 检查时间冲突 | **text/plain** | `crs_id` |
| `/minJwxt/mgmt/student/course/selectCourseCheckForConflicts` (POST) | 冲突检查 | **text/plain** | `crs_id` |
| `/minJwxt/mgmt/student/course/checkCourseSelected` (POST) | 检查是否已选 | **text/plain** | `crs_id` |
| `/minJwxt/mgmt/student/course/checkContactInfo` (POST) | 联系信息检查 | JSON | `{}` |
| `/minJwxt/mgmt/student/course/checkStuLabel` (POST) | 学生标签检查 | JSON | `{}` |
| `/minJwxt/mgmt/student/course/cheCourseTimeContr` (POST) | 时间+数量校验 | **text/plain** | `crs_id` |
| `/minJwxt/mgmt/student/course/getStuCourseNum` (POST) | 已选门数 | JSON | `{}` |

### 退课接口

| 接口 | Content-Type | Body | 状态 |
|------|-------------|------|------|
| `deleteStuCourseInfo` | **`text/plain`** | **`crs_stu_id`** | ✅ **200 OK** |
| `cancelSelectCourse` | `text/plain` | `crs_id` | ❌ 403 Forbidden |

> **关键**: `deleteStuCourseInfo` 的 body 是 `crs_stu_id`（不是 `crs_id`！）
> 两个 id 都是 32 字符，浏览器抓包无法区分，实测确认是 `crs_stu_id`。
> 之前错误地用了 `crs_id`，导致 400 "Cannot be cancelled!"。

### 请求格式示例

**选课** (text/plain, body = crs_id):
```
8a74591a9b13548c019b2101c646007a
```

**退课** (text/plain, body = crs_stu_id):
```
8a7476069e8e9760019e923d699c00a8
```

---

## 选课时间窗口

学期数据中包含三轮校内选课时间戳（北京时间）:

| 轮次 | 字段名 | 开始 | 结束 |
|------|--------|------|------|
| 第1轮 | `internalCourseStartTime` / `internalCourseEndTime` | 05-28 00:00 | 06-03 00:00 |
| 第2轮 | `internalCourseStartTime2` / `internalCourseEndTime2` | 06-03 00:00 | 06-05 00:00 |
| 第3轮 | `internalCourseStartTime3` / `internalCourseEndTime3` | 07-06 00:00 | 07-24 00:00 |
| 校外选课 | `externalCourseStartTime` / `externalCourseEndTime` | 03-01 00:00 | 05-27 00:00 |

---

## 已解决问题

### 1. Content-Type 错误
选课/退课/检查类接口要求 `Content-Type: text/plain`。之前错误地使用 `application/json` 导致 400。

### 2. deleteStuCourseInfo 退课成功
- Content-Type: `text/plain`
- Body: 纯 `crs_stu_id` 字符串（32字符，从已选课程列表获取）
- **不是** `crs_id`！**不是** JSON！

### 3. 选课调用链验证
8 步检查链全部通过 → `selectCourseByInner` 403 → fallback `selectCourse` 200 OK，成功选课。
- 最多选 2 门，满额后需先退再选
- 时间冲突会被 `checkCourseSettleTime` 拦截

---

## 重要警示
⚠️ `config.json` 包含真实凭据 (JWT + Cookie)，**不要提交到 git**。
已通过 `.gitignore` 排除。

## 文件说明
- `config.json` — 凭据和 API 端点清单（gitignore）
- `auto_course.py` — 自动选课脚本（轮询 + 检查链 + 选课）
- `CONTEXT.md` — 本文档 (API 分析笔记)

---
---

# 【第二套系统】本科生正常学期选课 — resService / jwxtpt

> ⚠️ 与上文**完全不同的系统**，别混淆：
> - 上文 `minJwxt` + `Authorization: Bearer` = **暑期学校/国际小学期**，token 需手动从浏览器抠。
> - 本节 `resService` + `token` header = **正常学期选课**，与**成绩 API 同一套认证**，
>   可直接用 `backend/app/services/auth.py` 的 `do_login()` 拿 token，无需手动抓包。

前端: `https://jw.ruc.edu.cn/Njw2017/` (强智 Vue SPA)

## ★ 关键发现: API 注册表公开可下载

```
GET https://jw.ruc.edu.cn/resService/data/api.json     # 无需登录, ~5MB, 22548 条
```

返回 `{"data": {"<resourceCode>_<apiCode>": "<url模板>"}}`，覆盖整个教务系统。
**不用 F12 抓包**，查表即可得到任意接口的 URL。

拼装规则：
```
https://jw.ruc.edu.cn/resService  +  路径({version} -> v1)  +  ?resourceCode=X&apiCode=Y
```
已用成绩接口交叉验证：查表结果与 `services/grade.py:16` 硬编码路径完全一致。

## 挖接口的通用方法（无需凭据）

1. `GET /Njw2017/biz/biz.config.js` → `Qz.routes.<模块>` = 路由表(name/resCode/scripts)
2. 页面 JS 路径规律：`/Njw2017/{模块}/{页面name}/{脚本}`
   例：`/Njw2017/student/student-choice-center/student.choice.center.service.js`
3. `*.service.js` 里是 `方法名 -> "<resourceCode>_<apiCode>"` 映射
4. 拿 apiCode 去 `api.json` 查真实 URL

## 页面 resCode 对照

| resCode | 页面 | 说明 |
|---------|------|------|
| XSMH0303 | student-choice-center | 选课中心（含"进入选课"） |
| XSMH0313 | student-choice-result | 选课结果 |
| XSMH0701 | student-course-list | 我的课程表 |
| XSMH0526 | course-score-search | 成绩查询（现有 grade.py 用的） |
| XSMH0316/0317 | *-xxq | 小学期版本 |

## 请求体格式

查询类接口（`query.queryJSON`）需要 page 包装，`pageSize: 0` = 全取：
```json
{ "custom字段摊在顶层": "...", "page": {"pageIndex": 1, "pageSize": 0, "orderBy": ""} }
```
`conditions` 若使用需 base64 加密（`Qz.base64Encrypt`）；目前用不到。

## 「进入选课」调用链（XSMH0303）

路径前缀 `/jwxtpt/v1/xsd/stuCourseCenterController/`，apiCode 前缀
`jw.xsd.courseCenter.controller.StuCourseCenterController.`

| 步骤 | 方法 | 说明 |
|------|------|------|
| 1 | `findXsxkjdList` | 当前选课活动 → `xkgl017id` / `jczy013id` |
| 2 | `findZxxkByEntry` | 学生信息、专业(`bllsList`)、节次时间表(`kbSj`)、可选类别(`showXklbList`) |
| 3 | `findXsxkjdByOne` | 课程类别列表(`kclbcode`)，29 个，`ms`=门数(前端隐藏 ms=0) |
| 4a | `findKcInfoByflByRmdx` | **可选课程池** → `showKclist`（需 `kclbCodeMapper` + `bllsZyId`） |
| 4b | `findXkResList` | **已提交志愿** → `kcCahe` ★ 课程表数据源 |

> 「进入选课」按钮 = `window.open("student-select-course.html#/?jczy013id=..&xkgl017id=..&xkgl019id=..")`，
> 该页按 `xkgl003id` 分发到编号组件（16=专业选修 12=选课结果 13=课程表 …）。

**写操作（本项目不使用）**: `saveStuXkByRmdx`(选课) / `saveStuTxByRmdx`(退选)

## 志愿制 / 待筛选

`xkkzMap.trfs_name = "志愿"`，`xkfscode = "1"`：人人可报，超额由系统筛选。

- `kcCahe[].xkzt_name = "待筛选"` (`xkztcode=110`) — 尚未筛选
- `kcCahe[].xkzy_name` = 志愿号（同一门课报多个平行班 → 志愿 1/2/3/4）
- `showKclist[].xkrs` / `xxrs` = 报名人数 / 限选人数（实测有 329 报 100 的）
- 实测：平行班上课时间**通常相同**（只差教室/老师），故课表格子位置不受筛选结果影响；
  但**存在例外**（如英语演讲两个班时间完全不同），课表需标注。

## ★ kbinfo 编码（上课时间，无文档）

`~` 分隔多个时段，`@` 分隔字段：

| 下标 | 含义 | 例 |
|------|------|-----|
| 0 | 周次显示 | `1-16` / `4-5` |
| 1 | 周次列表 | `1,2,...,16` |
| 2 | 星期节次串(无逗号) | `4010203` |
| 3 | **节次列表** | `401,402,403` |
| 4 | 教室 | `教一1302` |
| 5 | 开始时间 | `800` → 8:00 |
| 6 | 结束时间 | `1045` → 10:45 |
| 7 | 标志(未确认) | `1` |
| 8 / 9 / 10 | 校区 / 楼id / 楼名 | `中关村校区` |

**下标 3 每项 = 星期(1位) + 节次(2位)**：`401`=周四第1节，`107`=周一第7节。

节次时间表来自 `findZxxkByEntry` → `kbSj[].pkgl00201list`（7 大节 × 2 小节 = 14 小节）：
第一大节 08:00-09:30(1,2) / 第二 10:00-11:30(3,4) / 第三 12:00-13:30(5,6) /
第四 14:00-15:30(7,8) / 第五 16:00-17:30(9,10) / 第六 18:00-19:30(11,12) / 第七 19:40-21:10(13,14)

## 对应脚本
- `cli/xk_timetable.py` — 待筛选课程 → 课程表 HTML（**只读**，不含任何写操作）
