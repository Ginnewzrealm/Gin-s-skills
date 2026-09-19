# gin-writing-materials（写作素材）

通过结构化对话挖掘写作素材，输出供 `human-writing` 使用的素材文档。

## 安装

将本目录复制到 Claude Code skills 目录：

```bash
cp -r gin-writing-materials ~/.agents/skills/
```

## 初始化

```bash
python3 ~/.agents/skills/gin-writing-materials/scripts/init.py --material-root ~/Documents/写作素材库
```

### 备份配置到 Agent tools 目录（可选）

初始化完成后，Agent 可把配置备份到当前 Agent 自己的 tools 目录，
防止技能目录被更新/覆盖后丢失用户配置：

```bash
python3 ~/.agents/skills/gin-writing-materials/scripts/init.py \
  --material-root ~/Documents/写作素材库 \
  --tools-backup-dir ~/.agents/tools
```

备份会写入 `{tools-backup-dir}/gin-writing-materials/config.yaml`。
不同 Agent 平台请换成自己的 tools 路径。

在 Claude Code 对话中说。入口不要求你已经想好完整主题：

```text
整理素材：为什么AI写作总有AI味
```

或：

```text
我最近发现，准备越充分，反而越不想开始，但还没想明白原因。
```

技能会先保存这句灵感，再通过一问一答逐步澄清主问题、事实、判断、证据和边界。对话中出现的旁支会登记后暂存，未能立即归类的素材也会保留。

## 从灵感到后续写作

```text
灵感 / 经历 / 思维碎片
  → 暂定主问题（可回环）
  → 一次一问的非诱导采访
  → 原始问答与素材碎片持续落盘
  → 主线、QUD、P-X-R、旁支和闭环确认
  → 03-素材文档.md
  → 用户主动交给 human-writing 或其他下游写作 skill
```

只有知识闭环得到用户确认后，管线才把素材包视为 ready；素材数量是质量信号，不是唯一的结束条件。小灵感也可以在闭环确认后生成文档。

## 与 human-writing 衔接

素材整理完成后，本技能不会自动调用下游写作技能。如需手动调用：

```text
请基于 ~/Documents/写作素材库/20260823-为什么AI写作总有AI味/03-素材文档.md 写一篇活人感文章。
```

## 文件结构

```text
~/Documents/写作素材库/
├── 成品/
└── 20260823-为什么AI写作总有AI味/
    ├── 00-主题定义.md
    ├── 00-需求澄清.md
    ├── 01-会话状态.json
    ├── 02-素材碎片/
    │   ├── 20260823-001.md
    │   └── 20260824-001.md
    └── 03-素材文档.md
```

`01-会话状态.json` 会保存 `seed`、`main_qud`、`current_qud`、`p_x_r`、`branches` 和 `closure`，用于恢复对话主线和判断是否可以收束。

## 管线命令

完成采访并确认闭环后，可直接运行：

```bash
python3 ~/.agents/skills/gin-writing-materials/scripts/pipeline.py \
  --material-root ~/Documents/写作素材库 \
  --topic "准备越充分越不想开始"
```

需要单独检查时运行 `validate.py`；需要在确认后手动重建时运行 `build_doc.py`。两者都不会自动调用下游写作 skill。
