"""系统初始化流程与数据库会话依赖的单元测试。"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core import init as init_module
from src.core.init import initialize_system
from src.db.database import get_db


@pytest.fixture
def components(monkeypatch):
    """替换初始化过程中依赖的所有组件。"""
    vector_store = MagicMock()
    vector_store.initialize = AsyncMock()
    mocks = {
        "Base": MagicMock(),
        "VectorStore": MagicMock(return_value=vector_store),
        "ArxivCrawler": MagicMock(),
        "PaperInterpreter": MagicMock(),
        "ScriptGenerator": MagicMock(),
        "vector_store": vector_store,
    }
    for name in ("Base", "VectorStore", "ArxivCrawler", "PaperInterpreter", "ScriptGenerator"):
        monkeypatch.setattr(init_module, name, mocks[name])
    return mocks


class TestInitializeSystem:
    @pytest.mark.asyncio
    async def test_initializes_all_components(self, components):
        await initialize_system()

        components["Base"].metadata.create_all.assert_called_once_with(
            bind=init_module.engine
        )
        components["vector_store"].initialize.assert_awaited_once()
        components["ArxivCrawler"].assert_called_once()
        components["PaperInterpreter"].assert_called_once()
        components["ScriptGenerator"].assert_called_once()

    @pytest.mark.asyncio
    async def test_vector_store_failure_is_not_fatal(self, components):
        components["vector_store"].initialize.side_effect = RuntimeError("chroma down")

        await initialize_system()

        components["ArxivCrawler"].assert_called_once()

    @pytest.mark.asyncio
    async def test_database_failure_aborts_startup(self, components):
        components["Base"].metadata.create_all.side_effect = RuntimeError("no db")

        with pytest.raises(RuntimeError):
            await initialize_system()

        components["ArxivCrawler"].assert_not_called()

    @pytest.mark.asyncio
    async def test_crawler_failure_aborts_startup(self, components):
        components["ArxivCrawler"].side_effect = RuntimeError("crawler broken")

        with pytest.raises(RuntimeError):
            await initialize_system()

        components["PaperInterpreter"].assert_not_called()

    @pytest.mark.asyncio
    async def test_interpreter_failure_aborts_startup(self, components):
        components["PaperInterpreter"].side_effect = RuntimeError("no api key")

        with pytest.raises(RuntimeError):
            await initialize_system()

        components["ScriptGenerator"].assert_not_called()

    @pytest.mark.asyncio
    async def test_script_generator_failure_aborts_startup(self, components):
        components["ScriptGenerator"].side_effect = RuntimeError("no docker")

        with pytest.raises(RuntimeError):
            await initialize_system()


class TestGetDb:
    def test_yields_session_and_closes_it(self, monkeypatch):
        session = MagicMock()
        monkeypatch.setattr(
            "src.db.database.SessionLocal", MagicMock(return_value=session)
        )

        generator = get_db()
        assert next(generator) is session
        session.close.assert_not_called()

        with pytest.raises(StopIteration):
            next(generator)
        session.close.assert_called_once()
