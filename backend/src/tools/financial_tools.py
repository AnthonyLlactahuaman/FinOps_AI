"""
Herramientas de análisis financiero para el Agente AI de FinOps
"""
from typing import Annotated, Optional
from langchain_core.tools import tool
from langchain.chat_models import init_chat_model
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import json
from src.data.financial_data import (
    get_top_variances,
    get_expense_trend,
    analyze_with_filters
)
from src.rules.business_rules import (
    search_rules_by_query,
    search_rules_by_id,
    search_rules_by_name,
    format_rules_results,
    get_rules_retriever_tool,
)
from src.agent.prompts import FILTER_EXTRACTION_PROMPT


def parse_filter_string(filter_str: str) -> dict:
    """
    Parsea el string de filtros devuelto por el LLM
    """
    filters = {
        "gerencia": None,
        "pais": None,
        "centro_costo": None,
        "id_value": None,
        "periodo": None
    }
    
    try:
        # Limpiar y parsear
        filter_str = filter_str.strip()
        parts = filter_str.split(",")
        
        for part in parts:
            if ":" in part:
                key, value = part.split(":", 1)
                key = key.strip().upper()
                value = value.strip()
                
                if value:  # Solo si hay valor
                    if key == "GERENCIA":
                        filters["gerencia"] = value
                    elif key == "PAIS":
                        filters["pais"] = value
                    elif key == "CECO":
                        filters["centro_costo"] = value
                    elif key == "ID":
                        filters["id_value"] = value
                    elif key == "PERIODO":
                        # Soportar múltiples periodos: "1|2|3"
                        periodos = []
                        for p in value.split("|"):
                            p = p.strip()
                            if p.isdigit() and 1 <= int(p) <= 12:
                                periodos.append(int(p))
                        filters["periodo"] = periodos if periodos else None
    except Exception:
        pass
    
    return filters


@tool
def extract_filters(
    user_query: Annotated[str, "Pregunta del usuario sobre datos financieros"]
) -> str:
    """
    Extrae los filtros de la pregunta del usuario usando un LLM.

    Esta herramienta analiza la pregunta del usuario e identifica qué filtros
    quiere aplicar (GERENCIA, PAIS, CECO, ID, PERIODO).

    Usa esta herramienta PRIMERO para identificar los filtros antes de 
    llamar a analyze_financial_data.
    """
    try:
        # Crear el prompt
        prompt = ChatPromptTemplate.from_template(FILTER_EXTRACTION_PROMPT)
        
        # Crear LLM
        llm = init_chat_model("gpt-4.1", model_provider="openai")
        
        # Crear cadena
        chain = prompt | llm | StrOutputParser()
        
        # Ejecutar
        result = chain.invoke({
            "user_query": user_query
        })
        
        return result.strip()
    except Exception as e:
        return f"Error al extraer filtros: {str(e)}"


@tool
def budget_vs_actual(
    filter_string: Annotated[str, "String de filtros en formato 'GERENCIA:valor,PAIS:valor,CECO:valor,ID:valor,PERIODO:valor_o_valores' (PERIODO puede ser uno o varios separados por |, ej: 1|2|3)"]
) -> str:
    """
    Analiza datos financieros aplicando los filtros especificados.
    
    Recibe los filtros extraídos por extract_filters y calcula:
    - Presupuesto total (PB)
    - Gasto real total (REAL)
    - Varianza (diferencia entre REAL y PB)
    - Porcentaje de desviación
    - Severidad según umbrales (50%, 30%, 10%)
    """
    try:
        # Parsear filtros
        filters = parse_filter_string(filter_string)
        
        # Aplicar análisis
        result = analyze_with_filters(**filters)
        
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({
            "error": True,
            "mensaje": f"Error al analizar datos: {str(e)}"
        }, ensure_ascii=False)


@tool
def top_budget_variances(
    filter_string: Annotated[str, "String de filtros en formato 'GERENCIA:valor,PAIS:valor,CECO:valor,ID:valor,PERIODO:valor_o_valores' (PERIODO puede ser uno o varios separados por |, ej: 1|2|3; usar extract_filters primero)"],
    top_n: Annotated[int, "Número de IDs con mayores desviaciones a retornar"] = 5,
    threshold_percent: Annotated[Optional[float], "Umbral mínimo de desviación porcentual para incluir (ej: 10.0 para 10%)"] = None
) -> str:
    """
    Identifica los N IDs con mayores desviaciones presupuestarias.
    
    Recibe los filtros de extract_filters y aplica filtros de GERENCIA, PAIS, CECO y PERIODO.
    El filtro de ID se ignora ya que el objetivo es descubrir cuáles IDs tienen más varianza.
    Las desviaciones se ordenan por valor absoluto del porcentaje de varianza.
    """
    try:
        # Parsear filtros
        filters = parse_filter_string(filter_string)
        
        # Excluir id_value ya que get_top_variances no filtra por ID
        filters.pop("id_value", None)
        
        # Obtener top varianzas con filtros
        result = get_top_variances(
            top_n=top_n, 
            threshold=threshold_percent,
            **filters
        )
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({
            "error": True,
            "mensaje": f"Error al obtener top varianzas: {str(e)}"
        }, ensure_ascii=False)


