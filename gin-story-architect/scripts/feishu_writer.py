#!/usr/bin/env python3
"""飞书多维表格写入器：将"嵌套剧本架构"大纲 JSON 写入飞书多维表格。

用法：
  python3 feishu_writer.py list-tables --base-url <多维表格链接>
  python3 feishu_writer.py write      --base-url <链接> --data outline.json [--on-conflict rename|overwrite|error]
  python3 feishu_writer.py update     --base-url <链接> --data outline_partial.json
  python3 feishu_writer.py self-test  [--data outline.json]

凭证通过 --app-id / --app-secret 或环境变量 FEISHU_APP_ID / FEISHU_APP_SECRET 提供。
大纲 JSON 格式见 references/data_format.md；三张表的字段结构内置在本脚本中，模型只提供记录内容。
"""

import argparse
import json
import os
import re
import sys
import time

try:
    import requests
except ImportError:
    sys.exit("缺少依赖：请先执行 pip install requests")

API_BASE = "https://open.feishu.cn/open-apis"

# ---------------------------------------------------------------------------
# 三表结构定义 v2（字段顺序即列顺序；select 的 options 为预定义选项）
# ---------------------------------------------------------------------------

TABLE_SCHEMAS = {
    "总纲面板": {
        "feishu_name": "0-总纲面板",
        "key_fields": ["项目"],
        "fields": [
            ("项目", "text"),
            ("内容", "text"),
            ("调用产出物", "text"),
            ("对应集数", "text"),
        ],
    },
    "主线与分支线总表": {
        "feishu_name": "1-主线与分支线总表",
        "key_fields": ["编号"],
        "fields": [
            ("编号", "text"),
            ("模块名", "text"),
            ("模块目标", "text"),
            ("核心人物", "text"),
            ("进度条拉满标志", "text"),
            ("对总攻的贡献", "text"),
        ],
    },
    "剧集总表": {
        "feishu_name": "2-剧集总表",
        "key_fields": ["任务编号"],
        "fields": [
            ("集号", "number"),
            ("任务编号", "text"),
            ("挂载主线", ("select", ["A", "B", "C", "D", "E"])),
            ("单元事件", "text"),
            ("数据产出", "text"),
            ("产出物编号", "text"),
            ("消费线", "text"),
            ("回收集数", "number"),
            ("回收方式", "text"),
            ("状态更新", "text"),
            ("人物代价", "text"),
            ("结尾钩子", "text"),
            ("主线浓度", ("select", ["低", "中", "高"])),
            ("波及主线", "text"),
            ("助力还是麻烦", ("select", ["助力", "麻烦", "混合"])),
            ("反派同步动作", "text"),
        ],
    },
}

# 飞书字段类型码
FIELD_TYPE_CODE = {"text": 1, "number": 2, "select": 3}


# ---------------------------------------------------------------------------
# 凭证与 HTTP
# ---------------------------------------------------------------------------

class FeishuError(Exception):
    pass


def get_tenant_token(app_id, app_secret):
    resp = requests.post(
        f"{API_BASE}/auth/v3/tenant_access_token/internal",
        json={"app_id": app_id, "app_secret": app_secret},
        timeout=30,
    )
    data = resp.json()
    if data.get("code") != 0:
        raise FeishuError(
            f"获取 tenant_access_token 失败：{data.get('msg')}（code={data.get('code')}）。"
            "请检查 app_id / app_secret 是否正确、应用是否已启用并发布。"
        )
    return data["tenant_access_token"]


def api(token, method, path, **kwargs):
    resp = requests.request(
        method,
        f"{API_BASE}{path}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=60,
        **kwargs,
    )
    data = resp.json()
    if data.get("code") != 0:
        code = data.get("code")
        msg = data.get("msg")
        hint = ""
        if code in (99991672, 1254036, 1254043, 1254067) or resp.status_code in (401, 403):
            hint = (
                "【排查】权限不足。请依次确认："
                "1) 自建应用已开通「多维表格」相关权限并已发布版本；"
                "2) 已在目标多维表格中将该应用添加为协作者（文档右上角 … → 更多 → 添加文档应用）；"
                "3) 链接对应的 Base 与授权应用属于同一租户。"
            )
        raise FeishuError(f"飞书 API 错误 {method} {path}：{msg}（code={code}）。{hint}")
    return data.get("data", {})


