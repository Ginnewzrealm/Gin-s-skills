# 结构化问题清单字段定义

> 第七步输出格式。每条问题必须包含全部字段。

## 字段列表

| 字段 | 类型 | 说明 |
|------|------|------|
| question_id | string | 唯一标识符，Q-001 / Q-002 ... |
| text | string | 澄清后的精准表述 |
| dimension | string | 映射到第一步的维度标签 |
| depth | string | L1 / L2 / L3 知识深度层 |
| depth_label | string | 深度层人类可读标签 |
| primary_type | string | 知识型 / 方法型 / 判断型 |
| secondary_type | string \| null | 比较型 / 评估型 / 风险型（可选） |
| demand | string | H / M / L 需求强度 |
| priority | string | P0 / P1 / P2 档位 |
| priority_score | float | 量化分数（保留 2 位小数） |
| clarification | object | 五要素（主体/场景/目标/约束/边界） |
| original | string | 去重前的原始问题 |
| source | string | 问题发现渠道 |
| frequency | int | 收集阶段统计的频次 |
| source_count | int | 跨来源数 |

## 示例

```json
{
  "question_id": "Q-001",
  "text": "对于体重 70kg、目标每周减重 0.5-1kg 的久坐上班族，每日热量摄入应控制在什么范围？",
  "dimension": "实操方法",
  "depth": "L2",
  "depth_label": "L2 方法层（怎么做）",
  "primary_type": "方法型",
  "secondary_type": "评估型",
  "demand": "H",
  "priority": "P0",
  "priority_score": 8.6,
  "clarification": {
    "subject": "久坐上班族",
    "scenario": "减脂期",
    "goal": "每周减重 0.5-1kg",
    "constraints": "体重 70kg",
    "boundary": "只讨论热量摄入，不涉及具体食物选择"
  },
  "original": "减脂吃多少合适",
  "source": "知乎热问",
  "frequency": 12,
  "source_count": 3
}
```

## 输出位置建议

```
<工作目录>/outputs/question_list_YYYYMMDD.json
<工作目录>/outputs/question_list_YYYYMMDD.md  ← 人类可读版
```