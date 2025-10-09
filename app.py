import os
import time
import traceback
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, session
from openai import AzureOpenAI

# ---------- Carga .env ----------
BASE_DIR = Path(__file__).parent.resolve()
load_dotenv(BASE_DIR / ".env")

AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")
ASSISTANT_ID = os.getenv("AZURE_OPENAI_ASSISTANT_ID", "")

if not (AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT and ASSISTANT_ID):
    raise RuntimeError(
        "Faltan variables de entorno: AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_ASSISTANT_ID"
    )

# ---------- Cliente Azure OpenAI ----------
client = AzureOpenAI(
    api_key=AZURE_OPENAI_API_KEY,
    api_version=AZURE_OPENAI_API_VERSION,
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    timeout=60,
)

# ---------- Flask ----------
app = Flask(__name__, template_folder=str(BASE_DIR / "templates"))
app.secret_key = os.getenv("FLASK_SECRET_KEY", "super-secret-key")  # cambia en prod
app.permanent_session_lifetime = timedelta(hours=8)

# ---------- Helpers ----------
def _extract_text_from_message(message) -> str:
    """Extrae texto plano de los 'content' de tipo 'text' de un mensaje."""
    parts = []
    for c in getattr(message, "content", []) or []:
        if getattr(c, "type", None) == "text":
            t = getattr(getattr(c, "text", None), "value", None)
            if t:
                parts.append(t)
    return "\n".join(parts).strip()

def _get_latest_assistant_text(thread_id: str) -> str:
    """Devuelve SIEMPRE el texto Markdown más reciente del asistente."""
    messages = client.beta.threads.messages.list(
        thread_id=thread_id, order="desc", limit=50  # del más nuevo al más viejo
    )
    for m in messages.data:
        if m.role == "assistant":
            txt = _extract_text_from_message(m)
            if txt:
                return txt
    return "No response from assistant."

def _wait_for_run_completion(thread_id: str, run_id: str, timeout_s: int = 60) -> str:
    """Espera a que el run termine y devuelve el status final."""
    t0 = time.time()
    while True:
        run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run_id)
        status = run.status

        if status in ("completed", "failed", "cancelled", "expired"):
            return status
        if status == "requires_action":
            return status
        if time.time() - t0 > timeout_s:
            return "timeout"
        time.sleep(0.8)

# ---------- Rutas ----------
@app.route("/")
def index():
    return render_template("chat.html")

@app.route("/reset", methods=["POST"])
def reset():
    """Borra la sesión para arrancar un hilo nuevo en el próximo /chat."""
    session.clear()
    return jsonify({"ok": True})

@app.route("/chat", methods=["POST"])
def chat():
    """
    Recibe un 'message' del usuario, lo agrega al thread y devuelve:
      - response: texto Markdown (el front lo renderiza a HTML)
    """
    try:
        data = request.get_json(silent=True) or {}
        user_message = (data.get("message") or "").strip()

        if not user_message:
            return jsonify({"error": "Mensaje vacío."}), 400

        # Crear/recuperar thread en la sesión
        if "thread_id" not in session:
            thread = client.beta.threads.create()
            session["thread_id"] = thread.id

        thread_id = session["thread_id"]

        # Añadir mensaje del usuario
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=user_message,
        )

        # Ejecutar assistant
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=ASSISTANT_ID,
        )

        # Esperar finalización
        final_status = _wait_for_run_completion(thread_id, run.id, timeout_s=90)

        if final_status == "completed":
            assistant_md = _get_latest_assistant_text(thread_id)
            return jsonify(
                {
                    "thread_id": thread_id,
                    "status": final_status,
                    "response": assistant_md,  # Markdown (lo renderiza el front)
                }
            )

        if final_status == "requires_action":
            msg = "El asistente requiere una acción adicional (herramientas)."
            return jsonify({"thread_id": thread_id, "status": final_status, "response": msg})

        msg = f"No se pudo completar la ejecución (status={final_status})."
        return jsonify(
            {"thread_id": thread_id, "status": final_status, "response": msg}
        ), 500

    except Exception as e:
        print("❌ Excepción en /chat:", repr(e))
        traceback.print_exc()
        return jsonify({"error": f"{type(e).__name__}: {str(e)}"}), 500

# ---------- Main ----------
if __name__ == "__main__":
    print("🚀 Flask chatbot con Azure OpenAI Assistants")
    app.run(host="0.0.0.0", port=5000, debug=True)
