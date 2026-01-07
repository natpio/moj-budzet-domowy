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
    # --- STYLIZACJA COUNTRY (Wysoki Kontrast & Styl) ---
    st.markdown("""
        <style>
        /* Tło aplikacji - ciepły beż/pergamin */
        .main { background-color: #f4ece1; }
        
        /* Karty Metryk - Stylizowane na skórę/drewno */
        [data-testid="stMetric"] {
            background-color: #3e2723 !important;
            border: 3px solid #8d6e63 !important;
            padding: 20px !important;
            border-radius: 15px !important;
            box-shadow: 5px 5px 15px rgba(0,0,0,0.2) !important;
        }

        /* Tekst w metrykach - BARDZO CZYTELNY */
        [data-testid="stMetricLabel"] p {
            color: #d7ccc8 !important; /* jasny beż */
            font-size: 18px !important;
            font-weight: bold !important;
            text-transform: uppercase;
        }

        [data-testid="stMetricValue"] div {
            color: #ffffff !important;
            font-size: 38px !important;
            font-family: 'Courier New', Courier, monospace; /* Styl maszyny do pisania */
        }

        /* Nagłówki */
        h1, h2, h3 { 
            color: #5d4037 !important; 
            font-family: 'Georgia', serif;
            border-bottom: 2px solid #a1887f;
        }
        
        /* Przyciski - Styl rdzawy/skórzany */
        .stButton>button {
            background-color: #a1887f !important;
            color: white !important;
            border-radius: 5px !important;
            border: 2px solid #5d4037 !important;
            font-weight: bold !important;
            height: 3em !important;
        }
        
        /* Formularze */
        [data-testid="stForm"] {
            background-color: #ffffff !important;
            border: 2px dashed #8d6e63 !important;
            border-radius: 10px !important;
        }

        /* Zakładki (Tabs) */
        .stTabs [data-baseweb="tab-list"] { background-color: transparent; }
        .stTabs [data-baseweb="tab"] {
            color: #5d4037 !important;
            font-size: 20px !important;
            font-weight: bold !important;
        }
        .stTabs [aria-selected="true"] {
            background-color: #d7ccc8 !important;
            border-radius: 10px 10px 0 0 !important;
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
            amt = st.number_input("Ile dukatów zabrać?", min_value=0.0, key="side_w")
            if st.button("POBIERZ Z SEJFU"):
                s_sav.update_acell('A2', str(sav_val - amt))
                s_inc.append_row([get_now(), "WYPŁATA ZE SKARBCA", amt])
                st.rerun()

    # --- UKŁAD GŁÓWNY ---
    st.markdown("<h1 style='text-align: center;'>📜 KSIĘGA RACHUNKOWA RANCZA</h1>", unsafe_allow_html=True)
    
    # Metryki w dwóch rzędach dla lepszej czytelności na telefonie
    row1_1, row1_2 = st.columns(2)
    with row1_1: st.metric("💰 DOSTĘPNE", f"{balance:,.2f} PLN")
    with row1_2: st.metric("☀️ NA DZIEŃ", f"{daily:,.2f} PLN", f"Jeszcze {dni_m} dni")
    
    row2_1, row2_2 = st.columns(2)
    with row2_1: st.metric("📈 DOCHODY", f"{inc_total:,.2f} PLN")
    with row2_2: st.metric("📉 WYDATKI", f"{exp_total:,.2f} PLN")

    st.write("")
    
    tabs = st.tabs(["🤠 Dashboard", "💸 Wpisy", "🏠 Stałe", "📅 Plany", "🛒 Listy"])

    with tabs[0]:
        st.subheader("Gdzie płynie złoto?")
        if not df_exp.empty:
            fig = px.pie(df_exp, values='Kwota', names='Kategoria', hole=.4, 
                         color_discrete_sequence=['#5d4037', '#8d6e63', '#a1887f', '#d7ccc8', '#3e2723'])
            fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="#5d4037")
            st.plotly_chart(fig, use_container_width=True)
        
        if st.button("🏜️ ZAMKNIJ MIESIĄC I WYŚLIJ ZYSK DO SEJFU", use_container_width=True):
            s_sav.update_acell('B2', str(balance))
            s_sav.update_acell('A2', str(sav_val + balance))
            st.balloons(); st.rerun()

    with tabs[1]:
        st.subheader("Nowe Zapisy w Księdze")
        c1, c2 = st.columns(2)
        with c1:
            with st.form("f_inc"):
                st.markdown("### ➕ Przychód")
                ni, ki = st.text_input("Skąd wpłata?"), st.number_input("Kwota", key="k1")
                if st.form_submit_button("DODAJ DO KSIĘGI"):
                    s_inc.append_row([get_now(), ni, ki]); st.rerun()
        with c2:
            with st.form("f_exp"):
                st.markdown("### ➖ Wydatek")
                ne, ke = st.text_input("Na co wydano?"), st.number_input("Kwota", key="k2")
                ka = st.selectbox("Rodzaj", ["Jedzenie", "Dom", "Transport", "Rozrywka", "Inne"])
                if st.form_submit_button("ZAKSIĘGUJ"):
                    s_exp.append_row([get_now(), ne, ke, ka, "Zmienny"]); st.rerun()
        
        st.divider()
        st.markdown("### 🖋️ Historia Wydatków")
        df_exp["USUŃ"] = False
        e_exp = st.data_editor(df_exp, num_rows="dynamic", use_container_width=True, key="ed_exp")
        if st.button("Zapisz poprawki w księdze"):
            cl = e_exp[e_exp["USUŃ"] == False].drop(columns=["USUŃ"])
            s_exp.clear(); s_exp.append_row(["Data i Godzina", "Nazwa", "Kwota", "Kategoria", "Typ"])
            if not cl.empty: s_exp.append_rows(cl.values.tolist()); st.rerun()

    with tabs[2]:
        col_f, col_r = st.columns(2)
        with col_f:
            with st.form("f_fix"):
                st.subheader("🏠 Daniny Stałe")
                nf, kf = st.text_input("Nazwa"), st.number_input("Kwota", key="k3")
                if st.form_submit_button("DODAJ OPŁATĘ"):
                    s_fix.append_row([get_now(), nf, kf]); st.rerun()
            st.data_editor(df_fix, use_container_width=True, key="ed_fix")
        with col_r:
            with st.form("f_rat"):
                st.subheader("🗓️ Raty i Długi")
                nr, kr = st.text_input("Rata"), st.number_input("Kwota", key="k4")
                ds, de = st.date_input("Od kiedy"), st.date_input("Do kiedy")
                if st.form_submit_button("DODAJ RATĘ"):
                    s_rat.append_row([nr, kr, str(ds), str(de)]); st.rerun()
            st.data_editor(df_rat, use_container_width=True, key="ed_rat")

    with tabs[3]:
        st.subheader("📅 Plany na przyszłe żniwa")
        with st.form("f_pla"):
            pn, pk = st.text_input("Na co zbieramy?"), st.number_input("Szacowana kwota", key="k5")
            pm = st.selectbox("Miesiąc", ["Styczeń", "Luty", "Marzec", "Kwiecień", "Maj", "Czerwiec", "Lipiec", "Sierpień", "Wrzesień", "Październik", "Listopad", "Grudzień"])
            if st.form_submit_button("DODAJ DO PLANÓW"):
                s_pla.append_row([get_now(), pn, pk, pm]); st.rerun()
        st.data_editor(df_pla, use_container_width=True, key="ed_pla")

    with tabs[4]:
        z_k, z_d = st.columns(2)
        with z_k:
            st.subheader("🛒 Zapasy do kupienia")
            with st.form("f_shp"):
                it = st.text_input("Co kupić?")
                if st.form_submit_button("DODAJ ZAPAS"):
                    s_shp.append_row([get_now(), it]); st.rerun()
            df_shp["KUPIŁEM"] = False
            e_shp = st.data_editor(df_shp, use_container_width=True, key="ed_shp")
            if st.button("Wyczyść kupione zapasy"):
                rem = e_shp[e_shp["KUPIŁEM"] == False].drop(columns=["KUPIŁEM"])
                s_shp.clear(); s_shp.append_row(["Data i Godzina", "Produkt"])
                if not rem.empty: s_shp.append_rows(rem.values.tolist()); st.rerun()
        with z_d:
            st.subheader("✅ Zadania na ranczu")
            with st.form("f_tsk"):
                tn, td = st.text_input("Co zrobić?"), st.date_input("Termin")
                if st.form_submit_button("DODAJ ROBOTĘ"):
                    s_tsk.append_row([get_now(), tn, str(td), "Normalny"]); st.rerun()
            df_tsk["GOTOWE"] = False
            e_tsk = st.data_editor(df_tsk, use_container_width=True, key="ed_tsk")
            if st.button("Usuń zrobioną robotę"):
                rem_t = e_tsk[e_tsk["GOTOWE"] == False].drop(columns=["GOTOWE"])
                s_tsk.clear(); s_tsk.append_row(["Data i Godzina", "Zadanie", "Termin", "Priorytet"])
                if not rem_t.empty: s_tsk.append_rows(rem_t.values.tolist()); st.rerun()
