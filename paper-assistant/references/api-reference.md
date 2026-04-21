# API参考文档

## 核心类和方法

### ArXivCrawler 类
arXiv论文爬取客户端。

#### 方法
```python
def search(query: str, max_results: int = 10, categories: Optional[List[str]] = None) -> List[PaperInfo]
```
搜索arXiv论文。
- `query`: 搜索关键词
- `max_results`: 返回结果数量，默认10
- `categories`: 分类过滤列表，如["cs.CL", "cs.AI"]
- 返回: PaperInfo对象列表

```python
def get_paper_by_id(paper_id: str) -> Optional[PaperInfo]
```
根据ID获取论文信息。
- `paper_id`: arXiv论文ID，如"2310.06825"
- 返回: PaperInfo对象，不存在则返回None

```python
async def download_pdf(paper_id: str, save_path: Optional[Path] = None) -> Optional[Path]
```
下载论文PDF。
- `paper_id`: arXiv论文ID
- `save_path`: 保存路径，默认使用配置的STORAGE_PATH
- 返回: 下载后的文件路径，失败则返回None

---

### PaperInterpreter 类
论文结构化解读器。

#### 方法
```python
def extract_text_from_pdf(pdf_path: Path) -> str
```
从PDF文件提取文本内容。
- `pdf_path`: PDF文件路径
- 返回: 提取的文本字符串

```python
async def interpret_paper(paper: PaperInfo, pdf_path: Optional[Path] = None, full_interpret: bool = False) -> Dict[str, Any]
```
解读论文，返回结构化信息。
- `paper`: PaperInfo对象
- `pdf_path`: PDF文件路径（可选）
- `full_interpret`: 是否使用全文解读，默认False（仅用摘要）
- 返回: 包含解读结果的字典

---

### VectorStore 类
向量存储和语义检索管理器。

#### 方法
```python
def add_paper(paper: PaperInfo, content: Optional[str] = None) -> str
```
添加单篇论文到向量数据库。
- `paper`: PaperInfo对象
- `content`: 论文全文内容（可选）
- 返回: 文档ID

```python
def add_papers(papers: List[PaperInfo]) -> List[str]
```
批量添加论文到向量数据库。
- `papers`: PaperInfo对象列表
- 返回: 文档ID列表

```python
def semantic_search(query: str, limit: int = 5, threshold: float = 0.7) -> List[Dict[str, Any]]
```
语义搜索相似论文。
- `query`: 搜索文本
- `limit`: 返回结果数量，默认5
- `threshold`: 相似度阈值（0-1），默认0.7
- 返回: 相似论文列表，包含相似度分数

```python
def get_similar_papers(paper_id: str, limit: int = 10) -> List[Dict[str, Any]]
```
获取与指定论文相似的论文。
- `paper_id`: 论文ID
- `limit`: 返回结果数量，默认10
- 返回: 相似论文列表

```python
def get_paper_count() -> int
```
获取向量库中的论文总数。

```python
def delete_paper(paper_id: str) -> bool
```
从向量库删除指定论文。
- `paper_id`: 论文ID
- 返回: 删除成功返回True，否则False

---

### ReproductionGenerator 类
复现代码生成器。

#### 方法
```python
async def generate_code(paper: PaperInfo, content: Optional[str] = None) -> Dict[str, Any]
```
生成论文复现代码。
- `paper`: PaperInfo对象
- `content`: 论文方法部分内容（可选）
- 返回: 包含代码、依赖、Dockerfile等信息的字典

```python
def save_to_files(paper_id: str, code_data: Dict[str, Any]) -> Path
```
将生成的代码保存到文件。
- `paper_id`: 论文ID
- `code_data`: generate_code返回的代码数据
- 返回: 保存目录路径

---

## 数据模型

### PaperInfo 数据类
```python
@dataclass
class PaperInfo:
    paper_id: str          # 论文ID
    title: str             # 标题
    authors: List[str]     # 作者列表
    summary: str           # 摘要
    published: str         # 发表日期（YYYY-MM-DD）
    categories: List[str]  # 分类列表
    pdf_url: str           # PDF下载链接
    entry_id: str          # arXiv条目ID
```

### PaperInterpretation 模型
```python
class PaperInterpretation(BaseModel):
    core_contributions: List[str]   # 核心贡献
    research_methods: List[str]     # 研究方法
    datasets: List[str]             # 使用的数据集
    evaluation_metrics: List[str]   # 评估指标
    main_results: List[str]         # 主要结果
    limitations: List[str]          # 局限性
    future_work: List[str]          # 未来工作
```

### ReproductionCode 模型
```python
class ReproductionCode(BaseModel):
    main_code: str          # 主Python代码
    requirements: List[str] # 依赖包列表
    dockerfile: str         # Dockerfile内容
    readme: str             # 使用说明
    expected_output: str    # 预期输出说明
```

---

## 错误处理

### 常见错误码
| 错误码 | 说明 | 解决方案 |
|--------|------|----------|
| 1 | 配置错误 | 检查API密钥是否正确配置 |
| 2 | 网络错误 | 检查网络连接和API地址配置 |
| 3 | 论文不存在 | 确认论文ID是否正确 |
| 4 | PDF下载失败 | 检查网络连接或手动下载PDF |
| 5 | 大模型调用失败 | 检查API配额和模型可用性 |

### 异常类
- `ConfigurationError`: 配置错误
- `CrawlerError`: 爬取失败
- `PDFParseError`: PDF解析失败
- `InterpretationError`: 论文解读失败
- `GenerationError`: 代码生成失败

---

## 扩展开发

### 添加新的数据源
1. 在 `scripts/crawlers/` 目录下创建新的爬虫类
2. 实现 `search()` 和 `download_pdf()` 方法
3. 在CLI中添加对应的命令支持

### 自定义输出格式
1. 在 `scripts/formatters/` 目录下创建新的格式化器
2. 实现对应的格式化方法
3. 在CLI的output参数中添加新的格式选项

### 扩展解读字段
1. 修改 `PaperInterpretation` 模型添加新字段
2. 更新SKILL.md中的提示模板
3. 调整输出格式化方法
