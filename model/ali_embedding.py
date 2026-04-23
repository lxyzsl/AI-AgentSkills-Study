from typing import List

from langchain.embeddings.base import Embeddings
import dashscope

from core.config_manager import ConfigManager


class TongYiEmbeddings(Embeddings):
    def __init__(self):
        config = ConfigManager(env="BAI_LIAN")
        self.model = config.get("EmbeddingModel", dtype=str)
        dashscope.base_http_api_url = config.get("DashScopeURL", dtype=str)
        self.api_key = config.get("APIKey", dtype=str)
        dashscope.api_key = self.api_key


    def embed_query(self, text: str) -> list[float]:
        return dashscope.TextEmbedding.call(
            model=self.model,
            input=text,
        ).output['embeddings'][0]['embedding']

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        embeddings =  dashscope.TextEmbedding.call(
            model=self.model,
            input=texts,
        ).output['embeddings']
        embedding_list = [item["embedding"] for item in embeddings]
        return embedding_list


embedding = TongYiEmbeddings()
