import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
from io import BytesIO

# -------------------------------
# Config
# -------------------------------
st.set_page_config(page_title="Crude Oil News Explorer", layout="wide")
st.title("📰 Crude Oil News Explorer")

API_KEY = "3087034a13564f75bfc769c0046e729c"  # 🔑 Replace with your NewsAPI key
NEWSAPI_URL = "https://newsapi.org/v2/everything"

# -------------------------------
# Timeline (last 30 days)
# -------------------------------
today = datetime.today()
default_start = today - timedelta(days=7)
min_date = today - timedelta(days=30)

start_date = st.date_input(
    "Start Date",
    value=default_start,
    min_value=min_date,
    max_value=today
)

end_date = st.date_input(
    "End Date",
    value=today,
    min_value=min_date,
    max_value=today
)

if start_date > end_date:
    st.error("⚠️ Start date must be before End date")
    st.stop()

# -------------------------------
# Crude Oil Keywords (split later)
# -------------------------------
keywords = [
    # Core Benchmarks
    "crude oil price", "oil price", "Brent crude", "WTI crude", "Dated Brent",
    "Urals crude", "Dubai crude", "Oman crude", "Basrah Heavy", "ESPO crude",
    "Murban crude", "Bonny Light crude", "Mexican Maya crude", "Forties crude",
    "Russian crude price", "Middle East crude benchmarks",
    
    # Pricing Terms
    "ICE Brent futures", "NYMEX WTI futures", "Platts crude assessment", 
    "Argus crude price", "S&P Global crude benchmarks", "oil futures price",
    "oil spot price", "forward curve crude oil", "crude oil spreads", 
    "crude differentials", "crude oil swap", "benchmark oil prices",

    # Market Drivers
    "OPEC oil prices", "OPEC+ production cuts", "oil output cuts", 
    "supply disruption crude oil", "oil demand growth", "oil demand slowdown",
    "refinery demand crude", "refining margins oil", "crack spread oil",
    "floating storage crude", "oil shipping disruption", "tanker rates crude",
    "oil inventory build", "oil stock drawdown", "US crude exports",
    "China crude imports", "India crude imports",

    # Reports & Data
    "IEA oil market report", "EIA weekly petroleum status report", 
    "EIA crude inventory", "OPEC monthly oil report", "DOE crude stocks",
    "API crude stock report", "global oil balances",

    # Policy & Geopolitics
    "oil sanctions Russia", "EU Russian oil ban", "oil embargo Russia", 
    "US SPR release", "strategic petroleum reserve release", 
    "Iran oil sanctions", "Venezuela crude exports",
    "geopolitical premium oil", "oil price cap Russia",

    # Financial & Economic Links
    "Fed policy crude oil", "dollar index oil prices", "inflation oil prices",
    "interest rates oil demand", "recession oil demand"
    "crude oil price", "Brent crude", "WTI crude", "oil market", "oil prices",
    "OPEC", "OPEC+", "oil demand", "oil supply", "oil production", "oil output",
    "oil exports", "oil imports", "refinery output", "refinery shutdown",
    "geopolitical tensions oil", "oil sanctions", "oil embargo", "Middle East oil",
    "oil price forecast", "oil price outlook", "oil inventories", "EIA oil report",
    "IEA oil report", "tariffs on oil", "oil price cap", "oil storage", "oil disruption",
    "oil market volatility", "oil demand slowdown", "global oil consumption"
]

# -------------------------------
# Function: Fetch Articles for one query
# -------------------------------
def fetch_articles(query, start_date, end_date):
    params = {
        "q": query,
        "from": start_date.strftime("%Y-%m-%d"),
        "to": end_date.strftime("%Y-%m-%d"),
        "sortBy": "publishedAt",
        "language": "en",
        "pageSize": 100,
        "apiKey": API_KEY
    }
    try:
        response = requests.get(NEWSAPI_URL, params=params)
        if response.status_code != 200:
            st.error(f"❌ Failed: {response.status_code} - {response.text}")
            return []
        articles = response.json().get("articles", [])
        return [
            {
                "Title": a.get("title"),
                "Description": a.get("description"),
                "Published At": a.get("publishedAt"),
                "Source": a.get("source", {}).get("name"),
                "URL": a.get("url")
            }
            for a in articles
        ]
    except Exception as e:
        st.error(f"⚠️ API request failed: {e}")
        return []

# -------------------------------
# Split keywords into smaller groups (avoid 500 char limit)
# -------------------------------
def split_keywords(keywords, max_len=450):
    groups = []
    current = []
    length = 0
    for kw in keywords:
        piece = f'"{kw}" OR '
        if length + len(piece) > max_len:
            groups.append(" OR ".join([f'"{x}"' for x in current]))
            current = [kw]
            length = len(piece)
        else:
            current.append(kw)
            length += len(piece)
    if current:
        groups.append(" OR ".join([f'"{x}"' for x in current]))
    return groups

# -------------------------------
# Fetch and Display
# -------------------------------
if st.button("🔍 Fetch Crude Oil News"):
    keyword_groups = split_keywords(keywords)
    all_articles = []

    for group in keyword_groups:
        articles = fetch_articles(group, start_date, end_date)
        all_articles.extend(articles)

    if all_articles:
        df = pd.DataFrame(all_articles).drop_duplicates(subset=["Title", "URL"])
        st.subheader(f"🛢️ Crude Oil Related News ({len(df)} articles found)")
        st.dataframe(df)

        # Download Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False)
        output.seek(0)

        st.download_button(
            "📥 Download as Excel",
            data=output,
            file_name="crude_oil_news.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.warning("⚠️ No news articles found for the selected timeline.")
