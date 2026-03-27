"""
Creación y configuración del Agente AI de FinOps
"""
import os
from typing import Optional
from langchain.chat_models import init_chat_model
from langchain.agents import create_agent
from src.tools.financial_tools import (
    budget_vs_actual,
    top_budget_variances,
    analyze_expense_trend,
    get_business_rules,
    get_rule_by_id,
    get_rules_by_name,
    get_data_dictionary,
    extract_filters,
    query_ley_27287,
)
from src.memory.conversation_memory import get_memory
from src.agent.prompts import SYSTEM_PROMPT


def create_finops_agent(api_key: Optional[str] = None, model: str = "gpt-4.1"):
    """
    Crea el agente de FinOps con todas las herramientas configuradas
    """
    # Configurar API key
    if api_key:
        os.environ["OPENAI_API_KEY"] = api_key
    elif "OPENAI_API_KEY" not in os.environ:
        raise ValueError("Se requiere OPENAI_API_KEY en variables de entorno o como parámetro")
    
    # Inicializar modelo usando init_chat_model
    llm = init_chat_model(model, model_provider="openai")
    
    # Crear memoria
    memory = get_memory()
    
    # Registrar todas las herramientas
    tools = [
        extract_filters,
        budget_vs_actual,
        top_budget_variances,
        analyze_expense_trend,
        get_business_rules,
        get_rule_by_id,
        get_rules_by_name,
        get_data_dictionary,
        query_ley_27287,
    ]
    
    # Crear agente usando el patrón correcto
    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
        checkpointer=memory
    )
    
    return agent


def run_agent(agent, query: str, thread_id: str = "default") -> str:
    """
    Ejecuta una consulta en el agente
    
    Args:
        agent: Instancia del agente
        query: Pregunta o solicitud del usuario
        thread_id: ID del hilo de conversación para mantener contexto
    """
    try:
        # Configurar el thread para mantener contexto conversacional
        config = {"configurable": {"thread_id": thread_id}}
        
        # Invocar el agente
        response = agent.invoke({"messages": [("human", query)]}, config)
        
        # Extraer el mensaje de respuesta
        if "messages" in response and len(response["messages"]) > 0:
            last_message = response["messages"][-1]
            return last_message.content if hasattr(last_message, 'content') else str(last_message)
        
        return "No se generó respuesta"
    except Exception as e:
        return f"Error al procesar la consulta: {str(e)}"
