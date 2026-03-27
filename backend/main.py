"""
Entry point del FinOps AI Copilot
Funciona como backend Flask (por defecto) o como CLI interactiva (con --cli)
"""
import os
import sys
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from src.agent.agent import create_finops_agent, run_agent

# Cargar variables de entorno al inicio
load_dotenv()

# ─── Flask App ────────────────────────────────────────────────
app = Flask(__name__)

# Variable global para el agente (se inicializa una sola vez)
_agent = None


def setup_langsmith():
    """
    Configura LangSmith para monitoreo y trazabilidad del agente.
    Las credenciales se leen del archivo .env
    """
    langsmith_api_key = os.getenv("LANGCHAIN_API_KEY")

    if langsmith_api_key:
        os.environ["LANGSMITH_ENDPOINT"] = "https://api.smith.langchain.com"
        os.environ["LANGCHAIN_API_KEY"] = langsmith_api_key
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGCHAIN_PROJECT", "FinOps_AI_Copilot")
        print("LangSmith habilitado - Proyecto:", os.environ["LANGCHAIN_PROJECT"])
        return True
    else:
        print("LangSmith no configurado (LANGCHAIN_API_KEY no encontrada)")
        return False


def get_agent():
    """Retorna la instancia del agente, creándola si no existe."""
    global _agent
    if _agent is None:
        print(" Inicializando agente...")
        _agent = create_finops_agent()
        print("Agente inicializado correctamente")
    return _agent


# ─── Configuración inicial al cargar el módulo ───────────────
setup_langsmith()


# ─── Endpoints ────────────────────────────────────────────────
@app.route('/agent', methods=['GET'])
def agent_endpoint():
    """
    Endpoint principal del agente FinOps.
    Parámetros (query string):
        - idagente: ID del hilo de conversación (default: 'default')
        - msg: Mensaje/consulta del usuario (requerido)
    """
    id_usuario = request.args.get('idagente', 'default')
    msg = request.args.get('msg')

    # Validar que se envió un mensaje
    if not msg:
        return jsonify({"error": "El parámetro 'msg' es requerido"}), 400

    try:
        agent = get_agent()
        response = run_agent(agent, msg, thread_id=id_usuario)
        return jsonify({"response": response, "thread_id": id_usuario})
    except Exception as e:
        return jsonify({"error": f"Error al procesar la consulta: {str(e)}"}), 500


@app.route('/', methods=['GET'])
def health_check():
    """Endpoint de health check para Cloud Run."""
    return jsonify({"status": "ok", "service": "FinOps AI Copilot"})


# ─── Modo CLI (interactivo) ──────────────────────────────────
def main_cli():
    """
    Función para el modo CLI interactivo (uso local).
    Se activa con: python main.py --cli
    """
    print("=" * 60)
    print(" FinOps AI Copilot".center(60))
    print("=" * 60)
    print()

    # Crear agente
    try:
        agent = get_agent()
    except Exception as e:
        print(f"Error al inicializar agente: {e}")
        return

    # Mensaje de bienvenida
    print("Bienvenido al FinOps AI Copilot")
    print("   Puedo ayudarte a analizar datos financieros por:")
    print("   - TORRE/Gerencia")
    print("   - País")
    print("   - Centro de Costos")
    print("   - ID de proyecto")
    print()
    print("   Escribe 'salir' o 'exit' para terminar")
    print("-" * 60)
    print()

    # Loop de conversación
    while True:
        try:
            user_input = input("Tú: ").strip()

            if user_input.lower() in ['salir', 'exit', 'quit', 'adios']:
                print("\n ¡Hasta luego!")
                break

            if not user_input:
                continue

            print("\n Agente: ", end="", flush=True)
            response = run_agent(agent, user_input)
            print(response)
            print("\n" + "-" * 90 + "\n")

        except KeyboardInterrupt:
            print("\n\n Saliendo...")
            break
        except Exception as e:
            print(f"\n Error: {e}\n")


# ─── Entry point ──────────────────────────────────────────────
if __name__ == "__main__":
    if "--cli" in sys.argv:
        # Modo CLI interactivo
        main_cli()
    else:
        # Modo servidor Flask (desarrollo local)
        print("Iniciando servidor Flask en puerto 8080...")
        app.run(host='0.0.0.0', port=8080, debug=False)
