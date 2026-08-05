"""
向量存储和知识库模块
"""

import json
from typing import List, Dict, Optional
from loguru import logger
import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.utils import embedding_functions

from src.config.settings import settings
from src.db.models import Paper, PaperInterpretation
from src.db.database import get_db


def _paper_from_metadata(
    paper_id: str,
    metadata: Dict,
    distance: float,
    snippet: Optional[str] = None,
) -> Dict:
    """将Chroma查询返回的元数据转换为统一的论文字典。

    Args:
        paper_id: 论文ID。
        metadata: Chroma中存储的元数据。
        distance: 向量距离，用于换算相似度（0-1，越高越相似）。
        snippet: 文档内容，提供时附加分类、状态等完整字段和预览片段。
    """
    paper = {
        "paper_id": paper_id,
        "title": metadata.get("title", ""),
        "authors": json.loads(metadata.get("authors", "[]")),
        "source": metadata.get("source", ""),
        "publication_date": metadata.get("publication_date", ""),
        "similarity": 1 / (1 + distance),
    }

    if snippet is not None:
        paper.update(
            {
                "categories": json.loads(metadata.get("categories", "[]")),
                "citation_count": metadata.get("citation_count", 0),
                "status": metadata.get("status", ""),
                "snippet": snippet[:300] + "...",
            }
        )

    return paper


