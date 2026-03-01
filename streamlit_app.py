import streamlit as st
import pandas as pd
import gspread
from google.oauth2 import service_account
from datetime import datetime, date
import calendar

# --- KONFIGURACJA ---
st.set_page_config(page_title="Gospodarstwo 2026 - DEBUG", layout="wide")

@st.cache_resource
def get_client():
    creds_dict = st.secrets["gcp_service_account"]
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=scope)
    return gspread.authorize(creds)

# --- ŁADOWANIE DANYCH ---
client = get_client()
sh = client.open("Budzet_Data")

def load(name):
    return pd.DataFrame(sh.worksheet(name).get_all_records())

df_inc = load("Przychody")
df_exp = load("Wydatki")
df_fix = load("Koszty_Stale")
df_rat = load("Raty")
df_sav = load("Oszczednosci")

# --- OBLICZENIA DIAGNOSTYCZNE ---
today = date.today()
num_m = (today.year - 2026) * 12 + today.month # Powinno być 3 dla marca

# Konwersja kwot na liczby (na wypadek błędów w Excelu)
df_inc['Kwota'] = pd.to_numeric(df_inc['Kwota'], errors='coerce').fillna(0)
df_exp['Kwota'] = pd.to_numeric(df_exp['Kwota'], errors='coerce').fillna(0)
df_fix['Kwota'] = pd.to_numeric(df_fix['Kwota'], errors='coerce').fillna(0)
df_rat['Kwota'] = pd.to_numeric(df_rat['Kwota'], errors='coerce').fillna(0)

s_inc = df_inc['Kwota'].sum()
s_800 = num_m * 1600
s_exp = df_exp['Kwota'].sum()
s_fix = num_m * df_fix['Kwota'].sum()
s_sav = float(str(df_sav.iloc[0,0]).replace(',', '.'))

# Obliczanie rat
total_raty = 0
df_rat['Start'] = pd.to_datetime(df_rat['Start'])
df_rat['Koniec'] = pd.to_datetime(df_rat['Koniec'])
for m in pd.date_range(start="2026-01-01", periods=num_m, freq='MS'):
    mask = (df_rat['Start'] <= m) & (df_rat['Koniec'] >= m)
    total_raty += df_rat[mask]['Kwota'].sum()

# WYNIK KOŃCOWY
balance = s_inc + s_800 - s_exp - s_fix - total_raty - s_sav

# --- WYŚWIETLANIE DIAGNOSTYKI ---
st.title("🚜 DIAGNOSTYKA SYSTEMU")
with st.expander("🔍 ZOBACZ CO WIDZI KOMPUTER (DEBUG)", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Liczba miesięcy (od Jan 2026):** {num_m}")
        st.write(f"**Suma Przychodów (Tabela):** {s_inc:,.2f} PLN")
        st.write(f"**Suma 800+ ({num_m} msc):** {s_800:,.2f} PLN")
        st.write(f"**Suma Wydatków (Całość):** {s_exp:,.2f} PLN")
    with col2:
        st.write(f"**Suma Kosztów Stałych:** {s_fix:,.2f} PLN")
        st.write(f"**Suma Rat:** {total_raty:,.2f} PLN")
        st.write(f"**W Skrzyni (Sejf):** {s_sav:,.2f} PLN")
        st.write("---")
        st.write(f"### WYNIK: {balance:,.2f} PLN")

st.divider()

# --- GŁÓWNE METRYKI ---
c1, c2 = st.columns(2)
c1.metric("📦 W KALETCE", f"{balance:,.2f} PLN")
c2.metric("💰 W SKRZYNI", f"{s_sav:,.2f} PLN")
