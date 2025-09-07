import streamlit as st
import pandas as pd
import requests
import re
import datetime
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# ---------------------------
# CONFIG
# ---------------------------
NEWS_API_KEY = "3087034a13564f75bfc769c0046e729c"
MAX_SUMMARY_SENTENCES = 5

# ---------------------------
# HELPER FUNCTIONS
# ---------------------------

def fetch_news(query="crude oil", language="en", page_size=20):
    """Fetch crude oil related news globally using NewsAPI."""
    url = (
        f"https://newsapi.org/v2/everything?q={query}&language={language}"
        f"&pageSize={page_size}&apiKey={NEWS_API_KEY}"
    )
    response = requests.get(url)
    if response.status_code == 200:
        articles = response.json().get("articles", [])
        return [
            {
                "Date": a["publishedAt"][:10] if a["publishedAt"] else "",
                "Source": a["source"]["name"],
                "Title": a["title"],
                "Description": a["description"],
                "URL": a["url"],
            }
            for a in articles
        ]
    return []


def split_sentences(text):
    """Simple regex-based sentence tokenizer (avoids nltk punkt)."""
    sentences = re.split(r'(?<=[.!?]) +', text.strip())
    return [s for s in sentences if len(s) > 20]  # filter short


def score_sentences(text, top_n=5):
    """TF scoring for summary sentences."""
    words = re.findall(r'\w+', text.lower())
    freqs = {}
    for w in words:
        freqs[w] = freqs.get(w, 0) + 1

    sentences = split_sentences(text)
    ranking = {}
    for s in sentences:
        score = sum(freqs.get(w, 0) for w in s.lower().split())
        ranking[s] = score

    ranked_sentences = sorted(ranking, key=ranking.get, reverse=True)
    return ranked_sentences[:top_n]


def to_excel(df):
    """Convert dataframe to Excel binary for download."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Crude News", index=False)
    return output.getvalue()


def generate_pdf(summary_text, futuristic_points):
    """Generate PDF with summaries + futuristic insights."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph("🌍 Global Crude Oil News Summary", styles["Title"]))
    elements.append(Spacer(1, 12))

    for sent in summary_text:
        elements.append(Paragraph("• " + sent, styles["Normal"]))
        elements.append(Spacer(1, 6))

    elements.append(Spacer(1, 20))
    elements.append(Paragraph("🚀 Futuristic Insights", styles["Heading2"]))

    for fp in futuristic_points:
        elements.append(Paragraph("• " + fp, styles["Normal"]))
        elements.append(Spacer(1, 6))

    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf

# ---------------------------
# STREAMLIT APP
# ---------------------------

st.set_page_config(page_title="Global Crude Oil News", layout="wide")

st.title("🌍 Global Crude Oil News Dashboard")
st.write("Real-time crude oil related news with summaries, Excel exports, and futuristic insights.")

# Fetch news
articles = fetch_news()

if not articles:
    st.error("No news found. Check API key or query.")
else:
    df = pd.DataFrame(articles)

    # Show table
    st.subheader("📰 Latest Crude Oil News")
    st.dataframe(df, use_container_width=True)

    # Download Excel
    excel_data = to_excel(df)
    st.download_button(
        "📥 Download News as Excel",
        data=excel_data,
        file_name="global_crude_news.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # Combine text for summary
    combined_text = " ".join(df["Description"].dropna().tolist())
    if combined_text.strip():
        summary_sentences = score_sentences(combined_text, top_n=MAX_SUMMARY_SENTENCES)

        st.subheader("📝 Auto-Summary")
        for s in summary_sentences:
            st.write("- " + s)

        # Futuristic insights (static + dynamic blend)
        futuristic_points = [
            "Increased influence of AI on crude oil demand forecasting 📊",
            "Geopolitical risks will remain the key driver of crude volatility 🌍",
            "OPEC+ decisions to have amplified impact due to tightening supply ⛽",
            "Rising investment in alternative fuels may reduce long-term crude dependency 🔋",
            "Carbon emission policies will reshape the demand-supply balance 🌱",
        ]

        # PDF Export
        pdf_data = generate_pdf(summary_sentences, futuristic_points)
        st.download_button(
            "📄 Download Summary PDF",
            data=pdf_data,
            file_name="crude_news_summary.pdf",
            mime="application/pdf"
        )
    else:
        st.warning("Not enough description text to generate summary.")
