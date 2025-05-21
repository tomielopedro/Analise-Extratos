import streamlit as st

# --- Sessão de estado para evitar recarregamento ---
if 'pix_enviados' not in st.session_state:
    st.session_state.pix_enviados = None

if 'boletos_pagos' not in st.session_state:
    st.session_state.boletos_pagos = None

pages = {
    "Pages": [
        st.Page("paginas/Dashboard.py", title="Dashboard"),
    ]
}

pg = st.navigation(pages)
pg.run()