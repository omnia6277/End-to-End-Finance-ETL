"""
10x Genomics Financial Chatbot
Answers are grounded in your actual Excel financial files.
Run: python TXG_chatbot.py
Then open: http://localhost:5000
"""

from flask import Flask, render_template_string, request, jsonify
from groq import Groq
import os
import pandas as pd

app = Flask(__name__)

# ─── CONFIG ───────────────────────────────────────────────────────────────────
GROQ_API_KEY = "gsk_your_groq_key_here"       # ← paste your key here

# ★ UPDATE THESE PATHS TO WHERE YOUR 4 EXCEL FILES ARE ★
DATA_DIR = r"C:\Users\Admin\OneDrive\Desktop\10x-Genomics-Project\raw data"
# ──────────────────────────────────────────────────────────────────────────────


# ═══════════════════════════════════════════════════════════════════════════════
#  LOAD ALL EXCEL FILES INTO MEMORY AT STARTUP
# ═══════════════════════════════════════════════════════════════════════════════

YEARS    = ["FY2019", "FY2020", "FY2021", "FY2022", "FY2023", "FY2024", "FY2025"]
BS_YEARS = ["Q42019", "Q42020", "Q42021", "Q42022", "Q42023", "Q42024", "Q42025"]

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

def load_data():
    files = {
        "pl":  "TXG_PL.xlsx",
        "bs":  "TXG_BS.xlsx",
        "cf":  "TXG_CF.xlsx",
        "drv": "TXG_DERIVED.xlsx",
    }
    tables = {}
    for key, fname in files.items():
        path = os.path.join(DATA_DIR, fname)
        tables[key] = load_sheet(path)
        print(f"  ✅ Loaded {fname} ({len(tables[key])} rows)")
    return tables

DATA = load_data()


# ═══════════════════════════════════════════════════════════════════════════════
#  DATA QUERY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def fmt_row(label, values, years):
    parts = [f"{y}: {v if v is not None else 'N/A'}" for y, v in zip(years, values)]
    return f"{label}: " + " | ".join(parts)

def get_revenue():
    vals = DATA["pl"].get("Revenue", [])
    lines = [fmt_row("Revenue ($M)", vals, YEARS)]
    gp    = DATA["pl"].get("Gross Profit", [])
    lines.append(fmt_row("Gross Profit ($M)", gp, YEARS))
    # growth rates
    growth = []
    for i in range(1, len(vals)):
        if vals[i-1] and vals[i]:
            g = round((vals[i] - vals[i-1]) / abs(vals[i-1]) * 100, 1)
            growth.append(f"{YEARS[i]}: {g}%")
    lines.append("Revenue YoY Growth: " + " | ".join(growth))
    return "REVENUE & GROSS PROFIT:\n" + "\n".join(lines)

def get_margins():
    gm  = DATA["drv"].get("Gross Profit Margin", [])
    om  = DATA["drv"].get("Operating Margin", [])
    nm  = DATA["drv"].get("Net Profit Margin", [])
    lines = [
        fmt_row("Gross Margin", [f"{round(v*100,1)}%" if v else "N/A" for v in gm], YEARS),
        fmt_row("Operating Margin", [f"{round(v*100,1)}%" if v else "N/A" for v in om], YEARS),
        fmt_row("Net Margin", [f"{round(v*100,1)}%" if v else "N/A" for v in nm], YEARS),
    ]
    return "PROFITABILITY MARGINS:\n" + "\n".join(lines)

def get_income_statement():
    metrics = ["Revenue", "Cost of revenue", "Gross Profit",
               "Operating Expenses", "Operating Income (Loss)",
               "Pretax Income (Loss)", "Net Income"]
    lines = []
    for m in metrics:
        v = DATA["pl"].get(m, [])
        if v:
            lines.append(fmt_row(f"{m} ($M)", v, YEARS))
    return "INCOME STATEMENT:\n" + "\n".join(lines)

def get_expenses():
    rd  = DATA["pl"].get("Research & Development", [])
    sga = DATA["pl"].get("Selling, General & Administrative", [])
    opex= DATA["pl"].get("Operating Expenses", [])
    rev = DATA["pl"].get("Revenue", [])
    lines = [
        fmt_row("R&D ($M)", rd, YEARS),
        fmt_row("SG&A ($M)", sga, YEARS),
        fmt_row("Total OpEx ($M)", opex, YEARS),
    ]
    # R&D as % of revenue
    rd_pct = []
    for r, v in zip(rev, rd):
        if r and v:
            rd_pct.append(f"{round(v/r*100,1)}%")
        else:
            rd_pct.append("N/A")
    lines.append(fmt_row("R&D % of Revenue", rd_pct, YEARS))
    return "OPERATING EXPENSES:\n" + "\n".join(lines)

