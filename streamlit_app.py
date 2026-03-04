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
            .login-box { 
                text-align: center; padding: 50px; background-color: #fefae0; 
                border: 10px solid #d62828; border-radius: 20px; 
                box-shadow: 15px 15px 0px #003049; margin-top: 50px;
            }
            </style>
            <div class='login-box'>
                <h1 style='color: #d62828; font-family: "Pacifico", cursive;'>🎵 Jukebox Login</h1>
                <p style='color: #003049; font-weight: bold;'>Wprowadź klucz, aby uruchomić Diner</p>
            </div>
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
    # --- 3. PEŁNY STYL RETRO DINER (CSS) ---
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Pacifico&family=Bungee+Inline&family=Montserrat:wght@400;700&display=swap');
        
        .stApp { 
            background-color: #a2d2ff; 
            background-image: radial-gradient(#d62828 20%, transparent 20%), radial-gradient(#ffffff 15%, transparent 16%);
            background-size: 60px 60px;
            font-family: 'Montserrat', sans-serif;
        }

        div[data-testid="stForm"], .stDataEditor, div[data-testid="stDataFrameResizerContainer"] {
            background-color: #fefae0 !important; 
            border: 6px solid #003049 !important;
            border-radius: 20px !important;
            padding: 20px !important;
            box-shadow: 10px 10px 0px #d62828 !important;
        }

        h1 { 
            color: #ffffff !important; font-family: 'Pacifico', cursive !important; font-size: 4.5em !important; 
            text-shadow: 5px 5px 0px #d62828, 10px 10px 0px #003049; text-align: center;
        }

        [data-testid="stMetric"] { 
            background: #fefae0 !important; border: 8px solid #ffafcc !important; 
            border-radius: 50% 10px 50% 10px !important; box-shadow: 12px 12px 0px 0px #d62828 !important; 
        }

        .stButton>button { 
            background: #d62828 !important; color: white !important; font-family: 'Bungee Inline' !important; 
            border-radius: 50px !important; font-size: 20px !important; box-shadow: 5px 5px 0px #003049;
        }

        .stDataFrame { background-color: white !important; border-radius: 10px !important; }
        
        /* Styl nagłówków tabel */
        thead tr th { background-color: #003049 !important; color: white !important; }
        </style>
        """, unsafe_allow_html=True)

    # --- 4. POŁĄCZENIE Z DANYMI ---
    @st.cache_resource
    def get_client():
        creds_dict = st.secrets["gcp_service_account"]
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=scope)
        return gspread.authorize(creds)

    @st.cache_data(ttl=10)
    def load_all_data():
        client = get_client()
        sh = client.open("Budzet_Data")
        sheets = ["Przychody", "Wydatki", "Koszty_Stale", "Raty", "Oszczednosci", "Zakupy"]
        return {name: pd.DataFrame(sh.worksheet(name).get_all_records()) for name in sheets}

    data = load_all_data()
    df_inc = data["Przychody"]
    df_exp = data["Wydatki"]
    df_fix = data["Koszty_Stale"]
    df_rat = data["Raty"]
    df_sav = data["Oszczednosci"]
    df_shp = data["Zakupy"]
    sh = get_client().open("Budzet_Data")

    # Konwersja typów
    for df in [df_inc, df_exp, df_fix, df_rat]:
        df['Kwota'] = pd.to_numeric(df['Kwota'], errors='coerce').fillna(0)
    
    df_inc['Data i Godzina'] = pd.to_datetime(df_inc['Data i Godzina'], errors='coerce')
    df_exp['Data i Godzina'] = pd.to_datetime(df_exp['Data i Godzina'], errors='coerce')
    df_rat['Start'] = pd.to_datetime(df_rat['Start'], errors='coerce', dayfirst=False)
    df_rat['Koniec'] = pd.to_datetime(df_rat['Koniec'], errors='coerce', dayfirst=False)
    
    s_sav = float(str(df_sav.iloc[0,0]).replace(',', '.')) if not df_sav.empty else 0.0

    # --- 5. LOGIKA PEŁNEGO REJESTRU (LEDGER) ---
    def generate_full_ledger(sel_year, sel_month):
        target_date = pd.Timestamp(year=sel_year, month=sel_month, day=1)
        
        # 1. Bilans historyczny (przed wybranym miesiącem)
        inc_hist = df_inc[df_inc['Data i Godzina'] < target_date]['Kwota'].sum()
        exp_hist = df_exp[df_exp['Data i Godzina'] < target_date]['Kwota'].sum()
        
        months_passed = (target_date.year - 2026) * 12 + (target_date.month - 1)
        s_800_hist = max(0, months_passed * 1600)
        fix_hist = max(0, months_passed * df_fix['Kwota'].sum())
        
        rat_hist = 0
        if months_passed > 0:
            for m in pd.date_range(start="2026-01-01", periods=months_passed, freq='MS'):
                rat_hist += df_rat[(df_rat['Start'] <= m) & (df_rat['Koniec'] >= m)]['Kwota'].sum()
        
        # Saldo na start miesiąca
        curr_val = inc_hist + s_800_hist - exp_hist - fix_hist - rat_hist - s_sav
        
        ledger = []
        ledger.append({"Data": target_date.strftime("%Y-%m-01"), "Opis": "🛎️ BILANS OTWARCIA (Z POPRZ. MIESIĘCY)", "Zmiana": 0.0, "Saldo": curr_val})
        
        # 2. Operacje stałe wybranego miesiąca (zawsze na początku)
        curr_val += 1600
        ledger.append({"Data": target_date.strftime("%Y-%m-01"), "Opis": "🎁 GOVT 800+ (2x)", "Zmiana": 1600.0, "Saldo": curr_val})
        
        for _, row in df_fix.iterrows():
            curr_val -= row['Kwota']
            ledger.append({"Data": target_date.strftime("%Y-%m-01"), "Opis": f"🏠 KOSZT STAŁY: {row['Nazwa']}", "Zmiana": -row['Kwota'], "Saldo": curr_val})
            
        active_raty = df_rat[(df_rat['Start'] <= target_date) & (df_rat['Koniec'] >= target_date)]
        for _, row in active_raty.iterrows():
            curr_val -= row['Kwota']
            ledger.append({"Data": target_date.strftime("%Y-%m-01"), "Opis": f"💸 RATA: {row['Rata']}", "Zmiana": -row['Kwota'], "Saldo": curr_val})
        
        # 3. Operacje zmienne (Wpływy i Wydatki) z wybranego miesiąca
        mask_inc = (df_inc['Data i Godzina'].dt.month == sel_month) & (df_inc['Data i Godzina'].dt.year == sel_year)
        mask_exp = (df_exp['Data i Godzina'].dt.month == sel_month) & (df_exp['Data i Godzina'].dt.year == sel_year)
        
        this_month_ops = pd.concat([
            df_inc[mask_inc].assign(Type="IN"), 
            df_exp[mask_exp].assign(Type="OUT")
        ]).sort_values('Data i Godzina')
        
        for _, row in this_month_ops.iterrows():
            change = row['Kwota'] if row['Type'] == "IN" else -row['Kwota']
            curr_val += change
            prefix = "💰" if row['Type'] == "IN" else "🛒"
            ledger.append({
                "Data": row['Data i Godzina'].strftime("%Y-%m-%d %H:%M"),
                "Opis": f"{prefix} {row['Nazwa']}",
                "Zmiana": change,
                "Saldo": curr_val
            })
            
        return pd.DataFrame(ledger), curr_val

    # --- 6. DASHBOARD ---
    today_y, today_m = date.today().year, date.today().month
    df_full_ledger, current_bal = generate_full_ledger(today_y, today_m)
    
    col_met1, col_met2 = st.columns(2)
    with col_met1:
        st.metric("DOSTĘPNA KASA", f"{current_bal:,.2f} $")
    with col_met2:
        days_in_m = calendar.monthrange(today_y, today_m)[1]
        days_left = days_in_m - date.today().day + 1
        st.metric("BUDŻET DZIENNY", f"{current_bal/days_left:,.2f} $" if days_left > 0 else "0.00 $")

    # --- 7. ZAKŁADKI ---
    tabs = st.tabs(["🎵 NOWY WPIS", "🏠 USTAWIENIA", "📊 PEŁNA ANALIZA", "🛒 ZAKUPY", "🛠️ EDYCJA BAZY"])

    with tabs[0]:
        c1, c2 = st.columns(2)
        with c1:
            with st.form("f_inc", clear_on_submit=True):
                st.subheader("🍭 WPŁYW")
                n = st.text_input("Nazwa")
                k = st.number_input("Kwota", step=10.0)
                if st.form_submit_button("DODAJ"):
                    sh.worksheet("Przychody").append_row([datetime.now().strftime("%Y-%m-%d %H:%M"), n, k])
                    st.cache_data.clear(); st.rerun()
        with c2:
            with st.form("f_exp", clear_on_submit=True):
                st.subheader("👠 WYDATEK")
                n = st.text_input("Na co?")
                k = st.number_input("Cena", step=1.0)
                if st.form_submit_button("ZAPŁAĆ"):
                    sh.worksheet("Wydatki").append_row([datetime.now().strftime("%Y-%m-%d %H:%M"), n, k, "Retro", "Var"])
                    st.cache_data.clear(); st.rerun()

    with tabs[1]:
        ca, cb = st.columns(2)
        with ca:
            with st.form("f_fix"):
                st.subheader("Stałe Rachunki")
                n = st.text_input("Nazwa")
                k = st.number_input("Kwota")
                if st.form_submit_button("ZAPISZ"):
                    sh.worksheet("Koszty_Stale").append_row([n, k])
                    st.cache_data.clear(); st.rerun()
            st.dataframe(df_fix, use_container_width=True)
        with cb:
            with st.form("f_rat"):
                st.subheader("Raty")
                n = st.text_input("Nazwa")
                k = st.number_input("Rata")
                s = st.date_input("Start")
                e = st.date_input("Koniec")
                if st.form_submit_button("DODAJ"):
                    sh.worksheet("Raty").append_row([n, k, s.strftime("%Y-%m-%d"), e.strftime("%Y-%m-%d")])
                    st.cache_data.clear(); st.rerun()
            st.dataframe(df_rat, use_container_width=True)

    with tabs[2]:
        st.subheader("📊 Pełny Wyciąg z Jukeboxa")
        col_s1, col_s2 = st.columns(2)
        sy = col_s1.selectbox("Rok", [2026, 2025])
        sm = col_s2.selectbox("Miesiąc", range(1, 13), index=today_m-1, format_func=lambda x: calendar.month_name[x])
        
        res_df, _ = generate_full_ledger(sy, sm)
        
        # Wyświetlanie tabeli z kolorowaniem
        def color_change(val):
            color = 'green' if val > 0 else 'red' if val < 0 else 'black'
            return f'color: {color}; font-weight: bold'

        st.dataframe(
            res_df.style.applymap(color_change, subset=['Zmiana']).format({"Zmiana": "{:,.2f} $", "Saldo": "{:,.2f} $"}),
            use_container_width=True, hide_index=True
        )
        
        fig = px.line(res_df, x="Data", y="Saldo", title=f"Trend Salda w czasie")
        fig.update_traces(line_color='#d62828', mode='lines+markers')
        st.plotly_chart(fig, use_container_width=True)

    with tabs[3]:
        st.subheader("🛒 Lista Zakupów")
        with st.form("f_shop", clear_on_submit=True):
            item = st.text_input("Co kupić?")
            if st.form_submit_button("DODAJ"):
                sh.worksheet("Zakupy").append_row([datetime.now().strftime("%Y-%m-%d"), item])
                st.cache_data.clear(); st.rerun()
        st.table(df_shp["Produkt"])
        if st.button("WYCZYŚĆ LISTĘ"):
            w = sh.worksheet("Zakupy")
            w.clear(); w.append_row(["Data", "Produkt"])
            st.cache_data.clear(); st.rerun()

    with tabs[4]:
        st.subheader("🛠️ Panel Administracyjny")
        target = st.selectbox("Wybierz tabelę do edycji", ["Przychody", "Wydatki", "Koszty_Stale", "Raty"])
        # Pobierz świeże dane bez cache dla edytora
        raw_sh = get_client().open("Budzet_Data").worksheet(target)
        raw_df = pd.DataFrame(raw_sh.get_all_records())
        
        updated = st.data_editor(raw_df, num_rows="dynamic", use_container_width=True)
        
        if st.button("ZAPISZ ZMIANY W BAZIE"):
            raw_sh.clear()
            data_to_save = [updated.columns.values.tolist()] + updated.fillna("").values.tolist()
            raw_sh.update(data_to_save)
            st.success("Zapisano!")
            st.cache_data.clear(); time.sleep(1); st.rerun()

    with st.sidebar:
        st.markdown("<h2 style='color: white;'>💎 SEJF</h2>", unsafe_allow_html=True)
        st.metric("OSZCZĘDNOŚCI", f"{s_sav:,.2f} $")
        if st.button("🚜 ZRÓB ŻNIWA (DO SEJFU)"):
            if current_bal > 0:
                sh.worksheet("Oszczednosci").update_acell('A2', str(s_sav + current_bal))
                st.balloons(); st.cache_data.clear(); time.sleep(1); st.rerun()
