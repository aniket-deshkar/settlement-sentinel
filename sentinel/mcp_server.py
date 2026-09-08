"""Read-only MCP tools over stdio. No mutation tool is exposed to an LLM."""
from mcp.server.fastmcp import FastMCP
mcp = FastMCP('settlement-evidence')
DATA = {
 'fee_mismatch': {'payment_id':'PAY-1042','expected_minor':125000,'settled_minor':123500,'currency':'INR','reason':'Unbooked processor fee','reference':'processor-batch-042'},
 'duplicate': {'payment_id':'PAY-1043','expected_minor':80000,'settled_minor':160000,'currency':'INR','reason':'Possible duplicate settlement','reference':'processor-batch-043'},
 'high_value': {'payment_id':'PAY-1044','expected_minor':9000000,'settled_minor':1000000,'currency':'INR','reason':'Large unresolved settlement gap','reference':'processor-batch-044'},
}
@mcp.tool()
def get_settlement(scenario: str) -> dict:
    """Return authoritative SYNTHETIC settlement evidence for one named scenario."""
    if scenario not in DATA: raise ValueError('Unknown scenario')
    return DATA[scenario]
@mcp.tool()
def get_runbook() -> dict:
    """Return the versioned investigation runbook, without executable instructions."""
    return {'version':'2026-09-01','rule':'Compare expected and settled minor units. Document evidence. Always require human review. Never transfer real funds.'}
if __name__ == '__main__': mcp.run(transport='stdio')
