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

API_KEY = "YOUR_NEWSAPI_KEY"  # 🔑 Replace with your NewsAPI key
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
    "crude oil", "oil prices", "Brent", "WTI", "OPEC", "oil demand", "oil supply", "inventory",
    "sanctions", "tariffs", "Middle East tensions", "production cuts", "US shale", "rig count",
    "refinery outages", "pipeline disruption", "inflation", "dollar index", "Fed policy",
    "shipping disruptions", "geopolitical risks", "war", "conflict", "strikes", "embargo",
    "price cap", "imports", "exports", "demand slowdown", "energy policy", "fossil fuels",
    "fuel subsidies", "energy security", "global oil markets", "IEA report", "EIA report"
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
