"""PaperInterpreter的单元测试，PDF解析与大模型调用均使用替身。"""

import io
import os
from contextlib import contextmanager
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from PIL import Image

from src.db.models import PaperInterpretation
from src.modules.interpretation import paper_interpreter as interpreter_module
from src.modules.interpretation.paper_interpreter import (
    CodeLink,
    DatasetInfo,
    EvaluationMetric,
    ExperimentalResult,
    MethodDetail,
    PaperInterpretationResult,
    PaperInterpreter,
)


@pytest.fixture(autouse=True)
def patch_llm(monkeypatch):
    """屏蔽真实的ChatOpenAI构造。"""
    monkeypatch.setattr(
        interpreter_module, "ChatOpenAI", MagicMock(return_value=MagicMock())
    )


@pytest.fixture
def interpreter():
    return PaperInterpreter()


def png_bytes(color=(255, 0, 0)):
    buffer = io.BytesIO()
    Image.new("RGB", (4, 4), color).save(buffer, format="PNG")
    return buffer.getvalue()


def fake_pdf(monkeypatch, pages):
    """把pdfplumber.open替换为返回给定页面的上下文管理器。"""

    @contextmanager
    def _open(_path):
        yield SimpleNamespace(pages=pages)

    monkeypatch.setattr(interpreter_module.pdfplumber, "open", _open)


def make_page(text=None, images=()):
    return SimpleNamespace(extract_text=lambda: text, images=list(images))


def make_image(data, img_type="png"):
    return {
        "stream": SimpleNamespace(get_data=lambda: data),
        "type": img_type,
        "x0": 0,
        "top": 1,
        "x1": 2,
        "bottom": 3,
    }


def make_result(**overrides):
    data = {
        "problem_domain": "序列建模",
        "core_contributions": ["提出Transformer"],
        "innovations": ["自注意力"],
        "limitations": ["显存占用高"],
        "conclusions": ["优于RNN"],
        "technical_approach": "纯注意力架构",
        "method_details": [
            MethodDetail(
                name="Multi-Head Attention",
                description="并行注意力头",
                implementation_steps=["线性投影", "缩放点积"],
                formula="softmax(QK^T/\\sqrt{d})V",
            )
        ],
        "implementation_notes": ["注意mask"],
        "code_links": [
            CodeLink(url="https://github.com/example", description="官方实现", platform="GitHub")
        ],
        "datasets": [
            DatasetInfo(name="WMT 2014", source="statmt.org", scale="4.5M", characteristics="翻译语料")
        ],
        "experimental_setup": ["8 x P100"],
        "evaluation_metrics": [
            EvaluationMetric(
                name="BLEU", definition="n-gram重合度", existing_library="sacrebleu", paper_value="28.4"
            )
        ],
        "experimental_results": [
            ExperimentalResult(
                metric_name="BLEU", value="28.4", comparison="优于ConvS2S", significance="显著"
            )
        ],
        "baseline_comparison": ["优于ConvS2S"],
        "key_references": ["Bahdanau et al. 2015"],
        "confidence_score": 0.88,
        "figure_descriptions": [
            {"page_num": 1, "figure_num": "1", "description": "模型结构图"}
        ],
    }
    data.update(overrides)
    return PaperInterpretationResult(**data)


class TestTruncateText:
    def test_keeps_short_text_untouched(self, interpreter):
        assert interpreter._truncate_text("short") == "short"

    def test_truncates_long_text_from_both_ends(self, interpreter):
        text = "a" * 8000 + "b" * 8000

        truncated = interpreter._truncate_text(text)

        assert "...[内容截断]..." in truncated
        assert truncated.startswith("a" * 100)
        assert truncated.endswith("b" * 100)
        assert len(truncated) < len(text)


class TestExtractTextFromPdf:
    def test_returns_none_when_file_missing(self, interpreter, tmp_path):
        assert interpreter.extract_text_from_pdf(str(tmp_path / "nope.pdf")) is None

    def test_concatenates_page_text(self, interpreter, tmp_path, monkeypatch):
        pdf = tmp_path / "paper.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        fake_pdf(monkeypatch, [make_page("page one"), make_page(None), make_page("page two")])

        text = interpreter.extract_text_from_pdf(str(pdf))

        assert text == "page one\n\npage two\n\n"

    def test_returns_none_on_parse_error(self, interpreter, tmp_path, monkeypatch):
        pdf = tmp_path / "paper.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        monkeypatch.setattr(
            interpreter_module.pdfplumber, "open", MagicMock(side_effect=ValueError("bad pdf"))
        )

        assert interpreter.extract_text_from_pdf(str(pdf)) is None


