import sys
import requests

def get_weather(city):
    # 替换为真实 API
    return f"{city}：晴，22℃，风力 2 级"

if __name__ == "__main__":
    city = sys.argv[1] if len(sys.argv) > 1 else "北京"
    print(get_weather(city))