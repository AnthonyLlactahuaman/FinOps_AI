"""
Módulo RAG para consultas sobre la Ley 27287 peruana
"Reglas Generales Aplicables a los Títulos de Valores"

Usa LlamaIndex + Elasticsearch como vector store y OpenAI para generar respuestas.
Embeddings: OpenAI (text-embedding-3-small)
"""
import os
import logging
import nest_asyncio

# Permitir event loops anidados: LlamaIndex ElasticsearchStore usa
# internamente un cliente async (aiohttp), pero LangChain lo invoca
# desde un contexto sincrónico. Sin esto falla con:
# "Timeout context manager should be used inside a task"
nest_asyncio.apply()

logger = logging.getLogger(__name__)

_query_engine = None


def _get_query_engine():
    """
    Retorna (o crea) la instancia singleton del query engine de LlamaIndex
    conectado al índice de Elasticsearch con la Ley 27287.

    Solo recupera los 4 fragmentos más relevantes por consulta.
    """
    global _query_engine
    if _query_engine is not None:
        return _query_engine

    try:
        from llama_index.vector_stores.elasticsearch import ElasticsearchStore
        from llama_index.core import StorageContext, VectorStoreIndex
        from llama_index.embeddings.openai import OpenAIEmbedding
        from llama_index.llms.openai import OpenAI as LlamaOpenAI

        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError(
                "OPENAI_API_KEY no está configurada en las variables de entorno"
            )

        # El embed model debe ser el mismo que se usó al guardar
        embed_model = OpenAIEmbedding(model="text-embedding-3-small")

        # LLM para la respuesta: GPT-4.1 de OpenAI
        llm = LlamaOpenAI(
            model=os.getenv("LLM_MODEL", "gpt-4.1"),
            api_key=openai_api_key,
        )

        # Leer credenciales desde variables de entorno
        es_url      = os.getenv("ELASTICSEARCH_LEY27287_URL")
        es_user     = os.getenv("ELASTICSEARCH_LEY27287_USER")
        es_password = os.getenv("ELASTICSEARCH_LEY27287_PASSWORD")
        index_name  = os.getenv("ELASTICSEARCH_LEY27287_INDEX")

        # Reconectar al índice existente en Elasticsearch
        vector_store = ElasticsearchStore(
            es_url=es_url,
            es_user=es_user,
            es_password=es_password,
            index_name=index_name,
        )

        storage_context = StorageContext.from_defaults(vector_store=vector_store)

        # Crear índice en modo lectura
        index = VectorStoreIndex.from_vector_store(
            vector_store=vector_store,
            storage_context=storage_context,
            embed_model=embed_model,
        )

        # Crear el query engine usando GPT-4.1, limitado a 4 fragmentos
        _query_engine = index.as_query_engine(
            llm=llm,
            similarity_top_k=4,
        )

        logger.info("Query engine de la Ley 27287 inicializado correctamente.")
        return _query_engine

    except Exception as e:
        logger.error(f"Error al inicializar el query engine de la Ley 27287: {e}")
        raise


def query_ley_27287(pregunta: str) -> str:
    """
    Realiza una consulta RAG sobre la Ley 27287 peruana.

    Solo recupera los 4 fragmentos con mayor coincidencia semántica
    del vector store y genera la respuesta con GPT-4.1.
    """
    try:
        engine = _get_query_engine()
        response = engine.query(pregunta)
        return str(response.response)
    except Exception as e:
        logger.error(f"Error al consultar la Ley 27287: {e}")
        return f"Error al consultar la base vectorial de la Ley 27287: {str(e)}"
