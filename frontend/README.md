# MCP React Frontend

Development server (after installing deps):

```bash
cd frontend
npm install
npm run dev
```

It expects the FastAPI backend on http://localhost:8080 and MCP server mounted at /mcp on 8000.

Environment tweaks:
- Edit BASE_URL in src/util/api.ts if backend runs elsewhere.

Available panels:
- Tool list
- Chat panel
- Quick actions (all tools now)
- Status bar (auto refresh every 5s)

Build:
```bash
npm run build
```
