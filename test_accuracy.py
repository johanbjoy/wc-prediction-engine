"""
test_accuracy.py — Backtest the Poisson model against all 16 completed WC 2026 matches.

For each finished fixture, runs the prediction engine and compares the
predicted scoreline to the actual result. Reports:
  - Exact score hits  (3 pts)
  - Correct outcome   (1 pt)
  - Wrong outcome     (0 pts)
  - Overall accuracy %
"""
import logging
from data.scraper import get_completed_fixtures, _baseline_squad, TEAM_BASELINES
from models.poisson_model import predict as run_poisson
from models.xgboost_model import predict as run_xgboost
from evaluator import _calculate_points, _outcome

logging.basicConfig(level=logging.WARNING)

def main():
    completed = get_completed_fixtures()
    if not completed:
        print("No completed fixtures found in the database.")
        return

    total_pts    = 0
    exact_count  = 0
    correct_count = 0
    wrong_count   = 0
    results      = []

    print(f"\n{'='*80}")
    print(f"  BACKTEST: Ensemble (Poisson + XGBoost) vs {len(completed)} Completed WC 2026 Matches")
    print(f"{'='*80}\n")
    print(f"  {'Match':<35} {'Pred':>6} {'Actual':>8} {'Pts':>4}  {'Verdict'}")
    print(f"  {'─'*72}")

    for f in completed:
        home = f["home_team"]
        away = f["away_team"]
        real_h = f["real_home_score"]
        real_a = f["real_away_score"]

        # Generate predictions from both models
        home_players = _baseline_squad(home)
        away_players = _baseline_squad(away)
        
        poisson_res = run_poisson(home, away, home_players, away_players)
        xgb_res = run_xgboost(home, away, home_players, away_players)
        
        # Extract xG and blend
        p_xg_home = poisson_res["model_meta"]["lam_home"]
        p_xg_away = poisson_res["model_meta"]["lam_away"]
        x_xg_home = xgb_res["model_meta"]["raw_home_xg"]
        x_xg_away = xgb_res["model_meta"]["raw_away_xg"]
        
        blended_home_xg = (p_xg_home * 0.70) + (x_xg_home * 0.30)
        blended_away_xg = (p_xg_away * 0.70) + (x_xg_away * 0.30)
        
        pred_h = max(0, int(round(blended_home_xg)))
        pred_a = max(0, int(round(blended_away_xg)))

        pts = _calculate_points(pred_h, pred_a, real_h, real_a)
        total_pts += pts

        if pts == 3:
            exact_count += 1
            verdict = "✓✓ EXACT"
        elif pts == 1:
            correct_count += 1
            verdict = "✓  Outcome"
        else:
            wrong_count += 1
            verdict = "✗  Wrong"

        match_label = f"{home} vs {away}"
        pred_str = f"{pred_h}-{pred_a}"
        actual_str = f"{real_h}-{real_a}"

        if pred_h > pred_a:
            pred_winner = home
        elif pred_a > pred_h:
            pred_winner = away
        else:
            pred_winner = "Draw"

        results.append({
            "match": match_label, "pred": pred_str, "actual": actual_str,
            "pts": pts, "verdict": verdict,
            "pred_winner": pred_winner,
            "actual_outcome": _outcome(real_h, real_a),
        })

        print(f"  {match_label:<35} {pred_str:>6} {actual_str:>8} {pts:>4}  {verdict}")

    n = len(completed)
    scored = exact_count + correct_count + wrong_count

    print(f"\n{'='*80}")
    print(f"  RESULTS SUMMARY")
    print(f"{'='*80}")
    print(f"  Total matches tested:   {n}")
    print(f"  Total points scored:    {total_pts} / {n * 3} (max possible)")
    print(f"  Exact score matches:    {exact_count}  ({exact_count/n*100:.1f}%)")
    print(f"  Correct outcomes:       {correct_count}  ({correct_count/n*100:.1f}%)")
    print(f"  Wrong predictions:      {wrong_count}  ({wrong_count/n*100:.1f}%)")
    print(f"  Outcome accuracy:       {(exact_count + correct_count)/n*100:.1f}%")
    print(f"  Points per match:       {total_pts/n:.2f}")
    print(f"{'='*80}\n")

    # Draw analysis (important for Dixon-Coles validation)
    actual_draws = sum(1 for r in results if r["actual_outcome"] == "draw")
    predicted_draws = sum(1 for r in results if r["pred_winner"] == "Draw")
    draw_correct = sum(
        1 for r in results
        if r["actual_outcome"] == "draw" and r["pred_winner"] == "Draw"
    )
    print(f"  DRAW ANALYSIS (Dixon-Coles validation)")
    print(f"  Actual draws:           {actual_draws}/{n}")
    print(f"  Predicted draws:        {predicted_draws}/{n}")
    print(f"  Correct draw calls:     {draw_correct}/{actual_draws if actual_draws else 1}")
    print()


if __name__ == "__main__":
    main()
