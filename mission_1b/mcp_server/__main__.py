"""Entry point: `python -m mcp_server` runs the real-MCP stdio server."""
from .mcp_protocol import main

raise SystemExit(main())
