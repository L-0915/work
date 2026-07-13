#!/usr/bin/env python3
"""
Deep Research 评测框架总览工具

输出所有主流 Deep Research 评测框架/基准测试的结构化概览。
覆盖 2024-2026 年 20+ benchmark，包含 GitHub 和 HuggingFace 链接。
支持 JSON、Markdown 表格、终端表格三种输出格式。

用法:
    python eval_framework_overview.py                  # 默认终端表格
    python eval_framework_overview.py --format json    # JSON 输出
    python eval_framework_overview.py --format markdown # Markdown 表格
    python eval_framework_overview.py --format links   # 仅输出所有链接
    python eval_framework_overview.py --year 2026      # 仅看 2026 年
    python eval_framework_overview.py --sort-by samples
    python eval_framework_overview.py --filter gaia
"""

import json
import argparse
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
# 数据结构定义
# ============================================================

@dataclass
class Benchmark:
    name: str
    publisher: str
    release_date: str       # YYYY-MM or YYYY
    year: int               # 年份便于过滤
    samples: str            # "466" or "900" or "动态"
    language: str           # EN / ZH / EN+ZH / KO / 17 languages
    description: str
    eval_method: str
    scoring_type: str       # exact_match / llm_judge / multi_level / pairwise / rubric
    current_sota: str
    sota_score: str
    github_url: str = ""
    huggingface_url: str = ""
    paper_url: str = ""
    key_features: list = field(default_factory=list)
    is_2026: bool = False   # 标记 2026 年新 benchmark


# ============================================================
# 全量 Benchmark 数据（2024-2026，含链接）
# ============================================================