# ---------------------------------------------------------------------------
# 链接解析
# ---------------------------------------------------------------------------

def parse_base_url(url):
    """从飞书多维表格链接解析 app_token。支持 feishu.cn/base/xxx 及各租户域名。"""
    m = re.search(r"/base/([A-Za-z0-9]+)", url)
    if not m:
        raise FeishuError(
            f"无法从链接解析多维表格 app_token：{url}。"
            "请确认提供的是「多维表格」链接（形如 https://xxx.feishu.cn/base/XXXX），而非电子表格（/sheets/）或文档（/docx/）链接。"
        )
    return m.group(1)


# ---------------------------------------------------------------------------
# 数据校验与规范化
# ---------------------------------------------------------------------------

def validate_and_normalize(data):
    """校验大纲 JSON，返回 {表名: [规范化的记录]}。错误直接抛出。"""
    if not isinstance(data, dict):
        raise FeishuError("大纲 JSON 顶层必须是对象，键为表名，值为记录数组。")
    unknown = [k for k in data if k not in TABLE_SCHEMAS]
    if unknown:
        raise FeishuError(f"存在未知表名：{unknown}。合法表名：{list(TABLE_SCHEMAS)}")

    normalized = {}
    errors = []
    for table_name, rows in data.items():
        schema = TABLE_SCHEMAS[table_name]
        valid_fields = {f[0]: f[1] for f in schema["fields"]}
        if not isinstance(rows, list):
            errors.append(f"表「{table_name}」的值必须是数组")
            continue
        seen_keys = set()
        out_rows = []
        for i, row in enumerate(rows, 1):
            if not isinstance(row, dict):
                errors.append(f"表「{table_name}」第 {i} 行不是对象")
                continue
            rec = {}
            for fname, fval in row.items():
                if fname not in valid_fields:
                    errors.append(f"表「{table_name}」第 {i} 行含未知字段「{fname}」")
                    continue
                spec = valid_fields[fname]
                if spec == "number":
                    if fval is None or fval == "":
                        continue
                    if isinstance(fval, (int, float)):
                        rec[fname] = fval
                    else:
                        try:
                            rec[fname] = float(str(fval))
                        except ValueError:
                            errors.append(f"表「{table_name}」第 {i} 行字段「{fname}」应为数字，得到：{fval!r}")
                elif isinstance(spec, tuple) and spec[0] == "select":
                    if fval is None or fval == "":
                        continue
                    if fval not in spec[1]:
                        errors.append(f"表「{table_name}」第 {i} 行字段「{fname}」取值「{fval}」不在选项 {spec[1]} 内")
                    else:
                        rec[fname] = fval
                else:
                    rec[fname] = str(fval)
            # 必填：关键字段
            for kf in schema["key_fields"]:
                if kf not in rec or rec[kf] in ("", None):
                    errors.append(f"表「{table_name}」第 {i} 行缺少关键字段「{kf}」")
            key_tuple = tuple(rec.get(kf) for kf in schema["key_fields"])
            if key_tuple in seen_keys:
                errors.append(f"表「{table_name}」关键字段重复：{key_tuple}")
            seen_keys.add(key_tuple)
            out_rows.append(rec)
        normalized[table_name] = out_rows
    if errors:
        raise FeishuError("大纲数据校验未通过：\n- " + "\n- ".join(errors))
    return normalized


# ---------------------------------------------------------------------------
# 飞书表操作
# ---------------------------------------------------------------------------

def list_tables(token, app_token):
    tables = {}
    page_token = None
    while True:
        params = {"page_size": 100}
        if page_token:
            params["page_token"] = page_token
        data = api(token, "GET", f"/bitable/v1/apps/{app_token}/tables", params=params)
        for item in data.get("items", []):
            tables[item["name"]] = item["table_id"]
        if not data.get("has_more"):
            break
        page_token = data.get("page_token")
    return tables


