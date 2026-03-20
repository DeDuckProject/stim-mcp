# stim-mcp-server

MCP server wrapping [Google's Stim](https://github.com/quantumlib/Stim) stabilizer circuit simulator. Wire it up to an LLM and you can build and sample circuits through conversation.

## Tools

| Tool | Description |
|------|-------------|
| `hello_quantum` | Health check — returns Stim version and active session count |
| `create_circuit` | Validate a Stim circuit string and open a persistent session |
| `append_operation` | Append one or more Stim instructions to an existing circuit |
| `sample_circuit` | Simulate a circuit and return measurement statistics |
| `analyze_errors` | Build the Detector Error Model and find shortest logical error paths |
| `get_circuit_diagram` | Return an ASCII, SVG, or timeline diagram |
| `inject_noise` | Add depolarizing or X error noise to a circuit |

## Connecting to the remote server

A hosted instance runs on Google Cloud Run:

**URL**: `https://stim-mcp-5s3woqufqa-uc.a.run.app/mcp`
**Transport**: Streamable HTTP (MCP 1.x)

### Claude.ai

Go to **Settings → Integrations → Add custom integration** and enter the URL above.

### Claude Code (CLI)

Add to your `~/.claude/claude.json` (or project-level `.claude/claude.json`):

```json
{
  "mcpServers": {
    "stim-mcp": {
      "url": "https://stim-mcp-5s3woqufqa-uc.a.run.app/mcp"
    }
  }
}
```

### Other MCP clients

Use `POST https://stim-mcp-5s3woqufqa-uc.a.run.app/mcp` with `Content-Type: application/json` and `Accept: application/json, text/event-stream`.

> **Cold start**: The server scales to zero when idle. The first request after a period of inactivity may take 5–10 seconds. In-memory circuit sessions are lost on scale-down — circuits are cheap to recreate.

## Installation

Needs [uv](https://docs.astral.sh/uv/getting-started/installation/).

### Via PyPI (recommended)

No cloning needed. Configure your MCP client (see below) and `uvx` handles the rest on first run.

### From source (development)

```bash
git clone https://github.com/DeDuckProject/stim-mcp
cd stim-mcp
uv sync
```

## Running locally

### Claude Desktop

**macOS** — `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows** — `%APPDATA%\Claude\claude_desktop_config.json`
**Linux** — `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "stim": {
      "command": "/path/to/uvx",
      "args": ["--from", "stim-mcp-server", "stim-mcp-server"]
    }
  }
}
```

Replace `/path/to/uvx` with the output of `which uvx`.

### Claude Code

```bash
claude mcp add stim -- /path/to/uvx --from stim-mcp-server stim-mcp-server
```

Replace `/path/to/uvx` with the output of `which uvx`.

### From source (development)

```bash
claude mcp add stim -- /path/to/uv run --directory /path/to/stim-mcp stim-mcp-server
```

### Stdio (direct)

```bash
uv run stim-mcp-server
```

### HTTP / SSE (local testing)

```bash
MCP_TRANSPORT=sse stim-mcp-server
# Server listens on http://localhost:8080/mcp
```

Inspect with the MCP inspector:

```bash
npx @modelcontextprotocol/inspector http://localhost:8080/mcp
```

### Docker

```bash
docker build -t stim-mcp .
docker run -p 8080:8080 stim-mcp
# Server listens on http://localhost:8080/mcp
```

### MCP dev tools

```bash
uv run mcp dev src/stim_mcp_server/server.py
```

## Deploying to Cloud Run

### Prerequisites

```bash
brew install --cask google-cloud-sdk
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com
```

### Deploy

```bash
gcloud run deploy stim-mcp \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8080 \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 1
```

`--source .` triggers Cloud Build to build the Docker image — no local Docker required.
`--max-instances 1` keeps circuit sessions consistent (in-memory store).
`--min-instances 0` enables scale-to-zero.

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_TRANSPORT` | `stdio` | Set to anything else (e.g. `sse`) to start the HTTP server |
| `MCP_HOST` | `0.0.0.0` | Bind address for HTTP mode |
| `MCP_PORT` | `8080` | Port for HTTP mode |

## Examples

> "Create a Bell state and sample it 1000 times"

> "What's the shortest error path in this surface code?"

> "Add 0.1% depolarizing noise and show me what changes"

## Development

```bash
uv sync
uv run pytest
```
