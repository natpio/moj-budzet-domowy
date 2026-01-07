import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
from google.oauth2 import service_account
from datetime import datetime, date
import calendar

# --- KONFIGURACJA ---
st.set_page_config(page_title="Budżet Domowy", layout="wide")

# --- FUNKCJA LOGOWANIA ---
def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["credentials"]["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.title("🔒 Logowanie")
        st.text_input("Wpisz hasło i naciśnij Enter", type="password", on_change=password_entered, key="password")
        if "password_correct" in st.session_state and not st.session_state["password_correct"]:
            st.error("❌ Błędne hasło!")
        return False
    return True

if check_password():
    # --- STYLIZACJA WYSOKIEJ CZYTELNOŚCI (JASNY MOTYW) ---
    st.markdown("""
        <style>
        .main { background-color: #ffffff; }
        div[data-testid="stMetric"] {
            background-color: #f0f2f6 !important;
            border: 2px solid #000000 !important;
            border-radius: 10px;
        }
        /* Czarny, gruby tekst dla wszystkich napisów */
        label, p, [data-testid="stMetricLabel"], [data-testid="stMetricValue"] {
            color: #000000 !important;
            font-weight: bold !important;
            opacity: 1 !important;
        }
        h1, h2, h3 { color: #000000 !important; }
        </style>
        """, unsafe_allow_html=True)

    @st.cache_resource
    def get_sheet(name):
        creds = service_account.Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
        return gspread.authorize(creds).open("Budzet_Data").worksheet(name)

    # Pobieranie danych
    s_inc = get_sheet("Przychody")
    s_exp = get_sheet("Wydatki")
    s_sav = get_sheet("Oszczednosci")
    # ... (tutaj możesz dodać resztę arkuszy)

    df_inc = pd.DataFrame(s_inc.get_all_records())
    df_exp = pd.DataFrame(s_exp.get_all_records())

    # Obliczenia
    today = date.today()
    dni_m = calendar.monthrange(today.year, today.month)[1] - today.day + 1
    inc_total = df_inc['Kwota'].sum() if not df_inc.empty else 0
    exp_total = df_exp['Kwota'].sum() if not df_exp.empty else 0
    balance = inc_total - exp_total
    daily = balance / dni_m if dni_m > 0 else balance

    # DASHBOARD
    st.title("💰 Twój Budżet")
    c1, c2 = st.columns(2)
    c1.metric("DOSTĘPNE ŚRODKI", f"{balance:.2f} PLN")
    c2.metric("NA DZIEŃ", f"{daily:.2f} PLN")

    st.divider()
    
    # Formularz wydatku
    with st.form("nowy_wydatek"):
        st.subheader("Dodaj Wydatek")
        n = st.text_input("Co kupiłeś?")
        k = st.number_input("Kwota", min_value=0.0)
        if st.form_submit_button("ZAPISZ"):
            s_exp.append_row([datetime.now().strftime("%Y-%m-%d"), n, k])
            st.success("Dodano!")
            st.rerun()
