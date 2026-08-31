---
name: gin-question
description: |
  针对任意主题，从互联网全量检索真实用户提过的真问题，输出结构化问题清单。
  当用户说"去网上搜一下XX的问题"、"XX主题用户都在问什么"、"全量找XX的真问题"、"真实用户关于XX的疑问"、"这个领域有哪些真问题"时触发。
  也适用于上游编排器需要为某个主题生成问题清单的场景。
  不适用于：直接回答某个问题、写教程/长文、纯创意发散、已有清晰问题直接执行。
---

# gin-question：全量检索真问题

针对任意主题，从互联网全量检索真实用户提过的真问题，输出结构化问题清单。

核心原则：**问题必须来自真实网络检索，不是 AI 生成。**

---

## 适用场景

- "去网上搜一下减脂相关的问题"
- "真实用户关于新能源汽车都在问什么"
- "全量找一棵树的真问题"
- "这个领域有哪些真问题"
- 上游编排器需要为某个主题生成问题清单

## 不适用场景

- 直接回答某个问题 → 走答案生成类 skill
- 写教程/长文 → 走写作类 skill
- 已有清晰问题直接执行 → 直接做
- 纯创意发散 → 走 brainstorming 类 skill

---

## 输入

```bash
gin-question --topic "主题" [--output-dir ./output]
```

| 参数 | 必填 | 说明 |
|---|---|---|
| `--topic` | 是 | 任意主题字符串，任意粒度 |
| `--output-dir` | 否 | 输出目录，默认当前目录 |

## 输出

| 文件 | 说明 |
|---|---|
| `problem_list.json` | 结构化问题清单，供下游 skill 消费 |
| `problem_list.md` | 人类可读的问题清单 |
| `audit_report.json` | 检索审计报告 |

---

## 执行流程

### Progress

```markdown
Progress:
- [ ] Step 1 种子词扩展 `[自动]`
- [ ] Step 2 并行 4 视角 Agent 检索 `[自动]`
- [ ] Step 3 统一抽取 Agent 提取问题 `[自动]`
- [ ] Step 4 精确 + 语义去重 `[自动]`
- [ ] Step 5 QM1-QM3 过滤 `[自动]`
- [ ] Step 6 来源分级 + 频次门槛 `[自动]`
- [ ] Step 7 16 格子覆盖度检查 `[自动]`
- [ ] Step 8 信息充分性自检 + 输出 `[自动]`
```

### Step 1：种子词扩展

基于 WebSearch 搜索 `{topic} 同义词 / {topic} 别称 / {topic} 行业术语`，从搜索结果中提取 3-10 个扩展词。

**约束**：扩展词必须出现在搜索结果中，不能自由发挥。

### Step 2：并行 4 视角 Agent 检索

每个 Agent 使用固定检索词模板，基于扩展词表并行搜索。

| Agent | 视角 | 覆盖格子 |
|---|---|---|
| 基础视角 | 5W2H | What / Why / Who / When / Where / How / How much |
| 旅程视角 | 用户时间轴 | 认知期 / 准备期 / 执行期 / 瓶颈期 / 维持期 |
| 人群场景视角 | 人群/场景差异 | 人群差异 / 场景差异 |
| 争议时效视角 | 争议/时效 | 争议 / 时效 |

**Agent 失败处理**：失败 Agent 先重试 1 次，再用更宽泛检索词补搜，最多 3 次。仍失败则标记该视角"暂缺"。

### Step 3：统一抽取 Agent

从所有 Agent 返回的网页内容中抽取真实用户提出的求知性问题。

**两步法**：
1. 正则初筛：匹配疑问句式
2. LLM 二筛：判断是否为真实用户的求知性问题

**剔除**：广告、修辞反问、命令句、AI 倒推痕迹、过度抽象、严重残缺。

### Step 4：精确 + 语义去重

1. 精确去重：文本归一化后字符串相同
2. 语义去重：相似度 ≥ 0.85 视为重复
3. 子集去重：短问题是长问题的子集则合并

保留来源更多或限定更具体的问题。

### Step 5：QM1-QM3 过滤

应用 `references/qm-rules.md` 中的规则。

**QM1 真问题**：来源真实、疑问句式、可客观回答。  
**QM2 有效问题**：有真实来源、认知缺口、客观应答域、非简单常识。  
**QM3 假问题**：
- A 虚构类：AI 倒推伪问题
- B 修辞类：反问、情绪宣泄、命令
- C 无真实意图类：过度抽象、严重残缺
- D 不可证伪类：主观价值观、未来预测
- E 补充类：残缺重复、无效二元

### Step 6：来源分级 + 频次门槛

| 级别 | 门槛 | 入选规则 |
|---|---|---|
| 一手源 | ≥1 个 | 官方、学术、标准、政府 |
| 二手源 | ≥2 个 | 权威媒体、行业报告、深度原创 |
| 三手源 | ≥3 个 | 论坛、社交媒体、问答社区 |

任一满足 → 主清单；都不满足 → 待验证清单。

### Step 7：16 格子覆盖度检查

检查 16 个格子（基础 7 + 旅程 5 + 人群场景 2 + 争议时效 2）是否全部 ≥1。

0 覆盖 → 针对缺失格子补搜（不计入新增率统计）。

### Step 8：信息充分性自检 + 输出

```
新增率 = 本轮新增问题数 / 上轮总问题数
连续 3 轮新增率 < 50% → 停止
```

取消硬时间限制。

输出 `problem_list.json` + `problem_list.md` + `audit_report.json`。

---

## 4 视角检索词模板

