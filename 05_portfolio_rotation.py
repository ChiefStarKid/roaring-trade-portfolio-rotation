"""
H5 — Portfolio Rotation Backtest
==================================
Base:          $100k SPY, buy-and-hold from first OHLC date.
M-Signal Port: $100k SPY. On each M signal (sector ETFs only, excl QQQ/DIA/IWM/SPY):
               sell alloc% of $100k of SPY, enter ETF at T0+1 close.
               Exit after N trading days, re-enter SPY.
               Skip if SPY balance < position size.

Pre-computed across:
  exit_day : d0..d365   (1-day steps, 366 values)
  alloc    : 0%..100%   (1% steps, 101 values)
  = 36,966 simulations (vectorized, ~2-4 min)

Output: H5_portfolio_rotation/05_portfolio_rotation_vN.html
"""

import os, sys, pickle, subprocess, warnings, heapq, time, glob as _glob
import datetime
import numpy as np
import pandas as pd
import json

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
TOKEN_PATH  = r"C:/Users/Third Sight/.config/gspread/token.pickle"
REAUTH      = r"C:/Users/Third Sight/.claude/gspread_reauth.py"

_HERE       = os.path.dirname(os.path.abspath(__file__))
SIGNALS_CSV = os.path.join(_HERE, "..", "H4_optimal_hold", "04_m_optimal_hold.csv")
OHLC_ID     = "1gUpB56Qa0Hb8hfFF3js24fRtUCprYwtzMSzS7zhdf1I"
OHLC_GID    = 1116658394
OUT_BASE    = os.path.join(_HERE, "05_portfolio_rotation")

EXCLUDE     = {"QQQ", "DIA", "IWM", "SPY"}
INITIAL     = 100_000.0
RF_DEFAULT  = 4.5   # % annualised (US T-bill)

EXIT_FINE   = list(range(0, 366))        # d0..d365 (366)
ALLOC_FINE  = list(range(0, 101))        # 0%..100% (101)
EXIT_CHART  = list(range(0, 361, 10))    # d0,d10,...d360 for equity curves (37)
ALLOC_CHART = list(range(0, 101, 5))     # 0%,5%,...100% for equity curves (21)
EXIT_CHART_S  = set(EXIT_CHART)
ALLOC_CHART_S = set(ALLOC_CHART)


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------
def _gc():
    import gspread
    with open(TOKEN_PATH, "rb") as f:
        creds = pickle.load(f)
    return gspread.authorize(creds)


def _open_ws(gc, sheet_id, gid):
    import google.auth.exceptions, gspread
    try:
        sh = gc.open_by_key(sheet_id)
    except google.auth.exceptions.RefreshError:
        subprocess.run([sys.executable, REAUTH], check=True)
        with open(TOKEN_PATH, "rb") as f:
            creds = pickle.load(f)
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(sheet_id)
    return sh.get_worksheet_by_id(gid)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
def load_signals():
    df = pd.read_csv(SIGNALS_CSV)
    df["T0"] = pd.to_datetime(df["T0"])
    df = df[~df["Ticker"].isin(EXCLUDE)].copy()
    df = (df[["Ticker", "T0"]]
          .drop_duplicates()
          .sort_values("T0")
          .reset_index(drop=True))
    print(f"  Signals: {len(df)} events | tickers: {sorted(df['Ticker'].unique())}")
    return df


def load_ohlc():
    gc  = _gc()
    ws  = _open_ws(gc, OHLC_ID, OHLC_GID)
    raw = ws.get_all_values()
    hdr = [c.strip() for c in raw[0]]
    df  = pd.DataFrame(raw[1:], columns=hdr)
    date_col   = next(c for c in df.columns if c.lower() == "date")
    ticker_col = next(c for c in df.columns if c.lower() in {"symbol", "ticker"})
    close_col  = next(c for c in df.columns if c.lower() == "close")
    df[date_col]  = pd.to_datetime(df[date_col], errors="coerce")
    df[close_col] = pd.to_numeric(
        df[close_col].astype(str).str.replace(",", ""), errors="coerce"
    )
    close = df.pivot_table(
        index=date_col, columns=ticker_col, values=close_col, aggfunc="last"
    ).sort_index()
    print(f"  OHLC: {close.shape[0]} dates x {close.shape[1]} tickers  "
          f"({close.index[0].date()} to {close.index[-1].date()})")
    return close


