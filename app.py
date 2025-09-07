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
# Expanded Crude Oil Keywords
# -------------------------------
keywords = [
    "crude oil", "oil prices", "Brent", "WTI", "OPEC", "oil demand", "oil supply", "inventory",
    "sanctions", "tariffs", "Middle East tensions", "production cuts", "US shale", "rig count",
    "refinery outages", "pipeline disruption", "inflation", "dollar index", "Fed policy",
    "shipping disruptions", "geopolitical risks", "war", "conflict", "strikes", "embargo",
    "price cap", "imports", "exports", "demand slowdown", "energy policy", "fossil fuels",
    "fuel subsidies", "energy security", "global oil markets", "IEA report", "EIA report"
]

query = " OR ".join([f'"{kw}"' for kw in keywords])

# -------------------------------
# Fetch Articles
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
            st.error(f"❌ Failed to fetch news: {response.status_code} - {response.text}")
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
# Fetch and Display Button
# -------------------------------
if st.button("🔍 Fetch Crude Oil News"):
    articles = fetch_articles(query, start_date, end_date)

    if articles:
        df = pd.DataFrame(articles)
        st.subheader(f"🛢️ Crude Oil Related News ({len(df)} articles found)")
        st.dataframe(df)

        # Download as Excel
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
