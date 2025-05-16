import heapq

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