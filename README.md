# Deep Research 评测框架深度调研报告

> 调研日期：2026-07-12
> 覆盖 2024-2026 年共 **20+** 个 Benchmark
> 主要分析对象：[Alibaba-NLP/DeepResearch](https://github.com/Alibaba-NLP/DeepResearch)

---

## 目录

1. [2026 年最新 Benchmark 速览](#1-2026-年最新-benchmark-速览)
2. [核心概念：推理 vs 评估的 Prompt 设计差异](#2-核心概念推理-vs-评估的-prompt-设计差异)
3. [全量 Benchmark 详解（含链接）](#3-全量-benchmark-详解含链接)
4. [Alibaba-NLP/DeepResearch 深度分析](#4-alibaba-nlpdeepresearch-深度分析)
5. [评估方法论详解](#5-评估方法论详解)
6. [Prompt 设计对比：推理 Prompt vs 评估 Prompt](#6-prompt-设计对比推理-prompt-vs-评估-prompt)
7. [关键发现与最佳实践](#7-关键发现与最佳实践)
8. [脚本工具说明](#8-脚本工具说明)

---

## 1. 2026 年最新 Benchmark 速览

2026 年是 Deep Research 评测的爆发年，以下是最值得关注的 **11 个新 Benchmark**：

| # | Benchmark | 发布时间 | 发布方 | 样本量 | 核心创新 |
|---|-----------|----------|--------|--------|----------|
| 1 | **DeepSearchQA** | 2026-01 | Google DeepMind | 900 | 弥合全面性鸿沟，17 领域，65% 集合答案 |
| 2 | **DeepResearch Bench II** | 2026-02 | 社区 | 132 报告 / 9,430 rubrics | 层级化专家 rubric 诊断评估 |
| 3 | **MM-BrowseComp** | 2026-01 | 社区 | 400 | 多模态网页浏览（图片+文本） |
| 4 | **LiveBrowseComp** | 2026-05 | 社区 | 335 | 90 天内时间敏感问题，反制知识污染 |
| 5 | **K-BrowseComp** | 2026-06 | 社区 | 400 | 韩语网页浏览 Agent 评测 |
| 6 | **DRACO** | 2026-02 | Perplexity AI | 真实用户数据 | 跨 10 领域 + 40 国，准确性/完整性/客观性 |
| 7 | **PhySciBench** | 2026-06 | 社区 | 200 | 物理+化学深度研究，最强仅 33.5% |
| 8 | **MMDR-Bench** | 2026-01 | AIoT-MLSys | 140 | 多模态深度研究，12 指标 3 阶段评估 |
| 9 | **PDR-Bench** | 2026 | OPPO | 50×25 画像 | 个性化深度研究对齐评估 |
| 10 | **InfoSeek** | 2026 | 北京智源 | 50K+ | 首个专为深度研究打造的开源数据集 |
| 11 | **KnowledgeBerg** | 2026 (ACL) | 学术 | 4,800 | 系统性知识覆盖+组合推理，17 语言 |

**2026 年关键趋势**：
- **多模态化**：MM-BrowseComp、MMDR-Bench、PhySciBench 都要求图文联合理解
- **反知识污染**：LiveBrowseComp 使用 90 天内新事实，闭卷得分 <2%
- **个性化**：PDR-Bench 首次将用户画像引入深度研究评测
- **全面性**：DeepSearchQA 关注"答案是否完整列举"而非"是否包含正确答案"
- **语言多样化**：K-BrowseComp（韩语）、KnowledgeBerg（17 语言）

---

## 2. 核心概念：推理 vs 评估的 Prompt 设计差异

在 Deep Research 系统中，**推理 Prompt（Inference Prompt）** 和 **评估 Prompt（Evaluation Prompt）** 是两个完全不同但相互耦合的设计领域：

### 2.1 定义对比

| 维度 | 推理 Prompt (Inference) | 评估 Prompt (Evaluation) |
|------|------------------------|--------------------------|
| **目标** | 驱动 Agent 行动和工具使用 | 评分输出质量 |
| **使用者** | 执行搜索/研究的 Agent 模型 | LLM-as-Judge 评分模型 |
| **结构** | 程序性、分步工作流 | 标准驱动、多轴评分 |
| **复杂度趋势** | **越来越简单**（Bitter Lesson 效应） | **越来越复杂**（多维度标准） |
| **上下文处理** | 管理海量流式工具调用结果（100K+ tokens） | 整体评估长篇报告（多页 PDF） |
| **优化策略** | 遗传式 prompt 进化 + RL 微调 | 人类专家标准校准 + ELO 锦标赛对比 |
| **核心失败模式** | 上下文腐烂、认知窒息、噪声污染 | 隐性需求遗漏、综合质量差、reward hacking |

### 2.2 关键设计差异

```
推理 Prompt 的核心问题                    评估 Prompt 的核心问题
─────────────────────────              ─────────────────────────
"怎么搜索？"                            "搜索得怎么样？"
"用什么工具？"                          "工具使用是否恰当？"
"搜到什么程度算够了？"                   "答案的引用是否可靠？"
"如何组织找到的信息？"                   "推理链是否逻辑严谨？"
"上下文快溢出了，怎么裁剪？"              "有没有遗漏关键子问题？"
```

---

## 3. 全量 Benchmark 详解（含链接）

### 3.1 2024 年：奠基之年

#### GAIA — General AI Assistants Benchmark

| 属性 | 值 |
|------|-----|
| 发布方 | Meta + HuggingFace |
| 发布时间 | 2024-04（2025 年更新为 GAIA2） |
| 样本量 | 466（validation: 165, test: ~300） |
| 语言 | EN |
| **HuggingFace** | [gaia-benchmark/GAIA](https://huggingface.co/datasets/gaia-benchmark/GAIA) |
| **GAIA2** | [meta-agents-research-environments/Gaia2](https://huggingface.co/datasets/meta-agents-research-environments/Gaia2) |
| **Leaderboard** | [huggingface.co/spaces/gaia-benchmark/leaderboard](https://huggingface.co/spaces/gaia-benchmark/leaderboard) |
| **论文** | [arXiv:2311.12983](https://arxiv.org/abs/2311.12983) |
| 评估方式 | 准精确匹配 (Quasi-Exact Match) |

**设计哲学**：逆转传统基准——"对人类简单的任务对 AI 极难"。

**三级难度体系**：

| 等级 | 解题步骤 | 工具数量 | 人类准确率 |
|------|----------|----------|------------|
| Level 1 | <=5 步 | <=1 种工具 | 93.9% |
| Level 2 | 5-10 步 | 多种工具组合 | 91.8% |
| Level 3 | 任意长度 | 任意工具 | 87.3% |

**核心能力要求**：网页浏览、多模态理解、代码执行、文件读取（PDF/Excel/图片/音视频）

**GAIA2 (2025 更新)**：模拟智能手机环境，包含真实 App（Email、Calendar、Shopping、FileSystem），考察复杂多步行为和 App 交互。

#### FRAMES — Factuality, Retrieval, And reasoning Measurement Set

| 属性 | 值 |
|------|-----|
| 发布方 | Google DeepMind + Harvard + Meta |
| 发布时间 | 2024-09 |
| 样本量 | 824 多跳问题（每问需 2-15 篇 Wikipedia） |
| **HuggingFace** | [google/frames-benchmark](https://huggingface.co/datasets/google/frames-benchmark) |
| **论文** | [arXiv:2409.12941](https://arxiv.org/abs/2409.12941) |
| 评估方式 | 三级评分（CORRECT / INCORRECT / NOT_ATTEMPTED） |

**推理类型标注**：多约束(~36%)、数值推理(~20%)、时间推理、表格推理、后处理

**关键发现**：即使给出所有正确答案所在的文章（Oracle），模型上限也仅 ~73%——说明推理/综合仍是瓶颈。

---

### 3.2 2025 年：百花齐放

#### BrowseComp 系列

##### BrowseComp（原始版）

| 属性 | 值 |
|------|-----|
| 发布方 | OpenAI |
| 发布时间 | 2025-04 |
| 样本量 | 1,266 |
| **论文** | [openreview.net: ErnvfmSX0P](https://openreview.net/forum?id=ErnvfmSX0P) |
| 评估方式 | LLM Judge（语义等价） |
| 备注 | 数据集加密，包含 canary string 防污染 |

"网络浏览的编程竞赛"——衡量 Agent 在真实互联网上寻找难以发现关联信息的能力。核心考察搜索持久性、事实核查能力和浏览策略创造性。

**SOTA**（截至 2026.06）：Kimi K2.5 Swarm 72.1% | Tongyi DR 51.4% | GPT-5 38.2% | 人类专家(30min) 87.5%

##### BrowseComp-Plus (ACL 2026 Main)

| 属性 | 值 |
|------|-----|
| 发布方 | Chen et al. |
| 发布时间 | 2025-08 |
| 样本量 | 830，固定 ~100K 人工验证文档语料库 |
| **GitHub** | [texttron/BrowseComp-Plus](https://github.com/texttron/BrowseComp-Plus) |
| **HuggingFace** | [Tevatron/browsecomp-plus-corpus](https://huggingface.co/datasets/Tevatron/browsecomp-plus-corpus) |
| **论文** | [ACL 2026](https://aclanthology.org/2026.acl-long.1023/) |
| 评估方式 | 精确匹配 (Exact Match) |

**核心创新**：离线可复现——使用固定本地语料库，分离 Retriever 和 LLM Agent 贡献。Search-R1 + BM25 仅 3.86%，GPT-5 + Qwen3-Embedding-8B 达 70.1%。

##### BrowseComp-ZH（中文版）

| 属性 | 值 |
|------|-----|
| 发布方 | HKUST |
| 发布时间 | 2025-04 |
| 样本量 | 289 |
| 评估方式 | LLM Judge |
| 特点 | 11 领域，两阶段质量验证 |

##### MM-BrowseComp（多模态版）🆕 2026

| 属性 | 值 |
|------|-----|
| 发布方 | MMBrowseComp 社区 |
| 发布时间 | 2026-01（扩展至 400 问题） |
| 样本量 | 400 |
| **GitHub** | [MMBrowseComp/MM-BrowseComp](https://github.com/MMBrowseComp/MM-BrowseComp) |
| **HuggingFace** | [mmbrowsecomp/MMBrowseComp](https://huggingface.co/datasets/mmbrowsecomp/MMBrowseComp) |
| **论文** | [arXiv:2508.13186](https://arxiv.org/abs/2508.13186) |

加密数据集，需要多模态网页浏览（图片+文本联合理解）。

##### LiveBrowseComp 🆕 2026

| 属性 | 值 |
|------|-----|
| 发布方 | Forival 社区 |
| 发布时间 | 2026-05 |
| 样本量 | 335 |
| **HuggingFace** | [Forival/LiveBrowseComp](https://huggingface.co/datasets/Forival/LiveBrowseComp) |
| **论文** | [arXiv:2605.28721](https://arxiv.org/abs/2605.28721) |

**核心创新**：所有问题依赖 90 天内发布的事实——闭卷得分 <2%，搜索增强后下降 25-40 分 vs 原始 BrowseComp。有效反制知识污染。

##### K-BrowseComp（韩语版）🆕 2026

| 属性 | 值 |
|------|-----|
| 发布方 | prometheus-eval |
| 发布时间 | 2026-06 |
| 样本量 | 400（300 验证 + 100 合成） |
| **GitHub** | [prometheus-eval/K-BrowseComp](https://github.com/prometheus-eval/K-BrowseComp) |
| **HuggingFace** | [prometheus-eval/k-browsecomp](https://huggingface.co/datasets/prometheus-eval/k-browsecomp) |

最强模型仍低于 50% 准确率。

---

#### xbench-DeepSearch

| 属性 | 值 |
|------|-----|
| 发布方 | 红杉中国 (xbench-ai) |
| 发布时间 | 2025-06 |
| 样本量 | 100（加密） |
| 语言 | ZH |
| **GitHub** | [xbench-ai/xbench-evals](https://github.com/xbench-ai/xbench-evals) |
| **HuggingFace** | [xbench/DeepSearch](https://huggingface.co/datasets/xbench/DeepSearch) |
| **新版** | [xbench/DeepSearch-2510](https://huggingface.co/datasets/xbench/DeepSearch-2510) |
| **论文** | [arXiv:2506.13651](https://arxiv.org/abs/2506.13651) |
| 评估方式 | LLM Judge |

"想谜底，出谜面"——先确定可验证事实，逆向设计多约束问题。平均正确率仅~32%，高区分度。

---

#### WideSearch & FinSearchComp

| 属性 | WideSearch | FinSearchComp |
|------|-----------|---------------|
| 发布方 | Seed (字节跳动) | Seed (字节跳动) |
| 发布时间 | 2025-08 | 2025-09 |
| 样本量 | 200 | 635 |
| 语言 | EN + ZH | EN + ZH |
| 特点 | 18 领域，答案为事实集 | 金融领域，时间敏感分类 |

---

#### WebWalkerQA

| 属性 | 值 |
|------|-----|
| 发布时间 | 2025 |
| 样本量 | 680 |
| 语言 | EN |
| 核心能力 | 网页遍历与交互，行动型问题 |
| Tongyi DR 得分 | 62.1% |

---

#### HLE — Humanity's Last Exam

| 属性 | 值 |
|------|-----|
| 发布时间 | 2025 |
| 样本量 | 2,158 |
| 语言 | EN |
| 评估方式 | LLM Judge（结构化 JSON：reasoning + confidence） |
| Tongyi DR 得分 | 32.9% |

专家级极难推理问题集，需要跨领域专业知识。

---

#### ReportBench（ByteDance）

| 属性 | 值 |
|------|-----|
| 发布方 | ByteDance |
| 发布时间 | 2025-08 |
| **GitHub** | [ByteDance-BandAI/ReportBench](https://github.com/ByteDance-BandAI/ReportBench) |
| **论文** | [arXiv:2508.15804](https://arxiv.org/abs/2508.15804) |
| 评估方式 | 双路径：引用一致性 + 事实正确性 |

使用 arXiv 综述论文作为黄金标准，反向 Prompt 工程提取领域 prompt。完整自动化 pipeline（Apache 2.0 开源）。

---

#### DeepConsult（You.com）

| 属性 | 值 |
|------|-----|
| 发布方 | You.com |
| 发布时间 | 2025-05 |
| **GitHub** | [youdotcom-oss/ydc-deep-research-evals](https://github.com/youdotcom-oss/ydc-deep-research-evals) |
| 评估方式 | 成对比较 (Pairwise Comparison) |
| 维度 | 指令遵循、全面性、完整性、写作质量 |

MIT 开源，支持编程调用 `DeepResearchPairwiseMetric`。

---

### 3.3 2026 年：深度与广度的新高度

#### DeepSearchQA 🏆 年度最重要新 Benchmark

| 属性 | 值 |
|------|-----|
| 发布方 | **Google DeepMind** |
| 发布时间 | 2026-01 |
| 样本量 | **900 prompts**，17 领域 |
| **HuggingFace** | [google/deepsearchqa](https://huggingface.co/datasets/google/deepsearchqa) |
| **论文** | [arXiv:2601.20975](https://arxiv.org/abs/2601.20975) |
| **技术报告 PDF** | [storage.googleapis.com/deepmind-media/DeepSearchQA](https://storage.googleapis.com/deepmind-media/DeepSearchQA/DeepSearchQA_benchmark_paper.pdf) |
| **Kaggle Leaderboard** | [kaggle.com/benchmarks/google/dsqa](https://www.kaggle.com/benchmarks/google/dsqa) |
| License | Apache 2.0 |
| 答案类型 | 35% Single Answer / 65% Set Answer |

**核心创新**：弥合 Deep Research Agent 的"全面性鸿沟"（Comprehensiveness Gap）。传统 benchmark 只评估"是否答对"，DeepSearchQA 评估"是否答全"。

**三大能力**：
1. 跨源碎片信息系统性整理
2. 去重和实体消歧
3. 开放搜索空间中的停止条件推理

**SOTA**（截至 2026）：Google Deep Research Max (Gemini 3.1 Pro) **93.3%**，4 个月前仅 66.1%。

---

#### DeepResearch Bench II (DRB2) 🆕

| 属性 | 值 |
|------|-----|
| 发布时间 | 2026-02 |
| 样本量 | **132 份专家报告 → 9,430 层级化 rubrics** |
| **GitHub** | [imlrz/DeepResearch-Bench-II](https://github.com/imlrz/DeepResearch-Bench-II) |
| **论文** | [arXiv:2601.08536](https://arxiv.org/abs/2601.08536) |

**核心创新**：将专家撰写的报告分解为层级化评估 rubrics，覆盖呈现质量(Presentation)、分析深度(Analysis)、证据质量(Evidence)三大维度。用于诊断 Deep Research 系统与人类专家的差距。

---

#### DRACO

| 属性 | 值 |
|------|-----|
| 发布方 | **Perplexity AI** |
| 发布时间 | 2026-02 |
| 样本量 | 基于真实 Perplexity Deep Research 使用数据 |
| **HuggingFace** | [perplexity-ai/draco](https://huggingface.co/datasets/perplexity-ai/draco) |
| **论文** | [arXiv:2602.11685](https://arxiv.org/abs/2602.11685) |
| 覆盖范围 | 10 领域 + 40 个国家 |

跨领域 benchmark，评估准确性(Accuracy)、完整性(Completeness)、客观性(Objectivity)和引用质量(Citation Quality)。

---

#### PhySciBench

| 属性 | 值 |
|------|-----|
| 发布时间 | 2026-06 |
| 样本量 | 200 物理+化学专家策划问题 |
| **GitHub** | [yigengjiang/physci-deepresearch](https://github.com/yigengjiang/physci-deepresearch) |
| **HuggingFace** | [littletreee/PhySciBench](https://huggingface.co/datasets/littletreee/PhySciBench) |
| **论文** | [arXiv:2606.18648](https://arxiv.org/abs/2606.18648) |

6 种任务类型：多模态 QA、实验设计、代码生成等。**最强 baseline (Gemini Deep Research) 仅 33.5%**——物理科学深度研究仍有巨大空间。

---

#### MMDR-Bench（多模态深度研究）

| 属性 | 值 |
|------|-----|
| 发布方 | AIoT-MLSys-Lab |
| 发布时间 | 2026-01 |
| 样本量 | 140 专家策划多模态任务，19 领域 |
| **GitHub** | [AIoT-MLSys-Lab/MMDeepResearch-Bench](https://github.com/AIoT-MLSys-Lab/MMDeepResearch-Bench) |
| **论文** | [arXiv:2601.12346](https://arxiv.org/abs/2601.12346) |

3 阶段 12 指标评估 pipeline：声明-证据对齐、视觉证据保真度、基于图像的推理。

---

#### PDR-Bench（个性化深度研究）

| 属性 | 值 |
|------|-----|
| 发布方 | OPPO PersonalAI |
| 发布时间 | 2026 (ICLR 2026) |
| 样本量 | 50 任务 × 25 真实用户画像 |
| **GitHub** | [OPPO-PersonalAI/PersonalizedDeepResearchBench](https://github.com/OPPO-PersonalAI/PersonalizedDeepResearchBench) |
| **HuggingFace** | [PersonalAILab/PersonalizedDeepResearchBench](https://huggingface.co/datasets/PersonalAILab/PersonalizedDeepResearchBench) |
| **论文** | [arXiv:2509.25106](https://arxiv.org/abs/2509.25106) |

PQR 框架：个性化(Personalization)、质量(Quality)、可靠性(Reliability)。

---

#### InfoSeek 

| 属性 | 值 |
|------|-----|
| 发布方 | 北京智源 (BAAI) |
| 发布时间 | 2026 |
| 样本量 | **50K+** 高质量多步推理样本 |
| **GitHub** | [VectorSpaceLab/InfoSeek](https://github.com/VectorSpaceLab/InfoSeek) |
| **HuggingFace** | [Lk123/InfoSeek](https://huggingface.co/datasets/Lk123/InfoSeek) |
| **论文** | [arXiv:2509.00375](https://arxiv.org/abs/2509.00375) |

**首个专为 Deep Research 打造的开源数据集**。3B 模型在此数据集上训练后可匹配 Gemini/Sonnet 4.0 性能。

---

#### DEEPSYNTH 

| 属性 | 值 |
|------|-----|
| 发布方 | 华为诺亚方舟实验室(英国)和伦敦帝国学院|
| 发布时间 | 2026 |
| 样本量 | 120 tasks |
| **GitHub** | [agentdeepsynthesis/deepsynth-bench](https://github.com/agentdeepsynthesis/deepsynth-bench) |

**五种衡量指标**：F1 / Precision / Recall / Exact Match (EM) / LLM as Judge

---

#### DeepResearch Bench

| 属性 | 值 |
|------|-----|
| 发布方 | 中科大|
| 发布时间 | 2026 |
| 样本量 | 100 tasks |
| **GitHub** | [deep_research_bench](https://github.com/Ayanami0730/deep_research_bench) |

**衡量指标**：PAR、OPC、FAP、FAS、LLM as Judge
**两个框架**：RACE (Reference-based Adaptive Criteria-driven Evaluation)、FACT (Framework for Factual Abundance and Citation Trustworthiness)
'{"id": 1, "topic": "Finance & Business", "language": "zh", "prompt": "收集整理目前中国9阶层实际收入和财务状况，特别研究得出中国的中产有哪些特点，实际中产人数，财力等等"}
{"id": 2, "topic": "Finance & Business", "language": "zh", "prompt": "收集整理目前国际综合实力前十的保险公司的相关资料，横向比较各公司的融资情况、信誉度、过往五年的增长幅度、实际分红、未来在中国发展潜力等维度，并为我评估出最有可能在未来资产排名靠前的2-3家公司"}'

---

#### KnowledgeBerg 
| 属性 | 值 |
|------|-----|
| 发布时间 | 2026 (ACL 2026 Findings) |
| 样本量 | 4,800 多选问题，10 领域，17 语言 |
| **HuggingFace** | [2npc/KnowledgeBerg](https://huggingface.co/datasets/2npc/KnowledgeBerg) |
| **论文** | [ACL 2026 Findings](https://aclanthology.org/2026.findings-acl.548/) |

测试系统性知识覆盖和基于集合的组合推理能力。

---

#### 配套工具

| 工具 | 链接 | 说明 |
|------|------|------|
| **Perplexity search_evals** | [perplexityai/search_evals](https://github.com/perplexityai/search_evals) | 开箱即用的搜索 API 评估框架 |
| **LDR Benchmarks** | [LearningCircuit/ldr-benchmarks](https://github.com/LearningCircuit/ldr-benchmarks) | 社区驱动的 Deep Research 排行榜 |
| **OpenResearcher** | [TIGER-AI-Lab/OpenResearcher](https://github.com/TIGER-AI-Lab/OpenResearcher) | 全开源 30B Deep Research 模型 + 评测日志 |
| **Web-Bench (统一格式)** | [OpenResearcher/web-bench](https://huggingface.co/datasets/OpenResearcher/web-bench) | HuggingFace 统一 benchmark 格式项目 |
| **EvalScope** | [modelscope/evalscope](https://github.com/modelscope/evalscope) | ModelScope 评测框架，已集成 FRAMES |

---

### 3.4 全量对比总表

| Benchmark | 年份 | 发布方 | 样本 | 语言 | 评分方式 | GitHub | HuggingFace |
|-----------|------|--------|------|------|----------|--------|-------------|
| GAIA | 2024 | Meta+HF | 466 | EN | EM | — | [gaia-benchmark/GAIA](https://huggingface.co/datasets/gaia-benchmark/GAIA) |
| FRAMES | 2024 | Google | 824 | EN | 三级 | — | [google/frames-benchmark](https://huggingface.co/datasets/google/frames-benchmark) |
| BrowseComp | 2025 | OpenAI | 1,266 | EN | LLM Judge | — | 加密 |
| BrowseComp-ZH | 2025 | HKUST | 289 | ZH | LLM Judge | — | — |
| BrowseComp-Plus | 2025 | 社区 | 830 | EN | EM | [texttron/BrowseComp-Plus](https://github.com/texttron/BrowseComp-Plus) | [Tevatron/browsecomp-plus-corpus](https://huggingface.co/datasets/Tevatron/browsecomp-plus-corpus) |
| xbench-DeepSearch | 2025 | 红杉中国 | 100 | ZH | LLM Judge | [xbench-ai/xbench-evals](https://github.com/xbench-ai/xbench-evals) | [xbench/DeepSearch](https://huggingface.co/datasets/xbench/DeepSearch) |
| WideSearch | 2025 | Seed | 200 | EN+ZH | 事实集 | — | — |
| FinSearchComp | 2025 | Seed | 635 | EN+ZH | 事实匹配 | — | — |
| WebWalkerQA | 2025 | — | 680 | EN | — | — | — |
| HLE | 2025 | — | 2,158 | EN | LLM Judge | — | — |
| ReportBench | 2025 | ByteDance | 动态 | EN | Rubric | [ByteDance-BandAI/ReportBench](https://github.com/ByteDance-BandAI/ReportBench) | — |
| DeepConsult | 2025 | You.com | 动态 | EN | 成对比较 | [youdotcom-oss/ydc-deep-research-evals](https://github.com/youdotcom-oss/ydc-deep-research-evals) | — |
| **DeepSearchQA** | **2026** | **Google DeepMind** | **900** | **EN** | **LLM Judge** | — | [google/deepsearchqa](https://huggingface.co/datasets/google/deepsearchqa) |
| **DRB2** | **2026** | **社区** | **132报告** | **EN** | **Rubric** | [imlrz/DeepResearch-Bench-II](https://github.com/imlrz/DeepResearch-Bench-II) | — |
| **MM-BrowseComp** | **2026** | **社区** | **400** | **EN** | **LLM Judge** | [MMBrowseComp/MM-BrowseComp](https://github.com/MMBrowseComp/MM-BrowseComp) | [mmbrowsecomp/MMBrowseComp](https://huggingface.co/datasets/mmbrowsecomp/MMBrowseComp) |
| **LiveBrowseComp** | **2026** | **社区** | **335** | **EN** | **LLM Judge** | — | [Forival/LiveBrowseComp](https://huggingface.co/datasets/Forival/LiveBrowseComp) |
| **K-BrowseComp** | **2026** | **prometheus-eval** | **400** | **KO** | **LLM Judge** | [prometheus-eval/K-BrowseComp](https://github.com/prometheus-eval/K-BrowseComp) | [prometheus-eval/k-browsecomp](https://huggingface.co/datasets/prometheus-eval/k-browsecomp) |
| **DRACO** | **2026** | **Perplexity** | **真实数据** | **EN** | **Rubric** | — | [perplexity-ai/draco](https://huggingface.co/datasets/perplexity-ai/draco) |
| **PhySciBench** | **2026** | **社区** | **200** | **EN** | **LLM Judge** | [yigengjiang/physci-deepresearch](https://github.com/yigengjiang/physci-deepresearch) | [littletreee/PhySciBench](https://huggingface.co/datasets/littletreee/PhySciBench) |
| **MMDR-Bench** | **2026** | **AIoT-MLSys** | **140** | **EN** | **12指标** | [AIoT-MLSys-Lab/MMDeepResearch-Bench](https://github.com/AIoT-MLSys-Lab/MMDeepResearch-Bench) | — |
| **PDR-Bench** | **2026** | **OPPO** | **50×25** | **EN** | **PQR** | [OPPO-PersonalAI/PersonalizedDeepResearchBench](https://github.com/OPPO-PersonalAI/PersonalizedDeepResearchBench) | [PersonalAILab/PersonalizedDeepResearchBench](https://huggingface.co/datasets/PersonalAILab/PersonalizedDeepResearchBench) |
| **InfoSeek** | **2026** | **BAAI** | **50K+** | **EN** | **EM** | [VectorSpaceLab/InfoSeek](https://github.com/VectorSpaceLab/InfoSeek) | [Lk123/InfoSeek](https://huggingface.co/datasets/Lk123/InfoSeek) |
| **KnowledgeBerg** | **2026** | **学术** | **4,800** | **17语言** | **MC** | — | [2npc/KnowledgeBerg](https://huggingface.co/datasets/2npc/KnowledgeBerg) |

---

## 4. Alibaba-NLP/DeepResearch 深度分析

### 4.1 项目概览

| 属性 | 值 |
|------|-----|
| **GitHub** | [Alibaba-NLP/DeepResearch](https://github.com/Alibaba-NLP/DeepResearch) |
| **模型** | [Alibaba-NLP/Tongyi-DeepResearch-30B-A3B](https://huggingface.co/Alibaba-NLP/Tongyi-DeepResearch-30B-A3B) |
| **技术报告** | [arXiv:2510.24701](https://arxiv.org/abs/2510.24701) |
| 模型规模 | 30.5B 总参数 / 3.3B 激活 (MoE) |
| 训练流程 | 自动合成数据 -> Agentic 持续预训练 -> SFT -> GRPO |
| 得分 | BrowseComp 51.4%, FRAMES 90.6%, HLE 32.9%, WebWalkerQA 62.1% |

### 4.2 仓库结构（评测相关）

```
DeepResearch/
├── evaluation/                          # 评测核心目录
│   ├── prompt.py                        # ★ Judge Prompt（GAIA/QA/Confidence）
│   ├── evaluate_deepsearch_official.py  # DeepSearch 评测脚本
│   ├── evaluate_hle_official.py         # HLE 评测脚本
│   └── eval_data/                       # 评测数据
├── WebAgent/
│   └── WebResummer/
│       └── src/
│           ├── prompt.py                # ★ Agent 推理 Prompt（System+工具定义）
│           └── judge_prompt.py          # ★ BrowseComp Judge Prompt
├── inference/
│   └── react_agent.py                   # ★ ReAct Agent 实现
└── src/
    └── prompts.py                       # Explorer/Critic Agent Prompt
```

### 4.3 推理 Prompt（Inference）

#### System Prompt

```python
# 身份: "Web Information Seeking Master"
# 原则:
# 1. Persistent Actions — 深度交互，不放弃
# 2. Repeated Verification — 跨源交叉验证
# 3. Attention to Detail — 当前、相关、可信来源
```

#### 工具定义（嵌入 XML）

| 工具 | 功能 | 关键设计 |
|------|------|----------|
| `search` | 批量搜索 | 数组支持批量操作 |
| `visit` | URL 内容获取 + goal 参数 | goal 引导内容提取精度 |
| `PythonInterpreter` | Python 代码执行 | `<code>` 标签包裹 |
| `google_scholar` | 学术检索 | 查询数组 |
| `parse_file` | 本地文件解析 | PDF/DOCX/CSV |

#### ReAct 循环

```
Think -> Act (<tool_call> JSON) -> Observe (<tool_response>) -> Loop -> <answer>
```

#### EXTRACTOR_PROMPT 三步抽取

```json
{"rational": "...", "evidence": "...", "summary": "..."}
```

### 4.4 评估 Prompt（Evaluation）

| Judge Prompt | 用途 | 输出格式 | 示例校准 |
|-------------|------|----------|----------|
| `JUDGE_PROMPT_GAIA` | GAIA 等价判断 | Correct/Incorrect | 无 |
| `JUDGE_PROMPT_QA` | QA 三级评分 | CORRECT/INCORRECT/NOT_ATTEMPTED | Obama 孩子例子 |
| `JUDGE_PROMPT_CONFIDENCE` | 置信度评估 | JSON {correct, reasoning, confidence} | 无 |
| `JUDGE_PROMPT_BC_EN` | BrowseComp 英文 | CORRECT/INCORRECT + 推理 | 无 |
| `JUDGE_PROMPT_BC_ZH` | BrowseComp 中文 | CORRECT/INCORRECT + 推理 | 无 |
| `JUDGE_PROMPT_HLE` | HLE 高难度 | JSON {is_correct, reasoning, confidence, requires_expert_review} | 无 |

---

## 5. 评估方法论详解

### 5.1 三大评分范式

| 方法 | 适用场景 | 优点 | 缺点 |
|------|----------|------|------|
| **精确匹配 (EM)** | GAIA, BrowseComp-Plus | 客观、可复现 | 对表述差异过于严格 |
| **LLM-as-Judge** | BrowseComp, DeepSearchQA | 灵活语义等价 | 依赖 Judge 模型质量 |
| **多级/多轴评分** | FRAMES, DRB2, DRACO | 细粒度区分 | 边界定义复杂 |

### 5.2 评估陷阱

1. **数据污染**：LLM 预训练数据可能已包含答案 -> LiveBrowseComp 的 90 天时间窗口
2. **答案表述多样性**：同一语义多种表达 -> LLM Judge + 结构化答案
3. **过程作弊**：生成虚假引用 -> 验证 URL 真实性、保存网页快照
4. **全面性盲区**：只看正确与否，不看完整与否 -> DeepSearchQA 的集合答案评估

---

## 6. Prompt 设计对比：推理 Prompt vs 评估 Prompt

```
┌─────────────────────────────────────────────────────────────┐
│                     推理 Prompt 结构                         │
├─────────────────────────────────────────────────────────────┤
│ 1. 身份声明    -> "你是 Web Information Seeking Master"       │
│ 2. 行为原则    -> 持续性、验证性、细节关注                     │
│ 3. 工具定义    -> search/visit/Python/scholar 的 JSON Schema  │
│ 4. 输出格式    -> <think>/<tool_call>/<answer> XML 标签       │
│ 5. 上下文管理  -> 摘要触发、裁剪策略、降级方案                 │
│ 6. 停止条件    -> "\n<tool_response>" 停止序列                │
└─────────────────────────────────────────────────────────────┘
                            vs
┌─────────────────────────────────────────────────────────────┐
│                     评估 Prompt 结构                         │
├─────────────────────────────────────────────────────────────┤
│ 1. 角色定义    -> "你是评估助手"                              │
│ 2. 输入数据    -> {question} + {correct_answer} + {response}  │
│ 3. 评分标准    -> Correct/Incorrect or CORRECT/INCORRECT/NA   │
│ 4. Few-shot   -> 具体示例校准（如 Obama 孩子例子）           │
│ 5. 输出约束    -> "只输出一个词"或 JSON Schema                │
└─────────────────────────────────────────────────────────────┘
```

### 演进趋势

```
推理 Prompt：越来越简单
  2024 H1: 高度结构化，预定义章节
  2024 H2: 工具调用驱动，移除模板
  2025:    纯 ReAct，最小结构
  2026:    RL 取代手工（端到端训练）

评估 Prompt：越来越复杂
  2024:    简单 Correct/Incorrect
  2025:    三级评分 + Few-shot + 多轴 Rubric
  2026:    层级化 Rubric (DRB2) + 集合答案 (DeepSearchQA)
            + 多模态证据 (MMDR) + 个性化 (PDR)
```

### 耦合关系

| 评估维度 | 推理 Prompt 必须响应 |
|----------|---------------------|
| 引用准确性 | Agent 保存来源元数据 |
| 隐性需求遵循 | Agent 花步骤识别未声明假设 |
| 全面性 (DeepSearchQA) | Agent 显式追踪已覆盖子主题 |
| 个性化 (PDR-Bench) | Agent 考虑用户背景和偏好 |

---

## 7. 关键发现与最佳实践

### 7.1 Prompt 工程

1. **工具优先**：除非问题极其简单，否则先调用工具
2. **批量操作**：search/visit 支持数组，减少往返
3. **Goal-conditioned 抽取**：visit 的 goal 参数大幅提升信噪比
4. **结构化输出**：JSON Schema + XML 标签双重约束
5. **Stop Sequences**：防止 LLM 幻觉生成工具响应
6. **降级策略**：Token 超限时注入强制回答 prompt

### 7.2 评估设计

1. **Few-shot 校准**：用具体示例消除 Judge 歧义
2. **结构化输出**：JSON 格式可编程解析
3. **三级 > 二级**：区分"答错"和"没尝试"
4. **位置偏差缓解**：成对比较翻转顺序取平均
5. **集合答案评估**：DeepSearchQA 的全面性 scoring
6. **多 Judge 投票**：BrowseComp-ZH 的多 Agent 交叉检验

### 7.3 可复现性

- GAIA ICC = 0.304-0.774，单次运行不可靠，需 >=32 次试验
- BrowseComp-Plus 固定语料库解决在线不可复现
- LiveBrowseComp 时间窗口反制知识污染

---

## 8. 脚本工具说明

| 脚本 | 功能 |
|------|------|
| [`eval_framework_overview.py`](scripts/eval_framework_overview.py) | 20+ 评测框架结构化概览，含 GitHub/HF 链接 |
| [`extract_prompts.py`](scripts/extract_prompts.py) | Prompt 模板提取与对比（推理/评估分类） |
| [`evaluation_methods.py`](scripts/evaluation_methods.py) | 6 种评估方法可运行演示 |
| [`prompt_diff_analyzer.py`](scripts/prompt_diff_analyzer.py) | 推理 vs 评估 Prompt 差异深度分析 |

### 快速开始

```bash
# 查看全量评测框架（含链接）
python scripts/eval_framework_overview.py --format table

# 仅看 2026 年新 benchmark
python scripts/eval_framework_overview.py --year 2026

# 提取和对比 Prompt
python scripts/extract_prompts.py --analyze

# 评估方法演示
python scripts/evaluation_methods.py --method all

# Prompt 差异分析
python scripts/prompt_diff_analyzer.py --evolution
```

---

## 参考资料

**2026 年核心论文：**
- [DeepSearchQA (Google DeepMind)](https://arxiv.org/abs/2601.20975) — 全面性鸿沟
- [DRB2 (DeepResearch Bench II)](https://arxiv.org/abs/2601.08536) — 层级化 Rubric 诊断
- [DRACO (Perplexity AI)](https://arxiv.org/abs/2602.11685) — 跨领域跨国家
- [PhySciBench](https://arxiv.org/abs/2606.18648) — 物理科学 Deep Research
- [MMDR-Bench](https://arxiv.org/abs/2601.12346) — 多模态深度研究
- [LiveBrowseComp](https://arxiv.org/abs/2605.28721) — 反知识污染
- [PDR-Bench](https://arxiv.org/abs/2509.25106) — 个性化深度研究 (ICLR 2026)
- [InfoSeek (BAAI)](https://arxiv.org/abs/2509.00375) — 首个开源 Deep Research 数据集
- [KnowledgeBerg (ACL 2026)](https://aclanthology.org/2026.findings-acl.548/) — 17 语言知识覆盖

**关键仓库：**
- [Alibaba-NLP/DeepResearch](https://github.com/Alibaba-NLP/DeepResearch)
- [perplexityai/search_evals](https://github.com/perplexityai/search_evals)
- [LearningCircuit/ldr-benchmarks](https://github.com/LearningCircuit/ldr-benchmarks)
- [TIGER-AI-Lab/OpenResearcher](https://github.com/TIGER-AI-Lab/OpenResearcher)
