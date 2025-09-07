# app.py
import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
from io import BytesIO
import urllib.parse
import time
import zipfile
from fpdf import FPDF
import math
import re
from collections import Counter, defaultdict

# lightweight NLP
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.sentiment import SentimentIntensityAnalyzer

# ---------------------------
# Ensure NLTK data is present (first-run will download)
# ---------------------------
nltk_packages = ["punkt", "stopwords", "vader_lexicon"]
for pkg in nltk_packages:
    try:
        nltk.data.find(pkg if pkg != "vader_lexicon" else "sentiment/vader_lexicon")
    except Exception:
        nltk.download(pkg)

# ---------------------------
# CONFIG
# ---------------------------
st.set_page_config(page_title="Crude Oil News Research (Fast Summaries)", layout="wide")
st.title("🛢️ Crude Oil News Research — Fast Global Summary & Report")

NEWSAPI_KEY = "3087034a13564f75bfc769c0046e729c"  # <-- Replace with your NewsAPI key
NEWSAPI_URL = "https://newsapi.org/v2/everything"

# ---------------------------
# ULTRA-PRECISE KEYWORDS (safe groups will be built)
# ---------------------------
KEYWORDS = [
    # Benchmarks & grades
    "Brent crude", "WTI crude", "Dated Brent", "Urals crude", "Dubai crude", "Oman crude",
    "Basrah Heavy", "ESPO", "Murban", "Bonny Light", "Mexican Maya", "Forties",

    # Pricing & instruments
    "crude oil price", "oil price", "ICE Brent futures", "NYMEX WTI", "oil futures",
    "oil spot price", "forward curve", "crude spreads", "crude differential",

    # Providers & reports
    "Platts", "Argus", "S&P Global Platts", "IEA oil report", "EIA weekly", "OPEC monthly",

    # Supply/demand & drivers
    "OPEC", "OPEC+", "production cuts", "output cuts", "supply disruption",
    "oil inventories", "API crude", "US SPR release", "strategic petroleum reserve",

    # Trade & consumption
    "China crude imports", "India crude imports", "US crude exports",

    # Refining & shipping
    "refinery outage", "refinery margins", "crack spread", "floating storage",
    "tanker rates", "voyage charter rates",

    # Market structure
    "contango", "backwardation", "price volatility", "benchmark"
]

# ---------------------------
# Helpers: split keywords into safe query groups (< 480 chars)
# ---------------------------
def build_keyword_groups(keywords, max_chars=480):
    groups = []
    cur = []
    cur_len = 0
    for kw in keywords:
        piece = f'"{kw}" OR '
        if cur_len + len(piece) > max_chars and cur:
            groups.append(" OR ".join([f'"{k}"' for k in cur]).rstrip(" OR"))
            cur = [kw]
            cur_len = len(piece)
        else:
            cur.append(kw)
            cur_len += len(piece)
    if cur:
        groups.append(" OR ".join([f'"{k}"' for k in cur]).rstrip(" OR"))
    # final safety: strip trailing OR / spaces
    groups = [g.strip().rstrip("OR").strip() for g in groups]
    return groups

# ---------------------------
# NewsAPI fetch (single query)
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
        r = requests.get(NEWSAPI_URL, params=params, timeout=20)
    except Exception as e:
        st.error(f"Network/API error when calling NewsAPI: {e}")
        return []
    if r.status_code != 200:
        st.error(f"Failed to fetch: {r.status_code} - {r.text}")
        return []
    try:
        resp = r.json()
    except Exception:
        st.error("Failed to parse NewsAPI JSON response.")
        return []
    articles = resp.get("articles", []) or []
    rows = []
    for a in articles:
        rows.append({
            "Title": a.get("title"),
            "Description": a.get("description"),
            "Published At": a.get("publishedAt"),
            "Source": a.get("source", {}).get("name"),
            "URL": a.get("url")
        })
    return rows

# ---------------------------
# Text cleaning & sentence scoring summarizer (fast, extractive)
# ---------------------------
STOPWORDS = set(stopwords.words("english"))

