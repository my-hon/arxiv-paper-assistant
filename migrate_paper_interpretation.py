#!/usr/bin/env python3
"""
数据库迁移脚本：更新paper_interpretations表添加新字段
运行前请备份数据库
"""

import os
import sys
from sqlalchemy import text
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from db.database import engine, Base
from db.models import PaperInterpretation

def migrate_database():
    print("开始数据库迁移...")

    # 检查数据库连接
    try:
        with engine.connect() as conn:
            # 检查表是否存在
            result = conn.execute(text("""
                SELECT name FROM sqlite_master WHERE type='table' AND name='paper_interpretations'
            """))
            if not result.fetchone():
                print("paper_interpretations表不存在，无需迁移")
                return

            # 检查现有列
            result = conn.execute(text("PRAGMA table_info(paper_interpretations)"))
            existing_columns = [row[1] for row in result.fetchall()]
            print(f"现有列: {existing_columns}")

            # 需要添加的新列
            new_columns = [
                # 核心信息
                ("problem_domain", "TEXT"),

                # 方法实现
                ("technical_approach", "TEXT"),
                ("method_details", "JSON"),
                ("implementation_notes", "JSON"),
                ("code_links", "JSON"),

                # 实验结果
                ("experimental_setup", "JSON"),
                ("evaluation_metrics", "JSON"),
                ("experimental_results", "JSON"),
                ("baseline_comparison", "JSON"),

                # 图表描述
                ("figure_descriptions", "JSON"),
            ]

            # 添加不存在的列
            for col_name, col_type in new_columns:
                if col_name not in existing_columns:
                    print(f"添加列: {col_name} ({col_type})")
                    conn.execute(text(f"ALTER TABLE paper_interpretations ADD COLUMN {col_name} {col_type}"))

            # 检查是否需要删除旧的experimental_methods列
            if "experimental_methods" in existing_columns:
                print("注意：旧的experimental_methods列仍然存在，可手动删除（如果不需要）")

            conn.commit()
            print("数据库迁移完成！")

    except Exception as e:
        print(f"迁移失败: {str(e)}")
        sys.exit(1)

def show_migration_notes():
    print("\n迁移说明：")
    print("1. 新增的字段都允许NULL值，现有数据不会受到影响")
    print("2. 旧的experimental_methods字段已被新的method_details等字段替代")
    print("3. 重新解读已有论文会自动填充新字段")
    print("4. 如果需要删除旧字段，可以手动执行：ALTER TABLE paper_interpretations DROP COLUMN experimental_methods")

if __name__ == "__main__":
    migrate_database()
    show_migration_notes()
