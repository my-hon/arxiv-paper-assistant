"""VectorStore的单元测试，ChromaDB与embedding模型均使用替身。"""

import json
from unittest.mock import MagicMock

import pytest

from src.modules.knowledge import vector_store as vector_store_module
from src.modules.knowledge.vector_store import VectorStore


@pytest.fixture
def store():
    """返回一个已注入mock集合的VectorStore。"""
    store = VectorStore()
    store.paper_collection = MagicMock()
    return store


@pytest.fixture
def chroma_mocks(monkeypatch):
    """替换chromadb客户端和embedding函数，返回可断言的mock。"""
    collection = MagicMock(name="collection")
    persistent_client = MagicMock(name="persistent_client")
    persistent_client.get_or_create_collection.return_value = collection
    http_client = MagicMock(name="http_client")
    http_client.get_or_create_collection.return_value = collection

    persistent_factory = MagicMock(return_value=persistent_client)
    http_factory = MagicMock(return_value=http_client)
    monkeypatch.setattr(
        vector_store_module.chromadb, "PersistentClient", persistent_factory
    )
    monkeypatch.setattr(vector_store_module.chromadb, "HttpClient", http_factory)
    monkeypatch.setattr(
        vector_store_module.embedding_functions,
        "SentenceTransformerEmbeddingFunction",
        MagicMock(return_value="embedding-fn"),
    )
    return {
        "collection": collection,
        "persistent_factory": persistent_factory,
        "http_factory": http_factory,
    }


class TestInitialize:
    @pytest.mark.asyncio
    async def test_uses_local_persistent_client_by_default(
        self, chroma_mocks, monkeypatch, tmp_path
    ):
        monkeypatch.setattr(vector_store_module.settings, "CHROMA_DB_HOST", None)
        monkeypatch.setattr(vector_store_module.settings, "CHROMA_DB_PORT", None)
        monkeypatch.setattr(
            vector_store_module.settings, "CHROMA_DB_PATH", str(tmp_path)
        )
        store = VectorStore()

        await store.initialize()

        chroma_mocks["persistent_factory"].assert_called_once()
        chroma_mocks["http_factory"].assert_not_called()
        assert store.paper_collection is chroma_mocks["collection"]
        assert store.embedding_function == "embedding-fn"

    @pytest.mark.asyncio
    async def test_uses_http_client_when_host_configured(
        self, chroma_mocks, monkeypatch
    ):
        monkeypatch.setattr(vector_store_module.settings, "CHROMA_DB_HOST", "chroma")
        monkeypatch.setattr(vector_store_module.settings, "CHROMA_DB_PORT", 8000)
        store = VectorStore()

        await store.initialize()

        chroma_mocks["http_factory"].assert_called_once()
        assert chroma_mocks["http_factory"].call_args.kwargs["host"] == "chroma"
        assert chroma_mocks["http_factory"].call_args.kwargs["port"] == 8000

    @pytest.mark.asyncio
    async def test_raises_when_client_creation_fails(self, chroma_mocks, monkeypatch):
        monkeypatch.setattr(vector_store_module.settings, "CHROMA_DB_HOST", None)
        chroma_mocks["persistent_factory"].side_effect = RuntimeError("boom")
        store = VectorStore()

        with pytest.raises(RuntimeError):
            await store.initialize()


class TestAddPaperToIndex:
    @pytest.mark.asyncio
    async def test_returns_false_when_not_initialized(self):
        assert await VectorStore().add_paper_to_index("arxiv_1") is False

    @pytest.mark.asyncio
    async def test_returns_false_when_paper_missing(self, store, patch_get_db):
        patch_get_db(vector_store_module)

        assert await store.add_paper_to_index("missing") is False

    @pytest.mark.asyncio
    async def test_returns_true_when_already_indexed(
        self, store, patch_get_db, sample_paper
    ):
        patch_get_db(vector_store_module)
        store.paper_collection.get.return_value = {"ids": [sample_paper.paper_id]}

        assert await store.add_paper_to_index(sample_paper.paper_id) is True
        store.paper_collection.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_indexes_paper_with_interpretation_content(
        self, store, patch_get_db, sample_interpretation, sample_paper
    ):
        patch_get_db(vector_store_module)
        store.paper_collection.get.return_value = {"ids": []}

        assert await store.add_paper_to_index(sample_paper.paper_id) is True

        kwargs = store.paper_collection.add.call_args.kwargs
        assert kwargs["ids"] == [sample_paper.paper_id]
        document = kwargs["documents"][0]
        assert sample_paper.title in document
        assert "核心贡献: 提出Transformer" in document
        metadata = kwargs["metadatas"][0]
        assert json.loads(metadata["authors"]) == sample_paper.authors
        assert metadata["publication_date"].startswith("2017-06-12")
        assert metadata["citation_count"] == 100

    @pytest.mark.asyncio
    async def test_returns_false_when_add_fails(
        self, store, patch_get_db, sample_paper
    ):
        patch_get_db(vector_store_module)
        store.paper_collection.get.return_value = {"ids": []}
        store.paper_collection.add.side_effect = RuntimeError("chroma down")

        assert await store.add_paper_to_index(sample_paper.paper_id) is False


