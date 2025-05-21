# utils.py
import pdfplumber
import re
import pandas as pd


def parse_extrato_bancario(arquivo_pdf: str) -> pd.DataFrame:
    """
    Faz o parse de extratos bancários mensais (com colunas: Dia, Descrição, Documento, Valor).
    """
    texto_completo = ""
    with pdfplumber.open(arquivo_pdf) as pdf:
        for page in pdf.pages:
            texto_completo += page.extract_text() + "\n"

    padrao = re.compile(r"(?:(\d{2})\s+)?([A-Z ./]+?)\s{2,}(\d{6})\s+([\d.,\-]+)")
    dia_atual = ""
    dados = []

    for dia, descricao, documento, valor in padrao.findall(texto_completo):
        if dia.strip():
            dia_atual = dia
        dados.append([dia_atual, descricao.strip(), documento, valor.strip()])

    df = pd.DataFrame(dados, columns=["Dia", "Descricao", "Documento", "Valor"])
    df["Valor"] = df["Valor"].apply(_valor_to_float_corrigido)

    # Remove categorias automáticas
    df = df[~df['Descricao'].isin(["APLIC.AUTOM.", "RESGATE AUTOM"])]

    return df


def parse_recibos_banrisul(arquivo_pdf: str) -> pd.DataFrame:
    """
    Faz o parse de recibos Banrisul, garantindo captura da última transação mesmo com rodapé.
    """
    linhas = []
    with pdfplumber.open(arquivo_pdf) as pdf:
        for page in pdf.pages:
            linhas.extend(page.extract_text().splitlines())

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

    return df[:len(df) - 1]


def parse_pix_extrato_fitz(pdf_path: str) -> pd.DataFrame:
    """
    Extrai do PDF de extrato PIX (Banrisul) as colunas:
      Operação | Situação | Pagador/Recebedor | CPF/CNPJ | Data | Valor
    Tratando quebras de linha e hífens no meio dos campos.
    """
    texto = ""
    with pdfplumber.open(pdf_path) as pdf:
        for página in pdf.pages:
            texto += página.extract_text() + "\n"

    texto = re.sub(r'-\s*\n', '', texto)
    texto = re.sub(r'\n', ' ', texto)
    texto = re.sub(r'\s{2,}', ' ', texto).strip()

    pattern = re.compile(
        r'Pix\s+(\w+)\s+(\w+)\s+de\s+(.+?)\s+'
        r'(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})\s+'
        r'(\d{2}/\d{2}/\d{4})\s+'
        r'R\$ ?([\d\.\,]+)',
        flags=re.IGNORECASE
    )

    registros = []
    for m in pattern.finditer(texto):
        situacao = f"{m.group(1).capitalize()} {m.group(2).capitalize()}"
        nome = m.group(3).strip()
        cpfcnpj = m.group(4)
        data = m.group(5)
        valor = float(m.group(6).replace(".", "").replace(",", "."))
        registros.append({
            "Operação": "Pix",
            "Situação": situacao,
            "Pagador/Recebedor": nome,
            "CPF/CNPJ": cpfcnpj,
            "Data": data,
            "Valor": valor
        })

    df = pd.DataFrame(registros,
                      columns=["Operação", "Situação", "Pagador/Recebedor", "CPF/CNPJ", "Data", "Valor"])
    return df


def debug_extrair_linhas_pdf(arquivo_pdf: str, salvar_em_arquivo: bool = False):
    """
    Função auxiliar para visualizar as linhas extraídas de um PDF Pix do Banrisul.
    Isso ajuda a entender como o conteúdo está sendo estruturado no texto.
    """
    linhas = []
    with pdfplumber.open(arquivo_pdf) as pdf:
        for i, page in enumerate(pdf.pages):
            pagina_linhas = page.extract_text().splitlines()
            linhas.extend(pagina_linhas)
            print(f"\n--- Página {i + 1} ---")
            for linha in pagina_linhas:
                print(linha)

    if salvar_em_arquivo:
        with open("data/debug_linhas_pix.txt", "w", encoding="utf-8") as f:
            for linha in linhas:
                f.write(linha + "\n")


def _valor_to_float_corrigido(v):
    v = v.replace(".", "").replace(",", ".")
    if v.endswith("-"):
        v = "-" + v[:-1]
    return float(v)
