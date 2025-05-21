from typing import Dict, Any
import random
import math
from enum import Enum

class TransportMode(Enum):
    WALKING = "walking"
    CYCLING = "cycling"
    DRIVING = "driving"

# 添加交通方式的中文映射
TRANSPORT_MODE_CHINESE = {
    "walking": "步行",
    "cycling": "骑行",
    "driving": "驾车"
}

class EdgePropertiesGenerator:
    @staticmethod
    def calculate_distance(point1: Dict, point2: Dict) -> float:
        """
        计算两点之间的距离（使用欧几里得距离，单位：米）
        
        Args:
            point1: 第一个点的坐标 {'lng': float, 'lat': float}
            point2: 第二个点的坐标 {'lng': float, 'lat': float}
            
        Returns:
            float: 两点之间的距离（米）
        """
        # 地球半径（米）
        EARTH_RADIUS = 6371000

        # 将经纬度转换为弧度
        lat1 = math.radians(point1['lat'])
        lng1 = math.radians(point1['lng'])
        lat2 = math.radians(point2['lat'])
        lng2 = math.radians(point2['lng'])

        # 使用Haversine公式计算距离
        dlat = lat2 - lat1
        dlng = lng2 - lng1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        distance = EARTH_RADIUS * c

        return round(distance, 2)

    @staticmethod
    def calculate_travel_time(distance: float, mode: TransportMode, congestion: float) -> float:
        """
        根据距离、交通方式和拥挤度计算预计时间（分钟）
        
        Args:
            distance: 距离（米）
            mode: 交通方式
            congestion: 拥挤度系数（0.5-1.0）
            
        Returns:
            float: 预计时间（分钟）
        """
        # 各种交通方式的速度范围（米/分钟）
        SPEED_RANGES = {
            TransportMode.WALKING: (60, 80),    # 3.6-4.8 km/h
            TransportMode.CYCLING: (200, 300),  # 12-18 km/h
            TransportMode.DRIVING: (400, 800)   # 24-48 km/h
        }
        
        # 生成基础速度
        speed_range = SPEED_RANGES[mode]
        base_speed = random.uniform(speed_range[0], speed_range[1])
        
        # 考虑拥挤度影响，拥挤度越高，实际速度越低
        actual_speed = base_speed * (2 - congestion)  # 当拥挤度为1时，速度不变；当拥挤度为0.5时，速度提高50%
        
        # 计算时间（分钟）
        time = distance / actual_speed
            
        return round(time, 1)

    @staticmethod
    def generate_edge_properties(point1: Dict[str, Any], point2: Dict[str, Any]) -> Dict:
        """
        生成边的属性，包括距离、交通方式、时间和拥挤度
        
        Args:
            point1: 起点信息，包含location
            point2: 终点信息，包含location
            
        Returns:
            Dict: 包含距离、交通方式、时间、权重和拥挤度的字典
        """
        # 计算两点之间的距离
        distance = EdgePropertiesGenerator.calculate_distance(
            point1['location'], 
            point2['location']
        )
        
        # 生成拥挤度（0.5-1.0之间的随机数）
        congestion = round(random.uniform(0.5, 1.0), 2)
        
        # 确定可用的交通方式
        available_modes = []
        available_modes.append(TransportMode.WALKING)
        
        # 根据距离决定是否支持其他交通方式
        if random.random() < 0.7 and distance <= 5000:  # 5公里内70%概率支持骑行
            available_modes.append(TransportMode.CYCLING)
        if random.random() < 0.3:  # 30%概率支持驾车
            available_modes.append(TransportMode.DRIVING)
        
        # 为每种交通方式计算时间
        travel_times = {}
        weights = {}
        for mode in available_modes:
            time = EdgePropertiesGenerator.calculate_travel_time(distance, mode, congestion)
            chinese_mode = TRANSPORT_MODE_CHINESE[mode.value]
            travel_times[chinese_mode] = time
            weights[chinese_mode] = time
        
        return {
            'distance': distance,  # 单位：米
            'congestion': congestion,  # 拥挤度（0.5-1.0）
            'modes': [TRANSPORT_MODE_CHINESE[mode.value] for mode in available_modes],
            'times': travel_times,
            'weights': weights
        }

class EdgeProperties:
    def __init__(self):
        self.property_types = {
            'distance': self._generate_distance,
            'time': self._generate_time,
            'difficulty': self._generate_difficulty,
            'scenic_score': self._generate_scenic_score
        }

    def generate_properties(self):
        """生成边的属性"""
        properties = {}
        for prop_name, generator in self.property_types.items():
            properties[prop_name] = generator()
        return properties

    def _generate_distance(self):
        """生成距离属性（米）"""
        return random.randint(50, 500)

    def _generate_time(self):
        """生成时间属性（分钟）"""
        return random.randint(1, 30)

    def _generate_difficulty(self):
        """生成难度属性（1-5）"""
        return random.randint(1, 5)

    def _generate_scenic_score(self):
        """生成风景评分（1-10）"""
        return round(random.uniform(1, 10), 1) 