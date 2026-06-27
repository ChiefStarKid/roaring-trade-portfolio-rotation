# ETF Sector Rotation Backtest — M-Signal Portfolio Rotation

An interactive HTML backtest explorer that tests a momentum signal (M-Signal) against SPY buy-and-hold across every major US sector ETF.

The simulation runs **36,966 combinations** — 366 exit-day windows × 101 allocation steps — vectorised in Python in 2–4 minutes, then renders as a standalone HTML report you can open in any browser. No server, no dependencies, no API keys.

---

## What this answers

**Can a momentum-based rotation strategy beat SPY buy-and-hold?**

The backtest compares M-Signal-driven sector rotation against a passive SPY position across every permutation of:
- Exit day (day 1–366 of the holding period)
- Allocation weight (0–100% in 1pp steps)

Results are ranked by Sharpe ratio, CAGR, volatility, beta, and max drawdown. The heatmap makes the sweet spots visible at a glance.

---

## Common questions

**What is M-Signal?**
M-Signal is a momentum ranking signal that scores sector ETFs by relative strength. The rotation logic buys the highest-ranked sectors and exits when the signal degrades. Broad-market ETFs (SPY, QQQ, DIA, IWM) are excluded — this is a sector-only strategy.

**How do I run the backtest?**
Run  in Python. It outputs a self-contained HTML file. Open that file in any browser. The interactive heatmap and equity curves update in real time as you adjust parameters.

**How do I read the results?**
The HTML report has three panels: a parameter heatmap (colour = Sharpe), an equity curve for the selected combination, and a ranked results table. Click any cell in the heatmap to load its equity curve.

**What ETFs are in the universe?**
US sector ETFs only (XLK, XLV, XLE, XLF, XLI, XLC, XLY, XLP, XLB, XLRE, XLU and equivalents). Broad-market ETFs are excluded from the rotation universe by design — they would absorb allocation without providing the sector divergence the signal exploits.

**What time period does the backtest cover?**
See the CHANGELOG for the current data range. The Python source reads from a local price database — you can extend it by pointing at your own price history.

---

## Files

| File | Description |
|---|---|
|  | Source — runs the simulation and outputs the HTML |
|  | Latest interactive report (open in browser) |
|  | Full version history |
|  | Screenshots of all 26 versions |

---

## Version history

See [CHANGELOG.md](CHANGELOG.md) or commit 5ed6722ffc1706922609f0ff7d298eef55fc56c6
Author: Joseph Solomon <joseph@kainosis.com>
Date:   Sat Jun 27 15:00:07 2026 +0800

    feat(loop-back): detect bypass mode, ask permission, switch off before send

commit 5288fa25694bc1f835584bb0a1a097fe5a624c7e
Author: Joseph Solomon <joseph@kainosis.com>
Date:   Thu Jun 18 15:07:23 2026 +0800

    chore: retire joe-skill-build wrapper; fold gates into memory
    
    Delete the joe-skill-build command (thin wrapper over Anthropic skill-creator) and capture its two quality gates (adjacent use-case check, fresh-session verification) as feedback memory so they apply regardless of entry point.
    
    Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>

commit f369a831c51688d8e0f4bd269493cd6d7865c3ed
Author: Joseph Solomon <joseph@kainosis.com>
Date:   Sat Jun 13 18:22:25 2026 +0800

    chore: snapshot files before system-audit 2026-06-13 edits

commit b9c0b2fd0ce06be0969a2816f7bfebe92ac722de
Author: Joseph Solomon <joseph@kainosis.com>
Date:   Sat Jun 13 14:23:25 2026 +0800

    chore: snapshot memory wiki + KM commands before retrieval refactor (Plan C)
    
    Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>

commit 27291cb54d904bd3ac14f9060f4cd2167def74ba
Author: Joseph Solomon <joseph@kainosis.com>
Date:   Sat Jun 13 14:01:03 2026 +0800

    feat: rebuild memory wiki as hub-and-spoke graph (Plan A)
    
    - Add [[ ]] links across 84 files: 5 hubs + 60 spokes + 19 laterals
    - Fix 5 hyphen/underscore dead links
    - Retroactive verification sweep: fix 5 stale paths/refs
    - Add Wiki Hubs legend to MEMORY.md
    - Islands 83 -> 2 (universal rules, by design); 0 dead links
    
    Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>

commit 800fcc0b58cf42da7b1a6a3d748ad90df3b3baad
Author: Joseph Solomon <joseph@kainosis.com>
Date:   Sat Jun 13 13:54:55 2026 +0800

    chore: snapshot memory wiki before librarian rebuild (Plan A)
    
    Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>

commit bfc7e16fb677bd25a034364722f33109a1b95c90
Author: Joseph Solomon <joseph@kainosis.com>
Date:   Thu Jun 11 12:53:11 2026 +0800

    chore: snapshot assessor prompt + script before TC pipeline redesign
    
    Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>

