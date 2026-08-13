# RUC Helper

中国人民大学教务系统助手 — **成绩监控 / 自动选课 / Token 管理**，支持 Web 界面与 CLI 命令行两种使用方式。

## 项目结构

```
├── cli/                        # CLI 工具
│   ├── get_token.py            #   通过学号密码获取 Token
│   └── auto_grade.py           #   自动轮询成绩变动
├── backend/                    # FastAPI 后端
│   ├── Dockerfile
│   └── app/
│       ├── main.py             #   入口 + 生命周期
│       ├── database.py         #   SQLAlchemy + SQLite
│       ├── models.py           #   ORM 模型
│       ├── schemas.py          #   Pydantic 请求/响应
│       ├── routers/            #   students / grades / monitor
│       └── services/           #   auth / grade / monitor
├── frontend/                   # Vue 3 + Vite 前端
│   └── src/
│       ├── views/              #   Dashboard / StudentDetail
│       ├── components/         #   StudentCard / GradeTable / AddStudentDialog
│       ├── api/                #   Axios 封装
│       └── types/              #   TypeScript 类型
├── nginx/                      # Nginx 配置 + Dockerfile
├── docker-compose.yml          # 一键部署
├── config.example.json         # 配置模板
├── pyproject.toml              # uv / Python 项目
└── CONTEXT.md                  # API 分析笔记
```

## Web 应用（Docker 部署）

### 功能

- **多学生管理** — 添加多个学生，独立监控
- **成绩自动轮询** — 后台定时查询，发现新课/成绩变动即时通知
- **邮件通知** — 成绩变动自动发送邮件（支持 QQ 邮箱等 SMTP）
- **GPA 计算** — 自动计算平均学分绩点，P/F 课程排除在外
- **可视化面板** — Vue 3 前端，成绩表格含平时/期中/期末/最终成绩

### 快速启动

```bash
cp .env.example .env       # 编辑 .env 填入 SMTP 配置
docker compose up -d
```

访问 http://localhost:8080，在页面右上角齿轮图标配置 SMTP（或直接编辑 `.env` 文件）。

> 开发环境默认启动 Vite dev server（前端热更新），生产部署需另行构建静态文件。

## CLI 工具

```bash
# 获取成绩查询 Token
uv run cli/get_token.py

# 自动查成绩（轮询模式）
uv run cli/auto_grade.py
```

CLI 工具依赖根目录的 `config.json`（从 `config.example.json` 复制并填写凭据）。

## 凭据获取

运行 `get_token.py`，输入学号+密码即可自动获取 Token 并写入 `config.json`。

## API 架构

选课与成绩共用同一套 `resService` 网关和认证：

| | 说明 |
|------|----------|
| 路径 | `/resService/jwxtpt/v1/...` |
| 鉴权头 | `token: <JWT>` |
| Cookie | `SESSION`, `authcode` |
| 获取方式 | `get_token.py` 自动获取 |

## 技术栈

| 层 | 技术 |
|------|------|
| 前端 | Vue 3, TypeScript, Vite, Axios |
| 后端 | FastAPI, SQLAlchemy, SQLite, uvicorn |
| 部署 | Docker Compose, Nginx |
| CLI | Python 3.12+, requests |

## 免责声明

本工具仅供学习研究使用。请遵守学校相关规定，合理使用教务系统资源。

## License

MIT
