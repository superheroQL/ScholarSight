"""
借助大模型（prompts/pdf_prompt.txt）还原/排版 PDF 文本
原则：只做排版恢复，不改变原文内容；失败时返回 None，由调用方回退到原始文本
"""
from app.model.factory import chat_model
from app.utils.prompt_loader import load_pdf_metadata_prompts, load_pdf_prompts
from app.utils.logger_handler import logger

# 超过该长度的文本不送大模型清洗（控制成本与耗时），直接保留原文
MAX_INPUT_CHARS = 20000


def clean_pdf_text(text: str) -> str | None:
    """
    按 prompts/pdf_prompt.txt 的提示词让大模型还原 PDF 文本。
    成功返回清洗后的文本；任何失败返回 None（调用方保留原文）。
    """
    if not text or not text.strip():
        return None

    if len(text) > MAX_INPUT_CHARS:
        logger.warning(f"[⚠️  PDF清洗]文本过长（{len(text)}字，上限{MAX_INPUT_CHARS}），跳过模型清洗，保留原文")
        return None

    try:
        prompt_template = load_pdf_metadata_prompts()
        prompt = prompt_template.replace("{pdf_text}", text)
        response = chat_model.invoke(prompt)
        cleaned = (response.content or "").strip()
        if not cleaned:
            logger.warning("[⚠️ PDF清洗]模型返回内容为空，保留原文")
            return None
        return cleaned
    except Exception as error:
        logger.error(f"[❌ PDF清洗]模型清洗失败：{error}", exc_info=True)
        return None

def clean_pdf_metadata(text: str) -> str | None:
    """
    按 prompts/pdf_metadata_prompt.txt 的提示词让大模型提取论文元数据。
    成功返回模型输出的 JSON 文本；任何失败返回 None（调用方保留原文）。
    """
    if not text or not text.strip():
        return None

    # 元数据（标题/作者/摘要等）一般位于论文开头，超长时只取前 MAX_INPUT_CHARS 字符
    if len(text) > MAX_INPUT_CHARS:
        logger.info(f"[⚠️  PDF元数据]文本过长（{len(text)}字），截取前 {MAX_INPUT_CHARS} 字进行提取")
        text = text[:MAX_INPUT_CHARS]

    try:
        prompt_template = load_pdf_metadata_prompts()
        prompt = prompt_template.replace("{pdf_text}", text)
        response = chat_model.invoke(prompt)
        cleaned = (response.content or "").strip()
        print(f"\n\n[💡 PDF元数据]模型输出：{cleaned}\n\n")
        if not cleaned:
            logger.warning("[⚠️ PDF元数据]模型返回空内容，保留原文")
            return None
        return cleaned
    except Exception as error:
        logger.error(f"[❌ PDF元数据]模型提取失败：{error}", exc_info=True)
        return None
