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
import os
import firebase_admin
from firebase_admin import credentials, firestore

# --- CONFIGURAÇÃO DE CAMINHO ---
OUTPUT_PATH = r"\\192.168.1.168\Anexos\Documentos Digitalizados\Nova pasta (39)"

# --- CONFIGURAÇÃO FIREBASE ---
def init_firebase():
    if not firebase_admin._apps:
        try:
            cred_dict = {
                "type": st.secrets["firebase"]["type"],
                "project_id": st.secrets["firebase"]["project_id"],
                "private_key_id": st.secrets["firebase"]["private_key_id"],
                "private_key": st.secrets["firebase"]["private_key"].replace("\\n", "\n"),
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
        except Exception as e:
            st.error(f"Erro ao conectar Firebase: {e}")
    return firestore.client()

db = init_firebase()

# --- FUNÇÕES DE AUXÍLIO ---

def extract_section_near_total(page_text):
    # Tenta achar padrão exato perto de "TOTAL SEÇÃO"
    match = re.search(r'TOTAL SEÇÃO:?\s*(\d{2}\.\d{3}\.\d{2})', page_text, re.IGNORECASE)
    if match: return match.group(1)
    
    # Fallback: se tem o texto "TOTAL SEÇÃO", pega o último código da página
    if "TOTAL SEÇÃO" in page_text:
        all_codes = re.findall(r'(\d{2}\.\d{3}\.\d{2})', page_text)
        if all_codes: return all_codes[-1]
    return None

def get_firebase_mapping():
    mapping_dict = {}
    try:
        docs = db.collection('mapeamento_secoes').stream()
        for doc in docs:
            data = doc.to_dict()
            mapping_dict[str(data['COD_SECAO'])] = str(data['ONDE LANÇAR'])
    except Exception as e:
        st.error(f"Erro ao buscar mapeamento no Firebase: {e}")
    return mapping_dict

def get_unique_filename(base_type, obra, sufixo, existing_names):
    nome_base = f"{base_type}{obra}{sufixo}.pdf"
    if nome_base not in existing_names: return nome_base
    counter = 1
    while True:
        novo_nome = f"{base_type}{counter}{obra}{sufixo}.pdf"
        if novo_nome not in existing_names: return novo_nome
        counter += 1

# --- DIALOGO CADASTRO ---
@st.dialog("Nova Seção Encontrada")
def cadastrar_secao(secao):
    st.warning(f"A seção {secao} não existe no Firebase.")
    obra_input = st.text_input("Onde Lançar (Obra)", placeholder="Ex: 425")
    empresa_input = st.number_input("Empresa", value=1)
    if st.button("Salvar no Firebase"):
        if obra_input:
            try:
                db.collection('mapeamento_secoes').document(secao).set({
                    "COD_SECAO": secao, "ONDE LANÇAR": obra_input, "EMPRESA": empresa_input
                })
                st.success("Dados salvos!")
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao salvar: {e}")

# --- INTERFACE PRINCIPAL ---

def main():
    st.set_page_config(page_title="Processador Automático", layout="wide")
    st.title("📑 Divisor PDF: Rede ou Download")

    # Inicializa estado para armazenar arquivos que falharam no envio para a rede
    if 'arquivos_para_download' not in st.session_state:
        st.session_state['arquivos_para_download'] = []

    mapping_dict = get_firebase_mapping()

    st.sidebar.header("Configuração")
    mes_pl = st.sidebar.text_input("Mês", value="01", max_chars=2)
    ano_pl = st.sidebar.text_input("Ano", value="26", max_chars=2)
    sufixo = f"{mes_pl}{ano_pl}"

    uploaded_pdfs = st.file_uploader("Arraste os PDFs aqui", type="pdf", accept_multiple_files=True)

    if uploaded_pdfs:
        if st.button("🚀 Iniciar Processo"):
            # Limpa downloads anteriores
            st.session_state['arquivos_para_download'] = []
            
            # 1. Validação de Seções (Passada rápida)
            missing = []
            progress_bar = st.progress(0)
            
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

            # 2. Processamento Real
            used_filenames = set()
            container_log = st.container()
            
            # Espaço visual para logs
            with container_log:
                st.write("---")
                st.subheader("Log de Processamento")

            total_arquivos = len(uploaded_pdfs)
            
            for idx_file, pdf_file in enumerate(uploaded_pdfs):
                reader = PdfReader(pdf_file)
                
                # Abre com pdfplumber para ler texto
                with pdfplumber.open(pdf_file) as pdf_plumb:
                    paginas_acumuladas = []
                    
                    for i, page in enumerate(pdf_plumb.pages):
                        paginas_acumuladas.append(i)
                        text = page.extract_text() or ""
                        secao_encontrada = extract_section_near_total(text)
                        
                        if secao_encontrada and secao_encontrada in mapping_dict:
                            obra = mapping_dict[secao_encontrada]
                            
                            # Gerar PDF em memória
                            writer = PdfWriter()
                            for p_idx in paginas_acumuladas:
                                writer.add_page(reader.pages[p_idx])
                            
                            pdf_out = io.BytesIO()
                            writer.write(pdf_out)
                            content = pdf_out.getvalue()
                            
                            # Gerar os dois arquivos (Soma e Caixa)
                            for tipo in ["FOLHASOMA", "FOLHACAIXA"]:
                                nome = get_unique_filename(tipo, obra, sufixo, used_filenames)
                                used_filenames.add(nome)
                                
                                salvou_rede = False
                                
                                # TENTATIVA 1: Salvar na Rede
                                try:
                                    # Verifica se o diretório pai existe
                                    if os.path.exists(OUTPUT_PATH):
                                        full_path = os.path.join(OUTPUT_PATH, nome)
                                        with open(full_path, "wb") as f:
                                            f.write(content)
                                        salvou_rede = True
                                    else:
                                        # Tenta criar se for mapeado localmente, mas se for UNC path pode falhar
                                        pass 
                                except Exception as e:
                                    salvou_rede = False
                                
                                if salvou_rede:
                                    container_log.success(f"✅ {nome} -> Salvo na Rede")
                                else:
                                    container_log.warning(f"⚠️ {nome} -> Rede falhou. Adicionado para download.")
                                    # Adiciona à lista de download manual
                                    st.session_state['arquivos_para_download'].append({
                                        "nome": nome,
                                        "dados": content
                                    })
                            
                            # Limpa buffer
                            paginas_acumuladas = []
                
                # Atualiza barra de progresso
                progress_bar.progress((idx_file + 1) / total_arquivos)

            st.success("🏁 Processamento Finalizado!")

    # --- ÁREA DE DOWNLOAD MANUAL ---
    # Isso garante que os botões persistam e funcionem corretamente "um por um"
    if st.session_state['arquivos_para_download']:
        st.write("---")
        st.subheader("📥 Arquivos para Download (Não salvos na rede)")
        st.info("Estes arquivos não puderam ser salvos no caminho de rede. Baixe-os abaixo:")
        
        # Cria colunas para organizar os botões (opcional, para ficar mais bonito)
        cols = st.columns(3)
        
        for index, item in enumerate(st.session_state['arquivos_para_download']):
            col = cols[index % 3]
            with col:
                st.download_button(
                    label=f"⬇️ {item['nome']}",
                    data=item['dados'],
                    file_name=item['nome'],
                    mime="application/pdf",
                    key=f"btn_{index}"
                )

if __name__ == "__main__":
    main()