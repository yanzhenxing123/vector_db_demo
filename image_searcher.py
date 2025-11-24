"""
文字搜索图片模块
使用CLIP模型将文字查询编码为向量，然后在向量数据库中搜索最相似的图片
"""
import torch
from transformers import CLIPProcessor, CLIPModel
import chromadb
from typing import List, Dict
from PIL import Image


class ImageSearcher:
    """图片搜索器，负责根据文字查询搜索图片"""
    
    def __init__(self, model_name: str = "openai/clip-vit-base-patch32",
                 persist_directory: str = "./chroma_db"):
        """
        初始化图片搜索器
        
        Args:
            model_name: CLIP模型名称
            persist_directory: 向量数据库持久化目录
        """
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"使用设备: {self.device}")
        
        # 加载CLIP模型
        print("正在加载CLIP模型...")
        # 优先使用 safetensors 格式，避免 torch.load 安全限制
        try:
            self.model = CLIPModel.from_pretrained(
                model_name,
                use_safetensors=True
            ).to(self.device)
        except Exception:
            # 如果 safetensors 不可用，尝试普通加载（需要 torch >= 2.6）
            self.model = CLIPModel.from_pretrained(model_name).to(self.device)
        self.processor = CLIPProcessor.from_pretrained(model_name)
        self.model.eval()

        
        # 连接Chroma向量数据库（使用PersistentClient确保持久化）
        self.client = chromadb.PersistentClient(path=persist_directory)
        
        # 获取集合
        try:
            self.collection = self.client.get_collection(name="image_vectors")
        except Exception as e:
            raise ValueError(f"向量数据库未初始化，请先运行索引程序。错误: {e}")
    
    def encode_text(self, text: str) -> torch.Tensor:
        """
        将文字查询编码为向量
        
        Args:
            text: 查询文字
            
        Returns:
            文字向量
        """
        inputs = self.processor(text=[text], return_tensors="pt", padding=True).to(self.device)
        
        with torch.no_grad():
            text_features = self.model.get_text_features(**inputs)
            # 归一化向量
            text_features = text_features / text_features.norm(dim=1, keepdim=True)
        
        return text_features.cpu().numpy()[0]
    
    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        根据文字查询搜索最相似的图片
        
        Args:
            query: 文字查询
            top_k: 返回最相似的前k张图片
            
        Returns:
            搜索结果列表，每个结果包含图片路径和相似度分数
        """
        # 将查询文字编码为向量
        query_embedding = self.encode_text(query)
        
        # 在向量数据库中搜索
        results = self.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=top_k
        )
        
        # 格式化结果
        search_results = []
        if results['ids'] and len(results['ids'][0]) > 0:
            for i in range(len(results['ids'][0])):
                result = {
                    'image_path': results['metadatas'][0][i]['path'],
                    'image_id': results['ids'][0][i],
                    'distance': results['distances'][0][i],
                    'similarity': 1 - results['distances'][0][i]  # 余弦距离转相似度
                }
                search_results.append(result)
        
        return search_results
    
    def search_and_display(self, query: str, top_k: int = 5):
        """
        搜索并显示结果
        
        Args:
            query: 文字查询
            top_k: 返回最相似的前k张图片
        """
        results = self.search(query, top_k)
        
        if not results:
            print(f"未找到与 '{query}' 相关的图片")
            return
        
        print(f"\n找到 {len(results)} 张与 '{query}' 相关的图片:\n")
        for i, result in enumerate(results, 1):
            print(f"{i}. {result['image_path']}")
            print(f"   相似度: {result['similarity']:.4f}")
            print()

