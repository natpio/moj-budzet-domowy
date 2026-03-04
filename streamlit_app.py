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

# --- 2. LOGOWANIE (SYSTEM JUKEBOX) ---
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
                <p style='color: #003049; font-weight: bold;'>Włącz zasilanie, aby sprawdzić stan kasy</p>
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

        /* Formularze i kontenery danych */
        div[data-testid="stForm"], .stDataEditor, div[data-testid="stDataFrameResizerContainer"], .stTable {
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

        /* Metryki */
        [data-testid="stMetric"] { 
            background: #fefae0 !important; border: 8px solid #ffafcc !important; 
            border-radius: 50% 10px 50% 10px !important; box-shadow: 12px 12px 0px 0px #d62828 !important; 
        }
        [data-testid="stMetricValue"] div { color: #d62828 !important; font-family: 'Pacifico', cursive !important; }

        /* Przyciski */
        .stButton>button { 
            background: #d62828 !important; color: white !important; font-family: 'Bungee Inline' !important; 
            border-radius: 50px !important; font-size: 20px !important; box-shadow: 5px 5px 0px #003049;
        }

        /* Sidebar */
        [data-testid="stSidebar"] { background: #ffafcc !important; border-right: 8px solid #d62828 !important; }

        /* Tabele */
        .stDataFrame { background-color: white !important; border-radius: 10px !important; }
        </style>
        """, unsafe_allow_html=True)

    # --- 4. KOMUNIKACJA Z GOOGLE SHEETS ---
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

    # Pobieranie danych do pamięci
    data_dict = load_all_data()
    df_inc = data_dict["Przychody"]
    df_exp = data_dict["Wydatki"]
    df_fix = data_dict["Koszty_Stale"]
    df_rat = data_dict["Raty"]
    df_sav = data_dict["Oszczednosci"]
    df_shp = data_dict["Zakupy"]
    sh = get_client().open("Budzet_Data")

    # Przygotowanie typów danych
    for df in [df_inc, df_exp, df_fix, df_rat]:
        df['Kwota'] = pd.to_numeric(df['Kwota'], errors='coerce').fillna(0)
    
    df_inc['Data i Godzina'] = pd.to_datetime(df_inc['Data i Godzina'], errors='coerce')
    df_exp['Data i Godzina'] = pd.to_datetime(df_exp['Data i Godzina'], errors='coerce')
    df_rat['Start'] = pd.to_datetime(df_rat['Start'], errors='coerce')
    df_rat['Koniec'] = pd.to_datetime(df_rat['Koniec'], errors='coerce')
    
    # Stan oszczędności (z komórki A2 arkusza Oszczednosci)
    s_sav = float(str(df_sav.iloc[0,0]).replace(',', '.')) if not df_sav.empty else 0.0

    # --- 5. LOGIKA PEŁNEJ ANALIZY (LEDGER) ---
    def generate_full_ledger(sel_year, sel_month):
        target_date = pd.Timestamp(year=sel_year, month=sel_month, day=1)
        last_day = calendar.monthrange(sel_year, sel_month)[1]
        end_of_month = pd.Timestamp(year=sel_year, month=sel_month, day=last_day, hour=23, minute=59)
        
        # Obliczenie bilansu historycznego (wszystko przed 1-szym dniem wybranego miesiąca)
        inc_h = df_inc[df_inc['Data i Godzina'] < target_date]['Kwota'].sum()
        exp_h = df_exp[df_exp['Data i Godzina'] < target_date]['Kwota'].sum()
        
        # Stałe historyczne (800+, Rachunki, Raty) liczone od startu systemu (zakładamy styczeń 2026)
        start_sys = pd.Timestamp(year=2026, month=1, day=1)
        m_diff = (target_date.year - start_sys.year) * 12 + (target_date.month - start_sys.month)
        
        fix_h = max(0, m_diff * df_fix['Kwota'].sum())
        gov_h = max(0, m_diff * 1600) # 2x 800+
        rat_h = 0
        if m_diff > 0:
            for m in pd.date_range(start=start_sys, periods=m_diff, freq='MS'):
                rat_h += df_rat[(df_rat['Start'] <= m) & (df_rat['Koniec'] >= m)]['Kwota'].sum()
        
        # Saldo początkowe portfela (Przychody - Wydatki - Stałe - Raty - Sejf)
        curr_val = inc_h + gov_h - exp_h - fix_h - rat_h - s_sav
        
        ledger = []
        ledger.append({"Data": target_date.strftime("%Y-%m-%d"), "Opis": "🛎️ BILANS OTWARCIA", "Zmiana": 0.0, "Saldo": curr_val})
        
        # Operacje automatyczne na start miesiąca
        curr_val += 1600
        ledger.append({"Data": target_date.strftime("%Y-%m-01"), "Opis": "🎁 GOVT 800+ (2x)", "Zmiana": 1600.0, "Saldo": curr_val})
        
        for _, row in df_fix.iterrows():
            curr_val -= row['Kwota']
            ledger.append({"Data": target_date.strftime("%Y-%m-01"), "Opis": f"🏠 STAŁY: {row['Nazwa']}", "Zmiana": -row['Kwota'], "Saldo": curr_val})
            
        active_raty = df_rat[(df_rat['Start'] <= target_date) & (df_rat['Koniec'] >= target_date)]
        for _, row in active_raty.iterrows():
            curr_val -= row['Kwota']
            ledger.append({"Data": target_date.strftime("%Y-%m-01"), "Opis": f"💸 RATA: {row['Rata']}", "Zmiana": -row['Kwota'], "Saldo": curr_val})
        
        # --- KLUCZOWE: POBIERANIE WSZYSTKICH OPERACJI ZMIENNYCH ---
        m_inc = df_inc[(df_inc['Data i Godzina'] >= target_date) & (df_inc['Data i Godzina'] <= end_of_month)].copy()
        m_exp = df_exp[(df_exp['Data i Godzina'] >= target_date) & (df_exp['Data i Godzina'] <= end_of_month)].copy()
        
        m_inc['T'] = 'IN'; m_exp['T'] = 'OUT'
        combined_ops = pd.concat([m_inc, m_exp]).sort_values('Data i Godzina')
        
        for _, row in combined_ops.iterrows():
            change = row['Kwota'] if row['T'] == 'IN' else -row['Kwota']
            curr_val += change
            icon = "💰" if row['T'] == 'IN' else "🛒"
            ledger.append({
                "Data": row['Data i Godzina'].strftime("%Y-%m-%d %H:%M"),
                "Opis": f"{icon} {row['Nazwa']}",
                "Zmiana": change,
                "Saldo": curr_val
            })
            
        return pd.DataFrame(ledger), curr_val

    # --- 6. INTERFEJS GŁÓWNY ---
    st.markdown("<h1>Diner Budget 1960</h1>", unsafe_allow_html=True)
    
    today_y, today_m = date.today().year, date.today().month
    df_ledger, current_total_bal = generate_full_ledger(today_y, today_m)
    
    c_m1, c_m2 = st.columns(2)
    with c_m1:
        st.metric("DOSTĘPNA GOTÓWKA", f"{current_total_bal:,.2f} $")
    with c_m2:
        days_left = calendar.monthrange(today_y, today_m)[1] - date.today().day + 1
        st.metric("BUDŻET DZIENNY", f"{current_total_bal/days_left:,.2f} $" if days_left > 0 else "0.00 $")

    tabs = st.tabs(["🎵 WPISY", "🏠 KONFIGURACJA", "📊 ANALIZA HITÓW", "🍔 ZAKUPY", "🛠️ BAZA DANYCH"])

    with tabs[0]:
        c1, c2 = st.columns(2)
        with c1:
            with st.form("f_inc", clear_on_submit=True):
                st.subheader("🍭 PRZYCHÓD")
                n = st.text_input("Źródło")
                k = st.number_input("Kwota", step=10.0)
                if st.form_submit_button("DODAJ"):
                    sh.worksheet("Przychody").append_row([datetime.now().strftime("%Y-%m-%d %H:%M"), n, k])
                    st.cache_data.clear(); st.rerun()
        with c2:
            with st.form("f_exp", clear_on_submit=True):
                st.subheader("👠 WYDATEK")
                n = st.text_input("Na co?")
                k = st.number_input("Koszt", step=1.0)
                if st.form_submit_button("ZAPŁAĆ"):
                    sh.worksheet("Wydatki").append_row([datetime.now().strftime("%Y-%m-%d %H:%M"), n, k, "Retro", "Zmienne"])
                    st.cache_data.clear(); st.rerun()

    with tabs[1]:
        ca, cb = st.columns(2)
        with ca:
            with st.form("f_fix"):
                st.subheader("Rachunki Stałe")
                n = st.text_input("Nazwa")
                k = st.number_input("Kwota miesięczna")
                if st.form_submit_button("ZAPISZ"):
                    sh.worksheet("Koszty_Stale").append_row([n, k])
                    st.cache_data.clear(); st.rerun()
            st.dataframe(df_fix, use_container_width=True)
        with cb:
            with st.form("f_rat"):
                st.subheader("Harmonogram Rat")
                n = st.text_input("Nazwa raty")
                k = st.number_input("Rata")
                s = st.date_input("Kiedy start?")
                e = st.date_input("Kiedy koniec?")
                if st.form_submit_button("DODAJ RATĘ"):
                    sh.worksheet("Raty").append_row([n, k, s.strftime("%Y-%m-%d"), e.strftime("%Y-%m-%d")])
                    st.cache_data.clear(); st.rerun()
            st.dataframe(df_rat, use_container_width=True)

    with tabs[2]:
        st.subheader("📊 Pełny Rejestr Operacji")
        col_s1, col_s2 = st.columns(2)
        sel_y = col_s1.selectbox("Rok", [2026, 2025])
        sel_m = col_s2.selectbox("Miesiąc", range(1, 13), index=today_m-1, format_func=lambda x: calendar.month_name[x])
        
        res_df, _ = generate_full_ledger(sel_y, sel_m)
        
        st.dataframe(
            res_df.style.format({"Zmiana": "{:,.2f} $", "Saldo": "{:,.2f} $"}),
            use_container_width=True, hide_index=True
        )
        
        fig = px.area(res_df, x=range(len(res_df)), y="Saldo", title="Płynność finansowa (dzień po dniu)")
        fig.update_traces(line_color='#d62828', fillcolor='rgba(214, 40, 40, 0.2)')
        st.plotly_chart(fig, use_container_width=True)

    with tabs[3]:
        with st.form("f_shop", clear_on_submit=True):
            it = st.text_input("Dopisz do listy zakupów")
            if st.form_submit_button("DODAJ"):
                sh.worksheet("Zakupy").append_row([datetime.now().strftime("%Y-%m-%d"), it])
                st.cache_data.clear(); st.rerun()
        st.table(df_shp["Produkt"])
        if st.button("WYCZYŚĆ LISTĘ ZAKUPÓW"):
            w = sh.worksheet("Zakupy")
            w.clear(); w.append_row(["Data", "Produkt"])
            st.cache_data.clear(); st.rerun()

    with tabs[4]:
        st.subheader("🛠️ Panel Edytora (Naprawianie błędów)")
        target = st.selectbox("Wybierz tabelę", ["Przychody", "Wydatki", "Koszty_Stale", "Raty"])
        raw_sh = get_client().open("Budzet_Data").worksheet(target)
        raw_df = pd.DataFrame(raw_sh.get_all_records())
        
        updated_df = st.data_editor(raw_df, num_rows="dynamic", use_container_width=True)
        
        if st.button("ZAPISZ ZMIANY W GOOGLE SHEETS"):
            raw_sh.clear()
            final_data = [updated_df.columns.values.tolist()] + updated_df.fillna("").values.tolist()
            raw_sh.update(final_data)
            st.success("Baza danych zaktualizowana!")
            st.cache_data.clear(); time.sleep(1); st.rerun()

    with st.sidebar:
        st.markdown("<h2 style='color: white;'>💎 SEJF</h2>", unsafe_allow_html=True)
        st.metric("W SEJFIE", f"{s_sav:,.2f} $")
        st.divider()
        if st.button("🚜 ZRÓB ŻNIWA (PRZELEJ SALDO DO SEJFU)"):
            if current_total_bal > 0:
                sh.worksheet("Oszczednosci").update_acell('A2', str(s_sav + current_total_bal))
                st.balloons(); st.cache_data.clear(); time.sleep(1); st.rerun()
            else:
                st.error("Brak środków do przelania!")
