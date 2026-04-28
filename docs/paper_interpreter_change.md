# paper_interpreter.py 修改记录

## 2024-04-21 功能增强：PDF图片提取和Markdown报告生成

### 修改内容：

1. **导入依赖更新**
   - 添加 `from pathlib import Path`
   - 添加 `from PIL import Image`
   - 添加 `from typing import List, Tuple`

2. **新增图片提取功能**
   - 实现 `extract_images_from_pdf()` 方法
   - 支持从PDF中提取所有图片并保存到本地目录
   - 自动创建图片保存目录：`storage/papers/{paper_id}/images/`
   - 验证图片有效性，跳过损坏图片
   - 返回图片信息列表，包含路径、页码、大小等信息

3. **数据模型更新**
   - 在 `PaperInterpretationResult` 类中新增 `figure_descriptions` 字段
   - 类型为 `list[Dict]`，用于存储论文中图表的描述信息

4. **提示词优化**
   - 更新系统提示词，要求模型特别注意论文中的图表说明
   - 要求在 `figure_descriptions` 字段中记录每个图表的位置和内容描述

5. **解读流程增强**
   - 在全文解读模式下自动提取PDF中的图片
   - 新增图片提取步骤，在解读完成后执行

6. **新增Markdown报告生成功能**
   - 实现 `generate_markdown_report()` 方法
   - 生成完整的结构化Markdown解读报告
   - 自动将提取的图片插入到报告对应位置
   - 报告包含：基本信息、核心贡献、创新点、实验方法、数据集、结论、局限性、图表说明、参考文献等部分
   - 图片使用相对路径引用，方便查看和分享

7. **返回结果扩展**
   - 在返回结果中新增 `markdown_path` 字段，指向生成的Markdown文件路径
   - 新增 `extracted_images` 字段，返回提取的图片数量

8. **数据库存储更新**
   - 在 `PaperInterpretation` 模型存储中新增 `figure_descriptions` 字段
   - 保存图表描述信息到数据库

### 效果说明：
- 解读论文时自动提取所有图片并保存
- 生成的Markdown报告包含完整的论文解读内容和所有图片
- 图片按照论文中的顺序插入到对应位置
- 报告保存在 `storage/papers/{paper_id}/interpretation.md`
- 图片保存在 `storage/papers/{paper_id}/images/` 目录
- 无需手动处理图片，解读完成后直接查看完整报告

### 依赖更新：
- 新增依赖 `Pillow` 用于图片处理，需要执行 `pip install pillow` 安装
