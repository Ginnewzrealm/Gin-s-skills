# CHANGELOG
## 2026-08-30 · v0.4.0 · minor
- 新增 Progress Checklist 进度可视化设计
- 新增 `scripts/progress_reporter.py` 统一渲染 mine/review/correct/build 各动作 checklist
- 新增 `scripts/stage_validator.py` 阶段决策与跳转合法性校验
- `scripts/session.py` 增加 `stage` 字段持久化，支持会话恢复时重建 checklist
- `SKILL.md` 增加 Progress Checklist 使用规则、步骤标签、阻塞提示与禁止项

## 2026-08-23 · v0.3.0 · minor
- 重构输出结构：每个主题一个 `{日期}-{中文主题名}/` 项目文件夹
- 新增内部文件命名：`00-主题定义.md`、`01-会话状态.json`、`02-素材碎片/`、`03-素材文档.md`
- 碎片文件名改为 `{日期}-{当天序号}.md`
- 同一主题多次沟通时持续向同一文件夹追加
- 初始化不再创建 `.gin-writing-materials/` 隐藏目录，检测到旧目录时提示用户

## 2026-08-22 · v0.1.1 · patch
- 初版实现完成


## 2026-08-22 · v0.1.0 · 新增
- 初版：7 种提问方法、5 字段质检、human-writing 接口、主题定义阶段、完整性评分
