#!/usr/bin/env python3
"""
Deep Research Prompt 提取与分析工具

从各评测框架和数据集中提取 Prompt 模板，支持：
- 列出所有已知 Prompt 模板（推理/评估分类）
- 输出特定框架的 Prompt 详情
- 对比不同框架的 Prompt 设计差异
- 导出为 JSON/YAML 格式

用法:
    python extract_prompts.py                           # 列出所有 prompt
    python extract_prompts.py --framework tongyi        # Tongyi DR 的 prompt
    python extract_prompts.py --category inference      # 仅推理 prompt
    python extract_prompts.py --category evaluation     # 仅评估 prompt
    python extract_prompts.py --compare tongyi reportbench  # 对比
    python extract_prompts.py --export prompts_export/  # 导出到目录
"""

import json
import argparse
import os
import sys
from dataclasses import dataclass, field
from typing import Optional

# Fix Windows GBK encoding issues
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ============================================================
# Prompt 模板数据模型
# ============================================================


@dataclass
class PromptTemplate:
    name: str
    category: str  # "inference" | "evaluation"
    framework: str  # "tongyi" | "gaia" | "browsecomp" | "reportbench" | "deepconsult"
    sub_type: str  # "system" | "user" | "judge" | "extractor" | "rubric"
    description: str
    template: str
    variables: list = field(default_factory=list)
    source_file: str = ""
    notes: str = ""


# ============================================================
# Alibaba-NLP/DeepResearch (Tongyi) Prompts
# ============================================================

TONGYI_SYSTEM_PROMPT = """You are a Web Information Seeking Master. Your task is to thoroughly
seek the internet for information and provide accurate answers to questions.
No matter how complex the query, you will not give up until you find the
corresponding information.

Principles:
1. Persistent Actions for Answers — engage in many interactions, delving deeply
   into the question until a satisfactory answer is found.
2. Repeated Verification — cross-check and validate information from multiple
   sources before formulating your final answer.
3. Attention to Detail — ensure data is current, relevant, and from credible
   origins. Do not use outdated or unverified information."""

TONGYI_USER_PROMPT = """You have access to the following tools:

{tools}

Use the following format:
<think>Your reasoning about what to do next</think>
<tool_call>
[{"name": "tool_name", "arguments": {"arg": "value"}}]
</tool_call>

When you have found the answer, output:
<answer>Your final answer here</answer>

Question: {question}"""

TONGYI_EXTRACTOR_PROMPT = """You are a web content extractor. Given a webpage and a goal,
extract the relevant information.

Goal: {goal}

Webpage Content:
{content}

Output a JSON object with the following fields:
- "rational": Explain where the target information is located in the content
- "evidence": Extract the full original context containing the information
- "summary": A concise paragraph summarizing findings with logical flow"""

TONGYI_JUDGE_GAIA = """You are an evaluation assistant. Please determine if the predicted
answer is equivalent to the labeled answer.

Question: {question}

Labeled Answer: {correct_answer}

Predicted Answer: {response}

Did the model give an answer **equivalent** to the labeled answer?
Please respond with "Correct" if they are equivalent, or "Incorrect"
if they are not equivalent. Do not include any other text."""

TONGYI_JUDGE_QA = """You are an evaluation assistant. Grade the answer as CORRECT,
INCORRECT, or NOT_ATTEMPTED.

Question: {question}
Gold Answer: {correct_answer}
Predicted Answer: {response}

Examples of grading:
Q: How many children does Barack Obama have?
Gold: Two (Malia and Sasha)
Pred: Malia and Sasha → CORRECT
Pred: Malia → INCORRECT (incomplete)
Pred: I cannot answer this question → NOT_ATTEMPTED

Now grade the following:"""

TONGYI_JUDGE_CONFIDENCE = """You are an evaluation assistant. Extract the final answer
from the model response and provide a confidence assessment.

Response: {response}

Ground Truth: {correct_answer}

Output a JSON object:
{{
  "final_answer": "extracted answer string",
  "correct": "yes" or "no",
  "reasoning": "brief explanation of your judgment",
  "confidence": 0-100
}}"""

