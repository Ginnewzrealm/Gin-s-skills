# 公司研究缓存规范

## 目的

避免对同一公司重复做联网研究。求职信和面试准备时先查缓存，缓存命中且未过期则复用。

## 文件位置

`company_research/<normalized-company-name>.json`

公司名称标准化规则：
- 去掉前后空格
- 去掉「有限公司」「有限责任公司」「股份公司」「股份有限公司」「集团」「科技」「技术」等常见后缀
- 将非字母数字中文字符替换为短横线
- 全小写

示例：`示例科技有限公司` → `示例`

## TTL

30 天。

## 缓存内容

```json
{
  "company": "示例科技",
  "fetched_date": "2026-09-01",
  "sources": {
    "website": {"url": "https://example.com", "notes": "mission, values, recent news"},
    "reviews": {"url": "", "notes": ""},
    "media": {"url": "", "notes": ""}
  }
}
```

## 重要规则

缓存仅减少重复发现工作。写入最终材料的公司具体声明仍需独立验证。
