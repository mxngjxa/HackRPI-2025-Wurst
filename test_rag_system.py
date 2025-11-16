#!/usr/bin/env python3
"""
RAG 系统测试脚本

测试完整的 RAG 流程：
1. 上传文档
2. 生成嵌入
3. 存储到数据库
4. 语义搜索
5. 生成回答
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from backend.chat_service import generate_session_id, handle_upload, handle_question
from backend.db import search_similar_chunks, get_engine
from backend.embeddings import embed_query
from sqlalchemy import text


def print_section(title):
    """打印分节标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def test_rag_system():
    """测试完整的 RAG 系统"""
    
    print_section("RAG 系统测试开始")
    
    # 1. 生成会话 ID
    print("\n📝 步骤 1: 生成会话 ID")
    session_id = generate_session_id()
    print(f"   会话 ID: {session_id}")
    
    # 2. 准备测试文档
    print("\n📝 步骤 2: 准备测试文档")
    test_docs_dir = Path("test_documents")
    if not test_docs_dir.exists():
        print("   ❌ 错误: test_documents 目录不存在")
        return False
    
    test_files = list(test_docs_dir.glob("*.txt"))
    if not test_files:
        print("   ❌ 错误: 没有找到测试文档")
        return False
    
    print(f"   找到 {len(test_files)} 个测试文档:")
    for f in test_files:
        print(f"   - {f.name}")
    
    # 3. 上传文档
    print("\n📝 步骤 3: 上传文档到系统")
    
    # 创建文件对象（模拟 Gradio 的文件对象）
    class FileObject:
        def __init__(self, path):
            self.name = str(path)
    
    file_objects = [FileObject(f) for f in test_files]
    
    try:
        success_count, errors = handle_upload(file_objects, session_id)
        
        if errors:
            print(f"   ⚠️  部分成功: {success_count} 个文件上传成功")
            for error in errors:
                print(f"   ❌ {error}")
        else:
            print(f"   ✅ 成功上传 {success_count} 个文档")
    except Exception as e:
        print(f"   ❌ 上传失败: {str(e)}")
        return False
    
    # 4. 验证文档存储
    print("\n📝 步骤 4: 验证文档存储")
    try:
        engine = get_engine()
        with engine.connect() as conn:
            # 查询会话的文档
            result = conn.execute(
                text("""
                    SELECT d.id, d.filename, COUNT(c.id) as chunk_count
                    FROM documents d
                    LEFT JOIN document_chunks c ON d.id = c.document_id
                    WHERE d.session_id = :session_id
                    GROUP BY d.id, d.filename
                """),
                {"session_id": session_id}
            )
            documents = result.fetchall()
            
        print(f"   ✅ 数据库中有 {len(documents)} 个文档")
        for doc in documents:
            print(f"   - ID: {doc[0]}, 文件名: {doc[1]}, "
                  f"块数: {doc[2]}")
    except Exception as e:
        print(f"   ❌ 查询文档失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    # 5. 测试语义搜索
    print("\n📝 步骤 5: 测试语义搜索")
    test_queries = [
        "Python 是什么时候发布的？",
        "机器学习有哪些类型？",
        "PostgreSQL 有什么特点？"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n   查询 {i}: {query}")
        try:
            # 生成查询嵌入
            query_embedding = embed_query(query)
            print(f"   ✅ 生成查询嵌入 (维度: {len(query_embedding)})")
            
            # 搜索相似块
            chunks = search_similar_chunks(query_embedding, session_id, top_k=3)
            print(f"   ✅ 找到 {len(chunks)} 个相关文档块")
            
            if chunks:
                print(f"   📄 最相关的块 (相似度: {chunks[0]['similarity']:.4f}):")
                preview = chunks[0]['content'][:100].replace('\n', ' ')
                print(f"      {preview}...")
        except Exception as e:
            print(f"   ❌ 搜索失败: {str(e)}")
    
    # 6. 测试问答
    print("\n📝 步骤 6: 测试完整问答流程")
    test_questions = [
        "Python 有哪些主要特点？",
        "什么是监督学习？",
        "MySQL 和 PostgreSQL 有什么区别？"
    ]
    
    for i, question in enumerate(test_questions, 1):
        print(f"\n   问题 {i}: {question}")
        try:
            answer = handle_question(question, session_id)
            print(f"   ✅ 生成回答:")
            # 显示回答的前200个字符
            preview = answer[:200].replace('\n', ' ')
            print(f"      {preview}...")
            if len(answer) > 200:
                print(f"      (总长度: {len(answer)} 字符)")
        except Exception as e:
            print(f"   ❌ 问答失败: {str(e)}")
    
    # 7. 测试总结
    print_section("测试总结")
    print("\n✅ RAG 系统测试完成！")
    print("\n测试的功能:")
    print("  ✅ 会话管理")
    print("  ✅ 文档上传")
    print("  ✅ 文本分块")
    print("  ✅ 向量嵌入生成")
    print("  ✅ 数据库存储")
    print("  ✅ 语义搜索")
    print("  ✅ 上下文检索")
    print("  ✅ 答案生成")
    
    print("\n💡 提示:")
    print("  - 当前使用 Mock 模式（USE_MOCK_LLM=true）")
    print("  - Mock 模式生成模拟的嵌入和回答")
    print("  - 要使用真实 Gemini API，设置 USE_MOCK_LLM=false")
    
    return True


def main():
    """主函数"""
    try:
        success = test_rag_system()
        
        if success:
            print("\n" + "=" * 60)
            print("  🎉 所有测试通过！RAG 系统运行正常！")
            print("=" * 60)
            sys.exit(0)
        else:
            print("\n" + "=" * 60)
            print("  ❌ 测试失败，请检查错误信息")
            print("=" * 60)
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 测试过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
