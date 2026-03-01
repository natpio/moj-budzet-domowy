import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
from google.oauth2 import service_account
from datetime import datetime, date
import calendar
import time

# --- 1. KONFIGURACJA STRONY ---
st.set_page_config(page_title="Gospodarstwo Finansowe 2026", layout="wide", page_icon="🌾")

# --- 2. LOGOWANIE ---
def check_password():
    if "password_correct" not in st.session_state:
        st.markdown("<h2 style='text-align: center; color: #b00000;'>🪗 Witaj w Zagrodzie. Podaj hasło:</h2>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            pwd = st.text_input("Klucz do kłódki", type="password")
            if st.button("Otwórz"):
                if pwd == st.secrets["credentials"]["password"]:
                    st.session_state["password_correct"] = True
                    st.rerun()
                else:
                    st.error("❌ Zły klucz!")
        return False
    return True

if check_password():
    # --- 3. STYLE CSS ---
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Fondamento&family=Almendra&display=swap');
        .stApp { background-color: #f4ece1; background-image: url("https://www.transparenttextures.com/patterns/natural-paper.png"); }
        [data-testid="stMetric"] { background: #ffffff !important; border: 4px double #b00000 !important; border-radius: 10px !important; box-shadow: 5px 5px 0px 0px #2c3e50 !important; padding: 15px !important; }
        h1, h2, h3 { color: #b00000 !important; font-family: 'Almendra', serif !important; text-align: center; border-bottom: 2px solid #b00000; }
        .stButton>button { background: #2c3e50 !important; color: #f4ece1 !important; font-family: 'Fondamento', cursive !important; width: 100%; height: 3.5em; border: 2px solid #b00000; }
        [data-testid="stSidebar"] { background: #e6d5bc !important; border-right: 3px solid #b00000 !important; }
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
        st.error(f"🚜 Błąd bazy danych: {e}"); st.stop()

    # Czyszczenie danych (odporność na błędy)
    for df in [df_inc, df_exp, df_fix, df_rat]:
        df['Kwota'] = pd.to_numeric(df['Kwota'], errors='coerce').fillna(0)
    
    df_inc['Data i Godzina'] = pd.to_datetime(df_inc['Data i Godzina'], errors='coerce')
    df_exp['Data i Godzina'] = pd.to_datetime(df_exp['Data i Godzina'], errors='coerce')
    df_rat['Start'] = pd.to_datetime(df_rat['Start'], errors='coerce')
    df_rat['Koniec'] = pd.to_datetime(df_rat['Koniec'], errors='coerce')
    
    df_inc = df_inc.dropna(subset=['Data i Godzina'])
    df_exp = df_exp.dropna(subset=['Data i Godzina'])
    s_sav = float(str(df_sav.iloc[0,0]).replace(',', '.')) if not df_sav.empty else 0.0

    # --- 5. LOGIKA KSIĘGI ---
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

        ledger_data = []
        curr_val = op_bal
        ledger_data.append({"Data": target_date.strftime("%Y-%m-%d"), "Opis": "BILANS OTWARCIA", "Zmiana": 0.0, "Saldo": curr_val})
        curr_val += 1600
        ledger_data.append({"Data": target_date.strftime("%Y-%m-%d"), "Opis": "ZASILENIE: 800+", "Zmiana": 1600.0, "Saldo": curr_val})
        
        for _, row in df_fix.iterrows():
            curr_val -= row['Kwota']
            ledger_data.append({"Data": target_date.strftime("%Y-%m-%d"), "Opis": f"OPŁATA: {row['Nazwa']}", "Zmiana": -row['Kwota'], "Saldo": curr_val})
        
        active_raty = df_rat[(df_rat['Start'] <= target_date) & (df_rat['Koniec'] >= target_date)]
        for _, row in active_raty.iterrows():
            curr_val -= row['Kwota']
            ledger_data.append({"Data": target_date.strftime("%Y-%m-%d"), "Opis": f"RATA: {row['Rata']}", "Zmiana": -row['Kwota'], "Saldo": curr_val})

        mask_inc = (df_inc['Data i Godzina'].dt.month == sel_month) & (df_inc['Data i Godzina'].dt.year == sel_year)
        mask_exp = (df_exp['Data i Godzina'].dt.month == sel_month) & (df_exp['Data i Godzina'].dt.year == sel_year)
        ops = pd.concat([df_inc[mask_inc].assign(T="P"), df_exp[mask_exp].assign(T="W")]).sort_values('Data i Godzina')
        
        for _, row in ops.iterrows():
            change = row['Kwota'] if row['T'] == "P" else -row['Kwota']
            curr_val += change
            ledger_data.append({"Data": row['Data i Godzina'].strftime("%Y-%m-%d %H:%M"), "Opis": row['Nazwa'], "Zmiana": change, "Saldo": curr_val})
            
        return pd.DataFrame(ledger_data), curr_val

    # --- 6. GŁÓWNE METRYKI ---
    today_y, today_m = date.today().year, date.today().month
    _, current_total_balance = generate_ledger(today_y, today_m)
    
    st.markdown("<h1>🎻 REJESTR GOSPODARSKI</h1>", unsafe_allow_html=True)
    c_m1, c_m2 = st.columns(2)
    c_m1.metric("📦 W KALETCE (NA DZIŚ)", f"{current_total_balance:,.2f} PLN")
    days_left = calendar.monthrange(today_y, today_m)[1] - date.today().day + 1
    c_m2.metric("🥖 NA DZIEŃ", f"{current_total_balance/days_left:,.2f} PLN" if days_left > 0 else "---")

    # --- 7. ZAKŁADKI ---
    t1, t2, t3, t4 = st.tabs(["✍️ ZAPISY", "🏠 STAŁE & RATY", "📊 KSIĘGA (ANALIZA)", "🛒 LISTY"])

    with t1:
        col_i, col_e = st.columns(2)
        with col_i:
            with st.form("f_inc", clear_on_submit=True):
                st.subheader("➕ Przychód")
                t, k = st.text_input("Tytuł"), st.number_input("Kwota", step=50.0)
                if st.form_submit_button("DODAJ"):
                    sh.worksheet("Przychody").append_row([datetime.now().strftime("%Y-%m-%d %H:%M"), t, k])
                    st.cache_data.clear(); st.rerun()
        with col_e:
            with st.form("f_exp", clear_on_submit=True):
                st.subheader("➖ Wydatek")
                t, k = st.text_input("Na co?"), st.number_input("Kwota", step=1.0)
                if st.form_submit_button("ZAPŁAĆ"):
                    sh.worksheet("Wydatki").append_row([datetime.now().strftime("%Y-%m-%d %H:%M"), t, k, "Inne", "Zmienny"])
                    st.cache_data.clear(); st.rerun()

    with t2:
        st.subheader("⚙️ DODAWANIE NOWYCH OBCIĄŻEŃ")
        c_f1, c_f2 = st.columns(2)
        with c_f1:
            with st.form("new_fix"):
                st.write("**Nowy Stały Koszt**")
                n_fix, k_fix = st.text_input("Nazwa (np. Prąd)"), st.number_input("Kwota mies.", step=10.0)
                if st.form_submit_button("DODAJ KOSZT STAŁY"):
                    sh.worksheet("Koszty_Stale").append_row([n_fix, k_fix])
                    st.cache_data.clear(); st.rerun()
        with c_f2:
            with st.form("new_rat"):
                st.write("**Nowa Rata**")
                n_rat, k_rat = st.text_input("Nazwa kredytu/raty"), st.number_input("Kwota raty", step=10.0)
                d_s, d_e = st.date_input("Od kiedy"), st.date_input("Do kiedy")
                if st.form_submit_button("ZAPISZ RATĘ"):
                    # Tu poprawka: upewniamy się, że kolumny to Rata, Kwota, Start, Koniec
                    sh.worksheet("Raty").append_row([n_rat, k_rat, d_s.strftime("%Y-%m-%d"), d_e.strftime("%Y-%m-%d")])
                    st.cache_data.clear(); st.rerun()
        
        st.divider()
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            st.write("**🏠 Twoje Stałe Opłaty:**")
            st.dataframe(df_fix, use_container_width=True, hide_index=True)
        with col_t2:
            st.write("**📜 Twoje Harmonogramy Rat:**")
            # Pokazujemy raty, które jeszcze trwają
            df_active = df_rat[df_rat['Koniec'] >= pd.Timestamp(date.today())].copy()
            if not df_active.empty:
                df_active['Start'] = df_active['Start'].dt.strftime('%Y-%m-%d')
                df_active['Koniec'] = df_active['Koniec'].dt.strftime('%Y-%m-%d')
            st.dataframe(df_active, use_container_width=True, hide_index=True)

    with t3:
        st.subheader("📜 KSIĘGA GŁÓWNA")
        months_list = {1: "Styczeń", 2: "Luty", 3: "Marzec", 4: "Kwiecień", 5: "Maj", 6: "Czerwiec", 7: "Lipiec", 8: "Sierpień", 9: "Wrzesień", 10: "Październik", 11: "Listopad", 12: "Grudzień"}
        col_s1, col_s2 = st.columns(2)
        s_year = col_s1.selectbox("Rok", [2026, 2025])
        s_month = col_s2.selectbox("Miesiąc", range(1, 13), format_func=lambda x: months_list[x], index=date.today().month-1)
        
        df_ledger, _ = generate_ledger(s_year, s_month)
        st.dataframe(df_ledger.style.format({"Zmiana": "{:,.2f} PLN", "Saldo": "{:,.2f} PLN"}), use_container_width=True, hide_index=True)

    with t4:
        st.subheader("🛒 Listy")
        st.write(df_shp["Produkt"].tolist() if not df_shp.empty else "Brak zakupów")
        if st.button("Wyczyść listę"):
            sh.worksheet("Zakupy").clear(); sh.worksheet("Zakupy").append_row(["Data", "Produkt"])
            st.cache_data.clear(); st.rerun()

    with st.sidebar:
        st.metric("SKRZYNIA (SEJF)", f"{s_sav:,.2f} PLN")
        if st.button("🚜 ŻNIWA"):
            if current_total_balance > 0:
                sh.worksheet("Oszczednosci").update_acell('A2', str(s_sav + current_total_balance))
                st.cache_data.clear(); time.sleep(1); st.rerun()
