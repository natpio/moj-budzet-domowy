import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
from google.oauth2 import service_account
from datetime import datetime, date
import calendar

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Pro Budget 2026", layout="wide", page_icon="💰")

# --- FUNKCJA LOGOWANIA ---
def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["credentials"]["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.markdown("<h2 style='text-align: center; color: black;'>🔒 Zaloguj się</h2>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            st.text_input("Hasło dostępu (wpisz i naciśnij ENTER)", type="password", on_change=password_entered, key="password")
            if "password_correct" in st.session_state and not st.session_state["password_correct"]:
                st.error("❌ Błędne hasło. Sprawdź wielkość liter.")
        return False
    return True

if check_password():
    # --- STYLIZACJA WYSOKIEJ CZYTELNOŚCI ---
    st.markdown("""
        <style>
        .main { background-color: #ffffff; }
        [data-testid="stMetric"] {
            background-color: #f8f9fa !important;
            border: 2px solid #000000 !important;
            border-radius: 10px !important;
            padding: 15px !important;
        }
        [data-testid="stMetricLabel"] p, [data-testid="stMetricValue"] div {
            color: #000000 !important;
            font-weight: 800 !important;
            opacity: 1 !important;
        }
        label, p, h1, h2, h3, .stMarkdown {
            color: #000000 !important;
            font-weight: 600 !important;
        }
        .stButton>button {
            border: 2px solid #000000;
            font-weight: bold;
        }
        [data-testid="stForm"] {
            background-color: #fdfdfd !important;
            border: 2px solid #000000 !important;
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

    # --- POBIERANIE DANYCH ---
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
    
    # 800+
    p800 = 0
    for bd in [date(2018, 8, 1), date(2022, 11, 1)]:
        if (today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day))) < 18: p800 += 800

    # Raty
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

    # --- SIDEBAR (SKARBIEC) ---
    with st.sidebar:
        st.header("🏦 SKARBIEC")
        try:
            sav_val = float(str(s_sav.acell('A2').value).replace(',', '.'))
            last_trans = float(str(s_sav.acell('B2').value).replace(',', '.'))
        except:
            sav_val, last_trans = 0.0, 0.0
        st.metric("Oszczędności", f"{sav_val:,.2f} PLN")
        
        with st.expander("Wypłata"):
            amt = st.number_input("Kwota", min_value=0.0, key="side_w")
            if st.button("Zabierz ze skarbca"):
                s_sav.update_acell('A2', str(sav_val - amt))
                s_inc.append_row([get_now(), "WYPŁATA ZE SKARBCA", amt])
                st.rerun()
        if st.button("Cofnij zamknięcie"):
            s_sav.update_acell('A2', str(sav_val - last_trans))
            s_sav.update_acell('B2', "0")
            st.rerun()

    # --- WIDOK GŁÓWNY ---
    st.title("💰 Budżet Domowy 2026")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("PORTFEL", f"{balance:,.2f} PLN")
    m2.metric("NA DZIEŃ", f"{daily:,.2f} PLN", f"{dni_m} dni")
    m3.metric("DOCHODY", f"{inc_total:,.2f} PLN")
    m4.metric("WYDATKI", f"{exp_total:,.2f} PLN")

    tabs = st.tabs(["📊 Analiza", "💸 Wpisy", "🏠 Stałe/Raty", "📅 Plany", "🛒 Listy"])

    with tabs[0]:
        st.subheader("Struktura wydatków")
        if not df_exp.empty:
            fig = px.pie(df_exp, values='Kwota', names='Kategoria', hole=.4)
            st.plotly_chart(fig, use_container_width=True)
        if st.button("🔒 ZAMKNIJ MIESIĄC", type="primary"):
            s_sav.update_acell('B2', str(balance))
            s_sav.update_acell('A2', str(sav_val + balance))
            st.balloons(); st.rerun()

    with tabs[1]:
        c_i, c_e = st.columns(2)
        with c_i:
            with st.form("f_inc"):
                st.write("Dodaj Dochód")
                ni, ki = st.text_input("Nazwa"), st.number_input("Kwota", key="k1")
                if st.form_submit_button("Dodaj"):
                    s_inc.append_row([get_now(), ni, ki]); st.rerun()
        with c_e:
            with st.form("f_exp"):
                st.write("Dodaj Wydatek")
                ne, ke = st.text_input("Nazwa"), st.number_input("Kwota", key="k2")
                ka = st.selectbox("Kategoria", ["Jedzenie", "Dom", "Transport", "Rozrywka", "Inne"])
                if st.form_submit_button("Zaksięguj"):
                    s_exp.append_row([get_now(), ne, ke, ka, "Zmienny"]); st.rerun()
        
        st.divider()
        st.write("Edycja Wydatków")
        df_exp["USUŃ"] = False
        e_exp = st.data_editor(df_exp, num_rows="dynamic", use_container_width=True, key="ed_exp")
        if st.button("Zapisz zmiany"):
            cl = e_exp[e_exp["USUŃ"] == False].drop(columns=["USUŃ"])
            s_exp.clear(); s_exp.append_row(["Data i Godzina", "Nazwa", "Kwota", "Kategoria", "Typ"])
            if not cl.empty: s_exp.append_rows(cl.values.tolist()); st.rerun()

    with tabs[2]:
        col_f, col_r = st.columns(2)
        with col_f:
            with st.form("f_fix"):
                st.write("Koszty Stałe")
                nf, kf = st.text_input("Opłata"), st.number_input("Kwota", key="k3")
                if st.form_submit_button("Dodaj stały"):
                    s_fix.append_row([get_now(), nf, kf]); st.rerun()
            st.data_editor(df_fix, num_rows="dynamic", use_container_width=True, key="ed_fix")
        with col_r:
            with st.form("f_rat"):
                st.write("Raty")
                nr, kr = st.text_input("Rata"), st.number_input("Kwota", key="k4")
                ds, de = st.date_input("Start"), st.date_input("Koniec")
                if st.form_submit_button("Dodaj ratę"):
                    s_rat.append_row([nr, kr, str(ds), str(de)]); st.rerun()
            st.data_editor(df_rat, num_rows="dynamic", use_container_width=True, key="ed_rat")

    with tabs[3]:
        with st.form("f_pla"):
            st.write("Planowanie wydatków")
            pn, pk = st.text_input("Cel"), st.number_input("Kwota", key="k5")
            pm = st.selectbox("Miesiąc", ["Styczeń", "Luty", "Marzec", "Kwiecień", "Maj", "Czerwiec", "Lipiec", "Sierpień", "Wrzesień", "Październik", "Listopad", "Grudzień"])
            if st.form_submit_button("Dodaj do planu"):
                s_pla.append_row([get_now(), pn, pk, pm]); st.rerun()
        st.data_editor(df_pla, num_rows="dynamic", use_container_width=True, key="ed_pla")

    with tabs[4]:
        z_k, z_d = st.columns(2)
        with z_k:
            st.write("🛒 Zakupy")
            with st.form("f_shp"):
                it = st.text_input("Produkt")
                if st.form_submit_button("Dodaj do listy"):
                    s_shp.append_row([get_now(), it]); st.rerun()
            df_shp["OK"] = False
            e_shp = st.data_editor(df_shp, use_container_width=True, key="ed_shp")
            if st.button("Usuń zaznaczone zakupy"):
                rem = e_shp[e_shp["OK"] == False].drop(columns=["OK"])
                s_shp.clear(); s_shp.append_row(["Data i Godzina", "Produkt"])
                if not rem.empty: s_shp.append_rows(rem.values.tolist()); st.rerun()
        with z_d:
            st.write("✅ Zadania")
            with st.form("f_tsk"):
                tn, td = st.text_input("Zadanie"), st.date_input("Termin")
                if st.form_submit_button("Dodaj zadanie"):
                    s_tsk.append_row([get_now(), tn, str(td), "Normalny"]); st.rerun()
            df_tsk["OK"] = False
            e_tsk = st.data_editor(df_tsk, use_container_width=True, key="ed_tsk")
            if st.button("Usuń zrobione zadania"):
                rem_t = e_tsk[e_tsk["OK"] == False].drop(columns=["OK"])
                s_tsk.clear(); s_tsk.append_row(["Data i Godzina", "Zadanie", "Termin", "Priorytet"])
                if not rem_t.empty: s_tsk.append_rows(rem_t.values.tolist()); st.rerun()