# ---------------------------------------------------------------------------
# Vectorized simulation
# ---------------------------------------------------------------------------
def simulate_fast(entry_map, n, close_arr, spy_col, ticker_col_map, exit_n, pos_size):
    """
    Event-based simulation (not a day-by-day loop).
    SPY units tracked at discrete event days; position equity computed via numpy slices.
    ~50-100x faster than the day-by-day approach.
    """
    spy_prices    = close_arr[:, spy_col]
    spy_units_cur = INITIAL / spy_prices[0]

    entered    = []           # (entry_i, exit_i, col, units)
    spy_events = {0: spy_units_cur}
    exit_heap  = []
    ctr        = 0
    n_entered  = 0
    n_skipped  = 0

    for entry_idx in sorted(entry_map.keys()):
        # Drain exits on or before entry_idx
        while exit_heap and exit_heap[0][0] <= entry_idx:
            exit_idx, _, col, units = heapq.heappop(exit_heap)
            p = close_arr[exit_idx, col]
            if not np.isnan(p):
                spy_units_cur += units * p / spy_prices[exit_idx]
            spy_events[exit_idx] = spy_units_cur

        # Enter signals at entry_idx
        for ticker in entry_map[entry_idx]:
            col = ticker_col_map.get(ticker)
            if col is None:
                n_skipped += 1
                continue
            if spy_units_cur * spy_prices[entry_idx] < pos_size:
                n_skipped += 1
                continue
            ep = close_arr[entry_idx, col]
            if np.isnan(ep):
                n_skipped += 1
                continue
            units = pos_size / ep
            spy_units_cur -= pos_size / spy_prices[entry_idx]
            actual_exit = min(entry_idx + exit_n, n - 1)
            heapq.heappush(exit_heap, (actual_exit, ctr, col, units))
            ctr += 1
            entered.append((entry_idx, actual_exit, col, units))
            n_entered += 1

        spy_events[entry_idx] = spy_units_cur

    # Drain remaining exits
    while exit_heap:
        exit_idx, _, col, units = heapq.heappop(exit_heap)
        p = close_arr[exit_idx, col]
        if not np.isnan(p):
            spy_units_cur += units * p / spy_prices[exit_idx]
        spy_events[exit_idx] = spy_units_cur

    # Build spy_units step function
    spy_units_arr = np.empty(n)
    prev_day = 0
    prev_val = INITIAL / spy_prices[0]
    for day, val in sorted(spy_events.items()):
        spy_units_arr[prev_day:day] = prev_val
        prev_day, prev_val = day, val
    spy_units_arr[prev_day:] = prev_val

    # Vectorized position equity via numpy slices
    pos_equity = np.zeros(n)
    for entry_i, exit_i, col, units in entered:
        if exit_i > entry_i:
            pos_equity[entry_i:exit_i] += units * close_arr[entry_i:exit_i, col]

    return spy_units_arr * spy_prices + pos_equity, n_entered, n_skipped


def compute_stats_full(equity, spy_daily_ret, dates):
    years = (dates[-1] - dates[0]).days / 365.25
    final = float(equity[-1])
    cagr  = (final / INITIAL) ** (1 / years) - 1 if years > 0 else 0.0

    port_ret = np.diff(equity) / equity[:-1]
    vol_ann  = float(np.std(port_ret)) * np.sqrt(252)

    var_spy = float(np.var(spy_daily_ret))
    beta    = float(np.cov(port_ret, spy_daily_ret)[0, 1] / var_spy) if var_spy > 0 else 1.0

    peak = np.maximum.accumulate(equity)
    mdd  = float(((equity - peak) / peak).min())

    return {
        "final":    round(final, 2),
        "totret":   round((final / INITIAL - 1) * 100, 2),
        "cagr":     round(cagr * 100, 2),
        "vol":      round(vol_ann * 100, 4),
        "beta":     round(beta, 4),
        "mdd":      round(mdd * 100, 2),
    }


