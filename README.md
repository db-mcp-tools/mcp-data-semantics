# mcp-data-semantics

**数据口径治理** · MCP Server

> 两个部门都说 DAU 是 100 万，差 30 万 —— 问题多半不在数据，在口径。

## 安装（按需，不必装其他 MCP）

```bash
pip install ./mcp-data-semantics              # 在工具链根目录下执行
pip install "./mcp-data-semantics[mysql]"     # 需要连库时补驱动，或 [postgres]
```

会自动带上它需要的共享库：`dbt-core`（方言/AST）、`dbt-store`（口径字典）。**不会**带其他 MCP。

## 挂到 MCP 客户端

```json
{
  "mcpServers": {
    "data-semantics": {
      "command": "python",
      "args": ["-m", "data_semantics"],
      "env": { "DBT_STORE": "~/.dbtoolchain" }
    }
  }
}
```

按你的客户端（Claude Desktop / Cursor / Cline 等）说明，把这段合并到对应的 `mcpServers` 配置里。

命令行调试（不挂客户端也能用）：

```bash
dbt-data-semantics tools
dbt-data-semantics call <tool> --args '{"sql": "SELECT 1"}'
```

## 工具（13）

| 工具 | 作用 |
|---|---|
| `build_lineage` | 从一组 ETL/视图 SQL 推导表级与列级血缘。 |
| `check_grain` | 粒度冲突检测：明细 vs 聚合混用。 |
| `check_timezone_window` | 时区与日期窗口边界差异检查 —— 表现为"每天的数的都不一样"。 |
| `compare_definitions` | ★ 结构化 diff —— 不是让人肉眼对着两段 SQL 看，而是逐项列出不等价点。 |
| `detect_drift` | 同一指标的时间序列漂移检测。**只有 1 个点时明确说不能判断** |
| `detect_fanout` | JOIN 扇出检测 —— 数字虚高的头号原因。 |
| `generate_metric_contract` | 生成可读的指标契约 YAML —— 这是真正能落地的治理产物。 |
| `get_definition` | — |
| `list_definitions` | — |
| `parse_metric_definition` | 把口径抽成结构化对象。**没法比对的口径等于没有治理** |
| `reconcile` | 数字对不上时的下钻计划 —— 按"先口径后数据"的顺序排查。 |
| `record_definition` | 写入指标字典（共享档案的一部分）。 |
| `suggest_canonical` | 从多个候选口径里推荐标准口径，并列出需要改造的那些。 |

## 闭环

`parse_metric_definition` 结构化 → `compare_definitions` diff → `detect_fanout` 扇出检测（可选 SQL 证伪）→ `reconcile` 逐层下钻 → `generate_contract` 固化为 YAML 契约

## Tier（冷启动保证）

`tier0` 做定义层 diff；有历史数据点时才谈漂移 —— `detect_drift` 单点显式返回 `insufficient_data`，不硬猜趋势。

## 边界：这个仓不做什么

只做指标定义的比对、溯源与契约化。SQL 性能归 `mcp-sql-review`。

## 开发

```bash
python tests/test_data_semantics.py      # 不需要 pytest，也不需要数据库
```