TONGYI_JUDGE_BC_EN = """You are an expert evaluator for complex web browsing questions.
Determine if the model's answer is semantically equivalent to the gold answer.

Question: {question}

Gold Answer: {correct_answer}

Model Response: {response}

Evaluation Criteria:
1. Semantic equivalence: Does the model's answer convey the same meaning?
2. Completeness: Does it include all necessary information?
3. Precision: Is there any incorrect information?

Grade as CORRECT or INCORRECT. Provide your reasoning."""

TONGYI_JUDGE_BC_ZH = """你是一位复杂网页浏览问题的评估专家。
请判断模型的答案是否与标准答案语义等价。

问题：{question}

标准答案：{correct_answer}

模型回答：{response}

评估标准：
1. 语义等价：模型回答是否传达相同的含义？
2. 完整性：是否包含所有必要信息？
3. 准确性：是否包含任何错误信息？

请给出 CORRECT 或 INCORRECT 的评分，并提供推理过程。"""

TONGYI_JUDGE_HLE = """You are evaluating answers to Humanity's Last Exam questions.

Question: {question}
Gold Answer: {correct_answer}
Model Response: {response}

Output a JSON object:
{{
  "is_correct": true/false,
  "reasoning": "detailed explanation",
  "confidence": 0-100,
  "requires_expert_review": true/false
}}"""

# ============================================================
# ReportBench (ByteDance) Prompts
# ============================================================

REPORTBENCH_EXTRACT_PROMPT = """Extract all factual claims and their citations from the
following research report.

Report:
{report_text}

For each claim:
1. Identify the specific factual statement
2. Extract the associated citation markers [1], [2], etc.
3. Classify claim type: "quantitative", "qualitative", or "referential"

Output as a JSON array of claim objects."""

REPORTBENCH_JUDGE_PROMPT = """You are evaluating a factual claim against its cited source.

Claim: {claim}
Cited Source Excerpt: {source_text}

Determine if the claim is:
- SUPPORTED: The source directly supports the claim
- PARTIALLY_SUPPORTED: The source partially supports but misses key details
- UNSUPPORTED: The source does not support or contradicts the claim
- HALLUCINATED: The cited source does not exist or is incorrect

Provide your reasoning."""

# ============================================================
# DeepConsult (You.com) Prompts
# ============================================================

DEEPCONSULT_SYSTEM_PROMPT = """You are an expert evaluator of deep research reports.
Compare the following two reports and determine which is better.

Evaluation Dimensions:
1. Instruction Following: Does the report address all user requirements?
2. Comprehensiveness: Does it cover the topic thoroughly?
3. Completeness: Are all sub-topics adequately explored?
4. Writing Quality: Is the report well-structured and clearly written?"""

DEEPCONSULT_EVAL_PROMPT = """User Query: {query}

Report A (Baseline):
{report_a}

Report B (Candidate):
{report_b}

For each dimension, state which report is better and why.
Then provide an overall verdict: A is better, B is better, or TIE."""

# ============================================================
# GAIA 官方评估 Prompt
# ============================================================

GAIA_OFFICIAL_JUDGE = """You are given a question, a ground truth answer, and a
model's predicted answer. Determine if the model's answer matches the
ground truth.

Question: {question}
Ground Truth: {ground_truth}
Predicted: {prediction}

Rules:
1. Minor formatting differences (units, decimal places) should be ignored
2. Semantic equivalence is what matters
3. If the model's answer contains the correct answer among other text,
   it should be counted as CORRECT
4. Output ONLY "Correct" or "Incorrect", nothing else."""

# ============================================================
# 汇总所有 Prompt
# ============================================================

