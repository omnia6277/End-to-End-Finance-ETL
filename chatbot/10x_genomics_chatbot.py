import os
import pandas as pd
from flask import Flask, request, jsonify, render_template
from openai import OpenAI

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ★  PASTE YOUR GROK API KEY HERE  ★
#
#  Option A — hardcode it directly (quick and simple):
#     GROK_API_KEY = "xai-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
#
#  Option B — set it as an environment variable (recommended):
#     In your terminal: export GROK_API_KEY="xai-xxxx..."
#     Then leave the line below as-is.
#
GROK_API_KEY = os.environ.get("GROK_API_KEY", "PASTE_YOUR_KEY_HERE")
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

client = OpenAI(
    api_key=GROK_API_KEY,
    base_url="https://api.x.ai/v1",   # xAI / Grok endpoint
)

app = Flask(__name__)

# ── Load & build financial context ──────────────────────────────────────────
YEARS = ["FY 2019", "FY 2020", "FY 2021", "FY 2022", "FY 2023", "FY 2024", "FY 2025"]
BS_YEARS = ["Q4 2019", "Q4 2020", "Q4 2021", "Q4 2022", "Q4 2023", "Q4 2024", "Q4 2025"]

def load_sheet(path):
    df = pd.read_excel(path, header=None)
    rows = {}
    for _, row in df.iterrows():
        key = str(row[0]).strip() if pd.notna(row[0]) else ""
        if key and key not in ("", "nan", "Data Model"):
            vals = []
            for v in row[1:]:
                if pd.notna(v):
                    vals.append(round(float(v), 3) if isinstance(v, (int, float)) else v)
                else:
                    vals.append(None)
            rows[key] = vals
    return rows

pl  = load_sheet(f"C:/Users/Admin/OneDrive/Desktop/10x-Genomics-Project/raw data/TXG_PL.xlsx")
bs  = load_sheet(f"C:/Users/Admin/OneDrive/Desktop/10x-Genomics-Project/raw data/TXG_BS.xlsx")
cf  = load_sheet(f"C:/Users/Admin/OneDrive/Desktop/10x-Genomics-Project/raw data/TXG_CF.xlsx")
drv = load_sheet(f"C:/Users/Admin/OneDrive/Desktop/10x-Genomics-Project/raw data/TXG_DERIVED.xlsx")

def fmt_table(label, metrics, years):
    lines = [f"\n### {label}", "| Metric | " + " | ".join(years) + " |",
             "|---|" + "---|" * len(years)]
    for name, vals in metrics.items():
        row = [str(v) if v is not None else "—" for v in vals]
        lines.append(f"| {name} | " + " | ".join(row) + " |")
    return "\n".join(lines)

