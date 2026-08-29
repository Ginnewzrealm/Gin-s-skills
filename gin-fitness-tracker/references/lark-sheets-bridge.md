# lark-sheets（飞书表格）调用约定（桥接，不直连接口）

> 何时读我：任何子技能需要读写飞书表格前，必须先读本文件。
> 前提：用户环境中已安装 `lark-sheets` skill 或 `lark` CLI。未安装则返回 `LARK_SKILL_UNAVAILABLE` 错误。

## 一、职责边界（禁止越界）

- **lark-sheets skill / lark CLI 负责**：
  - 飞书开放接口的鉴权、请求发送、限频控制与重试
  - 返回结果的格式整理与错误信息返回
  - 凭证的存储与管理（在其自身配置中）
- **本技能（gin-fitness-tracker）负责**：
  - 检测 lark-sheets 能力是否可用
  - 构造业务参数（表格 URL、子表名、日期、字段映射等）
  - 接收返回结果并按本技能规则使用与验证（写后复查、截断检测等）
- **本技能明确不执行**：
  - 不直接向飞书开放接口发起网络请求
  - 不存储、不读取、不经手任何飞书凭证（App ID / App Secret / Token 等）
  - 不实现重试逻辑（重试由 lark-sheets 能力内部负责）
  - 不修改 lark-sheets 能力的行为逻辑

## 二、依赖检测

1. 检测环境中 `lark-sheets` skill 是否可用
2. 不可用则检测 `lark` CLI 是否已安装（`command -v lark`）
3. **任一可用** → 继续执行
4. **均不可用** → 返回 `LARK_SKILL_UNAVAILABLE` 错误，提示用户安装

## 三、输入参数

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `spreadsheet_url` | string | 是 | 飞书电子表格 URL，来自 `atlas-config.yaml` 的 `fitness.sheets.url` |
| `sheet_name` | string | 是 | 子表名，如 `每日记录`、`字段元数据`、`用户配置` |
| `range` | string | 视模式而定 | 单元格范围，如 `A1:Z1` |
| `fields` | object | 写入时 | `字段名 → 值` 的映射 |
| `date` | string | 查询/写入时 | 格式 `YYYY-MM-DD` |

具体调用模式（verify_spreadsheet / read_header / read_field_metadata / find_date_row / create_date_row / read_column_formats 等）详见 `knowledge/sheets-calling-patterns.md`。

## 四、输出结果

| 字段名 | 类型 | 存在条件 | 说明 |
|--------|------|----------|------|
| `status` | string | 始终 | `success` / `failed` |
| `data` | object/array | 成功时 | 读取到的表头、记录、配置等 |
| `error` | object | 失败时 | `code` + `message` |
| `revision` | string | 写入成功时 | 用于写后复查的证据 |
| `updated_cells_count` | number | 写入成功时 | 写入单元格数 |

## 五、异常处理

| 异常情况 | 处理方式 |
|----------|----------|
| lark-sheets / lark CLI 未安装 | 返回 `LARK_SKILL_UNAVAILABLE`，提示安装 |
| 表格或子表不存在 | 返回 `TABLE_NOT_FOUND`，不自动创建 |
| 写入后复查不一致 | 换工具重试，仍不一致则返回 `FIELD_WRITE_FAILED` |
| 返回字段数量/长度异常 | 标截断风险，降级手动粘贴 |
| 权限错误 | 返回 `TABLE_NOT_FOUND`，提示检查表格权限 |