class TestExtractImagesFromPdf:
    def test_returns_empty_when_file_missing(self, interpreter, tmp_path):
        assert interpreter.extract_images_from_pdf(str(tmp_path / "nope.pdf"), "p1") == []

    def test_saves_valid_images_with_metadata(
        self, interpreter, tmp_path, monkeypatch
    ):
        monkeypatch.setattr(interpreter_module.settings, "STORAGE_PATH", str(tmp_path))
        pdf = tmp_path / "paper.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        fake_pdf(monkeypatch, [make_page(images=[make_image(png_bytes())])])

        images = interpreter.extract_images_from_pdf(str(pdf), "arxiv_1")

        assert len(images) == 1
        assert images[0]["filename"] == "page_1_img_1.png"
        assert images[0]["page_num"] == 1
        assert (images[0]["width"], images[0]["height"]) == (4, 4)
        assert images[0]["bbox"] == (0, 1, 2, 3)
        assert os.path.exists(images[0]["path"])

    def test_skips_corrupted_images(self, interpreter, tmp_path, monkeypatch):
        monkeypatch.setattr(interpreter_module.settings, "STORAGE_PATH", str(tmp_path))
        pdf = tmp_path / "paper.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        fake_pdf(monkeypatch, [make_page(images=[make_image(b"not-an-image")])])

        images = interpreter.extract_images_from_pdf(str(pdf), "arxiv_1")

        assert images == []
        images_dir = tmp_path / "papers" / "arxiv_1" / "images"
        assert list(images_dir.iterdir()) == []

    def test_continues_after_stream_error(self, interpreter, tmp_path, monkeypatch):
        monkeypatch.setattr(interpreter_module.settings, "STORAGE_PATH", str(tmp_path))
        pdf = tmp_path / "paper.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        broken = {
            "stream": SimpleNamespace(get_data=MagicMock(side_effect=OSError("bad stream"))),
            "type": "png",
        }
        fake_pdf(monkeypatch, [make_page(images=[broken, make_image(png_bytes())])])

        images = interpreter.extract_images_from_pdf(str(pdf), "arxiv_1")

        assert len(images) == 1
        assert images[0]["index"] == 2

    def test_returns_empty_on_parse_error(self, interpreter, tmp_path, monkeypatch):
        monkeypatch.setattr(interpreter_module.settings, "STORAGE_PATH", str(tmp_path))
        pdf = tmp_path / "paper.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        monkeypatch.setattr(
            interpreter_module.pdfplumber, "open", MagicMock(side_effect=ValueError("bad pdf"))
        )

        assert interpreter.extract_images_from_pdf(str(pdf), "arxiv_1") == []


class TestGenerateMarkdownReport:
    def test_renders_all_sections(self, interpreter, sample_paper):
        sample_paper.updated_at = datetime(2024, 1, 2, 3, 4, 5)

        markdown = interpreter.generate_markdown_report(sample_paper, make_result(), [])

        assert markdown.startswith(f"# {sample_paper.title}")
        assert "## 🎯 问题领域" in markdown
        assert "- 提出Transformer" in markdown
        assert "### Multi-Head Attention" in markdown
        assert "```latex" in markdown
        assert "- [官方实现](https://github.com/example) (GitHub)" in markdown
        assert "### WMT 2014" in markdown
        assert "## 📚 关键参考文献" in markdown
        assert "2024-01-02 03:04:05" in markdown

    def test_matches_figures_to_page_images(self, interpreter, sample_paper):
        images = [
            {"page_num": 1, "index": 1, "filename": "page_1_img_1.png"},
            {"page_num": 2, "index": 1, "filename": "page_2_img_1.png"},
        ]

        markdown = interpreter.generate_markdown_report(sample_paper, make_result(), images)

        assert "![模型结构图](./images/page_1_img_1.png)" in markdown
        assert "### 其他图片" in markdown
        assert "./images/page_2_img_1.png" in markdown

    def test_figure_without_matching_image(self, interpreter, sample_paper):
        markdown = interpreter.generate_markdown_report(sample_paper, make_result(), [])

        assert "### 图 1 (第 1 页)" in markdown
        assert "![模型结构图]" not in markdown

    def test_optional_sections_are_skipped_when_empty(self, interpreter, sample_paper):
        result = make_result(
            implementation_notes=[],
            code_links=[],
            experimental_setup=[],
            evaluation_metrics=[],
            experimental_results=[],
            baseline_comparison=[],
            key_references=[],
            figure_descriptions=[],
        )

        markdown = interpreter.generate_markdown_report(sample_paper, result, [])

        assert "## 🔗 代码链接" not in markdown
        assert "## 📏 评价指标" not in markdown
        assert "## 📚 关键参考文献" not in markdown
        assert "## 🖼️ 图表说明" not in markdown


