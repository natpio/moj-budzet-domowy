import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
from google.oauth2 import service_account
from datetime import datetime, date
import calendar

# --- KONFIGURACJA STRONY (Musi być na samej górze) ---
st.set_page_config(page_title="Pro Budget 2026", layout="wide", page_icon="💎")

# --- FUNKCJA LOGOWANIA ---
def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["credentials"]["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.markdown("<h2 style='text-align: center;'>🔒 Autoryzacja Systemu</h2>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            st.text_input("Wprowadź hasło", type="password", on_change=password_entered, key="password")
        return False
    return st.session_state.get("password_correct", False)

if check_password():
    # --- ZAAWANSOWANY STYL CSS (NAPRAWA CZYTELNOŚCI MOBILE) ---
    st.markdown("""
        <style>
        /* Tło główne */
        .main { background-color: #0d1117; }
        
        /* Karty Metryk - WYSOKI KONTRAST */
        [data-testid="stMetric"] {
            background-color: #1c2128 !important;
            border: 1px solid #30363d !important;
            padding: 20px !important;
            border-radius: 12px !important;
            box-shadow: 0 4px 10px rgba(0,0,0,0.3) !important;
        }

        /* Etykiety metryk (np. Portfel) */
        [data-testid="stMetricLabel"] {
            color: #adbac7 !important;
            font-size: 15px !important;
            font-weight: 500 !important;
        }

        /* Wartości metryk (Kwoty) - WYRAŹNA BIEL */
        [data-testid="stMetricValue"] {
            color: #ffffff !important;
            font-size: 32px !important;
            font-weight: 800 !important;
        }

        /* Stylizacja przycisków */
        .stButton>button {
            border-radius: 10px;
            text-transform: uppercase;
            letter-spacing: 1px;
            font-weight: 600;
        }
        
        /* Naprawa widoczności formularzy */
        [data-testid="stForm"] {
            background-color: #1c2128 !important;
            border-radius: 15px !important;
            padding: 20px !important;
        }
        </style>
        """, unsafe_allow_html=True)

    # --- FUNKCJE POŁĄCZENIA ---
    @st.cache_resource
    def get_sheet(sheet_name):
        creds_dict = st.secrets["gcp_service_account"]
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        return client.open("Budzet_Data").worksheet(sheet_name)

    def get_now(): return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # --- POBIERANIE DANYCH ---
    # Używamy nazw Twoich zakładek z arkusza
    s_inc = get_sheet("Przychody")
    s_exp = get_sheet("Wydatki")
    s_fix = get_sheet("Koszty_Stale")
    s_rat = get_sheet("Raty")
    s_sav = get_sheet("Oszczednosci")
    s_shp = get_sheet("Zakupy")
    s_tsk = get_sheet("Zadania")
    s_pla = get_sheet("Planowanie")

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
    
    # Automatyczne 800+ dla dwóch córek (2018 i 2022)
    p800 = 0
    for bd in [date(2018, 8, 1), date(2022, 11, 1)]:
        if (today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day))) < 18: p800 += 800

    # Aktywne Raty
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
        st.title("🏦 SKARBIEC")
        try:
            sav_val = float(str(s_sav.acell('A2').value).replace(',', '.'))
            last_trans = float(str(s_sav.acell('B2').value).replace(',', '.'))
        except:
            sav_val, last_trans = 0.0, 0.0
        
        st.metric("Oszczędności ogółem", f"{sav_val:,.2f} PLN")
        
        with st.expander("💸 POBIERZ ZE SKARBCA"):
            amt = st.number_input("Kwota wypłaty", min_value=0.0, step=100.0, key="withdraw_val")
            if st.button("ZATWIERDŹ WYPŁATĘ"):
                s_sav.update_acell('A2', str(sav_val - amt))
                s_inc.append_row([get_now(), "WYPŁATA ZE SKARBCA", amt])
                st.rerun()
        
        st.divider()
        if st.button("🔄 COFNIJ ZAMKNIĘCIE"):
            s_sav.update_acell('A2', str(sav_val - last_trans))
            s_sav.update_acell('B2', "0")
            st.success("Przywrócono środki do budżetu")
            st.rerun()

    # --- INTERFEJS GŁÓWNY ---
    st.markdown(f"### 💎 Dashboard Finansowy | {today.strftime('%d.%m.%Y')}")
    
    # Górne Metryki
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("PORTFEL", f"{balance:,.2f} PLN")
    c2.metric("NA DZIEŃ", f"{daily:,.2f} PLN", f"{dni_m} dni")
    c3.metric("DOCHODY (+800)", f"{inc_total:,.2f} PLN")
    c4.metric("WYDATKI", f"{exp_total:,.2f} PLN", delta=f"-{suma_rat} raty", delta_color="inverse")

    tabs = st.tabs(["📈 ANALIZA", "💸 WPISY", "🏠 STAŁE & RATY", "📅 PLANY", "🛒 LISTY"])

    with tabs[0]:
        col_l, col_r = st.columns([2, 1])
        with col_l:
            if not df_exp.empty:
                fig = px.pie(df_exp, values='Kwota', names='Kategoria', hole=.4, 
                             title="Struktura Wydatków", template="plotly_dark")
                st.plotly_chart(fig, use_container_width=True)
        with col_r:
            st.subheader("Koniec Miesiąca")
            if st.button("🔒 ZAMKNIJ MIESIĄC", use_container_width=True, type="primary"):
                s_sav.update_acell('B2', str(balance))
                s_sav.update_acell('A2', str(sav_val + balance))
                st.balloons(); st.rerun()

    with tabs[1]:
        st.subheader("Nowe Operacje")
        ci, ce = st.columns(2)
        with ci:
            with st.form("form_inc"):
                ni, ki = st.text_input("Nazwa wpływu"), st.number_input("Kwota", key="n_inc")
                if st.form_submit_button("DODAJ PRZYCHÓD"):
                    s_inc.append_row([get_now(), ni, ki]); st.rerun()
        with ce:
            with st.form("form_exp"):
                ne, ke = st.text_input("Nazwa wydatku"), st.number_input("Kwota", key="n_exp")
                kat = st.selectbox("Kategoria", ["Jedzenie", "Dom", "Transport", "Rozrywka", "Inne"])
                if st.form_submit_button("DODAJ WYDATEK"):
                    s_exp.append_row([get_now(), ne, ke, kat, "Zmienny"]); st.rerun()
        
        st.divider()
        st.write("📝 **Historia i Szybka Edycja**")
        df_exp["USUŃ"] = False
        edit_exp = st.data_editor(df_exp, num_rows="dynamic", use_container_width=True, key="ed_main_exp")
        if st.button("ZAPISZ ZMIANY W HISTORII"):
            cleaned = edit_exp[edit_exp["USUŃ"] == False].drop(columns=["USUŃ"])
            s_exp.clear(); s_exp.append_row(["Data i Godzina", "Nazwa", "Kwota", "Kategoria", "Typ"])
            if not cleaned.empty: s_exp.append_rows(cleaned.values.tolist())
            st.rerun()

    with tabs[2]:
        sf, sr = st.columns(2)
        with sf:
            with st.form("form_fix"):
                st.write("🏠 Opłaty Stałe")
                nf, kf = st.text_input("Nazwa opłaty"), st.number_input("Kwota", key="n_fix")
                if st.form_submit_button("DODAJ OPŁATĘ"):
                    s_fix.append_row([get_now(), nf, kf]); st.rerun()
            st.data_editor(df_fix, num_rows="dynamic", use_container_width=True, key="ed_fix_list")
        with sr:
            with st.form("form_rat"):
                st.write("🗓️ Harmonogram Rat")
                nr, kr = st.text_input("Nazwa raty"), st.number_input("Kwota miesięczna", key="n_rat")
                ds, de = st.date_input("Start"), st.date_input("Koniec")
                if st.form_submit_button("DODAJ RATĘ"):
                    s_rat.append_row([nr, kr, str(ds), str(de)]); st.rerun()
            st.data_editor(df_rat, num_rows="dynamic", use_container_width=True, key="ed_rat_list")

    with tabs[3]:
        st.subheader("📅 Planowane większe wydatki")
        with st.form("form_pla"):
            cp1, cp2, cp3 = st.columns(3)
            pn = cp1.text_input("Co planujesz?")
            pk = cp2.number_input("Przewidywana kwota")
            pm = cp3.selectbox("Miesiąc", ["Styczeń", "Luty", "Marzec", "Kwiecień", "Maj", "Czerwiec", "Lipiec", "Sierpień", "Wrzesień", "Październik", "Listopad", "Grudzień"])
            if st.form_submit_button("DODAJ DO PLANERA"):
                s_pla.append_row([get_now(), pn, pk, pm]); st.rerun()
        st.data_editor(df_pla, num_rows="dynamic", use_container_width=True, key="ed_plan_list")

    with tabs[4]:
        sh, ts = st.columns(2)
        with sh:
            st.subheader("🛒 Lista Zakupów")
            with st.form("form_shp"):
                it = st.text_input("Produkt")
                if st.form_submit_button("DODAJ DO LISTY"):
                    s_shp.append_row([get_now(), it]); st.rerun()
            df_shp["OK"] = False
            e_shp = st.data_editor(df_shp, use_container_width=True, key="ed_shp_list")
            if st.button("USUŃ ZAZNACZONE ZAKUPY"):
                rem = e_shp[e_shp["OK"] == False].drop(columns=["OK"])
                s_shp.clear(); s_shp.append_row(["Data i Godzina", "Produkt"])
                if not rem.empty: s_shp.append_rows(rem.values.tolist()); st.rerun()
        with ts:
            st.subheader("✅ Zadania")
            with st.form("form_tsk"):
                tn, td = st.text_input("Zadanie"), st.date_input("Termin")
                if st.form_submit_button("DODAJ ZADANIE"):
                    s_tsk.append_row([get_now(), tn, str(td), "Normalny"]); st.rerun()
            df_tsk["GOTOWE"] = False
            e_tsk = st.data_editor(df_tsk, use_container_width=True, key="ed_tsk_list")
            if st.button("WYCZYŚĆ ZROBIONE ZADANIA"):
                rem_t = e_tsk[e_tsk["GOTOWE"] == False].drop(columns=["GOTOWE"])
                s_tsk.clear(); s_tsk.append_row(["Data i Godzina", "Zadanie", "Termin", "Priorytet"])
                if not rem_t.empty: s_tsk.append_rows(rem_t.values.tolist()); st.rerun()
