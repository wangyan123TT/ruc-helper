# 人大教务系统 XSMH0703 API 参考

> 2026-07-07 | 学期: 2026-2027-1 | Base URL: `https://jw.ruc.edu.cn/resService/jwxtpt/v1`

---

## 一、认证

### 获取 Token

```
POST https://jw.ruc.edu.cn/secService/login
Content-Type: application/json
Accept: application/json
KAPTCHA-KEY-GENERATOR-REDIS: securityKaptchaRedisServiceAdapter

{
  "userCode": "学号",
  "password": "密码",
  "kaptcha": "testa",       // 固定值，绕过验证码
  "userCodeType": "ldap"
}

返回:
  errorCode: "success"
  data.token: JWT (有效期约12小时)
  data.authcode: 学号
  Set-Cookie: SESSION=xxx
```

### 请求头模板

```
Content-Type: application/json;charset=UTF-8
Accept: application/json, text/plain, */*
app: PCWEB
userrolecode: student
token: <JWT>
Cookie: authcode=<学号>; SESSION=<SESSION_ID>; token=
Referer: https://jw.ruc.edu.cn/Njw2017/index.html
```

### OAuth 登录（微人大 SSO，浏览器端）

部分 API（学期列表、周历、教学大纲详情）只能通过浏览器端 `http.postJSON` 调用，需先完成 OAuth 登录。

**流程**：
```
1. 浏览器打开 jw.ruc.edu.cn → 302 → v.ruc.edu.cn/account/login（微人大 SSO）
2. 在 iframe 中填写学号 + 密码 + 验证码 → 点击登录
3. 回调 jw.ruc.edu.cn/secService/oauthlogin → JWT 存入 localStorage.qzdatasoft
4. 进入教务系统主页，全局 http 对象可用
```

**自动化**（Playwright + ddddocr）：

```python
# 1. 截图验证码
frame = page.locator('#login-iframe').contentFrame()
frame.locator('#codeImg').screenshot(path='captcha.png')

# 2. ddddocr 识别
import ddddocr
ocr = ddddocr.DdddOcr(show_ad=False)
code = ocr.classification(open('captcha.png', 'rb').read())

# 3. 填表登录
frame.locator('input[placeholder="学工号/手机号/邮箱"]').fill(学号)
frame.locator('input[placeholder="密码"]').fill(密码)
frame.locator('input[placeholder="请输入验证码"]').fill(code)
frame.locator('button:has-text("登录")').click()

# 4. 登录态持久化
# playwright-cli state-save browser_state.json  → 下次 state-load 直接恢复
```

**浏览器端调用**：
```js
// http 对象由教务系统 Vue.js 前端提供
http.postJSON("XSMH0703_com.qzdatasoft.jw.jczy...Controller.method", {params})
```

---

## 二、课程相关 API

### 1. 全校课程表 `findQxxKckbKcqdList`

含学分，**无上课时间和地点**。

```
POST /pkgl/pkglInfo_qxxzkb/findQxxKckbKcqdList
     ?resourceCode=XSMH0703
     &apiCode=jw.pkgl.pkglInfo.controller.PkqxxkbController.findQxxKckbKcqdList

Body: {"jczy013id": "2026-2027-1", "sctype": "zgrmdx"}
     可选过滤: "kkdwid" (院系ID), "skls_name" (教师名)
```

| 字段 | 含义 |
|------|------|
| `kcmc_name` | 课程名 |
| `ktmc_name` | 课堂名 |
| `kkdw_name` | 开课单位 |
| `zxf` | **学分** |
| `kclb_name` | 课程类别 |
| `khfs_name` | 考核方式 |
| `skdx_name` | 上课对象 |
| `jxl_name` | 教学楼 |
| `classroom_type` | 教室类型 |
| `jhxs` | 计划学时 |
| `zxs` | 总学时 |
| `xxrs` | 限选人数 |
| `xkrs` | 已选人数 |
| `skls_name` | 教师名 |
| `jszc_name` | 教师职称 |
| `pklb_name` | 排课类别 |
| `kcbh` | 课程编号 |
| `kth` | 课堂号 |
| `xnxq_name` | 学期名称 |

