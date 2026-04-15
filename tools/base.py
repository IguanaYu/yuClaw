"""工具基类，所有工具必须继承此类"""


class BaseTool:
    """工具基类"""

    name: str = ""
    description: str = ""
    parameters: dict = {}

    def execute(self, **kwargs) -> str:
        """执行工具，返回字符串结果"""
        raise NotImplementedError

    def to_function_schema(self) -> dict:
        """转换为 OpenAI function calling 格式的工具定义"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }
