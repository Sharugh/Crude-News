# app.py
import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
from io import BytesIO
from transformers import pipeline
from fpdf import FPDF
import urllib.parse
import time

# ---------------------------
# Config
# ---------------------------
NEWSAPI_KEY = "3087034a13564f75bfc769c0046e729c"   
NEWSAPI_URL = "https://newsapi.org/v2/everything"

st.set_page_config(page_title="Crude Oil Price News & Research", layout="wide")
st.title("🛢️ Crude Oil Price News & Research Dashboard")

# ---------------------------
# Keyword set (ultra-precise)
# ---------------------------
KEYWORDS = [
    # Benchmarks & grades
    "Brent crude", "WTI crude", "Dated Brent", "Urals crude", "Dubai crude", "Oman crude",
    "Basrah Heavy", "ESPO crude", "Murban", "Bonny Light", "Mexican Maya", "Forties",

    # Pricing & instruments
    "crude oil price", "oil price", "ICE Brent futures", "NYMEX WTI futures",
    "oil spot price", "oil futures", "forward curve", "crude spreads", "crude differential",

    # Data providers & assessments
    "Platts assessment", "Argus assessment", "S&P Global Platts", "Argus Media",

    # Supply/demand & drivers
    "OPEC", "OPEC+", "production cuts", "output cuts", "supply disruption", "supply shock",
    "oil inventories", "EIA crude inventory", "API crude", "IEA oil report", "OPEC monthly",

    # Trade flows & policy affecting prices
    "China crude imports", "India crude imports", "US crude exports", "EU oil sanctions",
    "oil embargo", "oil sanctions Russia", "US SPR release", "strategic petroleum reserve",

    # Refining & margin indicators
    "refinery outage", "refinery margins", "crack spread", "refining demand",

    # Shipping / logistics that move price
    "floating storage", "tanker rates", "voyage charter rates", "Suez Canal disruption",

    # Market sentiment / volatility
    "price volatility", "contango", "backwardation", "market premium"
]

# ---------------------------
# Utilities: split keywords into safe query groups
# ---------------------------
def build_keyword_groups(keywords, max_chars=480):
    groups = []
    cur = []
    cur_len = 0
    for kw in keywords:
        piece = f'"{kw}" OR '
        if cur_len + len(piece) > max_chars and cur:
            groups.append(" OR ".join([f'"{k}"' for k in cur]))
            cur = [kw]
            cur_len = len(piece)
        else:
            cur.append(kw)
            cur_len += len(piece)
    if cur:
        groups.append(" OR ".join([f'"{k}"' for k in cur]))
    # final safety: strip any trailing OR
    groups = [g.rstrip().rstrip("OR ").strip() for g in groups]
    return groups

# ---------------------------
# Load Hugging Face models (cached)
# ---------------------------
@st.cache_resource
def load_models():
    summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
    sentiment = pipeline("sentiment-analysis")
    return summarizer, sentiment

with st.spinner("Loading summarizer & sentiment models (first run will download models)..."):
    summarizer, sentiment_analyzer = load_models()

# ---------------------------
# Helper: call NewsAPI for one query
# ---------------------------
def fetch_articles_for_query(query, from_date_str, to_date_str, page_size=100):
    params = {
        "q": query,
        "from": from_date_str,
        "to": to_date_str,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": page_size,
        "apiKey": NEWSAPI_KEY
    }
    try:
        r = requests.get(NEWSAPI_URL, params=params, timeout=30)
    except Exception as e:
        st.error(f"Network/API error when calling NewsAPI: {e}")
        return []
    if r.status_code != 200:
        st.error(f"Failed to fetch: {r.status_code} - {r.text}")
        return []
    try:
        articles = r.json().get("articles", [])
    except Exception:
        st.error("Failed to parse NewsAPI response.")
        return []
    results = []
    for a in articles:
        results.append({
            "Title": a.get("title"),
            "Description": a.get("description"),
            "Published At": a.get("publishedAt"),
            "Source": a.get("source", {}).get("name"),
            "URL": a.get("url")
        })
    return results

# ---------------------------
# Summarize & sentiment helpers
# ---------------------------
def summarize_descriptions(descriptions, max_articles=30):
    if not descriptions:
        return "No descriptions to summarize."
    # join top descriptions but keep it reasonable
    joined = " ".join(descriptions[:max_articles])
    # summarizer expects reasonably sized input; pass directly
    try:
        s = summarizer(joined, max_length=250, min_length=60, do_sample=False)[0]["summary_text"]
    except Exception as e:
        s = f"Summarization failed: {e}"
    return s

