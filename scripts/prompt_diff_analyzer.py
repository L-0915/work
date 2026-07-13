#!/usr/bin/env python3
"""
推理 Prompt vs 评估 Prompt 差异分析工具

深度分析 Deep Research 系统中推理 Prompt 和评估 Prompt 的设计差异：
- 结构差异（模板变量、输出格式、约束条件）
- 语义差异（目标导向、复杂度、上下文处理）
- 演进趋势（推理越来越简单 vs 评估越来越复杂）
- 耦合关系（评估指标如何影响推理设计）

用法:
    python prompt_diff_analyzer.py                        # 完整分析报告
    python prompt_diff_analyzer.py --compact              # 紧凑输出
    python prompt_diff_analyzer.py --export report.json   # 导出 JSON
    python prompt_diff_analyzer.py --evolution            # 演进趋势分析
    python prompt_diff_analyzer.py --coupling             # 耦合关系分析
"""

import json
import argparse
import sys
from dataclasses import dataclass, field
from typing import Any

# Fix Windows GBK encoding issues
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


# ============================================================
# 核心差异维度数据
# ============================================================

@dataclass
class PromptCategory:
    """Prompt 分类特征"""
    name: str
    goal: str
    user: str
    complexity_trend: str
    structure_level: str
    failure_modes: list
    optimization: str
    context_scope: str


INFERENCE_CATEGORY = PromptCategory(
    name="推理 Prompt (Inference)",
    goal="驱动 Agent 行动：搜索→浏览→提取→综合→回答",
    user="Agent 模型（执行研究任务的主体）",
    complexity_trend="越来越简单 ↓（Bitter Lesson 效应）",
    structure_level="中低——给 Agent 探索空间",
    failure_modes=[
        "上下文腐烂 (Context Rot)：长时间积累的无用内容污染推理",
        "认知窒息 (Cognitive Suffocation)：信息过载导致无法有效决策",
        "噪声污染 (Noise Pollution)：工具返回的大量低信噪比内容",
        "幻觉工具调用：生成不存在的工具或参数",
        "过早终止：在找到正确答案前停止搜索",
    ],
    optimization="遗传式 Prompt 进化 (GEPA) + RL 微调 (GRPO)",
    context_scope="管理 100K+ token 流式工具调用结果，需要持续裁剪和压缩",
)

EVALUATION_CATEGORY = PromptCategory(
    name="评估 Prompt (Evaluation)",
    goal="驱动 Judge 判断：接收输入→应用标准→输出评分",
    user="LLM-as-Judge 模型（评分主体）",
    complexity_trend="越来越复杂 ↑（多轴 Rubric → Claim-Graph 验证 → 过程评估）",
    structure_level="高——确保评分一致性和可复现性",
    failure_modes=[
        "隐性需求遗漏 (Implicit Requirement Gap)：用户未明说但理应满足的需求被忽略",
        "Judge 偏见 (Judge Bias)：评分模型自身偏好影响客观性",
        "Reward Hacking：Agent 学习表面特征而非真正提高质量",
        "表面词汇重叠：评分基于词汇相似度而非语义理解",
        "综合质量盲区：无法评估跨段落的逻辑连贯性和论证强度",
    ],
    optimization="人类专家 Rubric 校准 + ELO 锦标赛对比",
    context_scope="全局评估完整输出（最终答案或长篇报告），一次输入全部内容",
)

# ============================================================
# 结构对比表
# ============================================================

