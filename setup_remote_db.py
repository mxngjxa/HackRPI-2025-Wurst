#!/usr/bin/env python3
"""
远程数据库配置助手

帮助配置连接到远程 PostgreSQL 数据库
"""

import os
import sys
from urllib.parse import quote_plus


def print_header(text):
    """打印标题"""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def get_input(prompt, default=None):
    """获取用户输入"""
    if default:
        prompt = f"{prompt} [{default}]: "
    else:
        prompt = f"{prompt}: "
    
    value = input(prompt).strip()
    return value if value else default


def url_encode_password(password):
    """URL 编码密码中的特殊字符"""
    return quote_plus(password)


def test_connection(connection_string):
    """测试数据库连接"""
    print("\n🔍 测试数据库连接...")
    
    try:
        from backend.db import get_engine
        from sqlalchemy import text
        
        # 临时设置环境变量
        os.environ['DATABASE_URL'] = connection_string
        
        engine = get_engine()
        with engine.connect() as conn:
            result = conn.execute(text('SELECT 1'))
            print("✅ 数据库连接成功！")
            
            # 检查 pgvector 扩展
            result = conn.execute(text(
                "SELECT * FROM pg_extension WHERE extname = 'vector'"
            ))
            if result.fetchone():
                print("✅ pgvector 扩展已安装")
            else:
                print("⚠️  警告: pgvector 扩展未安装")
                print("   请联系数据库管理员安装 pgvector")
            
            # 检查表
            result = conn.execute(text(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
            ))
            tables = [row[0] for row in result.fetchall()]
            
            if 'documents' in tables and 'document_chunks' in tables:
                print("✅ 数据库表已存在")
            else:
                print("⚠️  警告: 数据库表不存在")
                print("   需要运行: python -c \"from backend.db import init_db; init_db()\"")
            
            return True
            
    except Exception as e:
        print(f"❌ 连接失败: {str(e)}")
        return False


def main():
    """主函数"""
    print_header("远程 PostgreSQL 数据库配置助手")
    
    print("\n请输入数据库连接信息：")
    print("（如果不确定，请咨询管理数据库的小组成员）\n")
    
    # 获取连接信息
    host = get_input("主机地址 (例如: 192.168.1.100 或 db.example.com)")
    if not host:
        print("❌ 主机地址不能为空")
        sys.exit(1)
    
    port = get_input("端口", "5432")
    database = get_input("数据库名", "llm_chatbot")
    username = get_input("用户名")
    if not username:
        print("❌ 用户名不能为空")
        sys.exit(1)
    
    password = get_input("密码")
    if not password:
        print("❌ 密码不能为空")
        sys.exit(1)
    
    # URL 编码密码
    encoded_password = url_encode_password(password)
    
    # 构建连接字符串
    connection_string = f"postgresql://{username}:{encoded_password}@{host}:{port}/{database}"
    
    print_header("连接信息摘要")
    print(f"主机: {host}")
    print(f"端口: {port}")
    print(f"数据库: {database}")
    print(f"用户名: {username}")
    print(f"密码: {'*' * len(password)}")
    
    # 询问是否测试连接
    print("\n是否测试连接？(y/n): ", end="")
    if input().strip().lower() == 'y':
        if not test_connection(connection_string):
            print("\n❌ 连接测试失败")
            print("请检查：")
            print("  1. 网络连接是否正常")
            print("  2. 主机地址和端口是否正确")
            print("  3. 用户名和密码是否正确")
            print("  4. 防火墙是否允许连接")
            print("  5. 数据库是否允许远程连接")
            print("\n是否仍要保存配置？(y/n): ", end="")
            if input().strip().lower() != 'y':
                print("配置已取消")
                sys.exit(1)
    
    # 更新 .env 文件
    print_header("更新配置文件")
    
    env_file = '.env'
    if not os.path.exists(env_file):
        print(f"❌ 错误: {env_file} 文件不存在")
        sys.exit(1)
    
    # 读取现有配置
    with open(env_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 更新 DATABASE_URL
    updated = False
    for i, line in enumerate(lines):
        if line.startswith('DATABASE_URL='):
            lines[i] = f'DATABASE_URL={connection_string}\n'
            updated = True
            break
    
    if not updated:
        print("❌ 错误: 在 .env 文件中找不到 DATABASE_URL")
        sys.exit(1)
    
    # 写回文件
    with open(env_file, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print(f"✅ 已更新 {env_file}")
    
    print_header("配置完成")
    print("\n✅ 数据库配置已更新！")
    print("\n下一步：")
    print("  1. 如果表不存在，运行：")
    print("     python -c \"from backend.db import init_db; init_db()\"")
    print("\n  2. 启动应用：")
    print("     python app.py")
    print("\n  3. 访问：")
    print("     http://127.0.0.1:7860")
    
    print("\n📚 更多信息请查看：")
    print("  - REMOTE_DATABASE_SETUP.md")
    print("  - README.md")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  配置已取消")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 错误: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