ALL_PROMPTS: list[PromptTemplate] = [
    # ---- Tongyi Inference Prompts ----
    PromptTemplate(
        name="Tongyi System Prompt",
        category="inference",
        framework="tongyi",
        sub_type="system",
        description="核心 Agent 系统提示，定义身份和行为原则",
        template=TONGYI_SYSTEM_PROMPT,
        source_file="WebAgent/WebResummer/src/prompt.py",
        notes="Bitter Lesson 体现——相对简洁，主要定义身份和三大原则",
    ),
    PromptTemplate(
        name="Tongyi User Prompt (ReAct Format)",
        category="inference",
        framework="tongyi",
        sub_type="user",
        description="ReAct 格式的工具使用指令模板",
        template=TONGYI_USER_PROMPT,
        variables=["tools", "question"],
        source_file="WebAgent/WebResummer/src/prompt.py",
        notes="使用 XML 标签 (<think>/<tool_call>/<answer>) 结构化输出",
    ),
    PromptTemplate(
        name="Tongyi EXTRACTOR_PROMPT",
        category="inference",
        framework="tongyi",
        sub_type="extractor",
        description="网页内容三步抽取法（rational/evidence/summary）",
        template=TONGYI_EXTRACTOR_PROMPT,
        variables=["goal", "content"],
        source_file="WebAgent/WebResummer/src/prompt.py",
        notes="Goal-conditioned 抽取大幅提升信噪比",
    ),
    # ---- Tongyi Evaluation Prompts ----
    PromptTemplate(
        name="Tongyi JUDGE_PROMPT_GAIA",
        category="evaluation",
        framework="tongyi",
        sub_type="judge",
        description="GAIA 数据集 Judge——简单等价判断",
        template=TONGYI_JUDGE_GAIA,
        variables=["question", "correct_answer", "response"],
        source_file="evaluation/prompt.py",
        notes="最简单的 Judge——只输出 Correct/Incorrect 两个词",
    ),
    PromptTemplate(
        name="Tongyi JUDGE_PROMPT_QA",
        category="evaluation",
        framework="tongyi",
        sub_type="judge",
        description="QA 数据集 Judge——三级评分 (CORRECT/INCORRECT/NOT_ATTEMPTED)",
        template=TONGYI_JUDGE_QA,
        variables=["question", "correct_answer", "response"],
        source_file="evaluation/prompt.py",
        notes="使用 Obama 孩子示例作为 Few-shot 校准",
    ),
    PromptTemplate(
        name="Tongyi JUDGE_PROMPT_CONFIDENCE",
        category="evaluation",
        framework="tongyi",
        sub_type="judge",
        description="置信度评估 Judge——结构化 JSON 输出",
        template=TONGYI_JUDGE_CONFIDENCE,
        variables=["response", "correct_answer"],
        source_file="evaluation/prompt.py",
        notes="强制 JSON 输出，包含 correct/reasoning/confidence 字段",
    ),
    PromptTemplate(
        name="Tongyi JUDGE_PROMPT_BC_EN",
        category="evaluation",
        framework="tongyi",
        sub_type="judge",
        description="BrowseComp 英文 Judge——详细评分标准",
        template=TONGYI_JUDGE_BC_EN,
        variables=["question", "correct_answer", "response"],
        source_file="WebAgent/WebResummer/src/judge_prompt.py",
        notes="三维度：语义等价/完整性/准确性",
    ),
    PromptTemplate(
        name="Tongyi JUDGE_PROMPT_BC_ZH",
        category="evaluation",
        framework="tongyi",
        sub_type="judge",
        description="BrowseComp 中文 Judge——中文网络特殊考量",
        template=TONGYI_JUDGE_BC_ZH,
        variables=["question", "correct_answer", "response"],
        source_file="WebAgent/WebResummer/src/judge_prompt.py",
        notes="中文版，考虑命名规则不一致等中文特有挑战",
    ),
    PromptTemplate(
        name="Tongyi JUDGE_PROMPT_HLE",
        category="evaluation",
        framework="tongyi",
        sub_type="judge",
        description="HLE (Humanity's Last Exam) Judge——结构化 JSON + 专家审查标记",
        template=TONGYI_JUDGE_HLE,
        variables=["question", "correct_answer", "response"],
        source_file="evaluation/evaluate_hle_official.py",
        notes="最高难度的 Judge，标记是否需要人类专家审查",
    ),
    # ---- ReportBench Prompts ----
    PromptTemplate(
        name="ReportBench Claim Extractor",
        category="evaluation",
        framework="reportbench",
        sub_type="extractor",
        description="从研究报告中提取事实声明及其引用",
        template=REPORTBENCH_EXTRACT_PROMPT,
        variables=["report_text"],
        source_file="extract_citations.py (推测)",
        notes="声明分类：quantitative/qualitative/referential",
    ),
    PromptTemplate(
        name="ReportBench Judge (Factual Claim)",
        category="evaluation",
        framework="reportbench",
        sub_type="judge",
        description="逐声明验证是否被来源支持",
        template=REPORTBENCH_JUDGE_PROMPT,
        variables=["claim", "source_text"],
        source_file="evaluation pipeline (推测)",
        notes="四级评分：SUPPORTED/PARTIALLY/UNSUPPORTED/HALLUCINATED",
    ),
    # ---- DeepConsult Prompts ----
    PromptTemplate(
        name="DeepConsult System Prompt",
        category="evaluation",
        framework="deepconsult",
        sub_type="system",
        description="成对比较评估系统提示——四维度评估",
        template=DEEPCONSULT_SYSTEM_PROMPT,
        source_file="deep_research_pairwise_evals.py",
        notes="维度：指令遵循/全面性/完整性/写作质量",
    ),
    PromptTemplate(
        name="DeepConsult Eval Prompt",
        category="evaluation",
        framework="deepconsult",
        sub_type="judge",
        description="成对比较评估模板——A vs B 对比",
        template=DEEPCONSULT_EVAL_PROMPT,
        variables=["query", "report_a", "report_b"],
        source_file="deep_research_pairwise_evals.py",
        notes="包含位置偏差缓解——翻转 A/B 顺序取平均",
    ),
    # ---- GAIA Official ----
    PromptTemplate(
        name="GAIA Official Judge",
        category="evaluation",
        framework="gaia",
        sub_type="judge",
        description="GAIA 官方评估 Judge——考虑格式化差异和语义等价",
        template=GAIA_OFFICIAL_JUDGE,
        variables=["question", "ground_truth", "prediction"],
        notes="规则明确：忽略单位/小数差异、语义等价即可、答案被包含也算对",
    ),
]

