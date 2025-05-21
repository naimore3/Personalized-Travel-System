from utils.edge_properties import EdgePropertiesGenerator, TransportMode
import math

class Graph:
    def __init__(self):
        self.points = {}  # 存储所有点
        self.edges = {}   # 存储所有边
        self.edge_properties = EdgePropertiesGenerator()

    def calculate_distance(self, point1, point2):
        """计算两点之间的距离（米）"""
        try:
            # 使用经纬度计算距离
            lng1, lat1 = point1['location']['lng'], point1['location']['lat']
            lng2, lat2 = point2['location']['lng'], point2['location']['lat']
            
            # 将经纬度转换为弧度
            lng1, lat1, lng2, lat2 = map(math.radians, [lng1, lat1, lng2, lat2])
            
            # 地球半径（米）
            R = 6371000
            
            # 计算距离
            dlat = lat2 - lat1
            dlng = lng2 - lng1
            a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng/2)**2
            c = 2 * math.asin(math.sqrt(a))
            distance = R * c
            
            return distance
        except Exception as e:
            print(f"Error calculating distance: {str(e)}")
            return 0

    def _ensure_connectivity(self):
        """确保图的连通性"""
        def can_reach_all_nodes(start_node_id):
            """检查从起始节点是否能到达所有其他节点"""
            visited = set()
            def dfs(node_id):
                visited.add(node_id)
                for edge_id, edge in self.edges.items():
                    if node_id in edge_id:
                        # 获取边的另一个端点
                        neighbor_id = edge['target']['id'] if edge['source']['id'] == node_id else edge['source']['id']
                        if neighbor_id not in visited:
                            dfs(neighbor_id)
            
            dfs(start_node_id)
            return visited == set(self.points.keys())

        # 获取所有节点ID
        node_ids = list(self.points.keys())
        if not node_ids:
            return

        print(f"开始检查连通性，总节点数: {len(node_ids)}")
        
        # 对每个节点检查连通性
        for start_node_id in node_ids:
            if not can_reach_all_nodes(start_node_id):
                print(f"节点 {start_node_id} 不能到达所有其他节点")
                # 如果从当前节点不能到达所有节点，找到未访问的节点
                visited = set()
                def dfs(node_id):
                    visited.add(node_id)
                    for edge_id, edge in self.edges.items():
                        if node_id in edge_id:
                            neighbor_id = edge['target']['id'] if edge['source']['id'] == node_id else edge['source']['id']
                            if neighbor_id not in visited:
                                dfs(neighbor_id)
                dfs(start_node_id)
                unvisited = set(node_ids) - visited
                print(f"未访问节点数: {len(unvisited)}")

                # 计算当前节点到所有未访问节点的距离
                distances = []
                for node_id in unvisited:
                    distance = self.calculate_distance(self.points[start_node_id], self.points[node_id])
                    distances.append((node_id, distance))
                
                # 按距离排序
                distances.sort(key=lambda x: x[1])
                print(f"按距离排序后的未访问节点数: {len(distances)}")
                
                # 依次尝试连接更远的点，直到图连通
                for node_id, distance in distances:
                    print(f"尝试连接节点 {start_node_id} 和 {node_id}，距离: {distance}米")
                    # 添加边
                    edge_id = tuple(sorted([start_node_id, node_id]))
                    properties = self.edge_properties.generate_edge_properties(
                        {'location': self.points[start_node_id]['location']},
                        {'location': self.points[node_id]['location']}
                    )
                    
                    self.edges[edge_id] = {
                        'source': self.points[start_node_id],
                        'target': self.points[node_id],
                        'properties': properties
                    }
                    
                    # 检查是否已经连通
                    if can_reach_all_nodes(start_node_id):
                        print(f"添加边后图已连通")
                        break
            else:
                print(f"节点 {start_node_id} 可以到达所有其他节点")

        # 最终检查
        final_check = True
        for node_id in node_ids:
            if not can_reach_all_nodes(node_id):
                print(f"警告：最终检查时节点 {node_id} 仍然不能到达所有其他节点")
                final_check = False
        
        if final_check:
            print("最终检查：图完全连通")
        else:
            print("最终检查：图仍然存在不连通的情况")

    def add_points(self, points):
        """添加点并建立连接关系"""
        try:
            # 验证输入数据
            if not points or not isinstance(points, list):
                raise ValueError("Points must be a non-empty list")
            
            # 清空现有数据
            self.points = {}
            self.edges = {}

            # 添加所有点
            for point in points:
                # 验证点的数据格式
                if not isinstance(point, dict):
                    raise ValueError(f"Invalid point format: {point}")
                
                required_fields = ['id', 'name', 'location']
                if not all(field in point for field in required_fields):
                    raise ValueError(f"Missing required fields in point: {point}")
                
                if not isinstance(point['location'], dict) or not all(key in point['location'] for key in ['lng', 'lat']):
                    raise ValueError(f"Invalid location format in point: {point}")
                
                point_id = point['id']
                self.points[point_id] = {
                    'id': point_id,
                    'name': point['name'],
                    'location': point['location'],
                    'address': point.get('address', '')
                }

            # 为每个点找到最近的两个点
            for point_id, point in self.points.items():
                distances = []
                for other_id, other_point in self.points.items():
                    if point_id != other_id:
                        try:
                            distance = self.calculate_distance(point, other_point)
                            distances.append((other_id, distance))
                        except Exception as e:
                            print(f"Error calculating distance between {point_id} and {other_id}: {str(e)}")
                            continue
                
                # 按距离排序
                distances.sort(key=lambda x: x[1])
                
                # 连接最近的两个点
                for other_id, distance in distances[:2]:
                    edge_id = tuple(sorted([point_id, other_id]))
                    if edge_id not in self.edges:
                        try:
                            # 使用EdgePropertiesGenerator生成边的属性
                            properties = self.edge_properties.generate_edge_properties(
                                {'location': point['location']},
                                {'location': self.points[other_id]['location']}
                            )
                            
                            self.edges[edge_id] = {
                                'source': self.points[point_id],
                                'target': self.points[other_id],
                                'properties': properties
                            }
                        except Exception as e:
                            print(f"Error creating edge between {point_id} and {other_id}: {str(e)}")
                            continue

            # 检查图的连通性
            try:
                self._ensure_connectivity()
            except Exception as e:
                print(f"Error ensuring connectivity: {str(e)}")

            return self.get_connections()
        except Exception as e:
            print("Error in add_points:", str(e))
            import traceback
            traceback.print_exc()
            raise e

    def get_connections(self):
        """获取所有连接关系"""
        # 添加调试信息
        print(f"返回连接关系：点数={len(self.points)}，边数={len(self.edges)}")
        return {
            'points': list(self.points.values()),
            'edges': list(self.edges.values())
        }

    def get_point_connections(self, point_id):
        """获取指定点的所有连接"""
        connections = []
        for edge_id, edge in self.edges.items():
            if point_id in edge_id:
                neighbor_id = edge['target'] if edge['source'] == point_id else edge['source']
                connections.append({
                    'point': self.points[neighbor_id],
                    'edge': edge
                })
        return connections 