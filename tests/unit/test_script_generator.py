"""ScriptGenerator的单元测试，大模型与Docker均使用替身。"""

import os
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from docker.errors import DockerException

from src.db.models import ReproductionTask
from src.modules.reproduction import script_generator as script_generator_module
from src.modules.reproduction.script_generator import ScriptGenerator

LLM_RESPONSE = """生成结果如下：
```python
print("reproduce")
```
```requirements
torch==2.0.0
```
```dockerfile
FROM python:3.11
```
"""


@pytest.fixture(autouse=True)
def patch_external(monkeypatch):
    """屏蔽真实的ChatOpenAI和Docker连接。"""
    monkeypatch.setattr(
        script_generator_module, "ChatOpenAI", MagicMock(return_value=MagicMock())
    )
    monkeypatch.setattr(
        script_generator_module.docker,
        "DockerClient",
        MagicMock(return_value=MagicMock()),
    )


@pytest.fixture
def generator(tmp_path, monkeypatch):
    monkeypatch.setattr(
        script_generator_module.settings, "SCRIPT_STORAGE_PATH", str(tmp_path)
    )
    return ScriptGenerator()


class TestInit:
    def test_docker_client_created(self, generator):
        assert generator.docker_client is not None

    def test_docker_failure_disables_reproduction(self, monkeypatch, tmp_path):
        monkeypatch.setattr(
            script_generator_module.docker,
            "DockerClient",
            MagicMock(side_effect=DockerException("no socket")),
        )

        assert ScriptGenerator().docker_client is None


class TestExtractCodeBlock:
    def test_extracts_tagged_block(self, generator):
        assert generator._extract_code_block(LLM_RESPONSE, "python") == 'print("reproduce")'
        assert generator._extract_code_block(LLM_RESPONSE, "dockerfile") == "FROM python:3.11"

    def test_falls_back_to_untagged_block(self, generator):
        content = "```\nplain code\n```"

        assert generator._extract_code_block(content, "python") == "plain code"

    def test_returns_none_without_any_block(self, generator):
        assert generator._extract_code_block("no code here", "python") is None

    def test_returns_none_when_block_unterminated(self, generator):
        assert generator._extract_code_block("```python\nprint(1)", "python") is None


class TestGenerateScript:
    @pytest.mark.asyncio
    async def test_returns_none_when_paper_missing(self, generator, patch_get_db):
        patch_get_db(script_generator_module)

        assert await generator.generate_script("missing") is None

    @pytest.mark.asyncio
    async def test_returns_none_when_paper_not_interpreted(
        self, generator, patch_get_db, sample_paper
    ):
        patch_get_db(script_generator_module)

        assert await generator.generate_script(sample_paper.paper_id) is None

    @pytest.mark.asyncio
    async def test_writes_files_and_persists_task(
        self, generator, patch_get_db, sample_interpretation, sample_paper
    ):
        session = patch_get_db(script_generator_module)
        generator.llm.ainvoke = AsyncMock(return_value=MagicMock(content=LLM_RESPONSE))

        result = await generator.generate_script(sample_paper.paper_id)

        assert result["paper_id"] == sample_paper.paper_id
        with open(result["script_path"], encoding="utf-8") as f:
            assert f.read() == 'print("reproduce")'
        with open(result["requirements_path"], encoding="utf-8") as f:
            assert f.read() == "torch==2.0.0"
        with open(result["dockerfile_path"], encoding="utf-8") as f:
            assert f.read() == "FROM python:3.11"

        task = (
            session.query(ReproductionTask)
            .filter(ReproductionTask.task_id == result["task_id"])
            .one()
        )
        assert task.status == "pending"

    @pytest.mark.asyncio
    async def test_returns_none_when_no_python_block(
        self, generator, patch_get_db, sample_interpretation, sample_paper
    ):
        patch_get_db(script_generator_module)
        generator.llm.ainvoke = AsyncMock(return_value=MagicMock(content="no code"))

        assert await generator.generate_script(sample_paper.paper_id) is None

    @pytest.mark.asyncio
    async def test_returns_none_when_llm_fails(
        self, generator, patch_get_db, sample_interpretation, sample_paper
    ):
        patch_get_db(script_generator_module)
        generator.llm.ainvoke = AsyncMock(side_effect=RuntimeError("llm down"))

        assert await generator.generate_script(sample_paper.paper_id) is None

    @pytest.mark.asyncio
    async def test_untagged_block_is_reused_for_every_file(
        self, generator, patch_get_db, sample_interpretation, sample_paper
    ):
        """缺少语言标记时，_extract_code_block会回退到第一个代码块。"""
        session = patch_get_db(script_generator_module)
        generator.llm.ainvoke = AsyncMock(
            return_value=MagicMock(content='```python\nprint("only")\n```')
        )

        result = await generator.generate_script(sample_paper.paper_id)

        with open(result["requirements_path"], encoding="utf-8") as f:
            assert f.read() == 'python\nprint("only")'
        task = (
            session.query(ReproductionTask)
            .filter(ReproductionTask.task_id == result["task_id"])
            .one()
        )
        assert task.requirements_path == result["requirements_path"]
        assert task.dockerfile_path == result["dockerfile_path"]


