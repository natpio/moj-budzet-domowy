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

    # --- POŁĄCZENIE I OPTYMALIZACJA API ---
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
        sheets = ["Przychody", "Wydatki", "Koszty_Stale", "Raty", "Oszczednosci", "Zakupy", "Zadania", "Planowanie"]
        data = {}
        for name in sheets:
            data[name] = pd.DataFrame(sh.worksheet(name).get_all_records())
            time.sleep(0.3)
        return data

    def get_now(): return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Pobieranie danych
    try:
        all_data = load_all_data()
        df_inc = all_data["Przychody"]
        df_exp = all_data["Wydatki"]
        df_fix = all_data["Koszty_Stale"]
        df_rat = all_data["Raty"]
        df_sav = all_data["Oszczednosci"]
        df_shp = all_data["Zakupy"]
        df_tsk = all_data["Zadania"]
        df_pla = all_data["Planowanie"]
    except Exception as e:
        st.error(f"🤠 Problem z połączeniem. Spróbuj odświeżyć stronę za 30 sekund.")
        st.stop()

    # --- OBLICZENIA ---
    today = date.today()
    dni_m = calendar.monthrange(today.year, today.month)[1] - today.day + 1
    p800 = 1600
    
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
        client = get_client()
        ws_sav = client.open("Budzet_Data").worksheet("Oszczednosci")
        try:
            sav_val = float(str(ws_sav.acell('A2').value).replace(',', '.'))
        except:
            sav_val = 0.0
        st.metric("ZŁOTO W SEJFIE", f"{sav_val:,.2f} PLN")
        with st.expander("💰 WYPŁATA"):
            amt = st.number_input("Ile dukatów?", min_value=0.0, key="side_w")
            if st.button("POBIERZ Z SEJFU"):
                ws_sav.update_acell('A2', str(sav_val - amt))
                client.open("Budzet_Data").worksheet("Przychody").append_row([get_now(), "WYPŁATA ZE SKARBCA", amt])
                st.cache_data.clear(); st.rerun()

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
            fig = px.pie(df_exp, values='Kwota', names='Kategoria', hole=.4)
            st.plotly_chart(fig, use_container_width=True)

    with tabs[1]:
        ci, ce = st.columns(2)
        with ci:
            with st.form("f_inc"):
                ni, ki = st.text_input("Skąd wpłata?"), st.number_input("Kwota")
                if st.form_submit_button("DODAJ DOCHÓD"):
                    client.open("Budzet_Data").worksheet("Przychody").append_row([get_now(), ni, ki])
                    st.cache_data.clear(); st.rerun()
        with ce:
            with st.form("f_exp"):
                ne, ke = st.text_input("Na co?"), st.number_input("Kwota")
                ka = st.selectbox("Kategoria", ["Jedzenie", "Dom", "Transport", "Rozrywka", "Inne"])
                if st.form_submit_button("ZAKSIĘGUJ"):
                    client.open("Budzet_Data").worksheet("Wydatki").append_row([get_now(), ne, ke, ka, "Zmienny"])
                    st.cache_data.clear(); st.rerun()
        
        df_exp["USUŃ"] = False
        e_exp = st.data_editor(df_exp, num_rows="dynamic", use_container_width=True)
        if st.button("Zapisz zmiany w historii"):
            cl = e_exp[e_exp["USUŃ"] == False].drop(columns=["USUŃ"])
            ws = client.open("Budzet_Data").worksheet("Wydatki")
            ws.clear(); ws.append_row(["Data i Godzina", "Nazwa", "Kwota", "Kategoria", "Typ"])
            if not cl.empty: ws.append_rows(cl.values.tolist())
            st.cache_data.clear(); st.rerun()

    with tabs[2]:
        cf, cr = st.columns(2)
        with cf:
            with st.form("f_fix"):
                nf, kf = st.text_input("Opłata stała"), st.number_input("Kwota", key="fix_k")
                if st.form_submit_button("DODAJ STAŁĄ"):
                    client.open("Budzet_Data").worksheet("Koszty_Stale").append_row([get_now(), nf, kf])
                    st.cache_data.clear(); st.rerun()
            df_fix["USUŃ"] = False
            e_fix = st.data_editor(df_fix, use_container_width=True, key="ed_fix")
            if st.button("Zapisz zmiany w Stałych"):
                cl_f = e_fix[e_fix["USUŃ"] == False].drop(columns=["USUŃ"])
                ws_f = client.open("Budzet_Data").worksheet("Koszty_Stale")
                ws_f.clear(); ws_f.append_row(["Data i Godzina", "Nazwa", "Kwota"])
                if not cl_f.empty: ws_f.append_rows(cl_f.values.tolist())
                st.cache_data.clear(); st.rerun()

        with cr:
            with st.form("f_rat"):
                nr, kr = st.text_input("Rata"), st.number_input("Kwota", key="rat_k")
                ds, de = st.date_input("Start"), st.date_input("Koniec")
                if st.form_submit_button("DODAJ RATĘ"):
                    client.open("Budzet_Data").worksheet("Raty").append_row([nr, kr, str(ds), str(de)])
                    st.cache_data.clear(); st.rerun()
            
            df_rat["USUŃ"] = False
            e_rat = st.data_editor(df_rat, use_container_width=True, key="ed_rat")
            if st.button("Zatwierdź usuwanie rat"):
                cl_r = e_rat[e_rat["USUŃ"] == False].drop(columns=["USUŃ"])
                # KLUCZOWA POPRAWKA: Zamiana dat na tekst przed wysłaniem do Google
                if not cl_r.empty:
                    for col in ['Start', 'Koniec']:
                        if col in cl_r.columns:
                            cl_r[col] = cl_r[col].dt.strftime('%Y-%m-%d')
                
                ws_r = client.open("Budzet_Data").worksheet("Raty")
                ws_r.clear(); ws_r.append_row(["Rata", "Kwota", "Start", "Koniec"])
                if not cl_r.empty: ws_r.append_rows(cl_r.values.tolist())
                st.cache_data.clear(); st.rerun()

    with tabs[3]:
        with st.form("f_pla"):
            pn, pk = st.text_input("Plan"), st.number_input("Kwota", key="pla_k")
            pm = st.selectbox("Miesiąc", ["Styczeń", "Luty", "Marzec", "Kwiecień", "Maj", "Czerwiec", "Lipiec", "Sierpień", "Wrzesień", "Październik", "Listopad", "Grudzień"])
            if st.form_submit_button("PLANUJ"):
                client.open("Budzet_Data").worksheet("Planowanie").append_row([get_now(), pn, pk, pm])
                st.cache_data.clear(); st.rerun()
        df_pla["USUŃ"] = False
        e_pla = st.data_editor(df_pla, use_container_width=True)
        if st.button("Zaktualizuj plany"):
            cl_p = e_pla[e_pla["USUŃ"] == False].drop(columns=["USUŃ"])
            ws_p = client.open("Budzet_Data").worksheet("Planowanie")
            ws_p.clear(); ws_p.append_row(["Data i Godzina", "Cel", "Kwota", "Miesiąc"])
            if not cl_p.empty: ws_p.append_rows(cl_p.values.tolist())
            st.cache_data.clear(); st.rerun()

    with tabs[4]:
        cs, ct = st.columns(2)
        with cs:
            st.write("🛒 Zakupy")
            with st.form("f_shp"):
                it = st.text_input("Produkt")
                if st.form_submit_button("DODAJ"):
                    client.open("Budzet_Data").worksheet("Zakupy").append_row([get_now(), it])
                    st.cache_data.clear(); st.rerun()
            df_shp["USUŃ"] = False
            e_shp = st.data_editor(df_shp, use_container_width=True, key="ed_shp")
            if st.button("Usuń zaznaczone zakupy"):
                cl_s = e_shp[e_shp["USUŃ"] == False].drop(columns=["USUŃ"])
                ws_s = client.open("Budzet_Data").worksheet("Zakupy")
                ws_s.clear(); ws_s.append_row(["Data i Godzina", "Produkt"])
                if not cl_s.empty: ws_s.append_rows(cl_s.values.tolist())
                st.cache_data.clear(); st.rerun()
        with ct:
            st.write("✅ Zadania")
            with st.form("f_tsk"):
                tn, td = st.text_input("Zadanie"), st.date_input("Termin")
                if st.form_submit_button("DODAJ ZADANIE"):
                    client.open("Budzet_Data").worksheet("Zadania").append_row([get_now(), tn, str(td), "Normalny"])
                    st.cache_data.clear(); st.rerun()
            df_tsk["USUŃ"] = False
            e_tsk = st.data_editor(df_tsk, use_container_width=True, key="ed_tsk")
            if st.button("Usuń zaznaczone zadania"):
                cl_t = e_tsk[e_tsk["USUŃ"] == False].drop(columns=["USUŃ"])
                ws_t = client.open("Budzet_Data").worksheet("Zadania")
                ws_t.clear(); ws_t.append_row(["Data i Godzina", "Zadanie", "Termin", "Priorytet"])
                if not cl_t.empty: ws_t.append_rows(cl_t.values.tolist())
                st.cache_data.clear(); st.rerun()
