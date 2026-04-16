"""文件工具 - 文件读写和目录操作"""

import os
from .base import BaseTool


class FileTool(BaseTool):
    """文件和目录操作工具"""

    name = "file"
    description = "文件和目录操作工具。支持读取文件、写入文件、追加内容和列出目录。"
    parameters = {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["read", "write", "append", "list"],
                "description": "操作类型：read=读取文件, write=写入文件, append=追加内容, list=列出目录",
            },
            "path": {
                "type": "string",
                "description": "文件或目录的路径",
            },
            "content": {
                "type": "string",
                "description": "要写入或追加的内容（仅 write/append 操作使用）",
            },
        },
        "required": ["operation", "path"],
    }

    MAX_READ_SIZE = 100 * 1024  # 100KB

    def execute(self, operation: str, path: str, content: str = None) -> str:
        try:
            # 路径安全检查
            if ".." in os.path.normpath(path).split(os.sep):
                return "错误：路径不允许包含 '..'"

            if operation == "read":
                return self._read(path)
            elif operation == "write":
                return self._write(path, content)
            elif operation == "append":
                return self._append(path, content)
            elif operation == "list":
                return self._list(path)
            else:
                return f"错误：未知操作 '{operation}'"
        except Exception as e:
            return f"执行出错: {e}"

    def _read(self, path: str) -> str:
        if not os.path.exists(path):
            return f"错误：文件不存在 '{path}'"
        if os.path.isdir(path):
            return f"错误：'{path}' 是目录，不是文件"

        file_size = os.path.getsize(path)
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read(self.MAX_READ_SIZE)

        result = f"文件: {path} ({file_size} 字节)\n{'─' * 40}\n{text}"
        if file_size > self.MAX_READ_SIZE:
            result += f"\n\n... 已截断（文件共 {file_size} 字节，仅读取前 {self.MAX_READ_SIZE} 字节）"
        return result

    def _write(self, path: str, content: str) -> str:
        if content is None:
            return "错误：write 操作需要提供 content 参数"

        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"写入成功: {path} ({len(content.encode('utf-8'))} 字节)"

    def _append(self, path: str, content: str) -> str:
        if content is None:
            return "错误：append 操作需要提供 content 参数"

        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(content)
        return f"追加成功: {path} ({len(content.encode('utf-8'))} 字节)"

    def _list(self, path: str) -> str:
        if not os.path.exists(path):
            return f"错误：目录不存在 '{path}'"
        if not os.path.isdir(path):
            return f"错误：'{path}' 是文件，不是目录"

        entries = []
        for name in sorted(os.listdir(path)):
            full = os.path.join(path, name)
            if os.path.isdir(full):
                entries.append(f"  {name}/")
            else:
                size = os.path.getsize(full)
                entries.append(f"  {name}  ({self._format_size(size)})")

        if not entries:
            return f"目录: {path}\n（空目录）"

        return f"目录: {path}\n{'─' * 40}\n" + "\n".join(entries)

    @staticmethod
    def _format_size(size: int) -> str:
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        else:
            return f"{size / (1024 * 1024):.1f} MB"
