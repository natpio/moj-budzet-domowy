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
        [data-testid="stExpander"] {
            background-color: #ffffff !important;
            border: 1px solid #8d6e63 !important;
            border-radius: 10px !important;
            margin-bottom: 10px !important;
        }
        </style>
        """, unsafe_allow_html=True)

    # --- POŁĄCZENIE I OPTYMALIZACJA API ---
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
        data = {}
        for name in sheets:
            data[name] = pd.DataFrame(sh.worksheet(name).get_all_records())
            time.sleep(0.3)
        return data

    def get_now(): return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        all_data = load_all_data()
        df_inc = all_data["Przychody"]
        df_exp = all_data["Wydatki"]
        df_fix = all_data["Koszty_Stale"]
        df_rat = all_data["Raty"]
        df_sav = all_data["Oszczednosci"]
        df_shp = all_data["Zakupy"]
        df_tsk = all_data["Zadania"]
        df_pla = all_data["Planowanie"]
    except:
        st.error("🤠 Serwer zajęty, spróbuj odświeżyć za chwilę.")
        st.stop()

    # --- OBLICZENIA ---
    today = date.today()
    dni_m = calendar.monthrange(today.year, today.month)[1] - today.day + 1
    p800 = 1600
    
    # Raty aktywne
    df_rat_active = pd.DataFrame()
    suma_rat = 0
    if not df_rat.empty:
        df_rat['Start'] = pd.to_datetime(df_rat['Start'])
        df_rat['Koniec'] = pd.to_datetime(df_rat['Koniec'])
        mask = (df_rat['Start'] <= pd.Timestamp(today)) & (df_rat['Koniec'] >= pd.Timestamp(today))
        df_rat_active = df_rat[mask].copy()
        suma_rat = df_rat_active['Kwota'].sum()

    inc_total = (df_inc['Kwota'].sum() if not df_inc.empty else 0) + p800
    exp_total = (df_exp['Kwota'].sum() if not df_exp.empty else 0) + (df_fix['Kwota'].sum() if not df_fix.empty else 0) + suma_rat
    balance = inc_total - exp_total
    daily = balance / dni_m if dni_m > 0 else balance

    # --- SIDEBAR ---
    with st.sidebar:
        st.markdown("<h1 style='text-align:center;'>🤠 SEJF</h1>", unsafe_allow_html=True)
        client = get_client()
        ws_sav = client.open("Budzet_Data").worksheet("Oszczednosci")
        sav_val = float(str(ws_sav.acell('A2').value).replace(',', '.'))
        st.metric("ZŁOTO W SEJFIE", f"{sav_val:,.2f} PLN")
        with st.expander("💰 WYPŁATA"):
            amt = st.number_input("Ile dukatów?", min_value=0.0, key="side_w")
            if st.button("POBIERZ"):
                ws_sav.update_acell('A2', str(sav_val - amt))
                client.open("Budzet_Data").worksheet("Przychody").append_row([get_now(), "WYPŁATA ZE SKARBCA", amt])
                st.cache_data.clear(); st.rerun()

    # --- NAGŁÓWEK I METRYKI ---
    st.markdown("<h1 style='text-align: center;'>📜 KSIĘGA RACHUNKOWA RANCZA</h1>", unsafe_allow_html=True)
    
    m1, m2 = st.columns(2)
    m1.metric("💰 PORTFEL", f"{balance:,.2f} PLN")
    m2.metric("☀️ NA DZIEŃ", f"{daily:,.2f} PLN")

    # --- DYNAMICZNA HISTORIA (ROZWIJANA) ---
    c_inc, c_exp = st.columns(2)
    
    with c_inc:
        st.metric("📈 DOCHODY", f"{inc_total:,.2f} PLN")
        with st.expander("🔍 Zobacz listę wpływów"):
            hist_inc = df_inc.copy()
            if p800 > 0:
                hist_inc = pd.concat([hist_inc, pd.DataFrame([{"Nazwa": "Program 800+", "Kwota": p800}])], ignore_index=True)
            st.table(hist_inc[["Nazwa", "Kwota"]] if not hist_inc.empty else pd.DataFrame(columns=["Brak"]))

    with c_exp:
        st.metric("📉 WYDATKI", f"{exp_total:,.2f} PLN")
        with st.expander("🔍 Zobacz pełną listę kosztów"):
            # Łączenie wszystkich wydatków w jeden widok
            zmienne = df_exp[["Nazwa", "Kwota"]].copy()
            stale = df_fix[["Nazwa", "Kwota"]].copy()
            raty = df_rat_active[["Rata", "Kwota"]].rename(columns={"Rata": "Nazwa"}).copy()
            
            pelna_lista = pd.concat([zmienne, stale, raty], ignore_index=True)
            st.table(pelna_lista if not pelna_lista.empty else pd.DataFrame(columns=["Brak"]))

    # --- ZAKŁADKI OPERACYJNE ---
    tabs = st.tabs(["💸 Nowe Wpisy", "🏠 Stałe & Raty", "📅 Plany", "🛒 Listy"])

    with tabs[0]:
        col_i, col_e = st.columns(2)
        with col_i:
            with st.form("f_inc"):
                st.subheader("➕ Przychód")
                ni, ki = st.text_input("Skąd?"), st.number_input("Ile?")
                if st.form_submit_button("DODAJ"):
                    client.open("Budzet_Data").worksheet("Przychody").append_row([get_now(), ni, ki])
                    st.cache_data.clear(); st.rerun()
        with col_e:
            with st.form("f_exp"):
                st.subheader("➖ Wydatek")
                ne, ke = st.text_input("Na co?"), st.number_input("Ile?")
                ka = st.selectbox("Kategoria", ["Jedzenie", "Dom", "Transport", "Rozrywka", "Inne"])
                if st.form_submit_button("DODAJ"):
                    client.open("Budzet_Data").worksheet("Wydatki").append_row([get_now(), ne, ke, ka, "Zmienny"])
                    st.cache_data.clear(); st.rerun()
        
        st.divider()
        st.subheader("🖋️ Zarządzaj historią (Usuwanie)")
        df_exp["USUŃ"] = False
        e_exp = st.data_editor(df_exp, num_rows="dynamic", use_container_width=True)
        if st.button("Zapisz zmiany w bazie"):
            cl = e_exp[e_exp["USUŃ"] == False].drop(columns=["USUŃ"])
            ws = client.open("Budzet_Data").worksheet("Wydatki")
            ws.clear(); ws.append_row(["Data i Godzina", "Nazwa", "Kwota", "Kategoria", "Typ"])
            if not cl.empty: ws.append_rows(cl.values.tolist())
            st.cache_data.clear(); st.rerun()

    with tabs[1]:
        cf, cr = st.columns(2)
        with cf:
            with st.form("f_fix"):
                st.subheader("🏠 Koszty Stałe")
                nf, kf = st.text_input("Nazwa"), st.number_input("Kwota", key="fk")
                if st.form_submit_button("DODAJ"):
                    client.open("Budzet_Data").worksheet("Koszty_Stale").append_row([get_now(), nf, kf])
                    st.cache_data.clear(); st.rerun()
            # Tutaj możesz dodać edytor stałych jak wyżej
        with cr:
            with st.form("f_rat"):
                st.subheader("🗓️ Nowa Rata")
                nr, kr = st.text_input("Rata"), st.number_input("Kwota", key="rk")
                ds, de = st.date_input("Od"), st.date_input("Do")
                if st.form_submit_button("DODAJ"):
                    client.open("Budzet_Data").worksheet("Raty").append_row([nr, kr, str(ds), str(de)])
                    st.cache_data.clear(); st.rerun()

    # Pozostałe zakładki (Plany i Listy) pozostają bez zmian – działają na tej samej zasadzie.
    # Wklej tam kod z poprzedniej wersji, jeśli chcesz mieć pełny edytor.