BENCHMARKS: list[Benchmark] = [
    # ---- 2024 ----
    Benchmark(
        name="GAIA",
        publisher="Meta + HuggingFace",
        release_date="2024-04",
        year=2024,
        samples="466",
        language="EN",
        description="通用 AI 助手现实任务评测, 逆转传统基准设计: 对人类简单, 对 AI 极难",
        eval_method="准精确匹配 (Quasi-Exact Match)",
        scoring_type="exact_match",
        current_sota="H2O.ai DR (Claude 3.7 Sonnet)",
        sota_score="79.73%",
        huggingface_url="https://huggingface.co/datasets/gaia-benchmark/GAIA",
        paper_url="https://arxiv.org/abs/2311.12983",
        key_features=[
            "三级难度 (L1: <=5步, L2: 5-10步, L3: 任意)",
            "需要网页浏览、多模态、代码执行、文件读取",
            "人类 92% vs 最佳 AI ~80%",
            "GAIA2 (2025): 模拟智能手机环境",
        ],
    ),
    Benchmark(
        name="GAIA2",
        publisher="Meta Agents Research",
        release_date="2025",
        year=2025,
        samples="动态",
        language="EN",
        description="GAIA 升级版, 模拟智能手机环境 (Email/Calendar/Shopping/FileSystem)",
        eval_method="准精确匹配 (Quasi-Exact Match)",
        scoring_type="exact_match",
        current_sota="—",
        sota_score="—",
        huggingface_url="https://huggingface.co/datasets/meta-agents-research-environments/Gaia2",
        key_features=["模拟智能手机 + 真实 App", "复杂多步行为", "Persona-based 历史"],
    ),
    Benchmark(
        name="FRAMES",
        publisher="Google DeepMind + Harvard + Meta",
        release_date="2024-09",
        year=2024,
        samples="824",
        language="EN",
        description="事实性/检索/推理综合评测, 每问需 2-15 篇 Wikipedia",
        eval_method="三级评分 (CORRECT/INCORRECT/NOT_ATTEMPTED)",
        scoring_type="multi_level",
        current_sota="—",
        sota_score="~73% (Oracle 上限)",
        huggingface_url="https://huggingface.co/datasets/google/frames-benchmark",
        paper_url="https://arxiv.org/abs/2409.12941",
        key_features=[
            "推理类型标注: 多约束(~36%)/数值(~20%)/时间/表格",
            "即使给出 Oracle 文章, 上限也仅 ~73%",
            "Apache 2.0 开源",
        ],
    ),

    # ---- 2025 ----
    Benchmark(
        name="BrowseComp",
        publisher="OpenAI",
        release_date="2025-04",
        year=2025,
        samples="1,266",
        language="EN",
        description="网页浏览的编程竞赛, 衡量 Agent 在真实互联网上寻找难以发现关联信息的能力",
        eval_method="LLM Judge (语义等价)",
        scoring_type="llm_judge",
        current_sota="Kimi K2.5 Swarm (多 Agent)",
        sota_score="72.1%",
        paper_url="https://openreview.net/forum?id=ErnvfmSX0P",
        key_features=[
            "多约束条件, 答案唯一且简短",
            "直接 Google 搜不到, 需要多步导航",
            "人类专家(30min) 87.5%",
            "数据集加密, 含 canary string 防污染",
        ],
    ),
    Benchmark(
        name="BrowseComp-ZH",
        publisher="HKUST",
        release_date="2025-04",
        year=2025,
        samples="289",
        language="ZH",
        description="中文版 BrowseComp, 专门针对中文网络信息检索的特殊挑战",
        eval_method="LLM Judge",
        scoring_type="llm_judge",
        current_sota="—",
        sota_score="—",
        key_features=[
            "11 个领域 (影视 15.6%/艺术 13.8%/地理 12.8%)",
            "中文命名规则不一致、隐式指代",
            "两阶段质量验证",
        ],
    ),
    Benchmark(
        name="BrowseComp-Plus",
        publisher="Chen et al. (ACL 2026)",
        release_date="2025-08",
        year=2025,
        samples="830",
        language="EN",
        description="离线版 BrowseComp, 固定 ~100K 人工验证文档语料库, 分离 Retriever 和 Agent 贡献",
        eval_method="精确匹配 (Exact Match)",
        scoring_type="exact_match",
        current_sota="GPT-5 + Qwen3-Embedding-8B",
        sota_score="70.1%",
        github_url="https://github.com/texttron/BrowseComp-Plus",
        huggingface_url="https://huggingface.co/datasets/Tevatron/browsecomp-plus-corpus",
        paper_url="https://aclanthology.org/2026.acl-long.1023/",
        key_features=[
            "ACL 2026 Main",
            "完全可复现 — 固定本地语料库",
            "Search-R1 + BM25 仅 3.86%",
            "解密后用固定 corpus 评测",
        ],
    ),
    Benchmark(
        name="xbench-DeepSearch",
        publisher="红杉中国 (xbench-ai)",
        release_date="2025-06",
        year=2025,
        samples="100 (加密)",
        language="ZH",
        description="端到端深度搜索评测, 无法通过单次简单 Query 直接获得答案",
        eval_method="LLM Judge",
        scoring_type="llm_judge",
        current_sota="ChatGPT-5-Pro",
        sota_score="75+",
        github_url="https://github.com/xbench-ai/xbench-evals",
        huggingface_url="https://huggingface.co/datasets/xbench/DeepSearch",
        paper_url="https://arxiv.org/abs/2506.13651",
        key_features=[
            "「想谜底, 出谜面」逆向设计",
            "加密数据集 (XOR), canary GUID",
            "新版 DeepSearch-2510 已发布",
            "ChatGPT-5-Pro 75+, SuperGrok 40+",
        ],
    ),
    Benchmark(
        name="WideSearch",
        publisher="Seed (字节跳动)",
        release_date="2025-08",
        year=2025,
        samples="200",
        language="EN+ZH",
        description="多约束广度搜索评测, 答案为事实集而非单一事实",
        eval_method="事实集匹配 (F1-by-row)",
        scoring_type="exact_match",
        current_sota="Perplexity",
        sota_score="65.1%",
        key_features=["18 领域", "中英双语", "答案为事实集(非单一事实)"],
    ),
    Benchmark(
        name="FinSearchComp",
        publisher="Seed (字节跳动)",
        release_date="2025-09",
        year=2025,
        samples="635",
        language="EN+ZH",
        description="金融领域时间敏感搜索评测",
        eval_method="事实匹配",
        scoring_type="exact_match",
        current_sota="—",
        sota_score="—",
        key_features=["专注金融领域", "时间敏感/简单历史/复杂历史三类"],
    ),
    Benchmark(
        name="WebWalkerQA",
        publisher="—",
        release_date="2025",
        year=2025,
        samples="680",
        language="EN",
        description="网页遍历与交互评测, 行动型问题",
        eval_method="—",
        scoring_type="multi_level",
        current_sota="Tongyi DeepResearch",
        sota_score="62.1%",
        key_features=["网页遍历和交互", "行动型问题", "页面内导航和点击"],
    ),
    Benchmark(
        name="HLE",
        publisher="—",
        release_date="2025",
        year=2025,
        samples="2,158",
        language="EN",
        description="Humanity's Last Exam: 专家级极难推理问题集",
        eval_method="LLM Judge (结构化 JSON)",
        scoring_type="llm_judge",
        current_sota="Tongyi DeepResearch",
        sota_score="32.9%",
        key_features=["2,158 专家级问题", "JSON Judge (reasoning+confidence)", "跨领域专业知识"],
    ),
    Benchmark(
        name="ReportBench",
        publisher="ByteDance",
        release_date="2025-08",
        year=2025,
        samples="动态",
        language="EN",
        description="学术综述任务评测, 使用 arXiv 论文作为黄金标准, 反向 Prompt 工程",
        eval_method="双路径: 引用一致性 + 事实正确性",
        scoring_type="rubric",
        current_sota="—",
        sota_score="—",
        github_url="https://github.com/ByteDance-BandAI/ReportBench",
        paper_url="https://arxiv.org/abs/2508.15804",
        key_features=["Apache 2.0", "反向 Prompt 工程", "完整自动化 pipeline"],
    ),
    Benchmark(
        name="DeepConsult",
        publisher="You.com",
        release_date="2025-05",
        year=2025,
        samples="动态",
        language="EN",
        description="商业咨询场景 Deep Research 评测, 成对比较框架",
        eval_method="成对比较 (Pairwise Comparison)",
        scoring_type="pairwise",
        current_sota="—",
        sota_score="—",
        github_url="https://github.com/youdotcom-oss/ydc-deep-research-evals",
        key_features=["MIT 开源", "4 维度", "位置偏差缓解", "可编程调用"],
    ),

    # ---- 2026 ----
    Benchmark(
        name="DeepSearchQA",
        publisher="Google DeepMind",
        release_date="2026-01",
        year=2026,
        samples="900",
        language="EN",
        description="弥合 Deep Research Agent 的全面性鸿沟 (Comprehensiveness Gap), 17 领域, 65% 集合答案",
        eval_method="LLM Judge (Gemini 2.5 Flash auto-rater)",
        scoring_type="llm_judge",
        current_sota="Google Deep Research Max (Gemini 3.1 Pro)",
        sota_score="93.3%",
        huggingface_url="https://huggingface.co/datasets/google/deepsearchqa",
        paper_url="https://arxiv.org/abs/2601.20975",
        is_2026=True,
        key_features=[
            "Apache 2.0 开源!",
            "65% 集合答案 (Set Answer): 评估「答全」而非「答对」",
            "17 领域, 因果链任务结构",
            "Kaggle Leaderboard 可用",
            "4 个月前 SOTA 仅 66.1%, 如今 93.3%",
        ],
    ),
    Benchmark(
        name="DRB2",
        publisher="社区 (imlrz)",
        release_date="2026-02",
        year=2026,
        samples="132 报告 / 9,430 rubrics",
        language="EN",
        description="DeepResearch Bench II: 专家报告层级化 Rubric 诊断评估, 三大维度",
        eval_method="层级化 Rubric 评分",
        scoring_type="rubric",
        current_sota="—",
        sota_score="—",
        github_url="https://github.com/imlrz/DeepResearch-Bench-II",
        paper_url="https://arxiv.org/abs/2601.08536",
        is_2026=True,
        key_features=[
            "132 份专家报告 -> 9,430 rubrics",
            "三维度: Presentation/Analysis/Evidence",
            "诊断系统与人类专家差距",
        ],
    ),
    Benchmark(
        name="MM-BrowseComp",
        publisher="MMBrowseComp 社区",
        release_date="2026-01",
        year=2026,
        samples="400",
        language="EN",
        description="多模态网页浏览 Agent 评测, 需要图片+文本联合理解",
        eval_method="LLM Judge",
        scoring_type="llm_judge",
        current_sota="—",
        sota_score="—",
        github_url="https://github.com/MMBrowseComp/MM-BrowseComp",
        huggingface_url="https://huggingface.co/datasets/mmbrowsecomp/MMBrowseComp",
        paper_url="https://arxiv.org/abs/2508.13186",
        is_2026=True,
        key_features=[
            "加密数据集 (防污染)",
            "需要图文联合理解",
            "2026-01 扩展至 400 问题",
        ],
    ),
    Benchmark(
        name="LiveBrowseComp",
        publisher="Forival 社区",
        release_date="2026-05",
        year=2026,
        samples="335",
        language="EN",
        description="90 天内新事实, 反制知识污染: 闭卷<2%, 搜索后下降 25-40 分",
        eval_method="LLM Judge",
        scoring_type="llm_judge",
        current_sota="—",
        sota_score="—",
        huggingface_url="https://huggingface.co/datasets/Forival/LiveBrowseComp",
        paper_url="https://arxiv.org/abs/2605.28721",
        is_2026=True,
        key_features=[
            "所有问题依赖 90 天内发布的事实",
            "闭卷得分 <2% — 有效反制知识污染",
            "搜索增强后仍下降 25-40 分 vs BrowseComp",
            "335 人工编写问题",
        ],
    ),
    Benchmark(
        name="K-BrowseComp",
        publisher="prometheus-eval",
        release_date="2026-06",
        year=2026,
        samples="400",
        language="KO",
        description="韩语网页浏览 Agent 评测, 300 验证 + 100 合成问题",
        eval_method="LLM Judge",
        scoring_type="llm_judge",
        current_sota="—",
        sota_score="<50%",
        github_url="https://github.com/prometheus-eval/K-BrowseComp",
        huggingface_url="https://huggingface.co/datasets/prometheus-eval/k-browsecomp",
        is_2026=True,
        key_features=["首个韩语 BrowseComp", "最强模型仍低于 50%", "300+100 问题"],
    ),
    Benchmark(
        name="DRACO",
        publisher="Perplexity AI",
        release_date="2026-02",
        year=2026,
        samples="真实用户数据",
        language="EN (40 国)",
        description="跨领域跨国家 Deep Research 评测: 准确性/完整性/客观性/引用质量",
        eval_method="多维度 Rubric 评分",
        scoring_type="rubric",
        current_sota="—",
        sota_score="—",
        huggingface_url="https://huggingface.co/datasets/perplexity-ai/draco",
        paper_url="https://arxiv.org/abs/2602.11685",
        is_2026=True,
        key_features=[
            "10 领域 + 40 国家",
            "基于真实 Perplexity DR 使用数据",
            "4 维度: 准确性/完整性/客观性/引用",
        ],
    ),
    Benchmark(
        name="PhySciBench",
        publisher="社区 (yigengjiang)",
        release_date="2026-06",
        year=2026,
        samples="200",
        language="EN",
        description="物理+化学深度研究, 6 种任务类型, 最强 baseline 仅 33.5%",
        eval_method="LLM Judge",
        scoring_type="llm_judge",
        current_sota="Gemini Deep Research",
        sota_score="33.5%",
        github_url="https://github.com/yigengjiang/physci-deepresearch",
        huggingface_url="https://huggingface.co/datasets/littletreee/PhySciBench",
        paper_url="https://arxiv.org/abs/2606.18648",
        is_2026=True,
        key_features=[
            "200 物理+化学专家问题",
            "6 任务类型: QA/实验设计/代码生成等",
            "最强 baseline 仅 33.5% — 巨大空间",
        ],
    ),
    Benchmark(
        name="MMDR-Bench",
        publisher="AIoT-MLSys-Lab",
        release_date="2026-01",
        year=2026,
        samples="140",
        language="EN",
        description="多模态深度研究评测, 19 领域, 3 阶段 12 指标评估 pipeline",
        eval_method="3 阶段 12 指标 pipeline",
        scoring_type="rubric",
        current_sota="—",
        sota_score="—",
        github_url="https://github.com/AIoT-MLSys-Lab/MMDeepResearch-Bench",
        paper_url="https://arxiv.org/abs/2601.12346",
        is_2026=True,
        key_features=[
            "140 专家策划多模态任务",
            "19 领域覆盖",
            "声明-证据对齐 + 视觉保真度 + 图像推理",
        ],
    ),
    Benchmark(
        name="PDR-Bench",
        publisher="OPPO PersonalAI (ICLR 2026)",
        release_date="2026",
        year=2026,
        samples="50 任务 x 25 画像",
        language="EN",
        description="个性化 Deep Research: PQR 框架 (Personalization/Quality/Reliability)",
        eval_method="PQR 三维度评估",
        scoring_type="rubric",
        current_sota="—",
        sota_score="—",
        github_url="https://github.com/OPPO-PersonalAI/PersonalizedDeepResearchBench",
        huggingface_url="https://huggingface.co/datasets/PersonalAILab/PersonalizedDeepResearchBench",
        paper_url="https://arxiv.org/abs/2509.25106",
        is_2026=True,
        key_features=[
            "ICLR 2026",
            "50 专家任务 x 25 真实用户画像",
            "首次引入个性化对齐评估",
        ],
    ),
    Benchmark(
        name="InfoSeek",
        publisher="北京智源 (BAAI)",
        release_date="2026",
        year=2026,
        samples="50,000+",
        language="EN",
        description="首个专为 Deep Research 打造的开源数据集, 3B 模型训练后匹配 Gemini/Sonnet",
        eval_method="Exact Match",
        scoring_type="exact_match",
        current_sota="—",
        sota_score="—",
        github_url="https://github.com/VectorSpaceLab/InfoSeek",
        huggingface_url="https://huggingface.co/datasets/Lk123/InfoSeek",
        paper_url="https://arxiv.org/abs/2509.00375",
        is_2026=True,
        key_features=[
            "50K+ 高质量多步推理样本",
            "首个专为 DR 打造的开源数据集",
            "3B 模型训练后匹配 Gemini/Sonnet 4.0",
        ],
    ),
    Benchmark(
        name="KnowledgeBerg",
        publisher="学术 (ACL 2026 Findings)",
        release_date="2026",
        year=2026,
        samples="4,800",
        language="17 语言",
        description="系统性知识覆盖 + 基于集合的组合推理, 10 领域 17 语言",
        eval_method="多选题 (MC)",
        scoring_type="exact_match",
        current_sota="—",
        sota_score="—",
        huggingface_url="https://huggingface.co/datasets/2npc/KnowledgeBerg",
        paper_url="https://aclanthology.org/2026.findings-acl.548/",
        is_2026=True,
        key_features=[
            "ACL 2026 Findings",
            "4,800 多选问题, 10 领域",
            "17 种语言覆盖",
            "组合推理 + 知识覆盖",
        ],
    ),
]

