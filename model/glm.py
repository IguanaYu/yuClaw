"""GLM 模型封装，提供同步和流式调用接口"""

from openai import OpenAI
from config import API_KEY, BASE_URL, MODEL_NAME, TEMPERATURE, MAX_TOKENS


class GLMModel:
    """GLM 模型调用封装"""

    def __init__(self, api_key=API_KEY, base_url=BASE_URL, model=MODEL_NAME):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    def chat(self, messages, tools=None, temperature=TEMPERATURE, max_tokens=MAX_TOKENS):
        """同步调用模型，返回统一格式的回复

        Args:
            messages: 消息列表 [{"role": "...", "content": "..."}]
            tools: 工具定义列表（OpenAI function calling 格式）

        Returns:
            dict: {"role": "assistant", "content": "...", "tool_calls": [...]}
        """
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            kwargs["tools"] = tools

        response = self.client.chat.completions.create(**kwargs)

        message = response.choices[0].message
        # GLM 模型可能将回复放在 reasoning_content 或 content 中
        content = getattr(message, "reasoning_content", None) or message.content or ""

        result = {"role": "assistant", "content": content}
        if message.tool_calls:
            result["tool_calls"] = message.tool_calls

        return result

    def chat_stream(self, messages, temperature=TEMPERATURE, max_tokens=MAX_TOKENS):
        """流式调用模型，逐步返回内容

        Args:
            messages: 消息列表

        Yields:
            str: 每次返回一小段文本
        """
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )

        for chunk in stream:
            if chunk.choices:
                delta = chunk.choices[0].delta
                if hasattr(delta, "content") and delta.content:
                    yield delta.content
