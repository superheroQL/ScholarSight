"""
多论文对比分析服务
流程：分别在每篇选中文献的向量分片中检索 -> 按 prompts/multi_paper_analysis_prompt.txt
提示词由 LLM 输出 12 个维度的结构化分析 -> 映射为前端对比矩阵(matrix) + 综合分析(synthesis)
"""
from app.model.factory import chat_model
from app.rag.paper_analysis_service import _parse_json
from app.utils.prompt_loader import load_multi_paper_analysis_prompts
from app.utils.logger_handler import logger

# 每篇文献检索的分片数与字符上限
TOP_K_PER_PAPER = 8
MAX_CHARS_PER_PAPER = 6000

# 无主题时的通用检索问句
DEFAULT_QUERY = "research problem, proposed method, experiments, results and conclusions of this paper"


def _build_matrix(analysis: dict, paper_ids: list[int], titles: dict[int, str]) -> list[dict]:
    """把 LLM 分析结果映射为前端对比矩阵：每行一个维度，值为 {paper_id: 文本}"""
    labels = {f"论文{i + 1}": str(pid) for i, pid in enumerate(paper_ids)}

    def resolve(label) -> str | None:
        """模型输出的论文名 -> paper_id（按 论文N 编号匹配，失败时按标题匹配）"""
        text = str(label or "")
        for key, pid in labels.items():
            if key in text:
                return pid
        for pid, title in titles.items():
            if title and title[:20] in text:
                return str(pid)
        return None

    def make_row(dimension: str) -> dict:
        return {"dimension": dimension, "values": {str(pid): "" for pid in paper_ids}}

    rows = {
        "research_problem": make_row("研究问题"),
        "method": make_row("核心方法"),
        "advantages": make_row("优点"),
        "limitations": make_row("局限"),
        "application": make_row("适用场景"),
        "datasets": make_row("数据集"),
    }

    # 研究问题（问题 + 目标）
    for item in analysis.get("research_questions") or []:
        pid = resolve(item.get("paper"))
        if not pid:
            continue
        parts = [item.get("problem") or "", item.get("objective") or ""]
        rows["research_problem"]["values"][pid] = "；".join(p for p in parts if p)

    # 方法对比（方法/优点/局限/适用场景）
    for item in analysis.get("method_comparison") or []:
        pid = resolve(item.get("paper"))
        if not pid:
            continue
        rows["method"]["values"][pid] = item.get("method") or ""
        rows["advantages"]["values"][pid] = "；".join(item.get("advantages") or [])
        rows["limitations"]["values"][pid] = "；".join(item.get("limitations") or [])
        rows["application"]["values"][pid] = item.get("application_scope") or ""

    # 数据集（哪些论文用了哪些数据集）
    for ds in (analysis.get("experiment_analysis") or {}).get("datasets") or []:
        name = ds.get("name") or ""
        if not name:
            continue
        for label in ds.get("used_by") or []:
            pid = resolve(label)
            if not pid:
                continue
            current = rows["datasets"]["values"][pid]
            rows["datasets"]["values"][pid] = f"{current}；{name}".strip("；")

    # 只保留有内容的行
    return [row for row in rows.values() if any(v for v in row["values"].values())]


