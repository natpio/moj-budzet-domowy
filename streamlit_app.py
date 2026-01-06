import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, date
import calendar
import gspread
from google.oauth2 import service_account

# --- KONFIGURACJA POŁĄCZENIA ---
def get_gspread_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = st.secrets["gcp_service_account"]
    creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=scope)
    return gspread.authorize(creds)

# --- LOGIKA APLIKACJI ---
st.set_page_config(page_title="Budżet Pro", layout="wide")

def calculate_800plus():
    today = date.today()
    corka1 = date(2018, 8, 1)
    corka2 = date(2022, 11, 1)
    total = 0
    if (today.year - corka1.year) < 18: total += 800
    if (today.year - corka2.year) < 18: total += 800
    return total

def get_days_left():
    today = date.today()
    last_day = calendar.monthrange(today.year, today.month)[1]
    return last_day - today.day + 1

# --- INTERFEJS ---
st.title("💰 Domowy Budżet Pro")

tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "➕ Dodaj Dane", "⚙️ Ustawienia"])

with tab1:
    st.header("Stan na dziś")
    col1, col2, col3 = st.columns(3)
    
    dni = get_days_left()
    pieniadze_800 = calculate_800plus()
    
    col1.metric("800 Plus", f"{pieniadze_800} PLN")
    col2.metric("Dni do końca miesiąca", f"{dni}")
    col3.info("Połącz z Google Sheets w zakładce Ustawienia, aby zobaczyć pełne dane.")

with tab2:
    st.subheader("Wpisz wydatki i dochody")
    with st.form("budget_form"):
        typ = st.selectbox("Typ", ["Wydatek Zmienny", "Wydatek Stały", "Dochód", "Rata"])
        kwota = st.number_input("Kwota", min_value=0.0)
        data = st.date_input("Data", date.today())
        if typ == "Rata":
            koniec = st.date_input("Koniec spłaty")
        submit = st.form_submit_button("Zapisz do arkusza")
        if submit:
            st.success("Wysłano! (Połącz Streamlit z Secrets, aby zapisywać)")

st.sidebar.markdown("### 🏦 Kasa Oszczędnościowa")
st.sidebar.write("Tu pojawią się Twoje oszczędności po połączeniu bazy.")