# ---------------------------------------------------------------------------
# HTML builder
# ---------------------------------------------------------------------------
def build_html(payload, meta):
    data_json  = json.dumps(payload, separators=(",", ":"))
    n_signals  = meta["n_signals"]
    date_range = meta["date_range"]
    start_date = meta["start_date"]
    tickers    = meta["tickers"]
    generated  = meta["generated"]

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>H5 — M-Signal Portfolio Backtest</title>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    :root {{
      --bg: #ffffff; --bg-secondary: #f5f4f0; --bg-input: #eceae4;
      --text-primary: #1a1a19; --text-secondary: #5f5e5a;
      --border: rgba(0,0,0,0.12); --border-md: rgba(0,0,0,0.20);
      --blue: #378ADD; --blue-dark: #185FA5; --blue-bg: rgba(55,138,221,0.10);
      --red: #E24B4A; --red-bg: rgba(226,75,74,0.08);
      --green: #1D9E75; --green-bg: rgba(29,158,117,0.10);
      --orange: #C97A1A; --orange-bg: rgba(201,122,26,0.10);
      --purple: #7B4FBB; --purple-bg: rgba(123,79,187,0.10);
      --gray: #888780; --gray-bg: rgba(136,135,128,0.12);
      --radius-sm: 5px; --radius-md: 8px; --radius-lg: 12px;
      --font: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      --font-mono: ui-monospace, "Cascadia Code", monospace;
    }}
    @media (prefers-color-scheme: dark) {{
      :root {{
        --bg: #1a1a19; --bg-secondary: #2c2c2a; --bg-input: #3a3935;
        --text-primary: #f0efe8; --text-secondary: #b4b2a9;
        --border: rgba(255,255,255,0.12); --border-md: rgba(255,255,255,0.22);
        --blue: #85B7EB; --blue-dark: #B5D4F4; --blue-bg: rgba(55,138,221,0.18);
        --red: #F09595; --red-bg: rgba(226,75,74,0.15);
        --green: #5DCAA5; --green-bg: rgba(29,158,117,0.18);
        --orange: #E09B4A; --orange-bg: rgba(201,122,26,0.18);
        --purple: #B094E0; --purple-bg: rgba(123,79,187,0.20);
        --gray: #888780; --gray-bg: rgba(136,135,128,0.20);
      }}
    }}
    body {{
      font-family: var(--font);
      background: var(--bg);
      color: var(--text-primary);
      padding: 2rem;
      max-width: 980px;
      margin: 0 auto;
      line-height: 1.5;
    }}
    .page-title {{ font-size: 18px; font-weight: 500; margin-bottom: 4px; }}
    .meta {{ font-size: 12px; color: var(--text-secondary); margin-bottom: 1.5rem; }}

    /* ---- Top metric strip ---- */
    .top-strip {{
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 1.5rem;
    }}
    .top-card {{
      flex: 1;
      background: var(--bg-secondary);
      border-radius: var(--radius-lg);
      padding: 14px 16px 12px;
    }}
    .top-card-label {{ font-size: 11px; color: var(--text-secondary); margin-bottom: 3px; }}
    .top-card-val {{ font-size: 28px; font-weight: 600; line-height: 1.1; margin-bottom: 3px; }}
    .top-card-sub {{ font-size: 11px; color: var(--text-secondary); }}
    .rf-block {{
      display: flex;
      flex-direction: column;
      align-items: flex-end;
      gap: 4px;
      white-space: nowrap;
    }}
    .rf-label {{ font-size: 11px; color: var(--text-secondary); }}
    .rf-controls {{ display: flex; align-items: center; gap: 4px; }}
    .rf-controls input[type=number] {{
      width: 56px;
      font-size: 15px;
      font-weight: 600;
      text-align: center;
      border: 0.5px solid var(--border-md);
      border-radius: var(--radius-sm);
      background: var(--bg-input);
      color: var(--text-primary);
      padding: 4px 4px;
      -moz-appearance: textfield;
    }}
    .rf-controls input[type=number]::-webkit-inner-spin-button {{ -webkit-appearance: none; }}
    .rf-unit {{ font-size: 13px; color: var(--text-secondary); }}
    .step-btn {{
      width: 26px; height: 26px;
      border: 0.5px solid var(--border-md);
      border-radius: var(--radius-sm);
      background: var(--bg-secondary);
      color: var(--text-primary);
      font-size: 15px; font-weight: 500;
      cursor: pointer; line-height: 1;
      display: flex; align-items: center; justify-content: center;
      flex-shrink: 0;
    }}
    .step-btn:hover {{ background: var(--bg-input); }}

    /* ---- Scenario Setup (collapsible definition cards) ---- */
    .defn-toggle {{
      display: flex; align-items: center; justify-content: space-between;
      cursor: pointer; user-select: none;
      padding: 7px 0; border-bottom: 0.5px solid var(--border); margin-bottom: 1rem;
    }}
    .defn-toggle-label {{ font-size: 11px; font-weight: 500; letter-spacing: .05em; text-transform: uppercase; color: var(--text-secondary); }}
    .defn-chevron {{ font-size: 12px; color: var(--text-secondary); transition: transform 0.2s; display: inline-block; }}
    .defn-chevron.open {{ transform: rotate(180deg); }}
    .defn-body-wrap {{
      overflow: hidden; max-height: 0; opacity: 0; margin-bottom: 0;
      transition: max-height 0.25s ease, opacity 0.2s ease, margin-bottom 0.2s ease;
    }}
    .defn-body-wrap.open {{ max-height: 500px; opacity: 1; margin-bottom: 1.5rem; }}
    .defn-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
    .defn-card {{ border: 0.5px solid var(--border); border-radius: var(--radius-lg); padding: 14px 16px; }}
    .defn-pill {{ display: inline-block; font-size: 11px; font-weight: 500; padding: 2px 10px; border-radius: 99px; margin-bottom: 8px; }}
    .defn-title {{ font-size: 13px; font-weight: 500; margin-bottom: 6px; }}
    .defn-body {{ font-size: 12px; color: var(--text-secondary); line-height: 1.65; }}
    .defn-body code {{ font-family: var(--font-mono); font-size: 11px; background: var(--bg-secondary); padding: 1px 5px; border-radius: 3px; }}

    /* ---- Sliders panel ---- */
    .sliders-panel {{
      background: var(--bg-secondary);
      border-radius: var(--radius-lg);
      padding: 16px 18px;
      margin-bottom: 1.5rem;
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 18px;
    }}
    .slider-block {{ display: flex; flex-direction: column; }}
    .slider-label {{ font-size: 11px; color: var(--text-secondary); font-weight: 500; letter-spacing: .05em; text-transform: uppercase; margin-bottom: 5px; }}
    .slider-value-row {{ display: flex; align-items: baseline; gap: 7px; margin-bottom: 9px; }}
    .slider-big {{ font-size: 24px; font-weight: 600; line-height: 1; }}
    .slider-note {{ font-size: 11px; color: var(--text-secondary); }}
    .slider-controls {{
      display: flex;
      align-items: center;
      gap: 6px;
    }}
    .slider-controls input[type=range] {{
      flex: 1;
      accent-color: var(--blue);
      cursor: pointer;
    }}
    .num-input {{
      width: 48px;
      font-size: 12px;
      font-weight: 500;
      text-align: center;
      border: 0.5px solid var(--border-md);
      border-radius: var(--radius-sm);
      background: var(--bg-input);
      color: var(--text-primary);
      padding: 3px 2px;
      -moz-appearance: textfield;
    }}
    .num-input::-webkit-inner-spin-button {{ -webkit-appearance: none; }}
    .slider-ticks {{ display: flex; justify-content: space-between; margin-top: 5px; font-size: 10px; color: var(--text-secondary); }}

    /* ---- Stats grid ---- */
    .grid5 {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; margin-bottom: 1.5rem; }}
    .mc {{ background: var(--bg-secondary); border-radius: var(--radius-md); padding: 12px 14px; }}
    .mc-label {{ font-size: 11px; color: var(--text-secondary); margin-bottom: 4px; }}
    .mc-val {{ font-size: 20px; font-weight: 500; }}
    .mc-sub {{ font-size: 11px; color: var(--text-secondary); margin-top: 3px; }}

    /* ---- Charts ---- */
    .two-col {{ display: grid; grid-template-columns: 1.65fr 1fr; gap: 1.5rem; align-items: start; margin-bottom: 1.5rem; }}
    .section-head {{ font-size: 11px; font-weight: 500; letter-spacing: .06em; text-transform: uppercase; color: var(--text-secondary); margin-bottom: 8px; }}
    .legend-row {{ display: flex; flex-wrap: wrap; gap: 14px; margin-bottom: 8px; }}
    .li {{ display: flex; align-items: center; gap: 5px; font-size: 11px; color: var(--text-secondary); }}
    .ls {{ width: 10px; height: 10px; border-radius: 2px; flex-shrink: 0; }}
    .chart-wrap {{ position: relative; width: 100%; height: 270px; }}
    .chart-wrap-sm {{ position: relative; width: 100%; height: 210px; }}
    .callout {{ background: var(--bg-secondary); border-radius: var(--radius-md); padding: 10px 13px; font-size: 12px; color: var(--text-secondary); line-height: 1.65; margin-bottom: 8px; }}
    .chart-note {{ font-size: 10px; color: var(--text-secondary); margin-top: 4px; opacity: 0.7; }}

    .divider {{ border: none; border-top: 0.5px solid var(--border); margin: 1.5rem 0; }}
    .footer-note {{ font-size: 12px; color: var(--text-secondary); line-height: 1.7; }}
    .footer-note strong {{ font-weight: 500; color: var(--text-primary); }}
  </style>
