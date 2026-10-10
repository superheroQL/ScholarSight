import asyncio
import hashlib
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.papers import Paper
import fitz

from app.utils.extract import (extract_title,extract_authors,
                               extract_abstract,extract_keywords,
                               extract_publish_year,extract_journal,
                               extract_doi)
from app.utils.logger_handler import logger
from app.utils.llm_extract import clean_pdf_metadata, clean_pdf_text


async def check_md5(db: AsyncSession, user_id: int, md5_hex: str) -> Paper | None:
    result = await db.execute(
        select(Paper).where(
            Paper.user_id == user_id,
            Paper.file_md5 == md5_hex,
        )
    )
    return result.scalar_one_or_none()


async def get_paper_by_id(db: AsyncSession, paper_id: int) -> Paper | None:
    result = await db.execute(
        select(Paper).where(Paper.id == paper_id)
    )
    return result.scalar_one_or_none()


async def get_user_papers(db: AsyncSession, user_id: int) -> list[Paper]:
    result = await db.execute(
        select(Paper)
        .where(Paper.user_id == user_id)
        .order_by(Paper.created_at.desc())
    )
    return list(result.scalars().all())


async def get_paper_titles(db: AsyncSession, user_id: int, paper_ids: list[int]) -> dict[int, str]:
    """按 ID 批量查询论文标题（只查当前用户的文献），返回 {paper_id: title}"""
    if not paper_ids:
        return {}
    result = await db.execute(
        select(Paper.id, Paper.title).where(
            Paper.user_id == user_id,
            Paper.id.in_(paper_ids),
        )
    )
    return {row[0]: row[1] for row in result}


async def get_papers_by_ids(db: AsyncSession, user_id: int, paper_ids: list[int]) -> list[Paper]:
    """按 ID 批量查询论文（只查当前用户的文献）"""
    if not paper_ids:
        return []
    result = await db.execute(
        select(Paper).where(
            Paper.user_id == user_id,
            Paper.id.in_(paper_ids),
        )
    )
    return list(result.scalars().all())


async def delete_paper_row(db: AsyncSession, paper: Paper) -> None:
    """删除论文记录及其关联的智能分析结果（paper_analysis）"""
    from app.models.analysis import PaperAnalysis

    await db.execute(
        delete(PaperAnalysis).where(PaperAnalysis.paper_id == paper.id)
    )
    await db.delete(paper)

