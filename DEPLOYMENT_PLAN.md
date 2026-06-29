# Phase 6 continued: Deploy

Status as of commit `00b9e4b`: the cinematic site (`site/`) is feature-complete
(7 movements + dashboard hand-off), production build passes
(`npm run build` in `site/`), and the recommendation demo works end-to-end
against a locally-run API. Nothing has been deployed yet. This is the plan
to get both pieces live.

## Open decision before deploying: cold-start cost

`recommendations/serve.py: train_recommender_state()` calls `load_events()`,
which runs a live SQL query against Supabase Postgres (needs `DATABASE_URL`)
*before* training ALS + the LightGBM ranker. So the real cold-start cost on
Render is:

```
Supabase free-tier query time  +  model training time
   (measured 40-150s in Phase 4)    (~2 min per code comment;
                                      measured <1s locally, but
                                      Render's free CPU is far
                                      weaker than a dev machine)
```

Render's free tier also spins the service down after ~15 min idle, so this
isn't a one-time cost — it's "every first visitor after a quiet period pays
this," and the current frontend (`RecommendationDemo.tsx`) only tells the
user to retry after ~30s, which may not be enough.

**Decide one of these before deploying:**
1. Ship as-is, accept that the live demo may take a while to wake up, adjust
   the frontend copy to set that expectation honestly (e.g. "first request
   after idle can take 1-3 minutes").
2. Cache the trained model artifacts (e.g. pickle to disk or blob storage)
   so a cold start loads instead of retrains — only worth it if cold starts
   turn out to be painfully slow in practice.
3. Pay for a Render tier that doesn't spin down (defeats the "free-tier"
   constraint from the original plan, but is the simplest fix if the demo
   needs to feel snappy for hiring-manager-grade first impressions).

Recommendation: try option 1 first, deployed for real, and measure actual
cold-start time before deciding whether 2 or 3 is worth the effort.

## Step 1 — Deploy the API to Render

1. Create a new **Web Service** on Render, pointed at this repo.
2. Root directory: repo root (not `api/` — `api/main.py` imports from
   `recommendations/`, which lives at the repo root).
3. Runtime: Python. Build command: `pip install -r requirements.txt`.
4. Start command: `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
5. Environment variable: `DATABASE_URL` — the same Supabase Postgres
   connection string used locally (check `metrics/db.py` / `.env` locally
   for the exact value; do not commit it).
6. Deploy, then watch the boot logs for:
   - the SQL query running (no errors connecting to Supabase from Render's
     network — this hasn't been tested and could surface IP allowlist /
     SSL-mode issues Supabase didn't have locally)
   - "Training recommendation models..." → "Recommendation models ready."
7. Once live, hit `https://<your-service>.onrender.com/health` and
   `https://<your-service>.onrender.com/recommend?user_id=7493&n=5` directly
   to confirm both work before touching the frontend.
8. **Note the resulting URL** — needed in Step 2.

## Step 2 — Deploy the site to Vercel

1. Import this repo into Vercel.
2. **Root Directory: `site/`** — this is a monorepo; if Vercel tries to
   build from the repo root it will fail to find `package.json`.
3. Framework preset: Next.js (should auto-detect).
4. Environment variable: `NEXT_PUBLIC_API_URL` = the Render URL from Step 1
   (no trailing slash — `RecommendationDemo.tsx` appends `/recommend?...`
   directly).
5. Optional: `NEXT_PUBLIC_DASHBOARD_URL` if a separate Streamlit dashboard
   deployment exists. If unset, `Sidebar.tsx` falls back to the GitHub repo
   URL, which is a reasonable default.
6. Deploy. Note the resulting `*.vercel.app` URL.

## Step 3 — Post-deploy verification

Everything below was only verified against `localhost:3000` + a locally-run
API this session. Production CDN/edge behavior, font loading, and the
cross-origin fetch to Render are all unverified — check all of it fresh:

- [ ] Scroll through the full cinematic homepage on the deployed URL,
      start to finish. Pay particular attention to Movement 7's hand-off
      (the dashboard mounts dynamically and calls `resyncLenis()` to fix a
      Lenis scroll-height-caching bug found this session — only tested in
      Next dev mode, not a deployed production build).
- [ ] Confirm the live recommendation demo on `/recommendations` works
      against the *deployed* Render API (not localhost) — expect the first
      request to be slow per the cold-start note above; confirm it
      eventually succeeds rather than just timing out.
- [ ] Confirm `/dashboard`, `/retention`, `/funnels`, `/growth`,
      `/experiments`, `/recommendations` all load directly (not just via
      in-page navigation) — Vercel's static generation should handle this,
      but worth confirming.
- [ ] Confirm "GitHub" and "Full Streamlit dashboard" links in the sidebar
      go somewhere real.
- [ ] Quick mobile/narrow-viewport pass. The cinematic movements were built
      desktop-first per an earlier decision in this project — there is
      **no mobile fallback** for Movements 1/3/5 specifically (the ones
      with the heaviest custom physics/layout work). Confirm at minimum
      that mobile doesn't outright break (e.g. check it's at least
      readable/scrollable), even if the experience is acknowledged as
      degraded there.

## Known gaps (not blocking deploy, worth tracking)

- No `prefers-reduced-motion` handling for the GSAP-driven cinematic
  movements specifically (Framer Motion content elsewhere is covered via
  `MotionConfig`, but the 7 Movement components are not).
- No mobile-simplified versions of Movements 1, 3, 5.
- No `docker-compose.yml` for local dev (Postgres + api + Streamlit) or
  `.env.example` — both were in the original Phase 6 plan, deferred.
- README has not been rewritten with the new architecture / live URLs.
- `site/data/snapshot.json` is baked in at build time; re-run
  `snapshot/build_snapshot.py` and redeploy whenever the underlying data
  changes — there's no live re-sync.
