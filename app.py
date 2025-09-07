import requests
import pandas as pd
from collections import Counter
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

# ========== CONFIG ==========
API_KEY = "5atw17pic36k8mh0oqld4zw5nmkx8csn"
BASE_URL = "https://sparkuatapi.spglobal.com/news"
LLM_URL = "https://sparkuatapi.spglobal.com/ai/summarize"

KEYWORD_GROUPS = [
    ["crude oil", "oil price", "WTI", "Brent crude", "OPEC", "oil demand"],
    ["oil supply", "geopolitics oil", "Middle East oil", "oil production cuts"],
    ["EIA report", "IEA report", "API inventory", "US crude stocks"],
    ["refinery margins", "crack spread", "diesel prices", "gasoline prices"]
]

DAYS_BACK = 7
EXCEL_FILE = "crude_oil_news.xlsx"
PDF_FILE = "crude_oil_report.pdf"

# ========== FETCH NEWS ==========
def fetch_news(keywords):
    query = " OR ".join(keywords)
    url = f"{BASE_URL}/search"
    headers = {"Authorization": f"Bearer {API_KEY}"}
    params = {
        "q": query,
        "from": (datetime.utcnow() - timedelta(days=DAYS_BACK)).strftime("%Y-%m-%d"),
        "to": datetime.utcnow().strftime("%Y-%m-%d"),
        "sortBy": "publishedAt",
        "language": "en",
        "pageSize": 20
    }
    resp = requests.get(url, headers=headers, params=params)
    if resp.status_code != 200:
        print(f"❌ Failed to fetch news: {resp.status_code} - {resp.text}")
        return []
    return resp.json().get("articles", [])

def get_all_articles():
    all_articles = []
    seen_titles = set()
    for group in KEYWORD_GROUPS:
        articles = fetch_news(group)
        for a in articles:
            if a["title"] not in seen_titles:
                seen_titles.add(a["title"])
                all_articles.append(a)
    return all_articles

# ========== SUMMARIZATION ==========
def summarize_with_llm(texts):
    payload = {
        "model": "spg-ai-summarizer",
        "input": texts,
        "task": "summarize"
    }
    headers = {"Authorization": f"Bearer {API_KEY}"}
    resp = requests.post(LLM_URL, json=payload, headers=headers)
    if resp.status_code != 200:
        print(f"❌ Summarization failed: {resp.status_code} - {resp.text}")
        return "Summary unavailable."
    return resp.json().get("summary", "No summary returned.")

# ========== SENTIMENT & DRIVERS ==========
def classify_sentiment(description):
    desc = description.lower()
    if any(w in desc for w in ["rise", "increase", "higher", "up", "bullish"]):
        return "Bullish"
    elif any(w in desc for w in ["fall", "drop", "lower", "down", "bearish"]):
        return "Bearish"
    else:
        return "Neutral"

def extract_drivers(articles):
    drivers = Counter()
    for a in articles:
        desc = a.get("description", "").lower()
        for keyword in ["opec", "demand", "supply", "inventory", "geopolitical", "refinery", "china", "us", "russia"]:
            if keyword in desc:
                drivers[keyword] += 1
    return drivers.most_common()

# ========== EXCEL EXPORT ==========
def export_to_excel(articles):
    df = pd.DataFrame([{
        "Title": a.get("title"),
        "Published Date": a.get("publishedAt"),
        "Description": a.get("description"),
        "Sentiment": classify_sentiment(a.get("description", "")),
        "Source": a.get("source", {}).get("name", ""),
        "URL": a.get("url", "")
    } for a in articles])
    df.to_excel(EXCEL_FILE, index=False)
    print(f"📊 Excel report saved: {EXCEL_FILE}")
    return df

# ========== PDF REPORT ==========
def export_to_pdf(summary, sentiments, drivers, articles):
    doc = SimpleDocTemplate(PDF_FILE, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("📊 Crude Oil Price Analysis Report", styles["Title"]))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"Date: {datetime.utcnow().strftime('%Y-%m-%d')}", styles["Normal"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("📰 News Summary", styles["Heading2"]))
    story.append(Paragraph(summary, styles["Normal"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("📈 Market Sentiment", styles["Heading2"]))
    sentiment_table = Table([
        ["Bullish", sentiments["Bullish"]],
        ["Bearish", sentiments["Bearish"]],
        ["Neutral", sentiments["Neutral"]],
    ])
    sentiment_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.grey),
        ("TEXTCOLOR",(0,0),(-1,0),colors.whitesmoke),
        ("ALIGN",(0,0),(-1,-1),"CENTER"),
        ("GRID",(0,0),(-1,-1),0.5,colors.black)
    ]))
    story.append(sentiment_table)
    story.append(Spacer(1, 12))

    story.append(Paragraph("🔑 Key Drivers", styles["Heading2"]))
    driver_data = [["Driver", "Mentions"]] + drivers
    driver_table = Table(driver_data)
    driver_table.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),colors.lightblue),
        ("GRID",(0,0),(-1,-1),0.5,colors.black)
    ]))
    story.append(driver_table)
    story.append(Spacer(1, 12))

    story.append(Paragraph("🗞 Sample Headlines", styles["Heading2"]))
    for a in articles[:10]:
        story.append(Paragraph(f"- {a['title']} ({a['publishedAt'][:10]})", styles["Normal"]))

    doc.build(story)
    print(f"📑 PDF report saved: {PDF_FILE}")

# ========== MAIN ==========
def run_analysis():
    print("🔎 Fetching crude oil news...")
    articles = get_all_articles()
    if not articles:
        print("⚠️ No articles found.")
        return

    print(f"✅ Retrieved {len(articles)} unique articles.")

    # Summarize
    descriptions = [a.get("description", "") for a in articles if a.get("description")]
    summary = summarize_with_llm(" ".join(descriptions[:2000]))

    # Sentiment
    sentiments = Counter([classify_sentiment(a.get("description", "")) for a in articles])

    # Drivers
    drivers = extract_drivers(articles)

    # Export
    export_to_excel(articles)
    export_to_pdf(summary, sentiments, drivers, articles)

if __name__ == "__main__":
    run_analysis()

