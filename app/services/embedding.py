"""本地嵌入模型服务 - 基于 sentence-transformers

模型: shibing624/text2vec-base-chinese (768维)
模型文件缓存在项目目录 D:\\code\\models\\ 下 (cache_folder)
"""
import logging
import os
from typing import List

import numpy as np

logger = logging.getLogger(__name__)

# HuggingFace 国内镜像 (仅在在线下载时使用)
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

# 模型缓存目录: 项目根目录下的 models 文件夹
MODEL_CACHE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "models",
)
MODEL_NAME = "shibing624/text2vec-base-chinese"

_embedding_model = None


def _get_model():
    """懒加载嵌入模型 (单例, 首次调用时加载)"""
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        logger.info(f"Loading embedding model '{MODEL_NAME}' from {MODEL_CACHE_DIR} ...")
        _embedding_model = SentenceTransformer(
            MODEL_NAME,
            cache_folder=MODEL_CACHE_DIR,
            device="cpu",
        )
        logger.info("Embedding model loaded.")
    return _embedding_model


def encode(texts: List[str]) -> List[List[float]]:
    """将一批文本编码为归一化嵌入向量"""
    if not texts:
        return []
    model = _get_model()
    embeddings = model.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=False,
        convert_to_numpy=True,
    )
    return [vec.tolist() for vec in embeddings]


def encode_one(text: str) -> List[float]:
    """编码单条文本"""
    return encode([text])[0]


def encode_query(query: str) -> List[float]:
    """编码查询文本 (与文档使用相同的编码方式)"""
    return encode_one(query)
