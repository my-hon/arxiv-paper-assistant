#!/usr/bin/env python3
"""arXiv PDF下载测试工具，包含多种下载策略和错误处理。

支持的下载方式：
1. 官方arxiv.py库的download_pdf方法
2. 直接HTTP下载（带重试和代理支持）
3. 镜像站点下载
"""

import os
import random
import ssl
import sys
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import arxiv
import requests
from loguru import logger
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

# 添加项目根目录
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import settings
from modules.crawler.arxiv_client import ArxivClient


@dataclass
class DownloadResult:
    """下载结果"""

    success: bool
    file_path: Optional[str] = None
    method: Optional[str] = None
    error: Optional[str] = None
    time_cost: float = 0.0


class PDFDownloader:
    """增强版PDF下载器"""

    # arXiv镜像站点
    ARXIV_MIRRORS = [
        "https://arxiv.org/pdf/",
        "https://export.arxiv.org/pdf/",
        "https://cn.arxiv.org/pdf/",  # 中国镜像
    ]

    # User-Agent列表，随机选择避免被封
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_2) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    ]

    def __init__(self, save_dir: Optional[str] = None):
        self.save_dir = save_dir or settings.PDF_STORAGE_PATH
        os.makedirs(self.save_dir, exist_ok=True)
        logger.info(f"PDF保存目录: {self.save_dir}")

        # 禁用SSL验证（解决部分网络环境下的SSL错误）
        self._create_ssl_context()

    def _create_ssl_context(self):
        """创建SSL上下文，处理证书问题"""
        try:
            ssl._create_default_https_context = ssl._create_unverified_context
            logger.debug("已禁用SSL证书验证")
        except Exception as e:
            logger.warning(f"禁用SSL验证失败: {e}")

    def _get_random_user_agent(self) -> str:
        """获取随机User-Agent"""
        return random.choice(self.USER_AGENTS)

    def _get_pdf_path(self, arxiv_id: str) -> str:
        """生成PDF保存路径"""
        return os.path.join(self.save_dir, f"arxiv_{arxiv_id}.pdf")

    def download_with_arxiv_lib(self, arxiv_id: str) -> DownloadResult:
        """使用官方arxiv.py库下载"""
        start_time = time.time()
        method = "arxiv_lib"

        try:
            logger.info(f"[{method}] 开始下载: {arxiv_id}")

            # 搜索论文
            client = arxiv.Client(
                delay_seconds=settings.CRAWL_RATE_LIMIT,
                num_retries=settings.CRAWL_MAX_RETRIES,
            )
            search = arxiv.Search(id_list=[arxiv_id], max_results=1)
            results = list(client.results(search))

            if not results:
                return DownloadResult(
                    success=False,
                    method=method,
                    error="未找到论文",
                    time_cost=time.time() - start_time,
                )

            paper = results[0]
            save_path = self._get_pdf_path(arxiv_id)

            # 下载PDF
            downloaded_path = paper.download_pdf(
                dirpath=self.save_dir, filename=os.path.basename(save_path)
            )
            logger.info(f"[{method}] 下载成功: {downloaded_path}")

            return DownloadResult(
                success=True,
                file_path=downloaded_path,
                method=method,
                time_cost=time.time() - start_time,
            )

        except Exception as e:
            error_msg = f"下载失败: {str(e)}"
            logger.error(f"[{method}] {error_msg}")
            return DownloadResult(
                success=False,
                method=method,
                error=error_msg,
                time_cost=time.time() - start_time,
            )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(
            (requests.exceptions.RequestException, ssl.SSLError)
        ),
    )
    def download_with_requests(
        self, arxiv_id: str, mirror_index: int = 0
    ) -> DownloadResult:
        """使用requests库直接下载"""
        start_time = time.time()
        method = f"requests_mirror_{mirror_index}"

        try:
            logger.info(f"[{method}] 开始下载: {arxiv_id}")

            mirror_url = self.ARXIV_MIRRORS[mirror_index % len(self.ARXIV_MIRRORS)]
            pdf_url = f"{mirror_url}{arxiv_id}.pdf"

            headers = {
                "User-Agent": self._get_random_user_agent(),
                "Accept": "application/pdf",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Referer": "https://arxiv.org/",
            }

            proxy = None
            if settings.PROXY_URL:
                proxy = {
                    "http": settings.PROXY_URL,
                    "https": settings.PROXY_URL,
                }
                logger.info(f"使用代理: {settings.PROXY_URL}")

            logger.info(f"下载URL: {pdf_url}")

            response = requests.get(
                pdf_url,
                headers=headers,
                proxies=proxy,
                timeout=30,
                verify=False,  # 禁用SSL验证
                allow_redirects=True,
                stream=True,  # 流式下载
            )

            response.raise_for_status()

            save_path = self._get_pdf_path(arxiv_id)

            # 流式写入文件
            with open(save_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            # 验证文件
            if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
                file_size = os.path.getsize(save_path)
                logger.info(
                    f"[{method}] 下载成功: {save_path}, 大小: {file_size / 1024 / 1024:.2f} MB"
                )

                return DownloadResult(
                    success=True,
                    file_path=save_path,
                    method=method,
                    time_cost=time.time() - start_time,
                )
            else:
                raise Exception("下载的文件为空或不存在")

        except Exception as e:
            error_msg = f"下载失败: {str(e)}"
            logger.error(f"[{method}] {error_msg}")
            return DownloadResult(
                success=False,
                method=method,
                error=error_msg,
                time_cost=time.time() - start_time,
            )

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type((urllib.error.URLError, ssl.SSLError)),
    )
    def download_with_urllib(
        self, arxiv_id: str, mirror_index: int = 0
    ) -> DownloadResult:
        """使用urllib下载（备选方案）"""
        start_time = time.time()
        method = f"urllib_mirror_{mirror_index}"

        try:
            logger.info(f"[{method}] 开始下载: {arxiv_id}")

            mirror_url = self.ARXIV_MIRRORS[mirror_index % len(self.ARXIV_MIRRORS)]
            pdf_url = f"{mirror_url}{arxiv_id}.pdf"

            headers = {
                "User-Agent": self._get_random_user_agent(),
                "Accept": "application/pdf",
            }

            request = urllib.request.Request(pdf_url, headers=headers)

            # 设置代理
            if settings.PROXY_URL:
                proxy_handler = urllib.request.ProxyHandler(
                    {
                        "http": settings.PROXY_URL,
                        "https": settings.PROXY_URL,
                    }
                )
                opener = urllib.request.build_opener(proxy_handler)
                urllib.request.install_opener(opener)
                logger.info(f"使用代理: {settings.PROXY_URL}")

            # 禁用SSL验证
            context = ssl._create_unverified_context()

            with urllib.request.urlopen(
                request, context=context, timeout=30
            ) as response:
                content = response.read()

            save_path = self._get_pdf_path(arxiv_id)
            with open(save_path, "wb") as f:
                f.write(content)

            if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
                file_size = os.path.getsize(save_path)
                logger.info(
                    f"[{method}] 下载成功: {save_path}, 大小: {file_size / 1024 / 1024:.2f} MB"
                )

                return DownloadResult(
                    success=True,
                    file_path=save_path,
                    method=method,
                    time_cost=time.time() - start_time,
                )
            else:
                raise Exception("下载的文件为空或不存在")

        except Exception as e:
            error_msg = f"下载失败: {str(e)}"
            logger.error(f"[{method}] {error_msg}")
            return DownloadResult(
                success=False,
                method=method,
                error=error_msg,
                time_cost=time.time() - start_time,
            )

    def download(self, arxiv_id: str, try_all_mirrors: bool = True) -> DownloadResult:
        """尝试多种方式下载PDF"""
        logger.info(f"开始下载PDF: {arxiv_id}")

        # 检查文件是否已存在
        save_path = self._get_pdf_path(arxiv_id)
        if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
            logger.info(f"PDF已存在，跳过下载: {save_path}")
            return DownloadResult(success=True, file_path=save_path, method="cached")

        # 下载策略列表
        strategies = [
            ("arxiv_lib", lambda: self.download_with_arxiv_lib(arxiv_id)),
            ("requests_mirror_0", lambda: self.download_with_requests(arxiv_id, 0)),
            ("urllib_mirror_0", lambda: self.download_with_urllib(arxiv_id, 0)),
        ]

        if try_all_mirrors:
            # 添加更多镜像站点尝试
            for i in range(1, len(self.ARXIV_MIRRORS)):
                strategies.append(
                    (
                        f"requests_mirror_{i}",
                        lambda idx=i: self.download_with_requests(arxiv_id, idx),
                    )
                )
                strategies.append(
                    (
                        f"urllib_mirror_{i}",
                        lambda idx=i: self.download_with_urllib(arxiv_id, idx),
                    )
                )

        # 尝试各种下载策略
        for strategy_name, strategy_func in strategies:
            logger.info(f"尝试下载策略: {strategy_name}")

            try:
                result = strategy_func()
                if result.success:
                    logger.info(f"使用策略 {strategy_name} 下载成功！")
                    return result
                else:
                    logger.warning(f"策略 {strategy_name} 失败: {result.error}")
            except Exception as e:
                logger.error(f"策略 {strategy_name} 执行异常: {e}")

            # 策略间等待
            time.sleep(random.uniform(1, 3))

        # 所有策略都失败
        logger.error(f"所有下载策略都失败: {arxiv_id}")
        return DownloadResult(success=False, error="所有下载策略都失败")


