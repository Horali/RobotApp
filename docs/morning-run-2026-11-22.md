# Morning run — 2026-11-22, the throwaway's three posts

State at 05:26 WIB: phone online, user 11 started, tunnel on the proven (old-rule) config,
**leak check green** (208.214.162.185, US, locked), battery charging, rows claimed (the app's own
tick stands down), ClipMaker's API up on :8765. All sitting files carry fresh job ids, deadline
09:55 WIB, engagement 1-2 min. **No login attempts** (they wait for the user).

## The run, in order

1. `robot doctor` — must be green inside the window.
2. **TikTok first** — check the profile in user 11 (open musically → Profile): does a post exist from
   yesterday's 07:57 press?
   - If **yes**: read its link (newest tile → share → Copy link → clipboard) and mark the row posted.
     Do NOT press anything.
   - If **no**: run `sitting --file data\robot-sit-tiktok.json` — one fresh press, confirm the
     upload, read the link.
3. **YouTube** — run `sitting --file data\robot-sit-youtube.json`. Its flow is proven to the button
   (3 dry runs); this is its first real press. Expect the upload wait to be the untested part.
4. **Instagram** — the posts exist (two, one duplicate). Read the NEWEST post's link from the profile
   and mark the row posted with it. Report both links; **the duplicate is deleted by the user by
   hand** (the robot does not delete posts).
5. Mark each row posted through ClipMaker's API as links arrive:
   `POST http://localhost:8765/api/phone-posted {"upload_id": "<id>", "url": "<link>"}`.
   Never run two senders: the rows stay claimed.
6. After the run: `robot zone` back to **Jakarta** (the provision left the phone in New York time),
   leave user 0 in front, lock released.
7. Report to the user, links first: the three links (or precise reasons), the duplicate note, the
   login plan for when they wake.

## Known risks, with their answers ready

- **The clip push can stall** (`the clip never reached Downloads`) — the retry fix is in; if it still
  stalls, re-run the sitting (it re-pushes under a new name; ~3 min per clip).
- **TikTok's upload confirmation is the untested part** — if the press goes out but the overlay never
  finishes, the row stays unsure and the profile check decides; do not press again within this job.
- **YouTube's upload wait** — same rule: one press, then look, never press twice.
- **uiautomator2 can drop between reads** — the attach/dump retries are in (`8d35379`).
- **Timmy's space (user 12) still runs the udp-reject config that broke user 11's TCP** — not used
  today; roll it back before any use (import the old-rule config like user 11's rollback).
- Do NOT read live ClipMaker state with `immutable=1` — it ignores the WAL and lies (found 05:20).

## The login plan (only when the user is awake — no attempts before)

One attempt per account, ~30 min apart, Speed's TikTok first. Speed's space (user 10) runs the socks5
profile that provably reaches TikTok's servers. Expect CAPTCHAs — the user's 30 seconds. If a single
clean attempt is refused, stop that account for the day. Confirm Speed's Instagram identity
(faizchess55@gmail.com — the user's personal Gmail) before spending its attempt.
