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

在 Claude Code 对话中说：

```text
整理素材：为什么AI写作总有AI味
```

或：

```text
我想写一篇文章，主题是...
```

## 与 human-writing 衔接

素材整理完成后，会问你是否调用「活人感写作」。

如需手动调用：

```text
请基于 ~/Documents/写作素材库/20260823-为什么AI写作总有AI味/03-素材文档.md 写一篇活人感文章。
```

## 文件结构

```text
~/Documents/写作素材库/
├── 成品/
└── 20260823-为什么AI写作总有AI味/
    ├── 00-主题定义.md
    ├── 01-会话状态.json
    ├── 02-素材碎片/
    │   ├── 20260823-001.md
    │   └── 20260824-001.md
    └── 03-素材文档.md
```
