# Agent Skills

个人 Agent Skills 统一仓库，集中管理各类 Claude / OpenClaw Agent Skill。

## Skills

| Skill | 职责 |
|-------|------|
| `gin-wechat-article-core` | 公众号长文写作主编排入口 |
| `gin-wechat-article-clarify` | 公众号写作需求澄清 |
| `gin-wechat-article-angle` | 公众号写作素材诊断与角度匹配 |
| `gin-wechat-article-outline` | 公众号写作大纲生成 |
| `gin-wechat-article-writer` | 公众号长文正文写作 |
| `gin-wechat-article-polish` | 公众号正文润色、去 AI 味、小标题优化 |
| `gin-wechat-article-title` | 公众号全文标题与章节小标题优化 |
| `gin-wechat-article-quality` | 公众号文章四层质量自检 |
| `gin-writing-materials` | 写作素材库管理，为公众号写作准备素材 |
| `gin-fitness-tracker` | 健身追踪：每日健康数据采集、查询、写入校验，支持飞书 Sheets / Local JSON / Obsidian |
| `gin-workout-planner` | 健身助手：训练计划生成、动作安排、训记 App 写回 |
| `gin-fitness-pdca` | PDCA 减脂：基于每日健康数据执行 M1-M9 代谢扫描，生成 PDCA 周报并写入飞书表格 |
| `gin-question` | 问答技能：围绕问题构建高质量问答工作流（含评测工作区 `gin-question-workspace/`） |
| `gin-problem-clarify` | 通用问题澄清：在动手前把模糊需求问清楚 |
| `gin-resume-builder` | 中文简历求职一站式工具：简历定制、求职信、面试准备、ATS 诊断等 |
| `gin-story-brainstorm` | 脑洞大开——小说开书前的灵感孵化与世界观锻造 |
| `gin-story-architect` | 嵌套剧本架构师——把设定素材整理成剧集/网文大纲并写入飞书多维表格 |
| `shangyefenxi` | 商业可行性分析：基于横纵研究报告，输出 10 节商业可行性全景报告或对话式咨询问答 |
| `collector` | 内容采集：微信读书/网页文章抓取与转存（含 MCP server） |
| `gin-tutorial-harvest` | 教程沉淀采集：把好教程原文采下来存成本地知识 |
| `gin-tutorial-source-scan` | 教程来源扫描：发现值得沉淀的教程来源 |
| `xiejiaocheng` | 写教程：把掌握的技能/知识写成结构化教程 |
| `opencli-chrome-launcher` | OpenCLI 浏览器生命周期前置管理：检查/启动/切换 Chrome profile、清理 OpenCLI Browser 残留标签 |

## 使用方式

每个 skill 目录是标准的 Agent Skill 结构，可直接复制到 `~/.claude/skills/` 或 `~/.agents/skills/` 下使用。