def analyze_sentiment(descriptions, max_articles=30):
    if not descriptions:
        return {"positive":0, "negative":0, "neutral":0, "overall":"NEUTRAL"}
    batch = descriptions[:max_articles]
    try:
        results = sentiment_analyzer(batch)
    except Exception as e:
        return {"positive":0, "negative":0, "neutral":0, "overall":f"error: {e}"}
    pos = neg = neu = 0
    for r in results:
        # HF sentiment labels often "POSITIVE"/"NEGATIVE"
        lbl = r.get("label","").upper()
        if "POS" in lbl:
            pos += 1
        elif "NEG" in lbl:
            neg += 1
        else:
            neu += 1
    overall = "BULLISH" if pos>neg else ("BEARISH" if neg>pos else "NEUTRAL")
    return {"positive":pos, "negative":neg, "neutral":neu, "overall":overall}

# ---------------------------
# PDF builder (executive summary)
# ---------------------------
def build_executive_pdf(summary_text, sentiment_summary, top_headlines, filename="executive_summary.pdf"):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 8, "Executive Summary — Crude Oil Market", ln=True)
    pdf.ln(4)

    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 6, f"Period: {period_from} to {period_to}")
    pdf.ln(4)

    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 6, "Top-line Summary:", ln=True)
    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 6, summary_text)
    pdf.ln(6)

    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 6, "Sentiment Snapshot:", ln=True)
    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 6, f"Positive: {sentiment_summary['positive']} | Negative: {sentiment_summary['negative']} | Neutral: {sentiment_summary['neutral']}")
    pdf.multi_cell(0, 6, f"Overall Market Sentiment: {sentiment_summary['overall']}")
    pdf.ln(6)

    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 6, "Top Headlines (by recency):", ln=True)
    pdf.set_font("Arial", "", 11)
    for i, h in enumerate(top_headlines[:10], 1):
        pdf.multi_cell(0, 6, f"{i}. {h}")
    pdf.output(filename)
    return filename

# ---------------------------
# Tagging helper (match which KEYWORD matched article)
# ---------------------------
def tag_article(title, description, keywords):
    text = " ".join([str(title or ""), str(description or "")]).lower()
    matched = [kw for kw in keywords if kw.lower() in text]
    return "; ".join(matched) if matched else ""

# ---------------------------
# UI: timeline selection & controls
# ---------------------------
st.sidebar.header("1) Select timeline")
timeline = st.sidebar.selectbox("Timeline range", ["Last 7 Days", "Last 14 Days", "Last 30 Days", "Last 60 Days"])
days_map = {"Last 7 Days":7, "Last 14 Days":14, "Last 30 Days":30, "Last 60 Days":60}
days = days_map[timeline]
period_to = datetime.utcnow().date()
period_from = (datetime.utcnow() - timedelta(days=days)).date()

st.sidebar.markdown(f"**Fetching articles from:** {period_from} → {period_to}")

st.sidebar.header("2) Options")
use_relevancy = st.sidebar.checkbox("Sort API queries by relevancy", value=True)
page_size = st.sidebar.slider("NewsAPI page size (per query)", 10, 100, 100, step=10)