def test_single_paper_download(arxiv_id: str = "2310.06825") -> Dict:
    """测试单个论文下载"""
    logger.info("=" * 60)
    logger.info(f"测试论文PDF下载: {arxiv_id}")
    logger.info("=" * 60)

    downloader = PDFDownloader()
    result = downloader.download(arxiv_id)

    if result.success:
        logger.info("✅ 下载成功！")
        logger.info(f"保存路径: {result.file_path}")
        logger.info(f"使用方法: {result.method}")
        logger.info(f"耗时: {result.time_cost:.2f} 秒")

        # 验证文件
        file_size = os.path.getsize(result.file_path)
        logger.info(f"文件大小: {file_size / 1024 / 1024:.2f} MB")

        return {
            "success": True,
            "arxiv_id": arxiv_id,
            "file_path": result.file_path,
            "method": result.method,
            "file_size": file_size,
            "time_cost": result.time_cost,
        }
    else:
        logger.error(f"❌ 下载失败: {result.error}")
        return {"success": False, "arxiv_id": arxiv_id, "error": result.error}


def test_batch_download(paper_ids: List[str]) -> List[Dict]:
    """批量下载测试"""
    logger.info("\n" + "=" * 60)
    logger.info(f"批量下载测试，共 {len(paper_ids)} 篇论文")
    logger.info("=" * 60)

    downloader = PDFDownloader()
    results = []

    for i, arxiv_id in enumerate(paper_ids, 1):
        logger.info(f"\n[{i}/{len(paper_ids)}] 处理: {arxiv_id}")
        result = downloader.download(arxiv_id)
        results.append(
            {
                "arxiv_id": arxiv_id,
                "success": result.success,
                "method": result.method,
                "error": result.error,
                "time_cost": result.time_cost,
            }
        )

        # 论文间等待
        if i < len(paper_ids):
            wait_time = random.uniform(2, 5)
            logger.info(f"等待 {wait_time:.1f} 秒后处理下一篇...")
            time.sleep(wait_time)

    # 统计结果
    success_count = sum(1 for r in results if r["success"])
    logger.info("\n" + "=" * 60)
    logger.info(f"批量下载完成: 成功 {success_count}/{len(results)}")
    logger.info("=" * 60)

    for result in results:
        status = "✅" if result["success"] else "❌"
        logger.info(
            f"{status} {result['arxiv_id']}: {result['method'] if result['success'] else result['error']}"
        )

    return results


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="arXiv PDF下载测试工具")
    parser.add_argument("--id", type=str, default="2310.06825", help="要下载的论文ID")
    parser.add_argument("--batch", type=str, nargs="+", help="批量下载的论文ID列表")
    parser.add_argument("--recent", type=int, help="下载最近N篇机器学习论文")

    args = parser.parse_args()

    if args.batch:
        # 批量下载
        test_batch_download(args.batch)
    elif args.recent:
        # 搜索并下载最近的论文
        logger.info(f"搜索最近 {args.recent} 篇机器学习论文...")
        client = ArxivClient()
        papers = client.search_and_save(
            query="machine learning",
            max_results=args.recent,
            categories=["cs.LG"],
            download_pdfs=False,
        )

        if papers:
            paper_ids = [p["arxiv_id"] for p in papers]
            logger.info(f"找到 {len(paper_ids)} 篇论文，开始下载...")
            test_batch_download(paper_ids)
        else:
            logger.error("未找到论文")
    else:
        # 单个下载测试
        test_single_paper_download(args.id)
