# utils/indoor_path_finder.py
# 室内导航路径查找工具

def dfs_path(graph, start, end, path=None, visited=None):
    """在单层图中用DFS找到一条从start到end的路径"""
    if path is None:
        path = [start]
    if visited is None:
        visited = set([start])
    if start == end:
        return path
    for neighbor in graph.get(str(start), []):
        if neighbor not in visited:
            visited.add(neighbor)
            res = dfs_path(graph, neighbor, end, path + [neighbor], visited)
            if res:
                return res
    return None

def find_facility_indices(facilities, types):
    """返回指定类型设施的所有索引"""
    return [i for i, f in enumerate(facilities) if f['key'] in types]

def find_path_across_floors(floorData, start_floor, start_idx, end_floor, end_idx):
    """
    跨层路径查找：
    - 楼层差<=3优先楼梯，>3优先电梯
    - 返回完整路径点序列（含楼层、索引、类型等）
    """
    start_floor = int(start_floor)
    end_floor = int(end_floor)
    if start_floor == end_floor:
        # 同层DFS
        graph = floorData[str(start_floor)]['graph']
        path = dfs_path(graph, int(start_idx), int(end_idx))
        if not path:
            return []
        return [{
            'floor': start_floor,
            'index': idx,
            'name': floorData[str(start_floor)]['facilities'][idx]['name'],
            'type': floorData[str(start_floor)]['facilities'][idx]['key']
        } for idx in path]
    # 跨层
    diff = abs(start_floor - end_floor)
    prefer = ['stair'] if diff <= 3 else ['elevator']
    # 1. 起点层找所有中转点
    start_facilities = floorData[str(start_floor)]['facilities']
    end_facilities = floorData[str(end_floor)]['facilities']
    start_graph = floorData[str(start_floor)]['graph']
    end_graph = floorData[str(end_floor)]['graph']
    start_trans = find_facility_indices(start_facilities, prefer)
    end_trans = find_facility_indices(end_facilities, prefer)
    # 2. 起点到本层中转点
    for s_tran in start_trans:
        path1 = dfs_path(start_graph, int(start_idx), s_tran)
        if not path1:
            continue
        # 3. 目标层中转点到终点
        for e_tran in end_trans:
            path2 = dfs_path(end_graph, e_tran, int(end_idx))
            if not path2:
                continue
            # 4. 组合路径
            # 跨层部分只记录一次中转
            path_seq = []
            # 起点层
            path_seq += [{
                'floor': start_floor,
                'index': idx,
                'name': start_facilities[idx]['name'],
                'type': start_facilities[idx]['key']
            } for idx in path1]
            # 跨层
            path_seq.append({
                'floor': '跨层',
                'index': -1,
                'name': '通过%s从%d层到%d层' % (prefer[0]=='stair' and '楼梯' or '电梯', start_floor, end_floor),
                'type': prefer[0]
            })
            # 目标层
            path_seq += [{
                'floor': end_floor,
                'index': idx,
                'name': end_facilities[idx]['name'],
                'type': end_facilities[idx]['key']
            } for idx in path2]
            return path_seq
    return []