返回: `rowCount` 为真实总数(2270)。默认 `pageSize=30`，增大到 **1000** 后分页可用（上限约 1000-2000）。

---

### 2. 教师课表 `searchTeacherkbList`

含时间、地点、周次，**无学分**。

```
POST /xsd/xsdqxxkb_info/searchTeacherkbList
     ?resourceCode=XSMH0703
     &apiCode=xsdInfo.controller.XsdQxxkbController.searchTeacherkbList

Body: {"jczy013id": "2026-2027-1",
       "pkgl002id": "c13526460000WH",
       "sctype": "zgrmdx",
       "skls_name": "x"}      // "x" 不过滤，返回全部教师
```

| 字段 | 含义 |
|------|------|
| `teachername` | 教师名 |
| `kc_name` | 课程名 |
| `ktmc_name` | 课堂名 |
| `pksj` | **排课时间编码** |
| `idjkssj` / `idjjssj` | 起止时间 (如 1400 = 14:00) |
| `djjssj` / `djkssj` | 起止时间(文本) |
| `js_name` | 教室 |
| `pkzc` | 周次 (如 "1-16") |
| `pkzcmx` | 周次明细 (如 "1,2,3,...,16") |
| `sjbz_name` | 单双周 |
| `kkdwid` | 开课单位ID |
| `teacherid` | 教师工号 |

返回: 二维数组，第一层按课堂分组。

---

### 3. 教师课表 v2 `searchJskbList`

与 `searchTeacherkbList` 类似，可按教师名过滤。

```
POST /xsd/xsdqxxkb_info/searchJskbList
     ?resourceCode=XSMH0703
     &apiCode=xsd.xsdInfo.controller.XsdQxxkbController.searchJskbList

Body: 同上，skls_name 可填具体教师名
```

比 v1 多了 `bj_name`(班级名)、`skdw_name`(授课单位) 字段。

---

### 4. 班级课表 `searchBjkbList`

```
POST /xsd/xsdqxxkb_info/searchBjkbList
     ?resourceCode=XSMH0703
     &apiCode=jw.xsd.xsdInfo.controller.XsdQxxkbController.searchBjkbList

Body: {"jczy013id": "2026-2027-1",
       "pkgl002id": "c13526460000WH",
       "sctype": "zgrmdx",
       "zt": "4"}
```

返回二维数组，含 `bj_name`(班级名)、`ndzy_name`(年级专业)。

### 5. 教学大纲详情 `findSyllabusEntryInfoById`

含**教师联系方式**（手机、邮箱、办公地点）、教材、成绩构成。

```
POST /xsd/stuCourseCenterController/findSyllabusEntryInfoById
     ?resourceCode=XSMH0303
     &apiCode=jw.xsd.courseCenter.controller.StuCourseCenterController.findSyllabusEntryInfoById

Body: {"kkgl004id": "00410402995",
       "jczy013id": "2025-2026-2",
       "type": "xsck"}
```

`kkgl004id` 可从教师课表 API 的返回数据中获取。

**teacherList 字段** (教师信息):

| 字段 | 含义 |
|------|------|
| `skls_name` | 教师姓名 |
| `phone` | **手机号** |
| `email` | **邮箱** |
| `jszc_name` | 职称 |
| `bgdd` | 办公地点 |
| `sksj` | 上课时间 |
| `skdd` | 上课地点 |

**顶层字段** (课程信息):

| 字段 | 含义 |
|------|------|
| `kcmc_name` / `ktmc_name` | 课程名 / 课堂名 |
| `zxf` / `zxs` | 学分 / 总学时 |
| `xxrs` | 限选人数 |
| `qmkhfs` | 考核方式 (如 "闭卷考试") |
| `qmkhbl` / `pskhbl` | 期末% / 平时% |
| `khxmList` | 成绩构成明细 (课程作业/研讨/期中/期末) |
| `syjcList` | 教材列表 (书名/出版社/作者/ISBN/版次) |
| `aplist` | 排课记录 (时间/地点/周次/教师) |
| `lrxmList` | 教学内容 (课程简介/教学目标/思政设计) |

---

