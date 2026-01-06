import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
from google.oauth2 import service_account
from datetime import datetime, date
import calendar

# --- KONFIGURACJA STRONY (MUSI BYĆ NA SAMYM GÓRZE) ---
st.set_page_config(page_title="Pro Budget Master 2026", layout="wide", page_icon="💰")

# --- FUNKCJA LOGOWANIA ---
def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["credentials"]["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.title("🔒 Logowanie")
        st.text_input("Hasło", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Hasło", type="password", on_change=password_entered, key="password")
        st.error("❌ Błędne hasło")
        return False
    else:
        return True

if check_password():
    # --- STYLIZACJA CSS ---
    st.markdown("""
        <style>
        .stMetric { background-color: #1a1c24; padding: 15px; border-radius: 10px; border: 1px solid #3e4452; }
        [data-testid="stForm"] { border: 1px solid #3e4452; border-radius: 10px; }
        </style>
        """, unsafe_allow_html=True)

    # --- FUNKCJE POMOCNICZE ---
    def get_now():
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def get_sheet(sheet_name):
        try:
            creds_dict = st.secrets["gcp_service_account"]
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=scope)
            client = gspread.authorize(creds)
            return client.open("Budzet_Data").worksheet(sheet_name)
        except Exception as e:
            st.error(f"Błąd arkusza {sheet_name}: {e}")
            return None

    def calculate_800plus():
        today = date.today()
        dzieci = [date(2018, 8, 1), date(2022, 11, 1)]
        suma = 0
        for bday in dzieci:
            wiek = today.year - bday.year - ((today.month, today.day) < (bday.month, bday.day))
            if wiek < 18: suma += 800
        return suma

    # --- POBIERANIE DANYCH ---
    s_inc = get_sheet("Przychody")
    s_exp = get_sheet("Wydatki")
    s_fix = get_sheet("Koszty_Stale")
    s_rat = get_sheet("Raty")
    s_sav = get_sheet("Oszczednosci")
    s_shp = get_sheet("Zakupy")
    s_tsk = get_sheet("Zadania")
    s_pla = get_sheet("Planowanie")

    df_inc = pd.DataFrame(s_inc.get_all_records()) if s_inc else pd.DataFrame()
    df_exp = pd.DataFrame(s_exp.get_all_records()) if s_exp else pd.DataFrame()
    df_fix = pd.DataFrame(s_fix.get_all_records()) if s_fix else pd.DataFrame()
    df_rat = pd.DataFrame(s_rat.get_all_records()) if s_rat else pd.DataFrame()
    df_shp = pd.DataFrame(s_shp.get_all_records()) if s_shp else pd.DataFrame()
    df_tsk = pd.DataFrame(s_tsk.get_all_records()) if s_tsk else pd.DataFrame()
    df_pla = pd.DataFrame(s_pla.get_all_records()) if s_pla else pd.DataFrame()

    # --- LOGIKA FINANSOWA ---
    today_dt = pd.to_datetime(date.today())
    suma_rat = 0
    if not df_rat.empty:
        df_rat['Start'] = pd.to_datetime(df_rat['Start'])
        df_rat['Koniec'] = pd.to_datetime(df_rat['Koniec'])
        aktywne = df_rat[(df_rat['Start'] <= today_dt) & (df_rat['Koniec'] >= today_dt)]
        suma_rat = aktywne['Kwota'].sum()

    total_inc = (df_inc['Kwota'].sum() if not df_inc.empty else 0) + calculate_800plus()
    total_exp = (df_exp['Kwota'].sum() if not df_exp.empty else 0) + (df_fix['Kwota'].sum() if not df_fix.empty else 0) + suma_rat
    bilans = total_inc - total_exp
    dni_do_konca = calendar.monthrange(date.today().year, date.today().month)[1] - date.today().day + 1
    dzienny = bilans / dni_do_konca if dni_do_konca > 0 else bilans

    # --- SIDEBAR ---
    with st.sidebar:
        st.title("🏦 SKARBIEC")
        try:
            sav_val = float(str(s_sav.acell('A2').value).replace(',', '.'))
            last_trans = float(str(s_sav.acell('B2').value).replace(',', '.'))
        except:
            sav_val, last_trans = 0.0, 0.0
        st.metric("Oszczędności", f"{sav_val:,.2f} PLN")
        
        with st.expander("🚨 Ratunek"):
            kwota_r = st.number_input("Pobierz", min_value=0.0, max_value=sav_val, step=100.0)
            if st.button("WYPŁAĆ"):
                s_sav.update_acell('A2', str(sav_val - kwota_r))
                s_inc.append_row([get_now(), "RATUNEK ZE SKARBCA", kwota_r])
                st.rerun()
        if st.button("⏪ Cofnij zamknięcie"):
            s_sav.update_acell('A2', str(sav_val - last_trans))
            s_sav.update_acell('B2', "0")
            st.rerun()

    # --- TABS ---
    t1, t2, t3, t4, t5, t6 = st.tabs(["📊 ANALIZA", "💸 WPISY", "🏠 STAŁE/RATY", "📅 PLANOWANIE", "🛒 ZAKUPY", "✅ ZADANIA"])

    with t1:
        c1, c2, c3 = st.columns(3)
        c1.metric("Dostępne", f"{bilans:,.2f} PLN")
        c2.metric("Na dzień", f"{dzienny:,.2f} PLN", delta=f"{dni_do_konca} dni")
        c3.metric("800+", f"{calculate_800plus()} PLN")
        if st.button("🔒 ZAMKNIJ MIESIĄC"):
            s_sav.update_acell('B2', str(bilans))
            s_sav.update_acell('A2', str(sav_val + bilans))
            st.balloons(); st.rerun()

    with t2:
        st.subheader("Wydatki i Dochody")
        col_in, col_ex = st.columns(2)
        with col_in:
            with st.form("f_inc"):
                ni, ki = st.text_input("Nazwa wpływu"), st.number_input("Kwota", key="ki")
                if st.form_submit_button("Dodaj dochód"):
                    s_inc.append_row([get_now(), ni, ki]); st.rerun()
        with col_ex:
            with st.form("f_exp"):
                ne, ke = st.text_input("Nazwa wydatku"), st.number_input("Kwota", key="ke")
                kat = st.selectbox("Kategoria", ["Jedzenie", "Dom", "Transport", "Rozrywka", "Inne"])
                if st.form_submit_button("Dodaj wydatek"):
                    s_exp.append_row([get_now(), ne, ke, kat, "Zmienny"]); st.rerun()
        
        st.write("📝 **Edytuj Wydatki**")
        df_exp["USUŃ"] = False
        # TUTAJ KLUCZ: key="editor_wydatki"
        edit_exp = st.data_editor(df_exp, num_rows="dynamic", use_container_width=True, key="editor_wydatki")
        if st.button("Zapisz zmiany w wydatkach"):
            cleaned = edit_exp[edit_exp["USUŃ"] == False].drop(columns=["USUŃ"])
            s_exp.clear(); s_exp.append_row(["Data i Godzina", "Nazwa", "Kwota", "Kategoria", "Typ"])
            if not cleaned.empty: s_exp.append_rows(cleaned.values.tolist())
            st.rerun()

    with t3:
        st.subheader("Koszty Stałe i Raty")
        col_f, col_r = st.columns(2)
        with col_f:
            with st.form("f_fix"):
                nf, kf = st.text_input("Opłata stała"), st.number_input("Kwota", key="kf")
                if st.form_submit_button("Dodaj stały"):
                    s_fix.append_row([get_now(), nf, kf]); st.rerun()
        with col_r:
            with st.form("f_rat"):
                nr, kr = st.text_input("Rata"), st.number_input("Miesięcznie", key="kr")
                ds, de = st.date_input("Start"), st.date_input("Koniec")
                if st.form_submit_button("Dodaj ratę"):
                    s_rat.append_row([nr, kr, str(ds), str(de)]); st.rerun()
        
        st.write("🛠️ **Edytuj Raty**")
        # TUTAJ KLUCZ: key="editor_raty"
        edit_rat = st.data_editor(df_rat, num_rows="dynamic", use_container_width=True, key="editor_raty")
        if st.button("Zapisz zmiany w ratach"):
            s_rat.clear(); s_rat.append_row(["Nazwa", "Kwota", "Start", "Koniec"])
            if not edit_rat.empty: s_rat.append_rows(edit_rat.values.tolist())
            st.rerun()

    with t4:
        st.subheader("📅 Planowanie Przyszłości")
        with st.form("f_pla"):
            pn, pk = st.text_input("Co zaplanować?"), st.number_input("Kwota")
            pm = st.selectbox("Miesiąc", ["Styczeń", "Luty", "Marzec", "Kwiecień", "Maj", "Czerwiec", "Lipiec", "Sierpień", "Wrzesień", "Październik", "Listopad", "Grudzień"])
            if st.form_submit_button("Zapisz plan"):
                s_pla.append_row([get_now(), pn, pk, pm]); st.rerun()
        
        # TUTAJ KLUCZ: key="editor_planowanie"
        df_pla["USUŃ"] = False
        edit_pla = st.data_editor(df_pla, num_rows="dynamic", use_container_width=True, key="editor_planowanie")
        if st.button("Zapisz zmiany w planach"):
            cl_pla = edit_pla[edit_pla["USUŃ"] == False].drop(columns=["USUŃ"])
            s_pla.clear(); s_pla.append_row(["Data i Godzina", "Nazwa", "Kwota", "Miesiąc/Rok"])
            if not cl_pla.empty: s_pla.append_rows(cl_pla.values.tolist())
            st.rerun()

    with t5:
        st.subheader("🛒 Zakupy")
        with st.form("f_shp"):
            pr = st.text_input("Produkt")
            if st.form_submit_button("Dodaj"):
                s_shp.append_row([get_now(), pr]); st.rerun()
        df_shp["KUPIŁEM"] = False
        # TUTAJ KLUCZ: key="editor_zakupy"
        e_shp = st.data_editor(df_shp, use_container_width=True, key="editor_zakupy")
        if st.button("Usuń kupione"):
            rem = e_shp[e_shp["KUPIŁEM"] == False].drop(columns=["KUPIŁEM"])
            s_shp.clear(); s_shp.append_row(["Data i Godzina", "Produkt"])
            if not rem.empty: s_shp.append_rows(rem.values.tolist()); st.rerun()

    with t6:
        st.subheader("✅ Zadania")
        with st.form("f_tsk"):
            zt, zd = st.text_input("Zadanie"), st.date_input("Termin")
            if st.form_submit_button("Dodaj zadanie"):
                s_tsk.append_row([get_now(), zt, str(zd), "Normalny"]); st.rerun()
        df_tsk["GOTOWE"] = False
        # TUTAJ KLUCZ: key="editor_zadania"
        e_tsk = st.data_editor(df_tsk, use_container_width=True, key="editor_zadania")
        if st.button("Usuń zrobione"):
            rem_t = e_tsk[e_tsk["GOTOWE"] == False].drop(columns=["GOTOWE"])
            s_tsk.clear(); s_tsk.append_row(["Data i Godzina", "Zadanie", "Termin", "Priorytet"])
            if not rem_t.empty: s_tsk.append_rows(rem_t.values.tolist()); st.rerun()
