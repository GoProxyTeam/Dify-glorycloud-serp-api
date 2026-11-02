# GloryCloud SERP API development and release guide

End-user instructions belong in `README.md` and `readme/README_zh_Hans.md`. This file is for maintainers and is excluded from plugin packages.

## Version 0.0.1 tools

The provider registers exactly five independent tools with a shared `api_key` credential:

| Tool ID | Display name | Python and YAML files |
|---|---|---|
| `google_search` | Google Web Search | `tools/google_search.*` |
| `google_image` | Google Image Search | `tools/google_image.*` |
| `google_shopping` | Google Shopping Search | `tools/google_shopping.*` |
| `google_news` | Google News Search | `tools/google_news.*` |
| `google_maps` | Google Maps Search | `tools/google_maps.*` |

Each wrapper fixes the engine in code. Manifests contain only their applicable fields and have no `engine` selector. Web/images/shopping expose 8 fields, news 9, maps 13. Maps `maxResults` is capped at 40 in the form and client; the others are capped at 100. Files import `Tool` and the shared `search` function directly so the SDK discovers exactly one subclass in each source file.

Version 0.0.1 is the first Marketplace release and uses the production HTTPS endpoint. The combined `glorycloud-serp-api` tool from earlier local development packages is no longer registered. Existing nodes from local version 0.1.0 or earlier must be replaced with the appropriate independent tool and downstream references rebound. Provider identity and credential schema remain the same. Authentication and the result envelope retain the goproxy protocol.

Detailed README parameter tables are replaced by the verified official documentation link: `https://docs.glorycloud.com/api-reference/SERP-API/Use?link=1142bb`. The README retains a five-tool capability list, workflow example, output instructions and migration guidance.

## goproxy protocol

- Fixed API base: `https://serpapi.glorycloud.com` (production service).
- POST `/api/serp/google_search`, `/google_image`, `/google_shopping`, `/google_news` or `/google_maps` under the same `/api/serp/` prefix.
- Authenticate with the customer's `X-Api-Key` header. The engine belongs in the path, never the JSON body. Do not send `X-Biz-Id` or trial/service credentials.
- Successful responses use `code: 0` and `data: {requestId, engine, resultCount, result}`. Preserve the entire result; do not transform vendor fields.
- Saving credentials validates local format only. API access is checked during invocation.
- Search input is built from known, active form fields; the body is capped at 64 KiB. Invalid inputs fail before sending a billable request.
- No automatic retries or redirects. Read timeout is 90 seconds. API code 1517/HTTP 504 and transport timeouts explain potential billing and advise against immediate retry.

The original protocol snapshot and live records are in the parent directory under `verification/2026-10-26-goproxy/`; five-tool verification is under `verification/2026-10-26-five-tools/`. The source protocol was the goproxy section of the shared UDMS API manual supplied by the user; the link's original fragment pointed at the separate GloryCloud protocol, which was not selected.

## Migration from local development package 0.0.2

| Old | New |
|---|---|
| `https://api.glorycloud.com/go-serpapi-server/open/consume` | `https://serpapi.glorycloud.com/api/serp/{engine}` |
| Header `apiKey` | Header `X-Api-Key` |
| Only Google web search | Five independent tools |
| `gl` | UI `location`, sent as `options.location` (except maps) |
| `lang` | `language` |
| `domain`, `page` at the top level | `options.domain`, `options.page` (except maps) |
| `hostLang`, `retry` | Removed; reconfigure old workflow nodes |
| Success `code: 200`, results in `data` | Success `code: 0`, results in `data.result` |

Do not silently reinterpret old workflows. Unknown/legacy parameters produce a reconfiguration instruction. Each current tool exposes its own applicable parameters.

## Setup and tests

Use Python 3.12+ and install `requirements.txt`. Dependencies must also match `pyproject.toml`.

```bash
python3 -m pip install -r requirements.txt
python3 -m unittest discover -s tests -v
```

Tests use the real Dify provider/tool classes and replace only the HTTP transport. They need no real key and consume no quota. In the provided workspace, dependencies are available under `/tmp/glorycloud-plugin-deps`; set `PYTHONPATH` to that directory when running tests.

For live tests, use only a key authorized for this service, keep it outside the source tree, and avoid repeating timed-out requests. Never commit a key, copy it to a response fixture, or print request headers. The workspace host has invalid IPv6 CIDR patterns in its proxy exclusion environment; the recorded live check removed proxy variables for that test process. This is not a change to the plugin's Dify runtime networking.

## Remote debugging

Copy `.env.example` to `.env`, then set `REMOTE_INSTALL_URL` and `REMOTE_INSTALL_KEY` to the values shown by your own Dify instance. Run `python -m main`.

The Dify remote-install key is separate from the GloryCloud API Key entered in the plugin's authorization dialog. Do not include `.env` in a package.

## Packaging

From the plugin source root (the directory containing `manifest.yaml`):

```bash
dify plugin package . -o ../glorycloud-serp-api-0.0.1.difypkg
```

Keep the version synchronized in `manifest.yaml` and `pyproject.toml`. `meta.version` is the manifest format version and does not track the plugin release. The network domain in the manifest and the endpoint in `PRIVACY.md` must match the actual client destination.

Tests, this guide, workflows, caches, local settings and secrets are excluded through `.difyignore`. Preserve the old 0.0.2, 0.1.0 and 0.2.0 packages and source backups in the parent directory. Keep verification files and design documents outside the packaged plugin tree.

## Marketplace release

Packaging, SDK invocation and HTTP checks do not constitute installation or visual validation in a real Dify workspace. Before public submission, upload the current source to [GoProxyTeam/Dify-glorycloud-serp-api](https://github.com/GoProxyTeam/Dify-glorycloud-serp-api), confirm that support@glorycloud.com is monitored, review privacy, and follow the current [official submission requirements](https://docs.dify.ai/en/develop-plugin/publishing/marketplace-listing/submit-plugin-to-marketplace).

This task does not publish to Marketplace or create a submission PR. Keep developer validation status in release records, not in the customer-facing README.