## 三、基础数据 API

### 5. 开课单位列表 `findKkdwList`

```
POST /xsd/xjgl_public/findKkdwList
     ?resourceCode=XSMH0703
     &apiCode=jw.xsd.xsdInfo.controller.XsdPublicController.findKkdwList

Body: {}
返回: [{"dwid": "100100", "dw_name": "[100100]马克思主义学院"}, ...] (63条)
```

### 6. 授课单位列表 `findSkdwList`

```
POST /xsd/xjgl_public/findSkdwList
     ?resourceCode=XSMH0703
     &apiCode=jw.xsd.xsdInfo.controller.XsdPublicController.findSkdwList

Body: {}
返回: 44条，格式同上
```

### 7. 校区信息 `findXsdXqInfo`

```
POST /xsd/xjgl_public/findXsdXqInfo
     ?resourceCode=XSMH0703
     &apiCode=jw.xsd.xsdInfo.controller.XsdPublicController.findXsdXqInfo

Body: {"jczy013id": "2026-2027-1", "sctype": "zgrmdx"}
返回: 中关村、苏州、通州 3个校区 (xqbh, xqname1, city_name)
```

### 8. 教学楼信息 `findXsdJxlInfo`

```
POST /xsd/xjgl_public/findXsdJxlInfo
     ?resourceCode=XSMH0703
     &apiCode=jw.xsd.xsdInfo.controller.XsdPublicController.findXsdJxlInfo

Body: {}
返回: 75条 (jxl_name, xq_name, jxllb_name, jxlcs)
```

### 9. 班级信息 `findXsBjInfo`

```
POST /xsd/xjgl_public/findXsBjInfo
     ?resourceCode=XSMH0703
     &apiCode=jw.xsd.xsdInfo.controller.XsdPublicController.findXsBjInfo

Body: {}
返回: rowCount=3823, items=30条/页 (bj_name, bjbh, ndzy_name, ssdw_name, pycc_name, xkml_name)
```

### 10. 排课时间管理 `findPksjglList`

```
POST /pkgl/pksjgl/findPksjglList
     ?resourceCode=XSMH0703
     &apiCode=jw.pkgl.pkglInfo.controller.PksjglController.findPksjglList

Body: {"jczy013id": "2026-2027-1", "sctype": "zgrmdx"}
返回: rowCount=68, items=30条/页 (id, jcmb_name, xnxq_name, mtdj)
```

### 11. 排课管理ID列表 `searchPkgl002List`

获取排课时间段配置（大节 ↔ 精确时间映射），是解析 `pksj` 编码的权威参照表。

```
POST /xsd/xsdjsjygl_info/searchPkgl002List
     ?resourceCode=XSMH0703
     &apiCode=jw.xsd.xsdInfo.controller.XsdJsjyglController.searchPkgl002List

Body: {"jczy013id": "2026-2027-1", "sctype": "zgrmdx"}
```

返回 `pkgl00201List` (7 大节):

| 大节 | 时间 | 节次 |
|------|------|------|
| 第一大节 | 08:00 - 09:30 | 01,02 |
| 第二大节 | 10:00 - 11:30 | 03,04 |
| 第三大节 | 12:00 - 13:30 | 05,06 |
| 第四大节 | 14:00 - 15:30 | 07,08 |
| 第五大节 | 16:00 - 17:30 | 09,10 |
| 第六大节 | 18:00 - 19:30 | 11,12 |
| 第七大节 | 19:40 - 21:10 | 13,14 |

### 12. 授课专业列表 `findSkZyList`

```
POST /xsd/xjgl_public/findSkZyList
     ?resourceCode=XSMH0703
     &apiCode=jw.xsd.xsdInfo.controller.XsdPublicController.findSkZyList

Body: {}
返回: null (所有尝试的参数组合均返回 null，可能需特定页面上下文)
```

---

## 四、排课时间编码 (pksj)

`pksj` 为变长数字，格式: `W PP PP PP ...`

- **W**: 星期几 (1=周一 ~ 7=周日)
- **PP**: 每对数字表示一个大节

### 大节 ↔ 时间对照

