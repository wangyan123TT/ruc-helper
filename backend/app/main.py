"""
FastAPI 入口
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import init_db
from .routers import students, grades, monitor, settings, timetable, grab
from .services import grab as grab_svc


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    # 抢课检测循环随应用启动（无活跃目标时空转，代价极低）。
    # 当前处于段1：只检测余额、判冲突、更新状态，不提交。
    grab_svc.start_grab()
    yield
    grab_svc.stop_grab()


app = FastAPI(title="RUC Helper", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(students.router)
app.include_router(grades.router)
app.include_router(monitor.router)
app.include_router(settings.router)
app.include_router(timetable.router)
app.include_router(grab.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
