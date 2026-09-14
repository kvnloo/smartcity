# verified-oss-loop onboarding

This repo was onboarded with the kit at
[kvnloo/verified-oss-loop](https://github.com/kvnloo/verified-oss-loop):

```bash
./bin/oss-onboard /path/to/smartcity --name smartcity --owner kvnloo --repo smartcity \
  --with-automation --scheme rolling
```

Scheme is **rolling**: workers branch from `nightly`, day-pass PRs target
`preview`, overnight PRs target `nightly`. Humans merge `dev` and `main`.

Local extras (never overwritten by re-onboard if marked `local`):

- `verify.sh` — pytest + lookdev Vitest + `site` production build
- `config.yaml` — Pages source `site/dist` from `nightly`
- `.github/workflows/verified-oss-loop.yml` — CI + GitHub Pages artifact

Expected Pages URL after the public GitHub repo exists:

`https://kvnloo.github.io/smartcity/`

Maintainer clicks after Create repo: [docs/PAGES.md](../docs/PAGES.md)
(Settings → Pages → Source → GitHub Actions). No secrets.