# ============================================================
# 辅助工具 Benchmark
# ============================================================

TOOLS = [
    {
        "name": "Perplexity search_evals",
        "description": "开箱即用的搜索 API 评估框架, 集成 DeepSearchQA/BrowseComp/HLE/WideSearch",
        "github_url": "https://github.com/perplexityai/search_evals",
    },
    {
        "name": "LDR Benchmarks",
        "description": "社区驱动 Local Deep Research 排行榜, 聚合 SimpleQA/BrowseComp/xbench 结果",
        "github_url": "https://github.com/LearningCircuit/ldr-benchmarks",
        "huggingface_url": "https://huggingface.co/datasets/local-deep-research/ldr-benchmarks",
    },
    {
        "name": "OpenResearcher",
        "description": "全开源 30B Deep Research 模型 + 评测日志, BrowseComp-Plus 54.8%",
        "github_url": "https://github.com/TIGER-AI-Lab/OpenResearcher",
        "huggingface_url": "https://huggingface.co/datasets/OpenResearcher/OpenResearcher-Eval-Logs",
    },
    {
        "name": "Web-Bench (统一格式)",
        "description": "HuggingFace 统一 benchmark 格式项目",
        "huggingface_url": "https://huggingface.co/datasets/OpenResearcher/web-bench",
    },
    {
        "name": "EvalScope (ModelScope)",
        "description": "ModelScope 评测框架, 已集成 FRAMES benchmark",
        "github_url": "https://github.com/modelscope/evalscope",
    },
]

