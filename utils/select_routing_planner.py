from typing import List, Dict, Tuple
import heapq

def dijkstra_full(graph: Dict[int, Dict[int, Dict]], start: int, mode: str) -> Tuple[Dict[int, float], Dict[int, int]]:
    """
    Dijkstra算法，返回所有点的最短距离和前驱。
    :param graph: 图结构
    :param start: 起始点
    :param mode: 'distance' 或 'time'，表示使用距离还是时间作为权重
    :return: (距离字典, 前驱字典)
    """
    dist = {node: float('inf') for node in graph}
    prev = {node: None for node in graph}
    dist[start] = 0
    heap = [(0, start)]
    while heap:
        cost, u = heapq.heappop(heap)
        if cost > dist[u]:
            continue
        for v, props in graph[u].items():
            weight = props['distance'] if mode == 'distance' else props['time']
            if dist[v] > dist[u] + weight:
                dist[v] = dist[u] + weight
                prev[v] = u
                heapq.heappush(heap, (dist[v], v))
    return dist, prev

def reconstruct_path(prev: Dict[int, int], end: int) -> List[int]:
    path = []
    while end is not None:
        path.append(end)
        end = prev[end]
    return path[::-1]

def plan_route(pois: List[Dict], edges: List[Dict], mode: str = 'distance') -> List[Dict]:
    """
    规划经过所有必经点的最短路径，自动补全中间途径点。
    起点和终点必须相同（回路）。
    :param pois: [{'id': int, ...}, ...] 必经点
    :param edges: [{'from': int, 'to': int, 'distance': float, 'time': float, 'source': Dict, 'target': Dict}, ...]
    :param mode: 'distance' 或 'time'，表示使用距离还是时间作为权重
    :return: 按顺序排列的POI列表，含is_via字段
    """
    if not pois:
        return []

    # 保证起点和终点一致（回路）
    pois = list(pois)  # 拷贝，避免副作用
    if len(pois) > 1 and pois[0]['id'] != pois[-1]['id']:
        pois.append(pois[0])

    # 构建图
    all_ids = set()
    for edge in edges:
        all_ids.add(edge['from'])
        all_ids.add(edge['to'])
    graph = {nid: {} for nid in all_ids}
    for edge in edges:
        # 获取最短时间作为边的权重
        times = edge.get('times', {})
        min_time = float('inf')
        for time in times.values():
            min_time = min(min_time, time)
        if min_time == float('inf'):
            min_time = edge['distance'] / (5000/60)  # 默认步行时间
        
        graph[edge['from']][edge['to']] = {
            'distance': edge['distance'],
            'time': min_time
        }
        graph[edge['to']][edge['from']] = {
            'distance': edge['distance'],
            'time': min_time
        }

    # 构建所有点的信息映射
    all_points_info = {}
    # 首先添加用户选择的POI
    for poi in pois:
        all_points_info[poi['id']] = poi

    # 然后从边的信息中补充其他点
    for edge in edges:
        # 添加源点信息
        if edge['from'] not in all_points_info and 'source' in edge:
            all_points_info[edge['from']] = {
                'id': edge['from'],
                'name': edge['source'].get('name', f'途经点 {edge["from"]}'),
                'address': edge['source'].get('address', '自动生成的途经点'),
                'location': edge['source'].get('location', {'lng': 0, 'lat': 0})
            }
        
        # 添加目标点信息
        if edge['to'] not in all_points_info and 'target' in edge:
            all_points_info[edge['to']] = {
                'id': edge['to'],
                'name': edge['target'].get('name', f'途经点 {edge["to"]}'),
                'address': edge['target'].get('address', '自动生成的途经点'),
                'location': edge['target'].get('location', {'lng': 0, 'lat': 0})
            }

    must_ids = [poi['id'] for poi in pois]
    id2poi = {poi['id']: poi for poi in pois}

    # 1. 计算所有必经点两两之间的最短路径
    shortest = {}
    paths = {}
    for i in must_ids:
        dist, prev = dijkstra_full(graph, i, mode)
        for j in must_ids:
            if i != j:
                shortest[(i, j)] = dist[j]
                paths[(i, j)] = reconstruct_path(prev, j)

    # 2. 近似TSP：回路，起点为must_ids[0]，终点也为must_ids[0]
    from itertools import permutations
    n = len(must_ids)
    if n <= 9 and n > 2:
        # 枚举所有排列，选最短回路
        min_order = None
        min_len = float('inf')
        for order in permutations(must_ids[1:-1]):  # 除去首尾（首尾相同）
            seq = [must_ids[0]] + list(order) + [must_ids[0]]
            total = sum(shortest[(seq[i], seq[i+1])] for i in range(len(seq)-1))
            if total < min_len:
                min_len = total
                min_order = seq
        best_order = min_order
    else:
        # 贪心：每次选最近的未访问点，最后回到起点
        unvisited = set(must_ids[1:-1])  # 除去首尾
        curr = must_ids[0]
        best_order = [curr]
        while unvisited:
            next_id = min(unvisited, key=lambda nid: shortest[(curr, nid)])
            best_order.append(next_id)
            curr = next_id
            unvisited.remove(curr)
        best_order.append(must_ids[0])  # 回到起点

    # 3. 拼接所有段，补全中间点
    full_path = []
    for i in range(len(best_order)-1):
        seg = paths[(best_order[i], best_order[i+1])]
        if i > 0:
            seg = seg[1:]  # 避免重复
        full_path.extend(seg)

    # 4. 标记is_via，并补全所有点的信息
    result = []
    for i, pid in enumerate(full_path):
        # 如果是必经点，使用原始POI信息
        if pid in must_ids:
            info = dict(id2poi[pid])
            info['is_via'] = False
        else:
            # 对于途经点，使用实际的地点信息
            if pid in all_points_info:
                info = dict(all_points_info[pid])
            else:
                # 如果找不到信息，使用默认值
                info = {
                    'id': pid,
                    'name': f'途经点 {len(result) + 1}',
                    'address': '自动生成的途经点',
                    'location': {'lng': 0, 'lat': 0}
                }
            info['is_via'] = True

        # 添加距离和时间信息
        if i < len(full_path) - 1:
            next_pid = full_path[i + 1]
            # 查找对应的边
            edge_found = False
            for edge in edges:
                if (edge['from'] == pid and edge['to'] == next_pid) or \
                   (edge['from'] == next_pid and edge['to'] == pid):
                    # 找到对应的边，添加其属性
                    info['edge'] = {
                        'properties': {
                            'distance': edge['distance'],
                            'times': edge.get('times', {
                                '步行': edge['distance'] / (5000/60)  # 默认步行时间
                            })
                        }
                    }
                    edge_found = True
                    break
            
            if not edge_found:
                # 如果没有找到对应的边，使用最短路径信息
                if (pid, next_pid) in shortest:
                    distance = shortest[(pid, next_pid)]
                    info['edge'] = {
                        'properties': {
                            'distance': distance,
                            'times': {
                                '步行': distance / (5000/60)  # 默认步行时间
                            }
                        }
                    }

        result.append(info)

    return result
