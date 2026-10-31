# Femora AI

Generate AI-assistant knowledge from [Femora](https://github.com/GeotechUW/Femora), then package the same references for ChatGPT, Claude Code, and skill-compatible clients.

## One source, generated packages

This repository reuses **Femora's existing `agent/build_knowledge.py`**. It does not maintain a second API extractor or hand-written copies of API signatures.

1. Resolve the Femora revision configured in `source.json`.
2. Verify the upstream generator against its reviewed SHA-256 hash.
3. Run that generator against a clean Femora checkout to extract the API, concepts, and examples.
4. Verify the upstream output hashes and split complete source sections into topic files, preserving section contents.
5. Combine the upstream modeling rules with a compact routing template.
6. Validate and build three archives from the same shared skill.

Generated knowledge stays in the ignored `build/` directory and CI artifacts. Maintain source documents and API code in Femora; maintain routing and platform metadata here.

## Build locally

Use Python 3.12 and Git. The Femora checkout must contain its full history for complete per-file commit provenance.

```sh
git clone https://github.com/GeotechUW/femora-ai.git
cd femora-ai
git clone https://github.com/GeotechUW/Femora.git .upstream
# Check out the ref in source.json (currently main) before building.
python -m venv .venv
# Linux/macOS; on Windows use .venv\Scripts\activate
. .venv/bin/activate
python -m pip install -e .upstream
python -m unittest discover -s tests -v
python scripts/build.py --source .upstream
python scripts/verify.py
```

Build outputs:

| Path | Purpose |
| --- | --- |
| `build/upstream-bundle/` | Original generator output and its manifest |
| `build/shared/femora/` | Compact skill plus topic references and provenance |
| `build/packages/chatgpt/` | ChatGPT plugin package |
| `build/packages/claude-code/` | Claude Code plugin package |
| `build/dist/` | Three ZIPs, including the standalone skill |
| `build/build-manifest.json` | Source revision and generated file hashes |

ZIP ordering, timestamps, and modes are fixed. Identical generated inputs produce identical archive bytes. Extraction also depends on Python, installed dependencies, and Git history; compare provenance when investigating differences.

## Automatic builds

The GitHub Actions workflow builds on pushes to `main`, pull requests, manual runs, and a daily schedule (09:23 UTC). It follows `source.json`, currently Femora `main`. To target a release instead, set `ref` to a release tag or exact commit. The daily run picks up source changes without a cross-repository token or modifications to the Femora repository. Unchanged source and packaging revisions reuse cached build files after checksum verification.

Download the packages from the workflow run's **Artifacts** section. Artifacts follow GitHub's configured retention; they are not permanent releases. A source change may take until the next daily run to be detected. For immediate builds, use **Actions → Build AI packages → Run workflow**.

If Femora changes its generator, the build deliberately stops. Review the new generator and update `generator_sha256` in `source.json`; do not bypass this check. Bump `package_version` before publishing a new platform release. Keep platform template versions synchronized for clarity; the build takes its effective version from `source.json`.

**Builds do not publish to ChatGPT, Claude, or users' installed plugins.** See [publishing and installation](docs/publishing.md) for the remaining platform-specific steps. The current private ChatGPT plugin remains unchanged. Host-specific installation and conversational behavior still need testing.

## Repository layout

- `source.json`: upstream revision, reviewed generator hash, package version.
- `templates/`: shared routing instructions; modeling rules come from the upstream generator.
- `platforms/`: small platform-specific manifests.
- `scripts/`: splitting, packaging, and integrity checks.
- `tests/`: content-preservation, corruption detection, and package reproducibility checks.
- `site/`: public overview, support, privacy, and terms pages.
- `assets/`: existing Femora branding bundled in the ChatGPT package.
- `.github/workflows/`: automated builds with a read-only repository token.

## Public submission status

This is a working build pipeline, not a published public plugin. The icon is bundled and the four static page sources are in `site/`. The Pages deployment workflow is configured; repository Settings → Pages must use GitHub Actions. Public URLs are added to a separate submission copy only after live verification. Publisher verification and platform review remain separate.

## Upstream and attribution

Femora is maintained by Amin Pakzad and contributors. The API references, concept guides, examples, and upstream generator retain their source attribution and commit provenance. Consult [Femora's license](https://github.com/GeotechUW/Femora/blob/main/LICENSE) for upstream material. This setup does not assign a new license to this repository.

- Website: https://femora.io/
- Source: https://github.com/GeotechUW/Femora
- AI package issues: https://github.com/GeotechUW/femora-ai/issues

## Optional Render MCP service

The read-only Python MCP service and its free-plan Render Blueprint are documented in [Deploy on Render](docs/render.md). It serves generated documentation through search, exact API lookup, and paginated reference tools. It does not run simulations. Deployment and a public MCP-capable submission remain separate from this source setup.
