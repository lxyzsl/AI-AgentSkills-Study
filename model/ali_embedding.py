from typing import List

from langchain.embeddings.base import Embeddings
import dashscope
from numpy.f2py.auxfuncs import throw_error

from core.config_manager import ConfigManager


class TongYiEmbeddings(Embeddings):
    def __init__(self):
        config = ConfigManager(env="BAI_LIAN")
        self.model = config.get("EmbeddingModel", dtype=str)
        dashscope.base_http_api_url = config.get("DashScopeURL", dtype=str)
        self.api_key = config.get("APIKey", dtype=str)
        dashscope.api_key = self.api_key


    def embed_query(self, text: str) -> list[float]:
        try:
            result =  dashscope.TextEmbedding.call(
                model=self.model,
                input=text,
            )
            if  result["status_code"] != 200:
                throw_error(f"embedding error, status code: {result['status_code']}")
            output= result.output['embeddings'][0]['embedding']
            embeddings = output["embeddings"]
            return embeddings[0]["embedding"]
        except Exception as e:
            print(e)


    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        embeddings =  dashscope.TextEmbedding.call(
            model=self.model,
            input=texts,
        ).output['embeddings']
        embedding_list = [item["embedding"] for item in embeddings]
        return embedding_list


embedding = TongYiEmbeddings()
