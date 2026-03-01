import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
from google.oauth2 import service_account
from datetime import datetime, date
import calendar
import time

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Gospodarstwo Finansowe 2026", layout="wide", page_icon="🌾")

# --- FUNKCJA LOGOWANIA ---
def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["credentials"]["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.markdown("<h2 style='text-align: center; color: #b00000; font-family: \"Georgia\", serif;'>🪗 Witaj w Zagrodzie. Podaj hasło do spichlerza:</h2>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            st.text_input("Klucz do kłódki", type="password", on_change=password_entered, key="password")
            if "password_correct" in st.session_state and not st.session_state["password_correct"]:
                st.error("❌ Zły klucz! Psy szczekają, obcy nie wejdzie.")
        return False
    return True

if check_password():
    # --- STYLIZACJA FOLKLOROWA ---
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Fondamento&family=Almendra&display=swap');
        .stApp { background-color: #f4ece1; background-image: url("https://www.transparenttextures.com/patterns/natural-paper.png"); }
        [data-testid="stMetric"] { background: #ffffff !important; border: 4px double #b00000 !important; border-radius: 10px !important; box-shadow: 5px 5px 0px 0px #2c3e50 !important; padding: 15px !important; }
        [data-testid="stMetricLabel"] p { color: #2c3e50 !important; font-family: 'Fondamento', cursive !important; font-size: 24px !important; text-transform: uppercase; }
        [data-testid="stMetricValue"] div { color: #b00000 !important; font-family: 'Almendra', serif !important; font-size: 44px !important; font-weight: bold !important; }
        h1, h2 { color: #b00000 !important; font-family: 'Almendra', serif !important; font-size: 50px !important; text-align: center; border-bottom: 2px solid #b00000; margin-bottom: 30px !important; }
        .stButton>button { background: #2c3e50 !important; color: #f4ece1 !important; border-radius: 0px !important; border: 2px solid #b00000 !important; font-family: 'Fondamento', cursive !important; width: 100%; transition: 0.3s; }
        .stButton>button:hover { background: #b00000 !important; color: white !important; transform: translateY(-2px); }
        [data-testid="stSidebar"] { background: #e6d5bc !important; border-right: 3px solid #b00000 !important; }
        [data-testid="stExpander"] { background: white !important; border: 1px solid #2c3e50 !important; }
        header {background: transparent !important;}
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
        data = {name: pd.DataFrame(sh.worksheet(name).get_all_records()) for name in names}
        return data

    def get_now(): return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Pobranie danych
    try:
        all_d = load_all_data()
        df_inc, df_exp, df_fix, df_rat, df_sav, df_shp, df_tsk, df_pla = [all_d[n] for n in ["Przychody", "Wydatki", "Koszty_Stale", "Raty", "Oszczednosci", "Zakupy", "Zadania", "Planowanie"]]
        sh = get_client().open("Budzet_Data")
    except Exception as e:
        st.error(f"🚜 Traktor utknął: {e}"); st.stop()

    # --- LOGIKA CIĄGŁOŚCI ---
    today = date.today()
    current_month_str = today.strftime("%Y-%m")
    start_date = date(2026, 1, 1)
    num_months = (today.year - start_date.year) * 12 + (today.month - start_date.month) + 1
    
    # Sumowanie wszystkiego od początku (Jan 2026)
    total_inc = df_inc['Kwota'].sum() + (num_months * 1600)
    total_exp_var = df_exp['Kwota'].sum()
    total_fix = num_months * df_fix['Kwota'].sum()
    
    total_raty = 0
    if not df_rat.empty:
        df_rat['Start'] = pd.to_datetime(df_rat['Start'])
        df_rat['Koniec'] = pd.to_datetime(df_rat['Koniec'])
        month_range = pd.date_range(start="2026-01-01", periods=num_months, freq='MS')
        for m in month_range:
            mask = (df_rat['Start'] <= m) & (df_rat['Koniec'] >= m)
            total_raty += df_rat[mask]['Kwota'].sum()

    # Stan spichlerza
    sav_val = float(str(df_sav.iloc[0,0]).replace(',', '.')) if not df_sav.empty else 0.0

    # KLUCZOWY BILANS (to co zostało w kaletce)
    balance = total_inc - total_exp_var - total_fix - total_raty - sav_val
    
    dni_m = calendar.monthrange(today.year, today.month)[1] - today.day + 1
    daily = balance / dni_m if dni_m > 0 else balance

    # --- SIDEBAR ---
    with st.sidebar:
        st.markdown("<h1 style='font-size: 25px;'>🌾 SPICHLERZ</h1>", unsafe_allow_html=True)
        st.metric("ZASOBY W SKRZYNI", f"{sav_val:,.2f} PLN")
        
        st.divider()
        with st.expander("💰 ZARZĄDZAJ"):
            amt_s = st.number_input("Kwota", min_value=0.0, step=50.0)
            c1, c2 = st.columns(2)
            if c1.button("WPŁAĆ"):
                sh.worksheet("Oszczednosci").update_acell('A2', str(sav_val + amt_s))
                st.cache_data.clear(); st.rerun()
            if c2.button("WYJMIJ"):
                sh.worksheet("Oszczednosci").update_acell('A2', str(sav_val - amt_s))
                st.cache_data.clear(); st.rerun()

        if st.button("🚜 ZAMKNIJ ŻNIWA"):
            if balance > 0:
                sh.worksheet("Oszczednosci").update_acell('A2', str(sav_val + balance))
                st.snow(); st.success(f"Schowano {balance:.2f} PLN"); time.sleep(1); st.cache_data.clear(); st.rerun()

    # --- DASHBOARD ---
    st.markdown("<h1>🎻 REJESTR GOSPODARSKI</h1>", unsafe_allow_html=True)
    m1, m2 = st.columns(2)
    m1.metric("📦 W KALETCE", f"{balance:,.2f} PLN")
    m2.metric("🥖 NA DZIEŃ", f"{daily:,.2f} PLN")

    # --- TABS ---
    tabs = st.tabs(["✍️ Zapisy", "🏠 Stałe & Raty", "🛶 Plany", "📝 Listy"])

    with tabs[0]:
        ci, ce = st.columns(2)
        with ci:
            with st.form("f_inc", clear_on_submit=True):
                st.subheader("➕ Przybytek")
                ni, ki = st.text_input("Tytuł"), st.number_input("Kwota", step=10.0)
                if st.form_submit_button("DODAJ"):
                    sh.worksheet("Przychody").append_row([get_now(), ni, ki])
                    st.cache_data.clear(); st.rerun()
        with ce:
            with st.form("f_exp", clear_on_submit=True):
                st.subheader("➖ Wydatek")
                ne, ke = st.text_input("Na co?"), st.number_input("Kwota", step=1.0)
                ka = st.selectbox("Kat.", ["Jedzenie", "Dom", "Transport", "Rozrywka", "Inne"])
                if st.form_submit_button("ZAPŁAĆ"):
                    sh.worksheet("Wydatki").append_row([get_now(), ne, ke, ka, "Zmienny"])
                    st.cache_data.clear(); st.rerun()
        
        st.subheader("📖 Historia Wydatków (Bieżący Miesiąc)")
        df_exp_m = df_exp[df_exp['Data i Godzina'].astype(str).str.contains(current_month_str, na=False)].copy()
        if not df_exp_m.empty:
            df_exp_m["USUŃ"] = False
            ed_e = st.data_editor(df_exp_m, use_container_width=True, key="ed_e", hide_index=True)
            if st.button("Uaktualnij wydatki"):
                to_keep = ed_e[ed_e["USUŃ"] == False].drop(columns=["USUŃ"])
                other_months = df_exp[~df_exp['Data i Godzina'].astype(str).str.contains(current_month_str, na=False)]
                final_df = pd.concat([other_months, to_keep], ignore_index=True)
                ws = sh.worksheet("Wydatki")
                ws.clear(); ws.append_row(["Data i Godzina", "Nazwa", "Kwota", "Kategoria", "Typ"])
                if not final_df.empty: ws.append_rows(final_df.values.tolist())
                st.cache_data.clear(); st.rerun()

    with tabs[1]:
        c_fix, c_rat = st.columns(2)
        with c_fix:
            st.subheader("🏠 Opłaty Stałe")
            df_fix["USUŃ"] = False
            ed_f = st.data_editor(df_fix, use_container_width=True, hide_index=True)
            if st.button("Zapisz opłaty"):
                new_f = ed_f[ed_f["USUŃ"] == False].drop(columns=["USUŃ"])
                ws_f = sh.worksheet("Koszty_Stale")
                ws_f.clear(); ws_f.append_row(["Data i Godzina", "Nazwa", "Kwota"])
                if not new_f.empty: ws_f.append_rows(new_f.values.tolist())
                st.cache_data.clear(); st.rerun()
        with c_rat:
            st.subheader("📜 Aktywne Raty")
            st.table(df_rat[df_rat['Koniec'] >= pd.Timestamp(today)][["Rata", "Kwota", "Koniec"]])

    with tabs[2]:
        st.subheader("🛶 Planowanie")
        with st.form("f_pla"):
            p1, p2, p3 = st.columns(3)
            pn = p1.text_input("Cel")
            pk = p2.number_input("Kwota")
            pm = p3.selectbox("Miesiąc", ["Styczeń", "Luty", "Marzec", "Kwiecień", "Maj", "Czerwiec", "Lipiec", "Sierpień", "Wrzesień", "Październik", "Listopad", "Grudzień"])
            if st.form_submit_button("Dodaj do planów"):
                sh.worksheet("Planowanie").append_row([get_now(), pn, pk, pm])
                st.cache_data.clear(); st.rerun()
        st.dataframe(df_pla, use_container_width=True)

    with tabs[3]:
        l1, l2 = st.columns(2)
        with l1:
            st.subheader("🛒 Targ")
            df_shp["KUPIONE"] = False
            ed_s = st.data_editor(df_shp, use_container_width=True, hide_index=True)
            if st.button("Wyczyść koszyk"):
                new_s = ed_s[ed_s["KUPIONE"] == False].drop(columns=["KUPIONE"])
                ws_s = sh.worksheet("Zakupy")
                ws_s.clear(); ws_s.append_row(["Data i Godzina", "Produkt"])
                if not new_s.empty: ws_s.append_rows(new_s.values.tolist())
                st.cache_data.clear(); st.rerun()
        with l2:
            st.subheader("🔨 Robota")
            df_tsk["ZROBIONE"] = False
            ed_t = st.data_editor(df_tsk, use_container_width=True, hide_index=True)
            if st.button("Odlicz zadania"):
                new_t = ed_t[ed_t["ZROBIONE"] == False].drop(columns=["ZROBIONE"])
                ws_t = sh.worksheet("Zadania")
                ws_t.clear(); ws_t.append_row(["Data i Godzina", "Zadanie", "Termin", "Priorytet"])
                if not new_t.empty: ws_t.append_rows(new_t.values.tolist())
                st.cache_data.clear(); st.rerun()
