# 使用示例：搜索论文

## 基本搜索
```bash
paper-assistant search "large language model"
```

输出：
```
📚 搜索结果（共 10 篇）
==================================================

1. **Large Language Models: A Survey** (arXiv:2401.00001)
   👥 作者：Alice Smith, Bob Johnson, Charlie Davis...
   📅 发表日期：2024-01-01
   🏷️  分类：cs.CL, cs.AI
   🔗 链接：https://arxiv.org/abs/2401.00001
   📄 摘要：This survey provides a comprehensive overview of large language models, covering their history, architecture, training methods, applications, and future directions...

2. **Efficient Large Language Model Inference** (arXiv:2312.99999)
   👥 作者：David Wilson, Emma Brown, Frank Miller...
   📅 发表日期：2023-12-31
   🏷️  分类：cs.CL, cs.LG
   🔗 链接：https://arxiv.org/abs/2312.99999
   📄 摘要：Large language models have achieved remarkable performance across various tasks, but their high computational cost remains a major barrier to deployment...
...
```

## 指定分类搜索
```bash
paper-assistant search "diffusion model" --categories cs.CV,eess.IV
```

## 限制结果数量
```bash
paper-assistant search "reinforcement learning" --max-results 5
```

## 搜索并保存到向量库
```bash
paper-assistant search "3d reconstruction" --save
```
输出尾部会显示：
```
✅ 已将 10 篇论文保存到向量数据库
```

## 高级搜索语法
arXiv支持高级搜索语法：

```bash
# 按作者搜索
paper-assistant search "au:Yann LeCun"

# 按标题搜索
paper-assistant search "ti:\"attention is all you need\""

# 按发表时间搜索
paper-assistant search "submittedDate:[20230101 TO 20231231] AND large language model"

# 组合搜索
paper-assistant search "cat:cs.CL AND (llm OR \"large language model\") AND submittedDate:[20230601 TO *]"
```

更多搜索语法请参考 [arXiv API文档](https://info.arxiv.org/help/api/user-manual.html#query_details)。
