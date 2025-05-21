# utils.py
import fitz  # PyMuPDF
import re
import pandas as pd
from datetime import datetime, timedelta

def parse_extrato_bancario(arquivo_pdf: str) -> pd.DataFrame:
    """
    Faz o parse de extratos bancários mensais e retorna um DataFrame com a coluna 'Data' no formato datetime.date.
    Primeiro tenta extrair o período a partir de 'PERIODO: MÊS/ANO'. Se não encontrar, usa 'SALDO ANT EM DD/MM/AAAA'.
    """
    doc = fitz.open(arquivo_pdf)
    texto_completo = "".join([page.get_text() for page in doc])

    # === 1. Tenta extrair 'PERIODO: MÊS/ANO'
    match_periodo = re.search(r"PERIODO:\s+([A-ZÇ]+)[/\\](\d{4})", texto_completo, re.IGNORECASE)

    meses = {
        "JANEIRO": 1, "FEVEREIRO": 2, "MARCO": 3, "ABRIL": 4,
        "MAIO": 5, "JUNHO": 6, "JULHO": 7, "AGOSTO": 8,
        "SETEMBRO": 9, "OUTUBRO": 10, "NOVEMBRO": 11, "DEZEMBRO": 12
    }

    mes = None
    ano = None

    if match_periodo:
        nome_mes, ano_str = match_periodo.groups()
        nome_mes_upper = nome_mes.upper()
        if nome_mes_upper in meses:
            mes = meses[nome_mes_upper]
            ano = int(ano_str)
    else:
        # === 2. Tenta fallback via 'SALDO ANT EM DD/MM/AAAA'
        match_data = re.search(r"SALDO ANT EM\s+(\d{2}/\d{2}/\d{4})", texto_completo)
        if match_data:
            data_ant = datetime.strptime(match_data.group(1), "%d/%m/%Y")
            data_extrato = (data_ant + timedelta(days=1)).replace(day=1)
            mes = data_extrato.month
            ano = data_extrato.year
        else:
            raise ValueError("Não foi possível determinar o mês/ano do extrato.")

    # === 3. Regex para extrair os dados da tabela
    padrao = re.compile(
        r"(?:(\d{2})\s+)?([A-Z].*?)\s{2,}(\d{6})\s+([\d.,\-]+)", re.MULTILINE
    )

    dia_atual = ""
    dados = []

    for dia, descricao, documento, valor in padrao.findall(texto_completo):
        if dia.strip():
            dia_atual = dia
        dados.append([int(dia_atual), descricao.strip(), documento, valor.strip()])

    df = pd.DataFrame(dados, columns=["Dia", "Descricao", "Documento", "Valor"])
    df["Valor"] = df["Valor"].apply(_valor_to_float_corrigido)

    # === 4. Cria a coluna 'Data'
    def construir_data(row):
        try:
            return datetime.strptime(f"{row['Dia']:02d}/{mes:02d}/{ano}", "%d/%m/%Y").date()
        except ValueError:
            return None

    df["Data"] = df.apply(construir_data, axis=1)
    df = df.dropna(subset=["Data"])

    # Remove categorias automáticas
    df = df[~df["Descricao"].isin(["APLIC.AUTOM.", "RESGATE AUTOM"])]

    # Reorganiza colunas
    df = df[["Data", "Descricao", "Documento", "Valor"]]

    return df






def parse_recibos_banrisul(arquivo_pdf: str) -> pd.DataFrame:
    """
    Faz o parse de recibos Banrisul, garantindo captura da última transação mesmo com rodapé.
    """
    doc = fitz.open(arquivo_pdf)
    linhas = []
    for page in doc:
        linhas.extend(page.get_text().splitlines())

    dados = []
    buffer = []

    for linha in linhas:
        linha = linha.strip()

        if re.match(r"\d{2}/\d{2}/\d{4}", linha):
            if len(buffer) >= 7:
                dados.append(buffer[:7])
            buffer = [linha]
        elif linha.startswith("Situação") and len(buffer) >= 7:
            dados.append(buffer[:7])
            buffer = []
        elif linha:
            buffer.append(linha)

    if len(buffer) >= 7:
        dados.append(buffer[:7])

    df = pd.DataFrame(dados, columns=["Data", "NSU", "Situação", "Valor", "Operação", "Conta", "Complemento"])

    df["Valor"] = (
        df["Valor"]
        .str.replace("R$", "", regex=False)
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
        .str.strip()
    )
    df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce")
    df = df.dropna(subset=["Valor"])
    df["Complemento"] = df["Complemento"].str.extract(r"^(.*?)\s*-\s*")
    return df[:len(df) - 1]