async def save_paper(db: AsyncSession, user_id: int, temp_path: Path, file_name: str) -> Paper:
    """
    提取 PDF 论文的基础元数据并保存到 papers 数据表

        title       : 论文标题
        authors     : 作者
        abstract    : 摘要
        keywords    : 关键词
        journal     : 期刊 / 会议
        publish_year: 发表年份
        doi         : DOI
        file_name   : 原始文件名
        file_size   : 文件大小（MB）
        category    : 分类
    """
    BACKEND_ROOT = Path(__file__).resolve().parents[2]
    UPLOAD_ROOT = BACKEND_ROOT / 'data' / 'papers'

    # 计算文件 MD5 并去重
    file_md5 = hashlib.md5(temp_path.read_bytes()).hexdigest()
    if await check_md5(db, user_id, file_md5):
        raise HTTPException(status_code=409, detail='该论文已经上传过')

    file_size = temp_path.stat().st_size
    doc = fitz.open(temp_path)
    pdf_metadata = doc.metadata

    # 提取全文
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()

    # 借助大模型（prompts/pdf_prompt.txt）还原/排版 PDF 文本，
    # 与原文比较后选择更优版本入库；PDF 文件本身不做任何修改
    full_text = text
    try:
        import json
        if len(text) <= 20000 :
            cleaned_text = await asyncio.to_thread(clean_pdf_text, text)
            if cleaned_text and len(cleaned_text) >= len(text) * 0.8:
                full_text = cleaned_text
                cleaned_text = json.loads(cleaned_text)  # 检查是否为合法 JSON
                logger.info(f"[💡  论文入库]采用大模型清洗后的文本（{len(full_text)}字 vs 原文{len(text)}字）")
            else:
                logger.info("[💡  论文入库]大模型清洗结果为空或过短，保留原文")

        elif len(text) > 20000 :
            cleaned_text = await asyncio.to_thread(clean_pdf_metadata, text)
            if cleaned_text :
                full_text = cleaned_text
                cleaned_text = json.loads(cleaned_text)  # 检查是否为合法 JSON
                logger.info(f"[💡  论文入库]采用大模型清洗后的元数据")
            else:
                logger.info("[💡  论文入库]大模型清洗结果为空")

    except Exception as error:
        logger.warning(f"[⚠️  论文入库]大模型清洗异常，保留原文：{error}")

    title = cleaned_text["title"] if cleaned_text and "title" in cleaned_text else extract_title(full_text)
    authors = cleaned_text["authors"] if cleaned_text and "authors" in cleaned_text else extract_authors(full_text)
    abstract = cleaned_text["abstract"] if cleaned_text and "abstract" in cleaned_text else extract_abstract(full_text)
    keywords = cleaned_text["keywords"] if cleaned_text and "keywords" in cleaned_text else extract_keywords(full_text)
    publish_year = cleaned_text["publish_year"] if cleaned_text and "publish_year" in cleaned_text else extract_publish_year(full_text)
    journal = cleaned_text["journal"] if cleaned_text and "journal" in cleaned_text else extract_journal(full_text)
    doi = cleaned_text["doi"] if cleaned_text and "doi" in cleaned_text else extract_doi(full_text)
    category = "未分类"

    

    # 将临时文件移动到用户目录
    user_dir = UPLOAD_ROOT / str(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)
    final_path = user_dir / f'{file_md5}_{file_name}'
    temp_path.replace(final_path)

    if len(text) > 20000 :
        full_text = text
        
    # 将提取到的元数据写入 papers 数据表
    try:
        paper = Paper(
            user_id=user_id,
            title=title,
            authors=authors,
            abstract=abstract,
            full_text=text,
            keywords=keywords,
            journal=journal,
            publish_year=publish_year,
            doi=doi,
            file_name=file_name,
            file_path=str(final_path.relative_to(BACKEND_ROOT)).replace('\\', '/'),
            file_md5=file_md5,
            file_size=round(file_size / 1024 / 1024, 4),
            category=category,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db.add(paper)
        await db.flush()
        await db.refresh(paper)
        await db.commit()
        
    except Exception:
        # 入库失败时清理已移动的文件
        final_path.unlink(missing_ok=True)
        raise

    # 论文入库成功后，后台把择优后的文本写入向量数据库（失败不影响论文保存）
    asyncio.create_task(_upload_paper_to_vector_store(paper, full_text))

    return paper


async def _upload_paper_to_vector_store(paper: Paper, full_text: str) -> None:
    """
    将论文全文（原始文本或大模型清洗后的更优文本）写入向量数据库（Chroma）
    只做分片，不改变文本内容；在后台线程执行，失败只记录日志
    """

    def _sync() -> None:
        from app.rag.vector_store import VectorStoreService

        service = VectorStoreService()
        service.add_text(
            full_text,
            metadata={
                "paper_id": paper.id,
                "user_id": paper.user_id,
                "title": paper.title,
                "authors": paper.authors or "",
                "file_name": paper.file_name,
                "file_md5": paper.file_md5,
                "category": paper.category or "",
                "source": paper.file_path,
            },
        )

    try:
        # 向量化耗时较长（分片 + 调用嵌入接口），放到线程池执行
        await asyncio.to_thread(_sync)
    except Exception as error:
        logger.error(f"[❌ 向量入库]论文 id={paper.id} 写入向量库失败：{error}", exc_info=True)