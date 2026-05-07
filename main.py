"""hyclaw - 主循环入口"""

import sys
import os

# 将项目根目录加入 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent.agent import Agent
from tools.bash_tool import BashTool
from tools.file_tool import FileTool
from tools.http_tool import HttpTool
from tools.search_tool import SearchTool
from tools.plan_tool import PlanTool


# 增强系统提示词（含规划能力引导）
ENHANCED_SYSTEM_PROMPT = """你是一个智能助手，可以使用工具来帮助用户完成任务。

你可以使用以下工具：
{tool_descriptions}

## 规划能力

你拥有一个「plan」工具（任务规划工具）。当面对复杂任务时，你应该使用它来生成结构化执行计划。

### 何时使用规划工具
你应该自行判断任务的复杂度：
- **简单任务**（问答、单步操作、简单查询）→ 直接回答或使用其他工具完成，不需要规划
- **复杂任务**（多步骤项目、需要调研的任务、涉及多个文件的开发任务、需要多轮操作的任务）→ 先使用 plan 工具生成计划，然后按计划执行

### 判断标准
以下情况建议使用规划工具：
1. 任务需要 3 个以上独立步骤才能完成
2. 任务涉及创建或修改多个文件
3. 任务需要先调研再执行
4. 任务需要按照特定顺序执行多个操作
5. 用户明确要求"帮我规划"、"制定方案"等

以下情况不需要规划：
1. 简单的知识问答
2. 单个文件的读写
3. 单条命令执行
4. 已有计划且用户询问下一步该做什么

### 规划后的执行
如果你使用了 plan 工具生成了计划，你会在后续对话中看到该计划的内容。你应该按照计划中的步骤依次执行，每完成一个步骤向用户汇报进度。"""


# .hyclaw 数据目录路径
HYCLAW_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".hyclaw")
SESSIONS_DIR = os.path.join(HYCLAW_DIR, "sessions")
ACTIVE_FILE = os.path.join(HYCLAW_DIR, "active")


def load_active_plan() -> str | None:
    """读取当前活跃 session 的计划"""
    if not os.path.exists(ACTIVE_FILE):
        return None
    with open(ACTIVE_FILE, "r", encoding="utf-8") as f:
        session_name = f.read().strip()
    plan_path = os.path.join(SESSIONS_DIR, session_name, "plan.md")
    if not os.path.exists(plan_path):
        return None
    with open(plan_path, "r", encoding="utf-8") as f:
        return f.read()


def get_active_session_name() -> str | None:
    """获取当前活跃 session 名称"""
    if not os.path.exists(ACTIVE_FILE):
        return None
    with open(ACTIVE_FILE, "r", encoding="utf-8") as f:
        return f.read().strip()


def list_sessions() -> list[str]:
    """列出所有历史 session"""
    if not os.path.exists(SESSIONS_DIR):
        return []
    sessions = sorted(os.listdir(SESSIONS_DIR), reverse=True)
    return [s for s in sessions if os.path.isdir(os.path.join(SESSIONS_DIR, s))]


def inject_plan_context(agent: Agent, plan_content: str) -> None:
    """将活跃计划注入 Agent 的系统消息中"""
    plan_section = f"""

当前活跃计划：
{"=" * 50}
{plan_content}
{"=" * 50}

重要：你目前有一个正在执行的计划。在回答用户问题时，请参考此计划的内容和步骤。如果用户的问题与计划相关，按照计划中的步骤推进执行。如果用户的问题与计划无关，正常回答即可。"""
    # 基于原始 system_prompt 重建，避免重复叠加
    agent.messages[0]["content"] = agent.system_prompt + plan_section


def clear_plan_context(agent: Agent) -> None:
    """清除 Agent 系统消息中的计划上下文"""
    agent.messages[0]["content"] = agent.system_prompt


def main():
    print("=" * 50)
    print("  hyclaw - 基础 Agent 管理系统")
    print("  输入 'quit' 或 'exit' 退出")
    print("  /plan <任务>  创建计划  /plan  查看计划  /clearplan  清除计划")
    print("  /sessions  历史记录  /switch <session>  切换计划")
    print("=" * 50)

    # 初始化工具（包含 PlanTool）
    tools = [BashTool(), FileTool(), HttpTool(), SearchTool(), PlanTool()]

    # 初始化 Agent，使用增强系统提示词
    agent = Agent(system_prompt=ENHANCED_SYSTEM_PROMPT, tools=tools)

    print(f"\n已加载工具: {[t.name for t in tools]}")
    print("-" * 50)

    # 主循环
    while True:
        try:
            user_input = input("\n你: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit"):
            print("再见！")
            break

        try:
            # 强制规划模式：/plan <task>
            if user_input.startswith("/plan ") and len(user_input) > 6:
                task = user_input[6:].strip()
                print("\n[规划模式] 正在生成执行计划...")
                plan_tool = agent.tools["plan"]
                plan_result = plan_tool.execute(task=task)
                print(f"\n助手: {plan_result}")
                # 注入计划上下文
                plan_content = load_active_plan()
                if plan_content:
                    inject_plan_context(agent, plan_content)

            # 查看当前计划：/plan
            elif user_input == "/plan":
                plan_content = load_active_plan()
                if plan_content:
                    active = get_active_session_name()
                    print(f"\n当前计划 ({active}):\n{'=' * 50}\n{plan_content}\n{'=' * 50}")
                else:
                    print("\n当前没有活跃计划。使用 /plan <任务描述> 创建新计划。")

            # 清除活跃计划：/clearplan
            elif user_input == "/clearplan":
                if os.path.exists(ACTIVE_FILE):
                    os.remove(ACTIVE_FILE)
                    clear_plan_context(agent)
                    print("\n已清除活跃计划。（历史 session 数据保留在 .hyclaw/sessions/ 中）")
                else:
                    print("\n当前没有活跃计划。")

            # 列出历史 session：/sessions
            elif user_input == "/sessions":
                sessions = list_sessions()
                if not sessions:
                    print("\n暂无历史 session。")
                else:
                    active_name = get_active_session_name()
                    print(f"\n历史 session（共 {len(sessions)} 个）：")
                    for s in sessions:
                        marker = " ← 当前活跃" if s == active_name else ""
                        print(f"  - {s}{marker}")

            # 切换到历史 session：/switch <session>
            elif user_input.startswith("/switch ") and len(user_input) > 8:
                target = user_input[8:].strip()
                target_path = os.path.join(SESSIONS_DIR, target)
                if os.path.isdir(target_path) and os.path.exists(os.path.join(target_path, "plan.md")):
                    with open(ACTIVE_FILE, "w", encoding="utf-8") as f:
                        f.write(target)
                    plan_content = load_active_plan()
                    inject_plan_context(agent, plan_content)
                    print(f"\n已切换到 session: {target}")
                else:
                    print(f"\n未找到 session: {target}")

            # 正常模式
            else:
                # 检查并注入计划上下文
                plan_content = load_active_plan()
                if plan_content:
                    inject_plan_context(agent, plan_content)
                else:
                    clear_plan_context(agent)

                response = agent.run(user_input)
                print(f"\n助手: {response}")

        except Exception as e:
            print(f"\n[错误] {e}")


if __name__ == "__main__":
    main()
