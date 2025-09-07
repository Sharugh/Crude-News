import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
from io import BytesIO
from transformers import pipeline

# ---------------------------
# Configuration
# ---------------------------
NEWSAPI_KEY = "3087034a13564f75bfc769c0046e729c"  # replace with your key
NEWSAPI_URL = "https://newsapi.org/v2/everything"

# ---------------------------
# Keywords for crude oil prices
# ---------------------------
KEYWORDS = [
    # Core Benchmarks
    "crude oil price", "oil price", "Brent crude", "WTI crude", "Dated Brent",
    "Urals crude", "Dubai crude", "Oman crude", "Basrah Heavy", "ESPO crude",
    "Murban crude", "Bonny Light crude", "Mexican Maya crude", "Forties crude",

    # Pricing Terms
    "ICE Brent futures", "NYMEX WTI futures", "Platts crude assessment",
    "Argus crude price", "S&P Global crude benchmarks", "oil futures price",
    "oil spot price", "forward curve crude oil", "crude oil spreads",
    "crude differentials", "benchmark oil prices",

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
]

# ---------------------------
# Hugging Face Models (local summarizer & sentiment)
# ---------------------------
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
sentiment_analyzer = pipeline("sentiment-analysis")

def local_summarize_news(news_descriptions, from_date, to_date):
    if not news_descriptions:
        return "⚠️ No articles found to summarize."

    combined_text = " ".join(news_descriptions[:20])  # avoid overflow
    summary = summarizer(
        combined_text,
        max_length=200,
        min_length=60,
        do_sample=False
    )[0]['summary_text']

    # Sentiment analysis
    sentiments = sentiment_analyzer(news_descriptions[:20])
    sentiment_counts = {"POSITIVE": 0, "NEGATIVE": 0, "NEUTRAL": 0}
    for s in sentiments:
        label = s['label'].upper()
        if "POS" in label:
            sentiment_counts["POSITIVE"] += 1
        elif "NEG" in label:
            sentiment_counts["NEGATIVE"] += 1
        else:
            sentiment_counts["NEUTRAL"] += 1

    overall = max(sentiment_counts, key=sentiment_counts.get)

    return f"""
    📊 **Crude Oil Market Summary ({from_date} → {to_date})**

    **Summary:** {summary}

    **Sentiment Breakdown:** {sentiment_counts}  
    **Overall Market Sentiment:** {overall}
    """

# ---------------------------
# Helper Functions
# ---------------------------
def format_query():
    return " OR ".join(KEYWORDS)[:480]  # keep query under 500 chars

def fetch_articles(search_query, start_date, end_date):
    params = {
        "q": search_query,
        "from": start_date,
        "to": end_date,
        "apiKey": NEWSAPI_KEY,
        "language": "en",
        "pageSize": 100,
        "sortBy": "relevancy"
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
            } for a in articles
        ]
    except Exception as e:
        st.error(f"API request failed: {e}")
        return []

def display_articles(data, from_date, to_date):
    if not data:
        st.warning("⚠️ No articles found for the selected timeline.")
        return
    df = pd.DataFrame(data)
    st.write(f"### 📰 Crude Oil News ({from_date} → {to_date})")
    st.dataframe(df)

    # Excel download
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

    # Add summarization
    descriptions = [a["Description"] for a in data if a["Description"]]
    summary_text = local_summarize_news(descriptions, from_date, to_date)
    st.markdown(summary_text)

# ---------------------------
# Main App
# ---------------------------
def main():
    st.set_page_config(page_title="Crude Oil Price News Dashboard", layout="wide")
    st.title("🛢️ Crude Oil Price News Collector")

    st.sidebar.header("📅 Select Timeline")
    today = datetime.now().date()
    default_start = today - timedelta(days=7)

    start_date = st.sidebar.date_input("Start Date", default_start, max_value=today)
    end_date = st.sidebar.date_input("End Date", today, max_value=today)

    if start_date > end_date:
        st.sidebar.error("Start date cannot be after end date.")
        return

    if st.sidebar.button("Fetch Crude Oil News"):
        query = format_query()
        data = fetch_articles(query, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
        display_articles(data, start_date, end_date)

if __name__ == "__main__":
    main()

