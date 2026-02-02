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
                st.error("❌ Zły klucz!")
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
        .stButton>button { background-color: #a1887f !important; color: white !important; border: 2px solid #5d4037 !important; font-weight: bold !important; width: 100%; }
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
            # Pobranie danych i zamiana na DataFrame
            rows = sh.worksheet(name).get_all_records()
            data[name] = pd.DataFrame(rows)
            time.sleep(0.5) # Zwiększony odstęp dla stabilności API
        return data

    def get_now(): return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        all_d = load_all_data()
        df_inc = all_d["Przychody"]
        df_exp = all_d["Wydatki"]
        df_fix = all_d["Koszty_Stale"]
        df_rat = all_d["Raty"]
        df_sav = all_d["Oszczednosci"]
        df_shp = all_d["Zakupy"]
        df_tsk = all_d["Zadania"]
        df_pla = all_d["Planowanie"]
    except Exception as e:
        st.error(f"🤠 Serwer Google odpoczywa. Błąd: {e}")
        st.stop()

    # --- FILTROWANIE CZASU ---
    today = date.today()
    current_month_str = today.strftime("%Y-%m")
    # Ile dni do końca miesiąca
    last_day = calendar.monthrange(today.year, today.month)[1]
    dni_m = last_day - today.day + 1
    p800 = 1600 # Stały dodatek

    # Filtrowanie przychodów i wydatków tylko dla obecnego miesiąca
    if not df_inc.empty and 'Data i Godzina' in df_inc.columns:
        df_inc_m = df_inc[df_inc['Data i Godzina'].astype(str).str.contains(current_month_str, na=False)].copy()
    else:
        df_inc_m = pd.DataFrame(columns=df_inc.columns)

    if not df_exp.empty and 'Data i Godzina' in df_exp.columns:
        df_exp_m = df_exp[df_exp['Data i Godzina'].astype(str).str.contains(current_month_str, na=False)].copy()
    else:
        df_exp_m = pd.DataFrame(columns=df_exp.columns)

    # Raty aktywne
    df_rat_active = pd.DataFrame()
    suma_rat = 0
    if not df_rat.empty:
        df_rat['Start'] = pd.to_datetime(df_rat['Start'])
        df_rat['Koniec'] = pd.to_datetime(df_rat['Koniec'])
        mask = (df_rat['Start'] <= pd.Timestamp(today)) & (df_rat['Koniec'] >= pd.Timestamp(today))
        df_rat_active = df_rat[mask].copy()
        suma_rat = df_rat_active['Kwota'].sum()

    # Obliczenia balansu
    inc_total = (df_inc_m['Kwota'].sum() if not df_inc_m.empty else 0) + p800
    exp_total = (df_exp_m['Kwota'].sum() if not df_exp_m.empty else 0) + (df_fix['Kwota'].sum() if not df_fix.empty else 0) + suma_rat
    balance = inc_total - exp_total
    daily = balance / dni_m if dni_m > 0 else balance

    # --- SIDEBAR (SEJF + MROŻENIE + ZAMKNIĘCIE) ---
    with st.sidebar:
        st.markdown("<h1 style='text-align:center;'>🤠 SEJF</h1>", unsafe_allow_html=True)
        client = get_client()
        sh = client.open("Budzet_Data")
        ws_sav = sh.worksheet("Oszczednosci")
        
        # Pobranie wartości z Sejfu (komórka A2)
        try:
            val_raw = ws_sav.acell('A2').value
            sav_val = float(str(val_raw).replace(',', '.')) if val_raw else 0.0
        except:
            sav_val = 0.0
            
        st.metric("ZŁOTO W SEJFIE", f"{sav_val:,.2f} PLN")
        
        st.divider()
        with st.expander("💰 ZARZĄDZAJ SKABCEM"):
            amt_s = st.number_input("Ile dukatów?", min_value=0.0, step=10.0, key="amt_sidebar")
            c_in, c_out = st.columns(2)
            if c_in.button("WPŁAĆ"):
                if amt_s > 0:
                    ws_sav.update_acell('A2', str(sav_val + amt_s))
                    sh.worksheet("Wydatki").append_row([get_now(), "ZAMROŻONE: Wpłata do Sejfu", amt_s, "Inne", "Oszczędności"])
                    st.success(f"Zamrożono {amt_s} PLN!")
                    st.cache_data.clear(); time.sleep(1); st.rerun()
            if c_out.button("POBIERZ"):
                if amt_s > 0:
                    ws_sav.update_acell('A2', str(sav_val - amt_s))
                    sh.worksheet("Przychody").append_row([get_now(), "Wypłata z Sejfu", amt_s])
                    st.success(f"Pobrano {amt_s} PLN!")
                    st.cache_data.clear(); time.sleep(1); st.rerun()

        st.divider()
        if st.button("🏜️ ZAMKNIJ MIESIĄC"):
            # 1. Przesunięcie nadwyżki do sejfu
            new_sav = sav_val + balance
            ws_sav.update_acell('A2', str(new_sav))
            
            # 2. Logowanie zamknięcia w przychodach jako "Przeniesienie z poprzedniego m-ca" (opcjonalnie)
            # Tutaj możesz dodać czyszczenie tabel, jeśli chcesz zacząć od zera.
            
            st.balloons()
            st.success(f"Miesiąc rozliczony! Przelano {balance:.2f} PLN do sejfu.")
            st.cache_data.clear(); time.sleep(1); st.rerun()

    # --- DASHBOARD ---
    st.markdown("<h1 style='text-align: center;'>📜 KSIĘGA RACHUNKOWA</h1>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    c1.metric("💰 PORTFEL (MIESIĄC)", f"{balance:,.2f} PLN")
    c2.metric("☀️ NA DZIEŃ", f"{daily:,.2f} PLN")

    h_inc, h_exp = st.columns(2)
    with h_inc:
        st.metric("📈 DOCHODY", f"{inc_total:,.2f} PLN")
        with st.expander("🔍 Szczegóły wpływów"):
            # FIX: Sprawdzenie czy DataFrame nie jest pusty przed wysłaniem do st.table
            if not df_inc_m.empty:
                st.table(df_inc_m[["Nazwa", "Kwota"]])
            else:
                st.info("Brak wpisów w tym miesiącu.")

    with h_exp:
        st.metric("📉 WYDATKI", f"{exp_total:,.2f} PLN")
        with st.expander("🔍 Pełna lista kosztów"):
            # Łączenie wydatków zmiennych, stałych i rat
            e_list = []
            if not df_exp_m.empty: e_list.append(df_exp_m[["Nazwa", "Kwota"]])
            if not df_fix.empty: e_list.append(df_fix[["Nazwa", "Kwota"]])
            if not df_rat_active.empty: e_list.append(df_rat_active[["Rata", "Kwota"]].rename(columns={"Rata": "Nazwa"}))
            
            if e_list:
                e_all = pd.concat(e_list, ignore_index=True)
                st.table(e_all)
            else:
                st.info("Brak zarejestrowanych kosztów.")

    # --- ZAKŁADKI OPERACYJNE ---
    tabs = st.tabs(["💸 Wpisy", "🏠 Stałe & Raty", "📅 Plany", "🛒 Listy"])

    with tabs[0]:
        ci, ce = st.columns(2)
        with ci:
            with st.form("f_inc", clear_on_submit=True):
                st.subheader("➕ Przychód")
                ni, ki = st.text_input("Skąd?"), st.number_input("Kwota", key="f_inc_k", min_value=0.0)
                if st.form_submit_button("DODAJ"):
                    if ni:
                        sh.worksheet("Przychody").append_row([get_now(), ni, ki])
                        st.cache_data.clear(); st.rerun()
                    else: st.warning("Podaj nazwę!")

        with ce:
            with st.form("f_exp", clear_on_submit=True):
                st.subheader("➖ Wydatek")
                ne, ke = st.text_input("Na co?"), st.number_input("Kwota", key="f_exp_k", min_value=0.0)
                ka = st.selectbox("Kategoria", ["Jedzenie", "Dom", "Transport", "Rozrywka", "Inne"])
                if st.form_submit_button("DODAJ"):
                    if ne:
                        sh.worksheet("Wydatki").append_row([get_now(), ne, ke, ka, "Zmienny"])
                        st.cache_data.clear(); st.rerun()
                    else: st.warning("Podaj nazwę!")
        
        st.divider()
        st.subheader("📝 Edycja historii wydatków")
        df_exp["USUŃ"] = False
        ed_e = st.data_editor(df_exp, num_rows="dynamic", use_container_width=True, key="ed_wpisy_v_final")
        if st.button("Zapisz zmiany w historii wpisów"):
            cl = ed_e[ed_e["USUŃ"] == False].drop(columns=["USUŃ"])
            ws = sh.worksheet("Wydatki")
            ws.clear()
            ws.append_row(["Data i Godzina", "Nazwa", "Kwota", "Kategoria", "Typ"])
            if not cl.empty: ws.append_rows(cl.values.tolist())
            st.cache_data.clear(); st.rerun()

    with tabs[1]:
        cf, cr = st.columns(2)
        with cf:
            with st.form("f_fix"):
                st.subheader("🏠 Koszty Stałe")
                nf, kf = st.text_input("Opłata"), st.number_input("Kwota", key="f_fix_k", min_value=0.0)
                if st.form_submit_button("DODAJ"):
                    sh.worksheet("Koszty_Stale").append_row([get_now(), nf, kf])
                    st.cache_data.clear(); st.rerun()
            
            st.subheader("Zarządzaj stałymi")
            df_fix["USUŃ"] = False
            ed_f = st.data_editor(df_fix, use_container_width=True, key="ed_stale_v_final")
            if st.button("Zapisz zmiany w Stałych"):
                cl_f = ed_f[ed_f["USUŃ"] == False].drop(columns=["USUŃ"])
                ws_f = sh.worksheet("Koszty_Stale")
                ws_f.clear()
                ws_f.append_row(["Data i Godzina", "Nazwa", "Kwota"])
                if not cl_f.empty: ws_f.append_rows(cl_f.values.tolist())
                st.cache_data.clear(); st.rerun()

        with cr:
            with st.form("f_rat"):
                st.subheader("🗓️ Raty")
                nr, kr = st.text_input("Rata"), st.number_input("Kwota", key="f_rat_k", min_value=0.0)
                ds, de = st.date_input("Start"), st.date_input("Koniec")
                if st.form_submit_button("DODAJ RATĘ"):
                    sh.worksheet("Raty").append_row([nr, kr, str(ds), str(de)])
                    st.cache_data.clear(); st.rerun()
            
            st.subheader("Zarządzaj ratami")
            df_rat["USUŃ"] = False
            ed_r = st.data_editor(df_rat, use_container_width=True, key="ed_raty_v_final")
            if st.button("Zapisz zmiany w Ratach"):
                cl_r = ed_r[ed_r["USUŃ"] == False].drop(columns=["USUŃ"])
                if not cl_r.empty:
                    for c in ['Start', 'Koniec']: 
                        cl_r[c] = pd.to_datetime(cl_r[c]).dt.strftime('%Y-%m-%d')
                ws_r = sh.worksheet("Raty")
                ws_r.clear()
                ws_r.append_row(["Rata", "Kwota", "Start", "Koniec"])
                if not cl_r.empty: ws_r.append_rows(cl_r.values.tolist())
                st.cache_data.clear(); st.rerun()

    with tabs[2]:
        with st.form("f_pla"):
            st.subheader("📅 Planowanie zakupów")
            pn, pk = st.text_input("Cel"), st.number_input("Kwota", key="f_pla_k", min_value=0.0)
            pm = st.selectbox("Miesiąc", ["Styczeń", "Luty", "Marzec", "Kwiecień", "Maj", "Czerwiec", "Lipiec", "Sierpień", "Wrzesień", "Październik", "Listopad", "Grudzień"])
            if st.form_submit_button("ZAPLANUJ"):
                sh.worksheet("Planowanie").append_row([get_now(), pn, pk, pm])
                st.cache_data.clear(); st.rerun()
        
        df_pla["USUŃ"] = False
        ed_p = st.data_editor(df_pla, use_container_width=True, key="ed_plany_v_final")
        if st.button("Zaktualizuj Plany"):
            cl_p = ed_p[ed_p["USUŃ"] == False].drop(columns=["USUŃ"])
            ws_p = sh.worksheet("Planowanie")
            ws_p.clear()
            ws_p.append_row(["Data i Godzina", "Cel", "Kwota", "Miesiąc"])
            if not cl_p.empty: ws_p.append_rows(cl_p.values.tolist())
            st.cache_data.clear(); st.rerun()

    with tabs[3]:
        cs, ct = st.columns(2)
        with cs:
            st.subheader("🛒 Lista Zakupów")
            with st.form("f_sho", clear_on_submit=True):
                it = st.text_input("Produkt")
                if st.form_submit_button("DODAJ DO LISTY"):
                    if it:
                        sh.worksheet("Zakupy").append_row([get_now(), it])
                        st.cache_data.clear(); st.rerun()
            
            df_shp["USUŃ"] = False
            ed_s = st.data_editor(df_shp, use_container_width=True, key="ed_zakupy_v_final")
            if st.button("Usuń wybrane zakupy"):
                cl_s = ed_s[ed_s["USUŃ"] == False].drop(columns=["USUŃ"])
                ws_s = sh.worksheet("Zakupy")
                ws_s.clear()
                ws_s.append_row(["Data i Godzina", "Produkt"])
                if not cl_s.empty: ws_s.append_rows(cl_s.values.tolist())
                st.cache_data.clear(); st.rerun()

        with ct:
            st.subheader("✅ Zadania")
            with st.form("f_tsk", clear_on_submit=True):
                tn, td = st.text_input("Zadanie"), st.date_input("Termin")
                if st.form_submit_button("DODAJ ZADANIE"):
                    if tn:
                        sh.worksheet("Zadania").append_row([get_now(), tn, str(td), "Normalny"])
                        st.cache_data.clear(); st.rerun()
            
            df_tsk["USUŃ"] = False
            ed_t = st.data_editor(df_tsk, use_container_width=True, key="ed_zadania_v_final")
            if st.button("Usuń wybrane zadania"):
                cl_t = ed_t[ed_t["USUŃ"] == False].drop(columns=["USUŃ"])
                ws_t = sh.worksheet("Zadania")
                ws_t.clear()
                ws_t.append_row(["Data i Godzina", "Zadanie", "Termin", "Priorytet"])
                if not cl_t.empty: ws_t.append_rows(cl_t.values.tolist())
                st.cache_data.clear(); st.rerun()
