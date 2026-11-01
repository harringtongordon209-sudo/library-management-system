# Adding & Testing MCP Tools — Quick Reference

## Prerequisites (must be running before you test anything)

```bash
# 1. Postgres + Redis
docker compose up -d          # run from the project root

# 2. FastAPI backend (tools call this over HTTP)
cd backend
uv run uvicorn main:app --reload
```

# 3. Start the frontend web server
cd frontend
npm run dev
```

## Adding a new tool to mcp_server.py

Every tool needs three things:

```python
@server.tool()                              # 1. registers it as a tool — don't forget this!
def my_new_tool(some_arg: str) -> list[dict]:  # 2. type hints define the input/output schema
    """One clear sentence describing what this does and when to use it."""  # 3. docstring = description Claude reads to decide when to call it

    response = httpx.get(f"{API_BASE_URL}/api/some-endpoint", params={"some_arg": some_arg})
    # use httpx.post(..., json={...}) for endpoints that expect a JSON body (most POST/PATCH routes)
    # use params={...} only for query-string parameters (most GET routes)
    response.raise_for_status()   # let errors raise — don't try/except, the SDK reports failures to Claude for you
    return response.json()
```

Checklist before testing:
- [ ] `@server.tool()` decorator present (a plain function with no decorator is invisible to Claude/Inspector)
- [ ] Type hints on every parameter and the return value
- [ ] Docstring describes the action clearly (this is what Claude uses to decide when to call it)
- [ ] Matches the backend endpoint's actual expectations: query params (`params=`) vs JSON body (`json=`), and the right HTTP method (`httpx.get` / `.post` / `.patch`)

## Testing with the MCP Inspector

Run from the `backend/` directory:

```bash
npx @modelcontextprotocol/inspector uv run python mcp_server.py
```

- This installs/starts the Inspector and opens a browser UI (prints a URL with an auth token if it doesn't auto-open).
- Go to the **Tools** tab — your new tool should be listed with the schema auto-generated from its type hints/docstring.
- Select it, fill in the arguments, click **Run/Call Tool**, and check the JSON result matches what you'd expect from the real endpoint.
- Stop it with Ctrl+C when done (it doesn't need to stay running).

## Using it for real in Claude Code

No need to re-run `claude mcp add` — that registered the whole server once. Any tool currently in `mcp_server.py` is picked up automatically the next time the server process starts.

1. Save your changes to `mcp_server.py`.
2. Start a **new Claude Code session** (existing sessions already launched the server and won't see new tools).
3. Try a natural-language prompt that should trigger the new tool.

## Quick command reference

| Task | Command |
|---|---|
| Start Postgres/Redis | `docker compose up -d` (from project root) |
| Start backend | `uv run uvicorn main:app --reload` (from `backend/`) |
| Test tools manually | `npx @modelcontextprotocol/inspector uv run python mcp_server.py` (from `backend/`) |
| Check registered MCP servers | `claude mcp list` |
| Remove a registered server | `claude mcp remove library-management` |
