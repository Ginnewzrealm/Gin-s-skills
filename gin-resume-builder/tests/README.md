# 简历渲染回归测试

Python 测试需要 pytest，涵盖七项头部信息、岗位匹配置顶、全文小标题、完整教育记录、三主题普通/编辑版和缺项拦截：

```sh
python3 -m pytest -q tests
```

浏览器测试需要 Node.js、playwright-core 和 Chrome。通过 `NODE_PATH` 指向包含 playwright-core 的 node_modules，通过 `CHROME_PATH` 指向 Chrome 可执行文件：

```sh
node tests/test_print_layout.cjs
node tests/test_editable_fields.cjs
```

- 打印测试覆盖三种主题、编辑/保存态、短文/多页内容；设置 `PDF_OUT` 可导出 12 份模拟 PDF，以便检查页数、文本完整性及尾页。
- 编辑测试使用 `python3`（可通过 `PYTHON` 指定）生成模拟简历，验证顶部学历和独立教育条目可编辑，保存修改后内容保留，重新打开为预览态，可通过“预览/编辑”重新启用编辑。
- 测试不读取职业知识库，不包含真实简历资料。

浏览器用例需在允许浏览器访问的环境运行；仅 Python 测试或样式源码比对通过，不能声明已完成视觉或 PDF 验收。
