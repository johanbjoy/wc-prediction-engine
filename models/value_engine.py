import logging

logger = logging.getLogger(__name__)

def calculate_edge(model_prob: float, market_prob: float, bankroll: float = 1000.0) -> dict:
    """
    Calculates Edge, Expected Value (EV), and Full Kelly Criterion wager size.
    
    Args:
        model_prob (float): Model's probability (0-100)
        market_prob (float): Market's true probability (0-100)
        bankroll (float): Total betting bankroll
        
    Returns:
        dict: {'edge': float, 'ev': float, 'kelly_pct': float, 'wager_amount': float}
    """
    # Convert percentages to decimals
    p_model = model_prob / 100.0
    p_market = market_prob / 100.0
    
    if p_market <= 0.0 or p_model <= 0.0:
        return {'edge': 0.0, 'ev': 0.0, 'kelly_pct': 0.0, 'wager_amount': 0.0}
        
    # Decimal odds = 1 / implied probability
    decimal_odds = 1.0 / p_market
    
    # True Edge = Model Prob - Market Prob
    true_edge = p_model - p_market
    
    # Expected Value for a 1-unit stake
    ev = (p_model * decimal_odds) - 1.0
    
    # Full Kelly Criterion
    if true_edge > 0 and decimal_odds > 1.0:
        kelly_pct = true_edge / (decimal_odds - 1.0)
    else:
        kelly_pct = 0.0
        
    # Cap Full Kelly to max 25% of bankroll to avoid catastrophic ruin in extreme outlier cases
    kelly_pct = max(0.0, min(kelly_pct, 0.25))
    wager_amount = bankroll * kelly_pct
    
    return {
        'edge': round(true_edge * 100, 2),
        'ev': round(ev, 4),
        'kelly_pct': round(kelly_pct * 100, 2),
        'wager_amount': round(wager_amount, 2)
    }