if st.sidebar.button("🔎 Fetch & Analyze News"):
    start_time = time.time()
    st.info("Building keyword groups & fetching news...")

    groups = build_keyword_groups(KEYWORDS, max_chars=480)
    st.write(f"• Using {len(groups)} keyword group(s) to keep queries safe (NewsAPI limit).")

    all_articles = []
    progress = st.progress(0)
    total = len(groups)
    for idx, g in enumerate(groups):
        # ensure we pass raw string (requests will encode)
        query = g
        from_str = period_from.strftime("%Y-%m-%d")
        to_str = period_to.strftime("%Y-%m-%d")
        articles = fetch_articles_for_query(query, from_str, to_str, page_size=page_size)
        all_articles.extend(articles)
        progress.progress(int((idx+1)/total * 100))
        time.sleep(0.2)  # small pause to be gentle on API

    if not all_articles:
        st.warning("No articles found for the selected period and keywords.")
    else:
        # dedupe
        df = pd.DataFrame(all_articles)
        df = df.drop_duplicates(subset=["Title", "URL"])
        # format published date
        def fmt_date(x):
            try:
                return datetime.fromisoformat(x.replace("Z","")).strftime("%d-%m-%Y %H:%M:%S")
            except:
                return x
        df["Published At"] = df["Published At"].apply(fmt_date)

        # tag and sentiment per article (we do lightweight sentiment on descriptions)
        st.info("Tagging and running per-article sentiment (light).")
        summaries = []
        sentiments = []
        tags = []
        descriptions_list = []
        for _, row in df.iterrows():
            desc = row["Description"] if row["Description"] else ""
            descriptions_list.append(desc)
            # per-article sentiment (short)
            if desc:
                try:
                    sres = sentiment_analyzer(desc[:512])[0]
                    sentiments.append(sres.get("label"))
                except:
                    sentiments.append("UNKNOWN")
            else:
                sentiments.append("NO_DESC")
            # tags
            tags.append(tag_article(row["Title"], row["Description"], KEYWORDS))

        df["Sentiment"] = sentiments
        df["Tags"] = tags

        # Global summarization & sentiment summary
        st.info("Building combined summary and sentiment snapshot...")
        combined_summary = summarize_descriptions([d for d in descriptions_list if d], max_articles=30)
        sentiment_snapshot = analyze_sentiment([d for d in descriptions_list if d], max_articles=30)

        # Add one summary column per article by summarizing description (lighter)
        st.info("Generating short summaries for each article (may take some time)...")
        article_summaries = []
        # We'll try to summarize each description but keep it short and limited
        for desc in descriptions_list:
            if not desc:
                article_summaries.append("")
                continue
            try:
                s = summarizer(desc, max_length=50, min_length=10, do_sample=False)[0]["summary_text"]
                article_summaries.append(s)
            except:
                article_summaries.append("")
        df["Summary"] = article_summaries

        # Reorder columns to match requested output: Title | Description | Published At | Source | URL | Summary | Sentiment | Tags
        out_df = df[["Title", "Description", "Published At", "Source", "URL", "Summary", "Sentiment", "Tags"]]

        st.success(f"Fetched & processed {len(out_df)} unique articles in {int(time.time()-start_time)}s.")
        st.dataframe(out_df, use_container_width=True)

        # Excel download (same structure)
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            out_df.to_excel(writer, index=False, sheet_name="Articles")
            # also write a sheet with meta summary
            meta = pd.DataFrame([{
                "Period From": str(period_from),
                "Period To": str(period_to),
                "Fetched Articles": len(out_df),
                "Summary (excerpt)": combined_summary[:300],
                "Sentiment Overall": sentiment_snapshot["overall"],
                "Sentiment Positive": sentiment_snapshot["positive"],
                "Sentiment Negative": sentiment_snapshot["negative"],
                "Sentiment Neutral": sentiment_snapshot["neutral"]
            }])
            meta.to_excel(writer, index=False, sheet_name="Meta")
        output.seek(0)
        st.download_button(
            "📥 Download Results as Excel",
            data=output,
            file_name=f"crude_oil_news_{period_from}_{period_to}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # Executive summary PDF
        st.info("Generating Executive Summary PDF...")
        top_headlines = out_df["Title"].fillna("").tolist()
        pdf_name = f"executive_summary_{period_from}_{period_to}.pdf"
        try:
            build_executive_pdf(combined_summary, sentiment_snapshot, top_headlines, filename=pdf_name)
            with open(pdf_name, "rb") as f:
                st.download_button(
                    "📄 Download Executive Summary (PDF)",
                    data=f,
                    file_name=pdf_name,
                    mime="application/pdf"
                )
        except Exception as e:
            st.error(f"PDF generation failed: {e}")

        # Futuristic value-adds shown in UI
        st.markdown("### 🔮 Quick Insights (automated)")
        st.markdown(f"- **Top summary (auto):** {combined_summary[:400]}{'...' if len(combined_summary)>400 else ''}")
        st.markdown(f"- **Market sentiment (auto):** {sentiment_snapshot['overall']} (P:{sentiment_snapshot['positive']} / N:{sentiment_snapshot['negative']} / U:{sentiment_snapshot['neutral']})")
        # simple count of top tags
        tag_series = out_df["Tags"].str.split("; ").explode().value_counts().dropna()
        if not tag_series.empty:
            st.markdown("**Top Mentioned Benchmarks / Topics:**")
            for t, v in tag_series.head(10).items():
                if t:
                    st.write(f"- {t} — {v} mentions")
        else:
            st.write("- No topic tags matched strongly in headlines/descriptions.")

        st.balloons()

