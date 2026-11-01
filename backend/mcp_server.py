import httpx
from mcp.server.mcpserver import MCPServer

API_BASE_URL = "http://127.0.0.1:8000"

server = MCPServer("library-management")

@server.tool()
def get_all_borrowers() -> list[dict]:
    """Gets all borrowers. Returns all borrowers with their IDs."""

    response = httpx.get(f"{API_BASE_URL}/api/borrowers")
    response.raise_for_status()
    return response.json()


@server.tool()
def search_borrowers(name: str) -> list[dict]:
    """Search for borrowers by name (partial match). Returns matching borrowers with their IDs."""

    response = httpx.get(f"{API_BASE_URL}/api/borrowers", params={"name": name})
    response.raise_for_status()
    return response.json()

@server.tool()
def create_borrower(name: str) -> dict:
    """Provide a name to create a new borrower. Returns borrower ID for the created borrower."""

    response = httpx.post(f"{API_BASE_URL}/api/borrowers", json={"name": name})
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    server.run()  # defaults to stdio transport