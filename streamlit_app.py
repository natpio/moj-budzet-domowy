import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
from google.oauth2 import service_account
from datetime import datetime, date
import calendar
import time

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Ranczo Finansowe 2026", layout="wide", page_icon="🤠")

# --- FUNKCJA LOGOWANIA ---
def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["credentials"]["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.markdown("<h2 style='text-align: center; color: #5d4037;'>🌵 Zatrzymaj się, kowboju! Podaj hasło:</h2>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            st.text_input("Klucz do sejfu", type="password", on_change=password_entered, key="password")
            if "password_correct" in st.session_state and not st.session_state["password_correct"]:
                st.error("❌ Zły klucz! Konie parskają ze śmiechu.")
        return False
    return True

if check_password():
    # --- STYLIZACJA ---
    st.markdown("""
        <style>
        .main { background-color: #f4ece1; }
        [data-testid="stMetric"] { background-color: #3e2723 !important; border: 3px solid #8d6e63 !important; padding: 20px !important; border-radius: 15px !important; }
        [data-testid="stMetricLabel"] p { color: #d7ccc8 !important; font-size: 18px !important; font-weight: bold !important; text-transform: uppercase; }
        [data-testid="stMetricValue"] div { color: #ffffff !important; font-size: 38px !important; font-family: 'Courier New', Courier, monospace; }
        h1, h2, h3 { color: #5d4037 !important; font-family: 'Georgia', serif; }
        .stButton>button { background-color: #a1887f !important; color: white !important; border: 2px solid #5d4037 !important; font-weight: bold !important; width: 100%; }
        [data-testid="stExpander"] { background-color: #ffffff !important; border: 1px solid #8d6e63 !important; border-radius: 10px !important; }
        </style>
        """, unsafe_allow_html=True)

    # --- POŁĄCZENIE API ---
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
        names = ["Przychody", "Wydatki", "Koszty_Stale", "Raty", "Oszczednosci", "Zakupy", "Zadania", "Planowanie"]
        data = {}
        for name in names:
            data[name] = pd.DataFrame(sh.worksheet(name).get_all_records())
            time.sleep(0.3)
        return data

    def get_now(): return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        all_d = load_all_data()
        df_inc, df_exp, df_fix, df_rat, df_sav, df_shp, df_tsk, df_pla = [all_d[n] for n in ["Przychody", "Wydatki", "Koszty_Stale", "Raty", "Oszczednosci", "Zakupy", "Zadania", "Planowanie"]]
    except:
        st.error("🤠 Problem z połączeniem. Odśwież stronę."); st.stop()

    # --- OBLICZENIA I FILTROWANIE ---
    today = date.today()
    current_month = today.strftime("%Y-%m")
    dni_m = calendar.monthrange(today.year, today.month)[1] - today.day + 1
    p800 = 1600 # Stała 800+
    
    # Filtrujemy tylko obecny miesiąc dla Dashboardu
    if not df_inc.empty and 'Data i Godzina' in df_inc.columns:
        df_inc_curr = df_inc[df_inc['Data i Godzina'].str.contains(current_month, na=False)].copy()
    else:
        df_inc_curr = df_inc.copy()

    if not df_exp.empty and 'Data i Godzina' in df_exp.columns:
        df_exp_curr = df_exp[df_exp['Data i Godzina'].str.contains(current_month, na=False)].copy()
    else:
        df_exp_curr = df_exp.copy()

    # Raty aktywne dzisiaj
    df_rat_active = pd.DataFrame()
    suma_rat = 0
    if not df_rat.empty:
        df_rat['Start'] = pd.to_datetime(df_rat['Start'])
        df_rat['Koniec'] = pd.to_datetime(df_rat['Koniec'])
        mask = (df_rat['Start'] <= pd.Timestamp(today)) & (df_rat['Koniec'] >= pd.Timestamp(today))
        df_rat_active = df_rat[mask].copy()
        suma_rat = df_rat_active['Kwota'].sum()

    inc_total = (df_inc_curr['Kwota'].sum() if not df_inc_curr.empty else 0) + p800
    exp_total = (df_exp_curr['Kwota'].sum() if not df_exp_curr.empty else 0) + (df_fix['Kwota'].sum() if not df_fix.empty else 0) + suma_rat
    balance = inc_total - exp_total
    daily = balance / dni_m if dni_m > 0 else balance

    # --- SIDEBAR ---
    with st.sidebar:
        st.markdown("<h1 style='text-align:center;'>🤠 SEJF</h1>", unsafe_allow_html=True)
        client = get_client()
        sh = client.open("Budzet_Data")
        ws_sav = sh.worksheet("Oszczednosci")
        sav_val = float(str(ws_sav.acell('A2').value).replace(',', '.'))
        st.metric("ZŁOTO W SEJFIE", f"{sav_val:,.2f} PLN")
        
        st.divider()
        if st.button("🏜️ ZAMKNIJ MIESIĄC"):
            # 1. Przelej nadwyżkę do sejfu
            new_sav = sav_val + balance
            ws_sav.update_acell('A2', str(new_sav))
            # 2. Wyczyść arkusze (opcjonalnie - tutaj tylko czyścimy cache, by widzieć nowe saldo)
            st.success(f"Przelano {balance:.2f} PLN do sejfu!")
            st.cache_data.clear()
            time.sleep(1)
            st.rerun()

    # --- DASHBOARD ---
    st.markdown("<h1 style='text-align: center;'>📜 KSIĘGA RACHUNKOWA</h1>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    c1.metric("💰 PORTFEL", f"{balance:,.2f} PLN")
    c2.metric("☀️ NA DZIEŃ", f"{daily:,.2f} PLN")

    h_inc, h_exp = st.columns(2)
    with h_inc:
        st.metric("📈 DOCHODY", f"{inc_total:,.2f} PLN")
        with st.expander("🔍 Szczegóły wpływów"):
            i_list = df_inc_curr[["Nazwa", "Kwota"]].copy()
            st.table(i_list)

    with h_exp:
        st.metric("📉 WYDATKI", f"{exp_total:,.2f} PLN")
        with st.expander("🔍 Pełna lista kosztów"):
            e_all = pd.concat([df_exp_curr[["Nazwa", "Kwota"]], df_fix[["Nazwa", "Kwota"]], df_rat_active[["Rata", "Kwota"]].rename(columns={"Rata": "Nazwa"})], ignore_index=True)
            st.table(e_all)

    # --- ZAKŁADKI ---
    tabs = st.tabs(["💸 Wpisy", "🏠 Stałe & Raty", "📅 Plany", "🛒 Listy"])

    with tabs[0]:
        ci, ce = st.columns(2)
        with ci:
            with st.form("f_inc", clear_on_submit=True):
                st.subheader("➕ Przychód")
                ni, ki = st.text_input("Skąd?"), st.number_input("Kwota")
                if st.form_submit_button("DODAJ"):
                    sh.worksheet("Przychody").append_row([get_now(), ni, ki])
                    st.cache_data.clear(); st.rerun()
        with ce:
            with st.form("f_exp", clear_on_submit=True):
                st.subheader("➖ Wydatek")
                ne, ke = st.text_input("Na co?"), st.number_input("Kwota")
                ka = st.selectbox("Kategoria", ["Jedzenie", "Dom", "Transport", "Rozrywka", "Inne"])
                if st.form_submit_button("DODAJ"):
                    sh.worksheet("Wydatki").append_row([get_now(), ne, ke, ka, "Zmienny"])
                    st.cache_data.clear(); st.rerun()
        
        st.subheader("🖋️ Zarządzaj historią")
        df_exp["USUŃ"] = False
        ed_e = st.data_editor(df_exp, num_rows="dynamic", use_container_width=True, key="ed_w_v2")
        if st.button("Zapisz zmiany"):
            cl = ed_e[ed_e["USUŃ"] == False].drop(columns=["USUŃ"])
            ws = sh.worksheet("Wydatki")
            ws.clear(); ws.append_row(["Data i Godzina", "Nazwa", "Kwota", "Kategoria", "Typ"])
            if not cl.empty: ws.append_rows(cl.values.tolist())
            st.cache_data.clear(); st.rerun()

    # (Reszta zakładki Stałe, Raty, Plany pozostaje taka sama jak w poprzednim sprawnym kodzie)
