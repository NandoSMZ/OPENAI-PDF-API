from flask import Flask, request, jsonify
import openai
import os
from dotenv import load_dotenv
import time

load_dotenv()

client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
ASSISTANT_ID = os.getenv("OPENAI_ASSISTANT_ID")

app = Flask(__name__)

@app.route('/parse-pdf', methods=['POST'])
def parse_pdf():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    # Asegurarnos de que el stream esté al inicio
    file.stream.seek(0)

    # 1) Subir el PDF indicando nombre y tipo
    uploaded_file = client.files.create(
        file=( file.filename or "invoice.pdf",
               file.stream,
               file.content_type or "application/pdf" ),
        purpose="assistants"
    )

    # 2) Crear nuevo hilo
    thread = client.beta.threads.create()

    # 3) Enviar mensaje con attachment (no file_ids)
    client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content="Extrae los datos de esta factura",
        attachments=[
            {
                "file_id": uploaded_file.id,
                "tools": [{"type": "file_search"}]
            }
        ]
    )

    # 4) Ejecutar asistente
    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=ASSISTANT_ID
    )

    # 5) Esperar a que termine
    while True:
        run_status = client.beta.threads.runs.retrieve(
            thread_id=thread.id,
            run_id=run.id
        )
        if run_status.status == "completed":
            break
        elif run_status.status == "failed":
            return jsonify({"error": "OpenAI run failed"}), 500
        time.sleep(1)

    # 6) Obtener la respuesta final
    messages = client.beta.threads.messages.list(thread_id=thread.id)
    last_response = messages.data[0].content[0].text.value

    return jsonify({"csv": last_response})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)