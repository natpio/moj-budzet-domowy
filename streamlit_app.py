import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
from google.oauth2 import service_account
from datetime import datetime, date
import calendar

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Budżet Pro 2026", layout="wide", page_icon="💎")

# --- FUNKCJA LOGOWANIA ---
def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["credentials"]["password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.markdown("<h2 style='text-align: center;'>🔐 System Budżetowy 99 Pro</h2>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            st.text_input("Hasło dostępu", type="password", on_change=password_entered, key="password")
        return False
    return st.session_state.get("password_correct", False)

if check_password():
    # --- ZAAWANSOWANY STYL CSS ---
    st.markdown("""
        <style>
        /* Tło i główny font */
        .main { background-color: #0e1117; }
        
        /* Stylizacja metryk */
        [data-testid="stMetric"] {
            background-color: #161b22;
            border: 1px solid #30363d;
            padding: 20px;
            border-radius: 15px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        
        /* Przyciski */
        .stButton>button {
            border-radius: 8px;
            font-weight: 600;
            transition: all 0.3s;
        }
        
        /* Formularze */
        [data-testid="stForm"] {
            border: 1px solid #30363d;
            border-radius: 15px;
            padding: 25px;
            background-color: #161b22;
        }

        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {
            gap: 24px;
        }
        .stTabs [data-baseweb="tab"] {
            height: 50px;
            font-weight: 600;
        }
        </style>
        """, unsafe_allow_html=True)

    # --- FUNKCJE ---
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

    inc_total = df_inc['Kwota'].sum() + p800 if not df_inc.empty else p800
    exp_total = (df_exp['Kwota'].sum() if not df_exp.empty else 0) + (df_fix['Kwota'].sum() if not df_fix.empty else 0) + suma_rat
    balance = inc_total - exp_total
    daily = balance / dni_m if dni_m > 0 else balance

    # --- SIDEBAR ---
    with st.sidebar:
        st.image("https://cdn-icons-png.flaticon.com/512/1611/1611154.png", width=100)
        st.title("Skarbiec")
        sav_a2 = float(str(s_sav.acell('A2').value).replace(',', '.'))
        st.metric("Suma Oszczędności", f"{sav_a2:,.2f} PLN")
        
        with st.expander("💸 Szybka Wypłata"):
            amt = st.number_input("Kwota", min_value=0.0, step=100.0)
            if st.button("Pobierz"):
                s_sav.update_acell('A2', str(sav_a2 - amt))
                s_inc.append_row([get_now(), "WYPŁATA ZE SKARBCA", amt])
                st.rerun()
        st.divider()
        if st.button("🔄 Cofnij zamknięcie"):
            last = float(str(s_sav.acell('B2').value).replace(',', '.'))
            s_sav.update_acell('A2', str(sav_a2 - last))
            s_sav.update_acell('B2', "0")
            st.rerun()

    # --- MAIN UI ---
    st.title("💎 Dashboard Finansowy")
    
    # Górne Metryki
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Portfel (Dostępne)", f"{balance:,.2f} PLN")
    m2.metric("Budżet Dzienny", f"{daily:,.2f} PLN", f"{dni_m} dni")
    m3.metric("Dochody (z 800+)", f"{inc_total:,.2f} PLN")
    m4.metric("Wydatki", f"{exp_total:,.2f} PLN", delta=f"-{suma_rat} raty", delta_color="inverse")

    st.write("")

    tabs = st.tabs(["📈 Analiza", "💸 Operacje", "🏠 Stałe & Raty", "📅 Plany", "🛒 Listy"])

    with tabs[0]:
        c_l, c_r = st.columns([2, 1])
        with c_l:
            if not df_exp.empty:
                fig = px.bar(df_exp.tail(10), x='Data i Godzina', y='Kwota', color='Kategoria', 
                             title="Ostatnie 10 wydatków", template="plotly_dark")
                st.plotly_chart(fig, use_container_width=True)
        with c_r:
            st.subheader("Akcja")
            if st.button("🔒 Zamknij Miesiąc", use_container_width=True, type="primary"):
                s_sav.update_acell('B2', str(balance))
                s_sav.update_acell('A2', str(sav_a2 + balance))
                st.balloons(); st.rerun()
            st.info("Zamknięcie miesiąca przenosi bilans do skarbca.")

    with tabs[1]:
        col1, col2 = st.columns(2)
        with col1:
            with st.form("add_inc"):
                st.subheader("➕ Przychód")
                n, k = st.text_input("Nazwa"), st.number_input("Kwota", key="inc")
                if st.form_submit_button("Dodaj"):
                    s_inc.append_row([get_now(), n, k]); st.rerun()
        with col2:
            with st.form("add_exp"):
                st.subheader("➖ Wydatek")
                ne, ke = st.text_input("Nazwa"), st.number_input("Kwota", key="exp")
                kat = st.selectbox("Kat.", ["Jedzenie", "Dom", "Transport", "Rozrywka", "Zdrowie", "Inne"])
                if st.form_submit_button("Zaksięguj"):
                    s_exp.append_row([get_now(), ne, ke, kat, "Zmienny"]); st.rerun()
        
        st.divider()
        st.subheader("📝 Historia i Edycja")
        df_exp["USUŃ"] = False
        e_exp = st.data_editor(df_exp, num_rows="dynamic", use_container_width=True, key="ed_exp_pro")
        if st.button("Zapisz zmiany w historii"):
            cl = e_exp[e_exp["USUŃ"] == False].drop(columns=["USUŃ"])
            s_exp.clear(); s_exp.append_row(["Data i Godzina", "Nazwa", "Kwota", "Kategoria", "Typ"])
            if not cl.empty: s_exp.append_rows(cl.values.tolist())
            st.rerun()

    with tabs[2]:
        f1, f2 = st.columns(2)
        with f1:
            with st.form("add_fix"):
                st.subheader("🏠 Koszt Stały")
                nf, kf = st.text_input("Nazwa"), st.number_input("Kwota")
                if st.form_submit_button("Dodaj"):
                    s_fix.append_row([get_now(), nf, kf]); st.rerun()
            st.data_editor(df_fix, use_container_width=True, key="ed_fix")
        with f2:
            with st.form("add_rat"):
                st.subheader("🗓️ Rata")
                nr, kr = st.text_input("Nazwa"), st.number_input("Kwota")
                ds, de = st.date_input("Start"), st.date_input("Koniec")
                if st.form_submit_button("Dodaj"):
                    s_rat.append_row([nr, kr, str(ds), str(de)]); st.rerun()
            st.data_editor(df_rat, use_container_width=True, key="ed_rat")

    with tabs[3]:
        st.subheader("📅 Planowanie długoterminowe")
        with st.form("add_plan"):
            cp1, cp2, cp3 = st.columns(3)
            pn = cp1.text_input("Nazwa planu")
            pk = cp2.number_input("Kwota")
            pm = cp3.selectbox("Miesiąc", ["Styczeń", "Luty", "Marzec", "Kwiecień", "Maj", "Czerwiec", "Lipiec", "Sierpień", "Wrzesień", "Październik", "Listopad", "Grudzień"])
            if st.form_submit_button("Dodaj do planu"):
                s_pla.append_row([get_now(), pn, pk, pm]); st.rerun()
        st.data_editor(df_pla, use_container_width=True, key="ed_pla")

    with tabs[4]:
        l1, l2 = st.columns(2)
        with l1:
            st.subheader("🛒 Zakupy")
            with st.form("add_shp"):
                it = st.text_input("Produkt")
                if st.form_submit_button("Dodaj"):
                    s_shp.append_row([get_now(), it]); st.rerun()
            df_shp["KUPIŁEM"] = False
            e_shp = st.data_editor(df_shp, use_container_width=True, key="ed_shp")
            if st.button("Wyczyść koszyk"):
                rem = e_shp[e_shp["KUPIŁEM"] == False].drop(columns=["KUPIŁEM"])
                s_shp.clear(); s_shp.append_row(["Data i Godzina", "Produkt"])
                if not rem.empty: s_shp.append_rows(rem.values.tolist()); st.rerun()
        with l2:
            st.subheader("✅ Zadania")
            with st.form("add_tsk"):
                ts = st.text_input("Zadanie")
                dt = st.date_input("Termin")
                if st.form_submit_button("Zapisz"):
                    s_tsk.append_row([get_now(), ts, str(dt), "Normalny"]); st.rerun()
            df_tsk["OK"] = False
            e_tsk = st.data_editor(df_tsk, use_container_width=True, key="ed_tsk")
            if st.button("Usuń zrobione"):
                rem_t = e_tsk[e_tsk["OK"] == False].drop(columns=["OK"])
                s_tsk.clear(); s_tsk.append_row(["Data i Godzina", "Zadanie", "Termin", "Priorytet"])
                if not rem_t.empty: s_tsk.append_rows(rem_t.values.tolist()); st.rerun()
