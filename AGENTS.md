# Notes for agents — smartcity

You are a contributor, not a maintainer. Workers open PRs. They never merge `main` or `dev`.

This project follows the [Verified OSS Loop](https://github.com/kvnloo/verified-oss-loop). Issues are not claims. AI work is untrusted until proven.

## Surfaces

| Path | What | Tests |
| --- | --- | --- |
| `site/` | Mobile GitHub Pages lookdev (MapLibre, device LOD). **Not the sim.** | `npm test --prefix site` |
| `smartcity/` | Nested twin, tidal lanes, 8 km SUMO/mock TraCI, FastAPI ops map | `python -m pytest -q` |
| `src/` | Next.js cinematic intersection | visual; no unit script yet |
| `unreal/`, Blender scripts | Hero street. **Unreal** + Blender (not Unity) | pipeline docs, not this page |

Galaxy S25 Ultra (`SM-S938`) gets ultra LOD (terrain + extruded OSM). Other phones load less. Do not put SUMO/Unreal in `site/`. Hero renderer is Unreal, not Unity.

## First 60 seconds

1. Read this file, then `CONTRIBUTING.md`.
2. `git fetch origin`. `python3 .verified-oss-loop/rollout.py show`. Branch from `origin/$(python3 .verified-oss-loop/rollout.py get worker_base)` unless the issue names another base. Day-pass PRs target `feature_target`. Overnight unattended PRs target `overnight_target`. See [rollout](https://github.com/kvnloo/verified-oss-loop/blob/main/docs/rollout.md).
3. Search open issues and PRs. Do not duplicate in-flight work.
4. Orient (`skills/orient/SKILL.md`). Else `rg` + read.

```bash
gh issue list --label claimable --state open
gh pr list --state open
```

## Pick and claim

Take **one** open issue labeled `claimable` and not `claimed`. Prefer `priority:P0`, then `P1`, then `good-first-issue`. Skip `needs-discussion` unless a human assigned it.

If nothing is `claimable`: do not code. **Triage** — if a `needs-discussion` issue exists: one-paragraph proposal on the newest; stop. If none: mint **exactly one** issue from the first untracked item in `ROADMAP.md`, else a failing unit command from this file, else docs drift; label **`needs-discussion` only**; stop. Do not self-apply `claimable`. Do not rewrite `ROADMAP.md`. **Stop** if triage found nothing untracked, a live claim exists, a competing PR covers the scope, or secrets are required.

Claim comment (24h lease unless the project says otherwise):

```text
claiming for autodevelop
claimant: <github login or agent id>
base: <git rev-parse origin/$(python3 .verified-oss-loop/rollout.py get worker_base)>
expires: <now + 24h UTC>
scope: <one sentence>
```

Then add `claimed` and remove `claimable`. If a claim newer than 24h exists, pick a different issue.

## Proof

Do not invent a mutation score. This tree is mixed Python + lookdev TS; Stryker is not wired.

| Layer | Command |
|---|---|
| Unit | `./.verified-oss-loop/verify.sh` |
| Mutation | `n/a` |
| Runtime | lookdev: `npm run dev --prefix site` (port 43180). Twin: `smartcity serve` |

1. Name the intended vs current behavior.
2. Fail, then pass (`skills/tdd/SKILL.md`). Lookdev contracts live in `site/src/*.test.ts`.
3. Keep the smallest complete change (`skills/anti-slop/SKILL.md`).
4. Run unit tests on the touched surface.
5. Open a PR at `feature_target` (or `overnight_target` if unattended overnight). Fill `.github/PULL_REQUEST_TEMPLATE.md`. Never merge `main` or `dev`.
6. Independent review bots are review, not merge.

## Do not

- Commit secrets, tokens, `.env`, or pairing files.
- Merge `main` or `dev`.
- Redefine the roadmap.
- Claim mutation coverage that the stack cannot run.
- Overwrite `LICENSE`.
- Treat GitHub Pages as the digital twin. It is a camera.
- Duplicate this file into `CLAUDE.md` / `GEMINI.md` / copilot-instructions.

<!-- BEGIN:nextjs-agent-rules -->

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->
