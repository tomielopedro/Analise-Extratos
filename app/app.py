import streamlit as st
import pandas as pd
from utils.extrato_parse import (
    parse_extrato_bancario,
    parse_recibos_banrisul,
    parse_pix_extrato_fitz,
    debug_extrair_linhas_pdf,
    parse_pix_extrato_pdfplumber,
    moeda_para_float
)

st.set_page_config(layout="wide")

# === Dicionário de meses e caminhos ===
meses = {
    'Agosto 2024': ["data/extratos/agosto24.pdf", "data/boletos/agosto24.pdf", "data/pix/agosto24.csv"],
    'Setembro 2024': ["data/extratos/setembro24.pdf", "data/boletos/setembro24.pdf", "data/pix/setembro24.csv"],
    'Outubro 2024': ["data/extratos/outubro24.pdf", "data/boletos/outubro24.pdf", "data/pix/outubro24.csv"],
    'Novembro 2024': ["data/extratos/novembro24.pdf", "data/boletos/novembro24.pdf", "data/pix/novembro24.csv"],
    'Dezembro 2024': ["data/extratos/dezembro24.pdf", "data/boletos/dezembro24.pdf", "data/pix/dezembro24.csv"],
    'Janeiro 2025': ["data/extratos/janeiro25.pdf", "data/boletos/janeiro25.pdf", "data/pix/janeiro25.csv"],
    'Fevereiro 2025': ["data/extratos/fevereiro25.pdf", "data/boletos/fevereiro25.pdf", "data/pix/fevereiro25.csv"],
    'Marco 2025': ["data/extratos/marco25.pdf", "data/boletos/marco25.pdf", "data/pix/marco25.csv"],
    'Abril 2025': ["data/extratos/abril25.pdf", "data/boletos/abril25.pdf", "data/pix/abril25.csv"]
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
            dfs_boletos.append(parse_recibos_banrisul(caminho[1]))
            dfs_pix.append(pd.read_csv(caminho[2]))  # ✅ agora sim
        except Exception as e:
            st.warning(f"Erro ao processar {caminho}: {e}")

    df = pd.concat(dfs, ignore_index=True)
    df_boletos = pd.concat(dfs_boletos, ignore_index=True)
    df_pix = pd.concat(dfs_pix, ignore_index=True)  # ✅ agora funciona
else:
    caminho_pdf = meses[mes]
    df = parse_extrato_bancario(caminho_pdf[0])
    df_boletos = parse_recibos_banrisul(caminho_pdf[1])
    df_pix = pd.read_csv(caminho_pdf[2])


df_pix["Valor"] = df_pix["Valor"].apply(moeda_para_float)
df_pix["Operação"] = df_pix["Operação"].apply(lambda x: x.replace('Pix', '').strip())

# === Agrupamento e totais de extrato ===
df_agrupado = df.groupby('Descricao')['Valor'].sum().reset_index()
entradas = df_agrupado[df_agrupado['Valor'] > 0]
saidas = df_agrupado[df_agrupado['Valor'] < 0]

total_entradas = entradas['Valor'].sum()
total_saidas = saidas['Valor'].sum()
tab1, tab2, tab3 = st.tabs(['Extrato', 'Boletos', 'Pix'])
# === Cards com totais ===


# === Exibição das tabelas ===
config = {
    "Valor": st.column_config.NumberColumn(
        "Valor",
        format="R$ %.2f"
    )
}
with tab1:
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

    col1, col2, col3 = st.columns([2, 1, 1])
    col1.subheader("Extrato")
    col1.data_editor(df, hide_index=True, use_container_width=True, key='df', column_config=config)
    col2.subheader("Entradas")
    col2.data_editor(entradas, hide_index=True, use_container_width=True, key='entradas', column_config=config)
    col3.subheader("Saídas")
    col3.data_editor(saidas, hide_index=True, use_container_width=True, key='saidas', column_config=config)
with tab2:
    col1, col2 = st.columns(2)
    with col1:
        pagos = df_boletos[df_boletos['Situação'] == 'EFETUADA']
        st.markdown(f"""
        <div style=\"background-color:#f2dede;padding:20px;border-radius:10px;text-align:center;\">  
            <h3 style=\"color:#a94442;\">💰 Total de Boletos Pagos</h3>  
            <h2 style=\"margin:0;color:#a94442;\">R$ {pagos['Valor'].sum():,.2f}</h2>  
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.data_editor(df_boletos.groupby('Complemento')['Valor'].sum().reset_index(), height=200, hide_index=True, column_config=config)

    # === Outras tabelas ===
    st.subheader("📄 Boletos / Recibos Banrisul")
    st.dataframe(df_boletos, use_container_width=True)
with tab3:

    col1, col2, col3 = st.columns([1.1, 1.1, 2])
    with col1:
        pix_env = df_pix[df_pix['Operação'] == 'Enviado']
        pix_rec = df_pix[df_pix['Operação'] == 'Recebido']
        st.markdown(f"""
            <div style=\"background-color:#dff0d8;padding:20px;border-radius:10px;text-align:center;\">  
                <h3 style=\"color:#3c763d;\">💰Recebidos</h3>  
                <h2 style=\"margin:0;color:#3c763d;\">R$ {pix_rec['Valor'].sum():,.2f}</h2>  
            </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown(f"""
            <div style=\"background-color:#f2dede;padding:20px;border-radius:10px;text-align:center;\">  
                <h3 style=\"color:#a94442;\">💸 Enviados</h3>  
                <h2 style=\"margin:0;color:#a94442;\">R$ {pix_env['Valor'].sum():,.2f}</h2>  
            </div>
            """, unsafe_allow_html=True)

        with col3:
            st.subheader("🔁 PIX Enviados")
            st.data_editor(pix_env.groupby('Pagador/Recebedor')['Valor'].sum().reset_index(), height=200, hide_index=True, column_config=config)

    st.subheader("🔁 PIX Extrato")
    st.data_editor(df_pix,height=300, hide_index=True,
                       column_config=config)



