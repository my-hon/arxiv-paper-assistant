#!/usr/bin/env python3
"""
初始化数据库，创建所有表
"""
from db.database import Base, engine
from db.models import Paper, PaperInterpretation, ReproductionTask, KnowledgeGraph, GraphRelation

def init_database():
    print("开始初始化数据库...")
    # 创建所有表
    Base.metadata.create_all(bind=engine)
    print("数据库表创建完成！")

    # 检查表是否创建成功
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"已创建的表: {tables}")

if __name__ == "__main__":
    init_database()
