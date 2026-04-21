"""
向量存储和语义检索模块
"""

import json
from typing import Any, Dict, List, Optional

from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from loguru import logger

from .arxiv_crawler import PaperInfo
from .config import settings


class VectorStore:
    """向量存储管理器"""

    def __init__(self):
        self.embeddings = OpenAIEmbeddings(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
            model=settings.EMBEDDING_MODEL_NAME,
        )

        self.db = Chroma(
            persist_directory=str(settings.CHROMA_DB_PATH),
            embedding_function=self.embeddings,
            collection_name="papers",
        )

    def add_paper(self, paper: PaperInfo, content: Optional[str] = None) -> str:
        """
        添加论文到向量数据库

        Args:
            paper: 论文信息
            content: 论文全文内容（可选，默认使用摘要）

        Returns:
            文档ID
        """
        # 检查论文是否已存在
        existing = self.db.get(where={"paper_id": paper.paper_id})
        if existing["ids"]:
            logger.info(f"论文已存在于向量库：{paper.paper_id}")
            return existing["ids"][0]

        # 构建文档
        doc = Document(
            page_content=content if content else paper.summary,
            metadata={
                "paper_id": paper.paper_id,
                "title": paper.title,
                "authors": json.dumps(paper.authors),
                "published": paper.published,
                "categories": json.dumps(paper.categories),
                "pdf_url": paper.pdf_url,
            },
        )

        doc_id = self.db.add_documents([doc])[0]
        logger.info(f"论文已添加到向量库：{paper.paper_id}")
        return doc_id

    def add_papers(self, papers: List[PaperInfo]) -> List[str]:
        """批量添加论文"""
        docs = []
        for paper in papers:
            # 检查是否已存在
            existing = self.db.get(where={"paper_id": paper.paper_id})
            if not existing["ids"]:
                doc = Document(
                    page_content=paper.summary,
                    metadata={
                        "paper_id": paper.paper_id,
                        "title": paper.title,
                        "authors": json.dumps(paper.authors),
                        "published": paper.published,
                        "categories": json.dumps(paper.categories),
                        "pdf_url": paper.pdf_url,
                    },
                )
                docs.append(doc)

        if not docs:
            logger.info("所有论文均已存在于向量库")
            return []

        doc_ids = self.db.add_documents(docs)
        logger.info(f"批量添加了 {len(docs)} 篇论文到向量库")
        return doc_ids

    def semantic_search(
        self, query: str, limit: int = 5, threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        语义搜索相似论文

        Args:
            query: 搜索查询
            limit: 返回结果数量
            threshold: 相似度阈值（0-1）

        Returns:
            相似论文列表
        """
        logger.info(f"语义搜索：{query}")

        results = self.db.similarity_search_with_relevance_scores(
            query, k=limit, score_threshold=threshold
        )

        papers = []
        for doc, score in results:
            metadata = doc.metadata
            paper = {
                "paper_id": metadata["paper_id"],
                "title": metadata["title"],
                "authors": json.loads(metadata["authors"]),
                "published": metadata["published"],
                "categories": json.loads(metadata["categories"]),
                "pdf_url": metadata["pdf_url"],
                "similarity_score": float(score),
                "content": doc.page_content,
            }
            papers.append(paper)

        logger.info(f"找到 {len(papers)} 篇相似论文")
        return papers

    def get_similar_papers(
        self, paper_id: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        获取与指定论文相似的论文

        Args:
            paper_id: 论文ID
            limit: 返回结果数量

        Returns:
            相似论文列表
        """
        # 获取论文的向量
        existing = self.db.get(
            where={"paper_id": paper_id},
            include=["embeddings", "documents", "metadatas"],
        )
        if not existing["ids"]:
            logger.error(f"论文不在向量库中：{paper_id}")
            return []

        # 使用论文内容进行搜索
        content = existing["documents"][0]
        return self.semantic_search(content, limit=limit + 1)[1:]  # 排除自己

    def get_paper_count(self) -> int:
        """获取向量库中的论文总数"""
        return self.db._collection.count()

    def delete_paper(self, paper_id: str) -> bool:
        """删除指定论文"""
        try:
            existing = self.db.get(where={"paper_id": paper_id})
            if existing["ids"]:
                self.db.delete(ids=existing["ids"])
                logger.info(f"论文已从向量库删除：{paper_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"删除论文失败：{e}")
            return False


def format_search_results(results: List[Dict[str, Any]]) -> str:
    """格式化搜索结果为输出字符串"""
    if not results:
        return "未找到相关论文"

    output = [f"🔍 语义搜索结果（共 {len(results)} 篇）", "=" * 60]

    for i, paper in enumerate(results, 1):
        score = paper["similarity_score"]
        output.extend(
            [
                f"\n{i}. **{paper['title']}** (arXiv:{paper['paper_id']})",
                f"   🔢 相似度：{score:.4f}",
                f"   👥 作者：{', '.join(paper['authors'][:3])}{'...' if len(paper['authors']) > 3 else ''}",
                f"   📅 发表日期：{paper['published']}",
                f"   🏷️  分类：{', '.join(paper['categories'][:3])}",
                f"   🔗 链接：https://arxiv.org/abs/{paper['paper_id']}",
            ]
        )
        # 显示部分内容
        content = paper["content"][:150].replace("\n", " ")
        if len(paper["content"]) > 150:
            content += "..."
        output.append(f"   📄 摘要：{content}")

    return "\n".join(output)


# 测试代码
if __name__ == "__main__":
    from .arxiv_crawler import ArXivCrawler

    crawler = ArXivCrawler()
    vs = VectorStore()

    # 搜索并添加论文
    papers = crawler.search("large language model", max_results=5)
    vs.add_papers(papers)

    # 测试搜索
    results = vs.semantic_search("chain of thought reasoning")
    print(format_search_results(results))