def get_balance_sheet():
    metrics = [
        ("Cash & Cash Equivalents", "bs"),
        ("Cash, Cash Equivalents & Short Term Investments", "bs"),
        ("Total Current Assets", "bs"),
        ("Total Assets", "bs"),
        ("Total Current Liabilities", "bs"),
        ("Total Liabilities", "bs"),
        ("Total Equity", "bs"),
        ("Retained Earnings", "bs"),
    ]
    lines = []
    for m, src in metrics:
        v = DATA[src].get(m, [])
        if v:
            lines.append(fmt_row(f"{m} ($M)", v, BS_YEARS))
    return "BALANCE SHEET (year-end):\n" + "\n".join(lines)

def get_cash_flow():
    metrics = [
        "Cash from Operating Activities",
        "Cash from Investing Activities",
        "Cash from Financing Activities",
        "Net Changes in Cash",
        "Depreciation & Amortization",
        "Change in Fixed Assets & Intangibles",
    ]
    lines = []
    for m in metrics:
        v = DATA["cf"].get(m, [])
        if v:
            lines.append(fmt_row(f"{m} ($M)", v, YEARS))
    return "CASH FLOW STATEMENT:\n" + "\n".join(lines)

def get_fcf():
    fcf  = DATA["drv"].get("Free Cash Flow", [])
    fcfps= DATA["drv"].get("Free Cash Flow Per Share", [])
    cfo  = DATA["cf"].get("Cash from Operating Activities", [])
    lines = [
        fmt_row("Free Cash Flow ($M)", fcf, YEARS),
        fmt_row("FCF Per Share", fcfps, YEARS),
        fmt_row("Cash from Operations ($M)", cfo, YEARS),
    ]
    return "FREE CASH FLOW:\n" + "\n".join(lines)

def get_key_ratios():
    metrics = [
        ("Current Ratio",         "drv"),
        ("Return on Equity",      "drv"),
        ("Return on Assets",      "drv"),
        ("Return On Invested Capital", "drv"),
        ("Liabilities to Equity Ratio","drv"),
        ("Net Debt / EBITDA",     "drv"),
        ("Piotroski F-Score",     "drv"),
    ]
    lines = []
    for m, src in metrics:
        v = DATA[src].get(m, [])
        if v:
            lines.append(fmt_row(m, v, YEARS))
    return "KEY FINANCIAL RATIOS:\n" + "\n".join(lines)

def get_ebitda():
    ebitda = DATA["drv"].get("EBITDA", [])
    da     = DATA["cf"].get("Depreciation & Amortization", [])
    oi     = DATA["pl"].get("Operating Income (Loss)", [])
    lines = [
        fmt_row("EBITDA ($M)", ebitda, YEARS),
        fmt_row("D&A ($M)", da, YEARS),
        fmt_row("Operating Income ($M)", oi, YEARS),
    ]
    return "EBITDA ANALYSIS:\n" + "\n".join(lines)

def get_per_share():
    metrics = [
        ("Earnings Per Share, Basic", "drv"),
        ("Sales Per Share",           "drv"),
        ("Equity Per Share",          "drv"),
        ("Free Cash Flow Per Share",  "drv"),
    ]
    lines = []
    for m, src in metrics:
        v = DATA[src].get(m, [])
        if v:
            lines.append(fmt_row(m, v, YEARS))
    return "PER SHARE METRICS:\n" + "\n".join(lines)

def get_net_income():
    ni    = DATA["pl"].get("Net Income", [])
    ni_adj= DATA["drv"].get("Net Income (Adjusted)", [])
    abn   = DATA["pl"].get("Abnormal Gains (Losses)", [])
    lines = [
        fmt_row("Net Income ($M)", ni, YEARS),
        fmt_row("Net Income Adjusted ($M)", ni_adj, YEARS),
        fmt_row("Abnormal Gains/Losses ($M)", abn, YEARS),
    ]
    return "NET INCOME:\n" + "\n".join(lines)