class VectorStore:
    """向量存储管理器"""

    def __init__(self):
        self.client = None
        self.paper_collection = None
        self.embedding_function = None

    async def initialize(self):
        """初始化向量存储"""
        try:
            # 初始化ChromaDB客户端
            if settings.CHROMA_DB_HOST and settings.CHROMA_DB_PORT:
                # 远程Chroma服务
                self.client = chromadb.HttpClient(
                    host=settings.CHROMA_DB_HOST,
                    port=settings.CHROMA_DB_PORT,
                    settings=ChromaSettings(anonymized_telemetry=False, allow_reset=True),
                )
                logger.info(f"连接到远程Chroma服务: {settings.CHROMA_DB_HOST}:{settings.CHROMA_DB_PORT}")
            else:
                # 本地持久化存储
                self.client = chromadb.PersistentClient(
                    path=settings.CHROMA_DB_PATH,
                    settings=ChromaSettings(anonymized_telemetry=False, allow_reset=True),
                )
                logger.info(f"使用本地Chroma存储: {settings.CHROMA_DB_PATH}")

            # 初始化embedding函数
            self.embedding_function = (
                embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name=settings.EMBEDDING_MODEL_NAME
                )
            )

            # 获取或创建论文集合
            self.paper_collection = self.client.get_or_create_collection(
                name="papers",
                embedding_function=self.embedding_function,
                metadata={"description": "论文向量存储"},
            )

            logger.info("向量存储初始化完成")

        except Exception as e:
            logger.error(f"向量存储初始化失败: {str(e)}")
            raise

    def _is_initialized(self) -> bool:
        """检查集合是否已初始化，未初始化时记录错误日志。"""
        if not self.paper_collection:
            logger.error("向量存储未初始化")
            return False
        return True

    async def add_paper_to_index(self, paper_id: str) -> bool:
        """
        将论文添加到向量索引
        :param paper_id: 论文ID
        :return: 是否成功
        """
        if not self._is_initialized():
            return False

        db = next(get_db())
        paper = db.query(Paper).filter(Paper.paper_id == paper_id).first()

        if not paper:
            logger.error(f"论文不存在: {paper_id}")
            return False

        # 检查是否已存在于索引中
        existing = self.paper_collection.get(ids=[paper_id])
        if existing["ids"]:
            logger.info(f"论文已在索引中: {paper_id}")
            return True

        # 获取解读结果（如果有）
        interpretation = (
            db.query(PaperInterpretation)
            .filter(PaperInterpretation.paper_id == paper_id)
            .first()
        )

        # 构建索引内容
        content_parts = [
            f"标题: {paper.title}",
            f"作者: {', '.join(paper.authors)}",
            f"摘要: {paper.abstract}",
            f"分类: {', '.join(paper.categories)}",
        ]

        if interpretation:
            content_parts.extend(
                [
                    f"核心贡献: {'; '.join(interpretation.core_contributions)}",
                    f"创新点: {'; '.join(interpretation.innovations)}",
                    f"结论: {'; '.join(interpretation.conclusions)}",
                ]
            )

        content = "\n".join(content_parts)

        # 构建元数据
        metadata = {
            "paper_id": paper_id,
            "title": paper.title,
            "authors": json.dumps(paper.authors, ensure_ascii=False),
            "source": paper.source,
            "publication_date": paper.publication_date.isoformat()
            if paper.publication_date
            else "",
            "categories": json.dumps(paper.categories, ensure_ascii=False),
            "citation_count": paper.citation_count,
            "status": paper.status,
        }

        try:
            self.paper_collection.add(
                ids=[paper_id], documents=[content], metadatas=[metadata]
            )

            logger.info(f"论文已添加到向量索引: {paper_id}")
            return True

        except Exception as e:
            logger.error(f"添加论文到索引失败: {str(e)}")
            return False

    async def search_papers(
        self, query: str, limit: int = 10, filter_conditions: Optional[Dict] = None
    ) -> List[Dict]:
        """
        语义搜索论文
        :param query: 查询字符串
        :param limit: 返回结果数量
        :param filter_conditions: 过滤条件，如{"source": "arxiv"}
        :return: 搜索结果列表
        """
        if not self._is_initialized():
            return []

        try:
            results = self.paper_collection.query(
                query_texts=[query],
                n_results=limit,
                where=filter_conditions,
                include=["documents", "metadatas", "distances"],
            )

            papers = [
                _paper_from_metadata(
                    results["ids"][0][i],
                    results["metadatas"][0][i],
                    results["distances"][0][i],
                    snippet=results["documents"][0][i],
                )
                for i in range(len(results["ids"][0]))
            ]

            logger.info(f"搜索完成，找到 {len(papers)} 篇相关论文")
            return papers

        except Exception as e:
            logger.error(f"搜索论文失败: {str(e)}")
            return []

    async def get_similar_papers(self, paper_id: str, limit: int = 10) -> List[Dict]:
        """
        获取相似论文
        :param paper_id: 论文ID
        :param limit: 返回结果数量
        :return: 相似论文列表
        """
        if not self._is_initialized():
            return []

        try:
            # 获取论文的向量
            paper_data = self.paper_collection.get(
                ids=[paper_id], include=["embeddings"]
            )

            if not paper_data["embeddings"]:
                logger.error(f"论文不在索引中: {paper_id}")
                return []

            embedding = paper_data["embeddings"][0]

            # 搜索相似向量
            results = self.paper_collection.query(
                query_embeddings=[embedding],
                n_results=limit + 1,  # +1 排除自己
                include=["metadatas", "distances"],
            )

            papers = []
            for i in range(len(results["ids"][0])):
                result_id = results["ids"][0][i]
                if result_id == paper_id:
                    continue

                papers.append(
                    _paper_from_metadata(
                        result_id,
                        results["metadatas"][0][i],
                        results["distances"][0][i],
                    )
                )
                if len(papers) >= limit:
                    break

            logger.info(f"找到 {len(papers)} 篇相似论文")
            return papers

        except Exception as e:
            logger.error(f"获取相似论文失败: {str(e)}")
            return []

    async def delete_paper_from_index(self, paper_id: str) -> bool:
        """
        从索引中删除论文
        :param paper_id: 论文ID
        :return: 是否成功
        """
        if not self._is_initialized():
            return False

        try:
            self.paper_collection.delete(ids=[paper_id])
            logger.info(f"论文已从索引中删除: {paper_id}")
            return True
        except Exception as e:
            logger.error(f"删除论文索引失败: {str(e)}")
            return False

    def get_index_stats(self) -> Dict:
        """获取索引统计信息"""
        if not self.paper_collection:
            return {"count": 0}

        return {"count": self.paper_collection.count()}


async def get_vector_store() -> VectorStore:
    """创建并初始化向量存储实例，供各接口复用。"""
    vector_store = VectorStore()
    await vector_store.initialize()
    return vector_store
