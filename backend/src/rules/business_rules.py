"""
Módulo de reglas de negocio - Extracción mediante RAG con Elasticsearch
"""
import os
from typing import List, Optional
from langchain_openai import OpenAIEmbeddings
from langchain_elasticsearch import ElasticsearchStore


# ── Singleton: conexión al vector store ───────────────────────────────────
_vector_store: Optional[ElasticsearchStore] = None


def _get_vector_store() -> ElasticsearchStore:
    """
    Retorna (o crea) la instancia singleton del ElasticsearchStore.
    Las credenciales se leen de las variables de entorno.
    """
    global _vector_store
    if _vector_store is None:
        embeddings = OpenAIEmbeddings(
            model="text-embedding-3-large",
            openai_api_key=os.getenv("OPENAI_API_KEY"),
        )
        _vector_store = ElasticsearchStore(
            es_url=os.getenv("ELASTICSEARCH_URL"),
            es_user=os.getenv("ELASTICSEARCH_USER"),
            es_password=os.getenv("ELASTICSEARCH_PASSWORD"),
            index_name=os.getenv("ELASTICSEARCH_INDEX"),
            embedding=embeddings,
        )
    return _vector_store


# ── Funciones de búsqueda ──────────────────────────────────────────────────

def normalize_rule_id(raw_id: str) -> str:
    """
    Normaliza cualquier variante de ID de regla al formato canónico REGLA-NNN.

    Ejemplos:
        '1'          -> 'REGLA-001'
        '001'        -> 'REGLA-001'
        '12'         -> 'REGLA-012'
        'regla-1'    -> 'REGLA-001'
        'REGLA-001'  -> 'REGLA-001'
        'regla 2'    -> 'REGLA-002'
    """
    import re
    cleaned = raw_id.strip().upper()

    # Extraer el número, soportando "REGLA-NNN", "REGLA NNN" o solo dígitos
    match = re.search(r"(\d+)", cleaned)
    if match:
        number = int(match.group(1))
        return f"REGLA-{number:03d}"

    # Si no se encontró número, devolver tal cual
    return cleaned


def search_rules_by_query(query: str, k: int = 4) -> List[dict]:
    """
    Búsqueda semántica de reglas mediante similitud de embeddings.

    Args:
        query: Texto libre para buscar reglas relevantes.
        k: Número máximo de documentos a retornar.

    Returns:
        Lista de diccionarios con 'content' y 'metadata' de cada regla.
    """
    vs = _get_vector_store()
    docs = vs.similarity_search(query, k=k)
    return [
        {"content": doc.page_content, "metadata": doc.metadata}
        for doc in docs
    ]


def search_rules_by_id(rule_id: str, k: int = 4) -> List[dict]:
    """
    Busca reglas cuyo metadata.regla_id coincida con el valor proporcionado.
    Normaliza el input del usuario al formato REGLA-NNN antes de buscar.

    Args:
        rule_id: Identificador de la regla (ej: '1', '001', 'REGLA-001').
        k: Número máximo de documentos a retornar.

    Returns:
        Lista de diccionarios con 'content' y 'metadata'.
    """
    vs = _get_vector_store()
    normalized_id = normalize_rule_id(rule_id)

    # Intentar con filtro de metadata
    try:
        docs = vs.similarity_search(
            query=normalized_id,
            k=k,
            filter=[{"term": {"metadata.regla_id.keyword": normalized_id}}],
        )
    except Exception:
        # Fallback: búsqueda semántica pura con el ID como texto
        docs = vs.similarity_search(query=normalized_id, k=k)

    return [
        {"content": doc.page_content, "metadata": doc.metadata}
        for doc in docs
    ]


def search_rules_by_name(name: str, k: int = 4) -> List[dict]:
    """
    Busca reglas por nombre (metadata.nombre).

    Args:
        name: Nombre (o parte del nombre) de la regla.
        k: Número máximo de documentos a retornar.

    Returns:
        Lista de diccionarios con 'content' y 'metadata'.
    """
    vs = _get_vector_store()

    try:
        docs = vs.similarity_search(
            query=name,
            k=k,
            filter=[{"match": {"metadata.nombre": name}}],
        )
    except Exception:
        docs = vs.similarity_search(query=name, k=k)

    return [
        {"content": doc.page_content, "metadata": doc.metadata}
        for doc in docs
    ]


# ── Formateador de resultados ──────────────────────────────────────────────

def format_rules_results(results: List[dict], header: str = "") -> str:
    """
    Formatea una lista de resultados de reglas para lectura del agente.

    Args:
        results: Lista de diccionarios con 'content' y 'metadata'.
        header: Encabezado opcional.

    Returns:
        Texto formateado con las reglas encontradas.
    """
    if not results:
        return "No se encontraron reglas con los criterios proporcionados."

    lines = []
    if header:
        lines.append(f"=== {header} ===\n")

    for i, rule in enumerate(results, 1):
        meta = rule.get("metadata", {})
        lines.append(f"--- Regla #{i} ---")
        if meta.get("regla_id"):
            lines.append(f"ID: {meta['regla_id']}")
        if meta.get("nombre"):
            lines.append(f"Nombre: {meta['nombre']}")
        if meta.get("severidad"):
            lines.append(f"Severidad: {meta['severidad']}")
        if meta.get("fuente"):
            lines.append(f"Fuente: {meta['fuente']}")
        lines.append(f"Contenido:\n{rule['content']}")
        lines.append("")  # línea separadora

    return "\n".join(lines)


# ── Retriever como herramienta (para uso directo en el agente) ─────────────

def get_rules_retriever_tool():
    """
    Retorna un retriever de LangChain convertido en tool, listo para
    registrarse en el agente.

    Ejemplo de uso:
        tool = get_rules_retriever_tool()
        # añadir a la lista de tools del agente
    """
    vs = _get_vector_store()
    retriever_chain = vs.as_retriever(search_kwargs={"k": 4})

    tool = retriever_chain.as_tool(
        name="extraccion_reglas",
        description=(
            "Busca y extrae reglas de negocio de FinOps almacenadas en una "
            "base de datos vectorial. Recibe una consulta en texto libre y "
            "retorna las reglas más relevantes según similitud semántica. "
            "Útil para interpretar desviaciones presupuestarias, conocer "
            "umbrales de alerta, acciones requeridas y excepciones."
        ),
    )
    return tool