STRUCTURAL_COMPARISON = [
    {
        "aspect": "身份声明",
        "inference": "定义 Agent 角色和能力边界（如 'Web Information Seeking Master'）",
        "evaluation": "定义 Judge 角色和判断权限（如 'evaluation assistant'）",
        "diff_key": "Agent 需要知道能做什么，Judge 需要知道如何判断",
    },
    {
        "aspect": "工具/能力定义",
        "inference": "嵌入 JSON Schema 工具定义，详细描述每个工具的输入输出",
        "evaluation": "无工具定义——Judge 不需要外部工具",
        "diff_key": "推理需要工具，评估是纯文本判断",
    },
    {
        "aspect": "输出格式约束",
        "inference": "XML/JSON 标签约束 Action（<think>/<tool_call>/<answer>）",
        "evaluation": "限制为固定词汇（Correct/Incorrect）或 JSON Schema",
        "diff_key": "推理输出结构复杂（含工具调用），评估输出简单但严格",
    },
    {
        "aspect": "行为原则",
        "inference": "持续性、验证性、细节关注——驱动多轮探索",
        "evaluation": "语义等价、完整性、准确性——驱动多维度评分",
        "diff_key": "推理原则指导过程，评估原则指导判断",
    },
    {
        "aspect": "上下文管理",
        "inference": "定义摘要触发条件、裁剪策略、降级方案（Token 超限时措施）",
        "evaluation": "无需上下文管理——单次评估不超过窗口限制",
        "diff_key": "推理需要管理长对话，评估是一次性输入",
    },
    {
        "aspect": "停止条件",
        "inference": "Stop sequences 防止幻觉（如阻止 LLM 伪造工具响应）",
        "evaluation": "输出约束（只输出一词/JSON）防止 Judge 超范围回答",
        "diff_key": "推理防幻觉生成，评估防评分漂移",
    },
    {
        "aspect": "Few-shot 使用",
        "inference": "一般不加 Few-shot——Agent 需要泛化能力",
        "evaluation": "大量使用 Few-shot 校准评分标准（如 Obama 孩子例子）",
        "diff_key": "推理要泛化，评估要标准化",
    },
    {
        "aspect": "变量注入",
        "inference": "注入 tools schema / question / goal / context",
        "evaluation": "注入 question + correct_answer + predicted_answer 三要素",
        "diff_key": "推理需要动态信息，评估需要标准答案作为对照",
    },
]

# ============================================================
# 演进趋势数据
# ============================================================

EVOLUTION_TIMELINE = [
    {
        "period": "2024 H1",
        "inference": "高度结构化 Prompt——预定义章节、硬编码假设、分段写作",
        "evaluation": "简单等价判断——只输出 Correct/Incorrect",
        "key_event": "GAIA 发布 (2024.04)——确立 Exact Match 标准",
    },
    {
        "period": "2024 H2",
        "inference": "过渡到工具调用驱动——移除段落级模板，引入 ReAct",
        "evaluation": "LLM-as-Judge 开始兴起——处理语义等价",
        "key_event": "LangChain Open Deep Research 简化 Prompt 结构",
    },
    {
        "period": "2025 H1",
        "inference": "最小结构——Agent 自主确定研究路径，纯 ReAct",
        "evaluation": "三级评分 + Few-shot 校准——CORRECT/INCORRECT/NOT_ATTEMPTED",
        "key_event": "BrowseComp 发布——LLM Judge 成为主流",
    },
    {
        "period": "2025 H2",
        "inference": "RL 训练的端到端 Agent 出现——显式 Prompt 工程可能被淘汰",
        "evaluation": "多轴 Rubric（6+ 维度）+ Claim-Graph 验证 + 过程评估",
        "key_event": (
            "ResearchRubrics (Scale AI)、ReportBench (ByteDance)、"
            "Tongyi DeepResearch 开源"
        ),
    },
    {
        "period": "2026+ (趋势)",
        "inference": "极少手工 Prompt → 全部由 RL 学习的行为策略取代",
        "evaluation": "实时动态评估 + 自动发现新的评估维度 + 对抗式评分",
        "key_event": "Kimi K2.5 Swarm 多 Agent 达到 72.1% BrowseComp",
    },
]

# ============================================================
# 耦合关系数据
# ============================================================

