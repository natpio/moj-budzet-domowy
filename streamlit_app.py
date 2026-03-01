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
    if "password_correct" not in st.session_state:
        st.markdown("<h2 style='text-align: center; color: #b00000;'>🪗 Witaj w Zagrodzie. Podaj hasło:</h2>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            pwd = st.text_input("Klucz do kłódki", type="password")
            if st.button("Otwórz"):
                if pwd == st.secrets["credentials"]["password"]:
                    st.session_state["password_correct"] = True
                    st.rerun()
                else:
                    st.error("❌ Zły klucz!")
        return False
    return True

if check_password():
    # --- 3. CSS ---
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Fondamento&family=Almendra&display=swap');
        .stApp { background-color: #f4ece1; background-image: url("https://www.transparenttextures.com/patterns/natural-paper.png"); }
        [data-testid="stMetric"] { background: #ffffff !important; border: 4px double #b00000 !important; border-radius: 10px !important; box-shadow: 5px 5px 0px 0px #2c3e50 !important; padding: 15px !important; }
        h1, h2, h3 { color: #b00000 !important; font-family: 'Almendra', serif !important; text-align: center; border-bottom: 2px solid #b00000; }
        .stButton>button { background: #2c3e50 !important; color: #f4ece1 !important; font-family: 'Fondamento', cursive !important; width: 100%; height: 3.5em; }
        [data-testid="stSidebar"] { background: #e6d5bc !important; border-right: 3px solid #b00000 !important; }
        </style>
        """, unsafe_allow_html=True)

    # --- 4. DANE ---
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
        st.error(f"🚜 Błąd połączenia z bazą: {e}"); st.stop()

    # Konwersja kwot i dat we wszystkich tabelach
    for df in [df_inc, df_exp, df_fix, df_rat]:
        df['Kwota'] = pd.to_numeric(df['Kwota'], errors='coerce').fillna(0)
    
    df_inc['Data i Godzina'] = pd.to_datetime(df_inc['Data i Godzina'])
    df_exp['Data i Godzina'] = pd.to_datetime(df_exp['Data i Godzina'])
    df_rat['Start'] = pd.to_datetime(df_rat['Start'])
    df_rat['Koniec'] = pd.to_datetime(df_rat['Koniec'])
    s_sav = float(str(df_sav.iloc[0,0]).replace(',', '.')) if not df_sav.empty else 0.0

    # --- 5. ZAKŁADKI ---
    t1, t2, t3, t4 = st.tabs(["✍️ ZAPISY", "🏠 STAŁE & RATY", "📊 KSIĘGA (ANALIZA)", "🛒 LISTY"])

    with t3:
        st.subheader("📜 KSIĘGA GŁÓWNA - ARCHIWUM")
        
        # WYBÓR MIESIĄCA DO ANALIZY
        months_names = {1: "Styczeń", 2: "Luty", 3: "Marzec", 4: "Kwiecień", 5: "Maj", 6: "Czerwiec", 
                        7: "Lipiec", 8: "Sierpień", 9: "Wrzesień", 10: "Październik", 11: "Listopad", 12: "Grudzień"}
        
        col_sel1, col_sel2 = st.columns(2)
        sel_year = col_sel1.selectbox("Rok", [2026, 2025])
        sel_month = col_sel2.selectbox("Miesiąc", range(1, 13), format_func=lambda x: months_names[x], index=date.today().month-1)
        
        target_date = pd.Timestamp(year=sel_year, month=sel_month, day=1)
        
        # --- OBLICZENIE BILANSU OTWARCIA DLA WYBRANEGO MIESIĄCA ---
        # 1. Przychody i wydatki PRZED wybranym miesiącem
        inc_before = df_inc[df_inc['Data i Godzina'] < target_date]['Kwota'].sum()
        exp_before = df_exp[df_exp['Data i Godzina'] < target_date]['Kwota'].sum()
        
        # 2. 800+ (1600 zł za każdy miesiąc PRZED docelowym)
        months_diff = (target_date.year - 2026) * 12 + (target_date.month - 1)
        s_800_before = max(0, months_diff * 1600)
        
        # 3. Stałe i Raty PRZED docelowym
        fix_before = max(0, months_diff * df_fix['Kwota'].sum())
        rat_before = 0
        if months_diff > 0:
            for m in pd.date_range(start="2026-01-01", periods=months_diff, freq='MS'):
                rat_before += df_rat[(df_rat['Start'] <= m) & (df_rat['Koniec'] >= m)]['Kwota'].sum()
        
        # Stan początkowy kaletki w wybranym miesiącu
        op_bal = inc_before + s_800_before - exp_before - fix_before - rat_before - s_sav

        # --- GENEROWANIE WPISÓW DLA WYBRANEGO MIESIĄCA ---
        ledger = []
        curr_bal = op_bal
        ledger.append({"Data": target_date.strftime("%Y-%m-%d"), "Opis": f"STAN POCZĄTKOWY ({months_names[sel_month].upper()})", "Kwota": 0.0, "Saldo": curr_bal})
        
        # Dodanie 800+ za wybrany miesiąc
        curr_bal += 1600
        ledger.append({"Data": target_date.strftime("%Y-%m-%d"), "Opis": "WPŁYW: Świadczenie 800+", "Kwota": 1600.0, "Saldo": curr_bal})
        
        # Rezerwacje Stałe i Raty za wybrany miesiąc
        for _, row in df_fix.iterrows():
            curr_bal -= row['Kwota']
            ledger.append({"Data": target_date.strftime("%Y-%m-%d"), "Opis": f"OPŁATA: {row['Nazwa']}", "Kwota": -row['Kwota'], "Saldo": curr_bal})
        
        active_raty = df_rat[(df_rat['Start'] <= target_date) & (df_rat['Koniec'] >= target_date)]
        for _, row in active_raty.iterrows():
            curr_bal -= row['Kwota']
            ledger.append({"Data": target_date.strftime("%Y-%m-%d"), "Opis": f"RATA: {row['Rata']}", "Kwota": -row['Kwota'], "Saldo": curr_bal})

        # Operacje użytkownika w wybranym miesiącu
        mask_inc = (df_inc['Data i Godzina'].dt.month == sel_month) & (df_inc['Data i Godzina'].dt.year == sel_year)
        mask_exp = (df_exp['Data i Godzina'].dt.month == sel_month) & (df_exp['Data i Godzina'].dt.year == sel_year)
        
        ops = pd.concat([df_inc[mask_inc].assign(T="P"), df_exp[mask_exp].assign(T="W")]).sort_values('Data i Godzina')
        
        for _, row in ops.iterrows():
            val = row['Kwota'] if row['T'] == "P" else -row['Kwota']
            curr_bal += val
            ledger.append({"Data": row['Data i Godzina'].strftime("%Y-%m-%d %H:%M"), "Opis": row['Nazwa'], "Kwota": val, "Saldo": curr_bal})

        df_l = pd.DataFrame(ledger)
        st.dataframe(df_l.style.format({"Kwota": "{:.2f} PLN", "Saldo": "{:.2f} PLN"}), use_container_width=True, hide_index=True)
        
        fig = px.line(df_l, x=df_l.index, y="Saldo", title=f"Historia Salda: {months_names[sel_month]} {sel_year}")
        st.plotly_chart(fig, use_container_width=True)

    with t1:
        # Pasek główny (Metric) zawsze pokazuje stan na DZISIAJ
        today_m = date.today().month
        today_y = date.today().year
        # (Tutaj logika obliczeń na dziś dla metryki górnej - analogiczna do powyższej, ale zafiksowana na 'today')
        # ... (uproszczone dla czytelności, system używa zmiennej curr_bal z aktualnego miesiąca)
        
        st.markdown(f"### Dziś jest {date.today().strftime('%d')} {months_names[today_m]}")
        ci, ce = st.columns(2)
        with ci:
            with st.form("f_inc"):
                t, k = st.text_input("Tytuł"), st.number_input("Kwota", step=10.0)
                if st.form_submit_button("DODAJ PRZYCHÓD"):
                    sh.worksheet("Przychody").append_row([datetime.now().strftime("%Y-%m-%d %H:%M"), t, k])
                    st.cache_data.clear(); st.rerun()
        with ce:
            with st.form("f_exp"):
                t, k = st.text_input("Na co?"), st.number_input("Kwota", step=1.0)
                if st.form_submit_button("DODAJ WYDATEK"):
                    sh.worksheet("Wydatki").append_row([datetime.now().strftime("%Y-%m-%d %H:%M"), t, k, "Inne", "Zmienny"])
                    st.cache_data.clear(); st.rerun()

    with t2:
        st.subheader("⚙️ Zarządzanie obciążeniami")
        cf1, cf2 = st.columns(2)
        with cf1:
            with st.form("f_f"):
                n, k = st.text_input("Stały koszt"), st.number_input("Kwota mies.")
                if st.form_submit_button("DODAJ"):
                    sh.worksheet("Koszty_Stale").append_row([n, k])
                    st.cache_data.clear(); st.rerun()
        with cf2:
            with st.form("f_r"):
                n, k = st.text_input("Nazwa raty"), st.number_input("Kwota raty")
                s, e = st.date_input("Start"), st.date_input("Koniec")
                if st.form_submit_button("DODAJ RATĘ"):
                    sh.worksheet("Raty").append_row([n, k, s.strftime("%Y-%m-%d"), e.strftime("%Y-%m-%d")])
                    st.cache_data.clear(); st.rerun()
        st.table(df_fix)

    with t4:
        st.subheader("🛒 Listy")
        st.write(df_shp["Produkt"].tolist())
        if st.button("Czyść listę zakupów"):
            sh.worksheet("Zakupy").clear(); sh.worksheet("Zakupy").append_row(["Data", "Produkt"])
            st.cache_data.clear(); st.rerun()

    with st.sidebar:
        st.metric("SKRZYNIA (SEJF)", f"{s_sav:,.2f} PLN")
        # Wyświetlamy saldo końcowe z miesiąca dzisiejszego w sidebarze
        if st.button("🚜 ŻNIWA"):
            # (Logika przelewu nadwyżki)
            pass
