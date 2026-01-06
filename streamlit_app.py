import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
from google.oauth2 import service_account
from datetime import datetime, date
import calendar

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Pro Budget Master 2026", layout="wide", page_icon="💰")

# --- STYLIZACJA CSS ---
st.markdown("""
    <style>
    .stMetric { background-color: #1a1c24; padding: 15px; border-radius: 10px; border: 1px solid #3e4452; }
    [data-testid="stForm"] { border: 1px solid #3e4452; border-radius: 10px; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNKCJE POMOCNICZE ---
def get_now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def get_sheet(sheet_name):
    try:
        # Wykorzystanie danych z pliku JSON przesłanego przez użytkownika
        creds_dict = st.secrets["gcp_service_account"]
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        return client.open("Budzet_Data").worksheet(sheet_name)
    except Exception as e:
        st.error(f"Błąd połączenia z arkuszem '{sheet_name}': {e}")
        return None

def calculate_800plus():
    today = date.today()
    # Daty urodzenia córek podane przez użytkownika
    dzieci = [date(2018, 8, 1), date(2022, 11, 1)]
    suma = 0
    for bday in dzieci:
        wiek = today.year - bday.year - ((today.month, today.day) < (bday.month, bday.day))
        if wiek < 18: suma += 800
    return suma

# --- POŁĄCZENIE Z DANYMI ---
s_inc = get_sheet("Przychody")
s_exp = get_sheet("Wydatki")
s_fix = get_sheet("Koszty_Stale")
s_rat = get_sheet("Raty")
s_sav = get_sheet("Oszczednosci")
s_shp = get_sheet("Zakupy")
s_tsk = get_sheet("Zadania")
s_pla = get_sheet("Planowanie")

# Pobieranie danych do DataFrame
df_inc = pd.DataFrame(s_inc.get_all_records()) if s_inc else pd.DataFrame()
df_exp = pd.DataFrame(s_exp.get_all_records()) if s_exp else pd.DataFrame()
df_fix = pd.DataFrame(s_fix.get_all_records()) if s_fix else pd.DataFrame()
df_rat = pd.DataFrame(s_rat.get_all_records()) if s_rat else pd.DataFrame()
df_shp = pd.DataFrame(s_shp.get_all_records()) if s_shp else pd.DataFrame()
df_tsk = pd.DataFrame(s_tsk.get_all_records()) if s_tsk else pd.DataFrame()
df_pla = pd.DataFrame(s_pla.get_all_records()) if s_pla else pd.DataFrame()

# --- LOGIKA FINANSOWA ---
today_dt = pd.to_datetime(date.today())
suma_rat = 0
if not df_rat.empty:
    df_rat['Start'] = pd.to_datetime(df_rat['Start'])
    df_rat['Koniec'] = pd.to_datetime(df_rat['Koniec'])
    aktywne = df_rat[(df_rat['Start'] <= today_dt) & (df_rat['Koniec'] >= today_dt)]
    suma_rat = aktywne['Kwota'].sum()

total_inc = (df_inc['Kwota'].sum() if not df_inc.empty else 0) + calculate_800plus()
total_exp = (df_exp['Kwota'].sum() if not df_exp.empty else 0) + (df_fix['Kwota'].sum() if not df_fix.empty else 0) + suma_rat
bilans = total_inc - total_exp
dni_do_konca = calendar.monthrange(date.today().year, date.today().month)[1] - date.today().day + 1
dzienny = bilans / dni_do_konca if dni_do_konca > 0 else bilans

# --- SIDEBAR (SKARBIEC & RATUNEK) ---
with st.sidebar:
    st.title("🏦 SKARBIEC")
    try:
        sav_val = float(str(s_sav.acell('A2').value).replace(',', '.'))
        last_trans = float(str(s_sav.acell('B2').value).replace(',', '.'))
    except:
        sav_val, last_trans = 0.0, 0.0

    st.metric("Oszczędności ogółem", f"{sav_val:,.2f} PLN")
    
    with st.expander("🚨 Ratunek / Pobierz"):
        kwota_r = st.number_input("Ile pobrać?", min_value=0.0, max_value=sav_val, step=100.0)
        if st.button("POBIERZ ZE SKARBCA"):
            s_sav.update_acell('A2', str(sav_val - kwota_r))
            s_inc.append_row([get_now(), "RATUNEK ZE SKARBCA", kwota_r])
            st.rerun()

    if st.button("⏪ Cofnij zamknięcie"):
        s_sav.update_acell('A2', str(sav_val - last_trans))
        s_sav.update_acell('B2', "0")
        st.rerun()

# --- GŁÓWNY INTERFEJS ---
tabs = st.tabs(["📊 ANALIZA", "💸 KSIĘGOWOŚĆ", "📅 PLANOWANIE", "🏠 STAŁE & RATY", "🛒 ZAKUPY/ZADANIA"])

with tabs[0]:
    c1, c2, c3 = st.columns(3)
    c1.metric("Dostępne środki", f"{bilans:,.2f} PLN")
    c2.metric("Na każdy dzień", f"{dzienny:,.2f} PLN", delta=f"{dni_do_konca} dni")
    c3.metric("800+", f"{calculate_800plus()} PLN")
    
    st.divider()
    col_l, col_r = st.columns([2, 1])
    with col_l:
        if not df_exp.empty:
            fig = px.pie(df_exp, values='Kwota', names='Kategoria', hole=.4, title="Wydatki wg kategorii")
            st.plotly_chart(fig, use_container_width=True)
    with col_r:
        if st.button("🔒 ZAMKNIJ MIESIĄC", use_container_width=True):
            s_sav.update_acell('B2', str(bilans))
            s_sav.update_acell('A2', str(sav_val + bilans))
            st.balloons()
            st.rerun()

with tabs[1]:
    st.subheader("Wprowadzanie i Edycja")
    with st.expander("➕ Dodaj nowy wpis"):
        ci1, ci2 = st.columns(2)
        with ci1:
            with st.form("f_inc"):
                st.write("Wpływ")
                ni, ki = st.text_input("Nazwa"), st.number_input("Kwota")
                if st.form_submit_button("Dodaj"):
                    s_inc.append_row([get_now(), ni, ki]); st.rerun()
        with ci2:
            with st.form("f_exp"):
                st.write("Wydatek")
                ne, ke = st.text_input("Nazwa"), st.number_input("Kwota")
                kat = st.selectbox("Kat.", ["Jedzenie", "Dom", "Transport", "Rozrywka", "Inne"])
                if st.form_submit_button("Dodaj"):
                    s_exp.append_row([get_now(), ne, ke, kat, "Zmienny"]); st.rerun()

    st.write("📝 **Historia wydatków (Edytuj bezpośrednio)**")
    df_exp["USUŃ"] = False
    edit_exp = st.data_editor(df_exp, num_rows="dynamic", use_container_width=True)
    if st.button("Zapisz zmiany w wydatkach"):
        cleaned = edit_exp[edit_exp["USUŃ"] == False].drop(columns=["USUŃ"])
        s_exp.clear(); s_exp.append_row(["Data i Godzina", "Nazwa", "Kwota", "Kategoria", "Typ"])
        if not cleaned.empty: s_exp.append_rows(cleaned.values.tolist())
        st.rerun()

with tabs[2]:
    st.subheader("🗓️ Planowane wydatki w przyszłych miesiącach")
    with st.form("f_pla"):
        cp1, cp2, cp3 = st.columns(3)
        pn = cp1.text_input("Nazwa wydatku")
        pk = cp2.number_input("Szacowana kwota")
        pm = cp3.selectbox("Miesiąc", ["Styczeń", "Luty", "Marzec", "Kwiecień", "Maj", "Czerwiec", "Lipiec", "Sierpień", "Wrzesień", "Październik", "Listopad", "Grudzień"])
        if st.form_submit_button("Zaplanuj"):
            s_pla.append_row([get_now(), pn, pk, pm]); st.rerun()
    
    st.divider()
    df_pla["USUŃ"] = False
    edit_pla = st.data_editor(df_pla, num_rows="dynamic", use_container_width=True)
    if st.button("Zapisz zmiany w planach"):
        cleaned_pla = edit_pla[edit_pla["USUŃ"] == False].drop(columns=["USUŃ"])
        s_pla.clear(); s_pla.append_row(["Data i Godzina", "Nazwa", "Kwota", "Miesiąc/Rok"])
        if not cleaned_pla.empty: s_pla.append_rows(cleaned_pla.values.tolist())
        st.rerun()

with tabs[3]:
    st.subheader("🏠 Koszty Stałe i Raty")
    col_f, col_r = st.columns(2)
    with col_f:
        with st.form("f_fix"):
            nf, kf = st.text_input("Koszt stały"), st.number_input("Kwota")
            if st.form_submit_button("Dodaj"):
                s_fix.append_row([get_now(), nf, kf]); st.rerun()
    with col_r:
        with st.form("f_rat"):
            nr, kr = st.text_input("Rata"), st.number_input("Kwota miesięczna")
            ds, de = st.date_input("Start"), st.date_input("Koniec")
            if st.form_submit_button("Dodaj"):
                s_rat.append_row([nr, kr, str(ds), str(de)]); st.rerun()

    st.divider()
    edit_rat = st.data_editor(df_rat, num_rows="dynamic", use_container_width=True)
    if st.button("Zapisz zmiany w ratach"):
        s_rat.clear(); s_rat.append_row(["Nazwa", "Kwota", "Start", "Koniec"])
        if not edit_rat.empty: s_rat.append_rows(edit_rat.values.tolist())
        st.rerun()

with tabs[4]:
    st.subheader("🛒 Zakupy i ✅ Zadania")
    c_s, c_t = st.columns(2)
    with c_s:
        with st.form("f_shp"):
            pr = st.text_input("Dodaj produkt")
            if st.form_submit_button("Dodaj do listy"):
                s_shp.append_row([get_now(), pr]); st.rerun()
        df_shp["KUPIŁEM"] = False
        e_shp = st.data_editor(df_shp, use_container_width=True)
        if st.button("Usuń kupione"):
            rem = e_shp[e_shp["KUPIŁEM"] == False].drop(columns=["KUPIŁEM"])
            s_shp.clear(); s_shp.append_row(["Data i Godzina", "Produkt"])
            if not rem.empty: s_shp.append_rows(rem.values.tolist()); st.rerun()
    with c_t:
        with st.form("f_tsk"):
            zt, zd = st.text_input("Zadanie"), st.date_input("Termin")
            if st.form_submit_button("Zapisz zadanie"):
                s_tsk.append_row([get_now(), zt, str(zd), "Wysoki"]); st.rerun()
        df_tsk["GOTOWE"] = False
        e_tsk = st.data_editor(df_tsk, use_container_width=True)
        if st.button("Usuń zrobione"):
            rem_t = e_tsk[e_tsk["GOTOWE"] == False].drop(columns=["GOTOWE"])
            s_tsk.clear(); s_tsk.append_row(["Data i Godzina", "Zadanie", "Termin", "Priorytet"])
            if not rem_t.empty: s_tsk.append_rows(rem_t.values.tolist()); st.rerun()
