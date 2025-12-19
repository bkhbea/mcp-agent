from pathlib import Path
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("File Server")
mcp.title = "File MCP Server"

BASE_DIR = Path(__file__).resolve().parent.parent

# NOTE THE TRAILING SLASH
@mcp.resource("file://{path}/")
def read_file(path: str) -> str:
    file_path = (BASE_DIR / path).resolve()

    if not file_path.is_file() or BASE_DIR not in file_path.parents:
        raise ValueError(f"File not allowed: {path}\n {BASE_DIR}")

    return file_path.read_text(encoding="utf-8")

@mcp.tool()
def write_file(path: str, content: str) -> dict:
    """
    Write content to a file under BASE_DIR.
    Returns the file path and status.
    """
    file_path = (BASE_DIR / path).resolve()
    if BASE_DIR not in file_path.parents:
        raise ValueError(f"File not allowed: {path}")

    file_path.write_text(content, encoding="utf-8")
    return {"path": path, "status": "ok"}


if __name__ == "__main__":
    mcp.run(transport="stdio")
