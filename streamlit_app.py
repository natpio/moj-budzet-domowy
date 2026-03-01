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

    # --- 5. LOGIKA CIĄGŁOŚCI I OBLICZENIA ---
    today = date.today()
    current_month_str = today.strftime("%Y-%m")
    num_m = (today.year - 2026) * 12 + today.month 

    # Konwersja kwot na liczby
    df_inc['Kwota'] = pd.to_numeric(df_inc['Kwota'], errors='coerce').fillna(0)
    df_exp['Kwota'] = pd.to_numeric(df_exp['Kwota'], errors='coerce').fillna(0)
    df_fix['Kwota'] = pd.to_numeric(df_fix['Kwota'], errors='coerce').fillna(0)
    df_rat['Kwota'] = pd.to_numeric(df_rat['Kwota'], errors='coerce').fillna(0)

    # Sumy
    s_inc = df_inc['Kwota'].sum()
    s_800 = num_m * 1600
    s_exp = df_exp['Kwota'].sum()
    s_fix = num_m * df_fix['Kwota'].sum()
    s_sav = float(str(df_sav.iloc[0,0]).replace(',', '.')) if not df_sav.empty else 0.0

    # Raty
    total_raty = 0
    df_rat['Start'] = pd.to_datetime(df_rat['Start'])
    df_rat['Koniec'] = pd.to_datetime(df_rat['Koniec'])
    for m in pd.date_range(start="2026-01-01", periods=num_m, freq='MS'):
        mask = (df_rat['Start'] <= m) & (df_rat['Koniec'] >= m)
        total_raty += df_rat[mask]['Kwota'].sum()

    # WYNIK (KALETKA)
    balance = s_inc + s_800 - s_exp - s_fix - total_raty - s_sav
    days_left = calendar.monthrange(today.year, today.month)[1] - today.day + 1
    daily = balance / days_left if days_left > 0 else balance

    # --- 6. SIDEBAR ---
    with st.sidebar:
        st.markdown("<h2 style='border:none;'>🌾 SPICHLERZ</h2>", unsafe_allow_html=True)
        st.metric("W SKRZYNI (SEJF)", f"{s_sav:,.2f} PLN")
        st.divider()
        if st.button("🚜 PRZELEJ NADWYŻKĘ (ŻNIWA)"):
            if balance > 0:
                sh.worksheet("Oszczednosci").update_acell('A2', str(s_sav + balance))
                st.snow(); st.cache_data.clear(); time.sleep(1); st.rerun()

    # --- 7. DIAGNOSTYKA (ŚLEDZTWO) ---
    st.title("🚜 DIAGNOSTYKA SYSTEMU")
    with st.expander("🔍 ŚLEDZTWO: DLACZEGO JEST MINUS?", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Przychody z wypłat:** {s_inc:,.2f} PLN")
            st.write(f"**Suma 800+ (3 msc):** {s_800:,.2f} PLN")
            st.write(f"**Wszystkie wydatki (Paragony):** {s_exp:,.2f} PLN")
        with col2:
            st.write(f"**Wszystkie rachunki (3 msc):** {s_fix:,.2f} PLN")
            st.write(f"**Wszystkie raty (3 msc):** {total_raty:,.2f} PLN")
            st.write(f"### AKTUALNY BILANS: {balance:,.2f} PLN")
        
        st.divider()
        st.subheader("🕵️‍♂️ 10 NAJWIĘKSZYCH WYDATKÓW W HISTORII")
        top_10 = df_exp.nlargest(10, 'Kwota')[['Data i Godzina', 'Nazwa', 'Kwota', 'Kategoria']]
        st.table(top_10)

    # --- 8. DASHBOARD GŁÓWNY ---
    st.markdown("<h1>🎻 REJESTR GOSPODARSKI</h1>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    c1.metric("📦 W KALETCE (NA DZIŚ)", f"{balance:,.2f} PLN")
    c2.metric("🥖 NA DZIEŃ", f"{daily:,.2f} PLN")

    # --- 9. ZAKŁADKI ---
    t1, t2, t3, t4 = st.tabs(["✍️ WPISY", "🏠 STAŁE", "📊 ANALIZA", "📝 LISTY"])

    with t1:
        col_i, col_e = st.columns(2)
        with col_i:
            with st.form("add_inc", clear_on_submit=True):
                st.subheader("➕ Przybytek")
                t_i = st.text_input("Tytuł")
                v_i = st.number_input("Kwota", step=10.0)
                if st.form_submit_button("DODAJ"):
                    sh.worksheet("Przychody").append_row([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), t_i, v_i])
                    st.cache_data.clear(); st.rerun()
        with col_e:
            with st.form("add_exp", clear_on_submit=True):
                st.subheader("➖ Wydatek")
                t_e = st.text_input("Na co?")
                v_e = st.number_input("Kwota", step=1.0)
                k_e = st.selectbox("Kat.", ["Jedzenie", "Dom", "Transport", "Rozrywka", "Inne"])
                if st.form_submit_button("DODAJ"):
                    sh.worksheet("Wydatki").append_row([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), t_e, v_e, k_e, "Zmienny"])
                    st.cache_data.clear(); st.rerun()

        st.subheader("📖 Edytor Wydatków (Marzec)")
        df_m = df_exp[df_exp['Data i Godzina'].astype(str).str.contains(current_month_str, na=False)].copy()
        if not df_m.empty:
            df_m["USUŃ"] = False
            ed = st.data_editor(df_m, use_container_width=True, hide_index=True)
            if st.button("Zatwierdź zmiany"):
                to_keep = ed[ed["USUŃ"] == False].drop(columns=["USUŃ"])
                others = df_exp[~df_exp['Data i Godzina'].astype(str).str.contains(current_month_str, na=False)]
                final = pd.concat([others, to_keep], ignore_index=True)
                ws = sh.worksheet("Wydatki")
                ws.clear(); ws.append_row(["Data i Godzina", "Nazwa", "Kwota", "Kategoria", "Typ"])
                if not final.empty: ws.append_rows(final.values.tolist())
                st.cache_data.clear(); st.rerun()

    with t2:
        st.subheader("🏠 Stałe koszty")
        st.table(df_fix)
        st.subheader("📜 Raty")
        st.table(df_rat[df_rat['Koniec'] >= pd.Timestamp(today)])

    with t3:
        if not df_m.empty:
            fig = px.pie(df_m, values='Kwota', names='Kategoria', hole=0.4)
            st.plotly_chart(fig, use_container_width=True)

    with t4:
        st.subheader("🛒 Zakupy / Zadania")
        st.write("Zakupy:", df_shp["Produkt"].tolist())
        st.write("Zadania:", df_tsk["Zadanie"].tolist())
