from typing import List, Dict, Any
import networkx as nx

class SearchGraph:
    def __init__(self):
        self.graph = nx.Graph()
        
    def clear_graph(self):
        """清空图"""
        self.graph.clear()
        
    def add_points(self, pois: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        添加搜索到的点到图中，并返回所有点之间的连接关系
        
        Args:
            pois: 搜索结果点列表，每个点包含location信息
            
        Returns:
            connections: 所有点之间的连接列表
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
        
        # 连接所有点
        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                node1_id, node1_data = nodes[i]
                node2_id, node2_data = nodes[j]
                
                # 添加边到图中
                self.graph.add_edge(node1_id, node2_id)
                
                # 添加连接信息到返回列表
                connections.append({
                    'path': [
                        {
                            'lng': node1_data['location']['lng'],
                            'lat': node1_data['location']['lat']
                        },
                        {
                            'lng': node2_data['location']['lng'],
                            'lat': node2_data['location']['lat']
                        }
                    ],
                    'from_name': node1_data['name'],
                    'to_name': node2_data['name']
                })
        
        return connections

# 创建全局实例
search_graph = SearchGraph() 