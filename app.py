import streamlit as st
import requests
from datetime import datetime, timedelta

# -------------------------------
# Streamlit App Title
# -------------------------------
st.title("📰 Crude Oil News Explorer")

# -------------------------------
# Date Range Selection (within last 30 days)
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
# Expanded Keywords for Crude Oil News
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
# News API Call
# -------------------------------
API_KEY = "3087034a13564f75bfc769c0046e729c"  # 🔑 Replace with your NewsAPI key
url = (
    f"https://newsapi.org/v2/everything?"
    f"q={query}&"
    f"from={start_date}&"
    f"to={end_date}&"
    f"sortBy=publishedAt&"
    f"language=en&"
    f"apiKey={API_KEY}"
)

response = requests.get(url)

# -------------------------------
# Display News Results
# -------------------------------
if response.status_code == 200:
    articles = response.json().get("articles", [])
    if articles:
        st.subheader(f"🛢️ Crude Oil Related News ({len(articles)} articles found)")
        for i, article in enumerate(articles, 1):
            st.markdown(f"**{i}. {article['title']}**")
            st.write(article["description"] if article["description"] else "No description available.")
            st.write(f"Source: {article['source']['name']} | Published At: {article['publishedAt']}")
            st.markdown(f"[Read More]({article['url']})")
            st.markdown("---")
    else:
        st.warning("⚠️ No news articles found for the selected timeline.")
else:
    st.error(f"❌ Failed to fetch news: {response.status_code}")
