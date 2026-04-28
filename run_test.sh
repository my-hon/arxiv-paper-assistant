#!/bin/bash
echo "========================================"
echo "论文解读完整流程测试"
echo "========================================"

echo ""
echo "检查outputs目录..."
mkdir -p outputs

echo ""
echo "运行测试脚本..."
python tests/test_full_pipeline.py

echo ""
echo "测试完成！请查看 outputs 目录下的结果。"
