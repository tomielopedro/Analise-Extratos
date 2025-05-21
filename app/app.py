import streamlit as st
import pandas as pd
from utils.extrato_parse import (
    parse_extrato_bancario,
    parse_recibos_banrisul,
    parse_pix_extrato_fitz,
    debug_extrair_linhas_pdf,
)

st.set_page_config(layout="wide")

# === Dicionário de meses e caminhos ===
meses = {
    'Agosto 2024': ["data/extratos/agosto24.pdf", "data/boletos/agosto24.pdf", "data/pix/agosto24.pdf"],
    'Setembro 2024': ["data/extratos/setembro24.pdf", "data/boletos/setembro24.pdf", "data/pix/setembro24.pdf"],
    'Outubro 2024': ["data/extratos/outubro24.pdf", "data/boletos/outubro24.pdf", "data/pix/outubro24.pdf"],
    'Novembro 2024': ["data/extratos/novembro24.pdf", "data/boletos/novembro24.pdf", "data/pix/novembro24.pdf"],
    'Dezembro 2024': ["data/extratos/dezembro24.pdf", "data/boletos/dezembro24.pdf", "data/pix/dezembro24.pdf"],
    'Janeiro 2025': ["data/extratos/janeiro25.pdf", "data/boletos/janeiro25.pdf", "data/pix/janeiro25.pdf"],
    'Fevereiro 2025': ["data/extratos/fevereiro25.pdf", "data/boletos/fevereiro25.pdf", "data/pix/fevereiro25.pdf"],
}

# === Sidebar: seleção de mês ===
with st.sidebar:
    meses_opcoes = ["Todos"] + list(meses.keys())
    mes = st.selectbox('Selecione um mês', meses_opcoes)

st.title(f"📄 Visualização - {mes}")

# === Carrega dados conforme mês ===
if mes == "Todos":
    dfs, dfs_pix, dfs_boletos = [], [], []
    for caminho in meses.values():
        try:
            dfs.append(parse_extrato_bancario(caminho[0]))
            dfs_pix.append(parse_pix_extrato_fitz(caminho[2]))
            dfs_boletos.append(parse_recibos_banrisul(caminho[1]))
        except Exception as e:
            st.warning(f"Erro ao processar {caminho}: {e}")

    df = pd.concat(dfs, ignore_index=True)
    df_pix = pd.concat(dfs_pix, ignore_index=True)
    df_boletos = pd.concat(dfs_boletos, ignore_index=True)
else:
    caminho_pdf = meses[mes]
    df = parse_extrato_bancario(caminho_pdf[0])
    df_pix = parse_pix_extrato_fitz(caminho_pdf[2])
    df_boletos = parse_recibos_banrisul(caminho_pdf[1])
    debug_extrair_linhas_pdf(caminho_pdf[2], True)

# === Agrupamento e totais de extrato ===
df_agrupado = df.groupby('Descricao')['Valor'].sum().reset_index()
entradas = df_agrupado[df_agrupado['Valor'] > 0]
saidas = df_agrupado[df_agrupado['Valor'] < 0]

total_entradas = entradas['Valor'].sum()
total_saidas = saidas['Valor'].sum()

# === Cards com totais ===
col1, col2 = st.columns(2)
with col1:
    st.markdown(f"""
    <div style=\"background-color:#dff0d8;padding:20px;border-radius:10px;text-align:center;\">  
        <h3 style=\"color:#3c763d;\">💰 Total de Entradas</h3>  
        <h2 style=\"margin:0;color:#3c763d;\">R$ {total_entradas:,.2f}</h2>  
    </div>
    """, unsafe_allow_html=True)
with col2:
    st.markdown(f"""
    <div style=\"background-color:#f2dede;padding:20px;border-radius:10px;text-align:center;\">  
        <h3 style=\"color:#a94442;\">💸 Total de Saídas</h3>  
        <h2 style=\"margin:0;color:#a94442;\">R$ {abs(total_saidas):,.2f}</h2>  
    </div>
    """, unsafe_allow_html=True)

# === Exibição das tabelas ===
col1, col2, col3 = st.columns([2, 1, 1])
col1.data_editor(df, hide_index=True, use_container_width=True)
col2.subheader("Entradas")
col2.data_editor(entradas, hide_index=True, use_container_width=True)
col3.subheader("Saídas")
col3.data_editor(saidas, hide_index=True, use_container_width=True)

# === Outras tabelas ===
st.subheader("📄 Boletos / Recibos Banrisul")
st.dataframe(df_boletos, use_container_width=True)

st.subheader("🔁 PIX Recebidos")
st.dataframe(df_pix, hide_index=True)
