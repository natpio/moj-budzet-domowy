import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
from google.oauth2 import service_account
from datetime import datetime, date
import calendar
import time

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Ranczo Finansowe 2026", layout="wide", page_icon="🤠")

# --- FUNKCJA LOGOWANIA ---
def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["credentials"]["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.markdown("<h2 style='text-align: center; color: #5d4037;'>🌵 Zatrzymaj się, kowboju! Podaj hasło:</h2>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            st.text_input("Klucz do sejfu", type="password", on_change=password_entered, key="password")
            if "password_correct" in st.session_state and not st.session_state["password_correct"]:
                st.error("❌ Zły klucz! Konie parskają ze śmiechu.")
        return False
    return True

if check_password():
    # --- STYLIZACJA ---
    st.markdown("""
        <style>
        .main { background-color: #f4ece1; }
        [data-testid="stMetric"] { background-color: #3e2723 !important; border: 3px solid #8d6e63 !important; padding: 20px !important; border-radius: 15px !important; }
        [data-testid="stMetricLabel"] p { color: #d7ccc8 !important; font-size: 18px !important; font-weight: bold !important; text-transform: uppercase; }
        [data-testid="stMetricValue"] div { color: #ffffff !important; font-size: 38px !important; font-family: 'Courier New', Courier, monospace; }
        h1, h2, h3 { color: #5d4037 !important; font-family: 'Georgia', serif; }
        .stButton>button { background-color: #a1887f !important; color: white !important; border: 2px solid #5d4037 !important; font-weight: bold !important; }
        [data-testid="stExpander"] { background-color: #ffffff !important; border: 1px solid #8d6e63 !important; border-radius: 10px !important; }
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
            time.sleep(0.3)
        return data

    def get_now(): return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        all_d = load_all_data()
        df_inc, df_exp, df_fix, df_rat, df_sav, df_shp, df_tsk, df_pla = [all_d[n] for n in ["Przychody", "Wydatki", "Koszty_Stale", "Raty", "Oszczednosci", "Zakupy", "Zadania", "Planowanie"]]
    except:
        st.error("🤠 Problem z połączeniem. Odśwież stronę."); st.stop()

    # --- OBLICZENIA ---
    today = date.today()
    dni_m = calendar.monthrange(today.year, today.month)[1] - today.day + 1
    p800 = 1600
    
    df_rat_active = pd.DataFrame()
    suma_rat = 0
    if not df_rat.empty:
        df_rat['Start'] = pd.to_datetime(df_rat['Start'])
        df_rat['Koniec'] = pd.to_datetime(df_rat['Koniec'])
        mask = (df_rat['Start'] <= pd.Timestamp(today)) & (df_rat['Koniec'] >= pd.Timestamp(today))
        df_rat_active = df_rat[mask].copy()
        suma_rat = df_rat_active['Kwota'].sum()

    inc_total = (df_inc['Kwota'].sum() if not df_inc.empty else 0) + p800
    exp_total = (df_exp['Kwota'].sum() if not df_exp.empty else 0) + (df_fix['Kwota'].sum() if not df_fix.empty else 0) + suma_rat
    balance = inc_total - exp_total
    daily = balance / dni_m if dni_m > 0 else balance

    # --- SIDEBAR (SEJF) ---
    with st.sidebar:
        st.markdown("<h1 style='text-align:center;'>🤠 SEJF</h1>", unsafe_allow_html=True)
        client = get_client()
        ws_sav = client.open("Budzet_Data").worksheet("Oszczednosci")
        sav_val = float(str(ws_sav.acell('A2').value).replace(',', '.'))
        st.metric("ZŁOTO W SEJFIE", f"{sav_val:,.2f} PLN")
        with st.expander("💰 WYPŁATA"):
            amt = st.number_input("Kwota", min_value=0.0)
            if st.button("POBIERZ"):
                ws_sav.update_acell('A2', str(sav_val - amt))
                client.open("Budzet_Data").worksheet("Przychody").append_row([get_now(), "WYPŁATA ZE SKARBCA", amt])
                st.cache_data.clear(); st.rerun()

    # --- DASHBOARD ---
    st.markdown("<h1 style='text-align: center;'>📜 KSIĘGA RACHUNKOWA</h1>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    c1.metric("💰 PORTFEL", f"{balance:,.2f} PLN")
    c2.metric("☀️ NA DZIEŃ", f"{daily:,.2f} PLN")

    h_inc, h_exp = st.columns(2)
    with h_inc:
        st.metric("📈 DOCHODY", f"{inc_total:,.2f} PLN")
        with st.expander("🔍 Szczegóły wpływów"):
            i_list = df_inc[["Nazwa", "Kwota"]].copy()
            if p800 > 0: i_list = pd.concat([i_list, pd.DataFrame([{"Nazwa": "Program 800+", "Kwota": p800}])], ignore_index=True)
            st.table(i_list)

    with h_exp:
        st.metric("📉 WYDATKI", f"{exp_total:,.2f} PLN")
        with st.expander("🔍 Pełna lista kosztów"):
            e_all = pd.concat([df_exp[["Nazwa", "Kwota"]], df_fix[["Nazwa", "Kwota"]], df_rat_active[["Rata", "Kwota"]].rename(columns={"Rata": "Nazwa"})], ignore_index=True)
            st.table(e_all)

    # --- ZAKŁADKI OPERACYJNE ---
    tabs = st.tabs(["💸 Wpisy", "🏠 Stałe & Raty", "📅 Plany", "🛒 Listy"])

    with tabs[0]:
        ci, ce = st.columns(2)
        with ci:
            with st.form("f1"):
                st.subheader("➕ Przychód")
                ni, ki = st.text_input("Skąd?"), st.number_input("Kwota", key="ik")
                if st.form_submit_button("DODAJ"):
                    client.open("Budzet_Data").worksheet("Przychody").append_row([get_now(), ni, ki])
                    st.cache_data.clear(); st.rerun()
        with ce:
            with st.form("f2"):
                st.subheader("➖ Wydatek")
                ne, ke = st.text_input("Na co?"), st.number_input("Kwota", key="ek")
                ka = st.selectbox("Rodzaj", ["Jedzenie", "Dom", "Transport", "Rozrywka", "Inne"])
                if st.form_submit_button("DODAJ"):
                    client.open("Budzet_Data").worksheet("Wydatki").append_row([get_now(), ne, ke, ka, "Zmienny"])
                    st.cache_data.clear(); st.rerun()
        
        st.subheader("🖋️ Zarządzaj historią")
        df_exp["USUŃ"] = False
        ed_e = st.data_editor(df_exp, num_rows="dynamic", use_container_width=True)
        if st.button("Zapisz zmiany w wydatkach"):
            cl = ed_e[ed_e["USUŃ"] == False].drop(columns=["USUŃ"])
            ws = client.open("Budzet_Data").worksheet("Wydatki")
            ws.clear(); ws.append_row(["Data i Godzina", "Nazwa", "Kwota", "Kategoria", "Typ"])
            if not cl.empty: ws.append_rows(cl.values.tolist())
            st.cache_data.clear(); st.rerun()

    with tabs[1]:
        cf, cr = st.columns(2)
        with cf:
            with st.form("f3"):
                st.subheader("🏠 Stałe")
                nf, kf = st.text_input("Nazwa"), st.number_input("Kwota", key="fk")
                if st.form_submit_button("DODAJ"):
                    client.open("Budzet_Data").worksheet("Koszty_Stale").append_row([get_now(), nf, kf])
                    st.cache_data.clear(); st.rerun()
            df_fix["USUŃ"] = False
            ed_f = st.data_editor(df_fix, use_container_width=True)
            if st.button("Zapisz zmiany w Stałych"):
                cl_f = ed_f[ed_f["USUŃ"] == False].drop(columns=["USUŃ"])
                ws_f = client.open("Budzet_Data").worksheet("Koszty_Stale")
                ws_f.clear(); ws_f.append_row(["Data i Godzina", "Nazwa", "Kwota"])
                if not cl_f.empty: ws_f.append_rows(cl_f.values.tolist())
                st.cache_data.clear(); st.rerun()
        with cr:
            with st.form("f4"):
                st.subheader("🗓️ Raty")
                nr, kr = st.text_input("Nazwa"), st.number_input("Kwota", key="rk")
                ds, de = st.date_input("Od"), st.date_input("Do")
                if st.form_submit_button("DODAJ"):
                    client.open("Budzet_Data").worksheet("Raty").append_row([nr, kr, str(ds), str(de)])
                    st.cache_data.clear(); st.rerun()
            df_rat["USUŃ"] = False
            ed_r = st.data_editor(df_rat, use_container_width=True)
            if st.button("Zapisz zmiany w Ratach"):
                cl_r = ed_r[ed_r["USUŃ"] == False].drop(columns=["USUŃ"])
                if not cl_r.empty:
                    for c in ['Start', 'Koniec']: cl_r[c] = pd.to_datetime(cl_r[c]).dt.strftime('%Y-%m-%d')
                ws_r = client.open("Budzet_Data").worksheet("Raty")
                ws_r.clear(); ws_r.append_row(["Rata", "Kwota", "Start", "Koniec"])
                if not cl_r.empty: ws_r.append_rows(cl_r.values.tolist())
                st.cache_data.clear(); st.rerun()

    with tabs[2]:
        with st.form("f5"):
            st.subheader("📅 Plany")
            pn, pk = st.text_input("Cel"), st.number_input("Kwota", key="pk")
            pm = st.selectbox("Miesiąc", ["Styczeń", "Luty", "Marzec", "Kwiecień", "Maj", "Czerwiec", "Lipiec", "Sierpień", "Wrzesień", "Październik", "Listopad", "Grudzień"])
            if st.form_submit_button("PLANUJ"):
                client.open("Budzet_Data").worksheet("Planowanie").append_row([get_now(), pn, pk, pm])
                st.cache_data.clear(); st.rerun()
        df_pla["USUŃ"] = False
        ed_p = st.data_editor(df_pla, use_container_width=True)
        if st.button("Zapisz plany"):
            cl_p = ed_p[ed_p["USUŃ"] == False].drop(columns=["USUŃ"])
            ws_p = client.open("Budzet_Data").worksheet("Planowanie")
            ws_p.clear(); ws_p.append_row(["Data i Godzina", "Cel", "Kwota", "Miesiąc"])
            if not cl_p.empty: ws_p.append_rows(cl_p.values.tolist())
            st.cache_data.clear(); st.rerun()

    with tabs[3]:
        cs, ct = st.columns(2)
        with cs:
            st.subheader("🛒 Zakupy")
            with st.form("f6"):
                it = st.text_input("Co kupić?")
                if st.form_submit_button("DODAJ"):
                    client.open("Budzet_Data").worksheet("Zakupy").append_row([get_now(), it])
                    st.cache_data.clear(); st.rerun()
            df_shp["USUŃ"] = False
            ed_s = st.data_editor(df_shp, use_container_width=True)
            if st.button("Usuń zaznaczone zakupy"):
                cl_s = ed_s[ed_s["USUŃ"] == False].drop(columns=["USUŃ"])
                ws_s = client.open("Budzet_Data").worksheet("Zakupy")
                ws_s.clear(); ws_s.append_row(["Data i Godzina", "Produkt"])
                if not cl_s.empty: ws_s.append_rows(cl_s.values.tolist())
                st.cache_data.clear(); st.rerun()
        with ct:
            st.subheader("✅ Zadania")
            with st.form("f7"):
                tn, td = st.text_input("Co zrobić?"), st.date_input("Termin")
                if st.form_submit_button("DODAJ"):
                    client.open("Budzet_Data").worksheet("Zadania").append_row([get_now(), tn, str(td), "Normalny"])
                    st.cache_data.clear(); st.rerun()
            df_tsk["USUŃ"] = False
            ed_t = st.data_editor(df_tsk, use_container_width=True)
            if st.button("Usuń zaznaczone zadania"):
                cl_t = ed_t[ed_t["USUŃ"] == False].drop(columns=["USUŃ"])
                ws_t = client.open("Budzet_Data").worksheet("Zadania")
                ws_t.clear(); ws_t.append_row(["Data i Godzina", "Zadanie", "Termin", "Priorytet"])
                if not cl_t.empty: ws_t.append_rows(cl_t.values.tolist())
                st.cache_data.clear(); st.rerun()
