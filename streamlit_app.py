import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
from google.oauth2 import service_account
from datetime import datetime, date
import calendar

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
    # --- STYLIZACJA COUNTRY ---
    st.markdown("""
        <style>
        .main { background-color: #f4ece1; }
        [data-testid="stMetric"] {
            background-color: #3e2723 !important;
            border: 3px solid #8d6e63 !important;
            padding: 20px !important;
            border-radius: 15px !important;
        }
        [data-testid="stMetricLabel"] p {
            color: #d7ccc8 !important;
            font-size: 18px !important;
            font-weight: bold !important;
            text-transform: uppercase;
        }
        [data-testid="stMetricValue"] div {
            color: #ffffff !important;
            font-size: 38px !important;
            font-family: 'Courier New', Courier, monospace;
        }
        h1, h2, h3 { color: #5d4037 !important; font-family: 'Georgia', serif; }
        .stButton>button {
            background-color: #a1887f !important;
            color: white !important;
            border: 2px solid #5d4037 !important;
            font-weight: bold !important;
        }
        [data-testid="stForm"] {
            background-color: #ffffff !important;
            border: 2px dashed #8d6e63 !important;
        }
        </style>
        """, unsafe_allow_html=True)

    # --- POŁĄCZENIE Z ARKUSZEM ---
    @st.cache_resource
    def get_sheet(sheet_name):
        creds_dict = st.secrets["gcp_service_account"]
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        return client.open("Budzet_Data").worksheet(sheet_name)

    def get_now(): return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Pobieranie danych
    s_inc, s_exp, s_fix, s_rat, s_sav, s_shp, s_tsk, s_pla = [get_sheet(n) for n in ["Przychody", "Wydatki", "Koszty_Stale", "Raty", "Oszczednosci", "Zakupy", "Zadania", "Planowanie"]]

    df_inc = pd.DataFrame(s_inc.get_all_records())
    df_exp = pd.DataFrame(s_exp.get_all_records())
    df_fix = pd.DataFrame(s_fix.get_all_records())
    df_rat = pd.DataFrame(s_rat.get_all_records())
    df_shp = pd.DataFrame(s_shp.get_all_records())
    df_tsk = pd.DataFrame(s_tsk.get_all_records())
    df_pla = pd.DataFrame(s_pla.get_all_records())

    # --- OBLICZENIA ---
    today = date.today()
    dni_m = calendar.monthrange(today.year, today.month)[1] - today.day + 1
    p800 = 0
    for bd in [date(2018, 8, 1), date(2022, 11, 1)]:
        if (today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day))) < 18: p800 += 800

    suma_rat = 0
    if not df_rat.empty:
        df_rat['Start'] = pd.to_datetime(df_rat['Start'])
        df_rat['Koniec'] = pd.to_datetime(df_rat['Koniec'])
        mask = (df_rat['Start'] <= pd.Timestamp(today)) & (df_rat['Koniec'] >= pd.Timestamp(today))
        suma_rat = df_rat[mask]['Kwota'].sum()

    inc_total = (df_inc['Kwota'].sum() if not df_inc.empty else 0) + p800
    exp_total = (df_exp['Kwota'].sum() if not df_exp.empty else 0) + (df_fix['Kwota'].sum() if not df_fix.empty else 0) + suma_rat
    balance = inc_total - exp_total
    daily = balance / dni_m if dni_m > 0 else balance

    # --- SIDEBAR ---
    with st.sidebar:
        st.markdown("<h1 style='text-align:center;'>🤠 SEJF</h1>", unsafe_allow_html=True)
        try:
            sav_val = float(str(s_sav.acell('A2').value).replace(',', '.'))
            last_trans = float(str(s_sav.acell('B2').value).replace(',', '.'))
        except:
            sav_val, last_trans = 0.0, 0.0
        st.metric("ZŁOTO W SEJFIE", f"{sav_val:,.2f} PLN")
        with st.expander("💰 WYPŁATA"):
            amt = st.number_input("Ile dukatów?", min_value=0.0, key="side_w")
            if st.button("POBIERZ Z SEJFU"):
                s_sav.update_acell('A2', str(sav_val - amt))
                s_inc.append_row([get_now(), "WYPŁATA ZE SKARBCA", amt]); st.rerun()

    # --- UKŁAD GŁÓWNY ---
    st.markdown("<h1 style='text-align: center;'>📜 KSIĘGA RACHUNKOWA RANCZA</h1>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 PORTFEL", f"{balance:,.2f} PLN")
    c2.metric("☀️ NA DZIEŃ", f"{daily:,.2f} PLN")
    c3.metric("📈 DOCHODY", f"{inc_total:,.2f} PLN")
    c4.metric("📉 WYDATKI", f"{exp_total:,.2f} PLN")

    tabs = st.tabs(["🤠 Dashboard", "💸 Wpisy", "🏠 Stałe & Raty", "📅 Plany", "🛒 Listy"])

    with tabs[0]:
        if not df_exp.empty:
            fig = px.pie(df_exp, values='Kwota', names='Kategoria', hole=.4, template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)
        if st.button("🏜️ ZAMKNIJ MIESIĄC (WYŚLIJ ZYSK DO SEJFU)", use_container_width=True):
            s_sav.update_acell('B2', str(balance))
            s_sav.update_acell('A2', str(sav_val + balance)); st.balloons(); st.rerun()

    with tabs[1]:
        col_i, col_e = st.columns(2)
        with col_i:
            with st.form("f_inc"):
                ni, ki = st.text_input("Skąd wpłata?"), st.number_input("Kwota")
                if st.form_submit_button("DODAJ PRZYCHÓD"):
                    s_inc.append_row([get_now(), ni, ki]); st.rerun()
        with col_e:
            with st.form("f_exp"):
                ne, ke = st.text_input("Na co?"), st.number_input("Kwota")
                ka = st.selectbox("Kategoria", ["Jedzenie", "Dom", "Transport", "Rozrywka", "Inne"])
                if st.form_submit_button("ZAKSIĘGUJ"):
                    s_exp.append_row([get_now(), ne, ke, ka, "Zmienny"]); st.rerun()
        
        st.markdown("### 🖋️ Edycja Wydatków")
        df_exp["USUŃ"] = False
        e_exp = st.data_editor(df_exp, num_rows="dynamic", use_container_width=True, key="ed_exp")
        if st.button("Zapisz zmiany w wydatkach"):
            cl = e_exp[e_exp["USUŃ"] == False].drop(columns=["USUŃ"])
            s_exp.clear(); s_exp.append_row(["Data i Godzina", "Nazwa", "Kwota", "Kategoria", "Typ"])
            if not cl.empty: s_exp.append_rows(cl.values.tolist()); st.rerun()

    with tabs[2]:
        col_f, col_r = st.columns(2)
        with col_f:
            with st.form("f_fix"):
                nf, kf = st.text_input("Opłata stała"), st.number_input("Kwota", key="k_fix")
                if st.form_submit_button("DODAJ STAŁĄ"):
                    s_fix.append_row([get_now(), nf, kf]); st.rerun()
            df_fix["USUŃ"] = False
            e_fix = st.data_editor(df_fix, use_container_width=True, key="ed_fix")
            if st.button("Zatwierdź zmiany w stałych"):
                cl_f = e_fix[e_fix["USUŃ"] == False].drop(columns=["USUŃ"])
                s_fix.clear(); s_fix.append_row(["Data i Godzina", "Nazwa", "Kwota"])
                if not cl_f.empty: s_fix.append_rows(cl_f.values.tolist()); st.rerun()

        with col_r:
            with st.form("f_rat"):
                nr, kr = st.text_input("Rata"), st.number_input("Kwota", key="k_rat")
                ds, de = st.date_input("Od"), st.date_input("Do")
                if st.form_submit_button("DODAJ RATĘ"):
                    s_rat.append_row([nr, kr, str(ds), str(de)]); st.rerun()
            df_rat["USUŃ"] = False
            e_rat = st.data_editor(df_rat, use_container_width=True, key="ed_rat")
            if st.button("Zatwierdź zmiany w ratach"):
                cl_r = e_rat[e_rat["USUŃ"] == False].drop(columns=["USUŃ"])
                s_rat.clear(); s_rat.append_row(["Rata", "Kwota", "Start", "Koniec"])
                if not cl_r.empty: s_rat.append_rows(cl_r.values.tolist()); st.rerun()

    with tabs[3]:
        with st.form("f_pla"):
            pn, pk = st.text_input("Planowany wydatek"), st.number_input("Kwota", key="k_pla")
            pm = st.selectbox("Miesiąc", ["Styczeń", "Luty", "Marzec", "Kwiecień", "Maj", "Czerwiec", "Lipiec", "Sierpień", "Wrzesień", "Październik", "Listopad", "Grudzień"])
            if st.form_submit_button("DODAJ DO PLANU"):
                s_pla.append_row([get_now(), pn, pk, pm]); st.rerun()
        df_pla["USUŃ"] = False
        e_pla = st.data_editor(df_pla, use_container_width=True, key="ed_pla")
        if st.button("Zatwierdź zmiany w planach"):
            cl_p = e_pla[e_pla["USUŃ"] == False].drop(columns=["USUŃ"])
            s_pla.clear(); s_pla.append_row(["Data i Godzina", "Cel", "Kwota", "Miesiąc"])
            if not cl_p.empty: s_pla.append_rows(cl_p.values.tolist()); st.rerun()

    with tabs[4]:
        col_s, col_t = st.columns(2)
        with col_s:
            st.write("🛒 Zakupy")
            with st.form("f_shp"):
                it = st.text_input("Produkt")
                if st.form_submit_button("DODAJ PRODUKT"):
                    s_shp.append_row([get_now(), it]); st.rerun()
            df_shp["USUŃ"] = False
            e_shp = st.data_editor(df_shp, use_container_width=True, key="ed_shp")
            if st.button("Wyczyść zaznaczone zakupy"):
                cl_s = e_shp[e_shp["USUŃ"] == False].drop(columns=["USUŃ"])
                s_shp.clear(); s_shp.append_row(["Data i Godzina", "Produkt"])
                if not cl_s.empty: s_shp.append_rows(cl_s.values.tolist()); st.rerun()
        with col_t:
            st.write("✅ Zadania")
            with st.form("f_tsk"):
                tn, td = st.text_input("Zadanie"), st.date_input("Termin")
                if st.form_submit_button("DODAJ ZADANIE"):
                    s_tsk.append_row([get_now(), tn, str(td), "Normalny"]); st.rerun()
            df_tsk["USUŃ"] = False
            e_tsk = st.data_editor(df_tsk, use_container_width=True, key="ed_tsk")
            if st.button("Wyczyść zaznaczone zadania"):
                cl_t = e_tsk[e_tsk["USUŃ"] == False].drop(columns=["USUŃ"])
                s_tsk.clear(); s_tsk.append_row(["Data i Godzina", "Zadanie", "Termin", "Priorytet"])
                if not cl_t.empty: s_tsk.append_rows(cl_t.values.tolist()); st.rerun()
