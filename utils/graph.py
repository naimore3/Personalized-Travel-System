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
        """确保图的连通性，使用更优的算法"""
        def get_connected_components():
            """获取所有连通分量"""
            visited = set()
            components = []
            
            def dfs(node_id, component):
                visited.add(node_id)
                component.add(node_id)
                for edge_id, edge in self.edges.items():
                    if node_id in edge_id:
                        neighbor_id = edge['target']['id'] if edge['source']['id'] == node_id else edge['source']['id']
                        if neighbor_id not in visited:
                            dfs(neighbor_id, component)
            
            # 对每个未访问的节点进行DFS，找出所有连通分量
            for node_id in self.points.keys():
                if node_id not in visited:
                    component = set()
                    dfs(node_id, component)
                    components.append(component)
            
            return components

        def find_closest_components(components):
            """找到两个最近的连通分量"""
            min_distance = float('inf')
            closest_pair = None
            
            # 遍历所有连通分量对
            for i in range(len(components)):
                for j in range(i + 1, len(components)):
                    # 计算两个连通分量之间的最小距离
                    for node1_id in components[i]:
                        for node2_id in components[j]:
                            distance = self.calculate_distance(
                                self.points[node1_id],
                                self.points[node2_id]
                            )
                            if distance < min_distance:
                                min_distance = distance
                                closest_pair = (node1_id, node2_id)
            
            return closest_pair

        print("开始检查连通性...")
        
        while True:
            # 获取当前的所有连通分量
            components = get_connected_components()
            print(f"当前连通分量数量: {len(components)}")
            
            # 如果只有一个连通分量，说明图已经连通
            if len(components) == 1:
                print("图已完全连通")
                break
            
            # 找到最近的两个连通分量
            closest_pair = find_closest_components(components)
            if not closest_pair:
                print("无法找到可连接的连通分量")
                break
            
            # 连接最近的两个节点
            node1_id, node2_id = closest_pair
            edge_id = tuple(sorted([node1_id, node2_id]))
            
            # 生成边的属性
            properties = self.edge_properties.generate_edge_properties(
                {'location': self.points[node1_id]['location']},
                {'location': self.points[node2_id]['location']}
            )
            
            # 添加新边
            self.edges[edge_id] = {
                'source': self.points[node1_id],
                'target': self.points[node2_id],
                'properties': properties
            }
            
            print(f"添加新边连接节点 {node1_id} 和 {node2_id}，距离: {self.calculate_distance(self.points[node1_id], self.points[node2_id])}米")
        
        # 最终检查
        final_components = get_connected_components()
        if len(final_components) == 1:
            print("最终检查：图完全连通")
        else:
            print(f"最终检查：图仍然存在 {len(final_components)} 个不连通的子图")

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