# ============================================================
# 评分方式分类
# ============================================================

SCORING_METHODS = {
    "exact_match": {
        "name": "精确匹配 (Exact Match)",
        "description": "答案归一化后做字符串匹配。适用于答案为数字/短字符串的场景。",
        "pros": ["完全客观", "可复现", "零成本", "无 Judge 偏差"],
        "cons": ["对表述差异过于严格", "无法处理开放性答案"],
        "benchmarks": ["GAIA", "GAIA2", "BrowseComp-Plus", "WideSearch", "FinSearchComp", "InfoSeek", "KnowledgeBerg"],
    },
    "llm_judge": {
        "name": "LLM-as-Judge",
        "description": "使用另一个 LLM 判断答案语义等价性。",
        "pros": ["灵活处理语义等价", "可评估复杂/开放性答案"],
        "cons": ["依赖 Judge 模型质量", "存在偏见", "成本较高"],
        "benchmarks": ["BrowseComp", "BrowseComp-ZH", "MM-BrowseComp", "LiveBrowseComp", "K-BrowseComp", "xbench-DeepSearch", "HLE", "DeepSearchQA", "PhySciBench"],
    },
    "multi_level": {
        "name": "多级评分 (Multi-Level)",
        "description": "区分 CORRECT/INCORRECT/NOT_ATTEMPTED 等不同等级。",
        "pros": ["区分未尝试 vs 错误", "更细粒度分析"],
        "cons": ["边界定义需精细校准"],
        "benchmarks": ["FRAMES", "WebWalkerQA"],
    },
    "pairwise": {
        "name": "成对比较 (Pairwise)",
        "description": "比较两个系统在同一问题上的输出质量。",
        "pros": ["消除绝对评分偏差", "适合长文本"],
        "cons": ["位置偏差需要缓解", "计算成本高"],
        "benchmarks": ["DeepConsult"],
    },
    "rubric": {
        "name": "标准评分 (Rubric)",
        "description": "多维度多轴标准评分。适用于学术报告等复杂输出。",
        "pros": ["多维度覆盖", "可定制化"],
        "cons": ["需要大量专家标注", "伸缩性受限"],
        "benchmarks": ["ReportBench", "DRB2", "DRACO", "MMDR-Bench", "PDR-Bench"],
    },
}