COUPLING_MATRIX = [
    {
        "eval_dimension": "引用准确性 (Citation Accuracy)",
        "inference_implication": "Agent 必须在每次检索时保存来源 URL、标题和时间戳",
        "design_change": "在 <tool_response> 中增加引用元数据字段",
        "affected_components": ["visit 工具", "EXTRACTOR_PROMPT", "最终 <answer> 格式"],
    },
    {
        "eval_dimension": "隐性需求遵循 (Implicit Requirement)",
        "inference_implication": "Agent 需要在搜索前花步骤分析用户未明说的假设",
        "design_change": "在 SYSTEM_PROMPT 中增加 '分析隐性需求' 步骤",
        "affected_components": ["SYSTEM_PROMPT", "ReAct 循环第一步"],
    },
    {
        "eval_dimension": "结构连贯性 (Structural Coherence)",
        "inference_implication": "Agent 必须写作前先列大纲，保持逻辑流",
        "design_change": "增加 'outline' 工具或在 <think> 中要求结构化计划",
        "affected_components": ["SYSTEM_PROMPT", "输出格式指令"],
    },
    {
        "eval_dimension": "事实 Grounding",
        "inference_implication": "Agent 在声明前跨多源交叉引用",
        "design_change": "行为原则强调 '交叉验证' (已在 Tongyi 中体现)",
        "affected_components": ["SYSTEM_PROMPT 行为原则"],
    },
    {
        "eval_dimension": "关键点覆盖 (Key Points Coverage)",
        "inference_implication": "Agent 显式追踪哪些子主题已覆盖，哪些未覆盖",
        "design_change": "增加 'coverage_tracker' 内部状态或检查步骤",
        "affected_components": ["ReAct 循环", "SYSTEM_PROMPT"],
    },
    {
        "eval_dimension": "成本效率 (Cost Efficiency)",
        "inference_implication": "Agent 需在搜索广度和成本间平衡",
        "design_change": "增加搜索轮次上限、预算感知的决策逻辑",
        "affected_components": ["工具定义", "MAX_LLM_CALL_PER_RUN"],
    },
]

# ============================================================
# 具体 Prompt 对比示例
# ============================================================

PROMPT_SIDE_BY_SIDE = [
    {
        "title": "身份声明对比",
        "inference_prompt": (
            "You are a Web Information Seeking Master. Your task is "
            "to thoroughly seek the internet for information..."
        ),
        "evaluation_prompt": (
            "You are an evaluation assistant. Please determine if "
            "the predicted answer is equivalent to the labeled answer."
        ),
        "analysis": (
            "推理 Prompt 将 Agent 定位为主动探索者 (Master)，"
            "评估 Prompt 将 Judge 定位为被动判断者 (Assistant)。"
            "身份定位决定行为模式：前者要主动搜索，后者只需判断。"
        ),
    },
    {
        "title": "行为指令对比",
        "inference_prompt": (
            "Principles:\n"
            "1. Persistent Actions for Answers\n"
            "2. Repeated Verification\n"
            "3. Attention to Detail"
        ),
        "evaluation_prompt": (
            "Rules:\n"
            "1. Semantic equivalence matters, not exact wording\n"
            "2. Minor formatting differences should be ignored\n"
            "3. If the predicted answer contains the correct information "
            "among other text, count it as CORRECT"
        ),
        "analysis": (
            "推理指令关注过程 (怎么做)，评估指令关注标准 (怎么判)。"
            "推理的 'Persistent' 和 'Verification' 引导多轮搜索，"
            "评估的 'equivalence' 和 'ignore formatting' 防止过严判分。"
        ),
    },
    {
        "title": "输出约束对比",
        "inference_prompt": (
            "Use <think> for reasoning, <tool_call> for tool invocation, "
            "<answer> for final answer. Stop on '</tool_response>'."
        ),
        "evaluation_prompt": (
            'Respond with ONLY "Correct" or "Incorrect". '
            "Do not include any other text."
        ),
        "analysis": (
            "推理输出复杂——需要嵌套的工具调用 JSON，用 XML 标签分隔。"
            "评估输出极简——只输出一个词，消除解析歧义。"
            "这反映了两种 Prompt 的本质差异：推理要灵活，评估要精确。"
        ),
    },
]