class TestInterpretPaper:
    @pytest.mark.asyncio
    async def test_returns_none_when_paper_missing(self, interpreter, patch_get_db):
        patch_get_db(interpreter_module)

        assert await interpreter.interpret_paper("missing") is None

    @pytest.mark.asyncio
    async def test_returns_cached_interpretation(
        self, interpreter, patch_get_db, sample_interpretation, sample_paper
    ):
        patch_get_db(interpreter_module)
        interpreter.llm.ainvoke = AsyncMock()

        result = await interpreter.interpret_paper(sample_paper.paper_id)

        assert result["problem_domain"] == "序列建模"
        assert result["core_contributions"] == ["提出Transformer"]
        interpreter.llm.ainvoke.assert_not_called()

    @pytest.mark.asyncio
    async def test_interprets_abstract_and_persists_result(
        self, interpreter, patch_get_db, sample_paper, tmp_path, monkeypatch
    ):
        session = patch_get_db(interpreter_module)
        monkeypatch.setattr(interpreter_module.settings, "STORAGE_PATH", str(tmp_path))
        interpreter.llm.ainvoke = AsyncMock(return_value=MagicMock(content="raw-json"))
        interpreter.parser = MagicMock()
        interpreter.parser.get_format_instructions.return_value = "format"
        interpreter.parser.parse.return_value = make_result()

        result = await interpreter.interpret_paper(
            sample_paper.paper_id, use_abstract_only=True
        )

        assert result["confidence_score"] == 0.88
        assert result["extracted_images"] == 0
        assert os.path.exists(result["markdown_path"])

        stored = (
            session.query(PaperInterpretation)
            .filter(PaperInterpretation.paper_id == sample_paper.paper_id)
            .one()
        )
        assert stored.raw_response == "raw-json"
        assert sample_paper.status == "interpreted"

        human_prompt = interpreter.llm.ainvoke.call_args.args[0][1].content
        assert sample_paper.abstract in human_prompt

    @pytest.mark.asyncio
    async def test_falls_back_to_abstract_when_pdf_text_empty(
        self, interpreter, patch_get_db, sample_paper, db_session, tmp_path, monkeypatch
    ):
        patch_get_db(interpreter_module)
        monkeypatch.setattr(interpreter_module.settings, "STORAGE_PATH", str(tmp_path))
        pdf = tmp_path / "paper.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        sample_paper.pdf_path = str(pdf)
        db_session.commit()
        interpreter.extract_text_from_pdf = MagicMock(return_value=None)
        interpreter.extract_images_from_pdf = MagicMock(return_value=[])
        interpreter.llm.ainvoke = AsyncMock(return_value=MagicMock(content="raw-json"))
        interpreter.parser = MagicMock()
        interpreter.parser.parse.return_value = make_result()

        result = await interpreter.interpret_paper(sample_paper.paper_id)

        assert result is not None
        interpreter.extract_text_from_pdf.assert_called_once_with(str(pdf))
        human_prompt = interpreter.llm.ainvoke.call_args.args[0][1].content
        assert sample_paper.abstract in human_prompt

    @pytest.mark.asyncio
    async def test_uses_truncated_full_text_and_extracts_images(
        self, interpreter, patch_get_db, sample_paper, db_session, tmp_path, monkeypatch
    ):
        patch_get_db(interpreter_module)
        monkeypatch.setattr(interpreter_module.settings, "STORAGE_PATH", str(tmp_path))
        pdf = tmp_path / "paper.pdf"
        pdf.write_bytes(b"%PDF-1.4")
        sample_paper.pdf_path = str(pdf)
        db_session.commit()
        interpreter.extract_text_from_pdf = MagicMock(return_value="full text body")
        interpreter.extract_images_from_pdf = MagicMock(
            return_value=[{"page_num": 1, "index": 1, "filename": "page_1_img_1.png"}]
        )
        interpreter.llm.ainvoke = AsyncMock(return_value=MagicMock(content="raw-json"))
        interpreter.parser = MagicMock()
        interpreter.parser.parse.return_value = make_result()

        result = await interpreter.interpret_paper(sample_paper.paper_id)

        assert result["extracted_images"] == 1
        human_prompt = interpreter.llm.ainvoke.call_args.args[0][1].content
        assert "full text body" in human_prompt

    @pytest.mark.asyncio
    async def test_returns_none_when_parsing_fails(
        self, interpreter, patch_get_db, sample_paper
    ):
        session = patch_get_db(interpreter_module)
        interpreter.llm.ainvoke = AsyncMock(return_value=MagicMock(content="garbage"))
        interpreter.parser = MagicMock()
        interpreter.parser.parse.side_effect = ValueError("cannot parse")

        assert await interpreter.interpret_paper(sample_paper.paper_id, True) is None
        assert session.query(PaperInterpretation).count() == 0
