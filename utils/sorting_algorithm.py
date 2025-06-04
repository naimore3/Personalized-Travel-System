import heapq
import zlib

def get_top_ten_places(places):
    """
    从给定的地点列表中找出评分最高的前十个地点
    :param places: 地点列表，每个地点是一个字典，包含 ID, Place_Name, Place_Category, City, Tags, Description, Rating 等字段
    :return: 评分最高的前十个地点列表
    """
    # 定义一个小顶堆
    top_ten = []
    counter = 0  # 添加计数器作为唯一标识符
    
    for place in places:
        rating = place['Rating']  # 使用字典键访问评分
        if len(top_ten) < 10:
            # 如果堆的大小小于 10，直接添加到堆中
            # 使用计数器作为第二个排序键，确保相同评分的情况下比较是确定的
            heapq.heappush(top_ten, (rating, counter, place))
            counter += 1
        else:
            # 如果堆的大小已经达到 10，比较当前地点的评分和堆顶元素的评分
            if rating > top_ten[0][0]:
                # 如果当前地点的评分大于堆顶元素的评分，替换堆顶元素
                heapq.heappop(top_ten)
                heapq.heappush(top_ten, (rating, counter, place))
                counter += 1
    
    # 对堆中的元素按评分从高到低排序
    top_ten.sort(key=lambda x: x[0], reverse=True)
    # 提取地点信息
    result = [place for _, _, place in top_ten]
    return result

def kmp_search(text, pattern):
    """
    使用KMP算法进行字符串匹配
    :param text: 要搜索的文本
    :param pattern: 要匹配的模式
    :return: 是否匹配
    """
    if not text or not pattern:
        return False
    
    # 计算next数组
    def compute_next(pattern):
        next_array = [0] * len(pattern)
        j = 0
        for i in range(1, len(pattern)):
            while j > 0 and pattern[i] != pattern[j]:
                j = next_array[j - 1]
            if pattern[i] == pattern[j]:
                j += 1
            next_array[i] = j
        return next_array
    
    next_array = compute_next(pattern)
    j = 0
    
    # 进行匹配
    for i in range(len(text)):
        while j > 0 and text[i] != pattern[j]:
            j = next_array[j - 1]
        if text[i] == pattern[j]:
            j += 1
        if j == len(pattern):
            return True
    
    return False

def search_text(text, target, search_type='all'):
    """
    文本搜索算法
    :param text: 要搜索的文本
    :param target: 目标文本
    :param search_type: 搜索类型，可选值：'exact'（精确匹配）或 'partial'（部分匹配）
    :return: 是否匹配
    """
    if not text or not target:
        return False
    
    # 转换为小写以进行不区分大小写的搜索
    text = text.lower()
    target = target.lower()
    
    if search_type == 'exact':
        return text == target
    else:  # partial
        return kmp_search(text, target)

def filter_diaries(diaries, search_text, search_type='all'):
    """
    根据搜索条件筛选日记
    :param diaries: 日记列表
    :param search_text: 搜索文本
    :param search_type: 搜索类型，可选值：'place'（地点）、'title'（标题）、'content'（内容）、'all'（所有）
    :return: 筛选后的日记列表
    """
    if not search_text or search_type == 'all':
        return diaries
    
    filtered_diaries = []
    for diary in diaries:
        if search_type == 'place':
            # 从place_id获取地点名称
            place_name = diary.get('place', '')
            if search_text_in_content(search_text, place_name, 'partial'):
                filtered_diaries.append(diary)
        elif search_type == 'title':
            if search_text_in_content(search_text, diary.get('title', ''), 'exact'):
                filtered_diaries.append(diary)
        elif search_type == 'content':
            # 获取日记内容，如果为空则使用空字符串
            content = diary.get('content', '')
            # 记录内容长度，用于监控压缩效果
            print(f"日记ID: {diary.get('id')}, 内容长度: {len(content)}")
            if search_text_in_content(search_text, content, 'partial'):
                filtered_diaries.append(diary)
    
    print(f"搜索类型: {search_type}, 搜索结果数量: {len(filtered_diaries)}")
    return filtered_diaries

# 已经筛选完的日记才放到下面排序
def sort_diaries(diaries, sort_by='views', search_text='', search_type='all'):
    """
    对日记列表进行筛选和排序
    :param diaries: 日记列表
    :param sort_by: 排序依据，可选值：'views'（热度）或 'rating'（评分）
    :param search_text: 搜索文本
    :param search_type: 搜索类型，可选值：'place'（地点）、'title'（标题）、'content'（内容）、'all'（所有）
    :return: 排序后的日记列表
    """
    try:
        if not diaries:
            print("日记列表为空")
            return []
        
        # 首先进行筛选
        filtered_diaries = filter_diaries(diaries, search_text, search_type)
        print(f"筛选后的日记数量: {len(filtered_diaries)}")
        
        # 创建日记列表的副本，避免修改原始数据
        sorted_diaries = filtered_diaries.copy()
        
        # 使用冒泡排序算法
        n = len(sorted_diaries)
        for i in range(n):
            for j in range(0, n - i - 1):
                try:
                    # 获取当前比较的两个日记的评分或浏览量
                    current = float(sorted_diaries[j].get(sort_by, 0) or 0)
                    next_item = float(sorted_diaries[j + 1].get(sort_by, 0) or 0)
                    
                    # 如果当前项小于下一项，则交换位置（降序排序）
                    if current < next_item:
                        sorted_diaries[j], sorted_diaries[j + 1] = sorted_diaries[j + 1], sorted_diaries[j]
                except (ValueError, TypeError) as e:
                    print(f"排序时出错: {e}")
                    # 如果转换失败，使用默认值0
                    current = 0
                    next_item = 0
                    if current < next_item:
                        sorted_diaries[j], sorted_diaries[j + 1] = sorted_diaries[j + 1], sorted_diaries[j]
        
        print(f"排序完成，返回日记数量: {len(sorted_diaries)}")
        return sorted_diaries
    except Exception as e:
        print(f"排序过程中出错: {e}")
        import traceback
        print(traceback.format_exc())
        return []

def search_text_in_content(text, target, search_type='all'):
    """
    文本搜索算法
    :param text: 要搜索的文本
    :param target: 目标文本
    :param search_type: 搜索类型，可选值：'exact'（精确匹配）或 'partial'（部分匹配）
    :return: 是否匹配
    """
    if not text or not target:
        return False
    
    # 转换为小写以进行不区分大小写的搜索
    text = text.lower()
    target = target.lower()
    
    print(f"比较文本: {text}, 目标文本: {target}, 搜索类型: {search_type}")  # 调试信息
    
    if search_type == 'exact':
        return text == target
    else:  # partial
        return kmp_search(target, text)  # 使用KMP算法进行部分匹配