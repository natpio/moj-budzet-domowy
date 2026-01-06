import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
from google.oauth2 import service_account
from datetime import datetime, date
import calendar

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Pro Budget Master", layout="wide", page_icon="💰")

# --- STYLIZACJA ---
st.markdown("""
    <style>
    .stMetric { background-color: #1a1c24; padding: 15px; border-radius: 10px; border: 1px solid #3e4452; }
    div[data-testid="stExpander"] { border: none !important; box-shadow: none !important; }
    </style>
    """, unsafe_allow_html=True)

# --- POŁĄCZENIE Z GOOGLE SHEETS ---
def get_sheet(sheet_name):
    try:
        creds_dict = st.secrets["gcp_service_account"]
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        return client.open("Budzet_Data").worksheet(sheet_name)
    except:
        st.error(f"Nie znaleziono arkusza o nazwie '{sheet_name}'!")
        return None

# --- LOGIKA BIZNESOWA ---
def calculate_800plus():
    today = date.today()
    dzieci = [date(2018, 8, 1), date(2022, 11, 1)]
    suma = 0
    for bday in dzieci:
        wiek = today.year - bday.year - ((today.month, today.day) < (bday.month, bday.day))
        if wiek < 18: suma += 800
    return suma

def get_days_left():
    today = date.today()
    ostatni_dzien = calendar.monthrange(today.year, today.month)[1]
    return ostatni_dzien - today.day + 1

# --- POBIERANIE DANYCH ---
sheet_inc = get_sheet("Przychody")
sheet_exp = get_sheet("Wydatki")
sheet_rat = get_sheet("Raty")
sheet_sav = get_sheet("Oszczednosci")

# Konwersja do DataFrame
df_inc = pd.DataFrame(sheet_inc.get_all_records()) if sheet_inc else pd.DataFrame()
df_exp = pd.DataFrame(sheet_exp.get_all_records()) if sheet_exp else pd.DataFrame()
df_rat = pd.DataFrame(sheet_rat.get_all_records()) if sheet_rat else pd.DataFrame()

# Obliczenia rat na obecny miesiąc
suma_rat = 0
today_dt = pd.to_datetime(date.today())
if not df_rat.empty:
    df_rat['Start'] = pd.to_datetime(df_rat['Start'])
    df_rat['Koniec'] = pd.to_datetime(df_rat['Koniec'])
    aktywne_raty = df_rat[(df_rat['Start'] <= today_dt) & (df_rat['Koniec'] >= today_dt)]
    suma_rat = aktywne_raty['Kwota'].sum()

# --- SIDEBAR ---
with st.sidebar:
    st.title("💎 Menu")
    oszczednosci = float(sheet_sav.acell('A2').value.replace(',', '.')) if sheet_sav else 0
    st.metric("Skarbiec (Oszczędności)", f"{oszczednosci:,.2f} PLN")
    
    if st.button("🚨 RATUNEK (Pobierz 500zł)"):
        new_val = oszczednosci - 500
        sheet_sav.update_acell('A2', str(new_val))
        st.rerun()

# --- GŁÓWNY PANEL ---
tabs = st.tabs(["📊 ANALIZA", "💸 WYDATKI & DOCHODY", "📅 RATY & PLANOWANIE"])

with tabs[0]:
    st.subheader("Sytuacja na dziś")
    
    total_inc = (df_inc['Kwota'].sum() if not df_inc.empty else 0) + calculate_800plus()
    total_exp = (df_exp['Kwota'].sum() if not df_exp.empty else 0) + suma_rat
    bilans = total_inc - total_exp
    dzienny = bilans / get_days_left() if get_days_left() > 0 else 0
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Do dyspozycji", f"{bilans:,.2f} PLN")
    c2.metric("Na każdy dzień", f"{dzienny:,.2f} PLN", delta=f"{get_days_left()} dni")
    c3.metric("W tym 800+", f"{calculate_800plus()} PLN")

    st.divider()
    
    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        if not df_exp.empty:
            fig = px.pie(df_exp, values='Kwota', names='Kategoria', title="Struktura wydatków", hole=.4)
            st.plotly_chart(fig, use_container_width=True)
    with col_chart2:
        st.write("📈 **Ostatnie ruchy:**")
        st.dataframe(df_exp.tail(5), use_container_width=True)

with tabs[1]:
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("### 📥 Dodaj Dochód")
        with st.form("inc_form", clear_on_submit=True):
            n = st.text_input("Nazwa")
            k = st.number_input("Kwota", min_value=0.0)
            if st.form_submit_button("Zapisz dochód"):
                sheet_inc.append_row([str(date.today()), n, k])
                st.success("Zapisano!")
                st.rerun()

    with col_b:
        st.markdown("### 📤 Dodaj Wydatek")
        with st.form("exp_form", clear_on_submit=True):
            n_e = st.text_input("Nazwa")
            k_e = st.number_input("Kwota", min_value=0.0)
            kat = st.selectbox("Kategoria", ["Jedzenie", "Dom", "Transport", "Rozrywka", "Zdrowie"])
            typ = st.radio("Typ", ["Zmienny", "Stały"], horizontal=True)
            if st.form_submit_button("Zapisz wydatek"):
                sheet_exp.append_row([str(date.today()), n_e, k_e, kat, typ])
                st.success("Zaksięgowano!")
                st.rerun()

with tabs[2]:
    st.subheader("🗓️ Twoje Raty")
    st.dataframe(df_rat, use_container_width=True)
    
    with st.expander("➕ Dodaj nową ratę"):
        with st.form("rata_add"):
            rn = st.text_input("Nazwa kredytu")
            rk = st.number_input("Rata miesięczna")
            rs = st.date_input("Data startu")
            re = st.date_input("Data końca")
            if st.form_submit_button("Aktywuj ratę"):
                sheet_rat.append_row([rn, rk, str(rs), str(re)])
                st.rerun()

    st.divider()
    if st.button("🔒 ZAMKNIJ MIESIĄC (Przelej bilans do oszczędności)"):
        new_sav = oszczednosci + bilans
        sheet_sav.update_acell('A2', str(new_sav))
        # Tu można dodać czyszczenie arkusza wydatków na nowy miesiąc
        st.balloons()
        st.rerun()
