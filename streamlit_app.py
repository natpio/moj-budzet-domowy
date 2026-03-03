import streamlit as st
import pandas as pd
import gspread
from google.oauth2 import service_account
from datetime import datetime, date
import calendar
import time
import plotly.express as px

# --- 1. KONFIGURACJA STRONY ---
st.set_page_config(page_title="Rock'n'Roll Diner Budget 1960", layout="wide", page_icon="🍒")

# --- 2. LOGOWANIE ---
def check_password():
    if "password_correct" not in st.session_state:
        st.markdown("<h2 style='text-align: center; color: #d62828; font-family: \"Pacifico\", cursive;'>🎵 Witaj w Dinerze. Włącz Jukebox (Hasło):</h2>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            pwd = st.text_input("Klucz do szafy grającej", type="password")
            if st.button("PUNKT DLA CIEBIE! START!"):
                if pwd == st.secrets["credentials"]["password"]:
                    st.session_state["password_correct"] = True
                    st.rerun()
                else:
                    st.error("❌ Zły klucz, skarbie!")
        return False
    return True

if check_password():
    # --- 3. STYLIZACJA CSS ---
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Pacifico&family=Bungee+Inline&family=Montserrat:wght@400;700&display=swap');
        .stApp { background-color: #a2d2ff; background-image: radial-gradient(#d62828 20%, transparent 20%), radial-gradient(#ffffff 15%, transparent 16%); background-size: 60px 60px; background-position: 0 0, 30px 30px; font-family: 'Montserrat', sans-serif; }
        div[data-testid="stForm"] { background-color: #fefae0 !important; border: 5px solid #003049 !important; border-radius: 15px !important; padding: 25px !important; box-shadow: 10px 10px 0px #d62828 !important; }
        label p, .stMarkdown p { color: #003049 !important; font-weight: 700 !important; }
        [data-testid="stMetric"] { background: #fefae0 !important; border: 8px solid #ffafcc !important; border-radius: 50% 10px 50% 10px !important; box-shadow: 12px 12px 0px 0px #d62828 !important; padding: 30px !important; }
        h1 { color: #ffffff !important; font-family: 'Pacifico', cursive !important; font-size: 4.5em !important; text-shadow: 5px 5px 0px #d62828, 10px 10px 0px #003049; text-align: center; margin-bottom: 20px;}
        .stButton>button { background: #d62828 !important; color: white !important; font-family: 'Bungee Inline', cursive !important; border-radius: 50px !important; box-shadow: 6px 6px 0px #003049; }
        .stTabs [data-baseweb="tab-list"] { background-color: rgba(255, 255, 255, 0.8); border-radius: 15px; padding: 5px; }
        </style>
        """, unsafe_allow_html=True)

    # --- 4. POŁĄCZENIE Z DANYMI ---
    @st.cache_resource
    def get_client():
        creds_dict = st.secrets["gcp_service_account"]
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=scope)
        return gspread.authorize(creds)

    @st.cache_data(ttl=5) 
    def load_all_data():
        client = get_client()
        sh = client.open("Budzet_Data")
        sheets = ["Przychody", "Wydatki", "Koszty_Stale", "Raty", "Oszczednosci", "Zakupy"]
        all_data = {}
        for name in sheets:
            ws = sh.worksheet(name)
            records = ws.get_all_records()
            all_data[name] = pd.DataFrame(records) if records else pd.DataFrame()
        return all_data

    def refresh():
        st.cache_data.clear()
        time.sleep(0.5)
        st.rerun()

    # Inicjalizacja
    try:
        data_dict = load_all_data()
        df_inc = data_dict["Przychody"]
        df_exp = data_dict["Wydatki"]
        df_fix = data_dict["Koszty_Stale"]
        df_sav = data_dict["Oszczednosci"]
        df_shp = data_dict["Zakupy"]
        client = get_client()
        sh = client.open("Budzet_Data")
    except Exception as e:
        st.error(f"🚜 Błąd połączenia: {e}"); st.stop()

    # Czyszczenie danych
    for df in [df_inc, df_exp, df_fix]:
        if not df.empty and 'Kwota' in df.columns:
            df['Kwota'] = pd.to_numeric(df['Kwota'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
    
    if not df_inc.empty: df_inc['Data i Godzina'] = pd.to_datetime(df_inc['Data i Godzina'], errors='coerce')
    if not df_exp.empty: df_exp['Data i Godzina'] = pd.to_datetime(df_exp['Data i Godzina'], errors='coerce')
    s_sav = float(str(df_sav.iloc[0,0]).replace(',', '.')) if not df_sav.empty else 0.0

    # --- 5. LOGIKA FINANSOWA ---
    def generate_ledger(sel_year, sel_month):
        target_date = pd.Timestamp(year=sel_year, month=sel_month, day=1)
        inc_before = df_inc[df_inc['Data i Godzina'] < target_date]['Kwota'].sum() if not df_inc.empty else 0
        exp_before = df_exp[df_exp['Data i Godzina'] < target_date]['Kwota'].sum() if not df_exp.empty else 0
        
        months_diff = max(0, (target_date.year - 2026) * 12 + (target_date.month - 1))
        fix_total = df_fix['Kwota'].sum() if not df_fix.empty else 0
        
        op_bal = inc_before + (months_diff * 1600) - exp_before - (months_diff * fix_total) - s_sav
        
        ledger = [{"Data": target_date.strftime("%Y-%m-%d"), "Opis": "SALDO POCZĄTKOWE", "Zmiana": 0.0, "Saldo": op_bal}]
        curr = op_bal + 1600
        ledger.append({"Data": target_date.strftime("%Y-%m-%d"), "Opis": "800+", "Zmiana": 1600.0, "Saldo": curr})
        
        if not df_fix.empty:
            for _, r in df_fix.iterrows():
                curr -= r['Kwota']
                ledger.append({"Data": target_date.strftime("%Y-%m-%d"), "Opis": f"STAŁY: {r['Nazwa']}", "Zmiana": -r['Kwota'], "Saldo": curr})

        mask_i = (df_inc['Data i Godzina'].dt.month == sel_month) & (df_inc['Data i Godzina'].dt.year == sel_year) if not df_inc.empty else False
        mask_e = (df_exp['Data i Godzina'].dt.month == sel_month) & (df_exp['Data i Godzina'].dt.year == sel_year) if not df_exp.empty else False
        
        ops = pd.concat([df_inc[mask_i].assign(T="P"), df_exp[mask_e].assign(T="W")]).sort_values('Data i Godzina')
        for _, r in ops.iterrows():
            ch = r['Kwota'] if r['T'] == "P" else -r['Kwota']
            curr += ch
            ledger.append({"Data": r['Data i Godzina'].strftime("%m-%d %H:%M"), "Opis": f"[{r['Kategoria'] if 'Kategoria' in r else 'Inne'}] {r['Nazwa']}", "Zmiana": ch, "Saldo": curr})
            
        return pd.DataFrame(ledger), curr

    # --- 6. DASHBOARD ---
    st.markdown("<h1>Diner Budget 1960</h1>", unsafe_allow_html=True)
    today_y, today_m = date.today().year, date.today().month
    _, current_total_balance = generate_ledger(today_y, today_m)
    
    c_m1, c_m2 = st.columns(2)
    c_m1.metric("PORTFEL", f"{current_total_balance:,.2f} zł")
    days_left = calendar.monthrange(today_y, today_m)[1] - date.today().day + 1
    c_m2.metric("NA DZIEŃ", f"{current_total_balance/days_left:,.2f} zł" if days_left > 0 else "0 zł")

    # --- 7. TABS ---
    t1, t2, t3, t4 = st.tabs(["🎵 REKORDY", "🏠 USTAWIENIA", "📊 ANALIZA", "🍔 LISTA"])

    with t1:
        st.subheader("📻 Dodaj do Jukeboxa")
        c1, c2 = st.columns(2)
        with c1:
            with st.form("f_in", clear_on_submit=True):
                st.write("**🍭 WPŁATA**")
                t_n = st.text_input("Nazwa")
                k_n = st.number_input("Kwota", min_value=0.0)
                if st.form_submit_button("DODAJ WPŁATĘ"):
                    sh.worksheet("Przychody").append_row([datetime.now().strftime("%Y-%m-%d %H:%M"), t_n, k_n, "Przychód", "Stały"])
                    refresh()
        with c2:
            with st.form("f_out", clear_on_submit=True):
                st.write("**👠 WYDATEK**")
                t_o = st.text_input("Na co?")
                k_o = st.number_input("Cena", min_value=0.0)
                # NOWOŚĆ: Wybór kategorii
                kat = st.selectbox("Kategoria", ["jedzenie", "dom", "transport", "rozrywka", "inne"])
                if st.form_submit_button("ZAPŁAĆ"):
                    sh.worksheet("Wydatki").append_row([datetime.now().strftime("%Y-%m-%d %H:%M"), t_o, k_o, kat, "Zmienny"])
                    refresh()
        
        st.divider()
        st.write("**Ostatnie Wydatki:**")
        if not df_exp.empty:
            st.dataframe(df_exp.tail(5), use_container_width=True)
            if st.button("🗑️ USUŃ OSTATNI WYDATEK"):
                ws_e = sh.worksheet("Wydatki")
                ws_e.delete_rows(len(df_exp) + 1)
                refresh()

    with t2:
        st.subheader("🏠 Koszty Stałe")
        with st.form("f_fix"):
            n_f = st.text_input("Nazwa kosztu")
            k_f = st.number_input("Kwota miesięczna")
            if st.form_submit_button("ZAPISZ KOSZT"):
                sh.worksheet("Koszty_Stale").append_row([n_f, k_f])
                refresh()
        st.dataframe(df_fix, use_container_width=True)

    with t3:
        st.subheader("📊 Historia")
        c_s1, c_s2 = st.columns(2)
        s_y = c_s1.selectbox("Rok", [2026, 2025])
        s_m = c_s2.selectbox("Miesiąc", range(1, 13), index=date.today().month-1)
        df_l, _ = generate_ledger(s_y, s_m)
        st.dataframe(df_l, use_container_width=True)
        if not df_l.empty:
            fig = px.line(df_l, x=df_l.index, y="Saldo", title="Stan Portfela")
            st.plotly_chart(fig, use_container_width=True)

    with t4:
        st.subheader("🛒 Lista Zakupów")
        with st.form("f_s"):
            item = st.text_input("Produkt")
            if st.form_submit_button("DODAJ"):
                sh.worksheet("Zakupy").append_row([datetime.now().strftime("%Y-%m-%d"), item])
                refresh()
        if not df_shp.empty:
            st.dataframe(df_shp, use_container_width=True)
            if st.button("🧹 WYCZYŚĆ LISTĘ"):
                ws_s = sh.worksheet("Zakupy")
                ws_s.clear()
                ws_s.append_row(["Data", "Produkt"])
                refresh()

    with st.sidebar:
        st.markdown("<h2 style='color: white;'>💎 SKARBIEC</h2>", unsafe_allow_html=True)
        st.metric("OSZCZĘDNOŚCI", f"{s_sav:,.2f} zł")
        if st.button("🔄 PEŁNE ODŚWIEŻENIE"):
            refresh()
