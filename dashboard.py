"""
dashboard.py — Terminal and HTML leaderboard for WC 2026 Prediction Engine.

Usage:
    python dashboard.py            # Terminal display (single shot)
    python dashboard.py --html     # Write dashboard.html
    python dashboard.py --live     # Auto-refresh terminal every 30s
"""
import os, sys, time
from datetime import datetime
from data.database import get_connection


# ─── DATA LAYER ────────────────────────────────────────────────────────────

def get_leaderboard() -> list[dict]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    l.model_name,
                    l.total_points,
                    l.exact_scores_count,
                    COUNT(p.id)                                                AS total_preds,
                    SUM(CASE WHEN p.points_awarded > 0 THEN 1 ELSE 0 END)        AS correct_outcomes,
                    SUM(CASE WHEN p.points_awarded IS NOT NULL THEN 1 ELSE 0 END) AS scored_preds
                FROM leaderboard l
                LEFT JOIN predictions p ON p.model_name = l.model_name
                GROUP BY l.model_name
                ORDER BY l.total_points DESC, l.exact_scores_count DESC
            """)
            rows = cur.fetchall()
            return [dict(r) for r in rows]
    finally:
        conn.close()


def get_recent_predictions(limit: int = 12) -> list[dict]:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    f.home_team, f.away_team, f.match_date,
                    f.real_home_score, f.real_away_score,
                    p.model_name,
                    p.predicted_home_score, p.predicted_away_score,
                    p.points_awarded
                FROM predictions p
                JOIN fixtures f ON f.id = p.fixture_id
                ORDER BY f.match_date DESC, p.created_at DESC
                LIMIT %s
            """, (limit,))
            rows = cur.fetchall()
            return [dict(r) for r in rows]
    finally:
        conn.close()


def get_summary() -> dict:
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM predictions WHERE points_awarded IS NOT NULL")
            total = cur.fetchone()["count"]

            cur.execute("SELECT COUNT(*) FROM predictions WHERE points_awarded = 3")
            exact = cur.fetchone()["count"]

            cur.execute("SELECT COUNT(*) FROM predictions WHERE points_awarded > 0")
            correct = cur.fetchone()["count"]

            cur.execute("SELECT COUNT(*) FROM predictions WHERE points_awarded IS NULL")
            pending = cur.fetchone()["count"]

        return {
            "total":    total,
            "exact":    exact,
            "correct":  correct,
            "pending":  pending,
            "acc_pct":  round(correct / total * 100, 1) if total else 0.0,
            "exact_pct": round(exact / total * 100, 1) if total else 0.0,
        }
    finally:
        conn.close()


# ─── TERMINAL DISPLAY ──────────────────────────────────────────────────────

def _bar(value: float, max_val: float, width: int = 18) -> str:
    filled = int((value / max_val) * width) if max_val > 0 else 0
    return "█" * filled + "░" * (width - filled)


def print_dashboard():
    os.system("cls" if os.name == "nt" else "clear")
    now   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    board = get_leaderboard()
    stats = get_summary()

    print("\n" + "═" * 65)
    print("  ⚽  WC 2026 PREDICTION ENGINE")
    print(f"  {now}   |   {stats['pending']} predictions pending evaluation")
    print("═" * 65)

    # Leaderboard table
    if not board:
        print("\n  No scored predictions yet — run evaluator.py first.\n")
    else:
        max_pts = max((r["total_points"] or 0) for r in board) or 1
        print(f"\n  {'#':<3} {'Model':<32} {'Pts':>5} {'Exact':>6} {'Acc%':>6}  {'Bar'}")
        print("  " + "─" * 61)
        for i, r in enumerate(board, 1):
            pts     = r["total_points"] or 0
            scored  = r["scored_preds"] or 1
            acc     = round((r["correct_outcomes"] or 0) / scored * 100, 1)
            bar     = _bar(pts, max_pts)
            print(
                f"  {i:<3} {r['model_name']:<32} {pts:>5} "
                f"{r['exact_scores_count']:>6} {acc:>5.1f}%  {bar}"
            )

    # Summary row
    print(
        f"\n  TOTAL SCORED {stats['total']} | "
        f"Exact {stats['exact']} ({stats['exact_pct']}%) | "
        f"Correct {stats['correct']} ({stats['acc_pct']}%)"
    )

    # Recent predictions
    recent = get_recent_predictions(10)
    if recent:
        print("\n" + "─" * 65)
        print("  RECENT PREDICTIONS")
        print(f"  {'Match':<26} {'Pred':>6} {'Actual':>8} {'Pts':>5}")
        print("  " + "─" * 52)
        for r in recent:
            match   = f"{r['home_team']} vs {r['away_team']}"[:25]
            pred    = f"{r['predicted_home_score']}-{r['predicted_away_score']}"
            actual  = (
                f"{r['real_home_score']}-{r['real_away_score']}"
                if r["real_home_score"] is not None else "TBD"
            )
            pts     = r["points_awarded"]
            icon    = {3: "✓✓", 1: "✓ ", 0: "✗ "}.get(pts, "  ")
            pts_str = str(pts) if pts is not None else "–"
            print(f"  {match:<26} {pred:>6} {actual:>8} {icon}{pts_str:>3}")

    print("\n" + "═" * 65 + "\n")


# ─── HTML DASHBOARD ────────────────────────────────────────────────────────

