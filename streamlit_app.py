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

# --- 2. FUNKCJA LOGOWANIA ---
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
    # --- 3. STYLIZACJA FOLKLOROWA (CSS) ---
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Fondamento&family=Almendra&display=swap');
        .stApp { background-color: #f4ece1; background-image: url("https://www.transparenttextures.com/patterns/natural-paper.png"); }
        [data-testid="stMetric"] { background: #ffffff !important; border: 4px double #b00000 !important; border-radius: 10px !important; box-shadow: 5px 5px 0px 0px #2c3e50 !important; padding: 15px !important; }
        [data-testid="stMetricLabel"] p { color: #2c3e50 !important; font-family: 'Fondamento', cursive !important; font-size: 24px !important; text-transform: uppercase; }
        [data-testid="stMetricValue"] div { color: #b00000 !important; font-family: 'Almendra', serif !important; font-size: 44px !important; font-weight: bold !important; }
        h1, h2, h3 { color: #b00000 !important; font-family: 'Almendra', serif !important; text-align: center; }
        h1 { font-size: 50px !important; border-bottom: 2px solid #b00000; margin-bottom: 30px !important; }
        .stButton>button { background: #2c3e50 !important; color: #f4ece1 !important; border-radius: 0px !important; border: 2px solid #b00000 !important; font-family: 'Fondamento', cursive !important; width: 100%; transition: 0.3s; height: 3em; }
        .stButton>button:hover { background: #b00000 !important; color: white !important; transform: translateY(-2px); }
        [data-testid="stSidebar"] { background: #e6d5bc !important; border-right: 3px solid #b00000 !important; }
        .stTabs [data-baseweb="tab-list"] { gap: 10px; }
        .stTabs [data-baseweb="tab"] { background-color: #e6d5bc; border: 1px solid #b00000; padding: 10px 20px; font-family: 'Fondamento'; }
        .stTabs [aria-selected="true"] { background-color: #b00000 !important; color: white !important; }
        </style>
        """, unsafe_allow_html=True)

    # --- 4. POŁĄCZENIE Z GOOGLE SHEETS ---
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

    def get_now(): return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Wczytanie danych do zmiennych
    try:
        data = load_all_data()
        df_inc, df_exp, df_fix, df_rat, df_sav, df_shp, df_tsk, df_pla = [data[n] for n in ["Przychody", "Wydatki", "Koszty_Stale", "Raty", "Oszczednosci", "Zakupy", "Zadania", "Planowanie"]]
        sh = get_client().open("Budzet_Data")
    except Exception as e:
        st.error(f"🚜 Awaria traktora: {e}"); st.stop()

    # --- 5. LOGIKA CIĄGŁOŚCI (BILANS PRZECHODNI) ---
    today = date.today()
    current_month_str = today.strftime("%Y-%m")
    start_date = date(2026, 1, 1) # Początek Twojego systemu
    num_months = (today.year - start_date.year) * 12 + (today.month - start_date.month) + 1
    
    # Obliczenie wpływów (Tabela + 800+ za każdy miesiąc)
    total_income_ever = df_inc['Kwota'].sum() + (num_months * 1600)
    
    # Obliczenie wydatków zmiennych (Wszystko z tabeli)
    total_expenses_ever = df_exp['Kwota'].sum()
    
    # Obliczenie kosztów stałych (Miesięczna suma * liczba miesięcy)
    total_fixed_ever = num_months * df_fix['Kwota'].sum()
    
    # Obliczenie rat (Dynamicznie: tylko za miesiące, w których rata była aktywna)
    total_raty_ever = 0
    if not df_rat.empty:
        df_rat['Start'] = pd.to_datetime(df_rat['Start'])
        df_rat['Koniec'] = pd.to_datetime(df_rat['Koniec'])
        month_range = pd.date_range(start="2026-01-01", periods=num_months, freq='MS')
        for m in month_range:
            mask = (df_rat['Start'] <= m) & (df_rat['Koniec'] >= m)
            total_raty_ever += df_rat[mask]['Kwota'].sum()

    # Stan Sejfu (Spichlerza)
    sav_val = float(str(df_sav.iloc[0,0]).replace(',', '.')) if not df_sav.empty else 0.0

    # OSTATECZNY BILANS W KALETCE
    # Formuła: Suma wszystkiego co wpłynęło - Wszystko co wydane - To co już schowane w Sejfie
    balance = total_income_ever - total_expenses_ever - total_fixed_ever - total_raty_ever - sav_val
    
    # Budżet dzienny
    days_left = calendar.monthrange(today.year, today.month)[1] - today.day + 1
    daily = balance / days_left if days_left > 0 else balance

    # --- 6. SIDEBAR (NAWIGACJA I SEJF) ---
    with st.sidebar:
        st.markdown("<h2 style='border:none;'>🌾 SPICHLERZ</h2>", unsafe_allow_html=True)
        st.metric("ZASOBY W SKRZYNI", f"{sav_val:,.2f} PLN")
        
        st.divider()
        with st.expander("💰 RĘCZNA WPŁATA/WYPŁATA"):
            amt = st.number_input("Ile dukatów?", min_value=0.0, step=50.0)
            col_in, col_out = st.columns(2)
            if col_in.button("WPŁAĆ"):
                sh.worksheet("Oszczednosci").update_acell('A2', str(sav_val + amt))
                st.cache_data.clear(); st.rerun()
            if col_out.button("WYJMIJ"):
                sh.worksheet("Oszczednosci").update_acell('A2', str(sav_val - amt))
                st.cache_data.clear(); st.rerun()

        st.divider()
        st.subheader("🚜 ŻNIWA")
        st.write("Kliknij, aby przelać nadwyżkę z kaletki do sejfu na koniec miesiąca.")
        if st.button("ZAMKNIJ ŻNIWA"):
            if balance > 0:
                sh.worksheet("Oszczednosci").update_acell('A2', str(sav_val + balance))
                st.snow(); st.success(f"Zasiano {balance:.2f} PLN"); time.sleep(1); st.cache_data.clear(); st.rerun()
            else:
                st.warning("Kaletka pusta, nie ma co zbierać.")

    # --- 7. PANEL GŁÓWNY ---
    st.markdown("<h1>🎻 REJESTR GOSPODARSKI</h1>", unsafe_allow_html=True)
    
    m1, m2 = st.columns(2)
    m1.metric("📦 W KALETCE (NA DZIŚ)", f"{balance:,.2f} PLN")
    m2.metric("🥖 NA DZIEŃ", f"{daily:,.2f} PLN")

    # --- 8. ZAKŁADKI (TABS) ---
    tabs = st.tabs(["✍️ ZAPISY", "🏠 STAŁE & RATY", "📊 ANALIZA", "📝 LISTY", "🛶 PLANY"])

    # --- TAB: ZAPISY (DODAWANIE I EDYCJA) ---
    with tabs[0]:
        c_inc, c_exp = st.columns(2)
        with c_inc:
            with st.form("form_income", clear_on_submit=True):
                st.subheader("➕ Przybytek")
                t_i = st.text_input("Tytuł wpływu")
                v_i = st.number_input("Kwota", step=10.0)
                if st.form_submit_button("DODAJ DO KASY"):
                    sh.worksheet("Przychody").append_row([get_now(), t_i, v_i])
                    st.cache_data.clear(); st.rerun()
        with c_exp:
            with st.form("form_expense", clear_on_submit=True):
                st.subheader("➖ Wydatek")
                t_e = st.text_input("Na co poszło?")
                v_e = st.number_input("Kwota", step=1.0)
                k_e = st.selectbox("Kategoria", ["Jedzenie", "Dom", "Transport", "Rozrywka", "Inne"])
                if st.form_submit_button("ZAPŁAĆ"):
                    sh.worksheet("Wydatki").append_row([get_now(), t_e, v_e, k_e, "Zmienny"])
                    st.cache_data.clear(); st.rerun()
        
        st.divider()
        st.subheader("📖 Historia Wydatków (Bieżący miesiąc)")
        # Filtrowanie tylko bieżącego miesiąca do edycji
        df_exp_m = df_exp[df_exp['Data i Godzina'].astype(str).str.contains(current_month_str, na=False)].copy()
        if not df_exp_m.empty:
            df_exp_m["USUŃ"] = False
            ed_exp = st.data_editor(df_exp_m, use_container_width=True, hide_index=True, key="ed_expenses")
            if st.button("Zatwierdź zmiany w wydatkach"):
                # Pobierz rekordy, których nie usuwamy
                to_keep = ed_exp[ed_exp["USUŃ"] == False].drop(columns=["USUŃ"])
                # Pobierz rekordy z innych miesięcy (których nie edytowaliśmy)
                others = df_exp[~df_exp['Data i Godzina'].astype(str).str.contains(current_month_str, na=False)]
                final_df = pd.concat([others, to_keep], ignore_index=True)
                ws = sh.worksheet("Wydatki")
                ws.clear()
                ws.append_row(["Data i Godzina", "Nazwa", "Kwota", "Kategoria", "Typ"])
                if not final_df.empty: ws.append_rows(final_df.values.tolist())
                st.cache_data.clear(); st.rerun()

    # --- TAB: STAŁE & RATY ---
    with tabs[1]:
        st.subheader("🏠 Koszty Stałe (Miesięczne)")
        df_fix["USUŃ"] = False
        ed_fix = st.data_editor(df_fix, use_container_width=True, hide_index=True)
        if st.button("Uaktualnij koszty stałe"):
            new_fix = ed_fix[ed_fix["USUŃ"] == False].drop(columns=["USUŃ"])
            ws_fix = sh.worksheet("Koszty_Stale")
            ws_fix.clear()
            ws_fix.append_row(["Data i Godzina", "Nazwa", "Kwota"])
            if not new_fix.empty: ws_fix.append_rows(new_fix.values.tolist())
            st.cache_data.clear(); st.rerun()

        st.divider()
        st.subheader("📜 Aktywne Raty")
        # Wyświetlamy tylko raty, które jeszcze trwają
        active_rat = df_rat[df_rat['Koniec'] >= pd.Timestamp(today)].copy()
        st.table(active_rat[["Rata", "Kwota", "Koniec"]])

    # --- TAB: ANALIZA ---
    with tabs[2]:
        st.subheader("📊 Gdzie uciekają dukaty?")
        df_m = df_exp[df_exp['Data i Godzina'].astype(str).str.contains(current_month_str, na=False)]
        if not df_m.empty:
            fig = px.pie(df_m, values='Kwota', names='Kategoria', hole=.4, 
                         color_discrete_sequence=px.colors.sequential.RdBu)
            st.plotly_chart(fig, use_container_width=True)
            
            # Podsumowanie tabelaryczne
            summary = df_m.groupby('Kategoria')['Kwota'].sum().reset_index()
            st.dataframe(summary, use_container_width=True)
        else:
            st.info("Brak wpisów do analizy w tym miesiącu.")

    # --- TAB: LISTY (ZAKUPY I ZADANIA) ---
    with tabs[3]:
        l_col, z_col = st.columns(2)
        with l_col:
            st.subheader("🛒 Targ (Zakupy)")
            df_shp["KUPIONE"] = False
            ed_shp = st.data_editor(df_shp, use_container_width=True, hide_index=True)
            if st.button("Wyczyść koszyk"):
                new_shp = ed_shp[ed_shp["KUPIONE"] == False].drop(columns=["KUPIONE"])
                ws_shp = sh.worksheet("Zakupy")
                ws_shp.clear()
                ws_shp.append_row(["Data i Godzina", "Produkt"])
                if not new_shp.empty: ws_shp.append_rows(new_shp.values.tolist())
                st.cache_data.clear(); st.rerun()
        with z_col:
            st.subheader("🔨 Robota (Zadania)")
            df_tsk["ZROBIONE"] = False
            ed_tsk = st.data_editor(df_tsk, use_container_width=True, hide_index=True)
            if st.button("Odhacz wykonane"):
                new_tsk = ed_tsk[ed_tsk["ZROBIONE"] == False].drop(columns=["ZROBIONE"])
                ws_tsk = sh.worksheet("Zadania")
                ws_tsk.clear()
                ws_tsk.append_row(["Data i Godzina", "Zadanie", "Termin", "Priorytet"])
                if not new_tsk.empty: ws_tsk.append_rows(new_tsk.values.tolist())
                st.cache_data.clear(); st.rerun()

    # --- TAB: PLANY ---
    with tabs[4]:
        st.subheader("🛶 Plany na przyszłe miesiące")
        with st.form("form_plan"):
            p1, p2, p3 = st.columns(3)
            p_n = p1.text_input("Na co zbieramy?")
            p_k = p2.number_input("Szacunkowy koszt")
            p_m = p3.selectbox("Miesiąc docelowy", ["Styczeń", "Luty", "Marzec", "Kwiecień", "Maj", "Czerwiec", 
                                                   "Lipiec", "Sierpień", "Wrzesień", "Październik", "Listopad", "Grudzień"])
            if st.form_submit_button("DODAJ DO PLANÓW"):
                sh.worksheet("Planowanie").append_row([get_now(), p_n, p_k, p_m])
                st.cache_data.clear(); st.rerun()
        st.dataframe(df_pla, use_container_width=True)