# ============================================================
# 对比分析数据
# ============================================================

PROMPT_COMPARISONS = {
    "inference_characteristics": {
        "identity": "将 Agent 定义为有特定能力的角色（如 'Web Information Seeking Master'）",
        "behavior_rules": "列举行为原则（如持续性、验证性、细节关注）",
        "tool_definitions": "嵌入 JSON Schema 格式的工具定义",
        "output_format": "使用 XML/JSON 标签约束输出结构",
        "context_management": "定义摘要触发条件、裁剪策略、降级方案",
        "stop_conditions": "定义停止序列防止幻觉生成",
    },
    "evaluation_characteristics": {
        "role_definition": "将 Judge 定义为评估助手",
        "input_structure": "注入三要素：问题 + 标准答案 + 预测答案",
        "scoring_rubric": "明确定义评分标准和边界",
        "few_shot_examples": "使用具体示例校准评分标准",
        "output_constraint": "限制为固定词汇或 JSON Schema",
    },
    "key_differences": [
        {
            "aspect": "目标导向",
            "inference": "驱动行动（搜索、浏览、提取、综合）",
            "evaluation": "驱动判断（正确、错误、未尝试、置信度）",
        },
        {
            "aspect": "复杂度趋势",
            "inference": "越来越简单（Bitter Lesson → 通用 ReAct 取代手工 prompt）",
            "evaluation": "越来越复杂（多轴 rubric → claim-graph 验证 → 过程评估）",
        },
        {
            "aspect": "上下文范围",
            "inference": "管理 100K+ tokens 流式工具调用结果",
            "evaluation": "全局评估完整输出（最终答案或长篇报告）",
        },
        {
            "aspect": "优化方法",
            "inference": "遗传式 prompt 进化 + RL 微调（GRPO）",
            "evaluation": "人类专家校准 + ELO 锦标赛对比",
        },
        {
            "aspect": "核心挑战",
            "inference": "上下文腐烂、认知窒息、噪声污染",
            "evaluation": "隐性需求遗漏、Judge 偏见、reward hacking",
        },
        {
            "aspect": "结构化程度",
            "inference": "中低——给 Agent 探索空间",
            "evaluation": "高——确保评分一致性",
        },
    ],
}

