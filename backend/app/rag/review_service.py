"""
文献综述生成服务
流程：按综述主题构造 Query -> 分别在每篇选中文献的向量分片中检索 ->
汇总为 RAG 上下文 -> 按 prompts/review_prompt.txt 提示词由 LLM 生成中文文献综述
"""
from app.model.factory import chat_model
from app.utils.prompt_loader import load_review_prompts
from app.utils.logger_handler import logger

# 每篇文献检索的分片数
TOP_K_PER_PAPER = 6

# 每篇文献的片段计入上下文的最大字符数（控制总上下文长度）
MAX_CHARS_PER_PAPER = 6000


def generate_review(topic: str, paper_ids: list[int], paper_titles: dict[int, str]) -> str:
    """
    基于多篇论文的向量分片生成文献综述，返回综述全文（Markdown）
    检索不到任何内容时返回空字符串，由调用方提示用户
    """
    from app.rag.vector_store import VectorStoreService

    vector_store = VectorStoreService()

    # 1. 按主题 Query，分别在每篇选中文献中检索相关分片
    context_parts: list[str] = []
    for paper_id in paper_ids:
        chunks = vector_store.search_with_ids(topic, paper_ids=[paper_id], k=TOP_K_PER_PAPER)
        if not chunks:
            logger.warning(f"[⚠️ 文献综述]论文 {paper_id} 在向量库中没有相关分片，跳过")
            continue

        title = paper_titles.get(paper_id, f"论文 {paper_id}")
        parts = [f"【{title}】"]
        total_chars = 0
        for chunk in chunks:
            content = chunk["content"]
            if total_chars + len(content) > MAX_CHARS_PER_PAPER:
                break
            parts.append(f"[CHUNK {chunk['id']}] {content}")
            total_chars += len(content)
        context_parts.append("\n".join(parts))

    if not context_parts:
        return ""

    context = "\n\n".join(context_parts)

    # 2. 按 review_prompt.txt 提示词模板生成综述（模板使用 {{query}} / {{context}} 占位符）
    prompt_template = load_review_prompts()
    prompt = prompt_template.replace("{{query}}", topic).replace("{{context}}", context)
    response = chat_model.invoke(prompt)
    return (response.content or "").strip()