def generate_html(output_path: str = "dashboard.html") -> str:
    board  = get_leaderboard()
    recent = get_recent_predictions(15)
    stats  = get_summary()
    now    = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    max_pts = max((r["total_points"] or 0) for r in board) if board else 1
    max_pts = max_pts or 1  # guard against all-zero leaderboard

    def badge(pts) -> str:
        if pts is None:
            return '<span class="b b-pending">–</span>'
        cfg = {3: ("b-exact", "3 ✓✓"), 1: ("b-ok", "1 ✓"), 0: ("b-fail", "0 ✗")}
        cls, label = cfg.get(pts, ("b-pending", "–"))
        return f'<span class="b {cls}">{label}</span>'

    board_rows = "".join(
        f"""<tr>
          <td class="rank">#{i}</td>
          <td class="model">{r['model_name']}</td>
          <td class="pts">{r['total_points'] or 0}</td>
          <td>{r['exact_scores_count'] or 0}</td>
          <td>{round((r['correct_outcomes'] or 0) / (r['scored_preds'] or 1) * 100, 1)}%</td>
          <td><div class="bar"><div class="fill"
              style="width:{round((r['total_points'] or 0) / max_pts * 100)}%"></div></div></td>
        </tr>"""
        for i, r in enumerate(board, 1)
    ) or '<tr><td colspan="6" class="empty">No predictions scored yet</td></tr>'

    recent_rows = "".join(
        f"""<tr>
          <td>{r['home_team']} vs {r['away_team']}</td>
          <td>{r['predicted_home_score']}-{r['predicted_away_score']}</td>
          <td>{ f"{r['real_home_score']}-{r['real_away_score']}"
                if r['real_home_score'] is not None else "TBD" }</td>
          <td>{badge(r['points_awarded'])}</td>
        </tr>"""
        for r in recent
    ) or '<tr><td colspan="4" class="empty">No predictions yet</td></tr>'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>WC 2026 Prediction Engine</title>
<style>
:root {{
  --bg:#0a0c10; --surface:#111318; --border:#1e2130;
  --text:#e8eaf0; --muted:#6b7280;
  --green:#22c55e; --yellow:#eab308; --red:#ef4444;
  --accent:#6366f1;
}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--text);font-family:'DM Sans',system-ui,sans-serif;
      padding:28px 24px;max-width:900px;margin:auto}}
h1{{font-size:1.5rem;font-weight:700;color:#fff}}
.sub{{font-size:.8rem;color:var(--muted);margin-top:4px}}
.tag{{display:inline-block;font-size:.7rem;background:var(--accent);color:#fff;
      padding:3px 10px;border-radius:999px;vertical-align:middle;margin-left:10px}}
h2{{font-size:.78rem;font-weight:600;color:var(--muted);margin:28px 0 12px;
    text-transform:uppercase;letter-spacing:.08em}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:12px;margin:20px 0}}
.card{{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:16px}}
.card .v{{font-size:1.9rem;font-weight:700;color:var(--accent)}}
.card .l{{font-size:.72rem;color:var(--muted);margin-top:4px}}
table{{width:100%;border-collapse:collapse;background:var(--surface);
       border-radius:10px;overflow:hidden;border:1px solid var(--border)}}
th{{text-align:left;padding:10px 14px;font-size:.7rem;color:var(--muted);
    text-transform:uppercase;letter-spacing:.06em;border-bottom:1px solid var(--border)}}
td{{padding:10px 14px;border-bottom:1px solid var(--border);font-size:.85rem}}
tr:last-child td{{border-bottom:none}}
tr:hover td{{background:rgba(255,255,255,.02)}}
.rank{{color:var(--muted);width:36px}}
.model{{font-weight:600}}
.pts{{color:var(--accent);font-weight:700;font-size:1rem}}
.bar{{background:var(--border);border-radius:999px;height:7px;width:90px}}
.fill{{background:var(--accent);height:7px;border-radius:999px}}
.b{{font-size:.7rem;padding:3px 8px;border-radius:999px;font-weight:600}}
.b-exact{{background:rgba(34,197,94,.15);color:var(--green)}}
.b-ok{{background:rgba(234,179,8,.15);color:var(--yellow)}}
.b-fail{{background:rgba(239,68,68,.15);color:var(--red)}}
.b-pending{{background:var(--border);color:var(--muted)}}
.empty{{text-align:center;color:var(--muted);padding:24px}}
@media(max-width:560px){{.bar{{display:none}}}}
</style>
</head>
<body>
<h1>⚽ WC 2026 Prediction Engine <span class="tag">LIVE</span></h1>
<p class="sub">Last updated: {now} &nbsp;·&nbsp; {stats['pending']} predictions awaiting evaluation</p>

<div class="cards">
  <div class="card"><div class="v">{stats['total']}</div><div class="l">Scored</div></div>
  <div class="card"><div class="v">{stats['exact']}</div><div class="l">Exact Scores</div></div>
  <div class="card"><div class="v">{stats['exact_pct']}%</div><div class="l">Exact Rate</div></div>
  <div class="card"><div class="v">{stats['acc_pct']}%</div><div class="l">Correct Outcomes</div></div>
</div>

<h2>Leaderboard</h2>
<table>
  <tr><th>#</th><th>Model</th><th>Points</th><th>Exact</th><th>Accuracy</th><th>Score</th></tr>
  {board_rows}
</table>

<h2>Recent Predictions</h2>
<table>
  <tr><th>Match</th><th>Predicted</th><th>Actual</th><th>Result</th></tr>
  {recent_rows}
</table>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    return output_path


# ─── ENTRY POINT ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    args = sys.argv[1:]

    if "--html" in args:
        path = generate_html()
        print(f"✓ {path} written.")

    elif "--live" in args:
        print("Live mode — refreshes every 30s. Ctrl-C to stop.")
        try:
            while True:
                print_dashboard()
                time.sleep(30)
        except KeyboardInterrupt:
            print("Stopped.")

    else:
        print_dashboard()
