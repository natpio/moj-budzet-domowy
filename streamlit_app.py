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
    # --- STYLIZACJA COUNTRY ---
    st.markdown("""
        <style>
        .main { background-color: #f4ece1; }
        [data-testid="stMetric"] {
            background-color: #3e2723 !important;
            border: 3px solid #8d6e63 !important;
            padding: 20px !important;
            border-radius: 15px !important;
        }
        [data-testid="stMetricLabel"] p {
            color: #d7ccc8 !important;
            font-size: 18px !important;
            font-weight: bold !important;
            text-transform: uppercase;
        }
        [data-testid="stMetricValue"] div {
            color: #ffffff !important;
            font-size: 38px !important;
            font-family: 'Courier New', Courier, monospace;
        }
        h1, h2, h3 { color: #5d4037 !important; font-family: 'Georgia', serif; }
        .stButton>button {
            background-color: #a1887f !important;
            color: white !important;
            border: 2px solid #5d4037 !important;
            font-weight: bold !important;
        }
        [data-testid="stForm"] {
            background-color: #ffffff !important;
            border: 2px dashed #8d6e63 !important;
        }
        </style>
        """, unsafe_allow_html=True)

    # --- POŁĄCZENIE Z ARKUSZEM (Z OPTYMALIZACJĄ) ---
    @st.cache_resource
    def get_client():
        creds_dict = st.secrets["gcp_service_account"]
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=scope)
        return gspread.authorize(creds)

    # Cache danych na 2 minuty, aby nie przekroczyć limitu Read Requests
    @st.cache_data(ttl=120)
    def load_all_data():
        client = get_client()
        sh = client.open("Budzet_Data")
        names = ["Przychody", "Wydatki", "Koszty_Stale", "Raty", "Oszczednosci", "Zakupy", "Zadania", "Planowanie"]
        data = {}
        for name in names:
            data[name] = pd.DataFrame(sh.worksheet(name).get_all_records())
            time.sleep(0.2) # Krótka przerwa dla API
        return data

    def get_now(): return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Pobieranie danych z cache
    try:
        all_df = load_all_data()
    except Exception as e:
        st.error("🤠 Serwer Google odpoczywa. Odśwież za chwilę...")
        st.stop()

    df_inc, df_exp, df_fix, df_rat, df_sav, df_shp, df_tsk, df_pla = [all_df[n] for n in ["Przychody", "Wydatki", "Koszty_Stale", "Raty", "Oszczednosci", "Zakupy", "Zadania", "Planowanie"]]

    # --- OBLICZENIA ---
    today = date.today()
    dni_m = calendar.monthrange(today.year, today.month)[1] - today.day + 1
    p800 = 1600 # Stała kwota dla uproszczenia
    
    suma_rat = 0
    if not df_rat.empty:
        df_rat['Start'] = pd.to_datetime(df_rat['Start'])
        df_rat['Koniec'] = pd.to_datetime(df_rat['Koniec'])
        mask = (df_rat['Start'] <= pd.Timestamp(today)) & (df_rat['Koniec'] >= pd.Timestamp(today))
        suma_rat = df_rat[mask]['Kwota'].sum()

    inc_total = (df_inc['Kwota'].sum() if not df_inc.empty else 0) + p800
    exp_total = (df_exp['Kwota'].sum() if not df_exp.empty else 0) + (df_fix['Kwota'].sum() if not df_fix.empty else 0) + suma_rat
    balance = inc_total - exp_total
    daily = balance / dni_m if dni_m > 0 else balance

    # --- SIDEBAR ---
    with st.sidebar:
        st.markdown("<h1 style='text-align:center;'>🤠 SEJF</h1>", unsafe_allow_html=True)
        # Sejf pobieramy zawsze na świeżo, bo to krytyczne dane
        client = get_client()
        s_sav = client.open("Budzet_Data").worksheet("Oszczednosci")
        try:
            sav_val = float(str(s_sav.acell('A2').value).replace(',', '.'))
        except:
            sav_val = 0.0
        st.metric("ZŁOTO W SEJFIE", f"{sav_val:,.2f} PLN")
        
        with st.expander("💰 WYPŁATA"):
            amt = st.number_input("Ile dukatów?", min_value=0.0, key="side_w")
            if st.button("POBIERZ Z SEJFU"):
                s_sav.update_acell('A2', str(sav_val - amt))
                client.open("Budzet_Data").worksheet("Przychody").append_row([get_now(), "WYPŁATA ZE SKARBCA", amt])
                st.cache_data.clear() # Czyścimy cache po zmianie
                st.rerun()

    # --- UKŁAD GŁÓWNY ---
    st.markdown("<h1 style='text-align: center;'>📜 KSIĘGA RACHUNKOWA</h1>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 PORTFEL", f"{balance:,.2f} PLN")
    c2.metric("☀️ NA DZIEŃ", f"{daily:,.2f} PLN")
    c3.metric("📈 DOCHODY", f"{inc_total:,.2f} PLN")
    c4.metric("📉 WYDATKI", f"{exp_total:,.2f} PLN")

    tabs = st.tabs(["🤠 Dashboard", "💸 Wpisy", "🏠 Stałe & Raty", "📅 Plany", "🛒 Listy"])

    with tabs[1]: # Sekcja wpisów - przykład dodawania
        col_i, col_e = st.columns(2)
        with col_i:
            with st.form("f_inc"):
                ni, ki = st.text_input("Skąd wpłata?"), st.number_input("Kwota")
                if st.form_submit_button("DODAJ PRZYCHÓD"):
                    client.open("Budzet_Data").worksheet("Przychody").append_row([get_now(), ni, ki])
                    st.cache_data.clear()
                    st.rerun()
        # ... reszta formularzy analogicznie z st.cache_data.clear()
