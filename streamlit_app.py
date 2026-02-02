import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
from google.oauth2 import service_account
from datetime import datetime, date
import calendar
import time

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Ranczo Finansowe 2026", layout="wide", page_icon="💖")

# --- FUNKCJA LOGOWANIA ---
def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["credentials"]["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.markdown("<h2 style='text-align: center; color: #ff4081; font-family: \"Dancing Script\", cursive;'>🌹 Witaj w Miłosnym Sejfie. Podaj hasło:</h2>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            st.text_input("Klucz do serca", type="password", on_change=password_entered, key="password")
            if "password_correct" in st.session_state and not st.session_state["password_correct"]:
                st.error("❌ Zły klucz! Serce pozostaje zamknięte.")
        return False
    return True

if check_password():
    # --- ULTRA WALENTYNKOWA STYLIZACJA + ANIMOWANE TŁO ---
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Dancing+Script:wght@700&family=Great+Vibes&display=swap');

        /* Główne tło z gradientem */
        .stApp {
            background: linear-gradient(135deg, #ff9a9e 0%, #fecfef 99%, #fecfef 100%);
        }

        /* Animacja spadających serduszek w tle */
        @keyframes heartFade {
            0% { opacity: 0; transform: translateY(0) rotate(0deg); }
            50% { opacity: 0.8; }
            100% { opacity: 0; transform: translateY(-1000px) rotate(360deg); }
        }

        .stApp::before {
            content: '❤️';
            position: fixed;
            bottom: -100px;
            left: 10%;
            font-size: 20px;
            animation: heartFade 10s infinite linear;
            z-index: -1;
        }

        /* Karty metryk - stylizacja 'Love Letter' */
        [data-testid="stMetric"] { 
            background: rgba(255, 255, 255, 0.8) !important; 
            border: 3px solid #ff4f81 !important; 
            border-radius: 20px !important;
            box-shadow: 0 8px 32px 0 rgba(255, 79, 129, 0.3) !important;
            backdrop-filter: blur(4px);
            -webkit-backdrop-filter: blur(4px);
        }

        [data-testid="stMetricLabel"] p { 
            color: #ad1457 !important; 
            font-family: 'Dancing Script', cursive !important;
            font-size: 26px !important;
            letter-spacing: 1px;
        }

        [data-testid="stMetricValue"] div { 
            color: #d81b60 !important; 
            font-family: 'Great Vibes', cursive !important;
            font-size: 48px !important;
        }

        /* Nagłówki */
        h1, h2 { 
            color: #ffffff !important; 
            font-family: 'Great Vibes', cursive !important;
            font-size: 70px !important;
            text-shadow: 3px 3px 6px rgba(173, 20, 87, 0.5);
            text-align: center;
        }

        /* Przyciski w stylu 'Sweetheart' */
        .stButton>button { 
            background: #ff4f81 !important;
            background: linear-gradient(145deg, #ff558b, #e64774) !important;
            color: white !important; 
            border-radius: 50px !important;
            border: 2px solid #ffffff !important;
            font-family: 'Dancing Script', cursive !important;
            font-size: 22px !important;
            padding: 10px 24px !important;
            box-shadow: 4px 4px 10px rgba(0,0,0,0.1) !important;
        }

        .stButton>button:hover {
            transform: scale(1.05);
            background: #ffffff !important;
            color: #ff4f81 !important;
            border: 2px solid #ff4f81 !important;
        }

        /* Formularze i Expander */
        [data-testid="stExpander"], .stForm {
            background-color: rgba(255, 255, 255, 0.9) !important;
            border-radius: 20px !important;
            border: 2px solid #f8bbd0 !important;
        }

        /* Tabs */
        .stTabs [data-baseweb="tab"] {
            font-family: 'Dancing Script', cursive !important;
            font-size: 20px !important;
            color: #ffffff !important;
        }
        
        /* Sidebar */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #f8bbd0 0%, #fce4ec 100%) !important;
        }

        /* Ukrycie dekoracji Streamlit */
        header {background: transparent !important;}
        </style>
        """, unsafe_allow_html=True)

    # --- POŁĄCZENIE API ---
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
        names = ["Przychody", "Wydatki", "Koszty_Stale", "Raty", "Oszczednosci", "Zakupy", "Zadania", "Planowanie"]
        data = {}
        for name in names:
            data[name] = pd.DataFrame(sh.worksheet(name).get_all_records())
            time.sleep(0.5)
        return data

    def get_now(): return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        all_d = load_all_data()
        df_inc, df_exp, df_fix, df_rat, df_sav, df_shp, df_tsk, df_pla = [all_d[n] for n in ["Przychody", "Wydatki", "Koszty_Stale", "Raty", "Oszczednosci", "Zakupy", "Zadania", "Planowanie"]]
    except:
        st.error("🏹 Amor zgubił strzałę. Odśwież stronę."); st.stop()

    # --- LOGIKA FILTROWANIA (CZYSTA KARTA CO MIESIĄC) ---
    today = date.today()
    current_month_str = today.strftime("%Y-%m")
    dni_m = calendar.monthrange(today.year, today.month)[1] - today.day + 1
    p800 = 1600 

    # Filtry Dashboardu
    df_inc_m = df_inc[df_inc['Data i Godzina'].astype(str).str.contains(current_month_str, na=False)].copy() if not df_inc.empty else pd.DataFrame()
    df_exp_m = df_exp[df_exp['Data i Godzina'].astype(str).str.contains(current_month_str, na=False)].copy() if not df_exp.empty else pd.DataFrame()

    # Raty
    df_rat_active = pd.DataFrame()
    suma_rat = 0
    if not df_rat.empty:
        df_rat['Start'] = pd.to_datetime(df_rat['Start'])
        df_rat['Koniec'] = pd.to_datetime(df_rat['Koniec'])
        mask = (df_rat['Start'] <= pd.Timestamp(today)) & (df_rat['Koniec'] >= pd.Timestamp(today))
        df_rat_active = df_rat[mask].copy()
        suma_rat = df_rat_active['Kwota'].sum()

    inc_total = (df_inc_m['Kwota'].sum() if not df_inc_m.empty else 0) + p800
    exp_total = (df_exp_m['Kwota'].sum() if not df_exp_m.empty else 0) + (df_fix['Kwota'].sum() if not df_fix.empty else 0) + suma_rat
    balance = inc_total - exp_total
    daily = balance / dni_m if dni_m > 0 else balance

    # --- SIDEBAR (SEJF) ---
    with st.sidebar:
        st.markdown("<h1 style='color: #ad1457 !important;'>💖 SEJF</h1>", unsafe_allow_html=True)
        client = get_client()
        sh = client.open("Budzet_Data")
        ws_sav = sh.worksheet("Oszczednosci")
        sav_val = float(str(ws_sav.acell('A2').value).replace(',', '.'))
        st.metric("ZŁOTO W SERCU", f"{sav_val:,.2f} PLN")
        
        st.divider()
        with st.expander("🎁 ZARZĄDZAJ SKABCEM"):
            amt_s = st.number_input("Ile dukatów?", min_value=0.0, step=10.0, key="amt_sidebar")
            c_in, c_out = st.columns(2)
            if c_in.button("WPŁAĆ"):
                if amt_s > 0:
                    ws_sav.update_acell('A2', str(sav_val + amt_s))
                    sh.worksheet("Wydatki").append_row([get_now(), "ZAMROŻONE: Wpłata do Sejfu", amt_s, "Inne", "Oszczędności"])
                    st.success(f"Dodano {amt_s} PLN do miłości!")
                    st.cache_data.clear(); time.sleep(1); st.rerun()
            if c_out.button("POBIERZ"):
                if amt_s > 0:
                    ws_sav.update_acell('A2', str(sav_val - amt_s))
                    sh.worksheet("Przychody").append_row([get_now(), "Wypłata z Sejfu", amt_s])
                    st.success(f"Pobrano {amt_s} PLN z zapasów!")
                    st.cache_data.clear(); time.sleep(1); st.rerun()

        st.divider()
        if st.button("🏹 ZAMKNIJ MIESIĄC"):
            new_sav = sav_val + balance
            ws_sav.update_acell('A2', str(new_sav))
            st.balloons()
            st.success(f"Miesiąc zamknięty! {balance:.2f} PLN bezpieczne.")
            st.cache_data.clear(); time.sleep(1); st.rerun()

    # --- DASHBOARD ---
    st.markdown("<h1>📜 MIŁOSNA KSIĘGA RACHUNKOWA</h1>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    c1.metric("💰 PORTFEL (TEN MIESIĄC)", f"{balance:,.2f} PLN")
    c2.metric("🌹 NA KAŻDY DZIEŃ", f"{daily:,.2f} PLN")

    h_inc, h_exp = st.columns(2)
    with h_inc:
        st.metric("📈 WPŁYWY", f"{inc_total:,.2f} PLN")
        with st.expander("🔍 Szczegóły Twoich dochodów"):
            if not df_inc_m.empty:
                st.table(df_inc_m[["Nazwa", "Kwota"]])
            else:
                st.info("Cisza przed miłosną burzą (brak wpływów).")

    with h_exp:
        st.metric("📉 WYDATKI", f"{exp_total:,.2f} PLN")
        with st.expander("🔍 Pełna lista kosztów"):
            e_all = pd.concat([
                df_exp_m[["Nazwa", "Kwota"]] if not df_exp_m.empty else pd.DataFrame(),
                df_fix[["Nazwa", "Kwota"]] if not df_fix.empty else pd.DataFrame(),
                df_rat_active[["Rata", "Kwota"]].rename(columns={"Rata": "Nazwa"}) if not df_rat_active.empty else pd.DataFrame()
            ], ignore_index=True)
            if not e_all.empty:
                st.table(e_all)
            else:
                st.info("Czysta karta w tym miesiącu!")

    # --- ZAKŁADKI ---
    tabs = st.tabs(["🎀 Wpisy", "🏠 Stałe & Raty", "📅 Plany Marzeń", "🛒 Listy"])

    with tabs[0]:
        ci, ce = st.columns(2)
        with ci:
            with st.form("f_inc", clear_on_submit=True):
                st.subheader("➕ Przychód")
                ni, ki = st.text_input("Skąd?"), st.number_input("Kwota", key="f_inc_k")
                if st.form_submit_button("DODAJ DO SERCA"):
                    sh.worksheet("Przychody").append_row([get_now(), ni, ki])
                    st.cache_data.clear(); st.rerun()
        with ce:
            with st.form("f_exp", clear_on_submit=True):
                st.subheader("➖ Wydatek")
                ne, ke = st.text_input("Na co?"), st.number_input("Kwota", key="f_exp_k")
                ka = st.selectbox("Kategoria", ["Jedzenie", "Dom", "Transport", "Rozrywka", "Inne"])
                if st.form_submit_button("ODJMIJ"):
                    sh.worksheet("Wydatki").append_row([get_now(), ne, ke, ka, "Zmienny"])
                    st.cache_data.clear(); st.rerun()
        
        st.divider()
        st.subheader("📝 Edycja bieżących wpisów (Czysta karta)")
        df_exp_m["USUŃ"] = False
        ed_e = st.data_editor(df_exp_m, num_rows="dynamic", use_container_width=True, key="ed_wpisy_final")
        
        if st.button("Zapisz zmiany w historii"):
            df_hist = df_exp[~df_exp['Data i Godzina'].astype(str).str.contains(current_month_str, na=False)]
            cl_current = ed_e[ed_e["USUŃ"] == False].drop(columns=["USUŃ"])
            final_df = pd.concat([df_hist, cl_current], ignore_index=True)
            ws = sh.worksheet("Wydatki")
            ws.clear(); ws.append_row(["Data i Godzina", "Nazwa", "Kwota", "Kategoria", "Typ"])
            if not final_df.empty: ws.append_rows(final_df.values.tolist())
            st.cache_data.clear(); st.rerun()

    with tabs[1]:
        cf, cr = st.columns(2)
        with cf:
            with st.form("f_fix"):
                st.subheader("🏠 Stałe Opłaty")
                nf, kf = st.text_input("Opłata"), st.number_input("Kwota", key="f_fix_k")
                if st.form_submit_button("ZAPISZ"):
                    sh.worksheet("Koszty_Stale").append_row([get_now(), nf, kf])
                    st.cache_data.clear(); st.rerun()
            df_fix["USUŃ"] = False
            ed_f = st.data_editor(df_fix, use_container_width=True, key="ed_stale_final")
            if st.button("Zapisz zmiany w Stałych"):
                cl_f = ed_f[ed_f["USUŃ"] == False].drop(columns=["USUŃ"])
                ws_f = sh.worksheet("Koszty_Stale")
                ws_f.clear(); ws_f.append_row(["Data i Godzina", "Nazwa", "Kwota"])
                if not cl_f.empty: ws_f.append_rows(cl_f.values.tolist())
                st.cache_data.clear(); st.rerun()
        with cr:
            with st.form("f_rat"):
                st.subheader("🗓️ Raty")
                nr, kr = st.text_input("Rata"), st.number_input("Kwota", key="f_rat_k")
                ds, de = st.date_input("Start"), st.date_input("Koniec")
                if st.form_submit_button("DODAJ RATĘ"):
                    sh.worksheet("Raty").append_row([nr, kr, str(ds), str(de)])
                    st.cache_data.clear(); st.rerun()
            df_rat["USUŃ"] = False
            ed_r = st.data_editor(df_rat, use_container_width=True, key="ed_raty_final")
            if st.button("Zapisz zmiany w Ratach"):
                cl_r = ed_r[ed_r["USUŃ"] == False].drop(columns=["USUŃ"])
                if not cl_r.empty:
                    for c in ['Start', 'Koniec']: cl_r[c] = pd.to_datetime(cl_r[c]).dt.strftime('%Y-%m-%d')
                ws_r = sh.worksheet("Raty")
                ws_r.clear(); ws_r.append_row(["Rata", "Kwota", "Start", "Koniec"])
                if not cl_r.empty: ws_r.append_rows(cl_r.values.tolist())
                st.cache_data.clear(); st.rerun()

    with tabs[2]:
        with st.form("f_pla"):
            st.subheader("📅 Planowanie Marzeń")
            pn, pk = st.text_input("Cel"), st.number_input("Kwota", key="f_pla_k")
            pm = st.selectbox("Miesiąc", ["Styczeń", "Luty", "Marzec", "Kwiecień", "Maj", "Czerwiec", "Lipiec", "Sierpień", "Wrzesień", "Październik", "Listopad", "Grudzień"])
            if st.form_submit_button("ZAPLANUJ"):
                sh.worksheet("Planowanie").append_row([get_now(), pn, pk, pm])
                st.cache_data.clear(); st.rerun()
        df_pla["USUŃ"] = False
        ed_p = st.data_editor(df_pla, use_container_width=True, key="ed_plany_final")
        if st.button("Zaktualizuj Plany"):
            cl_p = ed_p[ed_p["USUŃ"] == False].drop(columns=["USUŃ"])
            ws_p = sh.worksheet("Planowanie")
            ws_p.clear(); ws_p.append_row(["Data i Godzina", "Cel", "Kwota", "Miesiąc"])
            if not cl_p.empty: ws_p.append_rows(cl_p.values.tolist())
            st.cache_data.clear(); st.rerun()

    with tabs[3]:
        cs, ct = st.columns(2)
        with cs:
            st.subheader("🛒 Lista Zakupów")
            with st.form("f_sho"):
                it = st.text_input("Produkt")
                if st.form_submit_button("DODAJ"):
                    sh.worksheet("Zakupy").append_row([get_now(), it])
                    st.cache_data.clear(); st.rerun()
            df_shp["USUŃ"] = False
            ed_s = st.data_editor(df_shp, use_container_width=True, key="ed_zakupy_final")
            if st.button("Usuń wybrane"):
                cl_s = ed_s[ed_s["USUŃ"] == False].drop(columns=["USUŃ"])
                ws_s = sh.worksheet("Zakupy")
                ws_s.clear(); ws_s.append_row(["Data i Godzina", "Produkt"])
                if not cl_s.empty: ws_s.append_rows(cl_s.values.tolist())
                st.cache_data.clear(); st.rerun()
        with ct:
            st.subheader("✅ Miłosne Zadania")
            with st.form("f_tsk"):
                tn, td = st.text_input("Zadanie"), st.date_input("Termin")
                if st.form_submit_button("DODAJ ZADANIE"):
                    sh.worksheet("Zadania").append_row([get_now(), tn, str(td), "Normalny"])
                    st.cache_data.clear(); st.rerun()
            df_tsk["USUŃ"] = False
            ed_t = st.data_editor(df_tsk, use_container_width=True, key="ed_zadania_final")
            if st.button("Ukończ wybrane"):
                cl_t = ed_t[ed_t["USUŃ"] == False].drop(columns=["USUŃ"])
                ws_t = sh.worksheet("Zadania")
                ws_t.clear(); ws_t.append_row(["Data i Godzina", "Zadanie", "Termin", "Priorytet"])
                if not cl_t.empty: ws_t.append_rows(cl_t.values.tolist())
                st.cache_data.clear(); st.rerun()
