# Installation

This repository can be used in two ways:

1. As a Codex plugin that provides the `hydrus1d` skill and MCP server.
2. As a standalone MCP server launched from a local MCP client configuration.

## Requirements

- Windows with HYDRUS-1D installed.
- Python 3.10 or newer.
- HYDRUS-1D command-line executable `H1D_CALC.EXE`.

The server has no required third-party Python packages. Observation XLSX validation uses
`openpyxl` when available; CSV validation works with the Python standard library.

## Environment Variables

Set these when the HYDRUS installation or project roots are not discoverable:

```powershell
$env:HYDRUS1D_INSTALL_DIR = "C:\Program Files (x86)\PC-Progress\Hydrus-1D 4.xx"
$env:HYDRUS1D_PROJECT_ROOTS = "C:\path\to\your\hydrus-project-root"
```

Multiple project roots can be separated with semicolons.

## Standalone MCP Configuration

Use this shape in your MCP client:

```json
{
  "mcpServers": {
    "hydrus1d": {
      "command": "python",
      "args": [
        "C:\\path\\to\\hydrus1d\\hydrus1d_mcp_server.py",
        "--install-dir",
        "C:\\Program Files (x86)\\PC-Progress\\Hydrus-1D 4.xx",
        "--project-root",
        "C:\\path\\to\\your\\hydrus-project-root"
      ]
    }
  }
}
```

For a trusted local workstation you can pass `--allow-any-project`, but project-root allowlisting
is safer and recommended.

## Direct Smoke Test

```powershell
python .\hydrus1d_mcp_server.py --install-dir "C:\Program Files (x86)\PC-Progress\Hydrus-1D 4.xx" --project-root "C:\path\to\your\hydrus-project-root"
```

Then send MCP JSON-RPC lines on stdin:

```json
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"manual","version":"0"}}}
{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"find_installation","arguments":{}}}
```
