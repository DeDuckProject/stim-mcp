# Stim MCP Server

An MCP (Model Context Protocol) server that makes quantum stabilizer circuit simulation accessible through natural language. Built on [Google's Stim](https://github.com/quantumlib/Stim) high-performance stabilizer circuit simulator.

## What It Does

Lets you build, simulate, and analyze quantum stabilizer circuits interactively. Helps researchers and developers answer questions like:

- "Simulate a Bell state circuit and show me the measurement statistics"
- "What are the shortest logical error paths in my surface code circuit?"
- "Add depolarizing noise to my circuit and compare the error rates"

## Tools

| Tool | Description |
|------|-------------|
| `hello_quantum` | Health check — returns Stim version and number of active sessions |
| `create_circuit` | Validate a Stim circuit string and open a persistent session |
| `append_operation` | Append instructions to an existing circuit without resending it |
| `sample_circuit` | Compile and simulate a circuit, returning measurement statistics |
| `analyze_errors` | Build the Detector Error Model and find shortest logical error paths |
| `get_circuit_diagram` | Generate a text, SVG, or timeline diagram of the circuit |
| `inject_noise` | Create a noisy copy of a circuit (DEPOLARIZE1 or X_ERROR) |

## Installation

Requires [uv](https://docs.astral.sh/uv/getting-started/installation/).

### Via PyPI (recommended)

No cloning needed. Configure your MCP client directly (see below) — `uvx` handles installation automatically on first run.

### From source

```bash
git clone https://github.com/DeDuckProject/stim-mcp
cd stim-mcp
uv sync
```

## Usage

### Configure in Claude Desktop

**macOS** — `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows** — `%APPDATA%\Claude\claude_desktop_config.json`
**Linux** — `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "stim": {
      "command": "/path/to/uvx",
      "args": [
        "--from",
        "stim-mcp-server",
        "stim-mcp-server"
      ]
    }
  }
}
```

Replace `/path/to/uvx` with the output of `which uvx`.

### Configure in Claude Code

```bash
claude mcp add stim -- /path/to/uvx --from stim-mcp-server stim-mcp-server
```

Replace `/path/to/uvx` with the output of `which uvx`.

### From source (development)

```bash
claude mcp add stim -- /path/to/uv run --directory /path/to/stim-mcp stim-mcp-server
```

### Inspect with MCP dev tools

```bash
uv run mcp dev src/stim_mcp_server/server.py
```

## Example Queries

Via an LLM with this MCP server connected:

> "Create a Bell state circuit and sample it 1000 times"

> "Build a 3-qubit repetition code and analyze its error model"

> "Inject 0.1% depolarizing noise into my circuit and show me the updated diagram"

> "What's the circuit diagram for this surface code as an SVG?"

## Running Tests

```bash
uv run pytest
```
