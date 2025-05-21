import streamlit as st
import pandas as pd

def carregar_categorias(caminho='app/data/configuracoes/categorias.txt'):
    with open(caminho, 'r') as file:
        categorias = [linha.strip() for linha in file if linha.strip() != '']
    return categorias

def salvar_categoria(nova_categoria, caminho='app/data/configuracoes/categorias.txt'):
    with open(caminho, 'a') as file:
        file.write(f'\n{nova_categoria}')

def salvar_dataframe(df, caminho):
    df.to_csv(caminho, index=False)

def main():
    st.title('Configurações')

    categorias = carregar_categorias()

    # Sidebar: entrada de nova categoria
    with st.sidebar:
        categoria_nova = st.text_input('Categoria', key='categoria')
        if st.button('Salvar'):
            if categoria_nova in categorias:
                st.warning('Categoria já cadastrada')
            elif categoria_nova.strip() == '':
                st.warning('Digite uma categoria válida')
            else:
                salvar_categoria(categoria_nova)
                st.success('Categoria cadastrada com sucesso!')

    # Carregar dataframes da sessão e remover duplicados
    df_pix = st.session_state.get('pix_enviados', pd.DataFrame())
    df_pix = df_pix.drop_duplicates(subset='Pagador/Recebedor')

    df_boletos = st.session_state.get('boletos_pagos', pd.DataFrame())
    df_boletos = df_boletos.drop_duplicates(subset='Complemento')

    # Layout: duas colunas
    c1, c2 = st.columns(2)

    # Editor Categorias Pix
    c1.write('### Categorias Pix')
    df_pix_edit = c1.data_editor(
        df_pix,
        column_order=['Pagador/Recebedor', 'Categoria'],
        column_config={
            "Categoria": st.column_config.SelectboxColumn(
                "Categoria",
                options=categorias,
                required=True,
            )
        },
        hide_index=True,
    )
    if c1.button('Salvar', key='pix'):
        salvar_dataframe(df_pix_edit, 'app/data/configuracoes/categorias_pix.csv')
        c1.success('Salvo com sucesso')

    # Editor Categorias Boletos
    c2.write('### Categorias Boletos')
    df_boletos_edit = c2.data_editor(
        df_boletos,
        column_order=['Complemento', 'Categoria'],
        column_config={
            "Categoria": st.column_config.SelectboxColumn(
                "Categoria",
                options=categorias,
                required=True,
            )
        },
        hide_index=True,
    )
    if c2.button('Salvar', key='boletos'):
        salvar_dataframe(df_boletos_edit, 'app/data/configuracoes/categorias_boletos.csv')
        c2.success('Salvo com sucesso')


main()