</head>
<body>

  <p class="page-title">H5 — M-Signal Portfolio vs SPY Buy-and-Hold</p>
  <p class="meta">M signals backtest · sector ETFs only (excl. QQQ, DIA, IWM) · n={n_signals} signals · {date_range} · entry T0+1 close · in-sample · generated {generated}</p>

  <!-- Top metric strip: Alpha, Beta, Sharpe + RF input -->
  <div class="top-strip">
    <div class="top-card">
      <p class="top-card-label">Jensen's Alpha (vs SPY)</p>
      <p class="top-card-val" id="tc-alpha">—</p>
      <p class="top-card-sub" id="tc-alpha-sub">CAGR − rf − β(SPY CAGR − rf)</p>
    </div>
    <div class="top-card">
      <p class="top-card-label">Beta (vs SPY)</p>
      <p class="top-card-val" id="tc-beta" style="color:var(--blue);">—</p>
      <p class="top-card-sub" id="tc-beta-sub">market exposure</p>
    </div>
    <div class="top-card">
      <p class="top-card-label">Sharpe Ratio</p>
      <p class="top-card-val" id="tc-sharpe" style="color:var(--purple);">—</p>
      <p class="top-card-sub" id="tc-sharpe-sub">vs base Sharpe —</p>
    </div>
    <div class="rf-block">
      <span class="rf-label">Risk-free rate</span>
      <div class="rf-controls">
        <button class="step-btn" id="rf-minus">−</button>
        <input type="number" id="rf-input" value="{RF_DEFAULT}" min="0" max="20" step="0.25">
        <span class="rf-unit">%</span>
        <button class="step-btn" id="rf-plus">+</button>
      </div>
      <span class="rf-label" style="font-size:10px;">US T-bill default</span>
    </div>
  </div>

  <!-- Scenario Setup (collapsible) -->
  <div class="defn-toggle" id="defn-toggle">
    <span class="defn-toggle-label">Scenario Setup</span>
    <span class="defn-chevron" id="defn-chevron">&#9662;</span>
  </div>
  <div class="defn-body-wrap" id="defn-body-wrap">
    <div class="defn-row">
      <div class="defn-card">
        <span class="defn-pill" style="background:var(--gray-bg);color:var(--gray);">Base — SPY buy and hold</span>
        <p class="defn-title">$100k in SPY from {start_date}</p>
        <p class="defn-body">$100,000 deployed into SPY on the first available OHLC date. Held throughout with no further action. Benchmark for the M-Signal Portfolio.</p>
      </div>
      <div class="defn-card">
        <span class="defn-pill" style="background:var(--blue-bg);color:var(--blue-dark);">M-Signal Portfolio</span>
        <p class="defn-title">SPY + sector rotation on M signals</p>
        <p class="defn-body">Start in SPY. On each M signal (sector ETFs: {tickers}): sell <strong id="defn-pos">$10k</strong> (<strong id="defn-pct">10%</strong> of $100k) of SPY, enter that ETF at <code>T0+1 close</code>. Exit after <strong id="defn-exit">38</strong> trading days, re-enter SPY. Skip if SPY balance &lt; position size.</p>
      </div>
    </div>
    <p class="footer-note" style="margin-top:12px;">
      <strong>In-sample.</strong> Entry and exit prices are backward-looking. Holding period and allocation are set by slider, not by real-time signals.
      <strong>Jensen's Alpha</strong> = CAGR &minus; rf &minus; &beta;&times;(SPY CAGR &minus; rf). Updates live with the risk-free rate input.
      <strong>Beta</strong> = cov(portfolio daily returns, SPY daily returns) / var(SPY daily returns).
      Excluded: QQQ, DIA, IWM (broad proxies; no diversification value over SPY).
    </p>
  </div>

  <!-- Sliders -->
  <div class="sliders-panel">
    <div class="slider-block">
      <div class="slider-label">Holding period</div>
      <div class="slider-value-row">
        <span class="slider-big" id="lbl-exit" style="color:var(--blue);">d38</span>
        <span class="slider-note" id="lbl-exit-note">median alpha-peak (H4)</span>
      </div>
      <div class="slider-controls">
        <button class="step-btn" id="exit-minus">−</button>
        <input type="range" id="slider-exit" min="0" max="365" value="38" step="1">
        <button class="step-btn" id="exit-plus">+</button>
        <input type="number" class="num-input" id="exit-num" value="38" min="0" max="365">
      </div>
      <div class="slider-ticks">
        <span>d0</span><span>d50</span><span>d100</span><span>d150</span>
        <span>d200</span><span>d250</span><span>d300</span><span>d365</span>
      </div>
    </div>
    <div class="slider-block">
      <div class="slider-label">Allocation per signal</div>
      <div class="slider-value-row">
        <span class="slider-big" id="lbl-alloc" style="color:var(--orange);">10%</span>
        <span class="slider-note" id="lbl-alloc-sub">$10k of $100k</span>
      </div>
      <div class="slider-controls">
        <button class="step-btn" id="alloc-minus">−</button>
        <input type="range" id="slider-alloc" min="0" max="100" value="10" step="1">
        <button class="step-btn" id="alloc-plus">+</button>
        <input type="number" class="num-input" id="alloc-num" value="10" min="0" max="100">
      </div>
      <div class="slider-ticks">
        <span>0%</span><span>10%</span><span>20%</span><span>30%</span>
        <span>40%</span><span>50%</span><span>75%</span><span>100%</span>
      </div>
    </div>
  </div>

  <!-- Stats cards -->
  <div class="grid5">
    <div class="mc">
      <p class="mc-label">M-Signal final value</p>
      <p class="mc-val" id="mc-final" style="color:var(--blue);">—</p>
      <p class="mc-sub" id="mc-totret">total return</p>
    </div>
    <div class="mc">
      <p class="mc-label">Base final value</p>
      <p class="mc-val" id="mc-base-final" style="color:var(--gray);">—</p>
      <p class="mc-sub" id="mc-base-ret">total return</p>
    </div>
    <div class="mc">
      <p class="mc-label">CAGR (M-Signal)</p>
      <p class="mc-val" id="mc-cagr">—</p>
      <p class="mc-sub" id="mc-cagr-sub">base CAGR —</p>
    </div>
    <div class="mc">
      <p class="mc-label">Max drawdown</p>
      <p class="mc-val" id="mc-mdd" style="color:var(--red);">—</p>
      <p class="mc-sub" id="mc-mdd-sub">base MDD —</p>
    </div>
    <div class="mc">
      <p class="mc-label">Trades / skipped</p>
      <p class="mc-val" id="mc-trades">—</p>
      <p class="mc-sub" id="mc-skipped">— skipped</p>
    </div>
  </div>

  <!-- Charts -->
  <div class="two-col">
    <div>
      <p class="section-head">Portfolio equity ($)</p>
      <div class="legend-row">
        <span class="li"><span class="ls" style="background:var(--blue);opacity:0.8;"></span>M-Signal Portfolio</span>
        <span class="li"><span class="ls" style="background:var(--gray);opacity:0.6;"></span>Base (SPY buy-hold)</span>
      </div>
      <div class="chart-wrap">
        <canvas id="equityChart"></canvas>
      </div>
      <p class="chart-note">Equity curve snaps to nearest 10-day / 5% allocation bucket. Stats reflect exact slider values.</p>
    </div>
    <div>
      <p class="section-head">Jensen's Alpha by holding period</p>
      <div class="chart-wrap-sm">
        <canvas id="alphaChart"></canvas>
      </div>
      <div class="callout" id="alpha-callout">Drag sliders to explore.</div>
      <div class="callout">
        <strong>Entry:</strong> T0+1 close. Same-day signals processed in order; skipped if SPY balance &lt; position size.
      </div>
    </div>
  </div>

  <script>
    const D = {data_json};

    // ---- Controls ----
    const sExit  = document.getElementById('slider-exit');
    const sAlloc = document.getElementById('slider-alloc');
    const rfIn   = document.getElementById('rf-input');
    const exitNum  = document.getElementById('exit-num');
    const allocNum = document.getElementById('alloc-num');

    // ---- Setters (keep slider + number input in sync) ----
    function setExit(v) {{
      v = Math.max(0, Math.min(365, Math.round(v)));
      sExit.value = v; exitNum.value = v; updateUI();
    }}
    function setAlloc(v) {{
      v = Math.max(0, Math.min(100, Math.round(v)));
      sAlloc.value = v; allocNum.value = v; updateUI();
    }}
    function setRf(v) {{
      v = Math.max(0, Math.min(20, Math.round(v * 4) / 4));
      rfIn.value = v.toFixed(2); updateUI();
    }}

    document.getElementById('exit-minus').onclick  = () => setExit(+sExit.value - 1);
    document.getElementById('exit-plus').onclick   = () => setExit(+sExit.value + 1);
    document.getElementById('alloc-minus').onclick = () => setAlloc(+sAlloc.value - 1);
    document.getElementById('alloc-plus').onclick  = () => setAlloc(+sAlloc.value + 1);
    document.getElementById('rf-minus').onclick    = () => setRf(+rfIn.value - 0.25);
    document.getElementById('rf-plus').onclick     = () => setRf(+rfIn.value + 0.25);
    sExit.addEventListener('input',  () => setExit(+sExit.value));
    sAlloc.addEventListener('input', () => setAlloc(+sAlloc.value));
    exitNum.addEventListener('change',  () => setExit(+exitNum.value));
    allocNum.addEventListener('change', () => setAlloc(+allocNum.value));
    rfIn.addEventListener('change', () => setRf(+rfIn.value));

    // ---- Data access ----
    function getS(alloc, exit) {{
      return {{
        cagr:    D.cagr[alloc][exit],
        vol:     D.vol[alloc][exit],
        beta:    D.beta[alloc][exit],
        mdd:     D.mdd[alloc][exit],
        trades:  D.trades[alloc][exit],
        skipped: D.skipped[alloc][exit],
        final:   D.final[alloc][exit],
        totret:  D.totret[alloc][exit],
      }};
    }}

    function snapIdx(val, arr) {{
      let best = 0;
      arr.forEach((a, i) => {{ if (Math.abs(a - val) < Math.abs(arr[best] - val)) best = i; }});
      return best;
    }}

    function getEquityData(exit_day, alloc_pct) {{
      const ei = snapIdx(exit_day, D.chart_exit);
      const ai = snapIdx(alloc_pct, D.chart_alloc);
      return D.chart_test[ai][ei];
    }}

    // ---- Computed metrics ----
    function jensenAlpha(cagr, beta, spy_cagr, rf) {{
      return cagr - rf - beta * (spy_cagr - rf);
    }}
    function sharpeRatio(cagr, vol, rf) {{
      return vol > 0 ? (cagr/100 - rf/100) / (vol/100) : 0;
    }}

    // ---- Formatters ----
    function fmt$(v)    {{ return '$' + Math.round(v).toLocaleString('en-US'); }}
    function fmtPct(v)  {{ return (v >= 0 ? '+' : '') + v.toFixed(2) + '%'; }}
    function fmtPp(v)   {{ return (v >= 0 ? '+' : '') + v.toFixed(2) + 'pp'; }}
    function fmtX(v)    {{ return v.toFixed(3); }}
    function fmtSh(v)   {{ return (v >= 0 ? '' : '') + v.toFixed(2); }}

    // ---- Charts ----
    const eCtx = document.getElementById('equityChart').getContext('2d');
    const eChart = new Chart(eCtx, {{
      type: 'line',
      data: {{
        labels: D.chart_dates,
        datasets: [
          {{ label: 'M-Signal', data: getEquityData(38, 10),
             borderColor: 'rgba(55,138,221,0.9)', backgroundColor: 'rgba(55,138,221,0.07)',
             borderWidth: 1.5, pointRadius: 0, fill: false, tension: 0.3 }},
          {{ label: 'Base (SPY)', data: D.chart_base,
             borderColor: 'rgba(136,135,128,0.65)', backgroundColor: 'transparent',
             borderWidth: 1.2, pointRadius: 0, fill: false, tension: 0.3, borderDash: [4,3] }},
        ]
      }},
      options: {{
        responsive: true, maintainAspectRatio: false,
        interaction: {{ mode: 'index', intersect: false }},
        plugins: {{
          legend: {{ display: false }},
          tooltip: {{ callbacks: {{ label: ctx => ctx.dataset.label + ': $' +
            ctx.parsed.y.toLocaleString('en-US', {{maximumFractionDigits:0}}) }} }}
        }},
        scales: {{
          x: {{ ticks: {{ maxTicksLimit: 8, font: {{size:10}}, color:'#888780',
                callback: (v,i) => D.chart_dates[i] }}, grid: {{ display: false }} }},
          y: {{ ticks: {{ font:{{size:10}}, color:'#888780',
                callback: v => '$' + (v/1000).toFixed(0) + 'k' }},
               grid: {{ color: 'rgba(136,135,128,0.15)' }}, border: {{ display: false }} }}
        }}
      }}
    }});

    const aCtx = document.getElementById('alphaChart').getContext('2d');
    const aChart = new Chart(aCtx, {{
      type: 'line',
      data: {{
        labels: D.exit_range,
        datasets: [{{
          label: "Jensen's alpha",
          data: [],
          borderColor: 'rgba(29,158,117,0.9)',
          backgroundColor: 'rgba(29,158,117,0.10)',
          borderWidth: 1.5, pointRadius: 0, fill: true, tension: 0.3,
        }}]
      }},
      options: {{
        responsive: true, maintainAspectRatio: false,
        plugins: {{
          legend: {{ display: false }},
          tooltip: {{ callbacks: {{ label: ctx =>
            (ctx.parsed.y >= 0 ? '+' : '') + ctx.parsed.y.toFixed(2) + 'pp' }} }}
        }},
        scales: {{
          x: {{ ticks: {{ font:{{size:10}}, color:'#888780',
                callback: (v,i) => D.exit_range[i] % 50 === 0 ? 'd'+D.exit_range[i] : '' }},
               grid: {{ display: false }} }},
          y: {{ ticks: {{ font:{{size:10}}, color:'#888780',
                callback: v => (v>=0?'+':'') + v.toFixed(1) + 'pp' }},
               grid: {{ color:'rgba(136,135,128,0.15)' }}, border: {{ display: false }} }}
        }}
      }},
      plugins: [{{
        id: 'cursor',
        afterDraw(chart) {{
          const {{ ctx, scales:{{x,y}} }} = chart;
          const idx = parseInt(sExit.value);
          if (idx < 0 || idx >= D.exit_range.length) return;
          const xPx = x.getPixelForValue(idx);
          ctx.save();
          ctx.strokeStyle = 'rgba(55,138,221,0.75)';
          ctx.lineWidth = 1.5;
          ctx.setLineDash([4,3]);
          ctx.beginPath(); ctx.moveTo(xPx,y.top); ctx.lineTo(xPx,y.bottom); ctx.stroke();
          ctx.restore();
        }}
      }}]
    }});

    // ---- Main update ----
    function updateUI() {{
      const exit  = parseInt(sExit.value);
      const alloc = parseInt(sAlloc.value);
      const rf    = parseFloat(rfIn.value) || 0;

      const s  = getS(alloc, exit);
      const sb = D.stats_base;

      // Slider labels
      document.getElementById('lbl-exit').textContent = 'd' + exit;
      document.getElementById('lbl-exit-note').textContent =
        exit === 38 ? 'median alpha-peak (H4)' :
        exit === 64 ? 'median return-peak (H4)' :
        exit === 33 ? 'H4 alpha-zone start' : '';
      document.getElementById('lbl-alloc').textContent = alloc + '%';
      document.getElementById('lbl-alloc-sub').textContent =
        '$' + (alloc * 100 / 10) + ' per $100k' + (alloc > 0 ? '' : ' — no rotation');

      // Defn card sync
      document.getElementById('defn-pos').textContent  = '$' + (alloc * 1000 / 10).toLocaleString();
      document.getElementById('defn-pct').textContent  = alloc + '%';
      document.getElementById('defn-exit').textContent = exit;

      // Computed metrics
      const alpha  = jensenAlpha(s.cagr, s.beta, D.spy_cagr, rf);
      const sharpe = sharpeRatio(s.cagr, s.vol, rf);
      const b_sharpe = sharpeRatio(sb.cagr, sb.vol, rf);

      // Top cards
      const alphaEl = document.getElementById('tc-alpha');
      alphaEl.textContent = fmtPp(alpha);
      alphaEl.style.color = alpha >= 0 ? 'var(--green)' : 'var(--red)';
      document.getElementById('tc-alpha-sub').textContent =
        'CAGR ' + fmtPct(s.cagr) + ' | beta ' + fmtX(s.beta);

      document.getElementById('tc-beta').textContent = fmtX(s.beta);
      document.getElementById('tc-beta-sub').textContent =
        s.beta < 1 ? 'lower market exposure than SPY' :
        s.beta > 1 ? 'higher market exposure than SPY' : 'same as SPY';

      const sharpeEl = document.getElementById('tc-sharpe');
      sharpeEl.textContent = fmtSh(sharpe);
      sharpeEl.style.color = sharpe >= b_sharpe ? 'var(--purple)' : 'var(--red)';
      document.getElementById('tc-sharpe-sub').textContent =
        'base ' + fmtSh(b_sharpe) + ' | ' + (sharpe >= b_sharpe ? 'above' : 'below') + ' base';

      // Stats cards
      document.getElementById('mc-final').textContent  = fmt$(s.final);
      document.getElementById('mc-totret').textContent = fmtPct(s.totret) + ' total';
      document.getElementById('mc-base-final').textContent = fmt$(sb.final);
      document.getElementById('mc-base-ret').textContent   = fmtPct(sb.totret) + ' total';

      document.getElementById('mc-cagr').textContent = fmtPct(s.cagr);
      document.getElementById('mc-cagr-sub').textContent = 'base ' + fmtPct(sb.cagr);

      const mddEl = document.getElementById('mc-mdd');
      mddEl.textContent = fmtPct(s.mdd);
      mddEl.style.color = s.mdd <= sb.mdd ? 'var(--green)' : 'var(--red)';
      document.getElementById('mc-mdd-sub').textContent = 'base ' + fmtPct(sb.mdd);

      document.getElementById('mc-trades').textContent  = s.trades;
      document.getElementById('mc-skipped').textContent = s.skipped + ' skipped';

      // Equity chart
      eChart.data.datasets[0].data = getEquityData(exit, alloc);
      eChart.update('none');

      // Alpha chart: Jensen's alpha across all exit days for current alloc + rf
      const alphaSeries = D.exit_range.map(d => {{
        const sd = getS(alloc, d);
        return jensenAlpha(sd.cagr, sd.beta, D.spy_cagr, rf);
      }});
      aChart.data.datasets[0].data = alphaSeries;
      aChart.update('none');

      // Alpha callout
      const maxA = Math.max(...alphaSeries);
      const bestD = D.exit_range[alphaSeries.indexOf(maxA)];
      document.getElementById('alpha-callout').innerHTML =
        'At ' + alloc + '% alloc, rf=' + rf.toFixed(2) + '%: peak Jensen&rsquo;s alpha ' +
        '<strong>' + fmtPp(maxA) + '</strong> at d' + bestD + '. ' +
        'Current (d' + exit + '): <strong>' + fmtPp(jensenAlpha(s.cagr, s.beta, D.spy_cagr, rf)) + '</strong>.';
    }}

    updateUI();

    // Scenario Setup toggle
    document.getElementById('defn-toggle').addEventListener('click', function() {{
      const wrap = document.getElementById('defn-body-wrap');
      const chevron = document.getElementById('defn-chevron');
      const open = wrap.classList.toggle('open');
      chevron.classList.toggle('open', open);
    }});
  </script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=== H5 Portfolio Rotation Backtest ===\n")

    print("Loading signals...")
    signals = load_signals()

    print("Loading OHLC from Sheets...")
    close = load_ohlc()
    close = close.ffill()

    needed    = {"SPY"} | set(signals["Ticker"].unique())
    available = sorted(needed & set(close.columns))
    missing   = needed - set(close.columns)
    if missing:
        print(f"  WARNING: tickers not in OHLC: {missing}")
    close = close[available]
    dates = close.index
    print(f"  Window: {dates[0].date()} to {dates[-1].date()} ({len(dates)} trading days)\n")

    # Numpy arrays
    close_arr      = close.values.astype(float)
    col_names      = list(close.columns)
    spy_col        = col_names.index("SPY")
    ticker_col_map = {t: col_names.index(t) for t in col_names if t != "SPY"}
    n              = len(dates)
    spy_prices     = close_arr[:, spy_col]
    spy_daily_ret  = np.diff(spy_prices) / spy_prices[:-1]

    # Entry map (T0+1)
    date_to_i = {d: i for i, d in enumerate(dates)}
    entry_map = {}
    for _, row in signals.iterrows():
        t0     = row["T0"]
        future = dates[dates > t0]
        if len(future) == 0:
            continue
        idx = date_to_i[future[0]]
        entry_map.setdefault(idx, []).append(row["Ticker"])
    n_sig_total = sum(len(v) for v in entry_map.values())

    # Base
    base_equity = (INITIAL / spy_prices[0]) * spy_prices
    stats_base  = compute_stats_full(base_equity, spy_daily_ret, dates)
    stats_base["n_trades"] = 0
    stats_base["n_skipped"] = n_sig_total
    print(f"  Base: CAGR={stats_base['cagr']:+.2f}%  Beta={stats_base['beta']:.3f}  "
          f"Vol={stats_base['vol']:.2f}%  MDD={stats_base['mdd']:.2f}%\n")

    # Monthly sample
    monthly_mask    = pd.Series(dates).dt.to_period("M").diff().fillna(1).ne(0).values
    chart_idx       = np.where(monthly_mask)[0]
    chart_dates_str = [dates[i].strftime("%Y-%m") for i in chart_idx]
    chart_base_v    = [round(float(base_equity[i]), 0) for i in chart_idx]

    # Result arrays [alloc_pct][exit_day]
    n_a, n_e = len(ALLOC_FINE), len(EXIT_FINE)
    cagr_2d    = [[0.0]*n_e for _ in range(n_a)]
    vol_2d     = [[0.0]*n_e for _ in range(n_a)]
    beta_2d    = [[0.0]*n_e for _ in range(n_a)]
    mdd_2d     = [[0.0]*n_e for _ in range(n_a)]
    final_2d   = [[0.0]*n_e for _ in range(n_a)]
    totret_2d  = [[0.0]*n_e for _ in range(n_a)]
    trades_2d  = [[0]*n_e for _ in range(n_a)]
    skipped_2d = [[0]*n_e for _ in range(n_a)]

    chart_test = [[None]*len(EXIT_CHART) for _ in range(len(ALLOC_CHART))]

    total = n_a * n_e
    print(f"Running {n_a} x {n_e} = {total:,} simulations (vectorized)...\n")
    t_start = time.time()
    done = 0

    for ai, alloc_pct in enumerate(ALLOC_FINE):
        pos_size = alloc_pct / 100.0 * INITIAL

        for ei, exit_n in enumerate(EXIT_FINE):
            if alloc_pct == 0:
                equity    = base_equity.copy()
                n_entered = 0
                n_skipped = n_sig_total
            else:
                equity, n_entered, n_skipped = simulate_fast(
                    entry_map, n, close_arr, spy_col, ticker_col_map, exit_n, pos_size
                )

            s = compute_stats_full(equity, spy_daily_ret, dates)
            cagr_2d[ai][ei]    = s["cagr"]
            vol_2d[ai][ei]     = s["vol"]
            beta_2d[ai][ei]    = s["beta"]
            mdd_2d[ai][ei]     = s["mdd"]
            final_2d[ai][ei]   = s["final"]
            totret_2d[ai][ei]  = s["totret"]
            trades_2d[ai][ei]  = n_entered
            skipped_2d[ai][ei] = n_skipped

            if alloc_pct in ALLOC_CHART_S and exit_n in EXIT_CHART_S:
                ca = ALLOC_CHART.index(alloc_pct)
                ce = EXIT_CHART.index(exit_n)
                chart_test[ca][ce] = [round(float(equity[i]), 0) for i in chart_idx]

            done += 1

        if ai % 10 == 9 or ai == n_a - 1:
            el  = time.time() - t_start
            eta = el / done * (total - done) if done < total else 0
            print(f"  alloc {alloc_pct:>3}%: {done:,}/{total:,}  "
                  f"elapsed={el:.0f}s  ETA={eta:.0f}s")

    print(f"\nTotal: {time.time()-t_start:.1f}s")

    payload = {
        "alloc_range": ALLOC_FINE,
        "exit_range":  EXIT_FINE,
        "chart_alloc": ALLOC_CHART,
        "chart_exit":  EXIT_CHART,
        "chart_dates": chart_dates_str,
        "chart_base":  chart_base_v,
        "chart_test":  chart_test,
        "stats_base":  {**stats_base, "totret": stats_base["totret"]},
        "spy_cagr":    stats_base["cagr"],
        "cagr":        cagr_2d,
        "vol":         vol_2d,
        "beta":        beta_2d,
        "mdd":         mdd_2d,
        "final":       final_2d,
        "totret":      totret_2d,
        "trades":      trades_2d,
        "skipped":     skipped_2d,
        "rf_default":  RF_DEFAULT,
    }

    meta = {
        "n_signals":  len(signals),
        "date_range": f"{dates[0].strftime('%b %Y')}-{dates[-1].strftime('%b %Y')}",
        "start_date": dates[0].strftime("%d %b %Y"),
        "tickers":    ", ".join(sorted(set(signals["Ticker"].unique()) - EXCLUDE)),
        "generated":  datetime.date.today().isoformat(),
    }

    existing = _glob.glob(OUT_BASE + "_v*.html")
    next_v = max(
        (int(os.path.basename(p).split("_v")[1].split(".")[0]) for p in existing),
        default=0
    ) + 1
    out_path = f"{OUT_BASE}_v{next_v}.html"

    print(f"\nBuilding HTML: {out_path}")
    html = build_html(payload, meta)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Done. (v{next_v})")


if __name__ == "__main__":
    main()
