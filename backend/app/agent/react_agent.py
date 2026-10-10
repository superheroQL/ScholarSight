import sys
import os
# 将项目根目录加入 sys.path，确保 backend 等模块可导入
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from langchain.agents import create_agent
from langchain_core.messages import AIMessage
from model.factory import chat_model
from utils.prompt_loader import load_system_prompts
from agent.tools.agent_tools import (rag_summarize, get_weather, get_user_location, get_user_id,
                                     get_current_month, fetch_external_data, fill_context_for_report)
from agent.tools.middleware import monitor_tool, log_before_model, report_prompt_switch


class ReactAgent:
    def __init__(self):
        self.agent = create_agent(
            model=chat_model,
            system_prompt=load_system_prompts(),
            tools=[rag_summarize, get_weather, get_user_location, get_user_id,
                   get_current_month, fetch_external_data, fill_context_for_report],
            middleware=[monitor_tool, log_before_model, report_prompt_switch],
        )

    def execute_stream(self, query: str, context: dict | None = None,
                       history_messages: list[dict] | None = None):
        # 组装消息：同一会话窗口的历史问答 + 本次提问，让模型带上下文回答
        messages: list[dict] = []
        if history_messages:
            messages.extend(history_messages)
        messages.append({"role": "user", "content": query})

        input_dict = {"messages": messages}

        # 第三个参数context就是上下文runtime中的信息，就是我们做提示词切换的标记
        for chunk in self.agent.stream(input_dict, stream_mode="values", context=context or {}):
            latest_message = chunk["messages"][-1]
            # 只输出 AI 回复内容，跳过用户消息的回显
            if isinstance(latest_message, AIMessage) and latest_message.content:
                yield latest_message.content.strip() + "\n"


if __name__ == '__main__':
    agent = ReactAgent()

    for chunk in agent.execute_stream("根据今天的天气和我的位置，今天想吃减脂餐，怎么做（不要问我）"):
        print(chunk, end="", flush=True)
