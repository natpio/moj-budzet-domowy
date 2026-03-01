import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
from google.oauth2 import service_account
from datetime import datetime, date
import calendar
import time

# --- 1. KONFIGURACJA STRONY ---
st.set_page_config(page_title="Pop-Art Diner 1960", layout="wide", page_icon="💄")

if "password_correct" not in st.session_state:
    st.markdown("<h1 style='color: #d62828; font-family: \"Pacifico\"; font-size: 80px; text-align: center;'>🍒 ENTER THE DINER</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        pwd = st.text_input("PASSWORD (JUKEBOX KEY)", type="password")
        if st.button("START THE MUSIC"):
            if pwd == st.secrets["credentials"]["password"]:
                st.session_state["password_correct"] = True
                st.rerun()
    st.stop()

# --- 2. EKSTREMALNY STYL POP-ART / RETRO (CSS) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Pacifico&family=Bungee+Shade&family=Bungee&family=Monoton&display=swap');
    
    /* Tło - Dynamiczny Color Blocking */
    .stApp { 
        background-color: #f72585; /* Neonowy róż */
        background-image: linear-gradient(45deg, #4cc9f0 25%, transparent 25%), 
                          linear-gradient(-45deg, #4cc9f0 25%, transparent 25%), 
                          linear-gradient(45deg, transparent 75%, #4cc9f0 75%), 
                          linear-gradient(-45deg, transparent 75%, #4cc9f0 75%);
        background-size: 100px 100px;
        background-attachment: fixed;
    }
    
    /* NAGŁÓWEK - Styl Neon Sign */
    h1 { 
        font-family: 'Monoton', cursive !important; 
        font-size: 6em !important; 
        color: #fefae0 !important;
        text-shadow: 0 0 10px #fff, 0 0 20px #fff, 0 0 30px #f72585, 0 0 40px #f72585;
        text-align: center;
        padding: 20px;
    }

    /* KARTY FORMULARZY - Komiksowy Pop-Art */
    div[data-testid="stForm"] {
        background-color: #fefae0 !important;
        border: 10px solid #000000 !important;
        border-radius: 0px !important;
        padding: 40px !important;
        box-shadow: 25px 25px 0px #4361ee !important; /* Mocny niebieski cień */
        transform: rotate(-1deg); /* Lekki przechył dla stylu */
    }

    /* METRYKI - Neonowe Kostki */
    [data-testid="stMetric"] { 
        background: #000000 !important; 
        border: 6px solid #4cc9f0 !important; 
        box-shadow: 15px 15px 0px #f72585 !important; 
        padding: 30px !important;
        transition: 0.3s;
    }
    [data-testid="stMetric"]:hover {
        transform: scale(1.05);
        border-color: #f72585;
    }
    [data-testid="stMetricLabel"] p { 
        color: #4cc9f0 !important; 
        font-family: 'Bungee', cursive !important; 
        font-size: 24px !important; 
        text-transform: uppercase;
    }
    [data-testid="stMetricValue"] div { 
        color: #ffffff !important; 
        font-family: 'Pacifico', cursive !important; 
        font-size: 50px !important; 
    }
    
    /* PRZYCISKI - Styl "POW!" */
    .stButton>button { 
        background: #f72585 !important; 
        color: white !important; 
        font-family: 'Bungee Shade', cursive !important; 
        font-size: 30px !important;
        border: 5px solid #000000 !important;
        box-shadow: 8px 8px 0px #000000 !important;
        height: 100px !important;
        transition: 0.2s;
    }
    .stButton>button:hover { 
        transform: translate(-4px, -4px);
        box-shadow: 12px 12px 0px #4361ee !important;
        background: #4361ee !important;
    }

    /* ZAKŁADKI (Tabs) */
    .stTabs [data-baseweb="tab-list"] { background: transparent; gap: 20px; }
    .stTabs [data-baseweb="tab"] {
        background: #000 !important;
        color: #fff !important;
        border: 3px solid #fff;
        font-family: 'Bungee';
        padding: 10px 30px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #fefae0 !important;
        color: #000 !important;
        border: 3px solid #f72585;
        transform: translateY(-5px);
    }

    /* INPUTY */
    input {
        border: 4px solid #000 !important;
        font-family: 'Bungee';
        font-size: 22px !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. DANE (Zoptymalizowane) ---
@st.cache_resource
def get_client():
    creds_dict = st.secrets["gcp_service_account"]
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=scope)
    return gspread.authorize(creds)

@st.cache_data(ttl=60)
def load_all_data():
    client = get_client()
    sh = client.open("Budzet_Data")
    sheets = ["Przychody", "Wydatki", "Koszty_Stale", "Raty", "Oszczednosci", "Zakupy", "Zadania", "Planowanie"]
    return {name: pd.DataFrame(sh.worksheet(name).get_all_records()) for name in sheets}

try:
    data = load_all_data()
    df_inc, df_exp, df_fix, df_rat, df_sav, df_shp, df_tsk, df_pla = [data[n] for n in ["Przychody", "Wydatki", "Koszty_Stale", "Raty", "Oszczednosci", "Zakupy", "Zadania", "Planowanie"]]
    sh = get_client().open("Budzet_Data")
except Exception as e:
    st.error(f"Oh Honey! Jukebox error: {e}"); st.stop()

# Konwersja
for df in [df_inc, df_exp, df_fix, df_rat]:
    df['Kwota'] = pd.to_numeric(df['Kwota'], errors='coerce').fillna(0)
df_inc['Data i Godzina'] = pd.to_datetime(df_inc['Data i Godzina'], errors='coerce')
df_exp['Data i Godzina'] = pd.to_datetime(df_exp['Data i Godzina'], errors='coerce')
df_rat['Start'] = pd.to_datetime(df_rat['Start'], errors='coerce')
df_rat['Koniec'] = pd.to_datetime(df_rat['Koniec'], errors='coerce')
df_inc, df_exp = df_inc.dropna(subset=['Data i Godzina']), df_exp.dropna(subset=['Data i Godzina'])
s_sav = float(str(df_sav.iloc[0,0]).replace(',', '.')) if not df_sav.empty else 0.0

# --- 4. LOGIKA ---
def generate_ledger(sel_year, sel_month):
    target_date = pd.Timestamp(year=sel_year, month=sel_month, day=1)
    inc_before = df_inc[df_inc['Data i Godzina'] < target_date]['Kwota'].sum()
    exp_before = df_exp[df_exp['Data i Godzina'] < target_date]['Kwota'].sum()
    months_diff = (target_date.year - 2026) * 12 + (target_date.month - 1)
    s_800_before = max(0, months_diff * 1600)
    fix_before = max(0, months_diff * df_fix['Kwota'].sum())
    rat_before = 0
    if months_diff > 0:
        for m in pd.date_range(start="2026-01-01", periods=months_diff, freq='MS'):
            rat_before += df_rat[(df_rat['Start'] <= m) & (df_rat['Koniec'] >= m)]['Kwota'].sum()
    op_bal = inc_before + s_800_before - exp_before - fix_before - rat_before - s_sav
    
    ledger_data, curr_val = [], op_bal
    ledger_data.append({"Opis": "⚡ START", "Zmiana": 0.0, "Saldo": curr_val})
    curr_val += 1600
    ledger_data.append({"Opis": "🎁 800+", "Zmiana": 1600.0, "Saldo": curr_val})
    for _, row in df_fix.iterrows():
        curr_val -= row['Kwota']; ledger_data.append({"Opis": f"🚫 {row['Nazwa']}", "Zmiana": -row['Kwota'], "Saldo": curr_val})
    active_raty = df_rat[(df_rat['Start'] <= target_date) & (df_rat['Koniec'] >= target_date)]
    for _, row in active_raty.iterrows():
        curr_val -= row['Kwota']; ledger_data.append({"Opis": f"💸 RATA: {row['Rata']}", "Zmiana": -row['Kwota'], "Saldo": curr_val})
    mask_inc = (df_inc['Data i Godzina'].dt.month == sel_month) & (df_inc['Data i Godzina'].dt.year == sel_year)
    mask_exp = (df_exp['Data i Godzina'].dt.month == sel_month) & (df_exp['Data i Godzina'].dt.year == sel_year)
    ops = pd.concat([df_inc[mask_inc].assign(T="P"), df_exp[mask_exp].assign(T="W")]).sort_values('Data i Godzina')
    for _, row in ops.iterrows():
        ch = row['Kwota'] if row['T'] == "P" else -row['Kwota']
        curr_val += ch; ledger_data.append({"Opis": row['Nazwa'], "Zmiana": ch, "Saldo": curr_val})
    return pd.DataFrame(ledger_data), curr_val

# --- 5. INTERFEJS ---
st.markdown("<h1>DINER CASH</h1>", unsafe_allow_html=True)

today_y, today_m = date.today().year, date.today().month
_, current_bal = generate_ledger(today_y, today_m)

c_m1, c_m2 = st.columns(2)
c_m1.metric("💰 WALLET", f"{current_bal:,.2f} PLN")
days_left = calendar.monthrange(today_y, today_m)[1] - date.today().day + 1
c_m2.metric("🍔 DAILY", f"{current_bal/days_left:,.2f} PLN" if days_left > 0 else "0")

t1, t2, t3 = st.tabs(["🔥 ADD TRANSACTION", "🎸 JUKEBOX RECORDS", "🛒 GROCERY"])

with t1:
    col1, col2 = st.columns(2)
    with col1:
        with st.form("f_inc", clear_on_submit=True):
            st.markdown("## 💵 GET CASH")
            t = st.text_input("SOURCE")
            k = st.number_input("AMOUNT", step=10.0)
            if st.form_submit_button("ADD TO PURSE"):
                sh.worksheet("Przychody").append_row([datetime.now().strftime("%Y-%m-%d %H:%M"), t, k]); st.cache_data.clear(); st.rerun()
    with col2:
        with st.form("f_exp", clear_on_submit=True):
            st.markdown("## 💄 SPEND IT")
            t = st.text_input("ITEM")
            k = st.number_input("COST", step=1.0)
            if st.form_submit_button("PAY NOW"):
                sh.worksheet("Wydatki").append_row([datetime.now().strftime("%Y-%m-%d %H:%M"), t, k, "PopArt", "Var"]); st.cache_data.clear(); st.rerun()

with t2:
    months = {1: "JAN", 2: "FEB", 3: "MAR", 4: "APR", 5: "MAY", 6: "JUN", 7: "JUL", 8: "AUG", 9: "SEP", 10: "OCT", 11: "NOV", 12: "DEC"}
    s_m = st.selectbox("SELECT MONTH", range(1, 13), format_func=lambda x: months[x], index=today_m-1)
    df_l, _ = generate_ledger(today_y, s_m)
    st.dataframe(df_l, use_container_width=True)

with t3:
    st.markdown("## 🌭 SHOPPING LIST")
    st.write(df_shp["Produkt"].tolist())
    if st.button("BOOM! CLEAR LIST"):
        sh.worksheet("Zakupy").clear(); sh.worksheet("Zakupy").append_row(["Data", "Produkt"]); st.cache_data.clear(); st.rerun()

with st.sidebar:
    st.markdown("<h2 style='color: white;'>💎 VAULT</h2>", unsafe_allow_html=True)
    st.metric("SAVINGS", f"{s_sav:,.2f} PLN")
    if st.button("🎰 HARVEST"):
        sh.worksheet("Oszczednosci").update_acell('A2', str(s_sav + current_bal))
        st.balloons(); st.cache_data.clear(); time.sleep(1); st.rerun()
