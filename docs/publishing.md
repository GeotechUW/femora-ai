# Building is separate from publishing

The GitHub workflow generates downloadable packages. It does not install them in your account, submit a public listing, or update users' installed plugins.

## ChatGPT

Use the generated `femora-chatgpt-<version>.zip` for the existing Femora plugin's supported update/submission workflow. Preserve its identity. The account's current private plugin is not linked automatically to this repository.

The template preserves the agreed publisher and worldwide targeting. It is a development package, not a completed public submission: the bundled icon is included; four published and verified listing URLs (overview, support, privacy, terms), publisher verification, and applicable attestations remain required. Do not add guessed URLs. The public page sources now live in `site/`, including support through this repository’s issue tracker. Enable GitHub Pages with the GitHub Actions source and run the Publish public pages workflow. Inspect the deployed pages, then run `python scripts/verify_listing.py --base-url ACTUAL_HTTPS_SITE_ROOT` to create a separate submission ZIP with verified URLs. Never use the normal development package as proof of completed public submission.

Before a public release, complete that metadata, bump `package_version` in `source.json`, build the packages, test representative prompts in the target host, then follow the platform's review/publication process. Build checks do not establish that generated code is scientifically valid or that a platform accepted the package.

## Claude Code

The generated Claude Code package places the manifest in `.claude-plugin/plugin.json` and the skill in `skills/femora/`. Extract it locally and test:

```sh
claude --plugin-dir /absolute/path/to/extracted/femora-plugin
```

The standalone `femora-skill-<version>.zip` contains `femora/SKILL.md` and its references for skill-compatible clients. Availability and installation differ across Claude products; this repository does not automatically upload or sync skills to claude.ai.

Official format references:
- https://code.claude.com/docs/en/plugins-reference
- https://code.claude.com/docs/en/skills

## Other assistants

Use `build/shared/femora` as the platform-neutral skill. Add a new package adapter using this same content. Do not hand-copy API documentation or claim a client is supported before testing its package format.

## GitHub Pages setup

In this repository, open Settings → Pages and choose **GitHub Actions** as the source. The `pages.yml` workflow deploys only the static `site/` directory. It does not modify femora.io. After enabling Pages, run **Actions → Publish public pages → Run workflow** if the initial push already ran. Use the deployment URL reported by that workflow.