| 大节 | 时间 |
|------|------|
| `01`+`02` | 08:00 - 09:30 |
| `03`+`04` | 10:00 - 11:30 |
| `05`+`06` | 12:00 - 13:30 |
| `07`+`08` | 14:00 - 15:30 |
| `09`+`10` | 16:00 - 17:30 |
| `11`+`12` | 18:00 - 19:30 |
| `13`+`14` | 19:40 - 21:10 |

### 示例

| pksj | 含义 |
|------|------|
| `10102` | 周一 08:00-09:30 |
| `30708` | 周三 14:00-15:30 |
| `501020304` | 周五 08:00-11:30 |
| `407080910` | 周四 14:00-17:30 |
| `11121314` | 周一 18:00-21:10 |
| `601020304050607080910` | 周六 08:00-17:30 |

---

## 五、获取全校完整课程表

`findQxxKckbKcqdList` (API #1) 默认 `pageSize=30` 且 `pageIndex` 无效。但将 `pageSize` 设为 **1000** 后分页可用，3 次请求即可拿全。

```
POST findQxxKckbKcqdList (API #1)
Body: {"jczy013id":"2026-2027-1","sctype":"zgrmdx","page":{"pageIndex":1,"pageSize":1000}}
      {"jczy013id":"2026-2027-1","sctype":"zgrmdx","page":{"pageIndex":2,"pageSize":1000}}
      {"jczy013id":"2026-2027-1","sctype":"zgrmdx","page":{"pageIndex":3,"pageSize":1000}}
```

pageSize 上限约 1000-2000 之间，1000 稳定可用。

### 合并教师课表（时间+地点）

全校课表有学分无时间地点，教师课表(API #2) 有时间地点无学分。按 (教师名, 课程名, 课堂名) 关联合并，多时段课程展开为多行。

### 实测 (2026-2027-1)

| 指标 | 数值 |
|------|------|
| 请求次数 | 3 次 |
| 课程总数 | 2270 条 |
| 合并教师课表后 | 3066 行 (多时段展开) |

---

## 六、认证体系

| | 数据查询类 API (XSMH) |
|---|---|
| 路径 | `/resService/jwxtpt/v1/...` |
| 鉴权头 | `token: <JWT>` |
| Cookie | `SESSION`, `authcode` |
| 获取方式 | `/secService/login` 自动获取 |
| Token 有效期 | ~12小时 |

---

## 七、获取全校教师联系方式

`findSyllabusEntryInfoById` (API #5) 返回的 `teacherList` 含有手机、邮箱、职称、办公地点。

### 方法

1. `searchTeacherkbList` → 获取所有教师的 `kkgl004id`（去重）
2. 对每个教师并行调 `findSyllabusEntryInfoById({kkgl004id, jczy013id, type:"xsck"})` → 提取 `teacherList`

### 实测 (2026-2027-1, 50线程)

| 指标 | 数值 |
|------|------|
| 教师总数 | 1434 |
| 命中（有联系方式） | 1137 (79.3%) |
| 未命中 | 297（体育课/思政大课等无教学大纲的课程） |
| 耗时 | 124 秒 |

无数据集中在：习近平新时代中国特色社会主义思想概论(20)、马克思主义基本原理(20)、体育课(游泳9/太极拳9/篮球5等)。

### Python 示例

```python
# 1. 获取所有教师 kkgl004id
tc = post(searchTeacherkbList, {jczy013id, pkgl002id, skls_name: "x"})
teachers = {}
for g in tc['data']:
    for item in g:
        if item['teachername'] not in teachers:
            teachers[item['teachername']] = item['kkgl004id']

# 2. 并行 50线程查询
def query(name, kid):
    d = post(findSyllabusEntryInfoById,
             {kkgl004id: kid, jczy013id, type: "xsck"})
    tl = d['data'][0].get('teacherList', [])
    return [{'name': t['skls_name'], 'phone': t['phone'],
             'email': t['email'], 'title': t['jszc_name'],
             'office': t['bgdd']} for t in tl]

with ThreadPoolExecutor(max_workers=50) as ex:
    futures = {ex.submit(query, n, k): n for n, k in teachers.items()}
```