# ============================================================
# 输出函数
# ============================================================

def print_header(title: str, level: int = 1) -> None:
    """打印格式化标题"""
    if level == 1:
        print(f"\n{'='*80}")
        print(f"  {title}")
        print(f"{'='*80}\n")
    elif level == 2:
        print(f"\n{'─'*80}")
        print(f"  {title}")
        print(f"{'─'*80}\n")
    else:
        print(f"\n  ▸ {title}")


def show_full_analysis() -> None:
    """完整分析报告"""
    print_header("推理 Prompt vs 评估 Prompt 深度差异分析", 1)

    # ---- Part 1: 核心特征对比 ----
    print_header("Part 1: 核心特征对比", 2)

    for cat in [INFERENCE_CATEGORY, EVALUATION_CATEGORY]:
        print(f"【{cat.name}】")
        print(f"  目标: {cat.goal}")
        print(f"  使用者: {cat.user}")
        print(f"  复杂度趋势: {cat.complexity_trend}")
        print(f"  结构化程度: {cat.structure_level}")
        print(f"  优化策略: {cat.optimization}")
        print(f"  上下文范围: {cat.context_scope}")
        print(f"\n  失败模式:")
        for fm in cat.failure_modes:
            print(f"    ✗ {fm}")
        print()

    # ---- Part 2: 结构对比 ----
    print_header("Part 2: 结构性差异", 2)

    print(f"| {'维度':<16} | {'推理 Prompt':<45} | {'评估 Prompt':<45} |")
    print(f"|{'─'*16} |{'─'*45} |{'─'*45} |")
    for item in STRUCTURAL_COMPARISON:
        inf_short = item["inference"][:42] + "..." if len(item["inference"]) > 42 else item["inference"]
        eva_short = item["evaluation"][:42] + "..." if len(item["evaluation"]) > 42 else item["evaluation"]
        print(f"| {item['aspect']:<16} | {inf_short:<45} | {eva_short:<45} |")

    print(f"\n核心差异总结:")
    for item in STRUCTURAL_COMPARISON:
        print(f"  [{item['aspect']}] {item['diff_key']}")

    # ---- Part 3: 具体 Prompt 对比 ----
    print_header("Part 3: 具体 Prompt 并排对比", 2)

    for example in PROMPT_SIDE_BY_SIDE:
        print(f"─── {example['title']} ───")
        print(f"\n推理 Prompt:")
        print(f"  {example['inference_prompt'][:200]}")
        print(f"\n评估 Prompt:")
        print(f"  {example['evaluation_prompt'][:200]}")
        print(f"\n分析:")
        print(f"  {example['analysis']}")
        print()

    # ---- Part 4: 演进趋势 ----
    print_header("Part 4: 演进趋势", 2)

    for entry in EVOLUTION_TIMELINE:
        print(f"【{entry['period']}】")
        print(f"  推理: {entry['inference']}")
        print(f"  评估: {entry['evaluation']}")
        print(f"  关键事件: {entry['key_event']}")
        print()

    print("核心洞察:")
    print("  推理 Prompt：高度结构化 → 工具调用驱动 → 最小结构 → RL 取代手工")
    print("  评估 Prompt：简单二元 → Few-shot 校准 → 多轴 Rubric → 过程级评估")
    print("  两条线在 2025 年交汇：推理极简 + 评估极繁，形成互补")

    # ---- Part 5: 耦合关系 ----
    print_header("Part 5: 耦合关系——评估如何塑造推理", 2)

    print("评估指标 → 推理设计变化的因果链:\n")
    for item in COUPLING_MATRIX:
        print(f"  评估维度: {item['eval_dimension']}")
        print(f"    → 推理影响: {item['inference_implication']}")
        print(f"    → 设计变更: {item['design_change']}")
        print(f"    → 影响组件: {', '.join(item['affected_components'])}")
        print()

    # ---- Part 6: 核心结论 ----
    print_header("Part 6: 核心结论", 2)

    conclusions = [
        (
            "本质差异",
            "推理 Prompt 是行动指南（如何做），评估 Prompt 是裁判标准（做得好不好）。"
            "前者指导过程，后者评判结果。",
        ),
        (
            "演进方向相反",
            "推理 Prompt 越来越简单（Bitter Lesson：通用方法 + 更多算力 > 手工 Prompt），"
            "评估 Prompt 越来越复杂（需要精细区分好答案和更好答案的微妙差异）。",
        ),
        (
            "形成耦合系统",
            "评估指标直接塑造推理设计。当评估从只看最终答案转向评估过程和引用质量时，"
            "推理 Prompt 必须相应增加来源追踪、子主题覆盖检查等机制。",
        ),
        (
            "最大未解决问题",
            "隐性需求识别——用户没明说但应该满足的要求。"
            "无论是推理 Prompt 还是评估 Prompt，目前都缺乏成熟的解决方案。"
            "ResearchRubrics 发现这是占所有失败 50% 的最大问题。",
        ),
        (
            "对实践的启示",
            "在 Deep Research 系统设计中，不要孤立设计推理 Prompt。"
            "应该同时设计对应的评估 Prompt，并确保两者形成有效的反馈循环："
            "评估发现的问题 → 转化为推理设计的改进 → 重新评估验证。",
        ),
    ]

    for i, (title, desc) in enumerate(conclusions, 1):
        print(f"  {i}. 【{title}】")
        print(f"     {desc}")
        print()


