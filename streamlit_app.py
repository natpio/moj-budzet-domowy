import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
from google.oauth2 import service_account
from datetime import datetime, date
import calendar
import time

# --- 1. KONFIGURACJA STRONY ---
st.set_page_config(page_title="Rock'n'Roll Diner Budget 1960", layout="wide", page_icon="🍒")

# --- 2. LOGOWANIE ---
def check_password():
    if "password_correct" not in st.session_state:
        st.markdown("<h2 style='text-align: center; color: #d62828; font-family: \"Pacifico\", cursive;'>🎵 Witaj w Dinerze. Włącz Jukebox (Hasło):</h2>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            pwd = st.text_input("Klucz do szafy grającej", type="password")
            if st.button("PUNKT DLA CIEBIE! START!"):
                if pwd == st.secrets["credentials"]["password"]:
                    st.session_state["password_correct"] = True
                    st.rerun()
                else:
                    st.error("❌ Zły klucz, skarbie!")
        return False
    return True

if check_password():
    # --- 3. STYL RETRO PIN-UP / DINER (CSS) - MAKSYMALNA CZYTELNOŚĆ ---
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Pacifico&family=Bungee+Inline&family=Montserrat:wght@400;700&display=swap');
        
        /* Tło strony - Winyl & Dots */
        .stApp { 
            background-color: #a2d2ff; 
            background-image: radial-gradient(#d62828 20%, transparent 20%), radial-gradient(#ffffff 15%, transparent 16%);
            background-size: 60px 60px;
            background-position: 0 0, 30px 30px;
            font-family: 'Montserrat', sans-serif;
        }

        /* Czytelność Formularzy - Solidne tło blokujące kropki */
        div[data-testid="stForm"], .stForm {
            background-color: #fefae0 !important; 
            border: 6px solid #003049 !important;
            border-radius: 20px !important;
            padding: 30px !important;
            box-shadow: 15px 15px 0px #d62828 !important;
        }
        
        /* Czytelność tekstów w formularzach */
        label p, .stMarkdown p, .stForm p {
            color: #003049 !important;
            font-weight: 700 !important;
            font-size: 1.1rem !important;
        }
        
        /* Styl pól wejściowych (Input) */
        input, .stNumberInput input, .stTextInput input {
            background-color: #ffffff !important;
            color: #000000 !important;
            border: 3px solid #d62828 !important;
            font-weight: bold !important;
        }

        /* Karty metryk - styl Winyl */
        [data-testid="stMetric"] { 
            background: #fefae0 !important; 
            border: 8px solid #ffafcc !important; 
            border-radius: 50% 10px 50% 10px !important; 
            box-shadow: 12px 12px 0px 0px #d62828 !important; 
            padding: 30px !important; 
            position: relative;
        }
        [data-testid="stMetricLabel"] p { 
            color: #003049 !important; 
            font-family: 'Bungee Inline', cursive !important; 
            font-size: 22px !important; 
        }
        [data-testid="stMetricValue"] div { 
            color: #d62828 !important; 
            font-family: 'Pacifico', cursive !important; 
            font-size: 48px !important; 
        }
        
        /* Nagłówek Główny */
        h1 { 
            color: #ffffff !important; 
            font-family: 'Pacifico', cursive !important; 
            font-size: 5em !important; 
            text-shadow: 6px 6px 0px #d62828, 12px 12px 0px #003049;
            text-align: center;
            margin-bottom: 50px;
            border: none !important;
        }
        
        h2, h3 { 
            color: #003049 !important; 
            font-family: 'Bungee Inline', cursive !important; 
            text-align: center;
            text-transform: uppercase;
            padding-bottom: 10px;
        }
        
        /* Przyciski - Neon / Vinyl */
        .stButton>button { 
            background: #d62828 !important; 
            color: white !important; 
            font-family: 'Bungee Inline', cursive !important; 
            border-radius: 50px !important; 
            border: 4px solid #fefae0 !important;
            font-size: 24px !important;
            height: 3.5em !important;
            width: 100% !important;
            box-shadow: 8px 8px 0px #003049;
            transition: 0.3s ease-in-out;
        }
        .stButton>button:hover { 
            transform: scale(1.05) rotate(-2deg);
            background: #003049 !important;
        }

        /* Tabele - Maksymalny kontrast */
        .stDataFrame {
            background-color: white !important;
            border: 4px solid #003049 !important;
            border-radius: 10px !important;
        }
        
        /* Sidebar */
        [data-testid="stSidebar"] { 
            background: #ffafcc !important; 
            border-right: 10px solid #d62828 !important; 
        }

        /* Zakładki */
        .stTabs [data-baseweb="tab-list"] { gap: 20px; }
        .stTabs [data-baseweb="tab"] {
            background-color: #fefae0;
            border-radius: 15px 15px 0px 0px;
            padding: 15px 40px;
            font-family: 'Bungee Inline', cursive;
            color: #003049;
            border: 3px solid #003049;
        }
        .stTabs [aria-selected="true"] {
            background-color: #d62828 !important;
            color: white !important;
            border-color: white;
        }
        </style>
        """, unsafe_allow_html=True)

    # --- 4. POŁĄCZENIE Z DANYMI ---
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
        st.error(f"🚜 Oh Honey, there's a Jukebox error: {e}"); st.stop()

    # Czyszczenie danych
    for df in [df_inc, df_exp, df_fix, df_rat]:
        df['Kwota'] = pd.to_numeric(df['Kwota'], errors='coerce').fillna(0)
    
    df_inc['Data i Godzina'] = pd.to_datetime(df_inc['Data i Godzina'], errors='coerce')
    df_exp['Data i Godzina'] = pd.to_datetime(df_exp['Data i Godzina'], errors='coerce')
    df_rat['Start'] = pd.to_datetime(df_rat['Start'], errors='coerce')
    df_rat['Koniec'] = pd.to_datetime(df_rat['Koniec'], errors='coerce')
    
    df_inc = df_inc.dropna(subset=['Data i Godzina'])
    df_exp = df_exp.dropna(subset=['Data i Godzina'])
    
    # Sejf (Oszczędności)
    s_sav = float(str(df_sav.iloc[0,0]).replace(',', '.')) if not df_sav.empty else 0.0

    # --- 5. LOGIKA FINANSOWA ---
    def generate_ledger(sel_year, sel_month):
        target_date = pd.Timestamp(year=sel_year, month=sel_month, day=1)
        
        # Obliczenia historyczne do otwarcia miesiąca
        inc_before = df_inc[df_inc['Data i Godzina'] < target_date]['Kwota'].sum()
        exp_before = df_exp[df_exp['Data i Godzina'] < target_date]['Kwota'].sum()
        
        # Obliczanie różnicy miesięcy od startu (styczeń 2026)
        months_diff = (target_date.year - 2026) * 12 + (target_date.month - 1)
        
        s_800_before = max(0, months_diff * 1600)
        fix_before = max(0, months_diff * df_fix['Kwota'].sum())
        
        rat_before = 0
        if months_diff > 0:
            for m in pd.date_range(start="2026-01-01", periods=months_diff, freq='MS'):
                rat_before += df_rat[(df_rat['Start'] <= m) & (df_rat['Koniec'] >= m)]['Kwota'].sum()
        
        op_bal = inc_before + s_800_before - exp_before - fix_before - rat_before - s_sav
        
        ledger_data = []
        curr_val = op_bal
        
        # Wpis otwarcia
        ledger_data.append({"Data": target_date.strftime("%Y-%m-%d"), "Opis": "OPENING BALANCE", "Zmiana": 0.0, "Saldo": curr_val})
        
        # Bonusy i stałe koszty dla wybranego miesiąca
        curr_val += 1600
        ledger_data.append({"Data": target_date.strftime("%Y-%m-%d"), "Opis": "GOVT 800+ BONUS", "Zmiana": 1600.0, "Saldo": curr_val})
        
        for _, row in df_fix.iterrows():
            curr_val -= row['Kwota']
            ledger_data.append({"Data": target_date.strftime("%Y-%m-%d"), "Opis": f"FIXED: {row['Nazwa']}", "Zmiana": -row['Kwota'], "Saldo": curr_val})
            
        active_raty = df_rat[(df_rat['Start'] <= target_date) & (df_rat['Koniec'] >= target_date)]
        for _, row in active_raty.iterrows():
            curr_val -= row['Kwota']
            ledger_data.append({"Data": target_date.strftime("%Y-%m-%d"), "Opis": f"INSTALLMENT: {row['Rata']}", "Zmiana": -row['Kwota'], "Saldo": curr_val})
        
        # Operacje bieżące
        mask_inc = (df_inc['Data i Godzina'].dt.month == sel_month) & (df_inc['Data i Godzina'].dt.year == sel_year)
        mask_exp = (df_exp['Data i Godzina'].dt.month == sel_month) & (df_exp['Data i Godzina'].dt.year == sel_year)
        
        ops = pd.concat([
            df_inc[mask_inc].assign(T="P"), 
            df_exp[mask_exp].assign(T="W")
        ]).sort_values('Data i Godzina')
        
        for _, row in ops.iterrows():
            ch = row['Kwota'] if row['T'] == "P" else -row['Kwota']
            curr_val += ch
            ledger_data.append({"Data": row['Data i Godzina'].strftime("%m-%d %H:%M"), "Opis": row['Nazwa'], "Zmiana": ch, "Saldo": curr_val})
            
        return pd.DataFrame(ledger_data), curr_val

    # --- 6. DASHBOARD ---
    today_y, today_m = date.today().year, date.today().month
    _, current_total_balance = generate_ledger(today_y, today_m)
    
    st.markdown("<h1>Diner Budget 1960</h1>", unsafe_allow_html=True)
    
    col_met1, col_met2 = st.columns(2)
    with col_met1:
        st.metric("CASH IN PURSE", f"{current_total_balance:,.2f} $")
    with col_met2:
        days_in_month = calendar.monthrange(today_y, today_m)[1]
        days_left = days_in_month - date.today().day + 1
        st.metric("DAILY MILKSHAKE", f"{current_total_balance/days_left:,.2f} $" if days_left > 0 else "---")

    # --- 7. TABS ---
    t1, t2, t3, t4 = st.tabs(["🎵 RECORDS", "🏠 DINER SETUP", "📊 JUKEBOX HIT LIST", "🍔 SODA FOUNTAIN"])

    with t1:
        st.subheader("📻 Rock'n'Roll Records")
        c1, c2 = st.columns(2)
        with c1:
            with st.form("f_i", clear_on_submit=True):
                st.write("*🍭 SODA FOUNTAIN SAVINGS (INCOME)*")
                t_i = st.text_input("Gdzie wpadło?")
                k_i = st.number_input("Ile monet?", step=10.0, min_value=0.0)
                if st.form_submit_button("DODAJ DO PORTFELA"):
                    sh.worksheet("Przychody").append_row([datetime.now().strftime("%Y-%m-%d %H:%M"), t_i, k_i])
                    st.cache_data.clear()
                    st.rerun()
        with c2:
            with st.form("f_e", clear_on_submit=True):
                st.write("*👠 RETRO RAGS (EXPENSE)*")
                t_e = st.text_input("Na co?")
                k_e = st.number_input("Cena", step=1.0, min_value=0.0)
                if st.form_submit_button("ZAPŁAĆ TERAZ"):
                    sh.worksheet("Wydatki").append_row([datetime.now().strftime("%Y-%m-%d %H:%M"), t_e, k_e, "Retro", "Variable"])
                    st.cache_data.clear()
                    st.rerun()

    with t2:
        st.subheader("🏠 Diner Setup - Monthly Bills")
        cf1, cf2 = st.columns(2)
        with cf1:
            with st.form("nf"):
                st.write("*Nowy Stały Wydatek*")
                n_f = st.text_input("Nazwa (np. Prąd)")
                k_f = st.number_input("Kwota mies.", step=10.0)
                if st.form_submit_button("DODAJ OPŁATĘ"):
                    sh.worksheet("Koszty_Stale").append_row([n_f, k_f])
                    st.cache_data.clear()
                    st.rerun()
        with cf2:
            with st.form("nr"):
                st.write("*Nowa Rata*")
                n_r = st.text_input("Nazwa raty")
                k_r = st.number_input("Rata", step=10.0)
                s_r = st.date_input("Start")
                e_r = st.date_input("End")
                if st.form_submit_button("ZAPISZ"):
                    sh.worksheet("Raty").append_row([n_r, k_r, s_r.strftime("%Y-%m-%d"), e_r.strftime("%Y-%m-%d")])
                    st.cache_data.clear()
                    st.rerun()
        st.divider()
        st.write("*Aktywne obciążenia:*")
        st.dataframe(df_fix, use_container_width=True)

    with t3:
        st.subheader("📊 Jukebox Analysis")
        months = {1: "JAN", 2: "FEB", 3: "MAR", 4: "APR", 5: "MAY", 6: "JUN", 7: "JUL", 8: "AUG", 9: "SEP", 10: "OCT", 11: "NOV", 12: "DEC"}
        c_s1, c_s2 = st.columns(2)
        sel_y = c_s1.selectbox("Rok", [2026, 2025])
        sel_m = c_s2.selectbox("Miesiąc", range(1, 13), format_func=lambda x: months[x], index=today_m-1)
        
        df_l, _ = generate_ledger(sel_y, sel_m)
        st.dataframe(df_l.style.format({"Zmiana": "{:,.2f} $", "Saldo": "{:,.2f} $"}), use_container_width=True, hide_index=True)
        
        fig = px.area(df_l, x=range(len(df_l)), y="Saldo", title=f"Wędrówka Bogactwa - {months[sel_m]}")
        fig.update_traces(line_color='#d62828', fillcolor='rgba(214, 40, 40, 0.2)')
        fig.update_layout(plot_bgcolor='white', paper_bgcolor='white')
        st.plotly_chart(fig, use_container_width=True)

    with t4:
        st.subheader("🍔 Soda Fountain - Shopping List")
        if not df_shp.empty:
            st.write("*Twoja Lista:*")
            for item in df_shp["Produkt"].tolist():
                st.write(f"- {item}")
        
        if st.button("WYCZYŚĆ LISTĘ ZAKUPÓW"):
            sh.worksheet("Zakupy").clear()
            sh.worksheet("Zakupy").append_row(["Data", "Produkt"])
            st.cache_data.clear()
            st.rerun()

    with st.sidebar:
        st.markdown("<h2 style='color: white !important;'>💎 THE VAULT</h2>", unsafe_allow_html=True)
        st.metric("SAVINGS", f"{s_sav:,.2f} $")
        st.divider()
        if st.button("🚜 HARVEST SURPLUS"):
            if current_total_balance > 0:
                sh.worksheet("Oszczednosci").update_acell('A2', str(s_sav + current_total_balance))
                st.balloons()
                st.cache_data.clear()
                time.sleep(1)
                st.rerun()