def make_container(exit_code=0, logs=b"done"):
    container = MagicMock()
    container.wait.return_value = {"StatusCode": exit_code}
    container.logs.return_value = logs
    return container


class TestRunReproduction:
    @pytest.mark.asyncio
    async def test_returns_none_without_docker(self, generator):
        generator.docker_client = None

        assert await generator.run_reproduction("task-1") is None

    @pytest.mark.asyncio
    async def test_returns_none_when_task_missing(self, generator, patch_get_db):
        patch_get_db(script_generator_module)

        assert await generator.run_reproduction("missing") is None

    @pytest.mark.asyncio
    async def test_returns_none_when_task_already_running(
        self, generator, patch_get_db, sample_task, db_session
    ):
        patch_get_db(script_generator_module)
        sample_task.status = "running"
        db_session.commit()

        assert await generator.run_reproduction(sample_task.task_id) is None

    @pytest.mark.asyncio
    async def test_successful_run_parses_result_block(
        self, generator, patch_get_db, sample_task
    ):
        patch_get_db(script_generator_module)
        logs = b'=== REPRODUCTION RESULT ===\n{"bleu": 28.4}\n=== END RESULT ==='
        container = make_container(logs=logs)
        generator.docker_client.images.build.return_value = (MagicMock(id="img"), [])
        generator.docker_client.containers.run.return_value = container

        result = await generator.run_reproduction(sample_task.task_id)

        assert result["status"] == "success"
        assert result["exit_code"] == 0
        assert result["result"] == {"bleu": 28.4}
        container.remove.assert_called_once()
        assert isinstance(sample_task.completed_at, datetime)

    @pytest.mark.asyncio
    async def test_nonzero_exit_marks_task_failed(
        self, generator, patch_get_db, sample_task
    ):
        patch_get_db(script_generator_module)
        generator.docker_client.images.build.return_value = (MagicMock(id="img"), [])
        generator.docker_client.containers.run.return_value = make_container(
            exit_code=1, logs=b"traceback"
        )

        result = await generator.run_reproduction(sample_task.task_id)

        assert result["status"] == "failed"
        assert result["error_message"] == "执行失败，退出码: 1"
        assert result["logs"] == "traceback"
        assert result["result"] is None

    @pytest.mark.asyncio
    async def test_invalid_result_json_falls_back_to_raw_output(
        self, generator, patch_get_db, sample_task
    ):
        patch_get_db(script_generator_module)
        logs = b"=== REPRODUCTION RESULT ===\nnot-json\n=== END RESULT ==="
        generator.docker_client.images.build.return_value = (MagicMock(id="img"), [])
        generator.docker_client.containers.run.return_value = make_container(logs=logs)

        result = await generator.run_reproduction(sample_task.task_id)

        assert result["result"] == {"raw_output": logs.decode("utf-8")}

    @pytest.mark.asyncio
    async def test_docker_error_marks_task_failed(
        self, generator, patch_get_db, sample_task
    ):
        patch_get_db(script_generator_module)
        generator.docker_client.images.build.side_effect = DockerException("build failed")

        assert await generator.run_reproduction(sample_task.task_id) is None
        assert sample_task.status == "failed"
        assert "build failed" in sample_task.error_message