# ============================================================
# 输出函数
# ============================================================


def list_all_prompts(category: str = "all") -> None:
    """列出所有 prompt"""
    prompts = ALL_PROMPTS
    if category != "all":
        prompts = [p for p in prompts if p.category == category]

    print(f"\n{'='*80}")
    print(f"{'推理 (Inference) Prompt' if category == 'inference' else '评估 (Evaluation) Prompt' if category == 'evaluation' else '所有 Prompt'} 总览")
    print(f"{'='*80}\n")

    current_framework = ""
    for p in prompts:
        if p.framework != current_framework:
            current_framework = p.framework
            print(f"\n── {current_framework.upper()} ──")

        cat_icon = "[I]" if p.category == "inference" else "[E]"
        print(f"  {cat_icon} [{p.sub_type.upper()}] {p.name}")
        print(f"     {p.description}")
        if p.variables:
            print(f"     变量: {', '.join(p.variables)}")
        print()


def show_framework_prompts(framework: str) -> None:
    """显示特定框架的所有 prompt"""
    prompts = [p for p in ALL_PROMPTS if p.framework.lower() == framework.lower()]

    if not prompts:
        print(f"未找到框架 '{framework}' 的 prompt")
        return

    print(f"\n{'='*80}")
    print(f"框架: {framework} — 完整 Prompt 详情")
    print(f"{'='*80}")

    for p in prompts:
        cat_name = "推理 (Inference)" if p.category == "inference" else "评估 (Evaluation)"
        print(f"\n{'─'*80}")
        print(f"[{cat_name}] [{p.sub_type.upper()}] {p.name}")
        print(f"描述: {p.description}")
        print(f"源文件: {p.source_file}")
        if p.notes:
            print(f"备注: {p.notes}")
        if p.variables:
            print(f"变量: {', '.join(p.variables)}")
        print(f"\n{'─'*40} TEMPLATE {'─'*40}")
        print(p.template)
        print(f"{'─'*80}\n")


def compare_frameworks(fw1: str, fw2: str) -> None:
    """对比两个框架的 prompt 设计"""
    p1 = [p for p in ALL_PROMPTS if p.framework.lower() == fw1.lower()]
    p2 = [p for p in ALL_PROMPTS if p.framework.lower() == fw2.lower()]

    print(f"\n{'='*80}")
    print(f"Prompt 设计对比: {fw1} vs {fw2}")
    print(f"{'='*80}\n")

    # 分类统计
    def count_by_category(prompts):
        inf = sum(1 for p in prompts if p.category == "inference")
        eva = sum(1 for p in prompts if p.category == "evaluation")
        return inf, eva

    inf1, eva1 = count_by_category(p1)
    inf2, eva2 = count_by_category(p2)

    print(f"| 维度 | {fw1} | {fw2} |")
    print(f"|------|{'─'*len(fw1)}|{'─'*len(fw2)}|")
    print(f"| 推理 Prompt 数 | {inf1} | {inf2} |")
    print(f"| 评估 Prompt 数 | {eva1} | {eva2} |")
    print(f"| Prompt 总数 | {len(p1)} | {len(p2)} |")

    # sub_type 分布
    subtypes1 = set(p.sub_type for p in p1)
    subtypes2 = set(p.sub_type for p in p2)
    print(f"| Prompt 类型 | {', '.join(subtypes1)} | {', '.join(subtypes2)} |")

    # 共同类型
    common = subtypes1 & subtypes2
    only1 = subtypes1 - subtypes2
    only2 = subtypes2 - subtypes1
    if only1:
        print(f"| 独有类型 | {', '.join(only1)} | — |")
    if only2:
        print(f"| 独有类型 | — | {', '.join(only2)} |")

    print()

    # 关键设计差异
    print("关键设计差异:")
    print(f"  {fw1}:")
    for p in p1:
        if p.notes:
            print(f"    - {p.name}: {p.notes}")
    print(f"  {fw2}:")
    for p in p2:
        if p.notes:
            print(f"    - {p.name}: {p.notes}")


