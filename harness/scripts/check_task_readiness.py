"""任务就绪检查脚本 —— 建议与指引

在任意 workflow 的 stage_0 执行，扫描项目结构并给出状态和建议。
始终 exit(0)，缺失项不会阻塞执行，仅作为改进提醒。

Usage:
    python harness/scripts/check_task_readiness.py [--task <task_name>]
"""

import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CHECKS = []


def check(description: str):
    """装饰器：注册一个检查项"""
    def decorator(func):
        CHECKS.append((description, func))
        return func
    return decorator


# ═══════════════════════════════════════════════════════════
# 检查项定义 — 每个函数返回 (ok: bool, message: str, suggestion: str|None)
# ═══════════════════════════════════════════════════════════

@check("project_spec.md 是否存在")
def check_project_spec():
    path = os.path.join(PROJECT_ROOT, "harness", "spec", "project_spec.md")
    if not os.path.exists(path):
        return False, "未找到 project_spec.md", (
            "建议创建 harness/spec/project_spec.md，"
            "在其中定义项目背景、目标、成功标准和框架设计原则"
        )
    content = open(path, "r", encoding="utf-8").read()
    if len(content.strip()) < 100:
        return False, "project_spec.md 内容较少", (
            "建议补充项目背景、目标、成功标准和框架设计原则"
        )
    return True, "project_spec.md 已就绪", None


@check("六层目录结构是否完整")
def check_six_layers():
    required_dirs = [
        "harness/spec",
        "harness/skills",
        "harness/agents",
        "harness/workflows",
        "harness/memory",
        "harness/evaluation",
        "harness/rules",
        "harness/scripts",
    ]
    missing = [d for d in required_dirs if not os.path.isdir(os.path.join(PROJECT_ROOT, d))]
    if missing:
        return False, f"缺失 {len(missing)} 个目录: {missing}", (
            "建议创建缺失的目录以保持 Harness 六层骨架完整。"
            "当前任务较简单时可暂时留空。"
        )
    return True, "六层目录结构完整", None


@check("是否定义了 Agent")
def check_agents():
    agents_dir = os.path.join(PROJECT_ROOT, "harness", "agents")
    agent_files = [f for f in os.listdir(agents_dir) if f.endswith(".md") and f != ".gitkeep"]
    if not agent_files:
        return False, "未定义任何 Agent", (
            "建议在 harness/agents/ 中定义至少一个 Agent 角色，"
            "描述其职责范围、不可越界和输出规范"
        )
    return True, f"已定义 {len(agent_files)} 个 Agent: {agent_files}", None


@check("是否定义了 Workflow")
def check_workflows():
    wf_dir = os.path.join(PROJECT_ROOT, "harness", "workflows")
    wf_files = [f for f in os.listdir(wf_dir) if f.endswith(".yaml") and f != ".gitkeep"]
    if not wf_files:
        return False, "未定义任何 Workflow", (
            "建议在 harness/workflows/ 中定义至少一个 Workflow YAML，"
            "描述分析流程的阶段、执行 Agent 和输入输出"
        )
    return True, f"已定义 {len(wf_files)} 个 Workflow: {wf_files}", None


@check("是否定义了 Task Spec")
def check_tasks():
    tasks_dir = os.path.join(PROJECT_ROOT, "harness", "spec", "tasks")
    if not os.path.isdir(tasks_dir):
        return False, "harness/spec/tasks/ 目录不存在", (
            "建议创建 harness/spec/tasks/ 目录，为每个分析阶段编写任务规范"
        )
    task_files = [f for f in os.listdir(tasks_dir) if f.endswith(".md") and f != ".gitkeep"]
    if not task_files:
        return False, "未定义任何 Task Spec", (
            "建议在 harness/spec/tasks/ 中创建任务规范文件，"
            "定义每个阶段的输入、输出和验收标准"
        )
    return True, f"已定义 {len(task_files)} 个 Task Spec: {task_files}", None