def show_evolution() -> None:
    """仅展示演进趋势"""
    print_header("推理 Prompt 与评估 Prompt 演进趋势", 1)

    print(f"| {'时间':<12} | {'推理 Prompt':<40} | {'评估 Prompt':<40} |")
    print(f"|{'─'*12} |{'─'*40} |{'─'*40} |")
    for entry in EVOLUTION_TIMELINE:
        inf = entry["inference"][:37] + "..." if len(entry["inference"]) > 37 else entry["inference"]
        eva = entry["evaluation"][:37] + "..." if len(entry["evaluation"]) > 37 else entry["evaluation"]
        print(f"| {entry['period']:<12} | {inf:<40} | {eva:<40} |")

    print(f"\n关键趋势图:")
    print(f"  推理复杂度: ████████▌ → ████▌ → ██▌ → █▌ → _")
    print(f"  评估复杂度: █▌ → ██▌ → ████▌ → ████████▌ → ████████████▌")

    print(f"\n  阶段: 2024H1 → 2024H2 → 2025H1 → 2025H2 → 2026+")
    print(f"  (推理越来越简单，评估越来越复杂)")


def show_coupling() -> None:
    """仅展示耦合关系"""
    print_header("评估指标 → 推理设计的耦合关系", 1)

    for item in COUPLING_MATRIX:
        print(f"【评估维度: {item['eval_dimension']}】")
        print(f"  推理需要: {item['inference_implication']}")
        print(f"  具体改动: {item['design_change']}")
        print(f"  影响范围: {', '.join(item['affected_components'])}")
        print()

    print("─── 耦合关系的实践意义 ───")
    print()
    print("当你改进评估（如增加新的评分维度），你必须同时修改推理 Prompt")
    print("来确保 Agent 能够生成满足新标准的信息。")
    print()
    print("例如：如果你在评估中加入 '引用准确性' 维度，")
    print("你必须在推理 Prompt 中：")
    print("  1. 要求 Agent 在 visit 时保存来源 URL")
    print("  2. 修改输出格式以包含引用标记")
    print("  3. 在行为原则中加入 '每次声明必须有来源'")
    print()
    print("反之，如果你改进推理 Prompt（如增加新的搜索策略），")
    print("你需要确认评估 Prompt 能够正确识别和奖励这种改进。")


