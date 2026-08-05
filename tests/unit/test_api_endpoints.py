"""API端点的单元测试，所有外部依赖（数据库、大模型、Docker、向量库）均被替换。"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.v1.api import api_router
from src.api.v1.endpoints import knowledge as knowledge_module
from src.api.v1.endpoints import papers as papers_module
from src.api.v1.endpoints import reproduction as reproduction_module
from src.db.models import Paper


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(api_router, prefix="/api/v1")
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def api_db(patch_get_db):
    """把所有直接使用get_db的端点模块指向测试会话。"""
    session = None
    for module in (papers_module, reproduction_module):
        session = patch_get_db(module)
    return session


@pytest.fixture
def mock_vector_store(monkeypatch):
    """替换知识库端点使用的VectorStore。"""
    store = MagicMock()
    store.initialize = AsyncMock()
    store.search_papers = AsyncMock(return_value=[])
    store.get_similar_papers = AsyncMock(return_value=[])
    store.add_paper_to_index = AsyncMock(return_value=True)
    store.delete_paper_from_index = AsyncMock(return_value=True)
    store.get_index_stats = MagicMock(return_value={"count": 3})
    monkeypatch.setattr(knowledge_module, "VectorStore", MagicMock(return_value=store))
    return store


@pytest.fixture
def mock_arxiv_client(monkeypatch):
    """替换爬虫端点使用的AsyncArxivClient。"""
    from src.api.v1.endpoints import crawler as crawler_module

    arxiv = MagicMock()
    arxiv.search_papers.return_value = ["result-1", "result-2"]
    arxiv.parse_result.side_effect = lambda r: {"paper_id": f"arxiv_{r}"}
    arxiv.save_papers_to_db.return_value = 2
    arxiv.search_by_id.return_value = "result-1"
    arxiv.download_pdf.return_value = "/tmp/arxiv_1.pdf"
    arxiv.search_and_save.return_value = [{"paper_id": "arxiv_1", "local_pdf_path": "/tmp/a.pdf"}]
    monkeypatch.setattr(crawler_module, "AsyncArxivClient", MagicMock(return_value=arxiv))
    return arxiv


class TestCrawlerEndpoints:
    def test_search_parses_and_saves_results(self, client, mock_arxiv_client):
        response = client.post("/api/v1/crawler/search/arxiv", json={"query": "attention"})

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 2
        assert body["saved_count"] == 2
        assert body["papers"][0]["paper_id"] == "arxiv_result-1"

    def test_search_skips_db_write_when_disabled(self, client, mock_arxiv_client):
        response = client.post(
            "/api/v1/crawler/search/arxiv", json={"query": "attention", "save_to_db": False}
        )

        assert response.json()["saved_count"] == 0
        mock_arxiv_client.save_papers_to_db.assert_not_called()

    def test_search_applies_start_offset(self, client, mock_arxiv_client):
        response = client.post(
            "/api/v1/crawler/search/arxiv", json={"query": "attention", "start": 1}
        )

        assert response.json()["total"] == 1

    def test_search_500_on_client_error(self, client, mock_arxiv_client):
        mock_arxiv_client.search_papers.side_effect = RuntimeError("arxiv down")

        response = client.post("/api/v1/crawler/search/arxiv", json={"query": "a"})

        assert response.status_code == 500
        assert "arxiv down" in response.json()["detail"]

    def test_download_404_for_unknown_paper(self, client, patch_get_db, mock_arxiv_client):
        from src.db import database as database_module

        patch_get_db(database_module)

        response = client.post("/api/v1/crawler/download/missing")

        assert response.status_code == 404
        assert response.json()["detail"] == "论文不存在"

    def test_download_returns_existing_file(
        self, client, patch_get_db, mock_arxiv_client, sample_paper, tmp_path
    ):
        from src.db import database as database_module

        db = patch_get_db(database_module)
        pdf = tmp_path / "existing.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        sample_paper.pdf_path = str(pdf)
        db.commit()

        response = client.post(f"/api/v1/crawler/download/{sample_paper.paper_id}")

        assert response.status_code == 200
        assert response.json()["message"] == "文件已存在，无需重复下载"
        mock_arxiv_client.download_pdf.assert_not_called()

    def test_download_stores_pdf_path(
        self, client, patch_get_db, mock_arxiv_client, sample_paper
    ):
        from src.db import database as database_module

        patch_get_db(database_module)

        response = client.post(f"/api/v1/crawler/download/{sample_paper.paper_id}")

        assert response.status_code == 200
        assert response.json()["pdf_path"] == "/tmp/arxiv_1.pdf"
        assert sample_paper.status == "downloaded"

    def test_search_by_id_returns_paper(self, client, mock_arxiv_client):
        response = client.get("/api/v1/crawler/search/arxiv/id/1706.03762")

        assert response.status_code == 200
        assert response.json()["paper"] == {"paper_id": "arxiv_result-1"}
        mock_arxiv_client.save_papers_to_db.assert_called_once()

    def test_search_by_id_reports_missing_paper(self, client, mock_arxiv_client):
        mock_arxiv_client.search_by_id.return_value = None

        response = client.get("/api/v1/crawler/search/arxiv/id/0000.00000")

        assert response.status_code == 500
        assert "未找到该论文" in response.json()["detail"]

    def test_advanced_search_counts_downloads(self, client, mock_arxiv_client):
        response = client.post(
            "/api/v1/crawler/search/arxiv/advanced",
            json={"query": "attention", "download_pdfs": True},
        )

        assert response.status_code == 200
        assert response.json()["downloaded_pdfs"] == 1

    def test_advanced_search_500_on_client_error(self, client, mock_arxiv_client):
        mock_arxiv_client.search_and_save.side_effect = TypeError("unexpected kwarg")

        response = client.post("/api/v1/crawler/search/arxiv/advanced", json={"query": "a"})

        assert response.status_code == 500

    def test_lists_supported_sources(self, client):
        response = client.get("/api/v1/crawler/sources")

        assert response.status_code == 200
        sources = response.json()["sources"]
        assert [s["id"] for s in sources] == ["arxiv", "semantic_scholar", "ieee_xplore"]
        assert sources[0]["supported"] is True

    def test_rejects_out_of_range_max_results(self, client):
        response = client.post("/api/v1/crawler/search/arxiv", json={"query": "a", "max_results": 500})

        assert response.status_code == 422


class TestPapersEndpoints:
    def test_lists_papers_with_pagination(self, client, api_db, sample_paper):
        response = client.get("/api/v1/papers/?limit=10&offset=0")

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["papers"][0]["paper_id"] == sample_paper.paper_id

    def test_filters_by_source_and_status(self, client, api_db, sample_paper):
        assert client.get("/api/v1/papers/?source=arxiv").json()["total"] == 1
        assert client.get("/api/v1/papers/?source=ieee").json()["total"] == 0
        assert client.get("/api/v1/papers/?status=interpreted").json()["total"] == 0

    def test_filters_by_keyword_and_category(self, client, api_db, sample_paper):
        assert client.get("/api/v1/papers/?keyword=Attention").json()["total"] == 1
        assert client.get("/api/v1/papers/?keyword=nonexistent").json()["total"] == 0
        assert client.get("/api/v1/papers/?category=cs.CL").json()["total"] == 1

    def test_truncates_long_abstracts(self, client, api_db, db_session):
        db_session.add(
            Paper(
                paper_id="arxiv_long",
                title="Long",
                authors=[],
                abstract="x" * 500,
                source="arxiv",
                categories=[],
                url="http://example.com",
                status="new",
            )
        )
        db_session.commit()

        papers = client.get("/api/v1/papers/?keyword=xxx").json()["papers"]

        assert papers[0]["abstract"].endswith("...")
        assert len(papers[0]["abstract"]) == 203

    def test_returns_paper_detail(self, client, api_db, sample_paper):
        response = client.get(f"/api/v1/papers/{sample_paper.paper_id}")

        assert response.status_code == 200
        assert response.json()["title"] == sample_paper.title

    def test_detail_404_for_unknown_paper(self, client, api_db):
        response = client.get("/api/v1/papers/missing")

        assert response.status_code == 404
        assert response.json()["detail"] == "论文不存在"

    def test_delete_removes_paper_and_interpretation(
        self, client, api_db, monkeypatch, sample_interpretation, sample_paper
    ):
        store = MagicMock()
        store.initialize = AsyncMock()
        store.delete_paper_from_index = AsyncMock(return_value=True)
        monkeypatch.setattr(
            "src.modules.knowledge.vector_store.VectorStore",
            MagicMock(return_value=store),
        )

        response = client.delete(f"/api/v1/papers/{sample_paper.paper_id}")

        assert response.status_code == 200
        assert api_db.query(Paper).count() == 0
        store.delete_paper_from_index.assert_awaited_once_with(sample_paper.paper_id)

    def test_delete_404_for_unknown_paper(self, client, api_db):
        assert client.delete("/api/v1/papers/missing").status_code == 404

    def test_interpretation_404_when_not_interpreted(self, client, api_db, sample_paper):
        response = client.get(f"/api/v1/papers/{sample_paper.paper_id}/interpretation")

        assert response.status_code == 404
        assert response.json()["detail"] == "论文尚未解读"


class TestReproductionEndpoints:
    def test_generate_script_returns_task(self, client, api_db, monkeypatch, sample_paper):
        generator = MagicMock()
        generator.generate_script = AsyncMock(
            return_value={
                "task_id": "task-x",
                "paper_id": sample_paper.paper_id,
                "script_path": "/tmp/reproduce.py",
                "requirements_path": None,
                "dockerfile_path": None,
            }
        )
        monkeypatch.setattr(
            reproduction_module, "ScriptGenerator", MagicMock(return_value=generator)
        )

        response = client.post(f"/api/v1/reproduction/generate/{sample_paper.paper_id}")

        assert response.status_code == 200
        assert response.json()["task_id"] == "task-x"

    def test_generate_script_500_when_generation_fails(self, client, api_db, monkeypatch):
        generator = MagicMock()
        generator.generate_script = AsyncMock(return_value=None)
        monkeypatch.setattr(
            reproduction_module, "ScriptGenerator", MagicMock(return_value=generator)
        )

        response = client.post("/api/v1/reproduction/generate/arxiv_1")

        assert response.status_code == 500
        assert response.json()["detail"] == "生成复现脚本失败"

    def test_run_task_returns_result(self, client, api_db, monkeypatch):
        generator = MagicMock()
        generator.run_reproduction = AsyncMock(
            return_value={
                "task_id": "task-1",
                "status": "success",
                "exit_code": 0,
                "logs": "ok",
                "result": {"bleu": 28.4},
                "error_message": None,
            }
        )
        monkeypatch.setattr(
            reproduction_module, "ScriptGenerator", MagicMock(return_value=generator)
        )

        response = client.post("/api/v1/reproduction/run/task-1")

        assert response.status_code == 200
        assert response.json()["status"] == "success"

    def test_run_task_500_on_error(self, client, api_db, monkeypatch):
        generator = MagicMock()
        generator.run_reproduction = AsyncMock(side_effect=RuntimeError("docker down"))
        monkeypatch.setattr(
            reproduction_module, "ScriptGenerator", MagicMock(return_value=generator)
        )

        response = client.post("/api/v1/reproduction/run/task-1")

        assert response.status_code == 500
        assert "docker down" in response.json()["detail"]

    def test_get_task_status(self, client, api_db, sample_task):
        response = client.get(f"/api/v1/reproduction/task/{sample_task.task_id}")

        assert response.status_code == 200
        assert response.json()["status"] == "pending"

    def test_get_task_404(self, client, api_db):
        assert client.get("/api/v1/reproduction/task/missing").status_code == 404

    def test_list_tasks_with_filters(self, client, api_db, sample_task):
        assert client.get("/api/v1/reproduction/tasks").json()["total"] == 1
        assert client.get("/api/v1/reproduction/tasks?status=success").json()["total"] == 0
        assert (
            client.get(f"/api/v1/reproduction/tasks?paper_id={sample_task.paper_id}").json()["total"]
            == 1
        )


class TestKnowledgeEndpoints:
    def test_semantic_search_passes_source_filter(self, client, mock_vector_store):
        mock_vector_store.search_papers.return_value = [{"paper_id": "arxiv_1"}]

        response = client.post("/api/v1/knowledge/search?query=attention&source=arxiv")

        assert response.status_code == 200
        assert response.json()["total"] == 1
        assert mock_vector_store.search_papers.await_args.kwargs["filter_conditions"] == {
            "source": "arxiv"
        }

    def test_semantic_search_without_filter(self, client, mock_vector_store):
        client.post("/api/v1/knowledge/search?query=attention")

        assert mock_vector_store.search_papers.await_args.kwargs["filter_conditions"] is None

    def test_semantic_search_500_on_error(self, client, mock_vector_store):
        mock_vector_store.initialize.side_effect = RuntimeError("chroma down")

        response = client.post("/api/v1/knowledge/search?query=attention")

        assert response.status_code == 500

    def test_similar_papers(self, client, mock_vector_store):
        mock_vector_store.get_similar_papers.return_value = [{"paper_id": "arxiv_2"}]

        response = client.get("/api/v1/knowledge/similar/arxiv_1?limit=5")

        assert response.json() == {"total": 1, "papers": [{"paper_id": "arxiv_2"}]}

    def test_add_to_index(self, client, mock_vector_store):
        response = client.post("/api/v1/knowledge/index/arxiv_1")

        assert response.status_code == 200
        assert response.json()["message"] == "添加成功"

    def test_add_to_index_500_when_rejected(self, client, mock_vector_store):
        mock_vector_store.add_paper_to_index.return_value = False

        response = client.post("/api/v1/knowledge/index/arxiv_1")

        assert response.status_code == 500
        assert response.json()["detail"] == "添加索引失败"

    def test_delete_from_index(self, client, mock_vector_store):
        assert client.delete("/api/v1/knowledge/index/arxiv_1").status_code == 200

    def test_delete_from_index_500_when_rejected(self, client, mock_vector_store):
        mock_vector_store.delete_paper_from_index.return_value = False

        assert client.delete("/api/v1/knowledge/index/arxiv_1").status_code == 500

    def test_stats_combines_vector_and_relational_counts(
        self, client, mock_vector_store, patch_get_db, sample_paper
    ):
        from src.db import database as database_module

        patch_get_db(database_module)

        response = client.get("/api/v1/knowledge/stats")

        assert response.status_code == 200
        body = response.json()
        assert body["indexed_papers"] == 3
        assert body["total_papers"] == 1
        assert body["interpreted_papers"] == 0
        assert body["reproduced_papers"] == 0


class TestInterpretationEndpoints:
    def test_interpret_500_when_interpreter_returns_none(self, client, monkeypatch):
        from src.api.v1.endpoints import interpretation as interpretation_module

        interpreter = MagicMock()
        interpreter.interpret_paper = AsyncMock(return_value=None)
        monkeypatch.setattr(
            interpretation_module, "PaperInterpreter", MagicMock(return_value=interpreter)
        )

        response = client.post("/api/v1/interpretation/arxiv_1")

        assert response.status_code == 500
        assert response.json()["detail"] == "论文解读失败"

    def test_get_interpretation_returns_null_when_absent(self, client, patch_get_db):
        from src.api.v1.endpoints import interpretation as interpretation_module

        patch_get_db(interpretation_module)

        response = client.get("/api/v1/interpretation/arxiv_1")

        assert response.status_code == 200
        assert response.json() is None

    def test_get_interpretation_returns_stored_fields(
        self, client, patch_get_db, sample_interpretation
    ):
        from src.api.v1.endpoints import interpretation as interpretation_module

        patch_get_db(interpretation_module)

        response = client.get(f"/api/v1/interpretation/{sample_interpretation.paper_id}")

        assert response.status_code == 200
        body = response.json()
        assert body["experimental_setup"] == ["8 GPU"]
        assert body["datasets"] == [{"name": "WMT 2014"}]
        assert body["interpretation_time"].startswith(
            sample_interpretation.interpretation_time.isoformat()[:10]
        )

    def test_get_interpretation_500_on_db_error(self, client, monkeypatch):
        from src.api.v1.endpoints import interpretation as interpretation_module

        def broken_get_db():
            raise RuntimeError("db gone")
            yield

        monkeypatch.setattr(interpretation_module, "get_db", broken_get_db)

        response = client.get("/api/v1/interpretation/arxiv_1")

        assert response.status_code == 500
        assert "db gone" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_batch_interpret_counts_successes_and_failures(self, monkeypatch):
        from src.api.v1.endpoints import interpretation as interpretation_module

        interpreter = MagicMock()
        interpreter.interpret_paper = AsyncMock(
            side_effect=[{"paper_id": "arxiv_1"}, None, RuntimeError("boom")]
        )
        monkeypatch.setattr(
            interpretation_module, "PaperInterpreter", MagicMock(return_value=interpreter)
        )

        result = await interpretation_module.batch_interpret(
            ["arxiv_1", "arxiv_2", "arxiv_3"]
        )

        assert result["total"] == 3
        assert result["success"] == 1
        assert result["failed"] == 2
        assert result["failed_ids"] == ["arxiv_2", "arxiv_3"]
        assert result["results"] == [{"paper_id": "arxiv_1"}]

    def test_batch_route_is_shadowed_by_paper_id_route(self, client, monkeypatch):
        """POST /{paper_id} 注册在 /batch 之前，因此 /batch 被当作 paper_id 处理。"""
        from src.api.v1.endpoints import interpretation as interpretation_module

        interpreter = MagicMock()
        interpreter.interpret_paper = AsyncMock(return_value=None)
        monkeypatch.setattr(
            interpretation_module, "PaperInterpreter", MagicMock(return_value=interpreter)
        )

        response = client.post(
            "/api/v1/interpretation/batch", json=["arxiv_1", "arxiv_2"]
        )

        assert response.status_code == 500
        interpreter.interpret_paper.assert_awaited_once_with("batch", False)
