import asyncio
import re
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.db_config import get_db
from app.crud.papers import save_paper, get_user_papers, get_paper_by_id, delete_paper_row
from app.utils.auth import get_current_user
from app.utils.logger_handler import logger
from app.models.users import User


# 创建 APIRouter 实例
# prefix 路由前缀（API 接口规范文档）
# tags 分组 标签
router = APIRouter(prefix='/api/v1/papers', tags=['papers'])
BACKEND_ROOT = Path(__file__).resolve().parents[2]
UPLOAD_ROOT = BACKEND_ROOT / 'data' / 'papers'
MAX_FILE_SIZE = 50 * 1024 * 1024


@router.post("/upload")
async def upload_paper(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    file: UploadFile = File(...),
):
    """
    上传论文文件
    """
    if not file.filename or not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail='只允许上传 PDF 文件')

    filename = re.sub(r'[^0-9A-Za-z._-]+', '_', Path(file.filename).name)
    user_id = user.id
    temp_path = UPLOAD_ROOT / f'.upload-{datetime.now().timestamp()}.pdf'

    try:
        UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)

        size = 0
        with temp_path.open('wb') as target:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_FILE_SIZE:
                    raise HTTPException(status_code=413, detail='PDF 文件不能超过 50 MB')
                target.write(chunk)

        paper = await save_paper(db, user_id, temp_path, filename)
        return {
            'code': 200,
            'message': '论文上传成功',
            'data': {
                'id': paper.id,
                'title': paper.title,
                'authors': paper.authors,
                'file_name': paper.file_name,
                'file_path': paper.file_path,
                'file_size': paper.file_size,
                'created_at': paper.created_at.isoformat(),
            },
        }
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=500, detail=f'论文入库失败：{error}') from error
    finally:
        temp_path.unlink(missing_ok=True)
        await file.close()


@router.get("")
async def list_papers(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    获取当前用户的论文列表
    """
    papers = await get_user_papers(db, user.id)
    return {
        'code': 200,
        'message': '获取论文列表成功',
        'data': [
            {
                'id': paper.id,
                'title': paper.title,
                'authors': paper.authors,
                'file_name': paper.file_name,
                'file_path': paper.file_path,
                'file_size': paper.file_size,
                'publish_year': paper.publish_year,
                'category': paper.category,
                'created_at': paper.created_at.isoformat() if paper.created_at else None,
            }
            for paper in papers
        ],
    }


@router.get("/{paper_id}")
async def get_paper_detail(
    paper_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    获取论文详情（含全文），供在线阅读页面使用
    """
    paper = await get_paper_by_id(db, paper_id)
    if not paper or paper.user_id != user.id:
        raise HTTPException(status_code=404, detail='论文不存在')
    return {
        'code': 200,
        'message': '获取论文成功',
        'data': {
            'id': paper.id,
            'title': paper.title,
            'authors': paper.authors,
            'abstract': paper.abstract,
            'full_text': paper.full_text,
            'keywords': paper.keywords,
            'journal': paper.journal,
            'publish_year': paper.publish_year,
            'doi': paper.doi,
            'file_name': paper.file_name,
            'file_path': paper.file_path,
            'file_size': paper.file_size,
            'category': paper.category,
            'created_at': paper.created_at.isoformat() if paper.created_at else None,
        },
    }


@router.get("/{paper_id}/file")
async def get_paper_file(
    paper_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    获取论文 PDF 原文件（在线阅读的 iframe 用）
    """
    paper = await get_paper_by_id(db, paper_id)
    if not paper or paper.user_id != user.id:
        raise HTTPException(status_code=404, detail='论文不存在')

    file_path = BACKEND_ROOT / paper.file_path
    if not file_path.exists():
        raise HTTPException(status_code=404, detail='PDF 文件不存在')
    return FileResponse(str(file_path), media_type='application/pdf', filename=paper.file_name)


@router.delete("/{paper_id}")
async def delete_paper(
    paper_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    删除论文：同时清理向量库分片、磁盘 PDF 文件、MySQL 论文记录及其关联分析结果
    """
    paper = await get_paper_by_id(db, paper_id)
    if not paper or paper.user_id != user.id:
        raise HTTPException(status_code=404, detail='论文不存在')

    file_path = BACKEND_ROOT / paper.file_path

    # 1. 删除向量库中该论文的全部分片（Chroma 同步调用，放线程池；失败只记日志）
    try:
        deleted_chunks = await asyncio.to_thread(
            _delete_vector_chunks, paper_id
        )
        logger.info(f"[🗑️ 删除论文]论文 {paper_id} 向量分片删除 {deleted_chunks} 条")
    except Exception as error:
        logger.error(f"[❌ 删除论文]论文 {paper_id} 向量分片删除失败：{error}", exc_info=True)

    # 2. 删除磁盘上的 PDF 文件
    try:
        file_path.unlink(missing_ok=True)
    except Exception as error:
        logger.warning(f"[⚠️ 删除论文]论文 {paper_id} 文件删除失败：{error}")

    # 3. 删除 MySQL 记录（papers + 关联的 paper_analysis）
    await delete_paper_row(db, paper)
    await db.commit()

    return {'code': 200, 'message': '论文已删除', 'data': {'id': paper_id}}


def _delete_vector_chunks(paper_id: int) -> int:
    """同步删除向量库分片（在独立线程中执行）"""
    from app.rag.vector_store import VectorStoreService

    return VectorStoreService().delete_paper_chunks(paper_id)
