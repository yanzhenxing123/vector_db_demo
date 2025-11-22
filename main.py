"""
主程序入口
演示如何使用文字搜索图片功能
"""
import argparse
import os
from image_indexer import ImageIndexer
from image_searcher import ImageSearcher


def index_images(image_dir: str, persist_dir: str = "./chroma_db"):
    """索引图片目录"""
    print("=" * 50)
    print("开始索引图片...")
    print("=" * 50)
    
    indexer = ImageIndexer(persist_directory=persist_dir)
    indexer.index_images(image_dir)
    
    count = indexer.get_indexed_count()
    print(f"\n索引完成！共索引 {count} 张图片")
    print(f"向量数据库保存在: {persist_dir}")


def search_images(query: str, top_k: int = 5, persist_dir: str = "./chroma_db"):
    """搜索图片"""
    print("=" * 50)
    print(f"搜索: '{query}'")
    print("=" * 50)
    
    searcher = ImageSearcher(persist_directory=persist_dir)
    searcher.search_and_display(query, top_k)


def interactive_search(persist_dir: str = "./chroma_db"):
    """交互式搜索模式"""
    print("=" * 50)
    print("进入交互式搜索模式")
    print("输入 'quit' 或 'exit' 退出")
    print("=" * 50)
    
    searcher = ImageSearcher(persist_directory=persist_dir)
    
    while True:
        query = input("\n请输入搜索关键词: ").strip()
        
        if query.lower() in ['quit', 'exit', 'q']:
            print("退出搜索")
            break
        
        if not query:
            print("请输入有效的搜索关键词")
            continue
        
        try:
            searcher.search_and_display(query, top_k=5)
        except Exception as e:
            print(f"搜索出错: {e}")


def main():
    parser = argparse.ArgumentParser(description="文字搜索图片工具")
    parser.add_argument(
        "mode",
        choices=["index", "search", "interactive"],
        help="运行模式: index(索引图片), search(搜索), interactive(交互式搜索)"
    )
    parser.add_argument(
        "--image_dir",
        type=str,
        default="./images",
        help="图片目录路径 (用于index模式)"
    )
    parser.add_argument(
        "--query",
        type=str,
        help="搜索查询文字 (用于search模式)"
    )
    parser.add_argument(
        "--top_k",
        type=int,
        default=5,
        help="返回最相似的前k张图片 (默认: 5)"
    )
    parser.add_argument(
        "--db_dir",
        type=str,
        default="./chroma_db",
        help="向量数据库目录 (默认: ./chroma_db)"
    )
    
    args = parser.parse_args()
    
    if args.mode == "index":
        if not os.path.exists(args.image_dir):
            print(f"错误: 图片目录 '{args.image_dir}' 不存在")
            return
        index_images(args.image_dir, args.db_dir)
    
    elif args.mode == "search":
        if not args.query:
            print("错误: search模式需要提供 --query 参数")
            return
        search_images(args.query, args.top_k, args.db_dir)
    
    elif args.mode == "interactive":
        interactive_search(args.db_dir)


if __name__ == "__main__":
    main()

