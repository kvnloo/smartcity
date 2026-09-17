# GitHub Pages (lookdev)

Public camera: **https://kvnloo.github.io/smartcity/**

This is the mobile lookdev site in `site/`, not the Unreal/SUMO twin. CI on
`nightly` runs pytest + lookdev tests, builds with Vite `base: "./"`, and
deploys `site/dist` through GitHub Actions. `.nojekyll` lives in
`site/public` so the build copies it into the artifact. No repository secrets.

## GitHub home

Public repo: **https://github.com/kvnloo/smartcity** (default branch `nightly`).
Pages source is **GitHub Actions**, not `gh-pages` / `main` / `/docs`.

If Pages is ever reset:

1. Open **https://github.com/kvnloo/smartcity**
2. **Settings → Pages → Build and deployment → Source → GitHub Actions**.
3. Leave **Custom domain** empty. Leave **Enforce HTTPS** on.

## First publish

1. Confirm `nightly` exists on GitHub.
2. Click the **Actions** tab → workflow **verified-oss-loop** → the latest run on branch `nightly`.
3. **verify** must be green: pytest, `npm test` in `site/`, `npm run build`, then upload of `site/dist`.
4. **pages** deploys that artifact to the **github-pages** environment.
5. GitHub creates environment **github-pages** on first deploy. If the job waits, click **Review deployments** → **Approve and deploy**.
6. When **pages** is green, open **https://kvnloo.github.io/smartcity/**

Do not add an environment protection rule that only allows `main` or `master`.
This site publishes from **`nightly`**. If you add a rule, allow branch `nightly`.

## What stays as-is

- LICENSE: MIT
- CODEOWNERS: `@kvnloo`
- No `PAGES_TOKEN`, deploy keys, AWS keys, or other secrets
- pytest + lookdev CI stay in the same workflow
