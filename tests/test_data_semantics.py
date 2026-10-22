#!/usr/bin/env python3
"""data-semantics 回归测试：口径 diff / 扇出 / 下钻 / 漂移

不依赖 pytest / 真实数据库。直接运行：

    python tests/test_data_semantics.py
"""

from __future__ import annotations

import os
import pathlib
import sys
import tempfile

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent / "src"))
# 开发期：兄弟仓库用源码目录；正式使用请 pip install（见 README）
for _sib in ("dbt-core", "dbt-store", "dbt-mcp-kit"):
    _p = _HERE.parent.parent / _sib / "src"
    if _p.is_dir() and str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

os.environ.setdefault("DBT_LOG_LEVEL", "ERROR")
_TMPDIR = tempfile.mkdtemp(prefix="dbt-data_semantics-")
os.environ.setdefault("DBT_STORE", os.path.join(_TMPDIR, "store.db"))

from dbcore.protocol import Result, ToolError  # noqa: E402
from data_semantics import server as DS  # noqa: E402

PASSED: list[str] = []
FAILED: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        PASSED.append(name)
    else:
        FAILED.append(f"{name}  << {detail[:300] if detail else ''}")


def section(title: str) -> None:
    print(f"\n── {title}")


section("8. data-semantics MCP")
# ==================================================================

c1 = DS.compare_definitions(
    "SELECT COUNT(DISTINCT uid) FROM orders WHERE created_at >= 1 AND status=1",
    "SELECT COUNT(*) FROM orders WHERE create_time >= 1").to_dict()
check("口径差异检出", not c1["data"]["equivalent"])
aspects = {d["aspect"] for d in c1["data"]["diffs"]}
check("去重差异被检出", "dedupe" in aspects, str(aspects))
check("度量差异被检出", "measures" in aspects)
check("过滤差异被检出", "filters" in aspects)

pd = DS.parse_metric_definition(sql="SELECT COUNT(DISTINCT uid) FROM orders WHERE status=1",
                                name="DAU").to_dict()
check("口径解析出度量", len(pd["data"]["measures"]) == 1)
check("口径解析出去重键", pd["data"]["dedupe_key"] == "uid", str(pd["data"]["dedupe_key"]))

fan = DS.detect_fanout("SELECT COUNT(*) FROM orders o JOIN pay p ON p.order_id=o.id",
                       "mysql").to_dict()
check("扇出风险检出", fan["data"]["risk"])
check("扇出给出验证 SQL", bool(fan["data"].get("verify_sql")))
fan2 = DS.detect_fanout("SELECT COUNT(DISTINCT o.id) FROM orders o JOIN pay p ON p.order_id=o.id",
                        "mysql").to_dict()
check("有 DISTINCT 保护时不报", not fan2["data"]["risk"])

lg = DS.build_lineage({"v1": "SELECT id FROM orders", "v2": "SELECT id FROM v1"},
                      "mysql").to_dict()
check("血缘构建", len(lg["data"]["table_edges"]) >= 2)
check("血缘根表识别", "orders" in lg["data"]["roots"])

cg = DS.check_grain("SELECT id, COUNT(*) FROM orders").to_dict()
check("粒度冲突检出", len(cg["data"]["issues"]) > 0)
tz = DS.check_timezone_window("SELECT COUNT(*) FROM t WHERE created_at >= 1").to_dict()
check("时区窗口检查", tz["ok"])
rc = DS.reconcile("SELECT COUNT(*) FROM orders o JOIN pay p ON p.oid=o.id",
                  expected=100, actual=137).to_dict()
check("下钻计划生成", len(rc["data"]["steps"]) >= 4)
check("下钻给出假设顺序", len(rc["data"]["hypothesis_order"]) >= 3)
ct = DS.generate_metric_contract(pd["data"], owner="data-team").to_dict()
check("契约生成", "dedupe_key" in ct["data"]["yaml"])
DS.record_definition("DAU", pd["data"])
gd = DS.get_definition("DAU").to_dict()
check("口径字典读写", gd["ok"] and gd["data"].get("name") == "DAU")
check("口径字典列表", DS.list_definitions().to_dict()["data"]["total"] >= 1)

# ==================================================================

from data_semantics.semantics import detect_drift as _drift
# 13.7 drift 容差分级 + 连续确认
_d1 = _drift([{"value": 100}, {"value": 106}, {"value": 101}, {"value": 100}])
check("drift：单点毛刺不告警", not _d1["drifted"])
_d2 = _drift([{"value": 100}, {"value": 110}, {"value": 121}])
check("drift：连续超差告警", _d2["drifted"])
_d3 = _drift([{"value": 1000}, {"value": 1010}, {"value": 1020}], metric_type="amount")
check("drift：金额类容差收紧到 0.5%", _d3["tolerance_pct"] == 0.5 and _d3["drifted"])


# 漂移检测的 Tier0 边界（单点不判断）
d1 = DS.detect_drift([{"ts": 1, "value": 100}]).to_dict()
check("单数据点不判断漂移", d1["data"]["status"] == "insufficient_data")
d2 = DS.detect_drift([{"ts": 1, "value": 100}, {"ts": 2, "value": 200}]).to_dict()
check("两点可判断漂移", d2["data"]["status"] == "ok" and d2["data"]["change_pct"] == 100.0)

# ==================================================================
print("\n" + "=" * 60)
print("通过 %d 项，失败 %d 项" % (len(PASSED), len(FAILED)))
if FAILED:
    print("\n失败明细：")
    for _f in FAILED:
        print("  ✗", _f)
    raise SystemExit(1)
print("全部通过")
