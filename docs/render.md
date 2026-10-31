# Deploy the documentation MCP on Render

The Python service exposes three read-only tools over Streamable HTTP at `/mcp`:

| Tool | Purpose |
| --- | --- |
| `search_femora` | Search API, concept, and example references with bounded excerpts |
| `get_femora_api` | Return the exact documented symbol's signature and docs; absent APIs return `found=false` |
| `read_femora_reference` | Read an indexed document in bounded pages |

The service does not execute Python submitted by users, run Femora simulations, access arbitrary files or URLs, or submit HPC jobs. It needs no OpenAI API key or user login. Documentation is public.

## Data updates

The existing GitHub workflow generates `build/mcp/femora-knowledge.json` from the same references used by the skills. After successful build and MCP tests, a separate job publishes that JSON to the repository's `knowledge-latest` prerelease. The source-extraction job keeps a read-only token; only the publication job can write release assets. Pull requests cannot publish knowledge.

The server fetches this fixed public release asset on startup and every five minutes. It validates document hashes, paths, and the schema before replacing the in-memory snapshot. A failed refresh retains the last valid snapshot. Health remains unavailable (503) until the first valid snapshot is loaded. The health response and every tool response identify the Femora source commit.

The daily upstream check means upstream changes may take until the next scheduled build plus the refresh interval to appear. Run the build manually for faster updates. Hosting the documentation server does not update bundled skills or publish the ChatGPT directory listing.

## Before deploying

1. Merge this change and wait for Build AI packages and its publish-knowledge job to succeed. Confirm `knowledge-latest` contains `femora-knowledge.json` in GitHub Releases.
2. Create or sign in to your Render account and connect `GeotechUW/femora-ai`.
3. Use **New → Blueprint** to deploy the root `render.yaml`, or create a **Web Service** using Python, build command `pip install -r server/requirements.txt`, start command `uvicorn server.app:app --host 0.0.0.0 --port $PORT --no-access-log`, and health check `/healthz`.
4. The Blueprint selects the **free** plan for initial testing. Review Render's current plan and billing screen before confirming. No paid service is authorized by this configuration. Free instances sleep when inactive and can have cold-start delays; evaluate a suitable paid plan separately before public launch.
5. After deployment, open the service's actual `/healthz` URL and verify `ready: true`. Use that service's actual HTTPS `/mcp` endpoint when connecting a private test plugin. Do not guess the allocated hostname.

Render sets `RENDER_EXTERNAL_HOSTNAME`; the application uses it to allow the correct Host header while retaining DNS-rebinding protection. Local development hosts are also permitted. Add an explicitly configured custom domain to the allowlist before using one.

To complete OpenAI domain verification later, set `OPENAI_APPS_CHALLENGE` in Render to the exact public challenge text from the submission portal. The service returns that text at `/.well-known/openai-apps-challenge`; without it the route returns 404. Do not put passwords or credentials there.

## Local development and checks

```sh
python -m pip install -r server/requirements.txt
python -m unittest discover -s server/tests -v
python -m server.tests.smoke_http
```

To serve a locally generated snapshot, set `FEMORA_KNOWLEDGE_FILE` to the absolute path of `build/mcp/femora-knowledge.json`, then run Uvicorn. Tool arguments cannot change that path. The HTTP smoke test uses a small local fixture by default. Set `FEMORA_SMOKE_KNOWLEDGE` to the real generated JSON to exercise the full reference corpus.

## Submission is a separate step

Keep the existing private skills-only plugin for testing. OpenAI's dashboard currently rejects new skills-only submissions and its documented flow does not add MCP servers to an existing skills-only plugin. Prepare an MCP-capable submission using the real deployed endpoint; do not invent an endpoint or claim directory acceptance.

Before public submission, test the actual deployed service in the target host, verify the server domain, prepare the required MCP review cases and demo, and review the updated privacy disclosure. Skills can remain bundled alongside these tools. Public approval, publication, and platform updates remain separate from Render deployment.
