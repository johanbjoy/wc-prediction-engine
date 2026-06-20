import os
import requests
import logging

logger = logging.getLogger(__name__)

# Fallback proxy values for WC teams (in millions €)
# In production, this would be periodically updated by the Apify scraper cron job.
MOCK_TEAM_VALUES = {
    "England": 1500, "France": 1200, "Brazil": 1100, "Portugal": 1050,
    "Spain": 1000, "Argentina": 850, "Germany": 800, "Netherlands": 750,
    "Italy": 700, "Belgium": 550, "Uruguay": 450, "Croatia": 350,
    "Colombia": 300, "USA": 280, "Senegal": 270, "Morocco": 260,
    "Japan": 250, "Switzerland": 240, "Denmark": 230, "South Korea": 180,
    "Mexico": 160, "Canada": 150, "Ecuador": 140, "Ghana": 130
}

def get_team_value_ratio(home_team: str, away_team: str) -> float:
    """
    Calculates the financial dominance ratio between two teams.
    Returns home_value / away_value.
    A ratio > 1.0 means home team has a more expensive squad.
    """
    api_key = os.getenv("TRANSFERMARKT_API_KEY")
    
    # Placeholder for live Apify synchronous request if needed.
    # Because Apify scraper runs take 2-5 minutes, we use cached values.
    
    home_val = MOCK_TEAM_VALUES.get(home_team, 100) # Default 100m for unknown
    away_val = MOCK_TEAM_VALUES.get(away_team, 100)
    
    # Cap the ratio to prevent extreme outliers (e.g. England vs San Marino)
    ratio = home_val / max(1, away_val)
    return max(0.2, min(5.0, ratio))
