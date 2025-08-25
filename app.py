from flask import Flask, render_template, request, jsonify, Response, session
from openai import AzureOpenAI
import os
import json
import time
import typing as t
from datetime import timedelta
from pathlib import Path
from dotenv import load_dotenv


env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

print("🔍 DEBUG ENV:", os.getenv("AZURE_OPENAI_API_KEY"))

# Configuración quemada (por ahora)
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-05-01-preview")
AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")

# Validar que estén definidas
missing = []
for var, val in {
    "AZURE_OPENAI_API_KEY": AZURE_OPENAI_API_KEY,
    "AZURE_OPENAI_ENDPOINT": AZURE_OPENAI_ENDPOINT,
    "AZURE_OPENAI_DEPLOYMENT_NAME": AZURE_OPENAI_DEPLOYMENT_NAME
}.items():
    if not val:
        missing.append(var)

if missing:
    raise RuntimeError(f"⚠️ Faltan variables en .env: {', '.join(missing)}")

client = AzureOpenAI(
    api_key=AZURE_OPENAI_API_KEY,
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_version=AZURE_OPENAI_API_VERSION,
)

print("✅ Cliente Azure OpenAI configurado con API Key")

app = Flask(__name__)
app.secret_key = "dev-secret-hardcoded"
app.permanent_session_lifetime = timedelta(days=7)

def _get_or_create_conversation_id(passed_conversation_id: t.Optional[str]) -> str:
    if passed_conversation_id:
        session["conversation_id"] = passed_conversation_id
        return passed_conversation_id
    if "conversation_id" in session and session["conversation_id"]:
        return session["conversation_id"]
    conversation_id = f"conv_{int(time.time())}_{os.getpid()}"
    session["conversation_id"] = conversation_id
    return conversation_id

@app.route("/")
def index():
    return render_template("chat.html")

@app.route("/conversation/new", methods=["POST"])
def new_conversation():
    conversation_id = f"conv_{int(time.time())}_{os.getpid()}"
    session.clear()
    session["conversation_id"] = conversation_id
    session["messages"] = []  # Limpiar historial
    return jsonify({"conversation_id": conversation_id})

@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json(silent=True) or {}
        user_message = (data.get("message") or "").strip()
        passed_conversation_id = data.get("conversation_id")

        if not user_message:
            return jsonify({"error": "No message provided"}), 400

        conversation_id = _get_or_create_conversation_id(passed_conversation_id)

        # Obtener historial de mensajes de la sesión
        messages = session.get("messages", [])

        # Instrucción general si no hay historial
        if not messages:
            system_instruction = "Eres un asistente útil y conversacional, puedes hablar sobre cualquier tema con conocimiento general."
            messages.append({"role": "system", "content": system_instruction})

        messages.append({"role": "user", "content": user_message})

        response = client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT_NAME,
            messages=messages,
            temperature=0.7,
            max_tokens=1000,
            top_p=1,
        )

        assistant_message = response.choices[0].message.content
        messages.append({"role": "assistant", "content": assistant_message})
        session["messages"] = messages

        return jsonify({
            "conversation_id": conversation_id,
            "response": assistant_message
        })

    except Exception as e:
        return jsonify({"error": f"{type(e).__name__}: {str(e)}"}), 500

if __name__ == "__main__":
    print("\U0001F680 Chatbot general con Azure OpenAI")
    app.run(debug=True, port=5000)