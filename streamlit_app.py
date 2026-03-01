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
    def password_entered():
        if st.session_state["password"] == st.secrets["credentials"]["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.markdown("<h2 style='text-align: center; color: #b00000; font-family: \"Georgia\", serif;'>🪗 Witaj w Zagrodzie. Podaj hasło:</h2>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            st.text_input("Klucz do kłódki", type="password", on_change=password_entered, key="password")
            if "password_correct" in st.session_state and not st.session_state["password_correct"]:
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
        [data-testid="stMetricLabel"] p { color: #2c3e50 !important; font-family: 'Fondamento', cursive !important; font-size: 24px !important; text-transform: uppercase; }
        [data-testid="stMetricValue"] div { color: #b00000 !important; font-family: 'Almendra', serif !important; font-size: 44px !important; font-weight: bold !important; }
        h1, h2, h3 { color: #b00000 !important; font-family: 'Almendra', serif !important; text-align: center; border-bottom: 2px solid #b00000; padding-bottom: 10px; }
        .stButton>button { background: #2c3e50 !important; color: #f4ece1 !important; border-radius: 0px !important; border: 2px solid #b00000 !important; font-family: 'Fondamento', cursive !important; width: 100%; transition: 0.3s; height: 3.5em; }
        .stButton>button:hover { background: #b00000 !important; color: white !important; transform: translateY(-2px); }
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
        st.error(f"🚜 Błąd połączenia: {e}"); st.stop()

    # --- 5. LOGIKA CIĄGŁOŚCI (NAJWAŻNIEJSZA CZĘŚĆ) ---
    today = date.today()
    current_month_str = today.strftime("%Y-%m")
    start_sys = date(2026, 1, 1)
    
    # Obliczamy ile miesięcy system już działa
    num_m = (today.year - start_sys.year) * 12 + (today.month - start_sys.month) + 1
    
    # 1. WSZYSTKIE WPŁYWY (Tabela + 1600 zł za każdy miesiąc)
    total_in = df_inc['Kwota'].sum() + (num_m * 1600)
    
    # 2. WSZYSTKIE WYDATKI ZMIENNE
    total_out_var = df_exp['Kwota'].sum()
    
    # 3. WSZYSTKIE KOSZTY STAŁE (Miesięczna suma razy liczba miesięcy)
    total_fix = num_m * df_fix['Kwota'].sum()
    
    # 4. WSZYSTKIE RATY (Sumowane miesięcznie tylko jeśli rata była aktywna)
    total_rat = 0
    if not df_rat.empty:
        df_rat['Start'] = pd.to_datetime(df_rat['Start'])
        df_rat['Koniec'] = pd.to_datetime(df_rat['Koniec'])
        for m in pd.date_range(start="2026-01-01", periods=num_m, freq='MS'):
            mask = (df_rat['Start'] <= m) & (df_rat['Koniec'] >= m)
            total_rat += df_rat[mask]['Kwota'].sum()

    # 5. STAN SKRZYNI (Z arkusza)
    sav_val = float(str(df_sav.iloc[0,0]).replace(',', '.')) if not df_sav.empty else 0.0

    # 6. OSTATECZNY BILANS (KALETKA)
    # Formuła: Suma wpływów - wydatki - stałe - raty - to co w skrzyni
    balance = total_in - total_out_var - total_fix - total_rat - sav_val
    
    # Budżet dzienny do końca miesiąca
    days_in_m = calendar.monthrange(today.year, today.month)[1] - today.day + 1
    daily = balance / days_in_m if days_in_m > 0 else balance

    # --- 6. SIDEBAR ---
    with st.sidebar:
        st.markdown("<h2 style='border:none;'>🌾 SPICHLERZ</h2>", unsafe_allow_html=True)
        st.metric("W SKRZYNI (SEJF)", f"{sav_val:,.2f} PLN")
        
        st.divider()
        with st.expander("💰 RĘCZNA WPŁATA/WYPŁATA"):
            val_change = st.number_input("Kwota", min_value=0.0, step=50.0)
            c1, c2 = st.columns(2)
            if c1.button("DOPISZ"):
                sh.worksheet("Oszczednosci").update_acell('A2', str(sav_val + val_change))
                st.cache_data.clear(); st.rerun()
            if c2.button("WYJMIJ"):
                sh.worksheet("Oszczednosci").update_acell('A2', str(sav_val - val_change))
                st.cache_data.clear(); st.rerun()

        st.divider()
        st.subheader("🚜 ŻNIWA")
        if st.button("PRZELEJ NADWYŻKĘ DO SKRZYNI"):
            if balance > 0:
                sh.worksheet("Oszczednosci").update_acell('A2', str(sav_val + balance))
                st.snow(); st.success(f"Oszczędzono {balance:.2f} PLN"); time.sleep(1); st.cache_data.clear(); st.rerun()
            else:
                st.warning("Brak nadwyżki w kaletce!")

    # --- 7. DASHBOARD ---
    st.markdown("<h1>🎻 REJESTR GOSPODARSKI</h1>", unsafe_allow_html=True)
    
    col_m1, col_m2 = st.columns(2)
    col_m1.metric("📦 W KALETCE (DOSTĘPNE)", f"{balance:,.2f} PLN")
    col_m2.metric("🥖 NA DZIEŃ", f"{daily:,.2f} PLN")

    # --- 8. ZAKŁADKI ---
    t1, t2, t3, t4, t5 = st.tabs(["✍️ WPISY", "🏠 STAŁE & RATY", "📊 ANALIZA", "📝 LISTY", "🛶 PLANY"])

    with t1:
        ci, ce = st.columns(2)
        with ci:
            with st.form("form_inc", clear_on_submit=True):
                st.subheader("➕ Nowy Przybytek")
                t, k = st.text_input("Tytuł"), st.number_input("Kwota", step=10.0)
                if st.form_submit_button("DODAJ"):
                    sh.worksheet("Przychody").append_row([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), t, k])
                    st.cache_data.clear(); st.rerun()
        with ce:
            with st.form("form_exp", clear_on_submit=True):
                st.subheader("➖ Nowy Wydatek")
                t, k = st.text_input("Na co?"), st.number_input("Kwota", step=1.0)
                cat = st.selectbox("Kat.", ["Jedzenie", "Dom", "Transport", "Rozrywka", "Inne"])
                if st.form_submit_button("ZAPŁAĆ"):
                    sh.worksheet("Wydatki").append_row([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), t, k, cat, "Zmienny"])
                    st.cache_data.clear(); st.rerun()

        st.subheader("📖 Wydatki z tego miesiąca")
        df_m = df_exp[df_exp['Data i Godzina'].astype(str).str.contains(current_month_str, na=False)].copy()
        if not df_m.empty:
            df_m["USUŃ"] = False
            edited = st.data_editor(df_m, use_container_width=True, hide_index=True)
            if st.button("Zapisz zmiany w historii"):
                to_keep = edited[edited["USUŃ"] == False].drop(columns=["USUŃ"])
                others = df_exp[~df_exp['Data i Godzina'].astype(str).str.contains(current_month_str, na=False)]
                final = pd.concat([others, to_keep], ignore_index=True)
                ws = sh.worksheet("Wydatki")
                ws.clear()
                ws.append_row(["Data i Godzina", "Nazwa", "Kwota", "Kategoria", "Typ"])
                if not final.empty: ws.append_rows(final.values.tolist())
                st.cache_data.clear(); st.rerun()

    with t2:
        st.subheader("🏠 Opłaty Stałe")
        st.table(df_fix[["Nazwa", "Kwota"]])
        st.subheader("📜 Raty w tym miesiącu")
        df_rat_active = df_rat[df_rat['Koniec'] >= pd.Timestamp(today)]
        st.table(df_rat_active[["Rata", "Kwota", "Koniec"]])

    with t3:
        st.subheader("📊 Analiza Wydatków")
        df_pie = df_exp[df_exp['Data i Godzina'].astype(str).str.contains(current_month_str, na=False)]
        if not df_pie.empty:
            fig = px.pie(df_pie, values='Kwota', names='Kategoria', hole=0.4, color_discrete_sequence=px.colors.qualitative.Antique)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Brak danych do wykresu.")

    with t4:
        c_l1, c_l2 = st.columns(2)
        with c_l1:
            st.subheader("🛒 Zakupy")
            df_shp["KUPIONE"] = False
            ed_s = st.data_editor(df_shp, use_container_width=True, hide_index=True)
            if st.button("Wyczyść kupione"):
                res = ed_s[ed_s["KUPIONE"] == False].drop(columns=["KUPIONE"])
                ws = sh.worksheet("Zakupy")
                ws.clear(); ws.append_row(["Data i Godzina", "Produkt"])
                if not res.empty: ws.append_rows(res.values.tolist())
                st.cache_data.clear(); st.rerun()
        with c_l2:
            st.subheader("🔨 Zadania")
            df_tsk["OK"] = False
            ed_t = st.data_editor(df_tsk, use_container_width=True, hide_index=True)
            if st.button("Wyczyść zrobione"):
                res = ed_t[ed_t["OK"] == False].drop(columns=["OK"])
                ws = sh.worksheet("Zadania")
                ws.clear(); ws.append_row(["Data i Godzina", "Zadanie", "Termin", "Priorytet"])
                if not res.empty: ws.append_rows(res.values.tolist())
                st.cache_data.clear(); st.rerun()

    with t5:
        st.subheader("🛶 Plany Finansowe")
        st.dataframe(df_pla, use_container_width=True)
