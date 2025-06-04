import random
import heapq
import string
import pandas as pd
from typing import List, Dict

# 随机生成美食数据
CUISINES = [
    '川菜', '粤菜', '湘菜', '鲁菜', '浙菜', '闽菜', '苏菜', '东北菜', '西北菜', '本地小吃',
    '徽菜', '豫菜', '赣菜', '晋菜', '清真菜', '藏餐', '新疆菜', '云南菜', '客家菜', '港式茶餐厅',
    '台式小吃', '日料', '韩餐', '东南亚菜', '西餐', '烧烤', '火锅', '自助餐', '素食', '快餐', '甜品饮品'
]
RESTAURANTS = [
    '食堂A', '食堂B', '美食广场', '小吃街', '校园餐厅', '风味餐厅', '特色窗口', '美味坊', '美食城', '快餐店',
    '老字号饭店', '新派餐厅', '家常菜馆', '海鲜酒楼', '烧烤摊', '夜市', '面馆', '米粉店', '饺子馆', '包子铺',
    '西餐厅', '咖啡馆', '甜品屋', '奶茶店', '汉堡店', '披萨店', '寿司店', '拉面馆', '烤肉店', '自助餐厅',
    '清真食堂', '素食餐厅', '港式茶餐厅', '台式便当', '东南亚风味', '新疆大盘鸡', '云南过桥米线', '藏餐馆', '韩式烤肉', '日式料理'
]

# 生成模拟美食数据
def generate_food_data(num=50, place=None):
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
            'distance': distance,
            'place': place if place else ''
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

def get_all_places():
    df = pd.read_excel('../data/places.xlsx')
    # 兼容绝对路径和相对路径
    if df is None or len(df) == 0:
        df = pd.read_excel('data/places.xlsx')
    return df['Place_Name'].dropna().unique().tolist()

# 组合查询接口
def search_and_sort_foods(query: str = '', cuisine: str = '', sort_key: str = 'popularity', reverse=True, n=200, place=None):
    foods = generate_food_data(200, place=place)
    if query:
        foods = fuzzy_search_foods(foods, query)
    if cuisine:
        foods = filter_by_cuisine(foods, cuisine)
    # 距离排序为升序，其它为降序
    if sort_key == 'distance':
        reverse = False
    # 返回全部（最多200个）
    return get_top_n_foods(foods, n=len(foods), sort_key=sort_key, reverse=reverse)
