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
            .login-box { text-align: center; padding: 50px; background-color: #fefae0; border: 10px solid #d62828; border-radius: 20px; box-shadow: 15px 15px 0px #003049; margin-top: 50px; }
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
    # --- 3. STYLE CSS ---
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Pacifico&family=Bungee+Inline&family=Montserrat:wght@400;700&display=swap');
        .stApp { background-color: #a2d2ff; background-image: radial-gradient(#d62828 20%, transparent 20%), radial-gradient(#ffffff 15%, transparent 16%); background-size: 60px 60px; font-family: 'Montserrat', sans-serif; }
        div[data-testid="stForm"], .stDataEditor { background-color: #fefae0 !important; border: 6px solid #003049 !important; border-radius: 20px !important; padding: 20px !important; box-shadow: 10px 10px 0px #d62828 !important; }
        h1 { color: #ffffff !important; font-family: 'Pacifico', cursive !important; font-size: 4em !important; text-shadow: 4px 4px 0px #d62828; text-align: center; }
        [data-testid="stMetric"] { background: #fefae0 !important; border: 8px solid #ffafcc !important; border-radius: 15px !important; box-shadow: 10px 10px 0px 0px #d62828 !important; }
        .stButton>button { background: #d62828 !important; color: white !important; font-family: 'Bungee Inline' !important; border-radius: 50px !important; }
        </style>
        """, unsafe_allow_html=True)

    # --- 4. POŁĄCZENIE I DANE ---
    @st.cache_resource
    def get_client():
        creds_dict = st.secrets["gcp_service_account"]
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=scope)
        return gspread.authorize(creds)

    @st.cache_data(ttl=5) # Bardzo krótki cache, żeby widzieć zmiany od razu
    def load_raw_data():
        client = get_client()
        sh = client.open("Budzet_Data")
        sheets = ["Przychody", "Wydatki", "Koszty_Stale", "Raty", "Oszczednosci", "Zakupy"]
        return {name: pd.DataFrame(sh.worksheet(name).get_all_records()) for name in sheets}

    data_all = load_raw_data()
    sh_obj = get_client().open("Budzet_Data")

    # Funkcja do czyszczenia dat i kwot (kluczowa dla naprawy błędu "nie pobiera")
    def clean_df(df, date_col=None):
        if df.empty: return df
        if 'Kwota' in df.columns:
            df['Kwota'] = pd.to_numeric(df['Kwota'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
        if date_col and date_col in df.columns:
            df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
        return df

    df_inc = clean_df(data_all["Przychody"], "Data i Godzina")
    df_exp = clean_df(data_all["Wydatki"], "Data i Godzina")
    df_fix = clean_df(data_all["Koszty_Stale"])
    df_rat = clean_df(data_all["Raty"], "Start") # Czyścimy daty rat
    df_rat['Koniec'] = pd.to_datetime(df_rat['Koniec'], errors='coerce')
    
    s_sav = float(str(data_all["Oszczednosci"].iloc[0,0]).replace(',', '.')) if not data_all["Oszczednosci"].empty else 0.0

    # --- 5. LOGIKA ANALIZY (LEDGER) ---
    def generate_full_ledger(sel_year, sel_month):
        target_start = pd.Timestamp(year=sel_year, month=sel_month, day=1)
        target_end = target_start + pd.offsets.MonthEnd(0) + pd.Timedelta(hours=23, minutes=59)
        
        # 1. Obliczamy wszystko CO BYŁO PRZED tym miesiącem (Saldo otwarcia)
        old_inc = df_inc[df_inc['Data i Godzina'] < target_start]['Kwota'].sum()
        old_exp = df_exp[df_exp['Data i Godzina'] < target_start]['Kwota'].sum()
        
        sys_start = pd.Timestamp(year=2026, month=1, day=1)
        m_diff = (target_start.year - sys_start.year) * 12 + (target_start.month - sys_start.month)
        
        old_fix = max(0, m_diff * df_fix['Kwota'].sum())
        old_gov = max(0, m_diff * 1600)
        old_rat = 0
        if m_diff > 0:
            for d in pd.date_range(start=sys_start, periods=m_diff, freq='MS'):
                old_rat += df_rat[(df_rat['Start'] <= d) & (df_rat['Koniec'] >= d)]['Kwota'].sum()
        
        current_val = old_inc + old_gov - old_exp - old_fix - old_rat - s_sav
        
        ledger = []
        ledger.append({"Data": target_start.strftime("%Y-%m-%d"), "Opis": "🛎️ SALDO POCZĄTKOWE", "Zmiana": 0.0, "Saldo": current_val})

        # 2. Operacje stałe wybranego miesiąca
        current_val += 1600
        ledger.append({"Data": target_start.strftime("%Y-%m-01"), "Opis": "🎁 800+ (2x)", "Zmiana": 1600.0, "Saldo": current_val})
        
        for _, r in df_fix.iterrows():
            current_val -= r['Kwota']
            ledger.append({"Data": target_start.strftime("%Y-%m-01"), "Opis": f"🏠 {r['Nazwa']}", "Zmiana": -r['Kwota'], "Saldo": current_val})
            
        active_raty = df_rat[(df_rat['Start'] <= target_start) & (df_rat['Koniec'] >= target_start)]
        for _, r in active_raty.iterrows():
            current_val -= r['Kwota']
            ledger.append({"Data": target_start.strftime("%Y-%m-01"), "Opis": f"💸 RATA: {r['Rata']}", "Zmiana": -r['Kwota'], "Saldo": current_val})

        # 3. POBIERANIE OPERACJI Z PRZYCHODÓW I WYDATKÓW (Kluczowa naprawa)
        m_inc = df_inc[(df_inc['Data i Godzina'] >= target_start) & (df_inc['Data i Godzina'] <= target_end)].copy()
        m_exp = df_exp[(df_exp['Data i Godzina'] >= target_start) & (df_exp['Data i Godzina'] <= target_end)].copy()
        
        if not m_inc.empty: m_inc['Typ'] = 'P'
        if not m_exp.empty: m_exp['Typ'] = 'W'
        
        combined = pd.concat([m_inc, m_exp]).sort_values('Data i Godzina')
        
        for _, row in combined.iterrows():
            val = row['Kwota'] if row['Typ'] == 'P' else -row['Kwota']
            current_val += val
            ico = "💰" if row['Typ'] == 'P' else "🛒"
            ledger.append({
                "Data": row['Data i Godzina'].strftime("%Y-%m-%d %H:%M"),
                "Opis": f"{ico} {row['Nazwa']}",
                "Zmiana": val,
                "Saldo": current_val
            })
            
        return pd.DataFrame(ledger), current_val

    # --- 6. INTERFEJS ---
    st.markdown("<h1>Diner Budget 1960</h1>", unsafe_allow_html=True)
    today = date.today()
    df_final, total_cash = generate_full_ledger(today.year, today.month)
    
    c1, c2 = st.columns(2)
    c1.metric("PORTFEL", f"{total_cash:,.2f} $")
    days_left = calendar.monthrange(today.year, today.month)[1] - today.day + 1
    c2.metric("DZIENNIE", f"{total_cash/days_left:,.2f} $" if days_left > 0 else "0.00 $")

    tabs = st.tabs(["🎵 WPISY", "🏠 SETUP", "📊 ANALIZA", "🛒 LISTA", "🛠️ EDYTOR"])

    with tabs[0]:
        col1, col2 = st.columns(2)
        with col1:
            with st.form("f1", clear_on_submit=True):
                st.subheader("🍭 PRZYCHÓD")
                n = st.text_input("Nazwa")
                k = st.number_input("Kwota", step=1.0)
                if st.form_submit_button("DODAJ"):
                    sh_obj.worksheet("Przychody").append_row([datetime.now().strftime("%Y-%m-%d %H:%M"), n, k])
                    st.cache_data.clear(); st.rerun()
        with col2:
            with st.form("f2", clear_on_submit=True):
                st.subheader("👠 WYDATEK")
                n = st.text_input("Na co?")
                k = st.number_input("Ile", step=1.0)
                if st.form_submit_button("ZAPŁAĆ"):
                    sh_obj.worksheet("Wydatki").append_row([datetime.now().strftime("%Y-%m-%d %H:%M"), n, k, "Retro", "Zmienne"])
                    st.cache_data.clear(); st.rerun()

    with tabs[2]:
        st.subheader("📊 Pełny Rejestr Operacji")
        sy = st.selectbox("Rok", [2026, 2025])
        sm = st.selectbox("Miesiąc", range(1, 13), index=today.month-1, format_func=lambda x: calendar.month_name[x])
        
        month_data, _ = generate_full_ledger(sy, sm)
        st.dataframe(month_data, use_container_width=True, hide_index=True)
        
        fig = px.line(month_data, x=range(len(month_data)), y="Saldo", title="Płynność finansowa")
        st.plotly_chart(fig, use_container_width=True)

    with tabs[4]:
        st.subheader("🛠️ Edycja bezpośrednia")
        t_name = st.selectbox("Tabela", ["Przychody", "Wydatki", "Koszty_Stale", "Raty"])
        raw_sh = sh_obj.worksheet(t_name)
        df_edit = pd.DataFrame(raw_sh.get_all_records())
        updated = st.data_editor(df_edit, num_rows="dynamic", use_container_width=True)
        if st.button("ZAPISZ ZMIANY"):
            raw_sh.clear()
            raw_sh.update([updated.columns.values.tolist()] + updated.fillna("").values.tolist())
            st.success("Gotowe!"); st.cache_data.clear(); time.sleep(1); st.rerun()

    with st.sidebar:
        st.metric("SEJF", f"{s_sav:,.2f} $")
        if st.button("🚜 ŻNIWA"):
            sh_obj.worksheet("Oszczednosci").update_acell('A2', str(s_sav + total_cash))
            st.balloons(); st.cache_data.clear(); time.sleep(1); st.rerun()
