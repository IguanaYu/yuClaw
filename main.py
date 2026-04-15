"""hyclaw - 主循环入口"""

import sys
import os

# 将项目根目录加入 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent.agent import Agent
from tools.bash_tool import BashTool


def main():
    print("=" * 50)
    print("  hyclaw - 基础 Agent 管理系统")
    print("  输入 'quit' 或 'exit' 退出")
    print("=" * 50)

    # 初始化工具
    tools = [BashTool()]

    # 初始化 Agent
    agent = Agent(tools=tools)

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
            response = agent.run(user_input)
            print(f"\n助手: {response}")
        except Exception as e:
            print(f"\n[错误] {e}")


if __name__ == "__main__":
    main()