class TestSearchPapers:
    @pytest.mark.asyncio
    async def test_returns_empty_when_not_initialized(self):
        assert await VectorStore().search_papers("query") == []

    @pytest.mark.asyncio
    async def test_maps_results_and_computes_similarity(self, store):
        store.paper_collection.query.return_value = {
            "ids": [["arxiv_1"]],
            "metadatas": [
                [
                    {
                        "title": "P1",
                        "authors": json.dumps(["A"]),
                        "source": "arxiv",
                        "publication_date": "2017-06-12",
                        "categories": json.dumps(["cs.CL"]),
                        "citation_count": 3,
                        "status": "new",
                    }
                ]
            ],
            "distances": [[1.0]],
            "documents": [["a" * 400]],
        }

        papers = await store.search_papers("attention", limit=5, filter_conditions={"source": "arxiv"})

        assert len(papers) == 1
        assert papers[0]["paper_id"] == "arxiv_1"
        assert papers[0]["similarity"] == 0.5
        assert papers[0]["snippet"].endswith("...")
        assert len(papers[0]["snippet"]) == 303
        assert store.paper_collection.query.call_args.kwargs["n_results"] == 5
        assert store.paper_collection.query.call_args.kwargs["where"] == {"source": "arxiv"}

    @pytest.mark.asyncio
    async def test_returns_empty_on_query_error(self, store):
        store.paper_collection.query.side_effect = RuntimeError("boom")

        assert await store.search_papers("attention") == []


class TestGetSimilarPapers:
    @pytest.mark.asyncio
    async def test_returns_empty_when_not_initialized(self):
        assert await VectorStore().get_similar_papers("arxiv_1") == []

    @pytest.mark.asyncio
    async def test_returns_empty_when_paper_not_indexed(self, store):
        store.paper_collection.get.return_value = {"embeddings": []}

        assert await store.get_similar_papers("arxiv_1") == []

    @pytest.mark.asyncio
    async def test_excludes_self_and_respects_limit(self, store):
        store.paper_collection.get.return_value = {"embeddings": [[0.1, 0.2]]}
        store.paper_collection.query.return_value = {
            "ids": [["arxiv_1", "arxiv_2", "arxiv_3"]],
            "metadatas": [
                [
                    {"title": "self"},
                    {"title": "P2", "authors": json.dumps(["B"]), "source": "arxiv"},
                    {"title": "P3", "authors": json.dumps(["C"]), "source": "arxiv"},
                ]
            ],
            "distances": [[0.0, 1.0, 3.0]],
        }

        papers = await store.get_similar_papers("arxiv_1", limit=1)

        assert [p["paper_id"] for p in papers] == ["arxiv_2"]
        assert papers[0]["similarity"] == 0.5
        assert store.paper_collection.query.call_args.kwargs["n_results"] == 2

    @pytest.mark.asyncio
    async def test_returns_empty_on_error(self, store):
        store.paper_collection.get.side_effect = RuntimeError("boom")

        assert await store.get_similar_papers("arxiv_1") == []


class TestDeleteAndStats:
    @pytest.mark.asyncio
    async def test_delete_returns_false_when_not_initialized(self):
        assert await VectorStore().delete_paper_from_index("arxiv_1") is False

    @pytest.mark.asyncio
    async def test_delete_calls_collection(self, store):
        assert await store.delete_paper_from_index("arxiv_1") is True
        store.paper_collection.delete.assert_called_once_with(ids=["arxiv_1"])

    @pytest.mark.asyncio
    async def test_delete_returns_false_on_error(self, store):
        store.paper_collection.delete.side_effect = RuntimeError("boom")

        assert await store.delete_paper_from_index("arxiv_1") is False

    def test_stats_without_collection(self):
        assert VectorStore().get_index_stats() == {"count": 0}

    def test_stats_with_collection(self, store):
        store.paper_collection.count.return_value = 7

        assert store.get_index_stats() == {"count": 7}
