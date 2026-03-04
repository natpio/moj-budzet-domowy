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
    # --- 3. STYL RETRO (CSS) - SKUPIONY NA CZYTELNOŚCI ---
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Pacifico&family=Bungee+Inline&family=Montserrat:wght@400;700&display=swap');
        
        .stApp { 
            background-color: #a2d2ff; 
            background-image: radial-gradient(#d62828 20%, transparent 20%), radial-gradient(#ffffff 15%, transparent 16%);
            background-size: 60px 60px;
            background-position: 0 0, 30px 30px;
            font-family: 'Montserrat', sans-serif;
        }

        /* Czytelność Formularzy */
        div[data-testid="stForm"] {
            background-color: #fefae0 !important; 
            border: 6px solid #003049 !important;
            border-radius: 20px !important;
            padding: 30px !important;
            box-shadow: 15px 15px 0px #d62828 !important;
        }
        
        label p { color: #003049 !important; font-weight: 700 !important; }
        
        /* Metryki */
        [data-testid="stMetric"] { 
            background: #fefae0 !important; 
            border: 8px solid #ffafcc !important; 
            border-radius: 50% 10px 50% 10px !important; 
            box-shadow: 12px 12px 0px 0px #d62828 !important; 
        }
        [data-testid="stMetricValue"] div { color: #d62828 !important; font-family: 'Pacifico', cursive !important; }

        h1 { 
            color: #ffffff !important; font-family: 'Pacifico', cursive !important; font-size: 4.5em !important; 
            text-shadow: 5px 5px 0px #d62828, 10px 10px 0px #003049; text-align: center;
        }

        .stButton>button { 
            background: #d62828 !important; color: white !important; font-family: 'Bungee Inline' !important;
            border-radius: 50px !important; font-size: 22px !important; box-shadow: 6px 6px 0px #003049;
        }

        .stDataFrame { background-color: white !important; border: 3px solid #003049 !important; }
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
        sheets = ["Przychody", "Wydatki", "Koszty_Stale", "Raty", "Oszczednosci", "Zakupy"]
        return {name: pd.DataFrame(sh.worksheet(name).get_all_records()) for name in sheets}

    data = load_all_data()
    df_inc, df_exp, df_fix, df_rat, df_sav, df_shp = [data[n] for n in ["Przychody", "Wydatki", "Koszty_Stale", "Raty", "Oszczednosci", "Zakupy"]]
    sh = get_client().open("Budzet_Data")

    # Konwersja typów
    df_inc['Kwota'] = pd.to_numeric(df_inc['Kwota'], errors='coerce').fillna(0)
    df_exp['Kwota'] = pd.to_numeric(df_exp['Kwota'], errors='coerce').fillna(0)
    df_fix['Kwota'] = pd.to_numeric(df_fix['Kwota'], errors='coerce').fillna(0)
    df_rat['Kwota'] = pd.to_numeric(df_rat['Kwota'], errors='coerce').fillna(0)
    
    df_inc['Data i Godzina'] = pd.to_datetime(df_inc['Data i Godzina'], errors='coerce')
    df_exp['Data i Godzina'] = pd.to_datetime(df_exp['Data i Godzina'], errors='coerce')
    df_rat['Start'] = pd.to_datetime(df_rat['Start'], errors='coerce')
    df_rat['Koniec'] = pd.to_datetime(df_rat['Koniec'], errors='coerce')
    
    s_sav = float(str(df_sav.iloc[0,0]).replace(',', '.')) if not df_sav.empty else 0.0

    # --- 5. LOGIKA HARMONOGRAMU ---
    def generate_ledger(sel_year, sel_month):
        target_date = pd.Timestamp(year=sel_year, month=sel_month, day=1)
        
        # 1. Bilans otwarcia (wszystko przed wybranym miesiącem)
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
        ledger.append({"Data": "START", "Opis": "SALDO POCZĄTKOWE", "Zmiana": 0.0, "Saldo": curr_val})
        
        # 2. Operacje stałe miesiąca
        curr_val += 1600
        ledger.append({"Data": "01", "Opis": "🎁 GOVT 800+ (2x)", "Zmiana": 1600.0, "Saldo": curr_val})
        
        for _, row in df_fix.iterrows():
            curr_val -= row['Kwota']
            ledger.append({"Data": "01", "Opis": f"🏠 STAŁY: {row['Nazwa']}", "Zmiana": -row['Kwota'], "Saldo": curr_val})
            
        # 3. Raty (tylko jeśli miesiąc mieści się w datach)
        active_raty = df_rat[(df_rat['Start'] <= target_date) & (df_rat['Koniec'] >= target_date)]
        for _, row in active_raty.iterrows():
            curr_val -= row['Kwota']
            ledger.append({"Data": "01", "Opis": f"💸 RATA: {row['Rata']}", "Zmiana": -row['Kwota'], "Saldo": curr_val})
            
        # 4. Operacje zmienne
        mask_inc = (df_inc['Data i Godzina'].dt.month == sel_month) & (df_inc['Data i Godzina'].dt.year == sel_year)
        mask_exp = (df_exp['Data i Godzina'].dt.month == sel_month) & (df_exp['Data i Godzina'].dt.year == sel_year)
        ops = pd.concat([df_inc[mask_inc].assign(T="P"), df_exp[mask_exp].assign(T="W")]).sort_values('Data i Godzina')
        
        for _, row in ops.iterrows():
            ch = row['Kwota'] if row['T'] == "P" else -row['Kwota']
            curr_val += ch
            ledger.append({"Data": row['Data i Godzina'].strftime("%d"), "Opis": row['Nazwa'], "Zmiana": ch, "Saldo": curr_val})
            
        return pd.DataFrame(ledger), curr_val

    # --- 6. DASHBOARD ---
    st.markdown("<h1>Diner Budget 1960</h1>", unsafe_allow_html=True)
    
    today_y, today_m = date.today().year, date.today().month
    df_current, current_bal = generate_ledger(today_y, today_m)
    
    c_m1, c_m2 = st.columns(2)
    c_m1.metric("W PORTFELU", f"{current_bal:,.2f} $")
    days_left = calendar.monthrange(today_y, today_m)[1] - date.today().day + 1
    c_m2.metric("DZIENNIE DO WYDANIA", f"{current_bal/days_left:,.2f} $" if days_left > 0 else "---")

    t1, t2, t3, t4 = st.tabs(["🎵 ZAPISY", "🏠 KONFIGURACJA DINERA", "📊 ANALIZA HITÓW", "🍔 LISTA ZAKUPÓW"])

    with t1:
        st.subheader("📻 Rejestracja Operacji")
        c1, c2 = st.columns(2)
        with c1:
            with st.form("f_i", clear_on_submit=True):
                st.write("*🍭 WPŁYWY*")
                t = st.text_input("Źródło")
                k = st.number_input("Kwota", step=10.0)
                if st.form_submit_button("DODAJ"):
                    sh.worksheet("Przychody").append_row([datetime.now().strftime("%Y-%m-%d %H:%M"), t, k])
                    st.cache_data.clear(); st.rerun()
        with c2:
            with st.form("f_e", clear_on_submit=True):
                st.write("*👠 WYDATKI*")
                t = st.text_input("Na co?")
                k = st.number_input("Koszt", step=1.0)
                if st.form_submit_button("ZAPŁAĆ"):
                    sh.worksheet("Wydatki").append_row([datetime.now().strftime("%Y-%m-%d %H:%M"), t, k, "Retro", "Var"])
                    st.cache_data.clear(); st.rerun()

    with t2:
        st.subheader("🏠 Stałe Zobowiązania")
        col_a, col_b = st.columns(2)
        with col_a:
            with st.form("f_fixed"):
                st.write("*Rachunki Stałe (Co miesiąc)*")
                n = st.text_input("Nazwa (np. Czynsz)")
                k = st.number_input("Kwota")
                if st.form_submit_button("ZAPISZ KOSZT"):
                    sh.worksheet("Koszty_Stale").append_row([n, k])
                    st.cache_data.clear(); st.rerun()
            st.write("Twoje stałe rachunki:")
            st.dataframe(df_fix, use_container_width=True)
            
        with col_b:
            with st.form("f_raty"):
                st.write("*Raty i Kredyty (Czasowe)*")
                n = st.text_input("Nazwa (np. Telefon)")
                k = st.number_input("Kwota raty")
                d1 = st.date_input("Kiedy start?")
                d2 = st.date_input("Kiedy koniec?")
                if st.form_submit_button("DODAJ RATĘ"):
                    sh.worksheet("Raty").append_row([n, k, d1.strftime("%Y-%m-%d"), d2.strftime("%Y-%m-%d")])
                    st.cache_data.clear(); st.rerun()
            st.write("Harmonogram rat:")
            st.dataframe(df_rat, use_container_width=True)

    with t3:
        st.subheader("📊 Jukebox History")
        months = {1: "STYCZEŃ", 2: "LUTY", 3: "MARZEC", 4: "KWIECIEŃ", 5: "MAJ", 6: "CZERWIEC", 7: "LIPIEC", 8: "SIERPIEŃ", 9: "WRZESIEŃ", 10: "PAŹDZIERNIK", 11: "LISTOPAD", 12: "GRUDZIEŃ"}
        c_sel1, c_sel2 = st.columns(2)
        sy = c_sel1.selectbox("Rok", [2026, 2025])
        sm = c_sel2.selectbox("Miesiąc", range(1, 13), format_func=lambda x: months[x], index=today_m-1)
        
        df_l, _ = generate_ledger(sy, sm)
        st.dataframe(df_l.style.format({"Zmiana": "{:,.2f} $", "Saldo": "{:,.2f} $"}), use_container_width=True, hide_index=True)

    with t4:
        st.subheader("🛒 Zaopatrzenie")
        if not df_shp.empty:
            st.write(df_shp["Produkt"].tolist())
        if st.button("WYCZYŚĆ LISTĘ"):
            sh.worksheet("Zakupy").clear(); sh.worksheet("Zakupy").append_row(["Data", "Produkt"])
            st.cache_data.clear(); st.rerun()

    with st.sidebar:
        st.markdown("<h2 style='color: white;'>💎 SEJF</h2>", unsafe_allow_html=True)
        st.metric("OSZCZĘDNOŚCI", f"{s_sav:,.2f} $")
        if st.button("🚜 ZRÓB ŻNIWA (DO SEJFU)"):
            sh.worksheet("Oszczednosci").update_acell('A2', str(s_sav + current_bal))
            st.balloons(); st.cache_data.clear(); time.sleep(1); st.rerun()
