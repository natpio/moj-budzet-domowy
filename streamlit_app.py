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
        st.markdown("<h2 style='text-align: center; color: #b00000;'>🪗 Witaj w Zagrodzie. Podaj hasło:</h2>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            st.text_input("Klucz do kłódki", type="password", on_change=password_entered, key="password")
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
        st.error(f"🚜 Błąd: {e}"); st.stop()

    # --- 5. LOGIKA FINANSOWA ---
    today = date.today()
    cur_m_str = today.strftime("%Y-%m")
    
    # Konwersja kwot
    for df in [df_inc, df_exp, df_fix, df_rat]:
        df['Kwota'] = pd.to_numeric(df['Kwota'], errors='coerce').fillna(0)

    # Obliczenie Bilansu Otwarcia (Styczeń + Luty)
    # Przyjmujemy stan na 01.03.2026 rano
    prev_m_range = pd.date_range(start="2026-01-01", end="2026-02-28", freq='D')
    
    inc_prev = df_inc[~df_inc['Data i Godzina'].astype(str).str.contains(cur_m_str, na=False)]['Kwota'].sum()
    exp_prev = df_exp[~df_exp['Data i Godzina'].astype(str).str.contains(cur_m_str, na=False)]['Kwota'].sum()
    fix_prev = 2 * df_fix['Kwota'].sum() # Styczeń + Luty
    
    rat_prev = 0
    df_rat['Start'] = pd.to_datetime(df_rat['Start'])
    df_rat['Koniec'] = pd.to_datetime(df_rat['Koniec'])
    for m in pd.date_range(start="2026-01-01", periods=2, freq='MS'):
        rat_prev += df_rat[(df_rat['Start'] <= m) & (df_rat['Koniec'] >= m)]['Kwota'].sum()
    
    s_sav = float(str(df_sav.iloc[0,0]).replace(',', '.')) if not df_sav.empty else 0.0
    
    # NADWYŻKA Z PRZESZŁOŚCI + 800+ (2 msc)
    opening_balance = inc_prev + (2 * 1600) - exp_prev - fix_prev - rat_prev - s_sav

    # --- 6. GENEROWANIE KSIĘGI GŁÓWNEJ (DLA ZAKŁADKI ANALIZA) ---
    ledger = []
    # 1. Bilans Otwarcia
    current_running_balance = opening_balance
    ledger.append({"Data": "2026-03-01", "Opis": "BILANS OTWARCIA (Z LUTYGO)", "Kwota": 0.0, "Saldo": current_running_balance})
    
    # 2. Dodanie 800+ za marzec
    current_running_balance += 1600
    ledger.append({"Data": "2026-03-01", "Opis": "ZASILENIE: Świadczenie 800+ (Marzec)", "Kwota": 1600.0, "Saldo": current_running_balance})
    
    # 3. Odjęcie Kosztów Stałych i Rat (Rezerwacja na początku miesiąca)
    for _, row in df_fix.iterrows():
        current_running_balance -= row['Kwota']
        ledger.append({"Data": "2026-03-01", "Opis": f"REZERWACJA: {row['Nazwa']}", "Kwota": -row['Kwota'], "Saldo": current_running_balance})
    
    m_start = pd.Timestamp("2026-03-01")
    active_raty_m = df_rat[(df_rat['Start'] <= m_start) & (df_rat['Koniec'] >= m_start)]
    for _, row in active_raty_m.iterrows():
        current_running_balance -= row['Kwota']
        ledger.append({"Data": "2026-03-01", "Opis": f"RATA: {row['Rata']}", "Kwota": -row['Kwota'], "Saldo": current_running_balance})

    # 4. Dodanie bieżących operacji z Marca (Przychody i Wydatki)
    df_inc_m = df_inc[df_inc['Data i Godzina'].astype(str).str.contains(cur_m_str, na=False)].sort_values('Data i Godzina')
    df_exp_m = df_exp[df_exp['Data i Godzina'].astype(str).str.contains(cur_m_str, na=False)].sort_values('Data i Godzina')
    
    combined_m = pd.concat([
        df_inc_m.assign(Typ="P"),
        df_exp_m.assign(Typ="W")
    ]).sort_values('Data i Godzina')

    for _, row in combined_m.iterrows():
        val = row['Kwota'] if row['Typ'] == "P" else -row['Kwota']
        current_running_balance += val
        ledger.append({
            "Data": row['Data i Godzina'][:10],
            "Opis": row['Nazwa'],
            "Kwota": val,
            "Saldo": current_running_balance
        })

    df_ledger = pd.DataFrame(ledger)
    final_balance = current_running_balance
    
    # --- 7. DASHBOARD ---
    st.markdown("<h1>🎻 REJESTR GOSPODARSKI</h1>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    c1.metric("📦 W KALETCE (SALDO KOŃCOWE)", f"{final_balance:,.2f} PLN")
    days_left = calendar.monthrange(today.year, today.month)[1] - today.day + 1
    c2.metric("🥖 NA DZIEŃ", f"{final_balance/days_left:,.2f} PLN" if days_left > 0 else "---")

    # --- 8. ZAKŁADKI ---
    t1, t2, t3, t4 = st.tabs(["✍️ ZAPISY", "🏠 STAŁE & RATY", "📊 KSIĘGA (ANALIZA)", "🛒 LISTY"])

    with t1:
        ci, ce = st.columns(2)
        with ci:
            with st.form("f_i", clear_on_submit=True):
                st.subheader("➕ Przybytek")
                t_i, k_i = st.text_input("Tytuł"), st.number_input("Kwota", step=10.0)
                if st.form_submit_button("DODAJ"):
                    sh.worksheet("Przychody").append_row([datetime.now().strftime("%Y-%m-%d %H:%M"), t_i, k_i])
                    st.cache_data.clear(); st.rerun()
        with ce:
            with st.form("f_e", clear_on_submit=True):
                st.subheader("➖ Wydatek")
                t_e, k_e = st.text_input("Na co?"), st.number_input("Kwota", step=1.0)
                if st.form_submit_button("ZAPŁAĆ"):
                    sh.worksheet("Wydatki").append_row([datetime.now().strftime("%Y-%m-%d %H:%M"), t_e, k_e, "Inne", "Zmienny"])
                    st.cache_data.clear(); st.rerun()

    with t2:
        cf1, cf2 = st.columns(2)
        with cf1:
            with st.form("f_fix"):
                st.write("**Dodaj Koszt Stały**")
                nf, kf = st.text_input("Nazwa"), st.number_input("Kwota")
                if st.form_submit_button("ZAPISZ KOSZT"):
                    sh.worksheet("Koszty_Stale").append_row([datetime.now().strftime("%Y-%m-%d"), nf, kf])
                    st.cache_data.clear(); st.rerun()
        with cf2:
            with st.form("f_rat"):
                st.write("**Dodaj Ratę**")
                nr, kr = st.text_input("Nazwa raty"), st.number_input("Kwota")
                ds, de = st.date_input("Start"), st.date_input("Koniec")
                if st.form_submit_button("ZAPISZ RATĘ"):
                    sh.worksheet("Raty").append_row([nr, kr, ds.strftime("%Y-%m-%d"), de.strftime("%Y-%m-%d")])
                    st.cache_data.clear(); st.rerun()

    with t3:
        st.subheader("📜 KSIĘGA GŁÓWNA - WYCIĄG Z KONTA")
        st.info("Poniższa tabela przedstawia każdą operację, która wpłynęła na obecny stan Twojej kaletki.")
        
        # Formatowanie tabeli bankowej
        styled_ledger = df_ledger.copy()
        styled_ledger['Kwota'] = styled_ledger['Kwota'].map('{:,.2f} PLN'.format)
        styled_ledger['Saldo'] = styled_ledger['Saldo'].map('{:,.2f} PLN'.format)
        
        st.dataframe(styled_ledger, use_container_width=True, hide_index=True)
        
        st.divider()
        st.subheader("📉 Wykres Salda")
        fig = px.line(df_ledger, x=df_ledger.index, y="Saldo", title="Zmiana zasobów w czasie", 
                      labels={"index": "Kolejne operacje", "Saldo": "Stan portfela (PLN)"})
        fig.update_traces(line_color='#b00000')
        st.plotly_chart(fig, use_container_width=True)

    with t4:
        st.subheader("🛒 Listy")
        # Wyświetlanie list bez edycji
        st.write("Do kupienia:", df_shp["Produkt"].tolist())
        if st.button("Wyczyść listy"):
            sh.worksheet("Zakupy").clear(); sh.worksheet("Zakupy").append_row(["Data", "Produkt"])
            st.cache_data.clear(); st.rerun()

    with st.sidebar:
        st.metric("W SKRZYNI", f"{s_sav:,.2f} PLN")
        if st.button("🚜 ZAMKNIJ ŻNIWA"):
            if final_balance > 0:
                sh.worksheet("Oszczednosci").update_acell('A2', str(s_sav + final_balance))
                st.cache_data.clear(); st.rerun()