@tool
def analyze_expense_trend(
    filter_string: Annotated[str, "String de filtros en formato 'GERENCIA:valor,PAIS:valor,CECO:valor,ID:valor,PERIODO:valor_o_valores' (usar extract_filters primero)"]
) -> str:
    """
    Analiza la tendencia de gastos aplicando los filtros extraídos.
    
    Recibe los filtros de extract_filters y analiza la tendencia de gastos REALES.
    Si el usuario indica un solo periodo, se analiza desde ese mes hasta 3 meses después.
    Si indica varios periodos, se analizan exactamente esos meses.
    
    Esta herramienta:
    - Muestra el gasto real (REAL) mes a mes
    - Calcula el cambio porcentual entre meses consecutivos
    - Identifica la tendencia general (aumentando/disminuyendo/estable)
    - Detecta volatilidad excesiva (cambios > 30%)
    """
    try:
        # Parsear filtros
        filters = parse_filter_string(filter_string)
        
        # Excluir id_value ya que no aplica para tendencia
        filters.pop("id_value", None)
        
        result = get_expense_trend(**filters)
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({
            "error": True,
            "mensaje": f"Error al analizar tendencia: {str(e)}"
        }, ensure_ascii=False)


# ── Herramientas RAG de reglas de negocio ──────────────────────────────────

@tool
def get_business_rules(
    query: Annotated[str, "Consulta en texto libre para buscar reglas de negocio relevantes (ej: 'sobregasto', 'desviación presupuestaria', 'tendencia de gastos')"]
) -> str:
    """
    Busca reglas de negocio mediante RAG (búsqueda semántica).
    
    Usa esta herramienta para encontrar reglas relevantes a partir de un
    tema o situación financiera descrita en texto libre.
    
    Usa esta herramienta cuando:
    - Necesites interpretar si una desviación requiere acción
    - Quieras conocer los umbrales de alerta
    - Necesites entender las acciones requeridas ante una situación
    - Quieras evaluar tendencias y volatilidad
    """
    try:
        results = search_rules_by_query(query, k=4)
        return format_rules_results(
            results,
            header=f"Reglas de Negocio Relevantes para: '{query}'"
        )
    except Exception as e:
        return f"Error al consultar reglas: {str(e)}"


@tool
def get_rule_by_id(
    rule_id: Annotated[str, "ID de la regla a buscar. Acepta variantes: '1', '001', 'REGLA-001', 'regla 1'"]
) -> str:
    """
    Busca una regla de negocio específica por su ID.
    
    Usa esta herramienta cuando el usuario solicite una regla puntual
    identificada por su código. El ID se normaliza automáticamente al
    formato REGLA-NNN (ej: '1' -> 'REGLA-001', '001' -> 'REGLA-001').
    """
    try:
        from src.rules.business_rules import normalize_rule_id
        normalized = normalize_rule_id(rule_id)
        results = search_rules_by_id(rule_id, k=2)
        return format_rules_results(
            results,
            header=f"Regla de Negocio: {normalized}"
        )
    except Exception as e:
        return f"Error al buscar regla {rule_id}: {str(e)}"



@tool
def get_rules_by_name(
    name: Annotated[str, "Nombre o parte del nombre de la regla a buscar (ej: 'Alerta Crítica', 'Sobregasto')"]
) -> str:
    """
    Busca reglas de negocio por nombre.
    
    Usa esta herramienta para encontrar reglas cuyo nombre coincida
    o contenga el texto proporcionado.
    """
    try:
        results = search_rules_by_name(name, k=4)
        return format_rules_results(
            results,
            header=f"Reglas de Negocio con Nombre: '{name}'"
        )
    except Exception as e:
        return f"Error al buscar reglas por nombre: {str(e)}"


@tool
def get_data_dictionary() -> str:
    """
    Consulta el diccionario de datos que describe la estructura del archivo financials.xlsx.
    
    Esta herramienta proporciona información detallada sobre:
    - Todas las columnas disponibles en los datos financieros
    - Tipos de datos de cada columna
    - Descripción y ejemplos de cada campo
    - Valores válidos para campos categóricos
    """
    try:
        with open("data/data_dictionary.txt", 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return "Error: No se encontró el archivo del diccionario de datos"
    except Exception as e:
        return f"Error al leer diccionario de datos: {str(e)}"


# ── Herramienta RAG - Ley 27287 peruana (Títulos de Valores) ──────────────

@tool
def query_ley_27287(
    pregunta: Annotated[str, "Pregunta sobre la Ley 27287 peruana relativa a Reglas Generales Aplicables a los Títulos de Valores"]
) -> str:
    """
    Consulta la base vectorial con el contenido de la Ley 27287 peruana,
    que trata sobre 'Reglas Generales Aplicables a los Títulos de Valores'.

    USA ESTA HERRAMIENTA EXCLUSIVAMENTE cuando el usuario haga preguntas
    relacionadas con:
    - La Ley 27287
    - Títulos de valores peruanos (letras de cambio, pagarés, cheques, etc.)
    - Reglas generales de títulos de valores en el marco legal peruano
    - Artículos, requisitos o disposiciones de la Ley 27287

    La respuesta es generada por OpenAI con base en el contenido real de la ley,
    recuperado mediante búsqueda semántica en Elasticsearch.
    """
    try:
        from src.legal.legal_rag import query_ley_27287 as _query
        return _query(pregunta)
    except Exception as e:
        return f"Error al consultar la Ley 27287: {str(e)}"