def _build_synthesis(analysis: dict) -> dict:
    """把 LLM 分析结果映射为 AI 综合分析（overview + points）"""
    overview_parts = []
    ro = analysis.get("research_overview") or {}
    if ro.get("field"):
        overview_parts.append(f"这些论文共同关注的研究领域是{ro['field']}。")
    if ro.get("common_problem"):
        overview_parts.append(f"该领域主要解决{ro['common_problem']}。")
    if ro.get("research_trend"):
        overview_parts.append(f"研究趋势：{ro['research_trend']}。")
    overview = "".join(overview_parts) or "已完成多论文对比分析，详见下方要点。"

    points = []
    for category in (analysis.get("method_categories") or [])[:3]:
        content = category.get("characteristics") or ""
        if category.get("development"):
            content += f"（演进：{category['development']}）"
        if content:
            points.append({"title": f"技术路线：{category.get('category') or '—'}", "content": content})

    ra = analysis.get("result_analysis") or {}
    if ra.get("performance_comparison") or ra.get("key_findings"):
        findings = "；".join(ra.get("key_findings") or [])
        points.append({
            "title": "实验结果",
            "content": (ra.get("performance_comparison") or "") + ("。关键发现：" + findings if findings else ""),
        })

    re_ = analysis.get("research_evolution") or {}
    if re_.get("timeline") or re_.get("development_direction"):
        content = re_.get("timeline") or ""
        directions = "；".join(re_.get("development_direction") or [])
        if directions:
            content += ("。演进方向：" + directions)
        points.append({"title": "研究演进", "content": content})

    challenges = [c for c in (analysis.get("research_challenges") or []) if c]
    if challenges:
        points.append({"title": "当前挑战", "content": "；".join(challenges[:5])})

    directions = (analysis.get("future_directions") or [])[:3]
    if directions:
        content = "；".join(
            f"{d.get('direction') or ''}（{d.get('reason') or ''}）" for d in directions
        )
        points.append({"title": "未来方向", "content": content})

    return {"overview": overview, "points": points[:6]}


def analyze_multi_papers(paper_ids: list[int], papers_info: dict[int, dict]) -> tuple[dict, list, dict]:
    """
    对多篇论文执行综合分析。
    papers_info: {paper_id: {title, authors, publish_year}}
    返回 (analysis 原始12维结果, matrix 对比矩阵, synthesis 综合分析)
    """
    from app.rag.vector_store import VectorStoreService

    vector_store = VectorStoreService()
    titles = {pid: info.get("title") or f"论文 {pid}" for pid, info in papers_info.items()}

    # 1. 每篇论文检索相关分片（带论文编号标注）
    context_parts: list[str] = []
    paper_list_lines: list[str] = []
    for index, pid in enumerate(paper_ids, 1):
        info = papers_info.get(pid) or {}
        title = titles[pid]
        authors = info.get("authors") or ""
        year = info.get("publish_year") or ""
        meta = "，".join(p for p in [authors, str(year) if year else ""] if p)
        paper_list_lines.append(f"论文{index}：{title}" + (f"（{meta}）" if meta else ""))

        chunks = vector_store.search_with_ids(DEFAULT_QUERY, paper_ids=[pid], k=TOP_K_PER_PAPER)
        if not chunks:
            logger.warning(f"[⚠️ 多论文分析]论文 {pid} 在向量库中没有分片，跳过")
            continue
        parts = [f"【论文{index}：{title}】"]
        total_chars = 0
        for chunk in chunks:
            if total_chars + len(chunk["content"]) > MAX_CHARS_PER_PAPER:
                break
            parts.append(chunk["content"])
            total_chars += len(chunk["content"])
        context_parts.append("\n".join(parts))

    if not context_parts:
        return {}, [], {"overview": "", "points": []}

    # 2. 按提示词模板生成 12 维分析（模板含 {topic}/{papers}/{context} 占位符，用 replace 填充避免 JSON 花括号冲突）
    template = load_multi_paper_analysis_prompts()
    prompt = (
        template.replace("{topic}", "多篇论文的对比分析")
        .replace("{papers}", "\n".join(paper_list_lines))
        .replace("{context}", "\n\n".join(context_parts))
    )
    response = chat_model.invoke(prompt)
    analysis = _parse_json((response.content or "") if hasattr(response, "content") else str(response))
    if not isinstance(analysis, dict):
        logger.error("[❌ 多论文分析]模型输出不是合法 JSON，返回空结果")
        return {}, [], {"overview": "", "points": []}

    # 3. 映射为前端展示结构
    matrix = _build_matrix(analysis, paper_ids, titles)
    synthesis = _build_synthesis(analysis)
    return analysis, matrix, synthesis
