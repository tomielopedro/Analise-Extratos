import pdfplumber
import pandas as pd
import os

def get_csv(pdf_path):
    dados = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            table = page.extract_table()
            if not table:
                continue

            for line in table:
                if line == ['Operação', 'Situação', 'Pagador/Recebedor', 'CPF/CNPJ', 'Data', 'Valor']:
                    continue  # pula o cabeçalho repetido

                if len(line) == 6:
                    dados.append({
                        'Operação': line[0],
                        'Situação': line[1],
                        'Pagador/Recebedor': line[2],
                        'CPF/CNPJ': line[3],
                        'Data': line[4],
                        'Valor': line[5]
                    })

    # Criação final do DataFrame
    df = pd.DataFrame(dados)
    output_csv = pdf_path.replace('.pdf', '.csv')
    df.to_csv(f'csv/{output_csv}', index=False)
    print(f"✔ CSV salvo: {output_csv}")

# === Loop pelos arquivos PDF em um diretório ===
diretorio = "./"  # ou substitua por outro caminho

for arquivo in os.listdir(diretorio):
    if arquivo.endswith(".pdf"):
        caminho_pdf = os.path.join(diretorio, arquivo)
        get_csv(caminho_pdf)
