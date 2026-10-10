from pydantic import BaseModel


class ChatAskRequest(BaseModel):
    question: str
    paper_ids: list[int] = []
    session_id: int | None = None   # 会话窗口 id，为空表示新开会话
    messages: list = []             # 前端携带的历史消息，当前版本以数据库中的会话记录为准