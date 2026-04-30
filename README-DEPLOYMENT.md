# Custom Qonto MCP — deployment guide for anzhe778

This adds two things to the upstream Qonto MCP:

1. **Extended `get_qonto_transactions`** — date filters, pagination, sort, side, includes.
2. **`create_transfer_request`** — stage a SEPA transfer that needs in-app approval.

## Step 1 — Fork upstream

Go to https://github.com/qonto/qonto-mcp-server and click **Fork** into your `anzhe778` account.

## Step 2 — Apply these files

Three files to drop into your fork (preserve directory layout):

```
qonto_mcp/tools/transactions/transactions.py    # REPLACE
qonto_mcp/tools/requests/__init__.py            # REPLACE
qonto_mcp/tools/requests/transfer_requests.py   # NEW
.github/workflows/ghcr.yml                      # NEW
```

You can either:
- Use GitHub web UI: open each file, paste, commit; create the new ones via "Add file > Create new file" and paste path + content.
- Or clone locally, copy these in, commit, push.

The existing `.github/workflows/docker.yml` (Docker Hub) can stay — it just won't run because it depends on a `DOCKERHUB_TOKEN` secret your fork doesn't have. Or delete it to keep things tidy.

## Step 3 — Make the package public (optional, recommended for first run)

After your first push, the Action will publish to `ghcr.io/anzhe778/qonto-mcp-server:latest`.
By default, ghcr packages are **private**. To pull from the NAS without needing a token,
go to your GitHub profile → Packages → `qonto-mcp-server` → Package settings → Change
visibility → Public. (The image only contains the open-source MCP code — your
QONTO_API_KEY lives in the NAS env vars, not in the image.)

If you'd rather keep it private, on the NAS run:

```
docker login ghcr.io -u anzhe778 -p <a GitHub PAT with read:packages>
```

Once. Then docker pulls will authenticate.

## Step 4 — Update QNAP container

In Container Station, edit the `qonto-mcp` application, replace the YAML with the
provided `docker-compose.yml` (image now points at `ghcr.io/anzhe778/qonto-mcp-server:latest`),
plug in your real `QONTO_API_KEY`, save & restart.

## Step 5 — Reconnect in Claude

Customize → Connectors → Qonto → Disconnect → Connect. The new tools appear in
the tool list once the session refreshes.

## Test it

After reconnect, ask Claude to:
- "Pull all credit-side transactions on Hauptkonto for April 2026, sorted ascending."
  Should now work in a single call without 100-row truncation.
- "Stage a €10 SEPA transfer to IBAN DE89370400440532013000, beneficiary 'Test', reference 'Test ignore'."
  Should return a JSON `request` object in `pending` status; you'll see it in the
  Qonto app awaiting approval.

## Endpoint caveat for `create_transfer_request`

The implementation targets `POST /v2/requests/transfers`. If Qonto returns 404 or 422
with an unexpected shape, the exact path or body shape may differ in your account's
API tier. Surface the error response here and we'll iterate — typical adjustments are:
- Path: `/v2/transfer_requests` instead of `/v2/requests/transfers`
- Body root key: `{ "transfer_request": {...} }` instead of `{ "request": {...} }`
- Replacing with `POST /v2/sepa_transfers` for direct SCA-approved transfer

The error path in the tool already echoes the Qonto response body, so debugging is
one round-trip away.