def clean_text(text):
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def score_sentences_by_tf(text, top_n=6):
    """
    Very lightweight extractive summarizer:
      - tokenize sentences
      - compute word frequency (term frequency)
      - score sentences by sum(freq of words in sentence)
      - return top_n sentences in the original order
    """
    if not text:
        return ""

    # Split into sentences
    sentences = sent_tokenize(text)
    if len(sentences) <= top_n:
        return " ".join([s.strip() for s in sentences])

    # Build frequency table
    freq = Counter()
    for sent in sentences:
        for w in word_tokenize(sent.lower()):
            w = re.sub(r'[^a-z0-9\-]', '', w)
            if not w or w.isnumeric() or w in STOPWORDS:
                continue
            freq[w] += 1

    if not freq:
        # fallback: return first few sentences
        return " ".join(sentences[:top_n])

    # Normalize frequencies
    max_freq = max(freq.values())
    for k in list(freq.keys()):
        freq[k] = freq[k] / max_freq

    # Score sentences
    sent_scores = {}
    for i, sent in enumerate(sentences):
        score = 0.0
        for w in word_tokenize(sent.lower()):
            w = re.sub(r'[^a-z0-9\-]', '', w)
            if w in freq:
                score += freq[w]
        # Penalize extremely short sentences
        sent_scores[i] = score * (len(sent.split())**0.5)

    # select top_n sentence indices
    top_idx = sorted(sent_scores, key=sent_scores.get, reverse=True)[:top_n]
    top_idx_sorted = sorted(top_idx)
    summary = " ".join([sentences[i].strip() for i in top_idx_sorted])
    return summary

# ---------------------------
# Sentiment: NLTK VADER (fast)
# ---------------------------
sia = SentimentIntensityAnalyzer()

def overall_sentiment(descriptions):
    """
    descriptions: list of strings
    returns counts and overall label
    """
    pos = neg = neu = 0
    for d in descriptions:
        if not d or not d.strip():
            continue
        sc = sia.polarity_scores(d)
        comp = sc["compound"]
        if comp >= 0.05:
            pos += 1
        elif comp <= -0.05:
            neg += 1
        else:
            neu += 1
    total = pos + neg + neu
    if total == 0:
        return {"positive":0,"negative":0,"neutral":0,"overall":"NEUTRAL"}
    overall = "BULLISH" if pos > neg else ("BEARISH" if neg > pos else "NEUTRAL")
    return {"positive":pos,"negative":neg,"neutral":neu,"overall":overall}

# ---------------------------
# PDF builder
# ---------------------------
def build_executive_pdf(period_from, period_to, summary_text, sentiment_summary, top_headlines, key_drivers, filename="executive_summary.pdf"):
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

    if key_drivers:
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 6, "Key Drivers (top terms):", ln=True)
        pdf.set_font("Arial", "", 11)
        pdf.multi_cell(0, 6, ", ".join(key_drivers[:20]))
        pdf.ln(6)

    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 6, "Top Headlines:", ln=True)
    pdf.set_font("Arial", "", 11)
    for i, h in enumerate(top_headlines[:12], 1):
        pdf.multi_cell(0, 6, f"{i}. {h}")
    pdf.output(filename)
    return filename

# ---------------------------
# Tagging helper (optional)
# ---------------------------
def tag_article(title, description, keywords):
    text = f"{title or ''} {description or ''}".lower()
    matched = [kw for kw in keywords if kw.lower() in text]
    return "; ".join(matched) if matched else ""

# ---------------------------
# UI - Controls
# ---------------------------
st.sidebar.header("Options")
timeline = st.sidebar.selectbox("Select timeline", ["Last 7 Days", "Last 14 Days", "Last 30 Days", "Last 60 Days"])
days_map = {"Last 7 Days":7, "Last 14 Days":14, "Last 30 Days":30, "Last 60 Days":60}
days = days_map[timeline]

period_to = datetime.utcnow().date()
period_from = (datetime.utcnow() - timedelta(days=days)).date()

st.sidebar.write(f"Fetching from **{period_from}** to **{period_to}**")

page_size = st.sidebar.slider("NewsAPI page size (per query)", min_value=20, max_value=100, value=100, step=10)
max_summary_sentences = st.sidebar.slider("Summary sentences (global)", 3, 8, 5)

