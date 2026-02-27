import streamlit as st
import pdfplumber
from PyPDF2 import PdfReader, PdfWriter
import re
import io
import zipfile
import json
import os

# --- FUNÇÕES DE LEITURA E ESCRITA DO JSON ---

def get_json_mapping():
    """
    Lê o mapeamento diretamente do arquivo JSON na raiz.
    """
    mapping_dict = {}
    if os.path.exists('mapeamento_planilha.json'):
        with open('mapeamento_planilha.json', 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                for item in data:
                    mapping_dict[str(item.get('COD_SECAO', ''))] = str(item.get('ONDE LANÇAR', ''))
            except json.JSONDecodeError:
                pass # Caso o arquivo esteja vazio ou inválido
    return mapping_dict

def save_to_json(secao, obra_input, empresa_input):
    """
    Salva a nova seção no arquivo JSON local.
    """
    file_path = 'mapeamento_planilha.json'
    
    # Lê os dados atuais
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = []
    else:
        data = []
        
    # Adiciona a nova seção à lista
    data.append({
        "COD_SECAO": secao,
        "ONDE LANÇAR": obra_input,
        "EMPRESA": empresa_input
    })
    
    # Grava novamente no arquivo
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


# --- FUNÇÕES DE AUXÍLIO ---

def extract_section_data(page_text):
    """
    Detecta o código da seção E o valor monetário na mesma linha.
    Retorna uma tupla: (secao, valor_limpo)
    """
    match = re.search(r'TOTAL SEÇÃO:?\s*(\d{2}\.\d{3}\.\d{2}).*?(\d{1,3}(?:\.\d{3})*,\d{2})', page_text, re.DOTALL)
    
    if match:
        secao = match.group(1)
        valor_bruto = match.group(2) 
        valor_limpo = valor_bruto.replace('.', '').split(',')[0]
        return secao, valor_limpo
    
    if "TOTAL SEÇÃO" in page_text:
        all_codes = re.findall(r'(\d{2}\.\d{3}\.\d{2})', page_text)
        if all_codes:
            return all_codes[-1], ""
            
    return None, None

def get_unique_filename(base_type, obra, sufixo, valor, existing_files):
    """
    Gera o nome do arquivo incluindo o valor no final.
    LIMITAÇÃO: O nome do arquivo (sem extensão) terá no máximo 20 caracteres.
    """
    valor_str = str(valor) if valor else ""
    
    # 1. Monta a string bruta completa
    raw_name = f"{base_type}{obra}{sufixo}{valor_str}"
    
    # 2. Verifica o tamanho e corta se for maior que 20
    if len(raw_name) > 20:
        raw_name = raw_name[:20]
    
    # Adiciona a extensão
    nome_final = f"{raw_name}.pdf"
    
    if nome_final not in existing_files:
        return nome_final
    
    # Caso já exista, adiciona contador (e garante que continua respeitando os 20 chars)
    counter = 1
    while True:
        # Monta com contador (base + contador + obra...)
        raw_with_counter = f"{base_type}{counter}{obra}{sufixo}{valor_str}"
        
        # Aplica o corte novamente na string com contador
        if len(raw_with_counter) > 20:
            raw_with_counter = raw_with_counter[:20]
            
        novo_nome = f"{raw_with_counter}.pdf"
        
        if novo_nome not in existing_files:
            return novo_nome
            
        counter += 1

# --- DIÁLOGO (POP-UP) ---

@st.dialog("Nova Seção Encontrada")
def cadastrar_secao(secao):
    st.warning(f"A seção {secao} não existe no arquivo mapeamento_planilha.json.")
    obra_input = st.text_input("Onde Lançar (Obra)", placeholder="Ex: 425")
    empresa_input = st.number_input("Empresa", value=1)
    
    if st.button("Salvar no JSON"):
        if obra_input:
            save_to_json(secao, obra_input, empresa_input)
            st.success("Dados salvos localmente com sucesso!")
            st.rerun()
        else:
            st.error("Preencha a obra!")

# --- INTERFACE ---

def main():
    st.set_page_config(page_title="Processador por Seção", layout="wide")
    st.title("📑 Divisor de PDF")

    mapping_dict = get_json_mapping()

    st.sidebar.header("Configuração de Data")
    mes_pl = st.sidebar.text_input("Mês", value="01", max_chars=2)
    ano_pl = st.sidebar.text_input("Ano", value="26", max_chars=2)
    sufixo = f"{mes_pl}{ano_pl}"

    uploaded_pdfs = st.file_uploader("Arquivos PDF", type="pdf", accept_multiple_files=True)

    if uploaded_pdfs:
        if st.button("🚀 Processar Tudo"):
            missing = []
            
            for pdf_file in uploaded_pdfs:
                with pdfplumber.open(pdf_file) as pdf_plumb:
                    for page in pdf_plumb.pages:
                        text = page.extract_text() or ""
                        secao, _ = extract_section_data(text)
                        
                        if secao and secao not in mapping_dict and secao not in missing:
                            missing.append(secao)

            if missing:
                cadastrar_secao(missing[0])
                return

            zip_buffer = io.BytesIO()
            processed_count = 0
            filenames_in_zip = set()

            with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                for uploaded_pdf in uploaded_pdfs:
                    reader = PdfReader(uploaded_pdf)
                    
                    with pdfplumber.open(uploaded_pdf) as pdf_plumb:
                        paginas_acumuladas = []
                        
                        for i, page in enumerate(pdf_plumb.pages):
                            paginas_acumuladas.append(i)
                            text = page.extract_text() or ""
                            
                            secao_encontrada, valor_encontrado = extract_section_data(text)
                            
                            if secao_encontrada and secao_encontrada in mapping_dict:
                                obra = mapping_dict[secao_encontrada]
                                
                                # --- ALTERAÇÃO AQUI: Prefixos corrigidos para FOLHASM e FOLHACX ---
                                n_soma = get_unique_filename("FOLHASM", obra, sufixo, valor_encontrado, filenames_in_zip)
                                filenames_in_zip.add(n_soma)
                                
                                n_caixa = get_unique_filename("FOLHACX", obra, sufixo, valor_encontrado, filenames_in_zip)
                                filenames_in_zip.add(n_caixa)
                                
                                writer = PdfWriter()
                                for p_idx in paginas_acumuladas:
                                    writer.add_page(reader.pages[p_idx])
                                
                                for nome in [n_soma, n_caixa]:
                                    pdf_out = io.BytesIO()
                                    writer.write(pdf_out)
                                    zip_file.writestr(nome, pdf_out.getvalue())
                                    processed_count += 1
                                
                                paginas_acumuladas = []
                            
                        if paginas_acumuladas:
                            st.warning(f"As últimas {len(paginas_acumuladas)} páginas do arquivo {uploaded_pdf.name} não continham um 'TOTAL SEÇÃO' e foram ignoradas.")

            if processed_count > 0:
                st.success(f"Finalizado! {processed_count} arquivos gerados agrupando as páginas por seção.")
                st.download_button(
                    label="📥 Baixar ZIP",
                    data=zip_buffer.getvalue(),
                    file_name=f"folhas_agrupadas_{sufixo}.zip",
                    mime="application/zip"
                )

if __name__ == "__main__":
    main()
# import streamlit as st
# import pdfplumber
# from PyPDF2 import PdfReader, PdfWriter
# import re
# import io
# import zipfile
# import firebase_admin
# from firebase_admin import credentials, firestore

# # --- CONFIGURAÇÃO FIREBASE ---

# def init_firebase():
#     if not firebase_admin._apps:
#         cred_dict = {
#             "type": "service_account",
#             "project_id": "mapeamento-planilha",
#             "private_key_id": "32613ce4859364c2f2db40fa792ea48f6d6badbd",
#             "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQCfNUfZ6blu3jLC\nleQNT1hgruieIl1OGIz6WHsYWaDQw+GC0ROnl1kIIFeMl82E+lpDsbU48stf0KPK\njDT0EX+YsjP8LHoF57csFHQ0g46FF2cEqmD3Ol4ZKk0R/J9XhYBz0AikRj7goYuM\nk4+xbBn8iRhVpQGrOA7Fv0wtdgZ4bdvUZzQMnTM9MII8jY90Gyuv6IWgLjB7cDqk\nCqDPtWjPyrijq2bTab7/cEhzWx/r0HL1X6/NDmoTaAyUypLVgGNmai226TNhdPSX\nihLnlxIu61GeH3ZFdznyD8cCQcrvosiCuhpLN2/S3bZ71sMIWGDjnBvCvOty+uGS\nmHqS2RBlAgMBAAECgf9UFvwKaEXNiTLqQNwrT3acRRJXMGXbNNJO9998tAdGuqQP\n2DzE36O+W9SDz2/Osvfu5oVvxdsg40uWvDqwoYRvN7B+ln0SvpUj1e01aCeVrVeF\nPaVsF+kyCfDsOvN+KqXTFX1XER0DLGIZlPHamr01eZIjEZUdioYn+/DldOu02fAI\nvQVGgOm34WiaAKh3YG3g2aQSHXJqpd86JmDlKc8lZG1fsRAVKW/J0WAjUMCIpYiV\naqwkP0sfViioVNPDC/jxrnziYg140HFb73bXcazZIbfVqAcTxEdVasDyXJcpQIrv\nSeKyYIxKSpvibh6uFBuBkLhdCTqAnnfz1+OOO7ECgYEA4A1NG0A5JFKhbyxJtl7L\nmFWas4KCaRt5+mFT4OOWJSag1fwL7E4Ra8yNS5DohJo/YggoMnetp6IqAbFgspgu\nU335HK+rxtgnEs8KMdu/D+hJY38fVpRvfuSGZ6WgS0Zb9VGR2acXTGhMciFuyCPw\nj/L2bFgrhVJCJRf6ruYJt7ECgYEAtejyjMLDLfWnUoW98klJEFmIxEpLB7YkfRlH\nEfqXYhkqsXck4k5yPOwjLHdholrq6T8e6CswSc0pLqXNBRLE829Lp1YfQlhQefbA\nCX4+2HGyVnLCLAmKSpHSDHTiSA6MuzSZTR3C9DDeb1Mh+oBAKSZHVwxujELXGa3V\ncPBlhPUCgYEAy8vNgygb0epHZTRHqFb5ogrbuMTRkoGnphO5lCnvfMNyMLIetkcc\nmY1qSH36wgL7/FOnHKC3mG9s/jU1272JBfDkEy/HdAtRH06r20YiuHl1p8cN3lcO\nQ8Hib4y8DTxmkPItVGkkTB/iyT2X4vyt6IH7m/lnPNHh0JPLNiOQW0ECgYEAis24\nHe4S7kPOq+o/ONvws1gOQvEJdVXnW8lo8HANCR549DccXs5K3u+0Gx7w0eib7ORs\nGe2yh+3TKbP7z4412CapTIMrkP1AUwAUImpBW/jNgqdIQD/7VNEVvMmHTEJF4ibN\nfwlhk+CiKcH+YF1yF7QMpYBn7gCmjwKUpfvZCu0CgYEAml8wGAvkvJBbaFHasW/k\nobqnTotE89SXuwCJFjawcLECbcME00KS67zgYL6HSIPzOrYF7FP2vC/dcx032+yS\niKcFugCg3ttd52CFPji2em2u4alU7SCfc5LXtu2SHVLB0BesY9Wlk4jhNLmWKbzH\nwSVEp+LixYrgBCJd9eS5WMs=\n-----END PRIVATE KEY-----\n",
#             "client_email": "firebase-adminsdk-fbsvc@mapeamento-planilha.iam.gserviceaccount.com",
#             "client_id": "117235355407089535572",
#             "auth_uri": "https://accounts.google.com/o/oauth2/auth",
#             "token_uri": "https://oauth2.googleapis.com/token",
#             "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
#             "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-fbsvc%40mapeamento-planilha.iam.gserviceaccount.com",
#             "universe_domain": "googleapis.com"
#         }
#         cred = credentials.Certificate(cred_dict)
#         firebase_admin.initialize_app(cred)
#     return firestore.client()

# db = init_firebase()

# # --- FUNÇÕES DE AUXÍLIO ---

# def extract_section_data(page_text):
#     """
#     Detecta o código da seção E o valor monetário na mesma linha.
#     Retorna uma tupla: (secao, valor_limpo)
#     """
#     match = re.search(r'TOTAL SEÇÃO:?\s*(\d{2}\.\d{3}\.\d{2}).*?(\d{1,3}(?:\.\d{3})*,\d{2})', page_text, re.DOTALL)
    
#     if match:
#         secao = match.group(1)
#         valor_bruto = match.group(2) 
#         valor_limpo = valor_bruto.replace('.', '').split(',')[0]
#         return secao, valor_limpo
    
#     if "TOTAL SEÇÃO" in page_text:
#         all_codes = re.findall(r'(\d{2}\.\d{3}\.\d{2})', page_text)
#         if all_codes:
#             return all_codes[-1], ""
            
#     return None, None

# def get_firebase_mapping():
#     mapping_dict = {}
#     docs = db.collection('mapeamento_secoes').stream()
#     for doc in docs:
#         data = doc.to_dict()
#         mapping_dict[str(data['COD_SECAO'])] = str(data['ONDE LANÇAR'])
#     return mapping_dict

# def get_unique_filename(base_type, obra, sufixo, valor, existing_files):
#     """
#     Gera o nome do arquivo incluindo o valor no final.
#     LIMITAÇÃO: O nome do arquivo (sem extensão) terá no máximo 20 caracteres.
#     """
#     valor_str = str(valor) if valor else ""
    
#     # 1. Monta a string bruta completa
#     raw_name = f"{base_type}{obra}{sufixo}{valor_str}"
    
#     # 2. Verifica o tamanho e corta se for maior que 20
#     if len(raw_name) > 20:
#         raw_name = raw_name[:20]
    
#     # Adiciona a extensão
#     nome_final = f"{raw_name}.pdf"
    
#     if nome_final not in existing_files:
#         return nome_final
    
#     # Caso já exista, adiciona contador (e garante que continua respeitando os 20 chars)
#     counter = 1
#     while True:
#         # Monta com contador (base + contador + obra...)
#         raw_with_counter = f"{base_type}{counter}{obra}{sufixo}{valor_str}"
        
#         # Aplica o corte novamente na string com contador
#         if len(raw_with_counter) > 20:
#             raw_with_counter = raw_with_counter[:20]
            
#         novo_nome = f"{raw_with_counter}.pdf"
        
#         if novo_nome not in existing_files:
#             return novo_nome
            
#         counter += 1

# # --- DIÁLOGO (POP-UP) ---

# @st.dialog("Nova Seção Encontrada")
# def cadastrar_secao(secao):
#     st.warning(f"A seção {secao} não existe no Firebase.")
#     obra_input = st.text_input("Onde Lançar (Obra)", placeholder="Ex: 425")
#     empresa_input = st.number_input("Empresa", value=1)
    
#     if st.button("Salvar no Firebase"):
#         if obra_input:
#             db.collection('mapeamento_secoes').document(secao).set({
#                 "COD_SECAO": secao,
#                 "ONDE LANÇAR": obra_input,
#                 "EMPRESA": empresa_input
#             })
#             st.success("Dados salvos na nuvem!")
#             st.rerun()
#         else:
#             st.error("Preencha a obra!")

# # --- INTERFACE ---

# def main():
#     st.set_page_config(page_title="Processador por Seção", layout="wide")
#     st.title("📑 Divisor de PDF")

#     mapping_dict = get_firebase_mapping()

#     st.sidebar.header("Configuração de Data")
#     mes_pl = st.sidebar.text_input("Mês", value="02", max_chars=2)
#     ano_pl = st.sidebar.text_input("Ano", value="26", max_chars=2)
#     sufixo = f"{mes_pl}{ano_pl}"

#     uploaded_pdfs = st.file_uploader("Arquivos PDF", type="pdf", accept_multiple_files=True)

#     if uploaded_pdfs:
#         if st.button("🚀 Processar Tudo"):
#             missing = []
            
#             for pdf_file in uploaded_pdfs:
#                 with pdfplumber.open(pdf_file) as pdf_plumb:
#                     for page in pdf_plumb.pages:
#                         text = page.extract_text() or ""
#                         secao, _ = extract_section_data(text)
                        
#                         if secao and secao not in mapping_dict and secao not in missing:
#                             missing.append(secao)

#             if missing:
#                 cadastrar_secao(missing[0])
#                 return

#             zip_buffer = io.BytesIO()
#             processed_count = 0
#             filenames_in_zip = set()

#             with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
#                 for uploaded_pdf in uploaded_pdfs:
#                     reader = PdfReader(uploaded_pdf)
                    
#                     with pdfplumber.open(uploaded_pdf) as pdf_plumb:
#                         paginas_acumuladas = []
                        
#                         for i, page in enumerate(pdf_plumb.pages):
#                             paginas_acumuladas.append(i)
#                             text = page.extract_text() or ""
                            
#                             secao_encontrada, valor_encontrado = extract_section_data(text)
                            
#                             if secao_encontrada and secao_encontrada in mapping_dict:
#                                 obra = mapping_dict[secao_encontrada]
                                
#                                 # --- ALTERAÇÃO AQUI: Prefixos corrigidos para FOLHASM e FOLHACX ---
#                                 n_soma = get_unique_filename("FOLHASM", obra, sufixo, valor_encontrado, filenames_in_zip)
#                                 filenames_in_zip.add(n_soma)
                                
#                                 n_caixa = get_unique_filename("FOLHACX", obra, sufixo, valor_encontrado, filenames_in_zip)
#                                 filenames_in_zip.add(n_caixa)
                                
#                                 writer = PdfWriter()
#                                 for p_idx in paginas_acumuladas:
#                                     writer.add_page(reader.pages[p_idx])
                                
#                                 for nome in [n_soma, n_caixa]:
#                                     pdf_out = io.BytesIO()
#                                     writer.write(pdf_out)
#                                     zip_file.writestr(nome, pdf_out.getvalue())
#                                     processed_count += 1
                                
#                                 paginas_acumuladas = []
                            
#                         if paginas_acumuladas:
#                             st.warning(f"As últimas {len(paginas_acumuladas)} páginas do arquivo {uploaded_pdf.name} não continham um 'TOTAL SEÇÃO' e foram ignoradas.")

#             if processed_count > 0:
#                 st.success(f"Finalizado! {processed_count} arquivos gerados agrupando as páginas por seção.")
#                 st.download_button(
#                     label="📥 Baixar ZIP",
#                     data=zip_buffer.getvalue(),
#                     file_name=f"folhas_agrupadas_{sufixo}.zip",
#                     mime="application/zip"
#                 )

# if __name__ == "__main__":
#     main()