commit 63718d49ce55fefcc05b231fa676cfb645921de1
Author: Joseph Solomon <joseph@kainosis.com>
Date:   Sun May 31 15:10:48 2026 +0800

    chore: delete stale stride-bug memory file; commit config snapshot
    
    Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

commit 7c590471611158e8997bbf0621a8dc8365aba205
Author: Joseph Solomon <joseph@kainosis.com>
Date:   Sun May 31 15:09:02 2026 +0800

    docs: update reference_km_command.md — km-auto is a prompt template, not a skill
    
    Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

commit 73f2ca3572aa724b2af7dec7e260d2f6cb519987
Author: Joseph Solomon <joseph@kainosis.com>
Date:   Sun May 31 15:06:09 2026 +0800

    fix: update km-defer path reference after moving km-auto out of commands/
    
    Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

commit a8b27bc69eaa793640e2c49205e9e1adec3b9895
Author: Joseph Solomon <joseph@kainosis.com>
Date:   Sun May 31 15:04:25 2026 +0800

    chore: move joe-km-auto out of commands/ to reduce injected skills list
    
    Scheduled task invokes it directly; never typed manually. Stays versioned
    at .claude/joe-km-auto.md.
    
    Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

commit 24281e111af3b8cf8f85d06eacd8734c8d454831
Author: Joseph Solomon <joseph@kainosis.com>
Date:   Sun May 31 14:59:13 2026 +0800

    chore: trim CLAUDE.md and remove stale MEMORY.md entry
    
    CLAUDE.md: 55 → 20 lines. Removed bullets duplicated by memory feedback
    files (Q&A mode, track-changes, browser rules, output style, folders,
    tools section). Kept plan-mode entry instruction, mode-as-intent-signal,
    AskUserQuestion behaviour. Removed remote control warning.
    
    MEMORY.md: removed stale stride-bug entry (FIXED 2026-05-30).
    
    Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

commit 41f2b3ffc89a013f2794d92641111527ffcc4950
Author: Joseph Solomon <joseph@kainosis.com>
Date:   Sun May 31 14:48:46 2026 +0800

    chore: add .claude/.gitignore and stage scripts + memory files
    
    Eliminates ~22k untracked files from gitStatus (runtime dirs, browser
    profiles, session transcript UUID dirs, data outputs). Stages 98 Python
    scripts, PS1/sh scripts, all memory files, and plans/ for tracking.
    
    Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

commit f349a9d522f4f49f7f715c751c4b87789657db0c
Author: Joseph Solomon <joseph@kainosis.com>
Date:   Fri May 29 19:50:43 2026 +0800

    refactor: improve system-audit command and CLAUDE.md plan-mode entry
    
    - joe-system-audit: defer Plan Mode to Step 6 (write phase only); remove
      mid-audit permission gate; add skill scriptability assessment table
    - CLAUDE.md: load all 3 plan-mode tools in one ToolSearch round-trip
    - .config.json: clear stale GrowthBook feature flag cache
    
    Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

commit 6ed9d4d8f5d25bfa17fb1e4d07ea8344f35cf06d
Author: Joseph Solomon <joseph@kainosis.com>
Date:   Thu May 28 15:54:59 2026 +0800

    refactor: rename all js-* commands to joe- prefix
    
    Avoids CC session labeller interpreting "js" as "JavaScript".
    Also fixes joe-system-audit to gate transcript searches behind a
    single AskUserQuestion popup instead of prompting per-call.
    
    Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

commit 9315d0da2b15c9bd7623eeb76d2ddb527fabedca
Author: Joseph Solomon <joseph@kainosis.com>
Date:   Thu May 28 12:59:56 2026 +0800

    chore: snapshot config before system-audit edits 2026-05-28

commit b6c0affa3c83bc1cf2d082ffd8e75b330f6302a5
Author: Joseph Solomon <joseph@kainosis.com>
Date:   Thu May 21 22:18:30 2026 +0800

    chore: snapshot .config.json before re-enabling Remote Control
    
    remoteEnabled was set to false on 2026-05-15 as part of RC disable.
    This commit preserves the prior state before flipping it back to true.

commit aa326e78d14f1123aae970dfff7cd5f2bbc92fd1
Author: Joseph Solomon <joseph@kainosis.com>
Date:   Thu May 21 16:13:29 2026 +0800

    fix: correct track-changes markup convention in CLAUDE.md
    
    Replace inline-code backtick format with **bold** for new/changed content
    in plan file track-changes guidance — matches feedback_track_changes.md
    and Plan Preview rendering behaviour.
    
    Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>

commit ed45b81e65ee60e093cac2bdbcda462f38635ad3
Author: Joseph Solomon <joseph@kainosis.com>
Date:   Fri May 15 19:26:39 2026 +0800

    initial for the full evolution across 26 versions.

---

## Caveats

This is a backtested simulation, not live trading. Past results do not predict future performance. The M-Signal is a proprietary momentum construct — this repo exposes the backtest tooling, not the live signal calculation.

---

## Related

- [etf-momentum-analytics](https://github.com/ChiefStarKid/etf-momentum-analytics) — the broader momentum analytics and signal quality testing suite this rotation backtest sits within
