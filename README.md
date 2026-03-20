# stim-mcp-server

An MCP server that exposes [Google's Stim](https://github.com/quantumlib/Stim) quantum stabilizer circuit simulator as tools for LLMs.

## Tools

| Tool | Description |
|------|-------------|
| `hello_quantum` | Health check — returns Stim version and active session count |
| `create_circuit` | Validate a Stim circuit string and open a persistent session |
| `append_operation` | Append one or more Stim instructions to an existing circuit |
| `sample_circuit` | Simulate a circuit and return measurement statistics |
| `analyze_errors` | Build the Detector Error Model and find shortest logical error paths |
| `get_circuit_diagram` | Return an ASCII diagram of the circuit |
| `inject_noise` | Add depolarizing or other noise to a circuit |

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

## Running locally

### Stdio (default — for local MCP clients)

```bash
uv run stim-mcp-server
```

Or install and run directly:

```bash
pip install .
stim-mcp-server
```

Add to your MCP client config:

```json
{
  "mcpServers": {
    "stim-mcp": {
      "command": "stim-mcp-server"
    }
  }
}
```

### HTTP (local SSE testing)

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

## Deploying to Google Cloud Run

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
`--min-instances 0` enables scale-to-zero for cost savings.

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_TRANSPORT` | `stdio` | Set to anything else (e.g. `sse`) to start the HTTP server |
| `MCP_HOST` | `0.0.0.0` | Bind address for HTTP mode |
| `MCP_PORT` | `8080` | Port for HTTP mode |

## Development

```bash
uv sync
uv run pytest
```
