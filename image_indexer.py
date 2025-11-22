"""
图片向量化和索引模块
使用CLIP模型将图片编码为向量，并存储到向量数据库中
"""
import os
import torch
from PIL import Image
from transformers import CLIPProcessor, CLIPModel
import chromadb
from tqdm import tqdm
from typing import List, Optional


class ImageIndexer:
    """图片索引器，负责将图片编码为向量并存储"""
    
    def __init__(self, model_name: str = "openai/clip-vit-base-patch32", 
                 persist_directory: str = "./chroma_db"):
        """
        初始化图片索引器
        
        Args:
            model_name: CLIP模型名称
            persist_directory: 向量数据库持久化目录
        """
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"使用设备: {self.device}")
        
        # 加载CLIP模型
        print("正在加载CLIP模型...")
        # 使用 use_safetensors=True 避免 torch.load 安全限制
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
        
        # 初始化Chroma向量数据库（使用PersistentClient确保持久化）
        self.client = chromadb.PersistentClient(path=persist_directory)
        
        # 获取或创建集合
        self.collection = self.client.get_or_create_collection(
            name="image_vectors",
            metadata={"hnsw:space": "cosine"}
        )
        
    def encode_image(self, image_path: str) -> torch.Tensor:
        """
        将单张图片编码为向量
        
        Args:
            image_path: 图片路径
            
        Returns:
            图片向量
        """
        try:
            image = Image.open(image_path).convert("RGB")
            inputs = self.processor(images=image, return_tensors="pt").to(self.device)
            
            with torch.no_grad():
                image_features = self.model.get_image_features(**inputs)
                # 归一化向量
                image_features = image_features / image_features.norm(dim=1, keepdim=True)
            
            return image_features.cpu().numpy()[0]
        except Exception as e:
            print(f"处理图片 {image_path} 时出错: {e}")
            return None
    
    def index_images(self, image_dir: str, batch_size: int = 32):
        """
        批量索引图片目录中的所有图片
        
        Args:
            image_dir: 图片目录路径
            batch_size: 批处理大小
        """
        # 获取所有图片文件
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp'}
        image_files = []
        
        for root, dirs, files in os.walk(image_dir):
            for file in files:
                if any(file.lower().endswith(ext) for ext in image_extensions):
                    image_files.append(os.path.join(root, file))
        
        if not image_files:
            print(f"在 {image_dir} 中未找到图片文件")
            return
        
        print(f"找到 {len(image_files)} 张图片，开始索引...")
        
        # 检查已存在的图片
        existing_ids = set(self.collection.get()['ids'])
        new_images = [img for img in image_files 
                     if os.path.basename(img) not in existing_ids]
        
        if not new_images:
            print("所有图片已索引，无需重复处理")
            return
        
        print(f"新增 {len(new_images)} 张图片需要索引")
        
        # 批量处理
        embeddings = []
        ids = []
        metadatas = []
        
        for image_path in tqdm(new_images, desc="索引图片"):
            embedding = self.encode_image(image_path)
            if embedding is not None:
                embeddings.append(embedding.tolist())
                ids.append(os.path.basename(image_path))
                metadatas.append({"path": image_path})
        
        # 批量添加到数据库
        if embeddings:
            self.collection.add(
                embeddings=embeddings,
                ids=ids,
                metadatas=metadatas
            )
            print(f"成功索引 {len(embeddings)} 张图片")
    
    def get_indexed_count(self) -> int:
        """获取已索引的图片数量"""
        return self.collection.count()

