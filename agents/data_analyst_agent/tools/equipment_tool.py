"""
设备属性查询工具
通过第三方接口获取设备的实时属性数据
"""

import requests
from langchain_core.tools import tool

from core.database import get_mysql_connection

# 第三方接口配置
EQUIPMENT_API_URL = "http://webnet.qhzssy.ltd/prod-api/datahub/EquipmentPropertyPostController/lastEquipmentPropertyPost"
PRODUCT_KEY = "hozg8qUpy1G"
EQUIPMENT_API_TOKEN = "eyJhbGciOiJIUzUxMiJ9.eyJ1c2VyX2lkIjoxOTEsInVzZXJfa2V5IjoiZDg4OWVhNWQtMGMxOC00OGNiLWJkY2UtYWMyZDk0MDBlM2MxIiwidXNlcm5hbWUiOiJkdGFkbWluIn0.Snqb8d8drOWdA4qrYPwknfNyaf6m3SP0SnAVaOsSGUq7hZHyMpjXMib3mULqWnwtq7i3bzitdTd6QAM2bnyUpw"


def get_iot_code_by_device_name(device_name: str) -> str:
    """
    根据设备名称从数据库获取 iot_code
    
    Args:
        device_name: 设备名称
    
    Returns:
        str: iot_code，如果未找到返回 None
    """
    conn = get_mysql_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT iot_code FROM att_irrd_i_st_base WHERE name = %s AND iot_code IS NOT NULL LIMIT 1",
            (device_name,)
        )
        result = cursor.fetchone()
        cursor.close()
        
        if result and result.get('iot_code'):
            return result['iot_code']
        return None
    finally:
        conn.close()


def get_iot_code_by_device_id(device_id: str) -> str:
    """
    根据设备 ID 从数据库获取 iot_code
    
    Args:
        device_id: 设备 ID
    
    Returns:
        str: iot_code，如果未找到返回 None
    """
    conn = get_mysql_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT iot_code FROM att_irrd_i_st_base WHERE id = %s AND iot_code IS NOT NULL LIMIT 1",
            (device_id,)
        )
        result = cursor.fetchone()
        cursor.close()
        
        if result and result.get('iot_code'):
            return result['iot_code']
        return None
    finally:
        conn.close()


@tool
def get_equipment_property(device_name: str) -> dict:
    """
    获取中水数易设备的实时属性数据（调用第三方接口）。
    
    【重要】此工具仅用于查询某个具体设备的"实时数据"，如流量、水位、闸门开度等实时监测值。
    
    适用场景（必须同时满足）：
    1. 用户提到"中水数易"（设备厂家名称）
    2. 用户要查询某个具体设备的"实时数据"、"当前状态"、"最新监测值"
    
    不适用场景（应使用 text2sql_query 工具）：
    - 查询"中水数易的设备有哪些"、"中水数易的闸门列表" → 使用 text2sql_query 查询 factory='5' 的设备
    - 查询设备的历史数据、统计数据 → 使用 text2sql_query
    - 查询设备基本信息（名称、位置等） → 使用 text2sql_query
    
    示例问题（适用本工具）：
    - "查询中水数易设备水车湾村祁元林农渠的实时流量"
    - "水车湾村的中水数易闸门当前开度是多少"
    - "获取中水数易设备的最新监测数据"
    
    Args:
        device_name: 设备名称，如"水车湾村祁元林农渠"
    
    Returns:
        dict: 包含设备属性数据的字典，包括：
            - success: 是否成功
            - device_name: 设备名称
            - iot_code: 物联网设备编码
            - data: 设备属性数据（包含流量、水位、闸门开度、电池电量等）
            - error: 错误信息（如果失败）
    """
    try:
        # 1. 从数据库获取 iot_code
        iot_code = get_iot_code_by_device_name(device_name)
        
        if not iot_code:
            return {
                "success": False,
                "device_name": device_name,
                "error": f"未找到设备 '{device_name}' 的物联网编码(iot_code)，请确认设备名称是否正确"
            }
        
        # 2. 调用第三方接口获取设备属性
        params = {
            "productKey": PRODUCT_KEY,
            "deviceName": iot_code
        }
        
        headers = {
            "Authorization": EQUIPMENT_API_TOKEN
        }
        
        response = requests.get(EQUIPMENT_API_URL, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        
        api_data = response.json()
        
        # 3. 处理返回数据
        if api_data.get('code') == 200 or api_data.get('success'):
            return {
                "success": True,
                "device_name": device_name,
                "iot_code": iot_code,
                "data": api_data.get('data', api_data)
            }
        else:
            return {
                "success": False,
                "device_name": device_name,
                "iot_code": iot_code,
                "error": api_data.get('msg', '接口返回错误')
            }
            
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "device_name": device_name,
            "error": "请求超时，第三方接口响应过慢"
        }
    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "device_name": device_name,
            "error": f"网络请求错误: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "device_name": device_name,
            "error": f"获取设备属性失败: {str(e)}"
        }
