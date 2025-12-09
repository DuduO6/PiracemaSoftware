import pdfplumber
import re

def extrair_dados_crlv(pdf_file):
    dados = {
        "placa": None,
        "renavam": None,
        "modelo": None,
    }

    with pdfplumber.open(pdf_file) as pdf:
        texto = ""
        for page in pdf.pages:
            txt = page.extract_text() or ""
            texto += txt + "\n"

    # remover quebras
    texto_limpo = " ".join(texto.split())

    # -----------------------------------
    # CÓDIGO RENAVAM
    # -----------------------------------
    renavam_regex = re.search(
        r"(CÓDIGO\s*RENAVAM|RENAVAM)[\s:]*([0-9]{8,12})",
        texto_limpo, re.IGNORECASE
    )
    if renavam_regex:
        dados["renavam"] = renavam_regex.group(2)

    # -----------------------------------
    # PLACA (padrão Mercosul)
    # -----------------------------------
    placa_regex = re.search(
        r"PLACA[\s:]*([A-Z]{3}[0-9][A-Z0-9][0-9]{2})",
        texto_limpo, re.IGNORECASE
    )
    if placa_regex:
        dados["placa"] = placa_regex.group(1)

    # -----------------------------------
    # MARCA / MODELO / VERSÃO
    # Muito mais preciso agora
    # -----------------------------------
    modelo_regex = re.search(
        r"MARCA\s*/\s*MODELO\s*/\s*VERSÃO\s*:?\s*([A-Z0-9\-/ ]+?)(?=\s+[0-9]{4}\s|ANO\s+MODELO|ANO\s+FABRICAÇÃO)",
        texto,
        re.IGNORECASE
    )

    if modelo_regex:
        modelo = modelo_regex.group(1).strip()
        # proteger contra frases do tipo "EXTRAÍDO DIGITALMENTE PELO DETRAN"
        if "EXTRA" not in modelo.upper() and "DIGITAL" not in modelo.upper():
            dados["modelo"] = modelo

    return dados
