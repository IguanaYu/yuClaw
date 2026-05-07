"""工具基类，所有工具必须继承此类"""

import os


class BaseTool:
    """工具基类"""

    name: str = ""
    description: str = ""
    parameters: dict = {}

    def __init__(self, workspace: str = None):
        """初始化工具

        Args:
            workspace: 工作目录路径，默认为当前工作目录。
                       工具的文件操作和命令执行都基于此目录。
        """
        self.workspace = workspace or os.getcwd()

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
