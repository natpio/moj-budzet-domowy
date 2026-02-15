import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
from google.oauth2 import service_account
from datetime import datetime, date
import calendar
import time

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Gospodarstwo Finansowe 2026", layout="wide", page_icon="🌾")

# --- FUNKCJA LOGOWANIA ---
def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["credentials"]["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.markdown("""
            <h2 style='text-align: center; color: #b00000; font-family: "Georgia", serif;'>
                🪗 Witaj w Zagrodzie. Podaj hasło do spichlerza:
            </h2>
            """, unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            st.text_input("Klucz do kłódki", type="password", on_change=password_entered, key="password")
            if "password_correct" in st.session_state and not st.session_state["password_correct"]:
                st.error("❌ Zły klucz! Psy szczekają, obcy nie wejdzie.")
        return False
    return True

if check_password():
    # --- STYLIZACJA FOLKLOROWA (LUDOWA) ---
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Fondamento&family=Almendra&display=swap');

        /* Główne tło - lniana tekstura i kolory wsi */
        .stApp {
            background-color: #f4ece1;
            background-image: url("https://www.transparenttextures.com/patterns/natural-paper.png");
        }

        /* Motyw wycinanki w tle (uproszczony CSS) */
        .stApp::before {
            content: '🌿🌷🌿';
            position: fixed;
            top: 10px;
            right: 20px;
            font-size: 30px;
            opacity: 0.3;
        }

        /* Karty metryk - stylizacja 'Na deskach' */
        [data-testid="stMetric"] { 
            background: #ffffff !important; 
            border: 4px double #b00000 !important; 
            border-radius: 10px !important;
            box-shadow: 5px 5px 0px 0px #2c3e50 !important;
            padding: 15px !important;
        }

        [data-testid="stMetricLabel"] p { 
            color: #2c3e50 !important; 
            font-family: 'Fondamento', cursive !important;
            font-size: 24px !important;
            text-transform: uppercase;
        }

        [data-testid="stMetricValue"] div { 
            color: #b00000 !important; 
            font-family: 'Almendra', serif !important;
            font-size: 44px !important;
            font-weight: bold !important;
        }

        /* Nagłówki - styl ludowy */
        h1, h2 { 
            color: #b00000 !important; 
            font-family: 'Almendra', serif !important;
            font-size: 60px !important;
            text-align: center;
            border-bottom: 2px solid #b00000;
            margin-bottom: 30px !important;
        }

        /* Przyciski - rzemieślnicza robota */
        .stButton>button { 
            background: #2c3e50 !important;
            color: #f4ece1 !important; 
            border-radius: 0px !important;
            border: 2px solid #b00000 !important;
            font-family: 'Fondamento', cursive !important;
            font-size: 20px !important;
            transition: 0.3s;
        }

        .stButton>button:hover {
            background: #b00000 !important;
            color: white !important;
            transform: translateY(-2px);
        }

        /* Formularze i Expander */
        [data-testid="stExpander"], .stForm {
            background-color: #ffffff !important;
            border-radius: 5px !important;
            border: 2px solid #2c3e50 !important;
        }

        /* Tabs */
        .stTabs [data-baseweb="tab"] {
            font-family: 'Fondamento', cursive !important;
            font-size: 22px !important;
            color: #2c3e50 !important;
        }
        
        /* Sidebar */
        [data-testid="stSidebar"] {
            background: #e6d5bc !important;
            border-right: 3px solid #b00000 !important;
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
        st.error("🚜 Traktor utknął w błocie. Odśwież stronę."); st.stop()

    # --- LOGIKA FILTROWANIA ---
    today = date.today()
    current_month_str = today.strftime("%Y-%m")
    dni_m = calendar.monthrange(today.year, today.month)[1] - today.day + 1
    p800 = 1600 

    df_inc_m = df_inc[df_inc['Data i Godzina'].astype(str).str.contains(current_month_str, na=False)].copy() if not df_inc.empty else pd.DataFrame()
    df_exp_m = df_exp[df_exp['Data i Godzina'].astype(str).str.contains(current_month_str, na=False)].copy() if not df_exp.empty else pd.DataFrame()

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

    # --- SIDEBAR (SPICHLERZ) ---
    with st.sidebar:
        st.markdown("<h1 style='color: #b00000 !important; font-size: 30px !important;'>🌾 SPICHLERZ</h1>", unsafe_allow_html=True)
        client = get_client()
        sh = client.open("Budzet_Data")
        ws_sav = sh.worksheet("Oszczednosci")
        sav_val = float(str(ws_sav.acell('A2').value).replace(',', '.'))
        st.metric("ZASOBY W SKRZYNI", f"{sav_val:,.2f} PLN")
        
        st.divider()
        with st.expander("💰 ZARZĄDZAJ ZAPASAMI"):
            amt_s = st.number_input("Ile dukatów?", min_value=0.0, step=10.0, key="amt_sidebar")
            c_in, c_out = st.columns(2)
            if c_in.button("DO SCHOWKA"):
                if amt_s > 0:
                    ws_sav.update_acell('A2', str(sav_val + amt_s))
                    sh.worksheet("Wydatki").append_row([get_now(), "DO SCHOWKA: Odłożone", amt_s, "Inne", "Oszczędności"])
                    st.success(f"Schowano {amt_s} PLN!")
                    st.cache_data.clear(); time.sleep(1); st.rerun()
            if c_out.button("WYJMIJ"):
                if amt_s > 0:
                    ws_sav.update_acell('A2', str(sav_val - amt_s))
                    sh.worksheet("Przychody").append_row([get_now(), "WYJĘTE: Ze schowka", amt_s])
                    st.success(f"Wyjęto {amt_s} PLN na wydatki!")
                    st.cache_data.clear(); time.sleep(1); st.rerun()

        st.divider()
        if st.button("🚜 ZAMKNIJ ŻNIWA (MIESIĄC)"):
            new_sav = sav_val + balance
            ws_sav.update_acell('A2', str(new_sav))
            st.snow()
            st.success(f"Żniwa zakończone! {balance:.2f} PLN trafiło do spichlerza.")
            st.cache_data.clear(); time.sleep(1); st.rerun()

    # --- DASHBOARD ---
    st.markdown("<h1>🎻 REJESTR GOSPODARSKI</h1>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    c1.metric("📦 W KALETCE (NA TEN MIESIĄC)", f"{balance:,.2f} PLN")
    c2.metric("🥖 NA DZIEŃ DZISIEJSZY", f"{daily:,.2f} PLN")

    h_inc, h_exp = st.columns(2)
    with h_inc:
        st.metric("🐓 WPŁYWY", f"{inc_total:,.2f} PLN")
        with st.expander("📜 Wykaz przychodów"):
            if not df_inc_m.empty:
                st.table(df_inc_m[["Nazwa", "Kwota"]])
            else:
                st.info("Pusto w sypialni (brak wpływów).")

    with h_exp:
        st.metric("📉 ROZCHODY", f"{exp_total:,.2f} PLN")
        with st.expander("📜 Wykaz kosztów"):
            e_all = pd.concat([
                df_exp_m[["Nazwa", "Kwota"]] if not df_exp_m.empty else pd.DataFrame(),
                df_fix[["Nazwa", "Kwota"]] if not df_fix.empty else pd.DataFrame(),
                df_rat_active[["Rata", "Kwota"]].rename(columns={"Rata": "Nazwa"}) if not df_rat_active.empty else pd.DataFrame()
            ], ignore_index=True)
            if not e_all.empty:
                st.table(e_all)
            else:
                st.info("W tym miesiącu nikt nie prosi o zapłatę.")

    # --- ZAKŁADKI ---
    tabs = st.tabs(["✍️ Zapisy", "🏡 Stałe & Daniny", "🛶 Dalekie Plany", "📝 Wykazy"])

    with tabs[0]:
        ci, ce = st.columns(2)
        with ci:
            with st.form("f_inc", clear_on_submit=True):
                st.subheader("➕ Nowy Przybytek")
                ni, ki = st.text_input("Od kogo / Za co?"), st.number_input("Kwota", key="f_inc_k")
                if st.form_submit_button("DODAJ DO KASY"):
                    sh.worksheet("Przychody").append_row([get_now(), ni, ki])
                    st.cache_data.clear(); st.rerun()
        with ce:
            with st.form("f_exp", clear_on_submit=True):
                st.subheader("➖ Nowy Wydatek")
                ne, ke = st.text_input("Na co poszło?"), st.number_input("Kwota", key="f_exp_k")
                ka = st.selectbox("Rodzaj", ["Jedzenie", "Dom", "Transport", "Rozrywka", "Inne"])
                if st.form_submit_button("ZAPŁAĆ"):
                    sh.worksheet("Wydatki").append_row([get_now(), ne, ke, ka, "Zmienny"])
                    st.cache_data.clear(); st.rerun()
        
        st.divider()
        st.subheader("📖 Korekta bieżących zapisków")
        df_exp_m["USUŃ"] = False
        ed_e = st.data_editor(df_exp_m, num_rows="dynamic", use_container_width=True, key="ed_wpisy_final")
        
        if st.button("Uaktualnij Księgę"):
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
                st.subheader("🏠 Opłaty Stałe")
                nf, kf = st.text_input("Tytuł opłaty"), st.number_input("Kwota", key="f_fix_k")
                if st.form_submit_button("ZAPISZ"):
                    sh.worksheet("Koszty_Stale").append_row([get_now(), nf, kf])
                    st.cache_data.clear(); st.rerun()
            df_fix["USUŃ"] = False
            ed_f = st.data_editor(df_fix, use_container_width=True, key="ed_stale_final")
            if st.button("Zapisz Zmiany w Stałych"):
                cl_f = ed_f[ed_f["USUŃ"] == False].drop(columns=["USUŃ"])
                ws_f = sh.worksheet("Koszty_Stale")
                ws_f.clear(); ws_f.append_row(["Data i Godzina", "Nazwa", "Kwota"])
                if not cl_f.empty: ws_f.append_rows(cl_f.values.tolist())
                st.cache_data.clear(); st.rerun()
        with cr:
            with st.form("f_rat"):
                st.subheader("📜 Raty i Zobowiązania")
                nr, kr = st.text_input("Nazwa raty"), st.number_input("Kwota", key="f_rat_k")
                ds, de = st.date_input("Od kiedy"), st.date_input("Do kiedy")
                if st.form_submit_button("DODAJ RATĘ"):
                    sh.worksheet("Raty").append_row([nr, kr, str(ds), str(de)])
                    st.cache_data.clear(); st.rerun()
            df_rat["USUŃ"] = False
            ed_r = st.data_editor(df_rat, use_container_width=True, key="ed_raty_final")
            if st.button("Zapisz Zmiany w Ratach"):
                cl_r = ed_r[ed_r["USUŃ"] == False].drop(columns=["USUŃ"])
                if not cl_r.empty:
                    for c in ['Start', 'Koniec']: cl_r[c] = pd.to_datetime(cl_r[c]).dt.strftime('%Y-%m-%d')
                ws_r = sh.worksheet("Raty")
                ws_r.clear(); ws_r.append_row(["Rata", "Kwota", "Start", "Koniec"])
                if not cl_r.empty: ws_r.append_rows(cl_r.values.tolist())
                st.cache_data.clear(); st.rerun()

    with tabs[2]:
        with st.form("f_pla"):
            st.subheader("🛶 Plany na Przyszłość")
            pn, pk = st.text_input("Jaki cel?"), st.number_input("Kwota", key="f_pla_k")
            pm = st.selectbox("Na który miesiąc?", ["Styczeń", "Luty", "Marzec", "Kwiecień", "Maj", "Czerwiec", "Lipiec", "Sierpień", "Wrzesień", "Październik", "Listopad", "Grudzień"])
            if st.form_submit_button("ZAPLANUJ"):
                sh.worksheet("Planowanie").append_row([get_now(), pn, pk, pm])
                st.cache_data.clear(); st.rerun()
        df_pla["USUŃ"] = False
        ed_p = st.data_editor(df_pla, use_container_width=True, key="ed_plany_final")
        if st.button("Odśwież Plany"):
            cl_p = ed_p[ed_p["USUŃ"] == False].drop(columns=["USUŃ"])
            ws_p = sh.worksheet("Planowanie")
            ws_p.clear(); ws_p.append_row(["Data i Godzina", "Cel", "Kwota", "Miesiąc"])
            if not cl_p.empty: ws_p.append_rows(cl_p.values.tolist())
            st.cache_data.clear(); st.rerun()

    with tabs[3]:
        cs, ct = st.columns(2)
        with cs:
            st.subheader("🛒 Do kupienia na targu")
            with st.form("f_sho"):
                it = st.text_input("Co kupić?")
                if st.form_submit_button("DOPISZ"):
                    sh.worksheet("Zakupy").append_row([get_now(), it])
                    st.cache_data.clear(); st.rerun()
            df_shp["USUŃ"] = False
            ed_s = st.data_editor(df_shp, use_container_width=True, key="ed_zakupy_final")
            if st.button("Kupione (Usuń)"):
                cl_s = ed_s[ed_s["USUŃ"] == False].drop(columns=["USUŃ"])
                ws_s = sh.worksheet("Zakupy")
                ws_s.clear(); ws_s.append_row(["Data i Godzina", "Produkt"])
                if not cl_s.empty: ws_s.append_rows(cl_s.values.tolist())
                st.cache_data.clear(); st.rerun()
        with ct:
            st.subheader("🔨 Robota w zagrodzie")
            with st.form("f_tsk"):
                tn, td = st.text_input("Co do zrobienia?"), st.date_input("Na kiedy")
                if st.form_submit_button("DODAJ ZADANIE"):
                    sh.worksheet("Zadania").append_row([get_now(), tn, str(td), "Normalny"])
                    st.cache_data.clear(); st.rerun()
            df_tsk["USUŃ"] = False
            ed_t = st.data_editor(df_tsk, use_container_width=True, key="ed_zadania_final")
            if st.button("Zrobione"):
                cl_t = ed_t[ed_t["USUŃ"] == False].drop(columns=["USUŃ"])
                ws_t = sh.worksheet("Zadania")
                ws_t.clear(); ws_t.append_row(["Data i Godzina", "Zadanie", "Termin", "Priorytet"])
                if not cl_t.empty: ws_t.append_rows(cl_t.values.tolist())
                st.cache_data.clear(); st.rerun()