def show_inference_vs_eval_analysis() -> None:
    """展示推理 vs 评估 prompt 的核心差异分析"""
    print(f"\n{'='*80}")
    print("推理 Prompt vs 评估 Prompt 核心差异分析")
    print(f"{'='*80}\n")

    print("【推理 Prompt 特征】")
    for key, desc in PROMPT_COMPARISONS["inference_characteristics"].items():
        print(f"  {key}: {desc}")

    print("\n【评估 Prompt 特征】")
    for key, desc in PROMPT_COMPARISONS["evaluation_characteristics"].items():
        print(f"  {key}: {desc}")

    print(f"\n【维度对比表】")
    print(f"| {'维度':<16} | {'推理 Prompt':<50} | {'评估 Prompt':<50} |")
    print(f"|{'─'*16} |{'─'*50} |{'─'*50} |")
    for diff in PROMPT_COMPARISONS["key_differences"]:
        print(f"| {diff['aspect']:<16} | {diff['inference']:<50} | {diff['evaluation']:<50} |")


def export_prompts(output_dir: str) -> None:
    """导出所有 prompt 到 JSON 文件"""
    os.makedirs(output_dir, exist_ok=True)

    data = {}
    for p in ALL_PROMPTS:
        if p.framework not in data:
            data[p.framework] = {"inference": [], "evaluation": []}
        data[p.framework][p.category].append({
            "name": p.name,
            "sub_type": p.sub_type,
            "description": p.description,
            "template": p.template,
            "variables": p.variables,
            "source_file": p.source_file,
            "notes": p.notes,
        })

    # 按框架导出
    for framework, prompts in data.items():
        filepath = os.path.join(output_dir, f"{framework}_prompts.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(prompts, f, ensure_ascii=False, indent=2)
        print(f"已导出: {filepath}")

    # 导出全部
    all_filepath = os.path.join(output_dir, "all_prompts.json")
    with open(all_filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"已导出: {all_filepath}")

    # 导出对比分析
    compare_filepath = os.path.join(output_dir, "inference_vs_eval_analysis.json")
    with open(compare_filepath, "w", encoding="utf-8") as f:
        json.dump(PROMPT_COMPARISONS, f, ensure_ascii=False, indent=2)
    print(f"已导出: {compare_filepath}")

    print(f"\n共导出 {len(ALL_PROMPTS)} 个 Prompt 模板到 {output_dir}/")


# ============================================================
# 主入口
# ============================================================


def main():
    parser = argparse.ArgumentParser(
        description="Deep Research Prompt 提取与分析工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s                                    # 列出所有 prompt
  %(prog)s --framework tongyi                 # Tongyi DR 的全部 prompt
  %(prog)s --category inference               # 仅推理 prompt
  %(prog)s --category evaluation              # 仅评估 prompt
  %(prog)s --compare tongyi reportbench       # 对比两个框架
  %(prog)s --analyze                          # 推理 vs 评估核心差异分析
  %(prog)s --export output_dir/               # 导出 JSON
        """,
    )
    parser.add_argument(
        "--framework", "-f",
        type=str,
        help="查看特定框架的 prompt (tongyi/gaia/reportbench/deepconsult)",
    )
    parser.add_argument(
        "--category", "-c",
        choices=["inference", "evaluation"],
        help="仅显示推理或评估 prompt",
    )
    parser.add_argument(
        "--compare",
        nargs=2,
        metavar=("FW1", "FW2"),
        help="对比两个框架的 prompt 设计",
    )
    parser.add_argument(
        "--analyze", "-a",
        action="store_true",
        help="显示推理 vs 评估 prompt 核心差异分析",
    )
    parser.add_argument(
        "--export", "-e",
        type=str,
        metavar="DIR",
        help="导出所有 prompt 到指定目录 (JSON 格式)",
    )

    args = parser.parse_args()

    if args.export:
        export_prompts(args.export)
    elif args.compare:
        compare_frameworks(args.compare[0], args.compare[1])
    elif args.analyze:
        show_inference_vs_eval_analysis()
    elif args.framework:
        show_framework_prompts(args.framework)
    else:
        list_all_prompts(category=args.category or "all")


if __name__ == "__main__":
    main()
