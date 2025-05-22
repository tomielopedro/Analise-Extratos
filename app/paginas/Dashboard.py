import streamlit as st
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
    'Agosto 2024': ["app/data/extratos/agosto24.pdf", "app/data/boletos/agosto24.pdf", "app/data/pix/agosto24.csv"],
    'Setembro 2024': ["app/data/extratos/setembro24.pdf", "app/data/boletos/setembro24.pdf", "app/data/pix/setembro24.csv"],
    'Outubro 2024': ["app/data/extratos/outubro24.pdf", "app/data/boletos/outubro24.pdf", "app/data/pix/outubro24.csv"],
    'Novembro 2024': ["app/data/extratos/novembro24.pdf", "app/data/boletos/novembro24.pdf", "app/data/pix/novembro24.csv"],
    'Dezembro 2024': ["app/data/extratos/dezembro24.pdf", "app/data/boletos/dezembro24.pdf", "app/data/pix/dezembro24.csv"],
    'Janeiro 2025': ["app/data/extratos/janeiro25.pdf", "app/data/boletos/janeiro25.pdf", "app/data/pix/janeiro25.csv"],
    'Fevereiro 2025': ["app/data/extratos/fevereiro25.pdf", "app/data/boletos/fevereiro25.pdf", "app/data/pix/fevereiro25.csv"],
    'Marco 2025': ["app/data/extratos/marco25.pdf", "app/data/boletos/marco25.pdf", "app/data/pix/marco25.csv"],
    'Abril 2025': ["app/data/extratos/abril25.pdf", "app/data/boletos/abril25.pdf", "app/data/pix/abril25.csv"]
}
with open('app/data/configuracoes/categorias.txt', 'r') as file:
    categorias = file.readlines()
    categorias = [categoria.strip() for categoria in categorias if categoria.strip() != '']
# === Sidebar: seleção de mês ===
with st.sidebar:
    meses_opcoes = ["Todos"] + list(meses.keys())
    mes = st.selectbox('Selecione um mês', meses_opcoes)

    categorias = ["Todas"]+categorias
    categorias_selecionada = st.selectbox('Selecione uma categoria', categorias)





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

def remove_prefix(text):
    if text.startswith('de'):
        return text.replace('de', '').strip().title()
    if text.startswith('para'):
        return text.replace('para', '').strip().title()
    return text


# === Agrupamento e totais de extrato ===

def forma_pagamento(descricao):
    if descricao.upper().startswith('PIX'):
        return 'Pix'

    if descricao.upper().startswith('PG'):
        return 'Boleto'

    return descricao.title()


categorias_pix = pd.read_csv('app/data/configuracoes/categorias_pix.csv')
categorias_pix = categorias_pix[['Pagador/Recebedor', 'Categoria']]
df_pix['Pagador/Recebedor'] = df_pix['Pagador/Recebedor'].apply(remove_prefix)
df_pix = df_pix.merge(categorias_pix, on='Pagador/Recebedor', how='left')

categorias_boletos = pd.read_csv('app/data/configuracoes/categorias_boletos.csv')
categorias_boletos = categorias_boletos[['Complemento', 'Categoria']]
df_boletos = df_boletos.merge(categorias_boletos, on='Complemento', how='left')

if categorias_selecionada != 'Todas':
    df_pix = df_pix[df_pix['Categoria'] == categorias_selecionada]
    df_boletos = df_boletos[df_boletos['Categoria'] == categorias_selecionada]

df_pix["Valor"] = df_pix["Valor"].apply(moeda_para_float)
df_pix["Operação"] = df_pix["Operação"].apply(lambda x: x.replace('Pix', '').strip())
df_pix = df_pix.drop(columns='CPF/CNPJ')


pix_env = df_pix[df_pix['Operação'] == 'Enviado']
pix_rec = df_pix[df_pix['Operação'] == 'Recebido']
df['Descricao'] = df['Descricao'].apply(forma_pagamento)

entradas = df[df['Valor'] > 0]
entradas = entradas.groupby('Descricao')['Valor'].sum().reset_index()

saidas = df[df['Valor'] < 0]
saidas = saidas.groupby('Descricao')['Valor'].sum().reset_index()

total_entradas = entradas['Valor'].sum()
total_saidas = saidas['Valor'].sum()
tab1, tab2, tab3, tab4 = st.tabs(['Extrato', 'Boletos', 'Pix', 'Dívidas'])



pagos = df_boletos[df_boletos['Situação'] == 'EFETUADA']



# === Cards com totais ===

if 'pix_enviados' not in st.session_state:
    st.session_state.pix_enviados = pix_env

if 'boletos_pagos' not in st.session_state:
    st.session_state.boletos_pagos = pagos
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

        st.markdown(f"""
        <div style=\"background-color:#f2dede;padding:20px;border-radius:10px;text-align:center;\">  
            <h3 style=\"color:#a94442;\">💰 Total de Boletos Pagos</h3>  
            <h2 style=\"margin:0;color:#a94442;\">R$ {pagos['Valor'].sum():,.2f}</h2>  
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.data_editor(pagos.groupby('Complemento')['Valor'].sum().reset_index(), height=200, hide_index=True, column_config=config)

    # === Outras tabelas ===
    st.subheader("📄 Boletos / Recibos Banrisul")
    st.dataframe(df_boletos, use_container_width=True)
with tab3:

    col1, col2, col3 = st.columns([1.2, 1.2, 2])
    with col1:

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





with tab4:
    caminho = 'app/data/configuracoes/dividas.csv'
    df_dividas = pd.read_csv(caminho)
    st.write(f'# Total de Dividas: R$ :red[{df_dividas['Valor'].sum():,.2f}]')
    df_dividas = st.data_editor(df_dividas, use_container_width=True,num_rows='dynamic', key='df_dividas', column_config=config)
    if st.button('Salvar'):
        df_dividas.to_csv(caminho, index=False)
        st.success('Salvo com sucesso!')
        st.rerun()


