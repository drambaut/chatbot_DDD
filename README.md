# Chatbot DDD

Un chatbot simple que se conecta a Azure OpenAI usando la API de Chat Completion (Responses API).

## 🚀 Instalación

1. **Instalar dependencias:**
```bash
pip install -r requirements.txt
```

2. **Crear archivo .env con tus credenciales:**
```env
AZURE_OPENAI_ENDPOINT=https://tu-resource.openai.azure.com
AZURE_OPENAI_API_KEY=tu-api-key-aqui
AZURE_OPENAI_API_VERSION=2024-10-21
AZURE_OPENAI_DEPLOYMENT_NAME=tu-deployment-name
FLASK_SECRET_KEY=tu-clave-secreta-aqui
```

3. **Ejecutar:**
```bash
python app.py
```

4. **Abrir en el navegador:**
```
http://localhost:5000
```

## 🔑 Configuración

Para obtener tu **Deployment Name**:

1. Ve a [Azure OpenAI Studio](https://oai.azure.com/)
2. Selecciona tu recurso
3. Ve a "Deployments"
4. Copia el nombre de tu deployment
5. Pégalo en tu archivo `.env`

## 📁 Archivos

- `app.py` - Aplicación Flask con API de Responses
- `templates/chat.html` - Interfaz del chat
- `requirements.txt` - Dependencias Python
- `.env` - Credenciales (crear tú mismo)

## 🔄 Migración de Assistants API

Este proyecto ha sido migrado de la API de Assistants (deprecada) a la API de Responses. Los cambios principales son:

- ✅ Eliminados todos los warnings de deprecación
- ✅ Uso directo de Chat Completion API
- ✅ Gestión de conversaciones en sesión local
- ✅ Interfaz mejorada con botón de reinicio
- ✅ Indicador de "escribiendo..."

## ✅ Listo

¡Eso es todo! Solo necesitas configurar tus credenciales y el nombre de tu deployment.