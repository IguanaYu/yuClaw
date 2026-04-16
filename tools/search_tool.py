"""搜索工具 - 使用 DuckDuckGo 搜索互联网"""

from .base import BaseTool


class SearchTool(BaseTool):
    """互联网搜索工具"""

    name = "web_search"
    description = "搜索互联网获取信息。返回相关网页的标题、摘要和链接。"
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "搜索关键词",
            },
            "max_results": {
                "type": "integer",
                "description": "返回结果数量，默认5",
                "default": 5,
            },
        },
        "required": ["query"],
    }

    def execute(self, query: str, max_results: int = 5) -> str:
        try:
            from ddgs import DDGS

            results = list(DDGS().text(query, max_results=max_results))

            if not results:
                return f"未找到相关结果: {query}"

            parts = [f"搜索: {query}", f"找到 {len(results)} 条结果", "═" * 40]
            for i, item in enumerate(results, 1):
                title = item.get("title", "无标题")
                body = item.get("body", "无摘要")
                href = item.get("href", "无链接")
                parts.append(f"\n[{i}] {title}")
                parts.append(f"{body}")
                parts.append(f"链接: {href}")
                if i < len(results):
                    parts.append("─" * 40)

            return "\n".join(parts)

        except ImportError:
            return "错误：未安装 ddgs 库，请运行 pip install ddgs"
        except Exception as e:
            error_msg = str(e).lower()
            if "rate" in error_msg or "limit" in error_msg or "429" in error_msg:
                return "搜索请求过于频繁，请稍后再试"
            return f"搜索出错: {e}"
