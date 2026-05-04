import os
import requests
import json
from langchain_community.document_loaders import TextLoader, DirectoryLoader
import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from src.core.config import Config
from src.core.constants import VALID_DEPARTMENTS, RAG_CHUNK_SIZE, RAG_CHUNK_OVERLAP, RAG_DEFAULT_K
from src.core.exceptions import ProviderException

class LMStudioEmbeddings(Embeddings):
    """Implementación personalizada de embeddings para LM Studio para evitar errores de tipo de campo 'input'."""
    
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
                json={
                    "model": self.model,
                    "input": texts
                },
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

class RAGManager:
    """Gestiona la carga de documentos, creación de índices y recuperación para RAG."""
    
    def __init__(self):
        self.embeddings = None
        self.vectorstores = {}

    def _init_embeddings(self):
        if self.embeddings:
            return
            
        provider = Config.LLM_PROVIDER
        print(f"  [RAG] Inicializando embeddings ({provider})...")
        
        try:
            if provider == "openai":
                self.embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
            elif provider == "gemini" or provider == "google":
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

    def _get_vectorstore(self, department: str):
        """Crea o recupera un vectorstore persistente para un departamento específico."""
        if department in self.vectorstores:
            return self.vectorstores[department]
        
        self.db_path = os.path.join(Config.PERSISTENT_DIR, f"chroma_db_{department.lower()}")
        self._init_embeddings()
        
        # Mapeo de departamentos a rutas de documentos
        paths = {
            "RRHH": Config.DATA_PATH_RRHH,
            "TECNOLOGIA": Config.DATA_PATH_TECH,
            "FINANZAS": Config.DATA_PATH_FINANZAS,
            "RECLAMOS": Config.DATA_PATH_RECLAMOS,
            "GENERAL": Config.DATA_PATH_GENERAL,
            "SEGURIDAD": Config.DATA_PATH_SEGURIDAD
        }
        
        try:
            # Inicializamos el cliente de Chroma
            client = chromadb.PersistentClient(path=self.db_path)
            collection_name = f"{department.lower()}_knowledge"
            
            # Intentamos obtener la colección si ya existe y tiene documentos
            try:
                coll = client.get_collection(name=collection_name)
                if coll.count() > 0:
                    vectorstore = Chroma(
                        client=client,
                        collection_name=collection_name,
                        embedding_function=self.embeddings
                    )
                    self.vectorstores[department] = vectorstore
                    return vectorstore
            except Exception:
                # Si falla o no existe, procedemos a crearla
                pass

            # Si no existe o está vacía, cargamos documentos
            path = paths.get(department)
            if not path or not os.path.exists(path) or not os.listdir(path):
                print(f"WARNING: No hay documentos para {department} en {path}")
                return None
                
            loader = DirectoryLoader(path, glob="*.md", loader_cls=TextLoader)
            docs = loader.load()
            
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=RAG_CHUNK_SIZE, chunk_overlap=RAG_CHUNK_OVERLAP)
            splits = text_splitter.split_documents(docs)
            
            vectorstore = Chroma.from_documents(
                documents=splits, 
                embedding=self.embeddings,
                collection_name=collection_name,
                client=client
            )
            self.vectorstores[department] = vectorstore
            return vectorstore

        except Exception as e:
            print(f"  [RAG ERROR] Error en Chroma ({department}): {e}")
            raise ProviderException(f"Error al acceder a la base de datos de conocimientos ({department})", detail=str(e))

    def retrieve_context(self, query: str, department: str) -> str:
        """Busca información relevante en el vectorstore del departamento."""
        if department not in VALID_DEPARTMENTS:
            return ""
            
        vectorstore = self._get_vectorstore(department)
        if not vectorstore:
            return ""
            
        # Simulación de recuperación simple
        docs = vectorstore.similarity_search(query, k=RAG_DEFAULT_K)
        context = "\n\n".join([doc.page_content for doc in docs])
        return context
