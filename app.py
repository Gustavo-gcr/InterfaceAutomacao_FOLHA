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
#             "type": st.secrets["firebase"]["type"],
#             "project_id": st.secrets["firebase"]["project_id"],
#             "private_key_id": st.secrets["firebase"]["private_key_id"],
#             "private_key": st.secrets["firebase"]["private_key"],
#             "client_email": st.secrets["firebase"]["client_email"],
#             "client_id": st.secrets["firebase"]["client_id"],
#             "auth_uri": st.secrets["firebase"]["auth_uri"],
#             "token_uri": st.secrets["firebase"]["token_uri"],
#             "auth_provider_x509_cert_url": st.secrets["firebase"]["auth_provider_x509_cert_url"],
#             "client_x509_cert_url": st.secrets["firebase"]["client_x509_cert_url"],
#             "universe_domain": st.secrets["firebase"]["universe_domain"]
#         }
#         cred = credentials.Certificate(cred_dict)
#         firebase_admin.initialize_app(cred)
#     return firestore.client()

# db = init_firebase()

# # --- FUNÇÕES DE AUXÍLIO ---

# def extract_section_near_total(page_text):
#     """Detecta o código da seção apenas quando o rótulo TOTAL SEÇÃO está presente."""
#     match = re.search(r'TOTAL SEÇÃO:?\s*(\d{2}\.\d{3}\.\d{2})', page_text, re.IGNORECASE)
#     if match:
#         return match.group(1)
    
#     # Fallback para casos onde o texto pode estar em linhas quebradas
#     if "TOTAL SEÇÃO" in page_text:
#         all_codes = re.findall(r'(\d{2}\.\d{3}\.\d{2})', page_text)
#         if all_codes:
#             return all_codes[-1]
#     return None

# def get_firebase_mapping():
#     mapping_dict = {}
#     docs = db.collection('mapeamento_secoes').stream()
#     for doc in docs:
#         data = doc.to_dict()
#         mapping_dict[str(data['COD_SECAO'])] = str(data['ONDE LANÇAR'])
#     return mapping_dict

# def get_unique_filename(base_type, obra, sufixo, existing_files):
#     nome_base = f"{base_type}{obra}{sufixo}.pdf"
#     if nome_base not in existing_files:
#         return nome_base
#     counter = 1
#     while True:
#         novo_nome = f"{base_type}{counter}{obra}{sufixo}.pdf"
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
#     st.title("📑 Divisor de PDF por Grupo de Seção")

#     mapping_dict = get_firebase_mapping()

#     st.sidebar.header("Configuração de Data")
#     mes_pl = st.sidebar.text_input("Mês", value="01", max_chars=2)
#     ano_pl = st.sidebar.text_input("Ano", value="26", max_chars=2)
#     sufixo = f"{mes_pl}{ano_pl}"

#     uploaded_pdfs = st.file_uploader("Arquivos PDF", type="pdf", accept_multiple_files=True)

#     if uploaded_pdfs:
#         if st.button("🚀 Processar Tudo"):
#             missing = []
            
#             # Pré-scan para validar seções existentes no arquivo
#             for pdf_file in uploaded_pdfs:
#                 with pdfplumber.open(pdf_file) as pdf_plumb:
#                     for page in pdf_plumb.pages:
#                         text = page.extract_text() or ""
#                         secao = extract_section_near_total(text)
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
#                         # Lista para acumular índices de páginas que pertencem à mesma seção
#                         paginas_acumuladas = []
                        
#                         for i, page in enumerate(pdf_plumb.pages):
#                             paginas_acumuladas.append(i)
#                             text = page.extract_text() or ""
                            
#                             # Tenta localizar o fim da seção nesta página
#                             secao_encontrada = extract_section_near_total(text)
                            
#                             if secao_encontrada and secao_encontrada in mapping_dict:
#                                 obra = mapping_dict[secao_encontrada]
                                
#                                 # Define nomes únicos para os arquivos
#                                 n_soma = get_unique_filename("FOLHASOMA", obra, sufixo, filenames_in_zip)
#                                 filenames_in_zip.add(n_soma)
#                                 n_caixa = get_unique_filename("FOLHACAIXA", obra, sufixo, filenames_in_zip)
#                                 filenames_in_zip.add(n_caixa)
                                
#                                 # Cria o PDF unindo todas as páginas acumuladas até agora
#                                 writer = PdfWriter()
#                                 for p_idx in paginas_acumuladas:
#                                     writer.add_page(reader.pages[p_idx])
                                
#                                 # Salva as duas versões no ZIP
#                                 for nome in [n_soma, n_caixa]:
#                                     pdf_out = io.BytesIO()
#                                     writer.write(pdf_out)
#                                     zip_file.writestr(nome, pdf_out.getvalue())
#                                     processed_count += 1
                                
#                                 # Limpa o acumulador para começar a próxima seção
#                                 paginas_acumuladas = []
                            
#                         # Se sobrar alguma página no final sem "TOTAL SEÇÃO", avisamos
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
import streamlit as st
import pdfplumber
from PyPDF2 import PdfReader, PdfWriter
import re
import io
import zipfile
import firebase_admin
from firebase_admin import credentials, firestore

# --- CONFIGURAÇÃO FIREBASE ---

def init_firebase():
    if not firebase_admin._apps:
        cred_dict = {
            "type": st.secrets["firebase"]["type"],
            "project_id": st.secrets["firebase"]["project_id"],
            "private_key_id": st.secrets["firebase"]["private_key_id"],
            "private_key": st.secrets["firebase"]["private_key"],
            "client_email": st.secrets["firebase"]["client_email"],
            "client_id": st.secrets["firebase"]["client_id"],
            "auth_uri": st.secrets["firebase"]["auth_uri"],
            "token_uri": st.secrets["firebase"]["token_uri"],
            "auth_provider_x509_cert_url": st.secrets["firebase"]["auth_provider_x509_cert_url"],
            "client_x509_cert_url": st.secrets["firebase"]["client_x509_cert_url"],
            "universe_domain": st.secrets["firebase"]["universe_domain"]
        }
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
    return firestore.client()

db = init_firebase()

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

def get_firebase_mapping():
    mapping_dict = {}
    docs = db.collection('mapeamento_secoes').stream()
    for doc in docs:
        data = doc.to_dict()
        mapping_dict[str(data['COD_SECAO'])] = str(data['ONDE LANÇAR'])
    return mapping_dict

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
    st.warning(f"A seção {secao} não existe no Firebase.")
    obra_input = st.text_input("Onde Lançar (Obra)", placeholder="Ex: 425")
    empresa_input = st.number_input("Empresa", value=1)
    
    if st.button("Salvar no Firebase"):
        if obra_input:
            db.collection('mapeamento_secoes').document(secao).set({
                "COD_SECAO": secao,
                "ONDE LANÇAR": obra_input,
                "EMPRESA": empresa_input
            })
            st.success("Dados salvos na nuvem!")
            st.rerun()
        else:
            st.error("Preencha a obra!")

# --- INTERFACE ---

def main():
    st.set_page_config(page_title="Processador por Seção", layout="wide")
    st.title("📑 Divisor de PDF")

    mapping_dict = get_firebase_mapping()

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
                                
                                # ALTERAÇÃO AQUI: Trocado "FOLHASOMA" por "SM" e "FOLHACAIXA" por "CX"
                                n_soma = get_unique_filename("SM", obra, sufixo, valor_encontrado, filenames_in_zip)
                                filenames_in_zip.add(n_soma)
                                
                                n_caixa = get_unique_filename("CX", obra, sufixo, valor_encontrado, filenames_in_zip)
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