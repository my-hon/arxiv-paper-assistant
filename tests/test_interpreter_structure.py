#!/usr/bin/env python3
"""
测试重构后的论文解读模块的数据结构是否正确
"""
import os
import json
from pathlib import Path
import sys

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from modules.interpretation.paper_interpreter import PaperInterpreter

import sys
# 设置输出编码为UTF-8
sys.stdout.reconfigure(encoding='utf-8')

def test_data_structure():
    """测试Pydantic模型结构是否正确"""
    print("=" * 80)
    print("测试论文解读模块数据结构")
    print("=" * 80)

    interpreter = PaperInterpreter()

    # 获取输出格式说明
    format_instructions = interpreter.parser.get_format_instructions()
    print("\n输出格式说明:")
    print(format_instructions)

    # 保存格式说明
    output_dir = project_root / "outputs"
    os.makedirs(output_dir, exist_ok=True)
    with open(output_dir / "interpretation_format.json", "w", encoding="utf-8") as f:
        f.write(format_instructions)
    print("\n格式说明已保存到 outputs/interpretation_format.json")

    # 测试模拟解读结果的结构
    print("\n测试模拟解读结果结构...")
    mock_result = {
        "problem_domain": "自然语言处理，机器翻译领域，深度学习架构改进研究",
        "core_contributions": [
            "提出了Transformer架构，完全基于自注意力机制，摒弃了递归和卷积",
            "在WMT 2014英德翻译任务上达到28.4 BLEU，比现有最优结果提升超过2 BLEU"
        ],
        "innovations": [
            "多头注意力机制：将输入映射到多个子空间计算注意力",
            "位置编码：使用正弦余弦函数为输入添加位置信息"
        ],
        "limitations": [
            "对长序列的处理复杂度是O(n²)，序列太长时计算量过大"
        ],
        "conclusions": [
            "注意力机制可以完全替代递归神经网络构建高性能的序列模型"
        ],
        "technical_approach": "提出了完全基于自注意力机制的序列转换模型，使用编码器解码器架构",
        "method_details": [
            {
                "name": "多头注意力机制",
                "description": "将查询、键、值分别线性投影到h个不同的子空间，在每个子空间计算注意力",
                "implementation_steps": [
                    "对输入进行三次线性变换得到Q, K, V",
                    "将Q, K, V拆分成h个头",
                    "计算缩放点积注意力"
                ],
                "formula": "Attention(Q,K,V) = softmax(\\frac{QK^T}{\\sqrt{d_k}})V"
            }
        ],
        "implementation_notes": [
            "注意力计算时使用缩放因子√d_k避免梯度消失"
        ],
        "code_links": [
            {
                "url": "https://github.com/tensorflow/tensor2tensor",
                "description": "Transformer官方实现",
                "platform": "GitHub"
            }
        ],
        "datasets": [
            {
                "name": "WMT 2014 English-German",
                "source": "https://www.statmt.org/wmt14/translation-task.html",
                "scale": "450万句子对",
                "characteristics": "标准机器翻译数据集"
            }
        ],
        "experimental_setup": [
            "硬件：8个NVIDIA P100 GPU",
            "批量大小：每个GPU 2048个词元的小批量训练"
        ],
        "evaluation_metrics": [
            {
                "name": "BLEU",
                "definition": "双语评估替补，衡量机器翻译结果与人工翻译的相似度",
                "existing_library": "使用sacrebleu库，命令行调用或Python API调用",
                "paper_value": "28.4（英德）"
            }
        ],
        "experimental_results": [
            {
                "metric_name": "BLEU (英德)",
                "value": "28.4",
                "comparison": "比之前最好的集成模型结果26.4高2.0 BLEU",
                "significance": "在统计上具有显著优势，p<0.05"
            }
        ],
        "baseline_comparison": [
            "比基于RNN的seq2seq模型快一个数量级"
        ],
        "key_references": [
            "Sequence to Sequence Learning with Neural Networks (Sutskever et al., 2014)"
        ],
        "confidence_score": 0.95,
        "figure_descriptions": []
    }

    # 测试是否符合Pydantic模型
    try:
        # 直接测试PaperInterpretationResult模型，而不是parser
        from modules.interpretation.paper_interpreter import PaperInterpretationResult
        parsed_result = PaperInterpretationResult(**mock_result)
        print("模拟结果符合数据结构要求")

        # 转换为字典保存
        result_dict = parsed_result.dict()
        with open(output_dir / "sample_interpretation.json", "w", encoding="utf-8") as f:
            json.dump(result_dict, f, ensure_ascii=False, indent=2)
        print("✅ 示例解读结果已保存到 outputs/sample_interpretation.json")

        # 打印主要字段说明
        print("\n📊 主要字段说明:")
        print(f"  问题领域: {result_dict['problem_domain']}")
        print(f"  核心贡献数量: {len(result_dict['core_contributions'])}")
        print(f"  方法细节数量: {len(result_dict['method_details'])}")
        print(f"  代码链接数量: {len(result_dict['code_links'])}")
        print(f"  数据集数量: {len(result_dict['datasets'])}")
        print(f"  评估指标数量: {len(result_dict['evaluation_metrics'])}")
        print(f"  实验结果数量: {len(result_dict['experimental_results'])}")
        print(f"  置信度: {result_dict['confidence_score']:.2f}")

        return True
    except Exception as e:
        print(f"❌ 数据结构验证失败: {str(e)}")
        return False

def test_prompt_templates():
    """测试提示词模板是否正确"""
    print("\n" + "=" * 80)
    print("测试提示词模板")
    print("=" * 80)

    from modules.interpretation.paper_interpreter import SYSTEM_PROMPT, HUMAN_PROMPT_TEMPLATE

    print("🔹 系统提示词长度:", len(SYSTEM_PROMPT))
    print("🔹 用户提示词模板长度:", len(HUMAN_PROMPT_TEMPLATE))

    # 检查是否包含关键指令
    key_instructions = [
        "问题领域与数据集",
        "方法实现与代码链接",
        "实验结果与评价指标",
        "代码链接",
        "评价指标",
        "实现方法"
    ]

    print("\n🔍 检查关键指令是否存在:")
    all_found = True
    for instruction in key_instructions:
        if instruction in SYSTEM_PROMPT:
            print(f"  ✅ {instruction}")
        else:
            print(f"  ❌ {instruction}")
            all_found = False

    # 保存提示词
    output_dir = project_root / "outputs"
    with open(output_dir / "system_prompt.txt", "w", encoding="utf-8") as f:
        f.write(SYSTEM_PROMPT)
    with open(output_dir / "human_prompt_template.txt", "w", encoding="utf-8") as f:
        f.write(HUMAN_PROMPT_TEMPLATE)
    print("\n✅ 提示词已保存到 outputs/system_prompt.txt 和 outputs/human_prompt_template.txt")

    return all_found

if __name__ == "__main__":
    success1 = test_data_structure()
    success2 = test_prompt_templates()

    print("\n" + "=" * 80)
    if success1 and success2:
        print("🎉 所有测试通过！重构后的模块结构正确")
    else:
        print("⚠️ 部分测试未通过，请检查相关问题")
    print("=" * 80)
    sys.exit(0 if success1 and success2 else 1)