def build_field_defs(schema):
    defs = []
    for fname, spec in schema["fields"]:
        if isinstance(spec, tuple) and spec[0] == "select":
            defs.append({
                "field_name": fname,
                "type": FIELD_TYPE_CODE["select"],
                "property": {"options": [{"name": o} for o in spec[1]]},
            })
        else:
            defs.append({"field_name": fname, "type": FIELD_TYPE_CODE[spec]})
    return defs


def create_table(token, app_token, name, schema):
    data = api(
        token, "POST", f"/bitable/v1/apps/{app_token}/tables",
        json={"table": {"name": name, "fields": build_field_defs(schema)}},
    )
    return data["table_id"]


def delete_table(token, app_token, table_id):
    api(token, "DELETE", f"/bitable/v1/apps/{app_token}/tables/{table_id}")


def batch_create(token, app_token, table_id, records):
    for i in range(0, len(records), 500):
        chunk = records[i:i + 500]
        api(
            token, "POST",
            f"/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_create",
            json={"records": [{"fields": r} for r in chunk]},
        )
        if i + 500 < len(records):
            time.sleep(0.5)


def list_records(token, app_token, table_id):
    records = []
    page_token = None
    while True:
        params = {"page_size": 500}
        if page_token:
            params["page_token"] = page_token
        data = api(token, "GET", f"/bitable/v1/apps/{app_token}/tables/{table_id}/records", params=params)
        records.extend(data.get("items", []))
        if not data.get("has_more"):
            break
        page_token = data.get("page_token")
    return records


def update_record(token, app_token, table_id, record_id, fields):
    api(
        token, "PUT",
        f"/bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}",
        json={"fields": fields},
    )


def extract_key(record_fields, key_fields):
    vals = []
    for kf in key_fields:
        v = record_fields.get(kf)
        # 飞书文本字段返回的可能是富文本数组
        if isinstance(v, list):
            v = "".join(seg.get("text", "") for seg in v if isinstance(seg, dict))
        vals.append(v)
    return tuple(vals)


# ---------------------------------------------------------------------------
# 子命令
# ---------------------------------------------------------------------------

def cmd_self_test(args):
    """离线自测：链接解析 + 数据校验，不访问网络。"""
    print("[self-test] 链接解析测试…")
    cases = [
        ("https://abc.feishu.cn/base/XyZ123AbC?table=tbl1", "XyZ123AbC"),
        ("https://feishu.cn/base/bascnAbCdEf123", "bascnAbCdEf123"),
    ]
    for url, expect in cases:
        got = parse_base_url(url)
        assert got == expect, f"{url} -> {got} != {expect}"
    try:
        parse_base_url("https://abc.feishu.cn/sheets/shtcn123")
        raise AssertionError("应拒绝电子表格链接")
    except FeishuError:
        pass
    print("[self-test] 链接解析 OK")

    print("[self-test] schema 校验测试…")
    sample = {
        "剧集总表": [
            {"集号": 1, "任务编号": "A-1", "挂载主线": "A", "单元事件": "e", "数据产出": "p",
             "产出物编号": "P-01", "状态更新": "s", "人物代价": "c", "结尾钩子": "h",
             "主线浓度": "中", "波及主线": "B", "助力还是麻烦": "助力"},
        ],
        "主线与分支线总表": [
            {"编号": "A", "模块名": "资源线", "模块目标": "g"},
        ],
        "总纲面板": [
            {"项目": "一句话故事", "内容": "x"},
        ],
    }
    out = validate_and_normalize(sample)
    assert out["剧集总表"][0]["集号"] == 1
    bad = {"剧集总表": [{"任务编号": "A-1", "挂载主线": "Z"}]}
    try:
        validate_and_normalize(bad)
        raise AssertionError("应拒绝非法单选值")
    except FeishuError:
        pass
    print("[self-test] schema 校验 OK")

    if args.data:
        with open(args.data, encoding="utf-8") as f:
            data = json.load(f)
        out = validate_and_normalize(data)
        total = sum(len(v) for v in out.values())
        print(f"[self-test] 数据文件校验 OK：{len(out)} 张表，共 {total} 行")
    print("self-test 全部通过")


def cmd_list_tables(args):
    token = get_tenant_token(args.app_id, args.app_secret)
    app_token = parse_base_url(args.base_url)
    tables = list_tables(token, app_token)
    print(json.dumps(tables, ensure_ascii=False, indent=2))


