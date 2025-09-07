import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
from io import BytesIO
from transformers import pipeline

# Configuration
NEWSAPI_KEY = "3087034a13564f75bfc769c0046e729c"
NEWSAPI_URL = "https://newsapi.org/v2/everything"

# Benchmarks & Crude-Related Keywords
SEARCH_TERMS = [
    # Benchmarks
    "Gasoline 92 RON Unl MOP West India $/bbl",
    "Gasoline 95 RON Unl MOP West India $/bbl",
    "Gasoil .25% (2500ppm) MOP West India $/bbl",
    "Gasoil .001% (10ppm) MOP West India $/bbl",
    "Gasoil .05% (500ppm) MOP West India $/bbl",
    "Marine Gasoil 0.5% Dlvd Mumbai",
    "Marine Gasoil 0.1% Dlvd Mumbai",
    "Marine Gasoil 1.5% Dlvd Mumbai",
    "Naphtha MOP West India $/bbl",
    "Jet Kero MOP West India $/bbl",
    "Marine Fuel 0.5% Bunker Dlvd Mumbai",
    "Bunker FO 380 CST Dlvd Mumbai",
    "Marine Fuel 0.5% Dlvd Kandla",
    "Dubai Mo01 (NextGen MOC)",
    "Oman Blend Mo01 (NextGen MOC)",
    "Dated Brent",
    "Urals DAP West Coast India",
    "Basrah Heavy Mo01 at Asia close",
    # Crude price keywords
    "crude oil price",
    "oil demand",
    "oil supply",
    "OPEC",
    "tariffs",
    "sanctions",
    "geopolitical risk",
    "energy policy",
    "oil price volatility",
    "global oil market",
    "Middle East tensions",
    "US shale oil",
    "India crude imports",
    "China oil demand"
]

# Summarizer model (cached)
@st.cache_resource
def load_summarizer():
    return pipeline("summarization", model="facebook/bart-large-cnn")

summarizer = load_summarizer()

def format_query(query):
    return " ".join(query.strip().split())[:200]

def fetch_articles(search_query, start_date, end_date):
    params = {
        "q": search_query,
        "from": start_date,
        "to": end_date,
        "apiKey": NEWSAPI_KEY,
        "language": "en",
        "pageSize": 100
    }
    try:
        response = requests.get(NEWSAPI_URL, params=params)
        if response.status_code != 200:
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
    except:
        return []

def add_summaries(articles):
    for a in articles:
        text = a.get("Description") or a.get("Title")
        if not text:
            summary = "No content available."
        else:
            try:
                summary = summarizer(
                    text, max_length=60, min_length=15, do_sample=False
                )[0]["summary_text"]
            except:
                summary = "Summarization failed."
        a["Summary"] = summary
        if a["Published At"]:
            try:
                a["Published At"] = datetime.fromisoformat(
                    a["Published At"].replace("Z", "")
                ).strftime("%d-%m-%Y")
            except:
                pass
    return articles

def display_articles(df):
    if df.empty:
        st.warning("No articles found in the last 30 days.")
        return

    st.write("### 📰 Crude & Refined Products News (Last 30 Days)")
    st.dataframe(df)

    # Excel Export
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Articles", index=False)
    output.seek(0)
    st.download_button(
        "Download as Excel",
        data=output,
        file_name="crude_news_with_summaries.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# Main App
def main():
    st.set_page_config(page_title="Crude Price & Benchmarks News", layout="wide")
    st.title("🛢️ Crude Price & Benchmarks News Dashboard")

    st.sidebar.header("ℹ️ Info")
    st.sidebar.write("This dashboard collects crude oil & refined product benchmark news with key crude price keywords for the last 30 days.")

    # Define last 30 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)

    if st.sidebar.button("Fetch News"):
        all_articles = []
        for term in SEARCH_TERMS:
            formatted_query = format_query(term)
            data = fetch_articles(
                formatted_query,
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d")
            )
            all_articles.extend(data)

        # Deduplicate by Title + URL
        df = pd.DataFrame(all_articles).drop_duplicates(subset=["Title", "URL"])

        # Add summaries
        if not df.empty:
            articles_with_summary = add_summaries(df.to_dict("records"))
            df = pd.DataFrame(articles_with_summary)

        display_articles(df)

if __name__ == "__main__":
    main()
