import streamlit as st
import pandas as pd
import gspread
from google.oauth2 import service_account
from datetime import datetime, date

# Połączenie z Google Sheets
def connect_to_sheet():
    creds_dict = st.secrets["gcp_service_account"]
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)
    # Zmień "Budzet_Data" na dokładną nazwę swojego arkusza!
    return client.open("Budzet_Data")

st.title("💰 Budżet Domowy 99 Pro")

try:
    doc = connect_to_sheet()
    st.success("✅ Połączono z Google Sheets!")
    
    # Przykład: Odczyt z zakładki "Przychody"
    sheet_incomes = doc.worksheet("Przychody")
    data = pd.DataFrame(sheet_incomes.get_all_records())
    
    if not data.empty:
        st.write("Twoje ostatnie dochody:")
        st.dataframe(data)
    else:
        st.info("Arkusz jest pusty. Dodaj pierwszy dochód w zakładce poniżej.")

except Exception as e:
    st.error(f"Błąd połączenia: {e}")
    st.info("Upewnij się, że arkusz nazywa się 'Budzet_Data' i ma zakładkę 'Przychody' z nagłówkami.")
