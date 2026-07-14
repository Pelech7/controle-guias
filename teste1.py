from fastapi import FastAPI, File, UploadFile, Form
from pymongo import MongoClient
import shutil
import os

app = FastAPI(title="Sistema de Guias de Recebimento")

# Conexão com o MongoDB Atlas
URI = "mongodb+srv://vagnernc88_db_user:dQ41bPrAGg6824Dk@cluster0.sbspqlq.mongodb.net/?retryWrites=true&w=majority"
client = MongoClient(URI)
db = client["controle_materiais"]
colecao_guias = db["guias_recebimento"]

# --- NOVA ESTRUTURA DE PASTAS SEPARADAS ---
PASTA_PAI = "armazenamento_pdfs"
PASTA_ORIGINAIS = os.path.join(PASTA_PAI, "originais")
PASTA_ASSINADOS = os.path.join(PASTA_PAI, "assinados")

# Cria as pastas automaticamente se elas não existirem
os.makedirs(PASTA_ORIGINAIS, exist_ok=True)
os.makedirs(PASTA_ASSINADOS, exist_ok=True)


@app.get("/")
def home():
    return {"mensagem": "API de Controle de Guias com pastas organizadas ativa!"}


# 1. Rota para CADASTRAR nova guia (SALVA EM: originais)
@app.post("/guias/upload")
def cadastrar_guia_com_pdf(
    nome_material: str = Form(...),
    data_recebimento: str = Form(...),
    ficheiro_pdf: UploadFile = File(...)
):
    nome_ficheiro = f"{nome_material}_original.pdf"
    # Salva na pasta 'originais'
    caminho_final = os.path.join(PASTA_ORIGINAIS, nome_ficheiro)
    
    with open(caminho_final, "wb") as buffer:
        shutil.copyfileobj(ficheiro_pdf.file, buffer)
        
    nova_guia = {
        "nome_material": nome_material,
        "data_recebimento": data_recebimento,
        "caminho_pdf_original": caminho_final,
        "caminho_pdf_assinado": None, 
        "status": "pendente"          
    }
    
    colecao_guias.insert_one(nova_guia)
    return {"mensagem": "Guia original salva em /originais com sucesso!"}


# 2. Rota para LISTAR guias PENDENTES
@app.get("/guias/pendentes")
def listar_pendentes():
    guias = list(colecao_guias.find({"status": "pendente"}, {"_id": 0}))
    return {"guias": guias}


# 3. Rota para LISTAR guias ASSINADAS
@app.get("/guias/assinadas")
def listar_assinadas():
    guias = list(colecao_guias.find({"status": "assinada"}, {"_id": 0}))
    return {"guias": guias}


# 4. Rota para ASSINAR a guia (SALVA EM: assinados)
@app.put("/guias/{nome_material}/assinar")
def assinar_guia(
    nome_material: str,
    ficheiro_pdf_assinado: UploadFile = File(...)
):
    nome_ficheiro = f"{nome_material}_assinado.pdf"
    # Salva na pasta 'assinados'
    caminho_final = os.path.join(PASTA_ASSINADOS, nome_ficheiro)
    
    with open(caminho_final, "wb") as buffer:
        shutil.copyfileobj(ficheiro_pdf_assinado.file, buffer)
        
    resultado = colecao_guias.update_one(
        {"nome_material": nome_material},
        {"$set": {
            "caminho_pdf_assinado": caminho_final,
            "status": "assinada"
        }}
    )
    
    if resultado.modified_count == 0:
        return {"erro": "Material não encontrado."}
        
    return {"mensagem": f"Material {nome_material} assinado e salvo em /assinados!"}