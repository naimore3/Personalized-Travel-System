import random
import heapq
import string
from typing import List, Dict

# 随机生成美食数据
CUISINES = ['川菜', '粤菜', '湘菜', '鲁菜', '浙菜', '闽菜', '苏菜', '东北菜', '西北菜', '本地小吃']
RESTAURANTS = ['食堂A', '食堂B', '美食广场', '小吃街', '校园餐厅', '风味餐厅', '特色窗口', '美味坊', '美食城', '快餐店']

# 生成模拟美食数据
def generate_food_data(num=50):
    foods = []
    for i in range(num):
        name = f"美食{i+1}" + random.choice(['', '（特色）', '（推荐）', ''])
        cuisine = random.choice(CUISINES)
        restaurant = random.choice(RESTAURANTS)
        popularity = random.randint(50, 100)  # 热度
        rating = round(random.uniform(3.0, 5.0), 1)  # 评分
        distance = round(random.uniform(0.1, 5.0), 2)  # 距离（km）
        foods.append({
            'name': name,
            'cuisine': cuisine,
            'restaurant': restaurant,
            'popularity': popularity,
            'rating': rating,
            'distance': distance
        })
    return foods

# 堆排序获取前N项（不完全排序）
def get_top_n_foods(foods: List[Dict], n: int, sort_key: str, reverse=True):
    if reverse:
        return heapq.nlargest(n, foods, key=lambda x: x[sort_key])
    else:
        return heapq.nsmallest(n, foods, key=lambda x: x[sort_key])

# 简单模糊查找（基于内容）
def fuzzy_search_foods(foods: List[Dict], query: str):
    query = query.lower()
    result = []
    for food in foods:
        if (query in food['name'].lower() or
            query in food['cuisine'].lower() or
            query in food['restaurant'].lower()):
            result.append(food)
    return result

# 菜系过滤
def filter_by_cuisine(foods: List[Dict], cuisine: str):
    if not cuisine:
        return foods
    return [food for food in foods if food['cuisine'] == cuisine]

# 组合查询接口
def search_and_sort_foods(query: str = '', cuisine: str = '', sort_key: str = 'popularity', reverse=True, n=10):
    foods = generate_food_data(50)
    if query:
        foods = fuzzy_search_foods(foods, query)
    if cuisine:
        foods = filter_by_cuisine(foods, cuisine)
    # 距离排序为升序，其它为降序
    if sort_key == 'distance':
        reverse = False
    return get_top_n_foods(foods, n, sort_key, reverse)
