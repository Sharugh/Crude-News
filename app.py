import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
from io import BytesIO
from transformers import pipeline

# Configuration
NEWSAPI_KEY = "3087034a13564f75bfc769c0046e729c"
NEWSAPI_URL = "https://newsapi.org/v2/everything"

# Benchmarks List
BENCHMARKS = [
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
    "Basrah Heavy Mo01 at Asia close"
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
            st.error(f"Failed to fetch news. {response.status_code}: {response.text}")
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
            except Exception:
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

def display_articles(data, query):
    if not data:
        st.warning("No articles found.")
        return

    # Add summaries
    data = add_summaries(data)

    df = pd.DataFrame(data)
    st.write(f"### News for '{query}' (Last 30 Days)")
    st.dataframe(df)

    # Excel Export (one sheet with summary column)
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Articles", index=False)
    output.seek(0)
    st.download_button(
        "Download as Excel",
        data=output,
        file_name="news_articles_with_summaries.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# Main App
def main():
    st.set_page_config(page_title="Energy Benchmarks News Dashboard", layout="wide")
    st.title("📰 Crude & Refined Products News Collector")

    st.sidebar.header("🔍 Search Filters")
    benchmark = st.sidebar.selectbox("Select Benchmark", BENCHMARKS)

    # Auto set past 30 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)

    if st.sidebar.button("Fetch News"):
        formatted_query = format_query(benchmark)
        data = fetch_articles(
            formatted_query,
            start_date.strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d")
        )
        display_articles(data, formatted_query)

if __name__ == "__main__":
    main()
