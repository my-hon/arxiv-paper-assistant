"""ArxivClient和AsyncArxivClient的单元测试，全部使用替身，不访问网络。"""

import os
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.db.models import Paper
from src.modules.crawler import arxiv_client as arxiv_client_module
from src.modules.crawler.arxiv_client import ArxivClient, AsyncArxivClient


def make_result(entry_id="http://arxiv.org/abs/1706.03762v5", **overrides):
    """构造一个模拟的arxiv.Result对象。"""
    data = {
        "entry_id": entry_id,
        "title": "Attention Is All\nYou Need",
        "authors": [SimpleNamespace(name="Ashish Vaswani"), SimpleNamespace(name="Noam Shazeer")],
        "summary": "The dominant sequence\ntransduction models.",
        "published": datetime(2017, 6, 12),
        "updated": datetime(2017, 12, 6),
        "categories": ["cs.CL", "cs.LG"],
        "pdf_url": "http://arxiv.org/pdf/1706.03762v5",
        "doi": None,
        "journal_ref": None,
        "comment": None,
        "primary_category": "cs.CL",
        "download_pdf": MagicMock(return_value="/tmp/downloaded.pdf"),
    }
    data.update(overrides)
    return SimpleNamespace(**data)


@pytest.fixture
def client():
    return ArxivClient()


class TestParseResult:
    def test_maps_all_core_fields(self):
        paper = ArxivClient.parse_result(make_result())

        assert paper["paper_id"] == "arxiv_1706.03762"
        assert paper["arxiv_id"] == "1706.03762"
        assert paper["title"] == "Attention Is All You Need"
        assert paper["abstract"] == "The dominant sequence transduction models."
        assert paper["authors"] == ["Ashish Vaswani", "Noam Shazeer"]
        assert paper["source"] == "arxiv"
        assert paper["categories"] == ["cs.CL", "cs.LG"]
        assert paper["primary_category"] == "cs.CL"

    def test_omits_empty_optional_fields(self):
        paper = ArxivClient.parse_result(make_result(primary_category=None))

        assert "journal_ref" not in paper
        assert "comment" not in paper
        assert "primary_category" not in paper

    def test_includes_optional_fields_when_present(self):
        paper = ArxivClient.parse_result(
            make_result(journal_ref="NeurIPS 2017", comment="15 pages")
        )

        assert paper["journal_ref"] == "NeurIPS 2017"
        assert paper["comment"] == "15 pages"

    def test_returns_empty_dict_on_error(self):
        assert ArxivClient.parse_result(SimpleNamespace()) == {}


class TestSearchPapers:
    @pytest.mark.asyncio
    async def test_returns_normalized_papers(self, client):
        client.client.results = MagicMock(return_value=iter([make_result()]))

        papers = await client.search_papers(query="transformer")

        assert len(papers) == 1
        assert papers[0]["paper_id"] == "1706.03762v5"
        assert papers[0]["pdf_url"] == "http://arxiv.org/pdf/1706.03762v5"

    @pytest.mark.asyncio
    async def test_builds_advanced_query_from_all_filters(self, client, monkeypatch):
        captured = {}

        def fake_search(**kwargs):
            captured.update(kwargs)
            return "search-object"

        monkeypatch.setattr(arxiv_client_module.arxiv, "Search", fake_search)
        client.client.results = MagicMock(return_value=iter([]))

        await client.search_papers(
            query="transformer",
            author="Vaswani",
            title="Attention",
            abstract="sequence",
            comment="pages",
            journal_reference="NeurIPS",
            subject_category="cs.CL",
            report_number="RN-1",
            categories=["cs.AI", "cs.CV"],
        )

        assert captured["query"] == (
            "all:transformer AND au:Vaswani AND ti:Attention AND abs:sequence "
            "AND co:pages AND jr:NeurIPS AND cat:cs.CL AND rn:RN-1 "
            "AND (cat:cs.AI OR cat:cs.CV)"
        )
        assert captured["id_list"] == []

    @pytest.mark.asyncio
    async def test_id_list_skips_other_conditions(self, client, monkeypatch):
        captured = {}

        def fake_search(**kwargs):
            captured.update(kwargs)
            return "search-object"

        monkeypatch.setattr(arxiv_client_module.arxiv, "Search", fake_search)
        client.client.results = MagicMock(return_value=iter([]))

        await client.search_papers(query="ignored", id_list=["1706.03762"])

        assert captured["query"] == ""
        assert captured["id_list"] == ["1706.03762"]

    @pytest.mark.asyncio
    async def test_returns_empty_list_on_api_error(self, client):
        client.client.results = MagicMock(side_effect=RuntimeError("api down"))

        assert await client.search_papers(query="transformer") == []


