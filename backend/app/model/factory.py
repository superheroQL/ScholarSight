from abc import ABC, abstractmethod
import sys
import os
# 将项目根目录加入 sys.path，确保 backend 等模块可导入
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from typing import Optional
from dotenv import load_dotenv
from langchain_core.embeddings import Embeddings
from langchain_community.chat_models.tongyi import BaseChatModel
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_community.chat_models.tongyi import ChatTongyi
from utils.config_handler import rag_conf

# 加载环境变量
load_dotenv()

class BaseModelFactory(ABC):
    @abstractmethod
    def generator(self) -> Optional[Embeddings | BaseChatModel]:
        pass


class ChatModelFactory(BaseModelFactory):
    def generator(self) -> Optional[Embeddings | BaseChatModel]:
        # 按 .env 中 LLM_TYPE 选择聊天模型：OLLAMA（本地）或 ALIYUN（DashScope 百炼）
        llm_type = (os.getenv("LLM_TYPE") or "ALIYUN").upper()
        if llm_type == "OLLAMA":
            from langchain_ollama import ChatOllama
            return ChatOllama(
                model=os.getenv("OLLAMA_MODEL_NAME"),
                base_url=os.getenv("OLLAMA_BASE_URL") or "http://localhost:11434",
            )
        return ChatTongyi(
            model=os.getenv("CHAT_MODEL_NAME"),
            dashscope_api_key=os.getenv("ALIYUN_ACCESS_KEY_SECRET"),
        )


class EmbeddingsFactory(BaseModelFactory):
    def generator(self) -> Optional[Embeddings | BaseChatModel]:
        # 按 .env 中 EMBED_MODEL_TYPE 选择嵌入模型：OLLAMA（本地免费）或 ALIYUN（DashScope 收费）
        embed_type = (os.getenv("EMBED_MODEL_TYPE") or "ALIYUN").upper()
        if embed_type == "OLLAMA":
            from langchain_ollama import OllamaEmbeddings
            return OllamaEmbeddings(
                model=os.getenv("TEXT_EMBEDDING_MODEL_NAME"),
                base_url=os.getenv("OLLAMA_BASE_URL") or "http://localhost:11434",
            )
        return DashScopeEmbeddings(
            model=os.getenv("ALIYUN_EMBED_MODEL_NAME"),
            dashscope_api_key=os.getenv("ALIYUN_ACCESS_KEY_SECRET"),
        )


chat_model = ChatModelFactory().generator()
embed_model = EmbeddingsFactory().generator()