def get_cash_position():
    cash  = DATA["bs"].get("Cash & Cash Equivalents", [])
    sti   = DATA["bs"].get("Short Term Investments", [])
    total = DATA["bs"].get("Cash, Cash Equivalents & Short Term Investments", [])
    lines = [
        fmt_row("Cash & Equivalents ($M)", cash, BS_YEARS),
        fmt_row("Short Term Investments ($M)", sti, BS_YEARS),
        fmt_row("Total Liquidity ($M)", total, BS_YEARS),
    ]
    return "CASH POSITION:\n" + "\n".join(lines)

def get_debt_equity():
    equity = DATA["bs"].get("Total Equity", [])
    liab   = DATA["bs"].get("Total Liabilities", [])
    debt   = DATA["drv"].get("Total Debt", [])
    de     = DATA["drv"].get("Liabilities to Equity Ratio", [])
    lines = [
        fmt_row("Total Equity ($M)", equity, BS_YEARS),
        fmt_row("Total Liabilities ($M)", liab, BS_YEARS),
        fmt_row("Total Debt ($M)", debt, YEARS),
        fmt_row("Liabilities/Equity Ratio", de, YEARS),
    ]
    return "DEBT & EQUITY:\n" + "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
#  SMART CONTEXT BUILDER — picks relevant data based on the question
# ═══════════════════════════════════════════════════════════════════════════════

def build_data_context(question: str) -> str:
    q = question.lower()
    contexts = []

    if any(w in q for w in ["revenue", "sales", "top line", "growth"]):
        contexts.append(get_revenue())

    if any(w in q for w in ["margin", "profitab", "gross profit", "operating margin", "net margin"]):
        contexts.append(get_margins())

    if any(w in q for w in ["income statement", "p&l", "profit loss", "operating income", "pretax", "income"]):
        contexts.append(get_income_statement())

    if any(w in q for w in ["expense", "r&d", "research", "sga", "selling", "opex", "operating expense", "cost"]):
        contexts.append(get_expenses())

    if any(w in q for w in ["balance sheet", "asset", "liabilit", "equity", "inventory", "receivable", "current ratio"]):
        contexts.append(get_balance_sheet())
        contexts.append(get_debt_equity())

    if any(w in q for w in ["cash flow", "operating cash", "investing", "financing", "capex", "capital expenditure", "depreciation"]):
        contexts.append(get_cash_flow())

    if any(w in q for w in ["free cash flow", "fcf"]):
        contexts.append(get_fcf())

    if any(w in q for w in ["ebitda", "earnings before"]):
        contexts.append(get_ebitda())

    if any(w in q for w in ["net income", "net loss", "bottom line", "profit", "loss", "abnormal"]):
        contexts.append(get_net_income())

    if any(w in q for w in ["cash", "liquidity", "short term invest", "cash position"]):
        contexts.append(get_cash_position())

    if any(w in q for w in ["debt", "leverage", "borrow", "loan"]):
        contexts.append(get_debt_equity())

    if any(w in q for w in ["ratio", "roe", "roa", "roic", "return on", "piotroski", "f-score"]):
        contexts.append(get_key_ratios())

    if any(w in q for w in ["per share", "eps", "earnings per share", "book value"]):
        contexts.append(get_per_share())

    if any(w in q for w in ["overall", "summary", "health", "overview", "general", "financial", "2025", "2024", "compare", "trend", "all"]):
        contexts.append(get_revenue())
        contexts.append(get_margins())
        contexts.append(get_fcf())
        contexts.append(get_key_ratios())
        contexts.append(get_cash_position())

    # Always include a base summary
    rev = DATA["pl"].get("Revenue", [])
    ni  = DATA["pl"].get("Net Income", [])
    base = (
        f"10x Genomics (TXG) Financial Data: FY2019–FY2025. "
        f"Latest revenue (FY2025): ${rev[-1]}M. "
        f"Latest net income (FY2025): ${ni[-1]}M. "
        f"Data covers: Income Statement, Balance Sheet, Cash Flow, Derived Ratios."
    )
    contexts.insert(0, base)

    # If nothing matched specifically, return all key data
    if len(contexts) == 1:
        contexts += [get_revenue(), get_margins(), get_income_statement(),
                     get_cash_flow(), get_fcf(), get_key_ratios()]

    return "\n\n".join(contexts)