# ============================================================
# 输出函数
# ============================================================


def output_table(benchmarks: list[Benchmark]) -> None:
    """终端表格输出"""
    headers = ["名称", "年份", "发布方", "样本", "语言", "评分方式", "SOTA", "GitHub/HF"]
    rows = []
    for b in benchmarks:
        has_link = "Y" if (b.github_url or b.huggingface_url) else "—"
        rows.append([
            b.name,
            str(b.year),
            b.publisher[:22],
            str(b.samples),
            b.language,
            b.scoring_type,
            b.sota_score,
            has_link,
        ])

    col_widths = [
        max(len(str(row[i])) for row in [headers] + rows) + 2
        for i in range(len(headers))
    ]

    def fmt_row(row):
        return "|".join(str(cell).ljust(col_widths[i]) for i, cell in enumerate(row))

    separator = "+".join("-" * w for w in col_widths)

    print(separator)
    print(fmt_row(headers))
    print(separator)
    for row in rows:
        print(fmt_row(row))
    print(separator)
    print(f"\n共 {len(benchmarks)} 个 Benchmark\n")


def output_markdown(benchmarks: list[Benchmark]) -> None:
    """Markdown 表格输出 (含链接)"""
    print("| Benchmark | 年份 | 发布方 | 样本 | 语言 | 评分 | SOTA | GitHub | HuggingFace |")
    print("|-----------|------|--------|------|------|------|------|--------|-------------|")
    for b in benchmarks:
        gh = f"[link]({b.github_url})" if b.github_url else "—"
        hf = f"[link]({b.huggingface_url})" if b.huggingface_url else "—"
        print(f"| **{b.name}** | {b.year} | {b.publisher} | {b.samples} | {b.language} | {b.scoring_type} | {b.sota_score} | {gh} | {hf} |")


