import os
import time
import traceback
from flask import Flask, render_template, request, jsonify, session
from datetime import timedelta
from openai import AzureOpenAI
import httpx
from dotenv import load_dotenv
from pathlib import Path

# Cargar variables desde .env
load_dotenv(dotenv_path=Path('.') / '.env')

# Inicializar cliente Azure OpenAI con API Key
client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-05-01-preview"),
    http_client=httpx.Client(verify=False)  # ⚠️ para desarrollo local sin certificados
)

app = Flask(__name__)
app.secret_key = "dev-secret-hardcoded"
app.permanent_session_lifetime = timedelta(days=7)

@app.route("/")
def index():
    return render_template("chat.html")

@app.route("/conversation/new", methods=["POST"])
def new_conversation():
    conversation_id = f"conv_{int(time.time())}_{os.getpid()}"
    session.clear()
    session["conversation_id"] = conversation_id
    session["messages"] = []
    return jsonify({"conversation_id": conversation_id})

# @app.route("/chat", methods=["POST"])
# def chat():
#     try:
#         data = request.get_json(silent=True) or {}
#         user_message = (data.get("message") or "").strip()
#         passed_conversation_id = data.get("conversation_id")

#         if not user_message:
#             return jsonify({"error": "No message provided"}), 400

#         conversation_id = passed_conversation_id or session.get("conversation_id")
#         if not conversation_id:
#             conversation_id = f"conv_{int(time.time())}_{os.getpid()}"
#             session["conversation_id"] = conversation_id
#             session["messages"] = []

#         messages = session.get("messages", [])

#         if not messages:
#             messages.append({
#                 "role": "system",
#                 "content": "Eres un asistente experto en información de Colombia."
#             })

#         messages.append({"role": "user", "content": user_message})

#         response = client.chat.completions.create(
#             model=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),  # ← el nombre del deployment
#             messages=messages,
#             temperature=0.7,
#             max_tokens=1000,
#             top_p=1
#         )

#         assistant_message = response.choices[0].message.content

#         messages.append({"role": "assistant", "content": assistant_message})
#         session["messages"] = messages

#         return jsonify({
#             "conversation_id": conversation_id,
#             "response": assistant_message
#         })

#     except Exception as e:
#         print("❌ Excepción en /chat:", repr(e))
#         traceback.print_exc()
#         return jsonify({"error": f"{type(e).__name__}: {str(e)}"}), 500

@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json(silent=True) or {}
        user_message = (data.get("message") or "").strip()
        passed_conversation_id = data.get("conversation_id")

        if not user_message:
            return jsonify({"error": "No message provided"}), 400

        # Obtener el assistant_id del .env
        assistant_id = os.getenv("AZURE_OPENAI_ASSISTANT_ID")

        # Crear un nuevo thread si no hay uno activo
        if "thread_id" not in session:
            thread = client.beta.threads.create()
            session["thread_id"] = thread.id

        thread_id = session["thread_id"]

        # Agregar mensaje del usuario al thread
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=user_message
        )

        # Lanzar ejecución del assistant
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant_id
        )

        # Esperar a que termine la ejecución
        while run.status in ["queued", "in_progress"]:
            time.sleep(1)
            run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)

        if run.status != "completed":
            return jsonify({"error": f"Assistant run failed: {run.status}"}), 500

        # Obtener los mensajes del thread (último mensaje es la respuesta)
        messages = client.beta.threads.messages.list(thread_id=thread_id)
        assistant_message = next(
            (m.content[0].text.value for m in reversed(messages.data) if m.role == "assistant"),
            "No response from assistant."
        )

        return jsonify({
            "conversation_id": passed_conversation_id or session.get("conversation_id"),
            "response": assistant_message
        })

    except Exception as e:
        print("❌ Excepción en /chat:", repr(e))
        traceback.print_exc()
        return jsonify({"error": f"{type(e).__name__}: {str(e)}"}), 500


if __name__ == "__main__":
    print("🚀 Flask chatbot con Azure OpenAI (chat.completions)")
    app.run(debug=True, port=5000)