import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
from io import BytesIO

# -------------------
# Configurations
# -------------------
NEWSAPI_KEY = "3087034a13564f75bfc769c0046e729c"
NEWSAPI_URL = "https://newsapi.org/v2/everything"

# S&P Spark API
SPARK_APP_ID = "SPGHFUOWA8M"
SPARK_API_KEY = "5atw17pic36k8mh0oqld4zw5nmkx8csn"
SPARK_URL = "https://sparkuatapi.spglobal.com/v1/nlp/summarize"  # Adjust if different

# -------------------
# Keywords (precise crude-related)
# -------------------
CRUDE_KEYWORDS = [
    # Benchmarks
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

    # Finance & Economy
    "Fed policy crude oil", "dollar index oil prices", "inflation oil prices",
    "interest rates oil demand", "recession oil demand"
]

# -------------------
# Helper Functions
# -------------------
def fetch_articles(search_query, start_date, end_date):
    params = {
        "q": search_query,
        "from": start_date,
        "to": end_date,
        "apiKey": NEWSAPI_KEY,
        "language": "en",
        "pageSize": 100,
        "sortBy": "publishedAt"
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
        st.error(f"⚠️ API request failed: {e}")
        return []


def display_articles(data, start_date, end_date):
    if not data:
        st.warning("⚠️ No news articles found for the selected timeline.")
        return None

    df = pd.DataFrame(data)
    st.write(f"### 📰 Crude Oil News ({start_date} → {end_date})")
    st.dataframe(df)

    # Excel Download
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="CrudeNews")
    output.seek(0)

    st.download_button(
        "📥 Download as Excel",
        data=output,
        file_name=f"crude_news_{start_date}_{end_date}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    return df


def summarize_with_spglobal(texts, from_date, to_date):
    if not texts:
        return "⚠️ No articles found to summarize."

    payload = {
        "appid": SPARK_APP_ID,
        "text": " ".join(texts[:20]),  # limit to first 20 descriptions
        "length": "short",
        "language": "en"
    }

    headers = {
        "x-api-key": SPARK_API_KEY,
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(SPARK_URL, headers=headers, json=payload)
        if response.status_code != 200:
            return f"❌ Failed to summarize: {response.status_code} - {response.text}"

        summary = response.json().get("summary", "No summary returned.")

        return f"""
        📊 **Crude Oil Market Summary ({from_date} → {to_date})**
        
        **Summary:** {summary}
        """
    except Exception as e:
        return f"⚠️ Summarization failed: {e}"


# -------------------
# Streamlit App
# -------------------
def main():
    st.set_page_config(page_title="Crude Oil Price News Dashboard", layout="wide")
    st.title("🛢️ Crude Oil Price News Collector")

    st.sidebar.header("📅 Timeline Filter")
    today = datetime.now().date()
    default_start = today - timedelta(days=7)  # last 7 days default

    start_date = st.sidebar.date_input("Start Date", default_start, max_value=today - timedelta(days=1))
    end_date = st.sidebar.date_input("End Date", today, max_value=today)

    if start_date > end_date:
        st.sidebar.error("❌ Start date cannot be after end date.")
        return

    if st.sidebar.button("Fetch Crude Oil News"):
        # Join all keywords with OR
        query = " OR ".join(CRUDE_KEYWORDS)
        data = fetch_articles(query, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))

        df = display_articles(data, start_date, end_date)

        if df is not None:
            descriptions = df["Description"].dropna().tolist()
            summary_text = summarize_with_spglobal(descriptions, start_date, end_date)
            st.markdown(summary_text)


if __name__ == "__main__":
    main()

