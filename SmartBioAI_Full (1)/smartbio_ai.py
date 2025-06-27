# Projeto: SmartBio AI - A bio inteligente que vende por você

"""
IDEIA:
Um app que gera páginas de bio otimizadas automaticamente com IA.
Ideal para empreendedores, afiliados e influencers que vendem pelo Instagram, TikTok e WhatsApp.
"""

# Etapas iniciais do projeto:
# 1. Perguntas para o usuário
# 2. Geração da copy da bio
# 3. Montagem da página
# 4. Exibição em link curto personalizado
# 5. Armazenamento em banco de dados
# 6. Tela de login e dashboard (com autenticação básica implementada)
# 7. Gerador de páginas reais simuladas (landing básica com HTML)
# 8. Hospedagem via Flask para servir as páginas publicamente

# Dependências: transformers, gradio, sqlite3, uuid, os, flask

from transformers import pipeline
import gradio as gr
import uuid
import sqlite3
import os
from flask import Flask, send_from_directory
import threading

# Banco de dados SQLite
conn = sqlite3.connect("bios.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS bios (
    id TEXT PRIMARY KEY,
    usuario_email TEXT,
    nome_negocio TEXT,
    produto TEXT,
    objetivo TEXT,
    bio TEXT,
    link TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE,
    senha TEXT
)
""")
conn.commit()

# Geração de texto com modelo GPT2
generator = pipeline("text-generation", model="gpt2")

# Sessão de usuário logado
usuario_logado = {"email": None}

def registrar_usuario(email, senha):
    try:
        cursor.execute("INSERT INTO usuarios (email, senha) VALUES (?, ?)", (email, senha))
        conn.commit()
        return "Usuário registrado com sucesso! Vá para Login."
    except sqlite3.IntegrityError:
        return "Email já registrado. Tente outro."

def login(email, senha):
    cursor.execute("SELECT * FROM usuarios WHERE email = ? AND senha = ?", (email, senha))
    user = cursor.fetchone()
    if user:
        usuario_logado["email"] = email
        return f"Bem-vindo, {email}! Vá para o gerador de bios."
    return "Credenciais inválidas. Tente novamente."

def gerar_bio(nome_negocio, produto_servico, objetivo_link):
    if not usuario_logado["email"]:
        return "Você precisa estar logado para gerar bios."

    prompt = (
        f"Crie uma bio de Instagram que seja persuasiva, com tom vendedor e amigável, para um negócio chamado {nome_negocio}, "
        f"que vende {produto_servico}, com foco em fazer as pessoas clicarem em {objetivo_link}."
    )
    resposta = generator(prompt, max_new_tokens=100, do_sample=True, temperature=0.9)[0]['generated_text']
    bio_id = str(uuid.uuid4())[:8]
    link = f"http://localhost:5000/{bio_id}"

    cursor.execute("INSERT INTO bios (id, usuario_email, nome_negocio, produto, objetivo, bio, link) VALUES (?, ?, ?, ?, ?, ?, ?)",
                   (bio_id, usuario_logado["email"], nome_negocio, produto_servico, objetivo_link, resposta.strip(), link))
    conn.commit()

    html_content = f"""
    <html>
        <head><title>{nome_negocio}</title></head>
        <body style='font-family: Arial; padding: 40px;'>
            <h1>{nome_negocio}</h1>
            <p><strong>O que você oferece:</strong> {produto_servico}</p>
            <p><strong>Objetivo:</strong> {objetivo_link}</p>
            <p><strong>Bio:</strong> {resposta.strip()}</p>
        </body>
    </html>
    """
    os.makedirs("bios_pages", exist_ok=True)
    with open(f"bios_pages/{bio_id}.html", "w", encoding="utf-8") as f:
        f.write(html_content)

    return f"\n📄 Bio gerada:\n{resposta.strip()}\n\n🔗 Link da sua página: {link}"

def listar_bios():
    if not usuario_logado["email"]:
        return "Faça login para ver suas bios."

    cursor.execute("SELECT nome_negocio, produto, objetivo, link FROM bios WHERE usuario_email = ?", (usuario_logado["email"],))
    linhas = cursor.fetchall()
    if not linhas:
        return "Você ainda não gerou nenhuma bio."
    resposta = "\n📁 Suas Bios:\n"
    for nome, produto, objetivo, link in linhas:
        resposta += f"• {nome} — {produto} — {objetivo}\n  🔗 {link}\n"
    return resposta

# Iniciar servidor Flask em paralelo
app = Flask(__name__)

@app.route('/<page_id>')
def serve_bio(page_id):
    return send_from_directory('bios_pages', f'{page_id}.html')

def iniciar_flask():
    app.run(debug=False, use_reloader=False)

threading.Thread(target=iniciar_flask).start()

# Interfaces Gradio
cadastro_interface = gr.Interface(
    fn=registrar_usuario,
    inputs=[gr.Textbox(label="Email"), gr.Textbox(label="Senha", type="password")],
    outputs="text",
    title="Cadastro de Usuário"
)

login_interface = gr.Interface(
    fn=login,
    inputs=[gr.Textbox(label="Email"), gr.Textbox(label="Senha", type="password")],
    outputs="text",
    title="Login"
)

bio_interface = gr.Interface(
    fn=gerar_bio,
    inputs=[
        gr.Textbox(label="Nome do seu negócio"),
        gr.Textbox(label="Produto ou serviço que você vende"),
        gr.Textbox(label="Objetivo do link (ex: ir para WhatsApp, comprar, seguir)")
    ],
    outputs="text",
    title="SmartBio AI"
)

dashboard_interface = gr.Interface(
    fn=listar_bios,
    inputs=[],
    outputs="text",
    title="Suas Bios Geradas"
)

gr.TabbedInterface(
    [cadastro_interface, login_interface, bio_interface, dashboard_interface],
    ["Cadastro", "Login", "Gerar Bio", "Minhas Bios"]
).launch()
