"""计划工具 - 分析任务并生成结构化执行计划"""

import os
import re
import json
from datetime import datetime

from .base import BaseTool
from agent.agent import Agent
from tools.bash_tool import BashTool
from tools.file_tool import FileTool
from tools.http_tool import HttpTool
from tools.search_tool import SearchTool


# .hyclaw 数据目录路径
HYCLAW_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".hyclaw")
SESSIONS_DIR = os.path.join(HYCLAW_DIR, "sessions")
ACTIVE_FILE = os.path.join(HYCLAW_DIR, "active")


PLAN_SYSTEM_PROMPT = """你是一个专业的任务规划专家。你的职责是分析用户提出的任务，收集必要的信息，然后输出一份结构化的执行计划。

你必须遵循以下工作流程：
1. 分析任务：理解任务目标、约束条件和预期成果
2. 信息收集：使用可用工具（bash、file、http_request、web_search）收集完成任务所需的背景信息
3. 制定计划：输出结构化的执行计划

计划必须使用以下 Markdown 格式：

# 执行计划：{{任务标题}}

## 任务概述
{{对任务目标、范围和约束的简要描述}}

## 前置条件
{{执行计划前需要满足的条件，如果无需前置条件则写"无"}}

## 执行步骤

### 步骤 1：{{步骤标题}}
- **目标**：{{本步骤要达成的目标}}
- **操作**：{{具体的操作指令}}
- **预期结果**：{{完成后的预期产出}}
- **工具**：{{建议使用的工具}}

### 步骤 2：{{步骤标题}}
（同上格式继续）

## 风险与注意事项
{{执行过程中可能遇到的问题和应对策略}}

## 预期最终成果
{{任务完成后的交付物描述}}

重要规则：
- 你必须使用上述 Markdown 格式输出计划，不要省略任何章节
- 每个步骤必须足够具体，包含可直接执行的操作指令
- 如果任务涉及代码开发，每个步骤应指明需要创建/修改的文件
- 如果需要调研，先使用搜索工具获取信息，再制定计划
- 计划的步骤数量应与任务复杂度匹配，通常 3-10 个步骤

你可以使用以下工具：
{tool_descriptions}

## 环境信息
- 你的工作目录：{workspace}
- 所有文件操作（读写、创建文件、执行命令）都在该目录下进行
- 如果需要访问工作目录之外的文件，请使用绝对路径
- 不要读取 plan/ 目录，那是项目开发计划，与你的任务无关"""


class PlanTool(BaseTool):
    """任务规划工具，创建子 Agent 分析任务并生成结构化执行计划"""

    name = "plan"
    description = "任务规划工具。当面对复杂、多步骤的任务时，使用此工具生成结构化执行计划。工具会创建一个子Agent来分析任务，使用搜索、文件、HTTP、Bash等工具收集信息，然后输出一个详细的分步执行计划。"
    parameters = {
        "type": "object",
        "properties": {
            "task": {
                "type": "string",
                "description": "需要规划的任务描述，应尽量详细、具体",
            },
            "context": {
                "type": "string",
                "description": "可选的额外上下文信息，比如之前的对话历史或已有计划",
            },
        },
        "required": ["task"],
    }

    def execute(self, task: str, context: str = None) -> str:
        """分析任务，生成执行计划并保存到本地"""
        try:
            # 1. 先创建 session（拿到路径）
            session_name = self._create_session(task)
            session_path = os.path.join(SESSIONS_DIR, session_name)
            session_workspace = os.path.join(session_path, "workspace")
            os.makedirs(session_workspace, exist_ok=True)

            # 2. 子工具使用 session workspace（不含 PlanTool，防止递归）
            sub_tools = [
                BashTool(workspace=session_workspace),
                FileTool(workspace=session_workspace),
                HttpTool(),
                SearchTool(),
            ]

            # 3. 构建带环境信息的系统提示词
            tool_descriptions = self._build_sub_tool_descriptions(sub_tools)
            prompt = PLAN_SYSTEM_PROMPT.format(
                tool_descriptions=tool_descriptions,
                workspace=session_workspace,
            )

            # 构建用户消息
            user_message = f"请为以下任务制定详细执行计划：\n\n{task}"
            if context:
                user_message += f"\n\n补充上下文：\n{context}"

            # 4. 创建并运行子 Agent
            sub_agent = Agent(system_prompt=prompt, tools=sub_tools)

            print("\n[规划子Agent] 开始分析任务...")

            plan_result = sub_agent.run(user_message)

            # 5. 检查截断标记
            if "截断" in plan_result or "最大迭代" in plan_result:
                plan_result += "\n\n> 注意：计划生成过程被中断，以下内容可能不完整。"

            # 6. 保存计划
            self._save_plan(session_name, plan_result, task)

            return (
                f"已生成执行计划并保存到 .hyclaw/sessions/{session_name}/plan.md\n\n"
                f"{'=' * 50}\n{plan_result}\n{'=' * 50}\n\n"
                f"请根据计划中的步骤开始执行。"
            )

        except Exception as e:
            return f"规划工具执行失败: {e}"

    def _build_sub_tool_descriptions(self, tools: list) -> str:
        """构建子 Agent 的工具描述文本"""
        descriptions = []
        for tool in tools:
            param_info = json.dumps(tool.parameters, ensure_ascii=False, indent=2)
            descriptions.append(f"- {tool.name}: {tool.description}\n  参数: {param_info}")
        return "\n\n".join(descriptions)

    def _create_session(self, task: str) -> str:
        """创建新 session 目录并设为活跃，返回 session 名称"""
        # 提取安全关键词：去非法字符、去空格、取前 20 字符
        keyword = re.sub(r'[\\/:*?"<>|\s]', '', task[:20])
        today = datetime.now().strftime("%Y-%m-%d")
        session_name = f"{today}-{keyword}"

        session_path = os.path.join(SESSIONS_DIR, session_name)
        os.makedirs(session_path, exist_ok=True)

        # 写入 active 指针
        os.makedirs(HYCLAW_DIR, exist_ok=True)
        with open(ACTIVE_FILE, "w", encoding="utf-8") as f:
            f.write(session_name)

        return session_name

    def _save_plan(self, session_name: str, plan_content: str, task: str) -> None:
        """保存计划到 .hyclaw/sessions/<session>/plan.md"""
        plan_path = os.path.join(SESSIONS_DIR, session_name, "plan.md")

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        header = f"<!-- 生成时间: {timestamp} -->\n<!-- 任务: {task} -->\n\n"

        with open(plan_path, "w", encoding="utf-8") as f:
            f.write(header + plan_content)
