import streamlit as st
import pandas as pd
from azure.storage.blob import BlobServiceClient
import os
import pyodbc
import uuid
import json
from dotenv import load_dotenv
load_dotenv()

# --- VARIÁVEIS DE AMBIENTE ---
blobConnectionString = os.getenv("BLOB_CONNECTION_STRING")
blobContainerName = os.getenv("BLOB_CONTAINER_NAME")
blobAccountName = os.getenv("BLOB_ACCOUNT_NAME")

SQL_SERVER = os.getenv("SQL_SERVER")
SQL_DATABASE = os.getenv("SQL_DATABASE")
SQL_USER = os.getenv("SQL_USER")
SQL_PASSWORD = os.getenv("SQL_PASSWORD")

# --- CONFIGURAÇÃO DA CONEXÃO PYODBC (ESCOPO GLOBAL) ---
# IMPORTANTE: Verifique e ajuste o nome do DRIVER conforme o seu sistema operacional e drivers instalados.
# Exemplos comuns:
# - No Windows: '{ODBC Driver 17 for SQL Server}' ou '{SQL Server}'
# - No Linux/macOS (com unixODBC e MS ODBC Driver): '{ODBC Driver 17 for SQL Server}'
DB_DRIVER = '{ODBC Driver 17 for SQL Server}' # <--- **AJUSTE ESTE VALOR SE NECESSÁRIO!**

DB_CONNECTION_STRING = (
    f"DRIVER={DB_DRIVER};"
    f"SERVER={SQL_SERVER};"
    f"DATABASE={SQL_DATABASE};"
    f"UID={SQL_USER};"
    f"PWD={SQL_PASSWORD}"
)
# --- FIM DA CONFIGURAÇÃO GLOBAL ---

st.title('Cadastro de Produtos')

# Formulário de produtos
product_name = st.text_input('Nome do Produto')
product_price = st.number_input('Preço do Produto', min_value=0.0, format='%.2f')
product_description = st.text_area('Descrição do Produto')
product_image = st.file_uploader('Imagem do Produto', type=('jpg', 'jpeg', 'png'))

# --- FUNÇÃO PARA UPLOAD DE IMAGEM ---
def upload_blob(file):
    try:
        blob_service_client = BlobServiceClient.from_connection_string(blobConnectionString)
        container_client = blob_service_client.get_container_client(blobContainerName)
        blob_name = str(uuid.uuid4()) + "_" + file.name # Adicione um separador para melhor legibilidade
        blob_client = container_client.get_blob_client(blob_name)
        blob_client.upload_blob(file.read(), overwrite=True)
        image_url = f"https://{blobAccountName}.blob.core.windows.net/{blobContainerName}/{blob_name}"
        st.success("Imagem enviada para o Blob Storage com sucesso!")
        return image_url
    except Exception as e:
        st.error(f"Erro ao fazer upload da imagem: {e}")
        return None

# --- FUNÇÃO PARA INSERIR PRODUTO NO BANCO DE DADOS ---
def insert_product(name, price, description, image_url):
    try:
        conn = pyodbc.connect(DB_CONNECTION_STRING)
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO Produtos (nome, descricao, preco, imagem_url) VALUES (?, ?, ?, ?)", 
            (name, description, price, image_url)
        )
        
        conn.commit()
        conn.close()
        st.success('Produto salvo com sucesso no banco de dados!')
        return True
    except pyodbc.Error as e:
        sqlstate = e.args[0]
        st.error(f'Erro ao inserir produto no banco de dados (SQLSTATE: {sqlstate}): {e}')
        return False

# --- FUNÇÃO PARA OBTER TODOS OS PRODUTOS DO BANCO DE DADOS ---
def get_products():
    try:
        conn = pyodbc.connect(DB_CONNECTION_STRING)
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, nome, descricao, preco, imagem_url FROM Produtos")
        
        # Obter os nomes das colunas a partir da descrição do cursor
        columns = [column[0] for column in cursor.description]
        
        # Buscar todas as linhas e combiná-las com os nomes das colunas em dicionários
        products_data = []
        for row in cursor.fetchall():
            product_dict = {}
            for i, col_name in enumerate(columns):
                product_dict[col_name] = row[i]
            products_data.append(product_dict)
            
        conn.close()
        st.success('Produtos carregados do banco de dados com sucesso!')
        return products_data
    except pyodbc.Error as e:
        sqlstate = e.args[0]
        st.error(f'Erro ao carregar produtos do banco de dados (SQLSTATE: {sqlstate}): {e}')
        return []

# --- FUNÇÃO PARA EXIBIR PRODUTOS NA TELA (CARDS) ---
def display_products_as_cards(products):
    if products:
        cards_per_row = 3
        
        # Garante que as colunas sejam criadas para a primeira linha
        cols = st.columns(cards_per_row) 
        
        for i, product in enumerate(products):
            # Determina em qual coluna o card atual será exibido
            col_index = i % cards_per_row
            with cols[col_index]:
                st.markdown(f"### {product['nome']}")
                st.write(f"**Descrição:** {product['descricao']}")
                st.write(f"**Preço:** R${product['preco']:.2f}")
                if product.get('imagem_url'): # Usar .get para evitar KeyError se a coluna não existir
                    html_img = f'<img src="{product["imagem_url"]}" width="200" height="200" style="object-fit: contain; border-radius: 5px;">'
                    st.markdown(html_img, unsafe_allow_html=True)
                st.markdown('---') # Separador entre card
            
            # Se a linha atual estiver cheia e não for o último item, cria novas colunas para a próxima linha
            if (i + 1) % cards_per_row == 0 and (i + 1) < len(products):
                cols = st.columns(cards_per_row)
    else:
        st.info('Nenhum produto cadastrado para exibir.')

# --- AÇÕES DA INTERFACE DO USUÁRIO ---
if st.button('Salvar Produto'):
    if product_name and product_price is not None and product_description and product_image:
        image_url = upload_blob(product_image)
        if image_url: # Apenas insere se o upload da imagem foi bem-sucedido
            insert_product(product_name, product_price, product_description, image_url)
    else:
        st.warning("Por favor, preencha todos os campos e selecione uma imagem antes de salvar.")

st.header('Produtos Cadastrados')

if st.button('Listar Produtos'):
    products_data = get_products() # Obtém os dados do banco
    if products_data:
        # Exibe em um DataFrame do Pandas para depuração/visão geral
        st.subheader("Dados em Tabela (para depuração)")
        df = pd.DataFrame(products_data)
        st.dataframe(df)
        
        # Exibe os produtos como cards
        st.subheader("Produtos em Cards")
        display_products_as_cards(products_data)
    else:
        st.info("Nenhum produto encontrado para listar.")