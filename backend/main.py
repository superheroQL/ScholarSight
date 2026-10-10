from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import papers, users, chat, analysis, review, compare


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时自动创建缺失的数据表（已存在的表不受影响）
    from app.db.db_config import async_engine
    from app.models import chat as chat_model
    from app.models import papers as papers_model
    from app.models import analysis as analysis_model
    from app.models import review as review_model
    from app.models import multi_analysis as multi_analysis_model
    from app.models.users import Base

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # 允许的源，开发阶段允许所有源，生产环境需要指定源
    allow_credentials=True,     # 允许携带cookie
    allow_methods=["*"],        # 允许的请求方法
    allow_headers=["*"],        # 允许的请求头
)


@app.get("/")
async def root():
    return {"message": "Hello World"}


# 挂载路由/注册路由
app.include_router(papers.router)
app.include_router(users.router)
app.include_router(chat.router)
app.include_router(analysis.router)
app.include_router(review.router)
app.include_router(compare.router)

