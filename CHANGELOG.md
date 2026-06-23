# H5 Portfolio Rotation Backtest — Changelog

Interactive backtest explorer for M-Signal–driven ETF rotation against a SPY buy-and-hold baseline.
Runs 36,966 simulations across 366 exit-day and 101 allocation combinations (vectorised, ~2–4 min).

---

## v1 — Initial output (7 MB, 403 lines)

- First working HTML output from the vectorised simulation engine.
- Single static view: heatmap of final portfolio value across exit-day × allocation grid.
- Title: *H5 — Portfolio Rotation Backtest*.

## v2 — Data expansion (8.4 MB, +19%)

- Enlarged simulation dataset — likely extended OHLC date range or added tickers.
- Output structure unchanged (403 lines).

## v3 / v4 — Minor data revisions (~8.4 MB)

- Near-identical file size to v2; small corrections to underlying data or formatting.
- Byte-level diffs suggest config or label tweaks only.

## v5 — Major rebuild: M-Signal framing + equity curves (22 MB, 570 lines)

- Renamed to *H5 — M-Signal Portfolio Backtest*; reframed as signal-driven strategy, not generic rotation.
- File size tripled (~8 MB → 22 MB): added embedded equity-curve data for a grid of exit/alloc combinations.
- Added interactive Chart.js equity-curve panel alongside the heatmap.
- Introduced dark-mode CSS custom properties.

## v5.1 / v5.2 — UI polish (22 MB, 572–574 lines)

- Incremental UI fixes on the v5 layout (minor line-count growth).
- Likely tooltip or axis-label adjustments.

## v6 — Layout expansion: stats panel (22 MB, 805 lines)

- Added a statistics summary panel (CAGR, vol, beta, MDD, Sharpe) rendered alongside the chart.
- Line count grew from 570 → 805 (+235 lines): new HTML/JS sections for stats cards.

## v6.1 / v6.2 — Stats + controls (865 lines)

- Added interactive controls (exit-day slider, allocation slider) to drive the equity curve live.
- Stats panel wired to selected parameters.

## v6.3 / v6.4 — Refactor: leaner layout (666 lines, −24%)

- Significant code reduction (-199 lines vs v6.2) — layout refactored, possibly replaced manual HTML with a JS-generated component.
- Data payload unchanged (~22 MB).

## v6.5 – v6.8 — Iterative UI fixes (708–717 lines)

- Incremental additions: likely tooltip polish, axis formatting, responsiveness fixes.
- File sizes very stable (~22.005–22.006 MB).

## v6.10 — Table panel added (923 lines, +215 lines vs v6.8)

- Large line-count jump: added a ranked results table (top-N combinations by selected metric).
- Title started carrying version suffix in `<title>` tag from this point.

## v6.11 — Table refinements (933 lines)

- Minor additions to the table view.

## v6.12 — Benchmark comparison row (956 lines)

- Added SPY buy-and-hold benchmark as a comparison row/line in charts and table.

## v6.13 / v6.14 — Label / cosmetic fixes (956 lines)

- Near-identical size to v6.12; likely label text or colour tweaks.
- v6.15 title still reads "v6.14" — indicates v6.15 was a quick patch without title bump.

## v6.15 — Regression fix (932 lines, −24 lines)

- Minor line reduction: possibly removed a debug panel or unused code block.

## v6.16 — Metric selector (936 lines)

- Added a metric-selector control (choose between CAGR, Sharpe, MDD etc. to colour the heatmap).

## v6.17 — Final feature set (958 lines)

- Further additions: possibly RF-rate input (T-bill rate field was in the Python config) or additional stats.

## v6.18 / v6.19 — Final output (958 lines)

- Near-identical to v6.17; byte-level diff only — data refresh or minor label fix.
- **v6.19 is the production output.**

---

*Screenshots of all versions are in `screenshots/`.*
