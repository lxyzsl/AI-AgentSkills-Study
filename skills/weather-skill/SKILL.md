---
name: weather_query
description: 查询城市实时天气、温度、风力
version: 1.0.0
tags: [weather, api, query]
allowed-tools: [http_fetch, python]
---

# 天气查询技能
## 输入
- city：城市名

## 输出
格式化天气信息

## 执行
调用 scripts/weather.py {city}