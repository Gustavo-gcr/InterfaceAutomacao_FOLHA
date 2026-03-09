# import streamlit as st
# import pdfplumber
# from PyPDF2 import PdfReader, PdfWriter
# import re
# import io
# import zipfile
# import json
# import os

# # --- FUNÇÕES DE LEITURA E ESCRITA DO JSON ---

# def get_json_mapping():
#     """
#     Lê o mapeamento diretamente do arquivo JSON na raiz.
#     """
#     mapping_dict = {}
#     if os.path.exists('mapeamento_planilha.json'):
#         with open('mapeamento_planilha.json', 'r', encoding='utf-8') as f:
#             try:
#                 data = json.load(f)
#                 for item in data:
#                     mapping_dict[str(item.get('COD_SECAO', ''))] = str(item.get('ONDE LANÇAR', ''))
#             except json.JSONDecodeError:
#                 pass # Caso o arquivo esteja vazio ou inválido
#     return mapping_dict

# def save_to_json(secao, obra_input, empresa_input):
#     """
#     Salva a nova seção no arquivo JSON local.
#     """
#     file_path = 'mapeamento_planilha.json'
    
#     # Lê os dados atuais
#     if os.path.exists(file_path):
#         with open(file_path, 'r', encoding='utf-8') as f:
#             try:
#                 data = json.load(f)
#             except json.JSONDecodeError:
#                 data = []
#     else:
#         data = []
        
#     # Adiciona a nova seção à lista
#     data.append({
#         "COD_SECAO": secao,
#         "ONDE LANÇAR": obra_input,
#         "EMPRESA": empresa_input
#     })
    
#     # Grava novamente no arquivo
#     with open(file_path, 'w', encoding='utf-8') as f:
#         json.dump(data, f, ensure_ascii=False, indent=4)


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
#     st.warning(f"A seção {secao} não existe no arquivo mapeamento_planilha.json.")
#     obra_input = st.text_input("Onde Lançar (Obra)", placeholder="Ex: 425")
#     empresa_input = st.number_input("Empresa", value=1)
    
#     if st.button("Salvar no JSON"):
#         if obra_input:
#             save_to_json(secao, obra_input, empresa_input)
#             st.success("Dados salvos localmente com sucesso!")
#             st.rerun()
#         else:
#             st.error("Preencha a obra!")

# # --- INTERFACE ---

# def main():
#     st.set_page_config(page_title="Processador por Seção", layout="wide")
#     st.title("📑 Divisor de PDF")

#     mapping_dict = get_json_mapping()

#     st.sidebar.header("Configuração de Data")
#     mes_pl = st.sidebar.text_input("Mês", value="01", max_chars=2)
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
    
    # --- CAMINHO DE REDE DEFINIDO AQUI ---
    # O "r" antes da string é essencial para o Python não confundir as barras invertidas
    caminho_rede = r"\\192.168.1.168\Anexos\Documentos Digitalizados\Nova pasta (39)"

    st.sidebar.header("Tipo de Lançamento")
    tipo_lancamento = st.sidebar.radio("Selecione o tipo:", ["Salários", "Adiantamento"])

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
            erros_rede = 0
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
                                
                                if tipo_lancamento == "Salários":
                                    prefixos = ["FOLHASM", "FOLHACX"]
                                else:
                                    prefixos = ["ADIANTSM", "ADIANTCX"]
                                
                                nomes_gerados = []
                                for pref in prefixos:
                                    nome_arq = get_unique_filename(pref, obra, sufixo, valor_encontrado, filenames_in_zip)
                                    filenames_in_zip.add(nome_arq)
                                    nomes_gerados.append(nome_arq)
                                
                                writer = PdfWriter()
                                for p_idx in paginas_acumuladas:
                                    writer.add_page(reader.pages[p_idx])
                                
                                for nome in nomes_gerados:
                                    pdf_out = io.BytesIO()
                                    writer.write(pdf_out)
                                    pdf_bytes = pdf_out.getvalue()
                                    
                                    # 1. Salva no ZIP para o botão de download
                                    zip_file.writestr(nome, pdf_bytes)
                                    
                                    # 2. Tenta salvar o PDF individual direto na pasta de rede
                                    try:
                                        if not os.path.exists(caminho_rede):
                                            os.makedirs(caminho_rede, exist_ok=True)
                                            
                                        caminho_arquivo_rede = os.path.join(caminho_rede, nome)
                                        with open(caminho_arquivo_rede, 'wb') as f_rede:
                                            f_rede.write(pdf_bytes)
                                    except Exception as e:
                                        erros_rede += 1
                                        # Printa o erro silenciosamente no terminal pra não poluir tanto o app
                                        print(f"Erro ao salvar na rede: {e}")
                                        
                                    processed_count += 1
                                
                                paginas_acumuladas = []
                            
                        if paginas_acumuladas:
                            st.warning(f"As últimas {len(paginas_acumuladas)} páginas do arquivo {uploaded_pdf.name} não continham um 'TOTAL SEÇÃO' e foram ignoradas.")

            if processed_count > 0:
                if erros_rede == 0:
                    st.success(f"Finalizado! {processed_count} arquivos gerados e salvos automaticamente na pasta de rede.")
                else:
                    st.warning(f"Processamento concluído. O ZIP foi gerado, mas houve erro ao salvar {erros_rede} arquivo(s) na pasta de rede. Verifique se a pasta está acessível.")
                
                st.download_button(
                    label="📥 Baixar ZIP (Backup)",
                    data=zip_buffer.getvalue(),
                    file_name=f"folhas_agrupadas_{sufixo}.zip",
                    mime="application/zip"
                )

if __name__ == "__main__":
    main()