# claude-warmup

A GitHub Actions cron job that sends one tiny message to Claude every hour, so a fresh 5-hour
usage window opens while you are away from your computer instead of starting whenever you happen
to sit down.

It does not give you more quota. It moves the quota you already have to a better time of day.

## The problem it solves

Claude subscription usage is metered in rolling 5-hour windows. A window opens the moment you send
your first message and nothing resets it early. So the phase of your entire day is set by whatever
time you happened to start.

Start at 9:40am and your windows are 9:40am-2:40pm and 2:40pm-7:40pm. Start at 11am and you get
11am-4pm. Neither is a choice you made; it is just whenever you got to your desk.

## How it works

The workflow pings Claude hourly from 6am to 8pm Eastern, and stops overnight. That overnight gap
is the important part: with no pings for ten hours, no window is open by morning, so the 6:17am
ping is always the one that anchors the day. Windows then land at roughly:

```
6am - 11am   |   11am - 4pm   |   4pm - 9pm
```

Two boundaries inside the working day means a long session draws on two windows' worth of quota
rather than one.

The ping itself is a single Haiku request — `Reply with the single word: ok` — which is about as
close to free as a request gets.

A few details that are deliberate rather than accidental:

- **Minute 17, not :00.** GitHub's free scheduler is busiest at the top of the hour and queued jobs
  are often delayed. An odd minute runs closer to on time.
- **Nothing after 8pm Eastern.** A 9:17pm ping would open an unwanted evening window and push the
  next morning's anchor off 6am.
- **`cancel-in-progress: false`.** A cancelled ping is a ping that never reached Claude, which
  defeats the whole point.
- **A rate-limit reply counts as success.** If Claude answers "rate limited", the request still
  landed, and landing is all the warmup needs.

The full reasoning lives in the comment block at the top of
[`.github/workflows/warmup.yml`](.github/workflows/warmup.yml).

## Set it up yourself

1. Fork or copy this repo. Keep it **public** — Actions minutes are free and unmetered on public
   repos, whereas hourly runs on a private repo burn roughly 900 of the 2,000 free minutes a month.
2. Generate a long-lived token on your own machine:
   ```
   claude setup-token
   ```
3. Add it to the repo as an Actions secret named `CLAUDE_CODE_OAUTH_TOKEN`
   (Settings → Secrets and variables → Actions), or from the CLI:
   ```
   gh secret set CLAUDE_CODE_OAUTH_TOKEN --repo <you>/claude-warmup
   ```
4. Edit the `cron` line in `warmup.yml` for your timezone. Cron is always UTC. The committed value
   `17 10-23,0 * * *` is 6:17am-8:17pm US Eastern Daylight Time (UTC-4).
5. Run it once by hand from the Actions tab (`Run workflow`) to confirm it works. A good run takes
   about 10 seconds and ends with `Warmup succeeded.`

Scheduled workflows only run from the default branch, so leave this on `main`.

## Maintenance you will actually need

- **Daylight Saving.** Cron has no timezone. When Eastern shifts to UTC-5 (2 Nov 2026), change the
  hours from `10-23,0` to `11-23,0-1` to hold the 6am anchor.
- **Token expiry.** The OAuth token is good for about a year. When it dies, runs start failing and
  GitHub emails you. Re-run `claude setup-token` and update the secret.
- **60-day dormancy.** GitHub disables scheduled workflows in repos with no commit activity for
  60 days. It warns you by email first and re-enabling is one button, but a commit every month or
  two avoids it entirely.
- **Unpinned install.** Each run does `npm install -g @anthropic-ai/claude-code`, so it always
  pulls the latest release. If the pings ever start failing for no obvious reason, an upstream
  release is the first thing to check.

## Things worth knowing

- **The pings do not show up in your history.** `--no-session-persistence` is set, and Claude Code
  transcripts are local files rather than cloud records. Nothing appears in Claude Desktop or on
  claude.ai. The only trace is the Actions run log.
- **GitHub's scheduler drops runs sometimes.** It is best-effort, not a guarantee. A dropped ping
  costs an hour of window time and shifts the phase, but the fixed 6am re-anchor means the damage
  never survives past the end of that day.
- **The 5-hour window is not the only limit.** There is also a weekly rolling cap, which is why
  pinging more aggressively than hourly is a bad trade: extra pings inside an already-open window
  achieve nothing and still count against the weekly ceiling.
