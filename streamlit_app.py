import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
from google.oauth2 import service_account
from datetime import datetime, date
import calendar
import time

# --- 1. KONFIGURACJA STRONY ---
st.set_page_config(page_title="Retro Pin-Up Budget 1960", layout="wide", page_icon="💄")

# --- 2. LOGOWANIE ---
def check_password():
    if "password_correct" not in st.session_state:
        st.markdown("<h2 style='text-align: center; color: #d62828; font-family: \"Pacifico\", cursive;'>🍒 Witaj w Dinerze. Podaj hasło:</h2>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            pwd = st.text_input("Klucz do szafy grającej", type="password")
            if st.button("START THE JUKEBOX"):
                if pwd == st.secrets["credentials"]["password"]:
                    st.session_state["password_correct"] = True
                    st.rerun()
                else:
                    st.error("❌ Zły klucz, skarbie!")
        return False
    return True

if check_password():
    # --- 3. NOWY STYL PIN-UP / RETRO (CSS) ---
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Pacifico&family=Bungee+Inline&family=Montserrat:wght@400;700&display=swap');
        
        /* Tło - miętowy pastel i delikatne kropki */
        .stApp { 
            background-color: #a2d2ff; 
            background-image: radial-gradient(#ffffff 15%, transparent 16%), radial-gradient(#ffffff 15%, transparent 16%);
            background-size: 40px 40px;
            background-position: 0 0, 20px 20px;
            font-family: 'Montserrat', sans-serif;
        }
        
        /* Karty metryk - styl Diner / Retro Fridge */
        [data-testid="stMetric"] { 
            background: #fefae0 !important; 
            border: 5px solid #ffafcc !important; 
            border-radius: 30px 0px 30px 0px !important; 
            box-shadow: 8px 8px 0px 0px #d62828 !important; 
            padding: 20px !important; 
        }
        [data-testid="stMetricLabel"] p { 
            color: #003049 !important; 
            font-family: 'Bungee Inline', cursive !important; 
            font-size: 18px !important; 
        }
        [data-testid="stMetricValue"] div { 
            color: #d62828 !important; 
            font-family: 'Pacifico', cursive !important; 
            font-size: 40px !important; 
        }
        
        /* Nagłówki */
        h1 { 
            color: #ffffff !important; 
            font-family: 'Pacifico', cursive !important; 
            font-size: 4em !important; 
            text-shadow: 4px 4px 0px #d62828, 8px 8px 0px #003049;
            text-align: center;
            margin-bottom: 30px;
            border: none !important;
        }
        h2, h3 { 
            color: #003049 !important; 
            font-family: 'Bungee Inline', cursive !important; 
            text-align: center;
            border-bottom: 3px dashed #ffafcc;
        }
        
        /* Przyciski - styl starego neonu / winylu */
        .stButton>button { 
            background: #d62828 !important; 
            color: white !important; 
            font-family: 'Bungee Inline', cursive !important; 
            border-radius: 50px !important; 
            border: 3px solid #fefae0 !important;
            font-size: 20px !important;
            height: 3em !important;
            box-shadow: 4px 4px 0px #003049;
            transition: 0.3s;
        }
        .stButton>button:hover { 
            transform: scale(1.05);
            background: #003049 !important;
        }
        
        /* Sidebar */
        [data-testid="stSidebar"] { 
            background: #ffafcc !important; 
            border-right: 5px solid #d62828 !important; 
        }
        
        /* Zakładki (Tabs) */
        .stTabs [data-baseweb="tab-list"] { gap: 10px; }
        .stTabs [data-baseweb="tab"] {
            background-color: #fefae0;
            border-radius: 15px 15px 0px 0px;
            padding: 10px 20px;
            font-family: 'Bungee Inline', cursive;
            color: #003049;
        }
        .stTabs [aria-selected="true"] {
            background-color: #d62828 !important;
            color: white !important;
        }
        </style>
        """, unsafe_allow_html=True)

    # --- 4. POŁĄCZENIE Z DANYMI (Bez zmian w logice) ---
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
        st.error(f"🚜 Oh Honey, there's a problem: {e}"); st.stop()

    # Czyszczenie i konwersja
    for df in [df_inc, df_exp, df_fix, df_rat]:
        df['Kwota'] = pd.to_numeric(df['Kwota'], errors='coerce').fillna(0)
    df_inc['Data i Godzina'] = pd.to_datetime(df_inc['Data i Godzina'], errors='coerce')
    df_exp['Data i Godzina'] = pd.to_datetime(df_exp['Data i Godzina'], errors='coerce')
    df_rat['Start'] = pd.to_datetime(df_rat['Start'], errors='coerce')
    df_rat['Koniec'] = pd.to_datetime(df_rat['Koniec'], errors='coerce')
    df_inc, df_exp = df_inc.dropna(subset=['Data i Godzina']), df_exp.dropna(subset=['Data i Godzina'])
    s_sav = float(str(df_sav.iloc[0,0]).replace(',', '.')) if not df_sav.empty else 0.0

    # --- 5. LOGIKA FINANSOWA ---
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
        ledger_data.append({"Data": target_date.strftime("%Y-%m-%d"), "Opis": "OPENING BALANCE", "Zmiana": 0.0, "Saldo": curr_val})
        curr_val += 1600
        ledger_data.append({"Data": target_date.strftime("%Y-%m-%d"), "Opis": "GOVT 800+ BONUS", "Zmiana": 1600.0, "Saldo": curr_val})
        for _, row in df_fix.iterrows():
            curr_val -= row['Kwota']; ledger_data.append({"Data": target_date.strftime("%Y-%m-%d"), "Opis": f"FIXED: {row['Nazwa']}", "Zmiana": -row['Kwota'], "Saldo": curr_val})
        active_raty = df_rat[(df_rat['Start'] <= target_date) & (df_rat['Koniec'] >= target_date)]
        for _, row in active_raty.iterrows():
            curr_val -= row['Kwota']; ledger_data.append({"Data": target_date.strftime("%Y-%m-%d"), "Opis": f"INSTALLMENT: {row['Rata']}", "Zmiana": -row['Kwota'], "Saldo": curr_val})
        mask_inc = (df_inc['Data i Godzina'].dt.month == sel_month) & (df_inc['Data i Godzina'].dt.year == sel_year)
        mask_exp = (df_exp['Data i Godzina'].dt.month == sel_month) & (df_exp['Data i Godzina'].dt.year == sel_year)
        ops = pd.concat([df_inc[mask_inc].assign(T="P"), df_exp[mask_exp].assign(T="W")]).sort_values('Data i Godzina')
        for _, row in ops.iterrows():
            ch = row['Kwota'] if row['T'] == "P" else -row['Kwota']
            curr_val += ch; ledger_data.append({"Data": row['Data i Godzina'].strftime("%m-%d %H:%M"), "Opis": row['Nazwa'], "Zmiana": ch, "Saldo": curr_val})
        return pd.DataFrame(ledger_data), curr_val

    # --- 6. DASHBOARD ---
    today_y, today_m = date.today().year, date.today().month
    _, current_total_balance = generate_ledger(today_y, today_m)
    
    st.markdown("<h1>Milkshake & Money 1960</h1>", unsafe_allow_html=True)
    
    col_met1, col_met2 = st.columns(2)
    col_met1.metric("CASH IN PURSE", f"{current_total_balance:,.2f} $")
    days_left = calendar.monthrange(today_y, today_m)[1] - date.today().day + 1
    col_met2.metric("DAILY MILKSHAKE", f"{current_total_balance/days_left:,.2f} $" if days_left > 0 else "---")

    # --- 7. TABS ---
    t1, t2, t3, t4 = st.tabs(["🍒 RECORDS", "🏠 FIXED COSTS", "📊 JUKEBOX ANALYSIS", "🛒 GROCERY"])

    with t1:
        c1, c2 = st.columns(2)
        with c1:
            with st.form("f_i", clear_on_submit=True):
                st.subheader("🍭 Sweet Income")
                t, k = st.text_input("Source"), st.number_input("Amount", step=10.0)
                if st.form_submit_button("ADD TO PURSE"):
                    sh.worksheet("Przychody").append_row([datetime.now().strftime("%Y-%m-%d %H:%M"), t, k]); st.cache_data.clear(); st.rerun()
        with c2:
            with st.form("f_e", clear_on_submit=True):
                st.subheader("👠 Fancy Expense")
                t, k = st.text_input("Item"), st.number_input("Price", step=1.0)
                if st.form_submit_button("PAY NOW"):
                    sh.worksheet("Wydatki").append_row([datetime.now().strftime("%Y-%m-%d %H:%M"), t, k, "Retro", "Variable"]); st.cache_data.clear(); st.rerun()

    with t2:
        st.subheader("📻 SETUP YOUR DINER COSTS")
        cf1, cf2 = st.columns(2)
        with cf1:
            with st.form("nf"):
                n, k = st.text_input("Monthly Bill"), st.number_input("Cost")
                if st.form_submit_button("ADD BILL"):
                    sh.worksheet("Koszty_Stale").append_row([n, k]); st.cache_data.clear(); st.rerun()
        with cf2:
            with st.form("nr"):
                n, k = st.text_input("Loan/Car"), st.number_input("Rata")
                s, e = st.date_input("Start"), st.date_input("End")
                if st.form_submit_button("ADD INSTALLMENT"):
                    sh.worksheet("Raty").append_row([n, k, s.strftime("%Y-%m-%d"), e.strftime("%Y-%m-%d")]); st.cache_data.clear(); st.rerun()
        st.divider()
        st.dataframe(df_fix, use_container_width=True)

    with t3:
        st.subheader("🎼 FINANCIAL JUKEBOX")
        months = {1: "JAN", 2: "FEB", 3: "MAR", 4: "APR", 5: "MAY", 6: "JUN", 7: "JUL", 8: "AUG", 9: "SEP", 10: "OCT", 11: "NOV", 12: "DEC"}
        c_s1, c_s2 = st.columns(2)
        s_y = c_s1.selectbox("Year", [2026, 2025])
        s_m = c_s2.selectbox("Month", range(1, 13), format_func=lambda x: months[x], index=date.today().month-1)
        df_l, _ = generate_ledger(s_y, s_m)
        st.dataframe(df_l.style.format({"Zmiana": "{:,.2f} $", "Saldo": "{:,.2f} $"}), use_container_width=True, hide_index=True)
        fig = px.line(df_l, x=df_l.index, y="Saldo", title="Wealth Journey", color_discrete_sequence=['#d62828'])
        st.plotly_chart(fig, use_container_width=True)

    with t4:
        st.subheader("🛒 GROCERY LIST")
        st.write(df_shp["Produkt"].tolist())
        if st.button("CLEAR THE CART"):
            sh.worksheet("Zakupy").clear(); sh.worksheet("Zakupy").append_row(["Data", "Produkt"]); st.cache_data.clear(); st.rerun()

    with st.sidebar:
        st.markdown("<h2 style='color: white !important;'>💎 THE VAULT</h2>", unsafe_allow_html=True)
        st.metric("SAVINGS", f"{s_sav:,.2f} $")
        if st.button("🚜 HARVEST SURPLUS"):
            if current_total_balance > 0:
                sh.worksheet("Oszczednosci").update_acell('A2', str(s_sav + current_total_balance))
                st.balloons(); st.cache_data.clear(); time.sleep(1); st.rerun()
