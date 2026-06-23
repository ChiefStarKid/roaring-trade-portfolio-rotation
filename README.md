# H5 — M-Signal Portfolio Rotation Backtest

Interactive HTML backtest explorer for M-Signal-driven ETF rotation vs SPY buy-and-hold.

- **36,966 simulations** across 366 exit-day x 101 allocation combinations (vectorised, ~2-4 min)
- Excludes broad-market ETFs (QQQ, DIA, IWM, SPY); sector ETFs only
- Metrics: CAGR, Volatility, Beta, Max Drawdown, Sharpe
- Charts: heatmap, equity curves, ranked results table

## Files

| File | Description |
|---|---|
| `05_portfolio_rotation.py` | Source — runs the simulation and outputs the HTML |
| `05_portfolio_rotation_v6.19.html` | Latest interactive report (open in browser) |
| `CHANGELOG.md` | Full version history |
| `_archive/screenshots/` | Screenshots of all 26 versions |

## Version history

See [CHANGELOG.md](CHANGELOG.md) or `git log` for the full evolution.
