import re
import fitz


# def extract_title(doc: fitz.Document) -> str:
#     """
#     基于 PDF 第一页的文本块、字体大小、位置等信息提取论文标题。
#     """
#     if len(doc) == 0:
#         return ""

#     page = doc[0]
#     page_height = page.rect.height
#     blocks = page.get_text("dict")["blocks"]
#     candidates = []

#     # 收集第一页所有文本 span
#     spans = []

#     for block in blocks:
#         if "lines" not in block:
#             continue
#         for line in block["lines"]:
#             for span in line["spans"]:
#                 text = span["text"].strip()
#                 if not text:
#                     continue
#                 spans.append({
#                     "text": text,
#                     "size": span["size"],
#                     "font": span["font"],
#                     "bbox": span["bbox"],
#                     "y": span["bbox"][1]
#                 })

#     if not spans:
#         return ""

#     # 计算正文主要字体大小
#     font_sizes = [round(s["size"], 1) for s in spans]
#     from collections import Counter
#     size_counter = Counter(font_sizes)
#     body_font_size = size_counter.most_common(1)[0][0]

#     # 标题候选
#     for span in spans:
#         text = span["text"]
#         size = span["size"]
#         font = span["font"]
#         y = span["y"]

#         score = 0
#         lower_text = text.lower()

#         # 1. 过滤明显不是标题的内容
#         invalid_patterns = [
#             r"^abstract$",
#             r"^keywords?$",
#             r"^introduction$",
#             r"^references$",
#             r"^contents$",
#             r"^doi[:\s]",
#             r"^arxiv[:\s]",
#             r"^https?://",
#             r"^www\.",
#             r"^received[:\s]",
#             r"^accepted[:\s]",
#             r"^copyright",
#         ]

#         if any(re.search(pattern, lower_text) for pattern in invalid_patterns):
#             continue
#         # DOI / URL / 邮箱
#         if "doi.org" in lower_text:
#             continue
#         if "@" in text:
#             continue

#         # 2. 长度
#         if 10 <= len(text) <= 200:
#             score += 2
#         if len(text) < 5:
#             score -= 5

#         # 3. 字体大小
#         if size >= body_font_size * 2:
#             score += 6
#         elif size >= body_font_size * 1.6:
#             score += 5
#         elif size >= body_font_size * 1.3:
#             score += 3
#         elif size > body_font_size:
#             score += 1

#         # 4. 页面位置
#         # 标题通常位于第一页顶部
#         if y < page_height * 0.20:
#             score += 4
#         elif y < page_height * 0.35:
#             score += 2

#         # 5. 粗体
#         if any(
#             keyword in font.lower()
#             for keyword in ["bold", "semibold", "heavy"]
#         ):
#             score += 2

#         # 6. 过滤作者/机构信息
#         author_keywords = [
#             "university",
#             "institute",
#             "department",
#             "school of",
#             "laboratory",
#             "lab.",
#             "college",
#         ]

#         if any(keyword in lower_text for keyword in author_keywords):
#             score -= 4

#         # 7. 特殊字符过多
#         if text.count(",") >= 4:
#             score -= 2

#         if text.count("@") > 0:
#             score -= 5

#         candidates.append({
#             "text": text,
#             "score": score,
#             "size": size,
#             "y": y,
#             "font": font,
#             "bbox": span["bbox"]
#         })

#     if not candidates:
#         return ""

#     # 按分数排序
#     candidates.sort(
#         key=lambda x: x["score"],
#         reverse=True
#     )

#     best = candidates[0]

#     # 分数太低，认为无法可靠判断
#     if best["score"] < 3:
#         return ""

#     title = best["text"]

#     # 8. 尝试合并标题的下一行
#     best_y = best["y"]
#     best_size = best["size"]

#     next_lines = []

#     for span in spans:
#         if span["text"] == best["text"]:
#             continue

#         # 字体大小接近
#         if abs(span["size"] - best_size) > 2:
#             continue

#         # 必须位于标题下面
#         if span["y"] <= best_y:
#             continue

#         # 两行之间距离不能太大
#         if span["y"] - best_y > best_size * 2:
#             continue

#         # 过滤明显不是标题的内容
#         lower = span["text"].lower()

#         if lower in {
#             "abstract",
#             "keywords",
#             "introduction"
#         }:
#             continue

#         next_lines.append(span)

#     if next_lines:
#         next_lines.sort(key=lambda x: x["y"])

#         next_line = next_lines[0]

#         # 如果第二行也是一个合理的标题行，则合并
#         if len(next_line["text"]) >= 3:
#             title = title + " " + next_line["text"]

#     # 9. 最终清洗
#     title = re.sub(r"\s+", " ", title).strip()

#     return title

def extract_title(text: str) -> str:
    """
    简单从论文开头提取标题
    """

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    if not lines:
        return ""

    # 简单策略：
    # 默认取前 10 行中较长的一行作为标题候选
    candidates = []

    for line in lines[:15]:
        if 10 <= len(line) <= 200:
            candidates.append(line)

    if candidates:
        return candidates[0]

    return ""


# 提取论文作者
def extract_authors(text: str) -> str:

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    for i, line in enumerate(lines[:30]):

        if line.lower() == "abstract":

            # Abstract 前面的几行通常存在作者信息
            candidates = lines[max(0, i - 5):i]

            return ", ".join(candidates[-2:])

    return ""


# 提取论文摘要
def extract_abstract(text: str) -> str:

    pattern = re.compile(
        r'(?is)\babstract\b[:\s]*(.*?)(?=\n\s*(keywords?|index terms|1\.?\s*introduction|introduction)\b)'
    )

    match = pattern.search(text)

    if match:
        return re.sub(r'\s+', ' ', match.group(1)).strip()

    return ""


# 提取论文关键词
def extract_keywords(text: str) -> str:

    pattern = re.compile(
        r'(?i)(keywords?|index terms)\s*[:：]\s*(.*)'
    )

    match = pattern.search(text)

    if match:
        keywords = match.group(2)

        # 防止把下一段正文也提取进去
        keywords = keywords.split("\n")[0]

        return keywords.strip()

    return ""


# 提取论文 DOI
def extract_doi(text: str) -> str:

    pattern = r'10\.\d{4,9}/[-._;()/:A-Z0-9]+'

    match = re.search(
        pattern,
        text,
        re.IGNORECASE
    )

    if match:
        doi = match.group(0)

        # 清理末尾标点
        doi = doi.rstrip(".,;")

        return doi

    return ""


# 提取论文发表年份
def extract_publish_year(text: str):

    # 优先寻找 19xx / 20xx 年份
    years = re.findall(
        r'\b(?:19|20)\d{2}\b',
        text[:10000]
    )

    if years:
        return int(years[0])

    return None


# 提取论文期刊 / 会议名称
def extract_journal(text: str) -> str:

    # 基础版本暂时从前 3000 字符中寻找常见期刊信息
    first_part = text[:3000]

    patterns = [
        r'(?i)journal\s+of\s+[A-Za-z0-9\s\-]+',
        r'(?i)proceedings\s+of\s+[A-Za-z0-9\s\-]+',
    ]

    for pattern in patterns:

        match = re.search(pattern, first_part)

        if match:
            return match.group(0).strip()

    return ""