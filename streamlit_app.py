import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
from google.oauth2 import service_account
from datetime import datetime, date
import calendar
import time

# --- 1. KONFIGURACJA STRONY ---
st.set_page_config(page_title="Rock'n'Roll Diner Budget 1960", layout="wide", page_icon="🍒")

# --- 2. LOGOWANIE ---
def check_password():
    if "password_correct" not in st.session_state:
        st.markdown("""
            <style>
            @import url('https://fonts.googleapis.com/css2?family=Pacifico&display=swap');
            .login-box { text-align: center; padding: 50px; background-color: #fefae0; border: 10px solid #d62828; border-radius: 20px; box-shadow: 15px 15px 0px #003049; }
            </style>
            <div class='login-box'><h1 style='color: #d62828; font-family: "Pacifico", cursive;'>🎵 Jukebox Login</h1></div>
        """, unsafe_allow_html=True)
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
    # --- 3. MAKSYMALNY STYL RETRO (CSS) ---
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Pacifico&family=Bungee+Inline&family=Montserrat:wght@400;700&display=swap');
        .stApp { background-color: #a2d2ff; background-image: radial-gradient(#d62828 20%, transparent 20%), radial-gradient(#ffffff 15%, transparent 16%); background-size: 60px 60px; font-family: 'Montserrat', sans-serif; }
        div[data-testid="stForm"], .stDataEditor { background-color: #fefae0 !important; border: 6px solid #003049 !important; border-radius: 20px !important; padding: 30px !important; box-shadow: 15px 15px 0px #d62828 !important; }
        label p, .stMarkdown p { color: #003049 !important; font-weight: 700 !important; }
        [data-testid="stMetric"] { background: #fefae0 !important; border: 8px solid #ffafcc !important; border-radius: 50% 10px 50% 10px !important; box-shadow: 12px 12px 0px 0px #d62828 !important; }
        [data-testid="stMetricValue"] div { color: #d62828 !important; font-family: 'Pacifico', cursive !important; font-size: 40px !important; }
        .stDataFrame, div[data-testid="stTable"] { background-color: white !important; border: 3px solid #003049 !important; border-radius: 10px !important; }
        h1 { color: #ffffff !important; font-family: 'Pacifico', cursive !important; font-size: 4.5em !important; text-shadow: 5px 5px 0px #d62828, 10px 10px 0px #003049; text-align: center; }
        .stButton>button { background: #d62828 !important; color: white !important; font-family: 'Bungee Inline' !important; border-radius: 50px !important; font-size: 20px !important; box-shadow: 6px 6px 0px #003049; }
        [data-testid="stSidebar"] { background: #ffafcc !important; border-right: 8px solid #d62828 !important; }
        </style>
        """, unsafe_allow_html=True)

    # --- 4. POŁĄCZENIE Z DANYMI ---
    @st.cache_resource
    def get_client():
        creds_dict = st.secrets["gcp_service_account"]
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=scope)
        return gspread.authorize(creds)

    @st.cache_data(ttl=30)
    def load_all_data():
        client = get_client()
        sh = client.open("Budzet_Data")
        sheets = ["Przychody", "Wydatki", "Koszty_Stale", "Raty", "Oszczednosci", "Zakupy"]
        return {name: pd.DataFrame(sh.worksheet(name).get_all_records()) for name in sheets}

    data = load_all_data()
    df_inc, df_exp, df_fix, df_rat, df_sav, df_shp = [data[n] for n in ["Przychody", "Wydatki", "Koszty_Stale", "Raty", "Oszczednosci", "Zakupy"]]
    sh = get_client().open("Budzet_Data")

    # Konwersja danych
    for df in [df_inc, df_exp, df_fix, df_rat]:
        df['Kwota'] = pd.to_numeric(df['Kwota'], errors='coerce').fillna(0)
    df_inc['Data i Godzina'] = pd.to_datetime(df_inc['Data i Godzina'], errors='coerce')
    df_exp['Data i Godzina'] = pd.to_datetime(df_exp['Data i Godzina'], errors='coerce')
    df_rat['Start'] = pd.to_datetime(df_rat['Start'], errors='coerce')
    df_rat['Koniec'] = pd.to_datetime(df_rat['Koniec'], errors='coerce')
    s_sav = float(str(df_sav.iloc[0,0]).replace(',', '.')) if not df_sav.empty else 0.0

    # --- 5. LOGIKA HARMONOGRAMU ---
    def generate_ledger(sel_year, sel_month):
        target_date = pd.Timestamp(year=sel_year, month=sel_month, day=1)
        inc_before = df_inc[df_inc['Data i Godzina'] < target_date]['Kwota'].sum()
        exp_before = df_exp[df_exp['Data i Godzina'] < target_date]['Kwota'].sum()
        months_passed = (target_date.year - 2026) * 12 + (target_date.month - 1)
        s_800_before = max(0, months_passed * 1600)
        fix_before = max(0, months_passed * df_fix['Kwota'].sum())
        rat_before = 0
        if months_passed > 0:
            for m in pd.date_range(start="2026-01-01", periods=months_passed, freq='MS'):
                rat_before += df_rat[(df_rat['Start'] <= m) & (df_rat['Koniec'] >= m)]['Kwota'].sum()
        
        curr_val = inc_before + s_800_before - exp_before - fix_before - rat_before - s_sav
        ledger = []
        ledger.append({"Dzień": "START", "Opis": "BILANS OTWARCIA", "Zmiana": 0.0, "Saldo": curr_val})
        
        curr_val += 1600
        ledger.append({"Dzień": "01", "Opis": "🎁 GOVT 800+ (2x)", "Zmiana": 1600.0, "Saldo": curr_val})
        
        for _, row in df_fix.iterrows():
            curr_val -= row['Kwota']
            ledger.append({"Dzień": "01", "Opis": f"🏠 STAŁY: {row['Nazwa']}", "Zmiana": -row['Kwota'], "Saldo": curr_val})
            
        active_raty = df_rat[(df_rat['Start'] <= target_date) & (df_rat['Koniec'] >= target_date)]
        for _, row in active_raty.iterrows():
            curr_val -= row['Kwota']
            ledger.append({"Dzień": "01", "Opis": f"💸 RATA: {row['Rata']}", "Zmiana": -row['Kwota'], "Saldo": curr_val})
            
        mask_inc = (df_inc['Data i Godzina'].dt.month == sel_month) & (df_inc['Data i Godzina'].dt.year == sel_year)
        mask_exp = (df_exp['Data i Godzina'].dt.month == sel_month) & (df_exp['Data i Godzina'].dt.year == sel_year)
        ops = pd.concat([df_inc[mask_inc].assign(T="P"), df_exp[mask_exp].assign(T="W")]).sort_values('Data i Godzina')
        
        for _, row in ops.iterrows():
            ch = row['Kwota'] if row['T'] == "P" else -row['Kwota']
            curr_val += ch
            ledger.append({"Dzień": row['Data i Godzina'].strftime("%d"), "Opis": row['Nazwa'], "Zmiana": ch, "Saldo": curr_val})
            
        return pd.DataFrame(ledger), curr_val

    # --- 6. INTERFEJS ---
    st.markdown("<h1>Diner Budget 1960</h1>", unsafe_allow_html=True)
    today_y, today_m = date.today().year, date.today().month
    df_curr, current_bal = generate_ledger(today_y, today_m)
    
    c_m1, c_m2 = st.columns(2)
    c_m1.metric("PORTFEL", f"{current_bal:,.2f} $")
    days_left = calendar.monthrange(today_y, today_m)[1] - date.today().day + 1
    c_m2.metric("DZIENNIE", f"{current_bal/days_left:,.2f} $" if days_left > 0 else "---")

    tabs = st.tabs(["🎵 ZAPISY", "🏠 KONFIGURACJA", "📊 ANALIZA", "🛒 ZAKUPY", "🛠️ KOREKTA DANYCH"])

    with tabs[0]:
        col1, col2 = st.columns(2)
        with col1:
            with st.form("inc_f", clear_on_submit=True):
                st.write("*🍭 PRZYCHÓD*")
                n = st.text_input("Nazwa")
                k = st.number_input("Kwota", step=10.0)
                if st.form_submit_button("DODAJ DO KASY"):
                    sh.worksheet("Przychody").append_row([datetime.now().strftime("%Y-%m-%d %H:%M"), n, k])
                    st.cache_data.clear(); st.rerun()
        with col2:
            with st.form("exp_f", clear_on_submit=True):
                st.write("*👠 WYDATEK*")
                n = st.text_input("Na co?")
                k = st.number_input("Koszt", step=1.0)
                if st.form_submit_button("ZAPŁAĆ"):
                    sh.worksheet("Wydatki").append_row([datetime.now().strftime("%Y-%m-%d %H:%M"), n, k, "Retro", "Var"])
                    st.cache_data.clear(); st.rerun()

    with tabs[1]:
        ca, cb = st.columns(2)
        with ca:
            with st.form("fix_f"):
                st.write("*RACHUNKI STAŁE*")
                n = st.text_input("Nazwa")
                k = st.number_input("Kwota")
                if st.form_submit_button("ZAPISZ"):
                    sh.worksheet("Koszty_Stale").append_row([n, k])
                    st.cache_data.clear(); st.rerun()
            st.dataframe(df_fix, use_container_width=True)
        with cb:
            with st.form("rat_f"):
                st.write("*RATY (CZASOWE)*")
                n = st.text_input("Nazwa")
                k = st.number_input("Kwota raty")
                s = st.date_input("Start")
                e = st.date_input("Koniec")
                if st.form_submit_button("DODAJ RATĘ"):
                    sh.worksheet("Raty").append_row([n, k, s.strftime("%Y-%m-%d"), e.strftime("%Y-%m-%d")])
                    st.cache_data.clear(); st.rerun()
            st.dataframe(df_rat, use_container_width=True)

    with tabs[2]:
        sy = st.selectbox("Rok", [2026, 2025])
        sm = st.selectbox("Miesiąc", range(1, 13), index=today_m-1)
        df_l, _ = generate_ledger(sy, sm)
        st.dataframe(df_l, use_container_width=True, hide_index=True)
        fig = px.line(df_l, x=df_l.index, y="Saldo", title="Przepływ gotówki")
        st.plotly_chart(fig, use_container_width=True)

    with tabs[3]:
        with st.form("shop_f", clear_on_submit=True):
            i = st.text_input("Co kupić?")
            if st.form_submit_button("DODAJ DO LISTY"):
                sh.worksheet("Zakupy").append_row([datetime.now().strftime("%Y-%m-%d"), i])
                st.cache_data.clear(); st.rerun()
        st.write(df_shp)
        if st.button("WYCZYŚĆ LISTĘ"):
            worksheet = sh.worksheet("Zakupy")
            worksheet.clear()
            worksheet.append_row(["Data", "Produkt"])
            st.cache_data.clear(); st.rerun()

    with tabs[4]:
        st.subheader("🛠️ Panel Korekty (Edycja bezpośrednia)")
        target = st.selectbox("Wybierz tabelę do edycji", ["Przychody", "Wydatki", "Koszty_Stale", "Raty"])
        client = get_client()
        edit_sh = client.open("Budzet_Data").worksheet(target)
        df_edit = pd.DataFrame(edit_sh.get_all_records())
        
        updated_df = st.data_editor(df_edit, num_rows="dynamic", use_container_width=True)
        
        if st.button("ZAPISZ ZMIANY W GOOGLE SHEETS"):
            edit_sh.clear()
            edit_sh.update([updated_df.columns.values.tolist()] + updated_df.fillna("").values.tolist())
            st.success("Zaktualizowano pomyślnie!")
            st.cache_data.clear(); time.sleep(1); st.rerun()

    with st.sidebar:
        st.markdown("<h2 style='color: white;'>💎 SEJF</h2>", unsafe_allow_html=True)
        st.metric("OSZCZĘDNOŚCI", f"{s_sav:,.2f} $")
        if st.button("🚜 ŻNIWA"):
            sh.worksheet("Oszczednosci").update_acell('A2', str(s_sav + current_bal))
            st.balloons(); st.cache_data.clear(); time.sleep(1); st.rerun()
