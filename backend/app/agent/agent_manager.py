# Agent 构建较重（加载模型工厂、RAG服务、向量库），懒加载 + 复用单例
import threading


_agent = None
_agent_lock = threading.Lock()


def _get_agent():
    # 这个函数里的 _agent 变量，使用的是函数外面定义的那个 _agent，而不是创建一个新的局部变量。
    global _agent
    if _agent is None:
        with _agent_lock:
            if _agent is None:
                from app.agent.react_agent import ReactAgent
                _agent = ReactAgent()
    return _agent