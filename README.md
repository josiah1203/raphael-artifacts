# raphael-artifacts

Artifact CRUD, metadata, lifecycle, snapshots

## API

- Prefix: `/v1/artifacts`
- Port: `8084`
- Health: `GET /health`

## Events

_Published and consumed events documented in `openapi.yaml` and raphael-contracts._

## Development

```bash
uv sync
uv run uvicorn raphael_artifacts.app:app --reload --port 8084
```

Part of the [Raphael Platform](https://github.com/hummingbird-labs) by HummingBird Labs.
