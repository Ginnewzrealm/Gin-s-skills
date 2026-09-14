# 简历渲染回归测试

Python 测试需要 pytest：

```sh
python3 -m pytest -q tests
```

浏览器测试需要 Node.js、playwright-core 和 Chrome。通过 `NODE_PATH` 指向包含 playwright-core 的 node_modules，通过 `CHROME_PATH` 指向 Chrome 可执行文件：

```sh
node tests/test_print_layout.cjs
node tests/test_editable_fields.cjs
```

- 打印测试覆盖三种主题、编辑/保存态、短文/多页内容；设置 `PDF_OUT` 可导出 12 份模拟 PDF，以便检查页数、文本完整性及尾页。
- 编辑测试使用 `python3`（可通过 `PYTHON` 指定）生成模拟简历，验证顶部学历和独立教育条目可编辑，下载 HTML 后内容与编辑能力保留。
- 测试不读取职业知识库，不包含真实简历资料。
