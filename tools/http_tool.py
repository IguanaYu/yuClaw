"""HTTP 工具 - 发送 HTTP 请求"""

import httpx
from .base import BaseTool


class HttpTool(BaseTool):
    """HTTP 请求工具"""

    name = "http_request"
    description = "发送 HTTP 请求获取网络资源。支持 GET、POST、PUT、DELETE 方法。"
    parameters = {
        "type": "object",
        "properties": {
            "method": {
                "type": "string",
                "enum": ["GET", "POST", "PUT", "DELETE"],
                "description": "HTTP 请求方法",
            },
            "url": {
                "type": "string",
                "description": "请求的 URL 地址",
            },
            "headers": {
                "type": "object",
                "description": "请求头（可选）",
            },
            "body": {
                "type": "string",
                "description": "请求体内容（POST/PUT 时使用）",
            },
            "timeout": {
                "type": "integer",
                "description": "超时时间（秒），默认30",
                "default": 30,
            },
        },
        "required": ["method", "url"],
    }

    MAX_RESPONSE_SIZE = 10 * 1024  # 10KB

    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }

    def execute(self, method: str, url: str, headers: dict = None,
                body: str = None, timeout: int = 30) -> str:
        try:
            # 合并默认浏览器请求头，用户传入的优先
            merged_headers = {**self.DEFAULT_HEADERS, **(headers or {})}

            with httpx.Client(timeout=timeout, follow_redirects=True, max_redirects=5) as client:
                kwargs = {"method": method, "url": url, "headers": merged_headers}
                if body:
                    kwargs["content"] = body

                response = client.request(**kwargs)

            # 格式化输出
            result_parts = [
                f"状态: {response.status_code} {response.reason_phrase}",
                f"URL: {response.url}",
            ]

            content_type = response.headers.get("content-type", "")
            if content_type:
                result_parts.append(f"Content-Type: {content_type}")

            result_parts.append("─" * 40)

            body_text = response.text
            if len(body_text) > self.MAX_RESPONSE_SIZE:
                body_text = body_text[:self.MAX_RESPONSE_SIZE]
                body_text += f"\n\n... 已截断（响应共 {len(response.content)} 字节）"

            result_parts.append(body_text)
            return "\n".join(result_parts)

        except httpx.TimeoutException:
            return f"请求超时（{timeout}秒）: {url}"
        except httpx.ConnectError:
            return f"连接失败: {url}"
        except httpx.InvalidURL:
            return f"URL 格式无效: {url}"
        except Exception as e:
            return f"请求出错: {e}"