def cmd_write(args):
    with open(args.data, encoding="utf-8") as f:
        data = json.load(f)
    normalized = validate_and_normalize(data)

    token = get_tenant_token(args.app_id, args.app_secret)
    app_token = parse_base_url(args.base_url)
    existing = list_tables(token, app_token)

    summary = []
    for table_name, schema in TABLE_SCHEMAS.items():
        rows = normalized.get(table_name)
        if rows is None:
            continue
        target_name = schema["feishu_name"]
        if target_name in existing:
            if args.on_conflict == "error":
                raise FeishuError(
                    f"多维表格中已存在同名数据表「{target_name}」。"
                    "请选择：--on-conflict rename（新建带时间戳副本）或 overwrite（删除旧表重建）。"
                )
            elif args.on_conflict == "rename":
                target_name = f"{target_name}-{time.strftime('%m%d-%H%M')}"
            elif args.on_conflict == "overwrite":
                delete_table(token, app_token, existing[target_name])
        table_id = create_table(token, app_token, target_name, schema)
        existing[target_name] = table_id
        if rows:
            batch_create(token, app_token, table_id, rows)
        summary.append({"表": target_name, "行数": len(rows), "table_id": table_id})

    print(json.dumps({"status": "ok", "base": args.base_url, "写入": summary},
                     ensure_ascii=False, indent=2))


def cmd_update(args):
    """按各表关键字段 upsert：存在则更新，不存在则追加。"""
    with open(args.data, encoding="utf-8") as f:
        data = json.load(f)
    normalized = validate_and_normalize(data)

    token = get_tenant_token(args.app_id, args.app_secret)
    app_token = parse_base_url(args.base_url)
    existing = list_tables(token, app_token)

    summary = []
    for table_name, rows in normalized.items():
        schema = TABLE_SCHEMAS[table_name]
        feishu_name = schema["feishu_name"]
        if feishu_name not in existing:
            raise FeishuError(f"多维表格中不存在表「{feishu_name}」，请先用 write 模式创建。")
        table_id = existing[feishu_name]
        current = list_records(token, app_token, table_id)
        key_fields = schema["key_fields"]
        index = {}
        for rec in current:
            index[extract_key(rec.get("fields", {}), key_fields)] = rec["record_id"]

        updated, appended = 0, 0
        for row in rows:
            key = tuple(row.get(kf) for kf in key_fields)
            if key in index:
                update_record(token, app_token, table_id, index[key], row)
                updated += 1
            else:
                batch_create(token, app_token, table_id, [row])
                appended += 1
        summary.append({"表": feishu_name, "更新": updated, "追加": appended})

    print(json.dumps({"status": "ok", "结果": summary}, ensure_ascii=False, indent=2))


# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="嵌套剧本架构 → 飞书多维表格写入器")
    parser.add_argument("command", choices=["list-tables", "write", "update", "self-test"])
    parser.add_argument("--base-url", help="飞书多维表格链接（…/base/XXXX）")
    parser.add_argument("--data", help="大纲 JSON 文件路径")
    parser.add_argument("--app-id", default=os.environ.get("FEISHU_APP_ID"))
    parser.add_argument("--app-secret", default=os.environ.get("FEISHU_APP_SECRET"))
    parser.add_argument("--on-conflict", choices=["error", "rename", "overwrite"], default="error",
                        help="write 模式下同名表的处理策略，默认 error")
    args = parser.parse_args()

    try:
        if args.command == "self-test":
            cmd_self_test(args)
            return
        if not args.base_url:
            sys.exit("缺少 --base-url")
        if not args.app_id or not args.app_secret:
            sys.exit("缺少飞书应用凭证：提供 --app-id/--app-secret 或设置环境变量 FEISHU_APP_ID/FEISHU_APP_SECRET")
        if args.command in ("write", "update") and not args.data:
            sys.exit("缺少 --data")
        {"list-tables": cmd_list_tables, "write": cmd_write, "update": cmd_update}[args.command](args)
    except FeishuError as e:
        sys.exit(f"错误：{e}")


if __name__ == "__main__":
    main()