@check("data_spec.md 是否存在")
def check_data_spec():
    path = os.path.join(PROJECT_ROOT, "harness", "spec", "data_spec.md")
    if not os.path.exists(path):
        return False, "未找到 data_spec.md", (
            "建议创建 harness/spec/data_spec.md，"
            "描述当前数据源的字段定义、质量基线和口径注册"
        )
    content = open(path, "r", encoding="utf-8").read()
    if len(content.strip()) < 50:
        return False, "data_spec.md 内容较少", (
            "建议补充数据集的字段定义、质量基线和数据使用约束"
        )
    return True, "data_spec.md 已就绪", None


@check("quality_gates.yaml 是否存在")
def check_quality_gates():
    path = os.path.join(PROJECT_ROOT, "harness", "evaluation", "quality_gates.yaml")
    if not os.path.exists(path):
        return False, "未找到 quality_gates.yaml", (
            "建议创建 harness/evaluation/quality_gates.yaml，"
            "为各分析阶段定义质量门和通过标准"
        )
    return True, "quality_gates.yaml 已就绪", None


@check("Agents 与 Workflows 是否匹配当前任务")
def check_agent_workflow_alignment():
    """检查 workflow 中引用的 agent 是否都已定义"""
    agents_dir = os.path.join(PROJECT_ROOT, "harness", "agents")
    wf_dir = os.path.join(PROJECT_ROOT, "harness", "workflows")

    agent_files = [f for f in os.listdir(agents_dir) if f.endswith(".md") and f != ".gitkeep"]
    agent_names = {f.replace(".md", "") for f in agent_files}
    wf_files = [f for f in os.listdir(wf_dir) if f.endswith(".yaml") and f != ".gitkeep"]

    unmatched = []
    for wf_file in wf_files:
        content = open(os.path.join(wf_dir, wf_file), "r", encoding="utf-8").read()
        for agent_name in agent_names:
            pass  # just checking referenced agents
        # Simple check: extract "agent:" lines
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("agent:"):
                ref_agent = line.replace("agent:", "").strip()
                if ref_agent and ref_agent not in agent_names:
                    unmatched.append(f"{wf_file} 引用了未定义的 agent: {ref_agent}")

    if unmatched:
        return False, f"存在未匹配的 Agent 引用: {unmatched}", (
            "建议检查 workflow 中引用的 agent 名称是否与 agents/ 中的定义文件一致，"
            "或创建对应的 agent 定义文件"
        )
    return True, "Agents 与 Workflows 引用关系一致", None


# ═══════════════════════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════════════════════

def run_all_checks():
    passed = 0
    advisory = 0

    print()
    print("╔" + "═" * 58 + "╗")
    print("║  Task Readiness Check — 任务就绪扫描                    ║")
    print("║  性质：建议与指引，缺失项不阻塞分析执行                  ║")
    print("╚" + "═" * 58 + "╝")
    print()

    for description, check_func in CHECKS:
        try:
            ok, msg, suggestion = check_func()
            if ok:
                print(f"  ✅  {description}")
                print(f"      {msg}")
                passed += 1
            else:
                print(f"  ⚠️   {description}")
                print(f"      {msg}")
                if suggestion:
                    print(f"      💡 建议: {suggestion}")
                advisory += 1
        except Exception as e:
            print(f"  ⚠️   {description}")
            print(f"      扫描异常: {e}")
            print(f"      💡 建议: 手动检查此项")
            advisory += 1

    print()
    print(f"  ──────────────────────────────")
    print(f"  已就绪: {passed} 项    可改进: {advisory} 项    总计: {len(CHECKS)} 项")
    print()

    if advisory > 0:
        print("  💡 以上可改进项不影响分析继续执行，可根据建议按需补充。")
    else:
        print("  ✅ 所有建议项均已满足，项目结构完善。")

    print()
    return True  # 始终返回 True，不阻塞


if __name__ == "__main__":
    run_all_checks()
    sys.exit(0)  # 始终 exit 0，不阻塞后续阶段