def export_analysis(filepath: str) -> None:
    """导出完整分析为 JSON"""
    data = {
        "inference_category": {
            "name": INFERENCE_CATEGORY.name,
            "goal": INFERENCE_CATEGORY.goal,
            "user": INFERENCE_CATEGORY.user,
            "complexity_trend": INFERENCE_CATEGORY.complexity_trend,
            "structure_level": INFERENCE_CATEGORY.structure_level,
            "failure_modes": INFERENCE_CATEGORY.failure_modes,
            "optimization": INFERENCE_CATEGORY.optimization,
            "context_scope": INFERENCE_CATEGORY.context_scope,
        },
        "evaluation_category": {
            "name": EVALUATION_CATEGORY.name,
            "goal": EVALUATION_CATEGORY.goal,
            "user": EVALUATION_CATEGORY.user,
            "complexity_trend": EVALUATION_CATEGORY.complexity_trend,
            "structure_level": EVALUATION_CATEGORY.structure_level,
            "failure_modes": EVALUATION_CATEGORY.failure_modes,
            "optimization": EVALUATION_CATEGORY.optimization,
            "context_scope": EVALUATION_CATEGORY.context_scope,
        },
        "structural_comparison": STRUCTURAL_COMPARISON,
        "prompt_side_by_side": PROMPT_SIDE_BY_SIDE,
        "evolution_timeline": EVOLUTION_TIMELINE,
        "coupling_matrix": COUPLING_MATRIX,
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"已导出到: {filepath}")


# ============================================================
# 主入口
# ============================================================


def main():
    parser = argparse.ArgumentParser(
        description="推理 Prompt vs 评估 Prompt 差异分析工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s                          # 完整分析报告
  %(prog)s --compact                # 紧凑输出
  %(prog)s --export report.json     # 导出 JSON
  %(prog)s --evolution              # 仅演进趋势
  %(prog)s --coupling               # 仅耦合关系
        """,
    )
    parser.add_argument(
        "--compact", "-c",
        action="store_true",
        help="紧凑输出（仅核心对比表和结论）",
    )
    parser.add_argument(
        "--export", "-e",
        type=str,
        metavar="FILE",
        help="导出为 JSON",
    )
    parser.add_argument(
        "--evolution",
        action="store_true",
        help="仅展示演进趋势分析",
    )
    parser.add_argument(
        "--coupling",
        action="store_true",
        help="仅展示耦合关系分析",
    )

    args = parser.parse_args()

    if args.export:
        export_analysis(args.export)
    elif args.evolution:
        show_evolution()
    elif args.coupling:
        show_coupling()
    elif args.compact:
        print_header("推理 vs 评估 Prompt — 核心差异", 1)
        print(f"| {'维度':<18} | {'推理 Prompt':<35} | {'评估 Prompt':<35} |")
        print(f"|{'─'*18}|{'─'*35}|{'─'*35}|")
        for item in STRUCTURAL_COMPARISON:
            inf = item["inference"][:32] + "..." if len(item["inference"]) > 32 else item["inference"]
            eva = item["evaluation"][:32] + "..." if len(item["evaluation"]) > 32 else item["evaluation"]
            print(f"| {item['aspect']:<18} | {inf:<35} | {eva:<35} |")

        print(f"\n核心结论:")
        print(f"  1. 推理 Prompt 越来越简单（Bitter Lesson），评估 Prompt 越来越复杂")
        print(f"  2. 两者形成耦合系统：评估指标的改变直接塑造推理 Prompt 设计")
        print(f"  3. 最大未解问题：隐性需求识别（占所有失败的 50%）")
    else:
        show_full_analysis()


if __name__ == "__main__":
    main()
