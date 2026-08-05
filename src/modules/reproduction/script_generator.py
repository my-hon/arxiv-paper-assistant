"""
复现脚本生成模块
"""

import json
import os
import uuid
from datetime import datetime
from typing import Dict, Optional

import docker
from docker.errors import DockerException
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from loguru import logger

from src.config.settings import settings
from src.db.database import get_db
from src.db.models import Paper, PaperInterpretation, ReproductionTask


class ScriptGenerator:
    """复现脚本生成器"""

    def __init__(self):
        self.llm = ChatOpenAI(
            model_name=settings.MODEL_NAME,
            openai_api_key=settings.OPENAI_API_KEY,
            openai_api_base=settings.OPENAI_BASE_URL,
            max_tokens=4000,
            temperature=0.1,
        )
        self.docker_client = None
        try:
            self.docker_client = docker.DockerClient(base_url=settings.DOCKER_SOCKET)
            logger.info("Docker客户端连接成功")
        except DockerException as e:
            logger.warning(f"Docker连接失败，复现功能将不可用: {str(e)}")

    async def generate_script(self, paper_id: str) -> Optional[Dict]:
        """
        生成复现脚本
        :param paper_id: 论文ID
        :return: 生成结果
        """
        db = next(get_db())

        # 获取论文和解读结果
        paper = db.query(Paper).filter(Paper.paper_id == paper_id).first()
        if not paper:
            logger.error(f"论文不存在: {paper_id}")
            return None

        interpretation = (
            db.query(PaperInterpretation)
            .filter(PaperInterpretation.paper_id == paper_id)
            .first()
        )

        if not interpretation:
            logger.error(f"论文尚未解读: {paper_id}")
            return None

        # 创建任务ID
        task_id = str(uuid.uuid4())

        # 创建任务目录
        task_dir = os.path.join(settings.SCRIPT_STORAGE_PATH, task_id)
        os.makedirs(task_dir, exist_ok=True)

        try:
            # 构建Prompt
            system_prompt = """
你是一位专业的机器学习/AI实验复现专家，擅长根据论文描述生成可执行的复现代码。
请根据论文的实验方法、数据集、结论等信息，生成完整的可执行Python代码、requirements.txt和Dockerfile。
代码必须能够直接运行，并且包含必要的注释、参数说明和结果输出。
输出必须包含三个部分：Python代码、requirements.txt内容、Dockerfile内容。
使用```python、```requirements、```dockerfile标签分别包裹三个部分。
确保代码是完整的、可运行的，没有遗漏关键部分。
"""

            human_prompt = f"""
请根据以下论文信息生成复现代码：

论文标题: {paper.title}
作者: {", ".join(paper.authors)}
发表日期: {paper.publication_date.strftime("%Y-%m-%d") if paper.publication_date else "未知"}

核心贡献:
{json.dumps(interpretation.core_contributions, indent=2, ensure_ascii=False)}

实验方法:
{json.dumps(interpretation.experimental_methods, indent=2, ensure_ascii=False)}

使用的数据集:
{json.dumps(interpretation.datasets, indent=2, ensure_ascii=False)}

结论:
{json.dumps(interpretation.conclusions, indent=2, ensure_ascii=False)}

创新点:
{json.dumps(interpretation.innovations, indent=2, ensure_ascii=False)}

请生成完整的复现代码，包含：
1. 主Python脚本，实现论文中的核心算法和实验
2. requirements.txt，列出所有依赖包及其版本
3. Dockerfile，用于构建运行环境

代码要求：
- 代码结构清晰，注释详细
- 包含数据加载、模型训练、评估、结果输出的完整流程
- 如果论文中的数据集可以公开获取，包含自动下载代码
- 输出结果要与论文中的报告结果具有可比性
- 包含超参数配置，与论文中提到的一致
- 包含评估指标计算代码
"""

            # 调用大模型生成代码
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt),
            ]

            response = await self.llm.ainvoke(messages)
            response_content = response.content

            # 解析生成的内容
            script_content = self._extract_code_block(response_content, "python")
            requirements_content = self._extract_code_block(
                response_content, "requirements"
            )
            dockerfile_content = self._extract_code_block(
                response_content, "dockerfile"
            )

            if not script_content:
                logger.error("未能提取到Python代码")
                return None

            # 保存文件
            script_path = os.path.join(task_dir, "reproduce.py")
            requirements_path = os.path.join(task_dir, "requirements.txt")
            dockerfile_path = os.path.join(task_dir, "Dockerfile")

            with open(script_path, "w", encoding="utf-8") as f:
                f.write(script_content)

            if requirements_content:
                with open(requirements_path, "w", encoding="utf-8") as f:
                    f.write(requirements_content)

            if dockerfile_content:
                with open(dockerfile_path, "w", encoding="utf-8") as f:
                    f.write(dockerfile_content)

            # 保存任务到数据库
            task = ReproductionTask(
                task_id=task_id,
                paper_id=paper_id,
                status="pending",
                script_path=script_path,
                requirements_path=requirements_path if requirements_content else None,
                dockerfile_path=dockerfile_path if dockerfile_content else None,
            )

            db.add(task)
            db.commit()

            logger.info(f"复现脚本生成完成，任务ID: {task_id}")

            return {
                "task_id": task_id,
                "paper_id": paper_id,
                "script_path": script_path,
                "requirements_path": requirements_path,
                "dockerfile_path": dockerfile_path,
            }

        except Exception as e:
            logger.error(f"生成复现脚本失败: {str(e)}")
            db.rollback()
            return None

    def _extract_code_block(self, content: str, language: str) -> Optional[str]:
        """从响应中提取指定语言的代码块"""
        start_tag = f"```{language}"
        end_tag = "```"

        start_idx = content.find(start_tag)
        if start_idx == -1:
            # 尝试不带语言标记的情况
            start_idx = content.find("```")
            if start_idx == -1:
                return None

        start_idx += len(start_tag) if start_tag in content else 3
        end_idx = content.find(end_tag, start_idx)

        if end_idx == -1:
            return None

        return content[start_idx:end_idx].strip()

    async def run_reproduction(self, task_id: str) -> Optional[Dict]:
        """
        运行复现任务
        :param task_id: 任务ID
        :return: 运行结果
        """
        if not self.docker_client:
            logger.error("Docker不可用，无法运行复现任务")
            return None

        db = next(get_db())
        task = (
            db.query(ReproductionTask)
            .filter(ReproductionTask.task_id == task_id)
            .first()
        )

        if not task:
            logger.error(f"复现任务不存在: {task_id}")
            return None

        if task.status == "running":
            logger.warning(f"任务正在运行中: {task_id}")
            return None

        # 更新任务状态
        task.status = "running"
        db.commit()

        try:
            task_dir = os.path.dirname(task.script_path)

            # 构建Docker镜像
            logger.info(f"构建Docker镜像，任务ID: {task_id}")
            image, build_logs = self.docker_client.images.build(
                path=task_dir, tag=f"reproduce-{task_id}"
            )

            # 运行容器
            logger.info(f"运行复现容器，任务ID: {task_id}")
            container = self.docker_client.containers.run(
                image.id,
                command="python reproduce.py",
                detach=True,
                mem_limit=settings.SANDBOX_MEMORY_LIMIT,
                nano_cpus=int(settings.SANDBOX_CPU_LIMIT * 1e9),
                volumes={task_dir: {"bind": "/app", "mode": "rw"}},
                working_dir="/app",
                # 沙箱加固：运行的是大模型生成的不可信代码，需最小化其权限
                network_disabled=True,
                cap_drop=["ALL"],
                security_opt=["no-new-privileges"],
                pids_limit=512,
            )

            # 等待执行完成
            wait_result = container.wait(timeout=settings.SANDBOX_TIMEOUT)
            logs = container.logs(stdout=True, stderr=True).decode("utf-8")

            # 获取结果
            exit_code = wait_result["StatusCode"]

            # 清理容器
            container.remove()

            # 更新任务状态
            if exit_code == 0:
                task.status = "success"
                logger.info(f"复现任务成功: {task_id}")
            else:
                task.status = "failed"
                task.error_message = f"执行失败，退出码: {exit_code}"
                logger.error(f"复现任务失败: {task_id}, 退出码: {exit_code}")

            task.execution_log = logs
            task.completed_at = datetime.utcnow()

            # 尝试解析结果
            try:
                # 简单的结果提取，假设脚本输出JSON格式的结果
                result_start = logs.find("=== REPRODUCTION RESULT ===")
                result_end = logs.find("=== END RESULT ===")
                if result_start != -1 and result_end != -1:
                    result_json = logs[
                        result_start + len("=== REPRODUCTION RESULT ===") : result_end
                    ].strip()
                    task.result = json.loads(result_json)
            except Exception as e:
                logger.warning(f"解析复现结果失败: {str(e)}")
                task.result = {"raw_output": logs}

            db.commit()

            return {
                "task_id": task_id,
                "status": task.status,
                "exit_code": exit_code,
                "logs": logs,
                "result": task.result,
                "error_message": task.error_message,
            }

        except Exception as e:
            logger.error(f"运行复现任务失败: {str(e)}")
            task.status = "failed"
            task.error_message = str(e)
            db.commit()
            return None