class TestSearchById:
    @pytest.mark.asyncio
    async def test_returns_first_match(self, client):
        client.client.results = MagicMock(return_value=iter([make_result()]))

        paper = await client.search_by_id("1706.03762")

        assert paper["title"] == "Attention Is All\nYou Need"

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self, client):
        client.client.results = MagicMock(return_value=iter([]))

        assert await client.search_by_id("0000.00000") is None


class TestDownloadPdf:
    def test_returns_none_without_pdf_url(self, client, tmp_path):
        result = make_result(pdf_url=None)

        assert client.download_pdf(result, save_dir=str(tmp_path)) is None

    def test_returns_existing_path_without_redownloading(self, client, tmp_path):
        result = make_result()
        existing = tmp_path / "arxiv_1706.03762.pdf"
        existing.write_bytes(b"%PDF-1.4")

        path = client.download_pdf(result, save_dir=str(tmp_path))

        assert path == str(existing)
        result.download_pdf.assert_not_called()

    def test_downloads_with_generated_filename(self, client, tmp_path):
        result = make_result()

        path = client.download_pdf(result, save_dir=str(tmp_path))

        assert path == "/tmp/downloaded.pdf"
        result.download_pdf.assert_called_once_with(
            dirpath=str(tmp_path), filename="arxiv_1706.03762.pdf"
        )

    def test_uses_default_storage_path(self, client, tmp_path, monkeypatch):
        monkeypatch.setattr(
            arxiv_client_module.settings, "PDF_STORAGE_PATH", str(tmp_path / "pdfs")
        )
        result = make_result()

        client.download_pdf(result)

        assert os.path.isdir(tmp_path / "pdfs")

    def test_returns_none_on_download_error(self, client, tmp_path):
        result = make_result(download_pdf=MagicMock(side_effect=OSError("disk full")))

        assert client.download_pdf(result, save_dir=str(tmp_path)) is None


class TestSavePapersToDb:
    def test_saves_new_papers_and_filters_unknown_fields(self, client, patch_get_db):
        session = patch_get_db(arxiv_client_module)

        saved = client.save_papers_to_db(
            [{"paper_id": "arxiv_1", "title": "P1", "unknown_field": "x"}]
        )

        assert saved == 1
        stored = session.query(Paper).filter(Paper.paper_id == "arxiv_1").one()
        assert stored.title == "P1"

    def test_skips_papers_without_id(self, client, patch_get_db):
        patch_get_db(arxiv_client_module)

        assert client.save_papers_to_db([{"title": "no id"}]) == 0

    def test_skips_already_stored_papers(self, client, patch_get_db, sample_paper):
        patch_get_db(arxiv_client_module)

        saved = client.save_papers_to_db(
            [{"paper_id": sample_paper.paper_id, "title": "dup"}]
        )

        assert saved == 0

    def test_saves_multiple_papers_in_one_call(self, client, patch_get_db):
        session = patch_get_db(arxiv_client_module)

        saved = client.save_papers_to_db(
            [
                {"paper_id": "arxiv_1", "title": "P1"},
                {"paper_id": "arxiv_2", "title": "P2"},
            ]
        )

        assert saved == 2
        assert session.query(Paper).count() == 2


class TestSearchAndSave:
    def test_parses_saves_and_optionally_downloads(self, client, patch_get_db, tmp_path, monkeypatch):
        session = patch_get_db(arxiv_client_module)
        monkeypatch.setattr(
            arxiv_client_module.settings, "PDF_STORAGE_PATH", str(tmp_path)
        )
        client.search_papers = MagicMock(return_value=[make_result()])

        papers = client.search_and_save("transformer", download_pdfs=True)

        assert len(papers) == 1
        assert papers[0]["local_pdf_path"] == "/tmp/downloaded.pdf"
        assert session.query(Paper).filter(Paper.paper_id == "arxiv_1706.03762").count() == 1

    def test_skips_db_write_when_nothing_parsed(self, client):
        client.search_papers = MagicMock(return_value=[])
        client.save_papers_to_db = MagicMock()

        assert client.search_and_save("transformer") == []
        client.save_papers_to_db.assert_not_called()


class TestAsyncArxivClient:
    @pytest.mark.asyncio
    async def test_search_papers_async_delegates(self):
        client = AsyncArxivClient()
        client.search_papers = MagicMock(return_value=[{"paper_id": "arxiv_1"}])

        assert await client.search_papers_async("q") == [{"paper_id": "arxiv_1"}]

    @pytest.mark.asyncio
    async def test_download_pdf_async_delegates(self):
        client = AsyncArxivClient()
        client.download_pdf = MagicMock(return_value="/tmp/a.pdf")

        assert await client.download_pdf_async("result") == "/tmp/a.pdf"

    @pytest.mark.asyncio
    async def test_search_and_save_async_delegates(self):
        client = AsyncArxivClient()
        client.search_and_save = MagicMock(return_value=[{"paper_id": "arxiv_1"}])

        assert await client.search_and_save_async("q") == [{"paper_id": "arxiv_1"}]