def build_context():
    # P&L key metrics ($ millions)
    pl_metrics = {
        "Revenue ($M)": pl.get("Revenue", []),
        "Cost of Revenue ($M)": pl.get("Cost of revenue", []),
        "Gross Profit ($M)": pl.get("Gross Profit", []),
        "Operating Expenses ($M)": pl.get("Operating Expenses", []),
        "SG&A ($M)": pl.get("Selling, General & Administrative", []),
        "R&D ($M)": pl.get("Research & Development", []),
        "Operating Income ($M)": pl.get("Operating Income (Loss)", []),
        "Pretax Income ($M)": pl.get("Pretax Income (Loss)", []),
        "Net Income ($M)": pl.get("Net Income", []),
        "Income from Continuing Operations ($M)": pl.get("Income (Loss) from Continuing Operations", []),
        "Abnormal Gains/Losses ($M)": pl.get("Abnormal Gains (Losses)", []),
    }
    bs_metrics = {
        "Cash & Equivalents ($M)": bs.get("Cash & Cash Equivalents", []),
        "Cash + Short-Term Investments ($M)": bs.get("Cash, Cash Equivalents & Short Term Investments", []),
        "Short Term Investments ($M)": bs.get("Short Term Investments", []),
        "Accounts Receivable ($M)": bs.get("Accounts Receivable, Net", []),
        "Inventories ($M)": bs.get("Inventories", []),
        "Total Current Assets ($M)": bs.get("Total Current Assets", []),
        "PP&E Net ($M)": bs.get("Property, Plant & Equipment, Net", []),
        "Total Assets ($M)": bs.get("Total Assets", []),
        "Accounts Payable ($M)": bs.get("Accounts Payable", []),
        "Total Current Liabilities ($M)": bs.get("Total Current Liabilities", []),
        "Total Liabilities ($M)": bs.get("Total Liabilities", []),
        "Total Equity ($M)": bs.get("Total Equity", []),
        "Retained Earnings ($M)": bs.get("Retained Earnings", []),
        "Share Capital & APIC ($M)": bs.get("Share Capital & Additional Paid-In Capital", []),
    }
    cf_metrics = {
        "Cash from Operations ($M)": cf.get("Cash from Operating Activities", []),
        "Cash from Investing ($M)": cf.get("Cash from Investing Activities", []),
        "Cash from Financing ($M)": cf.get("Cash from Financing Activities", []),
        "Net Changes in Cash ($M)": cf.get("Net Changes in Cash", []),
        "D&A ($M)": cf.get("Depreciation & Amortization", []),
        "Non-Cash Items ($M)": cf.get("Non-Cash Items", []),
        "Change in Working Capital ($M)": cf.get("Change in Working Capital", []),
        "CapEx / Fixed Assets ($M)": cf.get("Change in Fixed Assets & Intangibles", []),
        "Equity Raised ($M)": cf.get("Cash From (Repurchase of) Equity", []),
    }
    drv_metrics = {
        "Gross Profit Margin": drv.get("Gross Profit Margin", []),
        "Operating Margin": drv.get("Operating Margin", []),
        "Net Profit Margin": drv.get("Net Profit Margin", []),
        "EBITDA ($M)": drv.get("EBITDA", []),
        "EPS (Basic)": drv.get("Earnings Per Share, Basic", []),
        "Free Cash Flow ($M)": drv.get("Free Cash Flow", []),
        "FCF Per Share": drv.get("Free Cash Flow Per Share", []),
        "Current Ratio": drv.get("Current Ratio", []),
        "Return on Equity": drv.get("Return on Equity", []),
        "Return on Assets": drv.get("Return on Assets", []),
        "ROIC": drv.get("Return On Invested Capital", []),
        "Net Debt / EBITDA": drv.get("Net Debt / EBITDA", []),
        "Liabilities to Equity Ratio": drv.get("Liabilities to Equity Ratio", []),
        "Piotroski F-Score": drv.get("Piotroski F-Score", []),
        "Sales Per Share": drv.get("Sales Per Share", []),
        "Equity Per Share": drv.get("Equity Per Share", []),
        "Total Debt ($M)": drv.get("Total Debt", []),
        "Net Income Adjusted ($M)": drv.get("Net Income (Adjusted)", []),
    }

    context = """You are a highly skilled financial analyst specializing in 10x Genomics, Inc. (TXG).
You have access to their complete audited financial statements from FY 2019 through FY 2025.
All monetary values are in USD millions ($ millions) unless otherwise noted.
The Balance Sheet uses year-end dates (Q4). All other statements use full fiscal year (FY) figures.
Answer questions with precision, cite specific figures, calculate growth rates or ratios when helpful,
and always contextualize numbers (e.g., what they mean for the business, trends, concerns).

== COMPANY OVERVIEW ==
10x Genomics is a life science tools company that develops and sells instruments, software, and consumables
for genomic analysis. Founded in 2012, IPO'd in 2019. Known for its Chromium (single-cell), Visium (spatial),
and Xenium (in-situ) platforms.

"""
    context += fmt_table("INCOME STATEMENT (P&L) — FY 2019–2025 ($M)", pl_metrics, YEARS)
    context += fmt_table("BALANCE SHEET — Q4 2019–2025 ($M)", bs_metrics, BS_YEARS)
    context += fmt_table("CASH FLOW STATEMENT — FY 2019–2025 ($M)", cf_metrics, YEARS)
    context += fmt_table("DERIVED / RATIO METRICS — FY 2019–2025", drv_metrics, YEARS)

    context += """

== NOTES ==
- Abnormal gains/losses in 2020 (-449.1M) include litigation/settlement charges.
- Abnormal gains/losses in 2023 (-61.0M) and 2025 (+49.9M) are one-time items.
- Company has never paid dividends.
- Total debt became zero after 2019 (fully repaid).
- Stock-based compensation is a major non-cash charge included in Non-Cash Items.
- Free Cash Flow = Cash from Operations - CapEx.
- All margins are expressed as decimals (e.g., 0.75 = 75%).
"""
    return context

SYSTEM_PROMPT = build_context()

# ── Routes ────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    history = data.get("history", [])
    user_msg = data.get("message", "").strip()
    if not user_msg:
        return jsonify({"error": "Empty message"}), 400

    messages = (
        [{"role": "system", "content": SYSTEM_PROMPT}]
        + history
        + [{"role": "user", "content": user_msg}]
    )

    try:
        response = client.chat.completions.create(
            model="grok-3",
            max_tokens=1500,
            messages=messages,
        )
        reply = response.choices[0].message.content
        return jsonify({"reply": reply})
    except Exception as e:
        print(f"ERROR: {e}")
        return jsonify({"reply": f"API Error: {str(e)}"}), 500

if __name__ == "__main__":
    print("Starting TXG Financial Chatbot on http://localhost:5000")
    app.run(debug=False, port=5000)