def output_json(benchmarks: list[Benchmark]) -> None:
    """JSON 输出 (含完整链接)"""
    data = {
        "total_benchmarks": len(benchmarks),
        "benchmarks": [
            {
                "name": b.name,
                "publisher": b.publisher,
                "year": b.year,
                "release_date": b.release_date,
                "samples": b.samples,
                "language": b.language,
                "description": b.description,
                "evaluation_method": b.eval_method,
                "scoring_type": b.scoring_type,
                "current_sota": b.current_sota,
                "sota_score": b.sota_score,
                "github_url": b.github_url,
                "huggingface_url": b.huggingface_url,
                "paper_url": b.paper_url,
                "key_features": b.key_features,
                "is_2026": b.is_2026,
            }
            for b in benchmarks
        ],
    }
    print(json.dumps(data, ensure_ascii=False, indent=2))


def output_links(benchmarks: list[Benchmark]) -> None:
    """仅输出所有链接"""
    print(f"\n{'='*80}")
    print("Benchmark 链接汇总")
    print(f"{'='*80}\n")
    for b in benchmarks:
        print(f"### {b.name} ({b.year})")
        if b.github_url:
            print(f"  GitHub:      {b.github_url}")
        if b.huggingface_url:
            print(f"  HuggingFace: {b.huggingface_url}")
        if b.paper_url:
            print(f"  Paper:       {b.paper_url}")
        print()

    print(f"\n{'='*80}")
    print("配套工具链接")
    print(f"{'='*80}\n")
    for t in TOOLS:
        print(f"### {t['name']}")
        print(f"  {t['description']}")
        if t.get("github_url"):
            print(f"  GitHub:      {t['github_url']}")
        if t.get("huggingface_url"):
            print(f"  HuggingFace: {t['huggingface_url']}")
        print()


