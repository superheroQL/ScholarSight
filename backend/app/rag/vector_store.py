import sys
import os
# 将项目根目录加入 sys.path，确保 backend 等模块可导入
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from langchain_chroma import Chroma
from langchain_core.documents import Document
from utils.config_handler import chroma_conf
from model.factory import embed_model
from langchain_text_splitters import RecursiveCharacterTextSplitter
from utils.path_tool import get_abs_path
from utils.file_handler import docx_loader, pdf_loader, txt_loader, listdir_with_allowed_type, get_file_md5_hex
from utils.logger_handler import logger

# 嵌入接口单次请求的最大文本条数（阿里云百炼 DashScope 限制为 20）
EMBED_BATCH_SIZE = 20


def _load_documents(read_path: str) -> list[Document]:
    """按文件后缀选择对应的加载器读取文档"""
    if read_path.endswith("txt"):
        return txt_loader(read_path)

    if read_path.endswith("pdf"):
        return pdf_loader(read_path)

    if read_path.endswith("docx"):
        return docx_loader(read_path)

    return []


class VectorStoreService:
    def __init__(self):
        persist_dir = get_abs_path(chroma_conf['persist_directory'])
        self.vector_store = Chroma(
            collection_name=chroma_conf["collection_name"],
            embedding_function=embed_model,
            persist_directory=persist_dir,
        )

        self.spliter = RecursiveCharacterTextSplitter(
            chunk_size=chroma_conf["chunk_size"],
            chunk_overlap=chroma_conf["chunk_overlap"],
            separators=chroma_conf["separators"],
            length_function=len,
        )

    def get_retriever(self):
        return self.vector_store.as_retriever(search_kwargs={"k": chroma_conf["k"]})

    def search(self, query: str, paper_ids: list[int] | None = None, k: int | None = None) -> list[Document]:
        """
        相似度检索；指定 paper_ids 时通过元数据过滤，只检索选中文献的分片
        """
        k = k or chroma_conf["k"]
        if paper_ids:
            return self.vector_store.similarity_search(
                query, k=k, filter={"paper_id": {"$in": paper_ids}}
            )
        return self.vector_store.similarity_search(query, k=k)

    def search_with_ids(self, query: str, paper_ids: list[int] | None = None, k: int | None = None) -> list[dict]:
        """
        相似度检索并返回每个分片的 chunk_id（用于证据溯源）
        返回 [{"id": chunk_id, "content": 文本, "metadata": {...}}, ...]
        """
        k = k or chroma_conf["k"]
        where = {"paper_id": {"$in": paper_ids}} if paper_ids else None
        query_embedding = self.vector_store._embedding_function.embed_query(query)
        result = self.vector_store._collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            where=where,
            include=["documents", "metadatas"],
        )
        documents = result.get("documents") or [[]]
        metadatas = result.get("metadatas") or [[]]
        ids = result.get("ids") or [[]]
        items = []
        for index, content in enumerate(documents[0]):
            items.append({
                "id": ids[0][index],
                "content": content,
                "metadata": metadatas[0][index] or {},
            })
        return items

    def _check_md5_hex(self, md5_for_check: str) -> bool:
        """检查文件 MD5 是否已经处理过（已写入向量库）"""
        md5_store = get_abs_path(chroma_conf["md5_hex_store"])
        if not os.path.exists(md5_store):
            # 创建文件
            os.makedirs(os.path.dirname(md5_store), exist_ok=True)
            open(md5_store, "w", encoding="utf-8").close()
            return False            # md5 没处理过

        with open(md5_store, "r", encoding="utf-8") as f:
            for line in f.readlines():
                line = line.strip()
                if line == md5_for_check:
                    return True     # md5 处理过

            return False            # md5 没处理过

    def _add_documents(self, documents: list[Document]):
        """分批写入向量库，避免单次请求超过嵌入接口的批量上限"""
        for i in range(0, len(documents), EMBED_BATCH_SIZE):
            self.vector_store.add_documents(documents[i:i + EMBED_BATCH_SIZE])

    def _save_md5_hex(self, md5_for_check: str):
        md5_store = get_abs_path(chroma_conf["md5_hex_store"])
        os.makedirs(os.path.dirname(md5_store), exist_ok=True)
        with open(md5_store, "a", encoding="utf-8") as f:
            f.write(md5_for_check + "\n")

    def add_file(self, file_path: str, metadata: dict | None = None) -> bool:
        """
        将单个文件读取、分片并写入向量库，按文件 MD5 去重
        :param file_path: 文件绝对路径
        :param metadata: 附加到每个分片上的元数据（如 paper_id / user_id / title）
        :return: 是否成功写入向量库
        """
        # md5_hex = get_file_md5_hex(file_path)
        # if not md5_hex:
        #     logger.error(f"[向量入库]{file_path}计算MD5失败，跳过")
        #     return False

        # if self._check_md5_hex(md5_hex):
        #     logger.info(f"[向量入库]{file_path}内容已经存在向量库内，跳过")
        #     return False

        try:
            documents: list[Document] = _load_documents(file_path)

            if not documents:
                logger.warning(f"[向量入库]{file_path}内没有有效文本内容，跳过")
                return False

            split_document: list[Document] = self.spliter.split_documents(documents)

            if not split_document:
                logger.warning(f"[向量入库]{file_path}分片后没有有效文本内容，跳过")
                return False

            # 给每个分片都带上论文元数据，便于按论文检索与删除
            if metadata:
                for doc in split_document:
                    doc.metadata.update(metadata)

            # 将内容存入向量库
            self._add_documents(split_document)

            # # 记录这个已经处理好的文件的md5，避免下次重复加载
            # self._save_md5_hex(md5_hex)

            logger.info(f"[向量入库]{file_path}写入向量库成功")
            return True
        except Exception as e:
            # exc_info为True会记录详细的报错堆栈，如果为False仅记录报错信息本身
            logger.error(f"[向量入库]{file_path}写入失败：{str(e)}", exc_info=True)
            return False

    def delete_paper_chunks(self, paper_id: int) -> int:
        """
        删除向量库中某篇论文的全部分片（按 paper_id 元数据过滤），返回删除条数
        """
        try:
            result = self.vector_store._collection.delete(where={"paper_id": paper_id})
            # chromadb 不同版本返回值不同（dict / list / int），统一解析
            if isinstance(result, dict):
                count = len(result.get("ids") or [])
            elif isinstance(result, (list, tuple)):
                count = len(result)
            else:
                try:
                    count = int(result or 0)
                except (TypeError, ValueError):
                    count = 0
            logger.info(f"[✅ 向量删除]论文 {paper_id} 已从向量库删除 {count} 个分片")
            return count
        except Exception as error:
            logger.error(f"[❌ 向量删除]论文 {paper_id} 删除失败：{error}", exc_info=True)
            return 0

    def add_text(self, content: str, metadata: dict | None = None, source: str = "pdf_text") -> bool:
        """
        将一段文本内容分片并写入向量库（论文全文 / 大模型清洗后的文本走这里）
        不改变文本内容本身，只做分片
        """
        try:
            document = Document(page_content=content, metadata={"source": source})
            split_document: list[Document] = self.spliter.split_documents([document])

            if not split_document:
                logger.warning(f"[向量入库]文本分片后没有有效内容，跳过")
                return False

            # 给每个分片都带上论文元数据，便于按论文检索与删除
            if metadata:
                for doc in split_document:
                    doc.metadata.update(metadata)

            # 分批写入向量库
            self._add_documents(split_document)

            logger.info(f"[向量入库]文本内容写入向量库成功（{len(split_document)}个分片）")
            return True
        except Exception as e:
            logger.error(f"[向量入库]文本写入失败：{str(e)}", exc_info=True)
            return False

    def load_document(self):
        """
        从数据文件夹内读取数据文件，转为向量存入向量库
        要计算文件的MD5做去重
        :return: None
        """

        # 获取允许的文件类型的文件列表 返回文件绝对路径的元组
        allowed_files_path: tuple[str] = listdir_with_allowed_type(
            get_abs_path(chroma_conf["data_path"]),
            tuple(chroma_conf["allow_knowledge_file_types"]),
        )

        for path in allowed_files_path:
            # 获取文件的MD5
            md5_hex = get_file_md5_hex(path)

            if self._check_md5_hex(md5_hex):
                logger.info(f"[加载知识库]{path}内容已经存在知识库内，跳过")
                continue

            try:
                documents: list[Document] = _load_documents(path)

                if not documents:
                    logger.warning(f"[加载知识库]{path}内没有有效文本内容，跳过")
                    continue

                split_document: list[Document] = self.spliter.split_documents(documents)

                if not split_document:
                    logger.warning(f"[加载知识库]{path}分片后没有有效文本内容，跳过")
                    continue

                # 将内容存入向量库
                self._add_documents(split_document)

                # 记录这个已经处理好的文件的md5，避免下次重复加载
                self._save_md5_hex(md5_hex)

                logger.info(f"[加载知识库]{path} 内容加载成功")
            except Exception as e:
                # exc_info为True会记录详细的报错堆栈，如果为False仅记录报错信息本身
                logger.error(f"[加载知识库]{path}加载失败：{str(e)}", exc_info=True)
                continue


if __name__ == '__main__':
    vs = VectorStoreService()

    vs.load_document()

    retriever = vs.get_retriever()

    res = retriever.invoke("小孩")
    for r in res:
        print(r.page_content)
        print("-"*20)


 