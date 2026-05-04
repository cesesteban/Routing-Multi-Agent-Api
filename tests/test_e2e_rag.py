"""
E2E Tests — Hybrid RAG Feature

Tests:
  - HybridRetriever combines vector + BM25 results correctly
  - RRF score fusion: higher-ranked documents get higher scores
  - Results are deduplicated
  - Returns top-K documents
  - Returns empty list gracefully when no documents match
  - RAGManager.retrieve_context returns a string (not None)
  - Invalid department returns empty string (no crash)
"""
import pytest
import os
import sys

os.environ.setdefault("DRY_RUN", "true")

from unittest.mock import MagicMock, patch
from langchain_core.documents import Document
from src.services.ai.rag_service import HybridRetriever, RAGManager
from src.core.constants import VALID_DEPARTMENTS


# ── Helper: build mock documents ──────────────────────────────────────────────

def make_docs(texts: list[str]) -> list[Document]:
    return [Document(page_content=t, metadata={}) for t in texts]


# ── Unit: HybridRetriever (RRF fusion logic) ───────────────────────────────────

def test_hybrid_retriever_returns_top_k():
    """HybridRetriever should return at most K results."""
    k = 3
    vector_docs = make_docs([f"doc vector {i}" for i in range(10)])
    bm25_docs = make_docs([f"doc bm25 {i}" for i in range(10)])

    mock_vectorstore = MagicMock()
    mock_vectorstore.similarity_search.return_value = vector_docs

    mock_bm25 = MagicMock()
    mock_bm25.invoke.return_value = bm25_docs
    mock_bm25.k = k * 2

    retriever = HybridRetriever(mock_vectorstore, mock_bm25, k=k)
    results = retriever.invoke("query de prueba")

    assert len(results) <= k


def test_hybrid_retriever_merges_unique_docs():
    """HybridRetriever should deduplicate documents appearing in both sources."""
    shared_text = "Documento compartido entre vector y BM25"
    vector_docs = make_docs([shared_text, "Exclusivo vector"])
    bm25_docs = make_docs([shared_text, "Exclusivo BM25"])

    mock_vectorstore = MagicMock()
    mock_vectorstore.similarity_search.return_value = vector_docs

    mock_bm25 = MagicMock()
    mock_bm25.invoke.return_value = bm25_docs
    mock_bm25.k = 4

    retriever = HybridRetriever(mock_vectorstore, mock_bm25, k=5)
    results = retriever.invoke("query")

    # Deduplicated: 3 unique docs, not 4
    contents = [d.page_content for d in results]
    assert len(contents) == len(set(contents)), "Results should not contain duplicates"


def test_hybrid_retriever_higher_score_for_top_ranked():
    """Docs ranked first in both sources should appear before lower-ranked ones."""
    vector_docs = make_docs(["Top doc", "Middle doc", "Low doc"])
    bm25_docs = make_docs(["Top doc", "Other doc"])

    mock_vectorstore = MagicMock()
    mock_vectorstore.similarity_search.return_value = vector_docs

    mock_bm25 = MagicMock()
    mock_bm25.invoke.return_value = bm25_docs
    mock_bm25.k = 4

    retriever = HybridRetriever(mock_vectorstore, mock_bm25, k=3)
    results = retriever.invoke("query")

    # "Top doc" should be first (appears rank 1 in both sources)
    assert results[0].page_content == "Top doc"


def test_hybrid_retriever_handles_empty_results():
    """HybridRetriever should return empty list when both sources return nothing."""
    mock_vectorstore = MagicMock()
    mock_vectorstore.similarity_search.return_value = []

    mock_bm25 = MagicMock()
    mock_bm25.invoke.return_value = []
    mock_bm25.k = 0

    retriever = HybridRetriever(mock_vectorstore, mock_bm25, k=5)
    results = retriever.invoke("query vacía")
    assert results == []


def test_hybrid_retriever_respects_weights():
    """Vector weight 0.7 means vector-exclusive docs rank above BM25-exclusive ones."""
    vector_only = make_docs(["Solo en vector"])
    bm25_only = make_docs(["Solo en BM25"])

    mock_vectorstore = MagicMock()
    mock_vectorstore.similarity_search.return_value = vector_only

    mock_bm25 = MagicMock()
    mock_bm25.invoke.return_value = bm25_only
    mock_bm25.k = 2

    # w_vector=0.7 > w_bm25=0.3
    retriever = HybridRetriever(mock_vectorstore, mock_bm25, k=2, weights=(0.7, 0.3))
    results = retriever.invoke("query")

    assert results[0].page_content == "Solo en vector"


# ── Unit: RAGManager.retrieve_context ─────────────────────────────────────────

def test_rag_manager_invalid_department_returns_empty():
    """An invalid department should return empty string without crashing."""
    rag = RAGManager()
    result = rag.retrieve_context("¿Qué beneficios tengo?", "DEPARTAMENTO_INVALIDO")
    assert result == ""


def test_rag_manager_returns_string_type():
    """retrieve_context must always return a string, never None."""
    rag = RAGManager()

    with patch.object(rag, "_get_hybrid_retriever", return_value=None):
        result = rag.retrieve_context("consulta", "RRHH")
    assert isinstance(result, str)


def test_rag_manager_concatenates_doc_content():
    """retrieve_context should join all retrieved document contents."""
    rag = RAGManager()
    mock_retriever = MagicMock()
    mock_retriever.invoke.return_value = make_docs(["Parte 1", "Parte 2", "Parte 3"])

    with patch.object(rag, "_get_hybrid_retriever", return_value=mock_retriever):
        result = rag.retrieve_context("consulta", "RRHH")

    assert "Parte 1" in result
    assert "Parte 2" in result
    assert "Parte 3" in result


@pytest.mark.parametrize("department", VALID_DEPARTMENTS)
def test_rag_manager_all_valid_departments_dont_crash(department: str):
    """All valid departments should be handled without crashing (no documents = empty string)."""
    rag = RAGManager()
    with patch.object(rag, "_get_hybrid_retriever", return_value=None):
        result = rag.retrieve_context("test", department)
    assert result == ""