### 基础视角

```yaml
What: "{扩展词} 是什么 / 定义 / 什么意思"
Why: "{扩展词} 为什么 / 原理 / 原因"
Who: "{扩展词} 适合谁 / 人群 / 谁需要"
When: "{扩展词} 什么时候 / 多久 / 最佳时机"
Where: "{扩展词} 哪里 / 场景 / 在什么地方"
How: "{扩展词} 怎么做 / 步骤 / 方法"
How much: "{扩展词} 多少 / 标准 / 剂量 / 成本"
```

### 旅程视角

```yaml
认知期: "{扩展词} 新手 入门 是什么 值得吗"
准备期: "{扩展词} 准备 需要 第一次 怎么开始"
执行期: "{扩展词} 怎么做 方法 步骤 频率"
瓶颈期: "{扩展词} 平台期 出错 受伤 怎么办 没效果"
维持期: "{扩展词} 维持 保持 不反弹 进阶"
```

### 人群场景视角

```yaml
人群差异:
  - "{人群} {扩展词} 注意"
  - "{人群} {扩展词} 禁忌"
  - "{人群} {扩展词} 区别"
  人群池: [女性, 男性, 青少年, 老人, 孕妇, 哺乳期, 糖尿病, 高血压, 甲状腺, 高血脂, 运动员, 健身爱好者, 体力劳动者]

场景差异:
  - "{扩展词} 出差 旅行 怎么办"
  - "{扩展词} 经期 生理期 怎么办"
  - "{扩展词} 怀孕 哺乳 怎么办"
  - "{扩展词} 感冒 生病 怎么办"
```

### 争议时效视角

```yaml
争议:
  - "{扩展词} 争议"
  - "{扩展词} 哪个好 对比"
  - "{扩展词} 智商税"
  - "{扩展词} 伪科学"
  - "{扩展词} 反常识"
  - "{扩展词} 骗局"

时效:
  - "{扩展词} 历史 起源"
  - "{扩展词} 演变 发展"
  - "{扩展词} 2025 最新"
  - "{扩展词} 未来 趋势"
  - "{扩展词} 新技术 新方法"
```

---

## 输出 Schema

### problem_list.json

```json
{
  "topic": "减脂",
  "generated_at": "2026-08-31T12:34:56Z",
  "exit_reason": "saturated",
  "retrieval_rounds": 3,
  "problems": [
    {
      "id": "P001",
      "text": "上班族减脂怎么吃？",
      "original": "上班族减脂期间应该怎么吃？",
      "retrieval_perspective": "人群场景",
      "sub_dimension": "场景差异",
      "sources": [
        {"url": "https://...", "type": "secondary", "frequency": 5}
      ],
      "total_frequency": 5,
      "source_count": 1,
      "duplicates": ["减脂怎么吃？"],
      "status": "confirmed"
    }
  ],
  "pending_validation": []
}
```

### audit_report.json

```json
{
  "topic": "减脂",
  "generated_at": "2026-08-31T12:34:56Z",
  "search_terms_total": 24,
  "candidates_total": 156,
  "duplicates_merged": 34,
  "qm1_rejected": 0,
  "qm2_rejected": 12,
  "qm3_rejected": {"A": 0, "B": 5, "C": 8, "D": 10, "E": 5},
  "frequency_rejected": 19,
  "perspective_coverage": {
    "基础": {"What": 3, "Why": 2, "Who": 2, "When": 1, "Where": 2, "How": 4, "How much": 2},
    "旅程": {"认知期": 2, "准备期": 1, "执行期": 4, "瓶颈期": 3, "维持期": 2},
    "人群场景": {"人群差异": 4, "场景差异": 3},
    "争议时效": {"争议": 2, "时效": 1}
  },
  "agent_failures": [],
  "empty_perspectives": []
}
```

---

## 异常处理

| 场景 | 退出码 | 处理 |
|---|---|---|
| topic 为空 | 2 | 返回错误提示 |
| 全部 Agent 失败 | 1 | 返回空清单 + audit |
| 部分 Agent 失败且补搜失败 | 0 | 返回结果，audit 标记暂缺 |
| 主题无网络讨论 | 1 | 返回空清单 + audit |
| 覆盖度未全 | 0 | 针对缺失格子补搜 |

---

## 边界 / 不做事项

- 不回答问题
- 不生成教程/长文
- 不做主观判断
- 不替代下游研究 skill
- 不设置敏感词拦截（只写边界声明）
- 不做 AI 味检测（只保留输出禁区作为规则约束）
- 不做类型分布检查
- 不设置硬时间上限

---

## 参考资料

按需读取：

- `references/objective-rules.md` — 客观化规则手册（QM 规则、来源分级域名表、疑问句正则）
- `references/search-templates.md` — 4 视角检索词模板
- `references/output-schema.json` — 完整输出 schema

---

## 文件结构

```
gin-question/
├── SKILL.md
├── references/
│   ├── objective-rules.md
│   ├── search-templates.md
│   └── output-schema.json
├── scripts/
│   ├── pipeline.py
│   ├── seed_expander.py
│   ├── parallel_agents.py
│   ├── retry_agent.py
│   ├── question_extractor.py
│   ├── dedupe_questions.py
│   ├── judge_questions.py
│   ├── source_grader.py
│   ├── coverage_matrix.py
│   ├── saturation_checker.py
│   └── output_renderer.py
├── tests/
│   ├── test_pipeline.py
│   ├── test_judge_questions.py
│   └── test_source_grader.py
└── evals/
    └── evals.json
```
