"""data_semantics —— 数据口径治理（口径 diff → 扇出检测 → 下钻 → 契约固化）。

业务判断全部留在本包；跨 MCP 通用能力来自 dbt-core / dbt-store / dbt-know，
MCP 运行时外壳来自 dbt-core.mcp_kit。本包不 import 任何其他 MCP。
"""

from data_semantics import semantics
from data_semantics.server import MCP_NAME, TOOLS, main
__all__ = ["MCP_NAME", "TOOLS", "main", "semantics"]

__version__ = "0.2.0"
