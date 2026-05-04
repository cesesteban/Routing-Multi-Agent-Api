import os
import requests
import json
from typing import List
from langchain_community.document_loaders import TextLoader, DirectoryLoader, PyPDFLoader
import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_community.retrievers import BM25Retriever
from langchain_core.embeddings import Embeddings
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from src.core.config import Config
from src.core.constants import VALID_DEPARTMENTS, RAG_CHUNK_SIZE, RAG_CHUNK_OVERLAP, RAG_DEFAULT_K
from src.core.exceptions import ProviderException


class LMStudioEmbeddings(Embeddings):
    """Implementación personalizada de embeddings para LM Studio."""

    def __init__(self, model: str, base_url: str):
        self.model = model
        self.base_url = base_url.rstrip('/')
        if not self.base_url.endswith('/embeddings'):
            self.base_url = f"{self.base_url}/embeddings"

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Genera embeddings para una lista de textos."""
        try:
            response = requests.post(
                self.base_url,
                json={"model": self.model, "input": texts},
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            return [record["embedding"] for record in data["data"]]
        except Exception as e:
            raise ProviderException(f"Error al generar embeddings en LM Studio: {e}")

    def embed_query(self, text: str) -> list[float]:
        """Genera embedding para una única consulta."""
        return self.embed_documents([text])[0]


class HybridRetriever:
    """
    Retriever híbrido que combina búsqueda vectorial (semántica) y BM25 (léxica)
    implementado directamente sin depender de langchain.retrievers.EnsembleRetriever.
    Usa Reciprocal Rank Fusion (RRF) para fusionar los resultados.
    """

    def __init__(self, vectorstore: Chroma, bm25_retriever: BM25Retriever, k: int = RAG_DEFAULT_K, weights: tuple = (0.7, 0.3)):
        self.vectorstore = vectorstore
        self.bm25_retriever = bm25_retriever
        self.k = k
        self.w_vector, self.w_bm25 = weights

    def invoke(self, query: str) -> List[Document]:
        """Ejecuta búsqueda híbrida y devuelve los documentos más relevantes."""
        # 1. Búsqueda semántica (vectorial)
        vector_docs = self.vectorstore.similarity_search(query, k=self.k * 2)

        # 2. Búsqueda léxica (BM25)
        self.bm25_retriever.k = self.k * 2
        bm25_docs = self.bm25_retriever.invoke(query)

        # 3. Fusión por Reciprocal Rank Fusion (RRF)
        scores: dict[str, float] = {}
        doc_map: dict[str, Document] = {}

        for rank, doc in enumerate(vector_docs):
            key = doc.page_content[:200]
            scores[key] = scores.get(key, 0) + self.w_vector * (1 / (rank + 1))
            doc_map[key] = doc

        for rank, doc in enumerate(bm25_docs):
            key = doc.page_content[:200]
            scores[key] = scores.get(key, 0) + self.w_bm25 * (1 / (rank + 1))
            doc_map[key] = doc

        # 4. Ordenar por score y retornar top-k
        sorted_keys = sorted(scores, key=lambda k: scores[k], reverse=True)
        return [doc_map[key] for key in sorted_keys[:self.k]]


class RAGManager:
    """Gestiona la carga de documentos, creación de índices y recuperación para RAG."""

    def __init__(self):
        self.embeddings = None
        self.vectorstores = {}
        self.retrievers = {}  # Almacena HybridRetrievers por departamento

    def _init_embeddings(self):
        if self.embeddings:
            return

        provider = Config.LLM_PROVIDER
        print(f"  [RAG] Inicializando embeddings ({provider})...")

        try:
            if provider == "openai":
                self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
            elif provider in ("gemini", "google"):
                self.embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
            elif provider == "lm_studio":
                self.embeddings = LMStudioEmbeddings(
                    model=Config.MODEL_NAME,
                    base_url=Config.LM_STUDIO_BASE_URL
                )
            else:
                raise ProviderException(f"El proveedor '{provider}' no soporta embeddings nativos en esta configuración.")
        except Exception as e:
            if isinstance(e, ProviderException):
                raise e
            print(f"  [RAG ERROR] Error crítico inicializando embeddings: {e}")
            raise ProviderException(f"Error al conectar con el proveedor {provider}", detail=str(e))

    def _get_hybrid_retriever(self, department: str) -> HybridRetriever | None:
        """Crea o recupera un HybridRetriever para un departamento específico."""
        if department in self.retrievers:
            return self.retrievers[department]

        db_path = os.path.join(Config.PERSISTENT_DIR, f"chroma_db_{department.lower()}")
        self._init_embeddings()

        paths = {
            "RRHH": Config.DATA_PATH_RRHH,
            "TECNOLOGIA": Config.DATA_PATH_TECH,
            "FINANZAS": Config.DATA_PATH_FINANZAS,
            "RECLAMOS": Config.DATA_PATH_RECLAMOS,
            "GENERAL": Config.DATA_PATH_GENERAL,
            "SEGURIDAD": Config.DATA_PATH_SEGURIDAD
        }

        try:
            path = paths.get(department)
            if not path or not os.path.exists(path) or not os.listdir(path):
                print(f"WARNING: No hay documentos para {department} en {path}")
                return None

            # 1. Cargar documentos de múltiples formatos
            all_docs = []
            loaders = [
                DirectoryLoader(path, glob="*.md", loader_cls=TextLoader),
                DirectoryLoader(path, glob="*.txt", loader_cls=TextLoader),
                DirectoryLoader(path, glob="*.pdf", loader_cls=PyPDFLoader)
            ]

            for loader in loaders:
                try:
                    all_docs.extend(loader.load())
                except Exception as e:
                    print(f"  [RAG Loader] Error cargando algunos archivos: {e}")

            if not all_docs:
                return None

            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=RAG_CHUNK_SIZE,
                chunk_overlap=RAG_CHUNK_OVERLAP
            )
            splits = text_splitter.split_documents(all_docs)

            # 2. Inicializar Vectorstore (Chroma)
            client = chromadb.PersistentClient(path=db_path)
            collection_name = f"{department.lower()}_knowledge"
            vectorstore = Chroma(
                client=client,
                collection_name=collection_name,
                embedding_function=self.embeddings
            )

            if vectorstore._collection.count() == 0:
                vectorstore.add_documents(splits)

            self.vectorstores[department] = vectorstore

            # 3. Inicializar BM25 Retriever (léxico)
            bm25_retriever = BM25Retriever.from_documents(splits)

            # 4. Crear Hybrid Retriever (RRF: 70% semántico, 30% léxico)
            hybrid_retriever = HybridRetriever(
                vectorstore=vectorstore,
                bm25_retriever=bm25_retriever,
                k=RAG_DEFAULT_K,
                weights=(0.7, 0.3)
            )

            self.retrievers[department] = hybrid_retriever
            return hybrid_retriever

        except Exception as e:
            print(f"  [RAG ERROR] Error en Híbrido ({department}): {e}")
            raise ProviderException(f"Error al acceder al sistema RAG híbrido ({department})", detail=str(e))

    def retrieve_context(self, query: str, department: str) -> str:
        """Busca información relevante usando búsqueda híbrida (RRF)."""
        if department not in VALID_DEPARTMENTS:
            return ""

        retriever = self._get_hybrid_retriever(department)
        if not retriever:
            return ""

        docs = retriever.invoke(query)
        context = "\n\n".join([doc.page_content for doc in docs])
        return context
