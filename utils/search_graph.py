from typing import List, Dict, Any
import networkx as nx
from .edge_properties import EdgePropertiesGenerator

class SearchGraph:
    def __init__(self):
        self.graph = nx.Graph()
        
    def clear_graph(self):
        """清空图"""
        self.graph.clear()
    
    def find_nearest_neighbors(self, point_id: str, point_data: Dict, 
                             all_points: List[tuple], k: int = 3) -> List[tuple]:
        """
        找到距离给定点最近的k个邻居
        
        Args:
            point_id: 当前点的ID
            point_data: 当前点的数据
            all_points: 所有点的列表
            k: 需要找到的邻居数量
            
        Returns:
            List[tuple]: 最近的k个邻居列表
        """
        distances = []
        for other_id, other_data in all_points:
            if other_id != point_id:
                dist = EdgePropertiesGenerator.calculate_distance(
                    point_data['location'],
                    other_data['location']
                )
                distances.append((dist, other_id, other_data))
        
        # 按距离排序并返回最近的k个邻居
        distances.sort(key=lambda x: x[0])
        return [(neighbor_id, neighbor_data) 
                for _, neighbor_id, neighbor_data in distances[:k]]
    
    def find_nearest_points_between_components(self, components: List[List[str]], 
                                             nodes_data: Dict[str, Dict]) -> tuple:
        """
        找到两个连通分量之间距离最近的两个点
        
        Args:
            components: 连通分量列表
            nodes_data: 节点数据字典
            
        Returns:
            tuple: (point1_id, point2_id, distance)
        """
        min_distance = float('inf')
        nearest_points = None
        
        # 遍历所有连通分量对
        for i in range(len(components)):
            for j in range(i + 1, len(components)):
                # 遍历第一个连通分量中的所有点
                for point1_id in components[i]:
                    point1_data = nodes_data[point1_id]
                    # 遍历第二个连通分量中的所有点
                    for point2_id in components[j]:
                        point2_data = nodes_data[point2_id]
                        # 计算距离
                        distance = EdgePropertiesGenerator.calculate_distance(
                            point1_data['location'],
                            point2_data['location']
                        )
                        # 更新最近的点对
                        if distance < min_distance:
                            min_distance = distance
                            nearest_points = (point1_id, point2_id)
        
        return nearest_points[0], nearest_points[1], min_distance if nearest_points else None
    
    def add_points(self, pois: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        添加搜索到的点到图中，并返回所有点之间的连接关系
        
        Args:
            pois: 搜索结果点列表，每个点包含location信息
            
        Returns:
            connections: 所有点之间的连接列表，包含路径、交通方式和权重信息
        """
        # 清空之前的图
        self.clear_graph()
        
        # 添加所有点到图中
        for poi in pois:
            self.graph.add_node(poi['id'], 
                              location=poi['location'],
                              name=poi.get('name', ''))
        
        # 创建所有点之间的连接
        connections = []
        nodes = list(self.graph.nodes(data=True))
        
        # 为每个点找到最近的三个邻居并创建连接
        processed_edges = set()  # 用于记录已处理的边
        for node_id, node_data in nodes:
            # 找到最近的三个邻居
            nearest_neighbors = self.find_nearest_neighbors(node_id, node_data, nodes)
            
            # 创建与最近邻居的连接
            for neighbor_id, neighbor_data in nearest_neighbors:
                # 创建边的标识符（按字母顺序排序以确保无向图的唯一性）
                edge_id = tuple(sorted([node_id, neighbor_id]))
                
                # 如果这条边还没有处理过
                if edge_id not in processed_edges:
                    # 生成边的属性
                    edge_props = EdgePropertiesGenerator.generate_edge_properties(
                        node_data, neighbor_data
                    )
                    
                    # 添加边到图中
                    self.graph.add_edge(node_id, neighbor_id, **edge_props)
                    
                    # 添加连接信息到返回列表
                    connections.append({
                        'path': [
                            {
                                'lng': node_data['location']['lng'],
                                'lat': node_data['location']['lat']
                            },
                            {
                                'lng': neighbor_data['location']['lng'],
                                'lat': neighbor_data['location']['lat']
                            }
                        ],
                        'from_name': node_data['name'],
                        'to_name': neighbor_data['name'],
                        'distance': edge_props['distance'],
                        'transport_modes': edge_props['modes'],
                        'times': edge_props['times'],
                        'weights': edge_props['weights'],
                        'congestion': edge_props['congestion']
                    })
                    
                    # 标记这条边为已处理
                    processed_edges.add(edge_id)
        
        # 检查图的连通性并连接不联通的部分
        while True:
            # 获取所有连通分量
            components = list(nx.connected_components(self.graph))
            
            # 如果只有一个连通分量，图是连通的
            if len(components) == 1:
                break
                
            # 将连通分量转换为列表
            components = [list(comp) for comp in components]
            
            # 创建节点数据字典，用于快速查找
            nodes_dict = {node_id: data for node_id, data in self.graph.nodes(data=True)}
            
            # 找到不同连通分量之间距离最近的两个点
            point1_id, point2_id, _ = self.find_nearest_points_between_components(
                components, nodes_dict
            )
            
            # 生成新边的属性
            edge_props = EdgePropertiesGenerator.generate_edge_properties(
                nodes_dict[point1_id],
                nodes_dict[point2_id]
            )
            
            # 添加新的边
            self.graph.add_edge(point1_id, point2_id, **edge_props)
            
            # 添加新的连接到返回列表
            connections.append({
                'path': [
                    {
                        'lng': nodes_dict[point1_id]['location']['lng'],
                        'lat': nodes_dict[point1_id]['location']['lat']
                    },
                    {
                        'lng': nodes_dict[point2_id]['location']['lng'],
                        'lat': nodes_dict[point2_id]['location']['lat']
                    }
                ],
                'from_name': nodes_dict[point1_id]['name'],
                'to_name': nodes_dict[point2_id]['name'],
                'distance': edge_props['distance'],
                'transport_modes': edge_props['modes'],
                'times': edge_props['times'],
                'weights': edge_props['weights'],
                'congestion': edge_props['congestion']
            })
        
        return connections

# 创建全局实例
search_graph = SearchGraph() 