# GitHub Pages (lookdev)

Public camera: **https://kvnloo.github.io/smartcity/**

This is the mobile lookdev site in `site/`, not the Unreal/SUMO twin. CI on
`nightly` runs pytest + lookdev tests, builds with Vite `base: "./"`, and
deploys `site/dist` through GitHub Actions. `.nojekyll` lives in
`site/public` so the build copies it into the artifact. No repository secrets.

## After you click Create repository

You (the human) click **Create repository** on GitHub as public
**kvnloo/smartcity**. Do not let an agent create it. Push this tree (at least
`nightly`). Then enable Pages:

1. Open **https://github.com/kvnloo/smartcity**
2. Click the **Settings** tab under the repository name. If the tab is hidden, click the **⋯** dropdown → **Settings**.
3. In the left sidebar, in the **Code, planning, and automation** section, click **Pages**.
4. On the Pages screen, find **Build and deployment**.
5. Under **Source**, open the dropdown. It may say **Deploy from a branch**.
6. Click **GitHub Actions**. Do **not** click **Deploy from a branch**. Do **not** pick `gh-pages`, `main`, or `/docs`.
7. If GitHub lists workflow templates, skip them. This repo already ships `.github/workflows/verified-oss-loop.yml`.
8. Leave **Custom domain** empty.
9. Leave **Enforce HTTPS** checked (default for `*.github.io`).
10. If a **Save** button is shown, click **Save**. Some accounts persist the source as soon as you pick GitHub Actions.

That is the whole Settings path: **Settings → Pages → Source → GitHub Actions**.

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
