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
#
import streamlit as st
import pdfplumber
from PyPDF2 import PdfReader, PdfWriter
import re
import io
import os
import zipfile
import firebase_admin
from firebase_admin import credentials, firestore

# --- CONFIGURAÇÃO DE CAMINHO ---
OUTPUT_PATH = r"\\\\192.168.1.168\\Anexos\\Documentos Digitalizados\\Nova pasta (39)"

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

def extract_section_near_total(page_text):
    match = re.search(r'TOTAL SEÇÃO:?\s*(\d{2}\.\d{3}\.\d{2})', page_text, re.IGNORECASE)
    if match: return match.group(1)
    if "TOTAL SEÇÃO" in page_text:
        all_codes = re.findall(r'(\d{2}\.\d{3}\.\d{2})', page_text)
        if all_codes: return all_codes[-1]
    return None

def get_firebase_mapping():
    mapping_dict = {}
    docs = db.collection('mapeamento_secoes').stream()
    for doc in docs:
        data = doc.to_dict()
        mapping_dict[str(data['COD_SECAO'])] = str(data['ONDE LANÇAR'])
    return mapping_dict

def get_unique_filename(base_type, obra, sufixo, existing_names):
    nome_base = f"{base_type}{obra}{sufixo}.pdf"
    if nome_base not in existing_names: return nome_base
    counter = 1
    while True:
        novo_nome = f"{base_type}{counter}{obra}{sufixo}.pdf"
        if novo_nome not in existing_names: return novo_nome
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
                "COD_SECAO": secao, "ONDE LANÇAR": obra_input, "EMPRESA": empresa_input
            })
            st.success("Dados salvos!")
            st.rerun()

# --- INTERFACE ---

def main():
    st.set_page_config(page_title="Processador por Seção", layout="wide")
    st.title("📑 Processador de PDFs")

    mapping_dict = get_firebase_mapping()

    st.sidebar.header("Configuração")
    mes_pl = st.sidebar.text_input("Mês", value="01", max_chars=2)
    ano_pl = st.sidebar.text_input("Ano", value="26", max_chars=2)
    sufixo = f"{mes_pl}{ano_pl}"

    uploaded_pdfs = st.file_uploader("Arquivos PDF", type="pdf", accept_multiple_files=True)

    if uploaded_pdfs:
        if st.button("🚀 Iniciar Processamento"):
            all_generated_files = [] # Lista de tuplas (nome, bytes)
            missing = []
            
            # 1. SCAN DE SEÇÕES FALTANTES
            for pdf_file in uploaded_pdfs:
                with pdfplumber.open(pdf_file) as pdf_plumb:
                    for page in pdf_plumb.pages:
                        text = page.extract_text() or ""
                        secao = extract_section_near_total(text)
                        if secao and secao not in mapping_dict and secao not in missing:
                            missing.append(secao)

            if missing:
                cadastrar_secao(missing[0])
                return

            # 2. PROCESSAMENTO EM MEMÓRIA
            used_filenames = set()
            for uploaded_pdf in uploaded_pdfs:
                reader = PdfReader(uploaded_pdf)
                with pdfplumber.open(uploaded_pdf) as pdf_plumb:
                    paginas_acumuladas = []
                    for i, page in enumerate(pdf_plumb.pages):
                        paginas_acumuladas.append(i)
                        text = page.extract_text() or ""
                        secao_encontrada = extract_section_near_total(text)
                        
                        if secao_encontrada and secao_encontrada in mapping_dict:
                            obra = mapping_dict[secao_encontrada]
                            n_soma = get_unique_filename("FOLHASOMA", obra, sufixo, used_filenames)
                            used_filenames.add(n_soma)
                            n_caixa = get_unique_filename("FOLHACAIXA", obra, sufixo, used_filenames)
                            used_filenames.add(n_caixa)
                            
                            writer = PdfWriter()
                            for p_idx in paginas_acumuladas:
                                writer.add_page(reader.pages[p_idx])
                            
                            pdf_bytes = io.BytesIO()
                            writer.write(pdf_bytes)
                            content = pdf_bytes.getvalue()
                            
                            all_generated_files.append((n_soma, content))
                            all_generated_files.append((n_caixa, content))
                            paginas_acumuladas = []

            # 3. TENTATIVA DE SALVAMENTO NA REDE
            save_error = False
            files_saved_count = 0
            
            try:
                if not os.path.exists(OUTPUT_PATH):
                    raise Exception("Caminho de rede inacessível")
                
                for nome, conteudo in all_generated_files:
                    full_path = os.path.join(OUTPUT_PATH, nome)
                    with open(full_path, "wb") as f:
                        f.write(conteudo)
                    files_saved_count += 1
                
                st.success(f"✅ {files_saved_count} arquivos salvos com sucesso em: {OUTPUT_PATH}")
            
            except Exception as e:
                save_error = True
                st.error(f"❌ Erro ao salvar na rede: {e}")
                st.info("O sistema gerou um arquivo ZIP para você baixar manualmente abaixo.")

            # 4. FALLBACK: BOTÃO DE DOWNLOAD (SEMPRE APARECE SE HOUVER ERRO)
            if save_error and all_generated_files:
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w") as zf:
                    for nome, conteudo in all_generated_files:
                        zf.writestr(nome, conteudo)
                
                st.download_button(
                    label="📥 Baixar Arquivos (Download Local)",
                    data=zip_buffer.getvalue(),
                    file_name=f"backup_folhas_{sufixo}.zip",
                    mime="application/zip"
                )

if __name__ == "__main__":
    main()