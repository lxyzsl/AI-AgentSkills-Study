from langchain_openai import ChatOpenAI

from core.config_manager import ConfigManager

config  = ConfigManager( env="BAI_LIAN")
model = config.get("Model",  dtype=str)
APIKey = config.get("APIKey",  dtype=str)
baseURL = config.get("BaseURL",  dtype=str)

llm = ChatOpenAI(
    model=model,
    base_url=baseURL,
    api_key=APIKey,
    streaming=False,
    verbose=True,
)
