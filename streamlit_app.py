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
                <h1 style='color: #d62828; font-family: "Pacifico", cursive; font-size: 3em;'>🎵 Jukebox Login</h1>
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
        
        /* Tło i ogólna czcionka */
        .stApp { 
            background-color: #a2d2ff; 
            background-image: radial-gradient(#d62828 20%, transparent 20%), radial-gradient(#ffffff 15%, transparent 16%);
            background-size: 60px 60px;
            font-family: 'Montserrat', sans-serif;
        }

        /* Formularze i Edytor Danych - Białe tło dla czytelności */
        div[data-testid="stForm"], .stDataEditor, div[data-testid="stDataFrameResizerContainer"] {
            background-color: #fefae0 !important; 
            border: 6px solid #003049 !important;
            border-radius: 20px !important;
            padding: 20px !important;
            box-shadow: 10px 10px 0px #d62828 !important;
        }

        /* Nagłówki */
        h1 { 
            color: #ffffff !important; 
            font-family: 'Pacifico', cursive !important; 
            font-size: 4.5em !important; 
            text-shadow: 5px 5px 0px #d62828, 10px 10px 0px #003049;
            text-align: center;
            margin-bottom: 30px;
        }

        h2, h3 { 
            color: #003049 !important; 
            font-family: 'Bungee Inline', cursive !important; 
            text-transform: uppercase;
        }

        /* Metryki */
        [data-testid="stMetric"] { 
            background: #fefae0 !important; 
            border: 8px solid #ffafcc !important; 
            border-radius: 50% 10px 50% 10px !important; 
            box-shadow: 12px 12px 0px 0px #d62828 !important; 
            padding: 20px !important;
        }
        [data-testid="stMetricValue"] div { 
            color: #d62828 !important; 
            font-family: 'Pacifico', cursive !important; 
            font-size: 42px !important; 
        }

        /* Przyciski */
        .stButton>button { 
            background: #d62828 !important; 
            color: white !important; 
            font-family: 'Bungee Inline' !important; 
            border-radius: 50px !important; 
            font-size: 20px !important;
            box-shadow: 5px 5px 0px #003049;
            transition: 0.3s;
        }
        .stButton>button:hover { transform: scale(1.05); background: #003049 !important; }

        /* Sidebar */
        [data-testid="stSidebar"] { 
            background: #ffafcc !important; 
            border-right: 8px solid #d62828 !important; 
        }

        /* Tabele */
        .stDataFrame { background-color: white !important; border-radius: 10px !important; }
        </style>
        """, unsafe_allow_html=True)

    # --- 4. POŁĄCZENIE Z DANYMI (GOOGLE SHEETS) ---
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
    df_inc = data["Przychody"]
    df_exp = data["Wydatki"]
    df_fix = data["Koszty_Stale"]
    df_rat = data["Raty"]
    df_sav = data["Oszczednosci"]
    df_shp = data["Zakupy"]
    sh = get_client().open("Budzet_Data")

    # Konwersja typów danych
    for df in [df_inc, df_exp, df_fix, df_rat]:
        df['Kwota'] = pd.to_numeric(df['Kwota'], errors='coerce').fillna(0)
    
    df_inc['Data i Godzina'] = pd.to_datetime(df_inc['Data i Godzina'], errors='coerce')
    df_exp['Data i Godzina'] = pd.to_datetime(df_exp['Data i Godzina'], errors='coerce')
    df_rat['Start'] = pd.to_datetime(df_rat['Start'], errors='coerce')
    df_rat['Koniec'] = pd.to_datetime(df_rat['Koniec'], errors='coerce')
    
    s_sav = float(str(df_sav.iloc[0,0]).replace(',', '.')) if not df_sav.empty else 0.0

    # --- 5. LOGIKA HARMONOGRAMU (SALDO + 800+ + RATY) ---
    def generate_ledger(sel_year, sel_month):
        target_date = pd.Timestamp(year=sel_year, month=sel_month, day=1)
        
        # Obliczenia historyczne do otwarcia miesiąca
        inc_before = df_inc[df_inc['Data i Godzina'] < target_date]['Kwota'].sum()
        exp_before = df_exp[df_exp['Data i Godzina'] < target_date]['Kwota'].sum()
        
        months_diff = (target_date.year - 2026) * 12 + (target_date.month - 1)
        s_800_before = max(0, months_diff * 1600) # 2x 800+ co miesiąc
        fix_before = max(0, months_diff * df_fix['Kwota'].sum())
        
        rat_before = 0
        if months_diff > 0:
            for m in pd.date_range(start="2026-01-01", periods=months_diff, freq='MS'):
                rat_before += df_rat[(df_rat['Start'] <= m) & (df_rat['Koniec'] >= m)]['Kwota'].sum()
        
        # Saldo początkowe
        curr_val = inc_before + s_800_before - exp_before - fix_before - rat_before - s_sav
        
        ledger_data = []
        ledger_data.append({"Dzień": "START", "Opis": "BILANS OTWARCIA", "Zmiana": 0.0, "Saldo": curr_val})
        
        # Operacje stałe wybranego miesiąca
        curr_val += 1600
        ledger_data.append({"Dzień": "01", "Opis": "🎁 GOVT 800+ (2x)", "Zmiana": 1600.0, "Saldo": curr_val})
        
        for _, row in df_fix.iterrows():
            curr_val -= row['Kwota']
            ledger_data.append({"Dzień": "01", "Opis": f"🏠 STAŁY: {row['Nazwa']}", "Zmiana": -row['Kwota'], "Saldo": curr_val})
            
        active_raty = df_rat[(df_rat['Start'] <= target_date) & (df_rat['Koniec'] >= target_date)]
        for _, row in active_raty.iterrows():
            curr_val -= row['Kwota']
            ledger_data.append({"Dzień": "01", "Opis": f"💸 RATA: {row['Rata']}", "Zmiana": -row['Kwota'], "Saldo": curr_val})
        
        # Operacje zmienne (wpisywane ręcznie)
        mask_inc = (df_inc['Data i Godzina'].dt.month == sel_month) & (df_inc['Data i Godzina'].dt.year == sel_year)
        mask_exp = (df_exp['Data i Godzina'].dt.month == sel_month) & (df_exp['Data i Godzina'].dt.year == sel_year)
        
        ops = pd.concat([df_inc[mask_inc].assign(T="P"), df_exp[mask_exp].assign(T="W")]).sort_values('Data i Godzina')
        
        for _, row in ops.iterrows():
            ch = row['Kwota'] if row['T'] == "P" else -row['Kwota']
            curr_val += ch
            ledger_data.append({"Dzień": row['Data i Godzina'].strftime("%d"), "Opis": row['Nazwa'], "Zmiana": ch, "Saldo": curr_val})
            
        return pd.DataFrame(ledger_data), curr_val

    # --- 6. INTERFEJS GŁÓWNY ---
    st.markdown("<h1>Diner Budget 1960</h1>", unsafe_allow_html=True)
    
    today_y, today_m = date.today().year, date.today().month
    df_ledger, current_total_bal = generate_ledger(today_y, today_m)
    
    col_met1, col_met2 = st.columns(2)
    with col_met1:
        st.metric("CASH IN PURSE", f"{current_total_bal:,.2f} $")
    with col_met2:
        days_in_m = calendar.monthrange(today_y, today_m)[1]
        days_left = days_in_m - date.today().day + 1
        st.metric("NA DZIEŃ", f"{current_total_bal/days_left:,.2f} $" if days_left > 0 else "---")

    # Zakładki
    t1, t2, t3, t4, t5 = st.tabs(["🎵 ZAPISY", "🏠 KONFIGURACJA", "📊 ANALIZA", "🛒 ZAKUPY", "🛠️ KOREKTA"])

    with t1:
        st.subheader("Dodaj nowe rekordy")
        c1, c2 = st.columns(2)
        with c1:
            with st.form("inc_form", clear_on_submit=True):
                st.write("*🍭 WPŁYWY*")
                n = st.text_input("Nazwa (np. Bonus)")
                k = st.number_input("Kwota", step=10.0)
                if st.form_submit_button("DODAJ DO PORTFELA"):
                    sh.worksheet("Przychody").append_row([datetime.now().strftime("%Y-%m-%d %H:%M"), n, k])
                    st.cache_data.clear(); st.rerun()
        with c2:
            with st.form("exp_form", clear_on_submit=True):
                st.write("*👠 WYDATKI*")
                n = st.text_input("Na co?")
                k = st.number_input("Cena", step=1.0)
                if st.form_submit_button("ZAPŁAĆ"):
                    sh.worksheet("Wydatki").append_row([datetime.now().strftime("%Y-%m-%d %H:%M"), n, k, "Retro", "Var"])
                    st.cache_data.clear(); st.rerun()

    with t2:
        st.subheader("🏠 Diner Setup - Koszty Stałe i Raty")
        cf1, cf2 = st.columns(2)
        with cf1:
            with st.form("fix_form"):
                st.write("*Koszty Stałe (Co miesiąc)*")
                n = st.text_input("Nazwa (np. Czynsz)")
                k = st.number_input("Kwota miesięczna")
                if st.form_submit_button("ZAPISZ KOSZT"):
                    sh.worksheet("Koszty_Stale").append_row([n, k])
                    st.cache_data.clear(); st.rerun()
            st.dataframe(df_fix, use_container_width=True)
        with cf2:
            with st.form("rat_form"):
                st.write("*Raty i Kredyty (Z datami)*")
                n = st.text_input("Nazwa raty")
                k = st.number_input("Kwota raty")
                s = st.date_input("Kiedy start?")
                e = st.date_input("Kiedy koniec?")
                if st.form_submit_button("DODAJ RATĘ"):
                    sh.worksheet("Raty").append_row([n, k, s.strftime("%Y-%m-%d"), e.strftime("%Y-%m-%d")])
                    st.cache_data.clear(); st.rerun()
            st.dataframe(df_rat, use_container_width=True)

    with t3:
        st.subheader("📊 Jukebox Analysis")
        c_s1, c_s2 = st.columns(2)
        sel_y = c_s1.selectbox("Rok", [2026, 2025])
        sel_m = c_s2.selectbox("Miesiąc", range(1, 13), index=today_m-1)
        
        df_l, _ = generate_ledger(sel_y, sel_m)
        st.dataframe(df_l.style.format({"Zmiana": "{:,.2f} $", "Saldo": "{:,.2f} $"}), use_container_width=True, hide_index=True)
        
        fig = px.area(df_l, x=range(len(df_l)), y="Saldo", title="Płynność finansowa")
        fig.update_traces(line_color='#d62828', fillcolor='rgba(214, 40, 40, 0.2)')
        st.plotly_chart(fig, use_container_width=True)

    with t4:
        st.subheader("🛒 Soda Fountain - Lista Zakupów")
        with st.form("shop_form", clear_on_submit=True):
            item = st.text_input("Co kupić?")
            if st.form_submit_button("DODAJ"):
                sh.worksheet("Zakupy").append_row([datetime.now().strftime("%Y-%m-%d"), item])
                st.cache_data.clear(); st.rerun()
        if not df_shp.empty:
            st.table(df_shp["Produkt"])
        if st.button("WYCZYŚĆ LISTĘ ZAKUPÓW"):
            worksheet = sh.worksheet("Zakupy")
            worksheet.clear()
            worksheet.append_row(["Data", "Produkt"])
            st.cache_data.clear(); st.rerun()

    with t5:
        st.subheader("🛠️ Panel Korekty Danych")
        st.warning("Uwaga: Edytujesz bezpośrednio bazę danych w Google Sheets!")
        target = st.selectbox("Wybierz tabelę do poprawy", ["Przychody", "Wydatki", "Koszty_Stale", "Raty"])
        
        # Pobieranie surowych danych dla wybranej tabeli
        edit_worksheet = sh.worksheet(target)
        df_raw = pd.DataFrame(edit_worksheet.get_all_records())
        
        # Interaktywny edytor
        edited_df = st.data_editor(df_raw, num_rows="dynamic", use_container_width=True)
        
        if st.button("ZAPISZ WSZYSTKIE ZMIANY"):
            edit_worksheet.clear()
            # Przygotowanie danych do zapisu (nagłówki + wartości)
            data_to_save = [edited_df.columns.values.tolist()] + edited_df.fillna("").values.tolist()
            edit_worksheet.update(data_to_save)
            st.success("Baza danych zaktualizowana!")
            st.cache_data.clear(); time.sleep(1); st.rerun()

    with st.sidebar:
        st.markdown("<h2 style='color: white;'>💎 THE VAULT</h2>", unsafe_allow_html=True)
        st.metric("OSZCZĘDNOŚCI", f"{s_sav:,.2f} $")
        st.divider()
        if st.button("🚜 ZRÓB ŻNIWA (DO SEJFU)"):
            if current_total_bal > 0:
                nowe_oszczednosci = s_sav + current_total_bal
                sh.worksheet("Oszczednosci").update_acell('A2', str(nowe_oszczednosci))
                st.balloons()
                st.cache_data.clear(); time.sleep(1); st.rerun()
            else:
                st.error("Nie ma czego zbierać, skarbie!")