def output_statistics(benchmarks: list[Benchmark]) -> None:
    """输出统计信息"""
    print("\n========== 统计概览 ==========\n")

    # 按年份统计
    year_counts = {}
    for b in benchmarks:
        year_counts[b.year] = year_counts.get(b.year, 0) + 1
    print("按年份分布:")
    for year in sorted(year_counts):
        marker = " <-- 最新" if year == 2026 else ""
        print(f"  {year}: {year_counts[year]} benchmarks{marker}")

    # 按评分方式
    scoring_counts = {}
    for b in benchmarks:
        scoring_counts[b.scoring_type] = scoring_counts.get(b.scoring_type, 0) + 1
    print(f"\n按评分方式分布:")
    for stype, count in sorted(scoring_counts.items(), key=lambda x: -x[1]):
        method_name = SCORING_METHODS.get(stype, {}).get("name", stype)
        print(f"  {method_name}: {count}")

    # 按语言
    lang_counts = {}
    for b in benchmarks:
        for lang in b.language.replace("(", "").replace(")", "").split("+"):
            lang = lang.strip()
            if lang:
                lang_counts[lang] = lang_counts.get(lang, 0) + 1
    print(f"\n按语言分布:")
    for lang, count in sorted(lang_counts.items(), key=lambda x: -x[1]):
        print(f"  {lang}: {count}")

    # 链接覆盖率
    with_gh = sum(1 for b in benchmarks if b.github_url)
    with_hf = sum(1 for b in benchmarks if b.huggingface_url)
    with_paper = sum(1 for b in benchmarks if b.paper_url)
    print(f"\n链接覆盖率:")
    print(f"  GitHub:      {with_gh}/{len(benchmarks)} ({with_gh/len(benchmarks)*100:.0f}%)")
    print(f"  HuggingFace: {with_hf}/{len(benchmarks)} ({with_hf/len(benchmarks)*100:.0f}%)")
    print(f"  Paper:       {with_paper}/{len(benchmarks)} ({with_paper/len(benchmarks)*100:.0f}%)")