# ═══════════════════════════════════════════════════════════════════════════════
#  HTML FRONTEND (inline — no templates folder needed)
# ═══════════════════════════════════════════════════════════════════════════════

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>10x Genomics Financial Analyst</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet"/>
<style>
  :root{
    --bg:#0a0e1a;--surface:#111827;--surface2:#1a2236;--border:#1e2d45;
    --accent:#3b82f6;--accent2:#6366f1;--green:#10b981;--red:#ef4444;
    --text:#e2e8f0;--muted:#64748b;--user-bg:#1e3a5f;--bot-bg:#1a2236;
    --radius:12px;
  }
  *,*::before,*::after{box-sizing:border-box;margin:0;padding:0;}
  body{background:var(--bg);color:var(--text);font-family:'Inter',sans-serif;height:100vh;display:flex;flex-direction:column;overflow:hidden;}
  header{position:relative;z-index:10;display:flex;align-items:center;gap:14px;padding:14px 24px;background:var(--surface);border-bottom:1px solid var(--border);}
  .logo{width:40px;height:40px;background:linear-gradient(135deg,#3b82f6,#6366f1);border-radius:10px;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:14px;color:#fff;flex-shrink:0;}
  .header-info h1{font-size:16px;font-weight:600;}
  .header-info p{font-size:12px;color:var(--muted);margin-top:1px;}
  .badge{margin-left:auto;background:rgba(16,185,129,.15);color:var(--green);border:1px solid rgba(16,185,129,.3);border-radius:20px;padding:4px 12px;font-size:11px;font-weight:600;display:flex;align-items:center;gap:5px;}
  .dot{width:6px;height:6px;border-radius:50%;background:var(--green);animation:pulse 2s infinite;}
  @keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}

  .stats-bar{background:var(--surface2);border-bottom:1px solid var(--border);padding:10px 24px;display:flex;gap:28px;flex-wrap:wrap;flex-shrink:0;}
  .stat{display:flex;flex-direction:column;gap:1px;}
  .stat-label{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.05em;}
  .stat-value{font-size:13px;font-weight:600;}
  .up{color:var(--green);}
  .down{color:var(--red);}

  #chat{flex:1;overflow-y:auto;padding:24px 20px;display:flex;flex-direction:column;gap:16px;scroll-behavior:smooth;scrollbar-width:thin;scrollbar-color:var(--border) transparent;}
  #chat::-webkit-scrollbar{width:4px}
  #chat::-webkit-scrollbar-thumb{background:var(--border);border-radius:2px}

  .msg-wrap{display:flex;gap:10px;max-width:820px;width:100%;animation:fadeUp .3s ease forwards;opacity:0;}
  @keyframes fadeUp{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}
  .msg-wrap.user{align-self:flex-end;flex-direction:row-reverse;}
  .msg-wrap.bot{align-self:flex-start;}

  .avatar{width:32px;height:32px;border-radius:8px;display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:700;flex-shrink:0;margin-top:2px;}
  .msg-wrap.bot .avatar{background:linear-gradient(135deg,#3b82f6,#6366f1);color:#fff;}
  .msg-wrap.user .avatar{background:linear-gradient(135deg,#10b981,#0ea5e9);color:#fff;}

  .bubble{padding:12px 16px;border-radius:var(--radius);font-size:13.5px;line-height:1.7;max-width:calc(100% - 46px);white-space:pre-wrap;word-break:break-word;}
  .msg-wrap.bot .bubble{background:var(--bot-bg);border:1px solid var(--border);border-top-left-radius:3px;}
  .msg-wrap.user .bubble{background:var(--user-bg);border:1px solid #254a75;border-top-right-radius:3px;}

  .welcome{align-self:center;text-align:center;padding:36px 20px;max-width:540px;animation:fadeUp .5s ease forwards;opacity:0;}
  .welcome-icon{width:64px;height:64px;background:linear-gradient(135deg,#3b82f6,#6366f1);border-radius:18px;margin:0 auto 18px;display:flex;align-items:center;justify-content:center;font-size:28px;}
  .welcome h2{font-size:20px;font-weight:700;margin-bottom:8px;}
  .welcome p{font-size:13px;color:var(--muted);line-height:1.6;margin-bottom:20px;}
  .data-badge{display:inline-block;margin-bottom:18px;background:rgba(59,130,246,0.1);border:1px solid rgba(59,130,246,0.3);color:#93c5fd;font-size:12px;padding:5px 14px;border-radius:20px;}
  .suggestions{display:flex;flex-wrap:wrap;gap:8px;justify-content:center;}
  .suggestion{padding:7px 14px;border:1px solid var(--border);border-radius:20px;font-size:12.5px;color:var(--muted);cursor:pointer;transition:all .2s;background:var(--surface);}
  .suggestion:hover{border-color:#3b82f6;color:#93c5fd;background:rgba(59,130,246,0.08);}

  .typing-wrap{display:none;}
  .typing-wrap.visible{display:flex;}
  .typing{display:flex;align-items:center;gap:5px;padding:12px 16px;background:var(--bot-bg);border:1px solid var(--border);border-radius:var(--radius);border-bottom-left-radius:3px;}
  .typing span{width:7px;height:7px;border-radius:50%;background:var(--muted);animation:bounce 1.2s infinite;}
  .typing span:nth-child(2){animation-delay:.2s}
  .typing span:nth-child(3){animation-delay:.4s}
  @keyframes bounce{0%,80%,100%{transform:scale(1);opacity:.4}40%{transform:scale(1.3);opacity:1}}

  footer{position:relative;z-index:10;padding:14px 20px;background:var(--surface);border-top:1px solid var(--border);}
  .input-row{display:flex;gap:10px;max-width:820px;margin:0 auto;align-items:flex-end;}
  #input{flex:1;background:var(--surface2);border:1px solid var(--border);border-radius:var(--radius);padding:11px 15px;color:var(--text);font-family:'Inter',sans-serif;font-size:13.5px;resize:none;min-height:46px;max-height:120px;outline:none;transition:border-color .2s;line-height:1.5;}
  #input:focus{border-color:var(--accent);}
  #input::placeholder{color:var(--muted);}
  #send{width:46px;height:46px;border-radius:var(--radius);background:linear-gradient(135deg,var(--accent),var(--accent2));border:none;cursor:pointer;display:flex;align-items:center;justify-content:center;flex-shrink:0;transition:all .2s;box-shadow:0 4px 14px rgba(59,130,246,0.3);}
  #send:hover{opacity:.9;transform:translateY(-1px);}
  #send:active{transform:translateY(0);}
  #send:disabled{opacity:.4;cursor:not-allowed;transform:none;}
  #send svg{width:17px;height:17px;fill:#fff;}
  .powered{text-align:center;font-size:11px;color:var(--muted);margin-top:8px;}
</style>
</head>
<body>

<header>
  <div class="logo">TXG</div>
  <div class="header-info">
    <h1>10x Genomics Financial Analyst</h1>
    <p>FY 2019 – FY 2025 · Balance Sheet · P&L · Cash Flow · Key Ratios</p>
  </div>
  <div class="badge"><div class="dot"></div> Live Data</div>
</header>

<div class="stats-bar">
  <div class="stat"><span class="stat-label">Revenue (FY25)</span><span class="stat-value">$642.8M</span></div>
  <div class="stat"><span class="stat-label">Revenue Growth</span><span class="stat-value up">+5.2%</span></div>
  <div class="stat"><span class="stat-label">Gross Margin (FY25)</span><span class="stat-value up">69.1%</span></div>
  <div class="stat"><span class="stat-label">Net Income (FY25)</span><span class="stat-value down">-$43.5M</span></div>
  <div class="stat"><span class="stat-label">Cash (FY25)</span><span class="stat-value">$473.9M</span></div>
  <div class="stat"><span class="stat-label">FCF (FY25)</span><span class="stat-value down">-$52.0M</span></div>
  <div class="stat"><span class="stat-label">Total Assets (FY25)</span><span class="stat-value">$1,041.4M</span></div>
</div>

<div id="chat">
  <div class="welcome" id="welcome">
    <div class="welcome-icon">📈</div>
    <h2>Ask Me Anything About TXG Financials</h2>
    <div class="data-badge">📊 Answering from your Excel files</div>
    <p>4 financial statements · FY2019–FY2025 · Income Statement, Balance Sheet, Cash Flow & Ratios</p>
    <div class="suggestions">
      <div class="suggestion" onclick="ask(this)">What was TXG's revenue trend 2019–2025?</div>
      <div class="suggestion" onclick="ask(this)">How did gross margin evolve over time?</div>
      <div class="suggestion" onclick="ask(this)">When did TXG turn cash flow positive?</div>
      <div class="suggestion" onclick="ask(this)">How much did TXG spend on R&D each year?</div>
      <div class="suggestion" onclick="ask(this)">What is TXG's current ratio trend?</div>
      <div class="suggestion" onclick="ask(this)">Analyze TXG's free cash flow history</div>
      <div class="suggestion" onclick="ask(this)">Give me a full FY2025 financial summary</div>
      <div class="suggestion" onclick="ask(this)">Compare 2022 vs 2025 performance</div>
    </div>
  </div>
  <div class="msg-wrap bot typing-wrap" id="typing">
    <div class="avatar">AI</div>
    <div class="typing"><span></span><span></span><span></span></div>
  </div>
</div>

<footer>
  <div class="input-row">
    <textarea id="input" placeholder="Ask about revenue, margins, cash flow, ratios, net income…" rows="1"></textarea>
    <button id="send" onclick="sendMsg()">
      <svg viewBox="0 0 24 24"><path d="M2 21l21-9L2 3v7l15 2-15 2z"/></svg>
    </button>
  </div>
  <div class="powered">Answers grounded in your Excel files · Groq llama-3.3-70b</div>
</footer>

<script>
  const chatEl=document.getElementById('chat'),inputEl=document.getElementById('input'),
        sendBtn=document.getElementById('send'),typingEl=document.getElementById('typing'),
        welcomeEl=document.getElementById('welcome');

  inputEl.addEventListener('input',()=>{inputEl.style.height='auto';inputEl.style.height=Math.min(inputEl.scrollHeight,120)+'px';});
  inputEl.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();sendMsg();}});

  function ask(el){inputEl.value=el.textContent;sendMsg();}

  function addMsg(role,text){
    if(welcomeEl)welcomeEl.style.display='none';
    const wrap=document.createElement('div');
    wrap.className=`msg-wrap ${role}`;
    const av=document.createElement('div');
    av.className='avatar';av.textContent=role==='user'?'You':'AI';
    const bub=document.createElement('div');
    bub.className='bubble';bub.textContent=text;
    wrap.appendChild(av);wrap.appendChild(bub);
    chatEl.insertBefore(wrap,typingEl);
    chatEl.scrollTop=chatEl.scrollHeight;
  }

  async function sendMsg(){
    const text=inputEl.value.trim();if(!text)return;
    inputEl.value='';inputEl.style.height='auto';sendBtn.disabled=true;
    addMsg('user',text);
    typingEl.classList.add('visible');
    chatEl.scrollTop=chatEl.scrollHeight;
    try{
      const res=await fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:text})});
      const data=await res.json();
      typingEl.classList.remove('visible');
      addMsg('bot',data.reply||data.error||'Something went wrong.');
    }catch(e){
      typingEl.classList.remove('visible');
      addMsg('bot','❌ Could not reach the server.');
    }
    sendBtn.disabled=false;inputEl.focus();
  }
</script>
</body>
</html>
"""


# ═══════════════════════════════════════════════════════════════════════════════
#  FLASK ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

conversation_history = []

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/chat", methods=["POST"])
def chat():
    global conversation_history
    user_message = request.json.get("message", "").strip()
    if not user_message:
        return jsonify({"error": "Empty message"}), 400
    try:
        client = Groq(api_key=GROQ_API_KEY)
        data_context = build_data_context(user_message)
        system_prompt = (
            "You are a professional financial analyst specializing in 10x Genomics, Inc. (TXG), "
            "a life science tools company that IPO'd in 2019. "
            "You MUST answer using ONLY the data provided below — do not guess or use outside knowledge.\n\n"
            "DATA FROM EXCEL FILES:\n"
            f"{data_context}\n\n"
            "Instructions:\n"
            "- Base every answer strictly on the data above\n"
            "- Be precise: cite specific dollar amounts, percentages, and years\n"
            "- Calculate growth rates and trends when relevant\n"
            "- Contextualize numbers (what they mean for the business)\n"
            "- All monetary values are in USD millions ($M) unless stated otherwise\n"
            "- Balance Sheet uses year-end (Q4) figures; all other statements use full fiscal year (FY)\n"
            "- Margins in the data are decimals (e.g. 0.69 = 69%)\n"
            "- If the data doesn't contain enough info to answer, say so honestly"
        )
        messages = [{"role": "system", "content": system_prompt}]
        messages += conversation_history[-12:]
        messages.append({"role": "user", "content": user_message})
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=1024,
        )
        reply = response.choices[0].message.content
        conversation_history.append({"role": "user",      "content": user_message})
        conversation_history.append({"role": "assistant", "content": reply})
        if len(conversation_history) > 24:
            conversation_history = conversation_history[-24:]
        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    import webbrowser, threading
    print("\n📈  10x Genomics Financial Chatbot")
    print("─" * 40)
    print(f"📂 Data loaded from: {DATA_DIR}")
    print("🌐 Opening http://localhost:5000 ...")
    threading.Timer(1.2, lambda: webbrowser.open("http://localhost:5000")).start()
    app.run(debug=False, port=5000)
