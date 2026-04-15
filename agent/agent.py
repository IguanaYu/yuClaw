"""Agent 层 - 提示词模板 + 工具调用循环"""

import json
from model.glm import GLMModel
from tools.base import BaseTool
from config import MAX_ITERATIONS


# 默认系统提示词模板，支持 {tool_descriptions} 占位符
DEFAULT_SYSTEM_PROMPT = """你是一个智能助手，可以使用工具来帮助用户完成任务。

你可以使用以下工具：
{tool_descriptions}

当你需要使用工具时，请从可用的工具中选择合适的工具来完成任务。
如果不需要使用工具，请直接回答用户的问题。"""


class Agent:
    """Agent：封装提示词、消息历史和工具调用循环"""

    def __init__(self, system_prompt=None, tools=None, model=None, **prompt_params):
        """
        Args:
            system_prompt: 系统提示词模板，支持 {param} 占位符。
                           为 None 时使用默认模板。
            tools: 工具实例列表 [BaseTool, ...]
            model: GLMModel 实例，为 None 时自动创建
            **prompt_params: 注入到系统提示词模板中的参数
        """
        self.tools: dict[str, BaseTool] = {}
        if tools:
            for tool in tools:
                self.tools[tool.name] = tool

        # 构建工具描述文本
        tool_descriptions = self._build_tool_descriptions()

        # 组装系统提示词
        if system_prompt is None:
            system_prompt = DEFAULT_SYSTEM_PROMPT
        self.system_prompt = system_prompt.format(
            tool_descriptions=tool_descriptions, **prompt_params
        )

        self.model = model or GLMModel()
        self.messages = [{"role": "system", "content": self.system_prompt}]

    def _build_tool_descriptions(self) -> str:
        """构建工具描述文本，用于注入系统提示词"""
        if not self.tools:
            return "（无可用工具）"

        descriptions = []
        for name, tool in self.tools.items():
            param_info = json.dumps(tool.parameters, ensure_ascii=False, indent=2)
            descriptions.append(f"- {name}: {tool.description}\n  参数: {param_info}")
        return "\n\n".join(descriptions)

    def _get_tool_schemas(self) -> list[dict]:
        """获取 OpenAI function calling 格式的工具定义列表"""
        return [tool.to_function_schema() for tool in self.tools.values()]

    def run(self, user_message: str) -> str:
        """执行一次完整的 Agent 交互循环

        Args:
            user_message: 用户输入

        Returns:
            Agent 的最终文本回复
        """
        self.messages.append({"role": "user", "content": user_message})

        tool_schemas = self._get_tool_schemas() if self.tools else None

        for _ in range(MAX_ITERATIONS):
            response = self.model.chat(self.messages, tools=tool_schemas)

            # 记录助手回复到消息历史
            assistant_msg = {"role": "assistant", "content": response["content"]}

            if "tool_calls" in response:
                # 有工具调用 → 执行工具并喂回模型
                assistant_msg["tool_calls"] = response["tool_calls"]
                self.messages.append(assistant_msg)

                for tool_call in response["tool_calls"]:
                    func_name = tool_call.function.name
                    func_args = json.loads(tool_call.function.arguments)

                    # 执行工具
                    tool = self.tools.get(func_name)
                    if tool:
                        result = tool.execute(**func_args)
                    else:
                        result = f"错误：未知工具 '{func_name}'"

                    print(f"\n[工具调用] {func_name}({func_args})")
                    print(f"[工具结果] {result[:200]}{'...' if len(result) > 200 else ''}")

                    # 将工具结果加入消息历史
                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result,
                    })
            else:
                # 无工具调用 → 最终回复
                self.messages.append(assistant_msg)
                return response["content"]

        return "（已达到最大迭代次数，Agent 停止运行）"

    def reset(self):
        """重置消息历史"""
        self.messages = [{"role": "system", "content": self.system_prompt}]
