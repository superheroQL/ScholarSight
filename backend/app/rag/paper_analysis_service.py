"""
单篇论文智能分析服务
流程：按分析任务分别构造 Query -> 向量库检索该论文相关片段 -> LLM 结构化信息抽取 -> 汇总 JSON
分析基于论文向量库（RAG），不直接把整篇 PDF 输入 LLM
"""
import json
import re

from app.model.factory import chat_model
from app.utils.prompt_loader import load_paper_analysis_prompts
from app.utils.logger_handler import logger

# 每个分析任务的检索分片数
TOP_K = 8

# 八个分析任务：key（结果字段）/ query（检索问句）/ requirements（任务要求）/ schema（输出格式）
ANALYSIS_TASKS = [
    {
        "key": "research_question",
        "query": "What research problem does this paper address? What is the background, the problem in the field, and the research objective?",
        "requirements": "识别论文试图解决的核心科学问题或工程问题。需要回答：为什么要开展这项研究？当前领域存在什么问题？论文提出了什么研究目标？作者试图验证什么假设？",
        "schema": '{"research_question": {"background": "", "problem": "", "objective": ""}}',
    },
    {
        "key": "core_method",
        "query": "What methods, model architecture and key technical innovations are proposed in this paper?",
        "requirements": "提取论文提出的方法、模型结构以及关键技术创新。需要分析：方法名称、整体框架、核心模块、技术创新点、方法解决的问题。",
        "schema": '{"core_method": {"name": "", "overview": "", "components": [{"name": "", "description": ""}], "innovation": ""}}',
    },
    {
        "key": "datasets",
        "query": "What datasets are used in the experiments of this paper? Dataset name, source, scale, data split and task?",
        "requirements": "提取论文实验所使用的数据资源，需要分析：数据集名称、数据来源、数据规模、数据划分、使用任务。",
        "schema": '{"datasets": [{"name": "", "source": "", "scale": "", "split": "", "task": ""}]}',
    },
    {
        "key": "experimental_results",
        "query": "What are the experimental tasks, evaluation metrics, compared baselines and experimental results in this paper?",
        "requirements": "提取论文实验设计和核心实验发现，需要分析：实验任务、评价指标、对比方法、实验结果、性能提升。",
        "schema": '{"experimental_results": {"tasks": [{"task": "", "metrics": "", "comparison": "", "result": ""}], "main_findings": ""}}',
    },
    {
        "key": "core_conclusion",
        "query": "What does this paper finally conclude? What are the key points and main contributions?",
        "requirements": "总结论文最终证明了什么，以及作者的主要观点。需要回答：论文验证了什么？方法是否达到预期目标？研究贡献是什么？",
        "schema": '{"core_conclusion": {"summary": "", "key_points": [""]}}',
    },
    {
        "key": "limitations_and_insights",
        "query": "What are the limitations of this paper and what insights can be drawn for future research?",
        "requirements": "从论文实验和方法中分析不足，并总结对后续研究的启发。局限包括：方法限制、实验限制、数据限制、泛化能力问题；研究启示包括：可以改进哪些方向、对未来研究有什么价值。",
        "schema": '{"limitations_and_insights": {"limitations": [""], "research_insights": [""]}}',
    },
    {
        "key": "evidence_and_implications",
        "query": "What are the main contributions and key claims of this paper? What original statements support these claims?",
        "requirements": (
            "增强 RAG 的可解释性：提取论文中 3~5 个重要观点（claim），每个观点必须关联支撑它的原文证据"
            "（evidence，逐字摘自片段原文，不能改写或概括）、证据来源（source，含 page/section/chunk_id，"
            "chunk_id 必须使用片段标注 [CHUNK xxx] 中的值，page 在片段没有页码信息时填 0，section 根据片段内容推断所在章节）"
            "以及该观点对后续研究的启示（implication）。"
            "示例：{\"claim\": \"该方法完全基于注意力机制\", \"evidence\": \"We propose a new simple network architecture based solely on attention mechanisms.\", "
            "\"source\": {\"page\": 1, \"section\": \"Introduction\", \"chunk_id\": \"abc123\"}, \"implication\": \"说明序列模型可以减少对循环结构的依赖\"}。"
            "只要片段中能找到依据就必须输出对应条目，不得输出空数组。"
        ),
        "schema": '{"evidence_and_implications": [{"claim": "", "evidence": "", "source": {"page": 0, "section": "", "chunk_id": ""}, "implication": ""}]}',
        "top_k": 12,
    },
    {
        "key": "further_questions",
        "query": "What are the open questions and future research directions suggested by this paper?",
        "requirements": "模拟科研助手，基于论文内容生成值得进一步探索的问题（例如：论文方法是否适用于其他任务？如果改变某个模块会怎样？是否存在实验验证不足？未来可以研究哪些方向？），每个问题说明提出该问题的原因。",
        "schema": '{"further_questions": [{"question": "", "reason": ""}]}',
    },
]


def _parse_json(text: str):
    """从模型输出中解析 JSON（容忍 markdown 代码块等杂质）"""
    if not text:
        return None
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except Exception:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(cleaned[start:end + 1])
            except Exception:
                pass
        logger.warning(f"[⚠️ 论文分析]JSON 解析失败，模型输出前 200 字：{cleaned[:200]}")
        return None


def analyze_paper(paper_id: int, user_id: int, title: str) -> dict:
    """
    对单篇论文执行全部分析任务，返回结构化结果字典
    {research_question, core_method, datasets, ...}
    单个任务失败不影响其他任务
    """
    from app.rag.vector_store import VectorStoreService

    vector_store = VectorStoreService()
    prompt_template = load_paper_analysis_prompts()

    result: dict = {}
    for task in ANALYSIS_TASKS:
        key = task["key"]
        try:
            # 1. 按任务构造 Query，在向量库中检索该论文相关片段（带 chunk_id，供证据溯源）
            top_k = task.get("top_k", TOP_K)
            chunks = vector_store.search_with_ids(task["query"], paper_ids=[paper_id], k=top_k)

            if not chunks:
                logger.warning(f"[⚠️ 论文分析]论文 {paper_id} 在向量库中没有分片，任务「{key}」跳过")
                result[key] = None
                continue

            evidence_text = "\n\n".join(
                f"[CHUNK {chunk['id']}]\n{chunk['content']}" for chunk in chunks
            )

            # 2. LLM 按任务要求做结构化信息抽取
            prompt = prompt_template.format(
                paper_title=title,
                task_requirements=task["requirements"],
                schema=task["schema"],
                evidence=evidence_text,
            )
            response = chat_model.invoke(prompt)
            parsed = _parse_json((response.content or "") if hasattr(response, "content") else str(response))

            # 3. 从模型输出中取该任务对应的顶层字段
            if isinstance(parsed, dict) and key in parsed:
                result[key] = parsed[key]
            elif isinstance(parsed, dict):
                result[key] = parsed
            else:
                result[key] = None
            logger.info(f"[✅ 论文分析]论文 {paper_id} 任务「{key}」完成")
        except Exception as error:
            logger.error(f"[❌ 论文分析]论文 {paper_id} 任务「{key}」失败：{error}", exc_info=True)
            result[key] = None

    return result
