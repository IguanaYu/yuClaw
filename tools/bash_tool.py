"""Bash 工具 - 执行 shell 命令"""

import subprocess
from .base import BaseTool


class BashTool(BaseTool):
    """执行 bash/shell 命令的工具"""

    name = "bash"
    description = "在终端中执行 shell 命令并返回输出结果。可以用来执行文件操作、运行脚本、查看系统信息等。"
    parameters = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "要执行的 shell 命令",
            },
            "timeout": {
                "type": "integer",
                "description": "超时时间（秒），默认30秒",
                "default": 30,
            },
        },
        "required": ["command"],
    }

    def execute(self, command: str, timeout: int = 30) -> str:
        """执行 shell 命令

        Args:
            command: 要执行的命令
            timeout: 超时时间（秒）

        Returns:
            命令的输出结果（stdout + stderr）
        """
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            output = ""
            if result.stdout:
                output += result.stdout
            if result.stderr:
                output += f"\n[stderr]\n{result.stderr}"
            if result.returncode != 0:
                output += f"\n[退出码: {result.returncode}]"
            return output.strip() if output.strip() else "(无输出)"
        except subprocess.TimeoutExpired:
            return f"命令执行超时（{timeout}秒）"
        except Exception as e:
            return f"执行出错: {e}"