def parse_pix_extrato_fitz(arquivo_pdf: str) -> pd.DataFrame:
    """
    Faz o parse de extrato Pix do Banrisul extraído via PyMuPDF.
    Retorna um DataFrame com colunas: Tipo, Direção, Pessoa, CPF/CNPJ, Data, Valor.
    """
    doc = fitz.open(arquivo_pdf)
    texto = "\n".join([page.get_text() for page in doc])

    # Normaliza espaços e quebras de linha
    texto = re.sub(r'\s+', ' ', texto)

    # Regex robusto para captar as informações
    padrao = re.compile(
        r"Pix\s+(Recebido|Enviado)\s+Efetivado\s+(?:de|para)\s+(.+?)\s+(\d{2,3}\.\d{3}\.\d{3}/\d{4}-\d{2}|\d{3}\.\d{3}\.\d{3}-\d{2})\s+(\d{2}/\d{2}/\d{4})\s+R\$\s*([\d.,]+)"
    )

    dados = []
    for tipo, pessoa, cpf_cnpj, data, valor in padrao.findall(texto):
        valor = float(valor.replace('.', '').replace(',', '.'))
        direcao = "de" if tipo == "Recebido" else "para"
        dados.append([tipo, direcao, pessoa.strip(), cpf_cnpj.strip(), data, valor])

    df = pd.DataFrame(dados, columns=["Tipo", "Direcao", "Pessoa", "CPF/CNPJ", "Data", "Valor"])
    return df

import pdfplumber

def debug_extrair_linhas_pdf(arquivo_pdf: str, salvar_em_arquivo: bool = False):
    """
    Função auxiliar para visualizar e/ou salvar as linhas extraídas de um PDF Pix do Banrisul.

    Args:
        arquivo_pdf (str): Caminho para o arquivo PDF a ser analisado.
        salvar_em_arquivo (bool): Se True, salva as linhas em um arquivo de texto.
    """
    linhas = []

    with pdfplumber.open(arquivo_pdf) as doc:
        for i, page in enumerate(doc.pages):
            pagina_linhas = page.extract_text().splitlines()
            linhas.extend(pagina_linhas)

            print(f"\n--- Página {i + 1} ---")
            for linha in pagina_linhas:
                print(linha)

    if salvar_em_arquivo:
        caminho_saida = "data/debug_linhas_pix.txt"
        with open(caminho_saida, "w", encoding="utf-8") as f:
            for linha in linhas:
                f.write(linha + "\n")
        print(f"\nLinhas salvas em: {caminho_saida}")


def _valor_to_float_corrigido(v):
    v = v.replace(".", "").replace(",", ".")
    if v.endswith("-"):
        v = "-" + v[:-1]
    return float(v)

def moeda_para_float(valor):
    return float(valor.replace("R$", "").replace(".", "").replace(",", ".").strip())

def parse_pix_extrato_pdfplumber(caminho_pdf: str) -> pd.DataFrame:
    """
    Faz o parse de um extrato Pix do Banrisul em formato PDF usando pdfplumber.

    Args:
        caminho_pdf (str): Caminho para o arquivo PDF.

    Returns:
        pd.DataFrame: DataFrame com colunas: ['Tipo', 'Direcao', 'Nome', 'Documento', 'Data', 'Valor']
    """
    linhas = []

    with pdfplumber.open(caminho_pdf) as pdf:
        texto = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])

    # Junta linhas quebradas no meio
    texto = texto.replace("\n", " ")

    # Padrao para capturar as operações Pix
    padrao = re.compile(
        r"(Pix)\s+(?:de|para)?\s*(.*?)\s+(\d{2,3}[.\d]{3,}/\d{4}-\d{2}|\d{3}[.\d]{3}-\d{2})?\s*R?\$?\s*Efetivado\s+(\d{2}/\d{2}/\d{4})\s*(?:Recebido|Enviado)?\s*(.*?)?\s*([R\$ ]*[\d.,]+)",
        flags=re.IGNORECASE
    )

    for match in padrao.findall(texto):
        tipo, nome, documento, data, complemento, valor = match
        direcao = "Recebido" if "Recebido" in texto[texto.find(match[0]):texto.find(match[0])+100] else "Enviado"

        nome_completo = (nome + " " + complemento).strip()
        valor = valor.replace("R$", "").replace(" ", "").replace(".", "").replace(",", ".")
        try:
            valor_float = float(valor)
        except ValueError:
            valor_float = None

        linhas.append([tipo, direcao, nome_completo, documento, data, valor_float])

    df = pd.DataFrame(linhas, columns=["Tipo", "Direcao", "Nome", "Documento", "Data", "Valor"])
    return df
if __name__ == "__main__":
    debug_extrair_linhas_pdf('../data/pix/abril25.pdf', True)