if st.sidebar.button("Fetch & Build Report"):
    if NEWSAPI_KEY == "YOUR_NEWSAPI_KEY" or not NEWSAPI_KEY:
        st.error("Please set your NewsAPI key in NEWSAPI_KEY variable inside the script.")
    else:
        start = time.time()
        st.info("Building keyword groups (to avoid NewsAPI query length limit)...")
        groups = build_keyword_groups(KEYWORDS, max_chars=480)
        st.write(f"Using {len(groups)} keyword group(s).")

        all_articles = []
        p = st.progress(0)
        for i, g in enumerate(groups):
            from_str = period_from.strftime("%Y-%m-%d")
            to_str = period_to.strftime("%Y-%m-%d")
            # query is raw; requests will encode appropriately
            articles = fetch_articles_for_query(g, from_str, to_str, page_size=page_size)
            all_articles.extend(articles)
            p.progress((i+1)/len(groups))
            time.sleep(0.15)

        if not all_articles:
            st.warning("No articles found for the selected period / keywords.")
        else:
            # dedupe by Title + URL
            df = pd.DataFrame(all_articles).drop_duplicates(subset=["Title","URL"]).reset_index(drop=True)

            # format Published At
            def fmt_date(x):
                try:
                    return datetime.fromisoformat(x.replace("Z","")).strftime("%Y-%m-%d %H:%M:%S")
                except:
                    return x
            df["Published At"] = df["Published At"].apply(lambda x: fmt_date(x) if pd.notna(x) else x)

            # Tags (which keywords matched)
            df["Tags"] = df.apply(lambda r: tag_article(r["Title"], r["Description"], KEYWORDS), axis=1)

            # Display table (same core columns)
            out_df = df[["Title","Description","Published At","Source","URL","Tags"]]
            st.success(f"Fetched {len(out_df)} unique articles.")
            st.dataframe(out_df, use_container_width=True)

            # Prepare descriptions list (non-empty)
            descriptions = [clean_text(d) for d in out_df["Description"].fillna("").tolist() if d and d.strip()]

            # Global summary (fast extractor)
            combined_text = " ".join(descriptions)
            # Use sentence scoring summarizer
            global_summary = score_sentences_by_tf(combined_text, top_n=max_summary_sentences)

            # Sentiment summary (VADER)
            sentiment_summary = overall_sentiment(descriptions)

            # Key drivers: top frequent non-stopwords
            word_counts = Counter()
            for d in descriptions:
                for w in word_tokenize(d.lower()):
                    w = re.sub(r'[^a-z0-9\-]', '', w)
                    if not w or w.isnumeric() or w in STOPWORDS:
                        continue
                    word_counts[w] += 1
            top_drivers = [w for w, _ in word_counts.most_common(30)]

            # Write Excel to BytesIO (Articles sheet + Meta sheet)
            excel_io = BytesIO()
            with pd.ExcelWriter(excel_io, engine="openpyxl") as writer:
                out_df.to_excel(writer, index=False, sheet_name="Articles")
                meta = pd.DataFrame([{
                    "Period From": str(period_from),
                    "Period To": str(period_to),
                    "Fetched Articles": len(out_df),
                    "Summary (excerpt)": global_summary[:500],
                    "Sentiment Overall": sentiment_summary["overall"],
                    "Sentiment Positive": sentiment_summary["positive"],
                    "Sentiment Negative": sentiment_summary["negative"],
                    "Sentiment Neutral": sentiment_summary["neutral"]
                }])
                meta.to_excel(writer, index=False, sheet_name="Meta")
            excel_io.seek(0)

            # Build PDF executive summary
            top_headlines = out_df["Title"].fillna("").tolist()
            pdf_name = f"executive_summary_{period_from}_{period_to}.pdf"
            try:
                build_executive_pdf(str(period_from), str(period_to), global_summary, sentiment_summary, top_headlines, top_drivers, filename=pdf_name)
            except Exception as e:
                st.error(f"PDF generation failed: {e}")
                pdf_name = None

            # Create zip containing excel + pdf (or individual downloads)
            zip_io = BytesIO()
            with zipfile.ZipFile(zip_io, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
                zf.writestr(f"crude_oil_articles_{period_from}_{period_to}.xlsx", excel_io.getvalue())
                if pdf_name:
                    with open(pdf_name, "rb") as f:
                        zf.writestr(pdf_name, f.read())
            zip_io.seek(0)

            # Provide downloads
            st.download_button("📥 Download Excel (Articles + Meta)", data=excel_io, file_name=f"crude_oil_articles_{period_from}_{period_to}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            if pdf_name:
                with open(pdf_name, "rb") as f:
                    st.download_button("📄 Download Executive Summary (PDF)", data=f, file_name=pdf_name, mime="application/pdf")
            st.download_button("🗂️ Download ZIP (Excel + PDF)", data=zip_io, file_name=f"crude_oil_report_{period_from}_{period_to}.zip", mime="application/zip")

            # Quick insights in UI
            st.markdown("### 🔎 Quick Insights (automated)")
            st.markdown(f"- **Top-line Summary:** {global_summary}")
            st.markdown(f"- **Market Sentiment:** {sentiment_summary['overall']} (P:{sentiment_summary['positive']} / N:{sentiment_summary['negative']} / U:{sentiment_summary['neutral']})")
            if top_drivers:
                st.markdown("**Top detected drivers (keywords):**")
                st.write(", ".join(top_drivers[:20]))

            st.balloons()
            st.success("Report ready!")

