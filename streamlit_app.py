import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
from google.oauth2 import service_account
from datetime import datetime, date
import calendar
import time

# --- 1. KONFIGURACJA STRONY ---
st.set_page_config(page_title="Retro Diner 1960", layout="wide", page_icon="🍒")

if "password_correct" not in st.session_state:
    st.markdown("<h1 style='color: #d62828; font-family: \"Pacifico\";'>🍒 DINER LOGIN</h1>", unsafe_allow_html=True)
    pwd = st.text_input("Klucz do Jukeboxa", type="password")
    if st.button("OPEN DINER"):
        if pwd == st.secrets["credentials"]["password"]:
            st.session_state["password_correct"] = True
            st.rerun()
        else: st.error("Wrong key!")
    st.stop()

# --- 2. STYL WYSOKIEGO KONTRASTU (CSS) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Pacifico&family=Bungee&family=Montserrat:wght@800&display=swap');
    
    /* Czyste tło bez kropek pod tekstem */
    .stApp { 
        background-color: #a2d2ff; 
        font-family: 'Montserrat', sans-serif;
    }
    
    /* GIGANTYCZNY NAGŁÓWEK */
    h1 { 
        font-family: 'Pacifico', cursive !important; 
        font-size: 5em !important; 
        color: #fefae0 !important;
        text-shadow: 6px 6px 0px #d62828, 12px 12px 0px #003049;
        margin-bottom: 50px !important;
    }

    /* KARTY FORMULARZY - MAKSYMALNA CZYTELNOŚĆ */
    div[data-testid="stForm"] {
        background-color: #fefae0 !important; /* Kremowe, solidne tło */
        border: 6px solid #000000 !important; /* Gruba czarna linia */
        border-radius: 0px !important; /* Kanciaste, retro */
        padding: 30px !important;
        box-shadow: 15px 15px 0px #d62828 !important;
    }

    /* WEJŚCIA TEKSTOWE (INPUTS) */
    input {
        background-color: #ffffff !important;
        color: #000000 !important;
        font-size: 20px !important;
        font-weight: bold !important;
        border: 3px solid #000000 !important;
    }
    
    /* METRYKI - CZYTELNE I DUŻE */
    [data-testid="stMetric"] { 
        background: #003049 !important; 
        border: 5px solid #ffffff !important; 
        box-shadow: 10px 10px 0px #d62828 !important; 
        padding: 25px !important;
    }
    [data-testid="stMetricLabel"] p { 
        color: #ffafcc !important; 
        font-family: 'Bungee', cursive !important; 
        font-size: 22px !important; 
    }
    [data-testid="stMetricValue"] div { 
        color: #ffffff !important; 
        font-family: 'Pacifico', cursive !important; 
        font-size: 45px !important; 
    }
    
    /* PRZYCISKI - STYL KOMIKSOWY */
    .stButton>button { 
        background: #d62828 !important; 
        color: white !important; 
        font-family: 'Bungee', cursive !important; 
        font-size: 24px !important;
        border: 4px solid #000000 !important;
        box-shadow: 5px 5px 0px #003049 !important;
        height: 80px !important;
    }

    /* ZAKŁADKI */
    .stTabs [data-baseweb="tab-list"] { background: #003049; padding: 10px; border-radius: 10px; }
    .stTabs [data-baseweb="tab"] {
        color: white !important;
        font-family: 'Bungee';
        font-size: 18px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #d62828 !important;
    }

    /* TABELE */
    .stDataFrame { 
        background: white !important; 
        border: 3px solid #000000 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. DANE ---
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
    st.error(f"Error: {e}"); st.stop()

# Konwersja dat i kwot
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
    ledger_data.append({"Opis": "START", "Zmiana": 0.0, "Saldo": curr_val})
    curr_val += 1600
    ledger_data.append({"Opis": "PLUS 800+", "Zmiana": 1600.0, "Saldo": curr_val})
    for _, row in df_fix.iterrows():
        curr_val -= row['Kwota']; ledger_data.append({"Opis": f"FIXED: {row['Nazwa']}", "Zmiana": -row['Kwota'], "Saldo": curr_val})
    active_raty = df_rat[(df_rat['Start'] <= target_date) & (df_rat['Koniec'] >= target_date)]
    for _, row in active_raty.iterrows():
        curr_val -= row['Kwota']; ledger_data.append({"Opis": f"RATA: {row['Rata']}", "Zmiana": -row['Kwota'], "Saldo": curr_val})
    mask_inc = (df_inc['Data i Godzina'].dt.month == sel_month) & (df_inc['Data i Godzina'].dt.year == sel_year)
    mask_exp = (df_exp['Data i Godzina'].dt.month == sel_month) & (df_exp['Data i Godzina'].dt.year == sel_year)
    ops = pd.concat([df_inc[mask_inc].assign(T="P"), df_exp[mask_exp].assign(T="W")]).sort_values('Data i Godzina')
    for _, row in ops.iterrows():
        ch = row['Kwota'] if row['T'] == "P" else -row['Kwota']
        curr_val += ch; ledger_data.append({"Opis": row['Nazwa'], "Zmiana": ch, "Saldo": curr_val})
    return pd.DataFrame(ledger_data), curr_val

# --- 5. DASHBOARD ---
st.markdown("<h1>Diner Budget</h1>", unsafe_allow_html=True)

today_y, today_m = date.today().year, date.today().month
_, current_bal = generate_ledger(today_y, today_m)

c_m1, c_m2 = st.columns(2)
c_m1.metric("CASH IN PURSE", f"{current_bal:,.2f} PLN")
days_left = calendar.monthrange(today_y, today_m)[1] - date.today().day + 1
c_m2.metric("DAILY BUDGET", f"{current_bal/days_left:,.2f} PLN" if days_left > 0 else "0")

t1, t2, t3 = st.tabs(["🎵 ADD RECORD", "📊 ANALYSIS", "🛒 SHOPPING"])

with t1:
    col1, col2 = st.columns(2)
    with col1:
        with st.form("f_inc", clear_on_submit=True):
            st.markdown("### 🍭 INCOME")
            t = st.text_input("Source")
            k = st.number_input("Amount", step=10.0)
            if st.form_submit_button("ADD CASH"):
                sh.worksheet("Przychody").append_row([datetime.now().strftime("%Y-%m-%d %H:%M"), t, k]); st.cache_data.clear(); st.rerun()
    with col2:
        with st.form("f_exp", clear_on_submit=True):
            st.markdown("### 👠 EXPENSE")
            t = st.text_input("For what?")
            k = st.number_input("Cost", step=1.0)
            if st.form_submit_button("PAY NOW"):
                sh.worksheet("Wydatki").append_row([datetime.now().strftime("%Y-%m-%d %H:%M"), t, k, "Retro", "Var"]); st.cache_data.clear(); st.rerun()

with t2:
    months = {1: "JAN", 2: "FEB", 3: "MAR", 4: "APR", 5: "MAY", 6: "JUN", 7: "JUL", 8: "AUG", 9: "SEP", 10: "OCT", 11: "NOV", 12: "DEC"}
    s_m = st.selectbox("Month", range(1, 13), format_func=lambda x: months[x], index=today_m-1)
    df_l, _ = generate_ledger(today_y, s_m)
    st.dataframe(df_l, use_container_width=True)

with t3:
    st.markdown("### 🍔 SHOPPING LIST")
    st.write(df_shp["Produkt"].tolist())
    if st.button("CLEAR LIST"):
        sh.worksheet("Zakupy").clear(); sh.worksheet("Zakupy").append_row(["Data", "Produkt"]); st.cache_data.clear(); st.rerun()

with st.sidebar:
    st.markdown("## 💎 VAULT")
    st.metric("SAVINGS", f"{s_sav:,.2f} PLN")
    if st.button("🚜 HARVEST"):
        sh.worksheet("Oszczednosci").update_acell('A2', str(s_sav + current_bal))
        st.balloons(); st.cache_data.clear(); time.sleep(1); st.rerun()