def output_scoring_methods() -> None:
    """输出评分方式汇总"""
    print("\n========== 评分方式汇总 ==========\n")
    for key, method in SCORING_METHODS.items():
        print(f"### {method['name']}")
        print(f"  {method['description']}")
        print(f"  优点: {'; '.join(method['pros'])}")
        print(f"  缺点: {'; '.join(method['cons'])}")
        print(f"  使用方: {', '.join(method['benchmarks'])}")
        print()


# ============================================================
# 主入口
# ============================================================


def main():
    parser = argparse.ArgumentParser(
        description="Deep Research 评测框架总览工具 (2024-2026)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s                          # 默认终端表格
  %(prog)s --year 2026              # 仅 2026 年新 benchmark
  %(prog)s --format json            # JSON 输出
  %(prog)s --format markdown        # Markdown 表格 (含链接)
  %(prog)s --format links           # 仅输出所有 GitHub/HF 链接
  %(prog)s --format stats           # 统计信息
  %(prog)s --format scoring         # 评分方式汇总
  %(prog)s --format all             # 全部输出
  %(prog)s --filter gaia            # 按名称过滤
  %(prog)s --sort-by samples        # 按样本数排序
  %(prog)s --scoring-type llm_judge # 按评分方式过滤
        """,
    )
    parser.add_argument("--format", "-f", choices=["table", "json", "markdown", "links", "stats", "scoring", "all"], default="table", help="输出格式 (默认: table)")
    parser.add_argument("--year", "-y", type=int, choices=[2024, 2025, 2026], help="按年份过滤")
    parser.add_argument("--filter", "-q", type=str, default="", help="按名称/发布方过滤")
    parser.add_argument("--sort-by", choices=["name", "samples", "year", "scoring_type"], default="year", help="排序方式")
    parser.add_argument("--scoring-type", choices=list(SCORING_METHODS.keys()), help="按评分方式过滤")
    parser.add_argument("--language", type=str, help="按语言过滤")

    args = parser.parse_args()

    benchmarks = BENCHMARKS.copy()

    if args.year:
        benchmarks = [b for b in benchmarks if b.year == args.year]

    if args.filter:
        q = args.filter.lower()
        benchmarks = [b for b in benchmarks if q in b.name.lower() or q in b.publisher.lower()]

    if args.scoring_type:
        benchmarks = [b for b in benchmarks if b.scoring_type == args.scoring_type]

    if args.language:
        benchmarks = [b for b in benchmarks if args.language.upper() in b.language.upper()]

    if args.sort_by == "samples":
        benchmarks.sort(key=lambda b: int(b.samples.replace(",", "").split()[0]) if b.samples.split()[0].replace(",", "").isdigit() else 0, reverse=True)
    elif args.sort_by == "year":
        benchmarks.sort(key=lambda b: (b.year, b.name.lower()))
    elif args.sort_by == "scoring_type":
        benchmarks.sort(key=lambda b: b.scoring_type)
    else:
        benchmarks.sort(key=lambda b: b.name.lower())

    if args.format == "json":
        output_json(benchmarks)
    elif args.format == "markdown":
        output_markdown(benchmarks)
    elif args.format == "links":
        output_links(benchmarks)
    elif args.format == "stats":
        output_statistics(benchmarks)
    elif args.format == "scoring":
        output_scoring_methods()
    elif args.format == "all":
        output_table(benchmarks)
        output_statistics(benchmarks)
        output_scoring_methods()
    else:
        output_table(benchmarks)


if __name__ == "__main__":
    main()
