import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import requests
import xml.etree.ElementTree as ET

def get_sentiment(team):
    url = f"https://news.google.com/rss/search?q={team}+national+football+team&hl=en-US&gl=US&ceid=US:en"
    try:
        r = requests.get(url, timeout=5)
        root = ET.fromstring(r.text)
        headlines = [item.find('title').text for item in root.findall('.//item')[:3]]
        return headlines
    except Exception as e:
        return []

print(get_sentiment("Argentina"))
