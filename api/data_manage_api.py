"""
数据管理 API (FastAPI 版本)
提供训练文件的统计、列表、删除等功能
"""
import sys
import os
import hashlib
from datetime import datetime, date
from pathlib import Path
from typing import Optional, List

from fastapi import APIRouter, Query, HTTPException, Depends
from pydantic import BaseModel
import mysql.connector
from mysql.connector import Error

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import DB_CONFIG

from common.dependencies import get_current_user

# ==================== 数据库工具函数 ====================

def get_db_connection():
    """获取数据库连接"""
    try:
        conn = mysql.connector.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG.get('port', 3306),
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            database=DB_CONFIG['database']
        )
        return conn
    except Error as e:
        print(f"[DataManage] 连接数据库失败: {e}")
        return None


def init_table():
    """初始化训练文件记录表"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        create_sql = """
        CREATE TABLE IF NOT EXISTS training_files (
            id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
            file_name VARCHAR(255) NOT NULL COMMENT '文件名',
            file_path VARCHAR(500) NOT NULL COMMENT '文件完整路径',
            file_type VARCHAR(20) NOT NULL COMMENT '文件类型',
            train_type VARCHAR(20) NOT NULL COMMENT '训练类型：sql或document',
            file_size BIGINT DEFAULT 0 COMMENT '文件大小(字节)',
            file_hash VARCHAR(64) COMMENT '文件MD5哈希值',
            train_status VARCHAR(20) DEFAULT 'pending' COMMENT '训练状态',
            train_result TEXT COMMENT '训练结果或错误信息',
            train_count INT DEFAULT 0 COMMENT '训练生成的知识条目数',
            upload_date DATE NOT NULL COMMENT '上传日期',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
            
            INDEX idx_file_type (file_type),
            INDEX idx_train_type (train_type),
            INDEX idx_train_status (train_status),
            INDEX idx_upload_date (upload_date),
            INDEX idx_file_hash (file_hash)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='训练文件记录表'
        """
        cursor.execute(create_sql)
        conn.commit()
        print("[DataManage] 训练文件记录表初始化成功")
        return True
        
    except Error as e:
        print(f"[DataManage] 初始化表失败: {e}")
        return False
    finally:
        cursor.close()
        conn.close()


def calculate_file_hash(file_path: Path) -> str:
    """计算文件MD5哈希值"""
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception:
        return ""


def insert_training_file(
    file_name: str,
    file_path: str,
    file_type: str,
    train_type: str,
    file_size: int = 0,
    file_hash: str = None,
    upload_date: date = None
) -> Optional[int]:
    """插入训练文件记录"""
    conn = get_db_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        
        if upload_date is None:
            upload_date = date.today()
        
        sql = """
        INSERT INTO training_files 
        (file_name, file_path, file_type, train_type, file_size, file_hash, upload_date)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (
            file_name, file_path, file_type, train_type, file_size, file_hash, upload_date
        ))
        conn.commit()
        
        return cursor.lastrowid
        
    except Error as e:
        print(f"[DataManage] 插入记录失败: {e}")
        return None
    finally:
        cursor.close()
        conn.close()


def update_training_status(
    file_id: int,
    train_status: str,
    train_result: str = None,
    train_count: int = None
) -> bool:
    """更新训练状态"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        updates = ["train_status = %s"]
        params = [train_status]
        
        if train_result is not None:
            updates.append("train_result = %s")
            params.append(train_result)
        
        if train_count is not None:
            updates.append("train_count = %s")
            params.append(train_count)
        
        params.append(file_id)
        
        sql = f"UPDATE training_files SET {', '.join(updates)} WHERE id = %s"
        cursor.execute(sql, params)
        conn.commit()
        
        return cursor.rowcount > 0
        
    except Error as e:
        print(f"[DataManage] 更新状态失败: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

# 创建路由器
router = APIRouter(prefix="/api/data-manage", tags=["数据管理"])


# ==================== Pydantic 模型 ====================

class DeleteFilesRequest(BaseModel):
    ids: Optional[List[int]] = None
    delete_all: bool = False


# ==================== 接口 ====================

@router.get("/stats")
async def get_training_stats(user=Depends(get_current_user)):
    """获取训练数据统计"""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="数据库连接失败")
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        sql = """
        SELECT 
            COUNT(*) as total_files,
            SUM(CASE WHEN train_type = 'sql' THEN 1 ELSE 0 END) as sql_count,
            SUM(CASE WHEN train_type = 'document' THEN 1 ELSE 0 END) as doc_count,
            SUM(CASE WHEN train_status = 'success' THEN 1 ELSE 0 END) as success_count,
            SUM(CASE WHEN train_status = 'failed' THEN 1 ELSE 0 END) as failed_count,
            SUM(CASE WHEN train_status = 'pending' THEN 1 ELSE 0 END) as pending_count,
            COALESCE(SUM(train_count), 0) as total_train_items,
            COALESCE(SUM(file_size), 0) as total_file_size
        FROM training_files
        """
        cursor.execute(sql)
        result = cursor.fetchone()
        
        cursor.execute("""
            SELECT file_type, COUNT(*) as count 
            FROM training_files 
            GROUP BY file_type
        """)
        type_stats = {row['file_type']: row['count'] for row in cursor.fetchall()}
        
        return {
            "success": True,
            "stats": {
                "total_files": result['total_files'] or 0,
                "sql_count": int(result['sql_count'] or 0),
                "doc_count": int(result['doc_count'] or 0),
                "success_count": int(result['success_count'] or 0),
                "failed_count": int(result['failed_count'] or 0),
                "pending_count": int(result['pending_count'] or 0),
                "total_train_items": int(result['total_train_items'] or 0),
                "total_file_size": int(result['total_file_size'] or 0),
                "by_type": type_stats
            }
        }
        
    except Error as e:
        print(f"[DataManage] 获取统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@router.get("/activity")
async def get_activity(days: int = Query(30, ge=1, le=365), user=Depends(get_current_user)):
    """获取训练活跃度"""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="数据库连接失败")
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        sql = """
        SELECT 
            upload_date,
            COUNT(*) as file_count,
            COALESCE(SUM(train_count), 0) as train_items
        FROM training_files
        WHERE upload_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
        GROUP BY upload_date
        ORDER BY upload_date ASC
        """
        cursor.execute(sql, (days,))
        results = cursor.fetchall()
        
        data = []
        for row in results:
            data.append({
                "date": row['upload_date'].isoformat() if row['upload_date'] else None,
                "count": row['file_count'],
                "train_items": int(row['train_items'])
            })
        
        return {"success": True, "data": data}
        
    except Error as e:
        print(f"[DataManage] 获取活跃度失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@router.get("/files")
async def get_files(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    train_type: str = Query(""),
    file_type: str = Query(""),
    train_status: str = Query(""),
    keyword: str = Query(""),
    user=Depends(get_current_user),
):
    """获取训练文件列表"""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="数据库连接失败")
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        conditions = []
        params = []
        
        if train_type:
            conditions.append("train_type = %s")
            params.append(train_type)
        
        if file_type:
            conditions.append("file_type = %s")
            params.append(file_type)
        
        if train_status:
            conditions.append("train_status = %s")
            params.append(train_status)
        
        if keyword:
            conditions.append("(file_name LIKE %s OR file_path LIKE %s)")
            params.extend([f"%{keyword}%", f"%{keyword}%"])
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        # 查询总数
        count_sql = f"SELECT COUNT(*) as total FROM training_files WHERE {where_clause}"
        cursor.execute(count_sql, params)
        total = cursor.fetchone()['total']
        
        # 查询数据
        offset = (page - 1) * page_size
        data_sql = f"""
        SELECT * FROM training_files 
        WHERE {where_clause}
        ORDER BY created_at DESC
        LIMIT %s OFFSET %s
        """
        cursor.execute(data_sql, params + [page_size, offset])
        data = cursor.fetchall()
        
        # 转换日期格式
        for row in data:
            if row.get('upload_date'):
                row['upload_date'] = row['upload_date'].isoformat()
            if row.get('created_at'):
                row['created_at'] = row['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            if row.get('updated_at'):
                row['updated_at'] = row['updated_at'].strftime('%Y-%m-%d %H:%M:%S')
        
        return {
            "success": True,
            "data": data,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": (total + page_size - 1) // page_size
            }
        }
        
    except Error as e:
        print(f"[DataManage] 查询失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()


@router.delete("/files")
async def delete_files(req: DeleteFilesRequest, user=Depends(get_current_user)):
    """删除训练文件记录"""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="数据库连接失败")
    
    try:
        cursor = conn.cursor(dictionary=True)
        
        # 查询要删除的记录
        if req.delete_all:
            cursor.execute("SELECT id, file_name, file_path, file_hash, train_type FROM training_files")
        elif req.ids:
            placeholders = ','.join(['%s'] * len(req.ids))
            cursor.execute(f"SELECT id, file_name, file_path, file_hash, train_type FROM training_files WHERE id IN ({placeholders})", req.ids)
        else:
            raise HTTPException(status_code=400, detail="请指定要删除的记录")
        
        records = cursor.fetchall()
        
        if not records:
            raise HTTPException(status_code=404, detail="未找到要删除的记录")
        
        deleted_db_count = 0
        deleted_file_count = 0
        deleted_vector_count = 0
        errors = []
        
        # 删除向量数据库中的数据
        try:
            from common.vanna_instance import get_vanna_instance
            vn = get_vanna_instance()
            
            training_data = vn.get_training_data()
            if hasattr(training_data, 'to_dict'):
                all_data = training_data.to_dict('records')
            elif isinstance(training_data, list):
                all_data = training_data
            else:
                all_data = []
            
            for record in records:
                file_hash = record.get('file_hash')
                file_name = record.get('file_name')
                train_type = record.get('train_type')
                
                if file_hash and file_name:
                    prefix = 'sql' if train_type == 'sql' else 'doc'
                    file_id = f"{prefix}_{file_name}_{file_hash[:8]}"
                    
                    for item in all_data:
                        content = item.get('content', '') or ''
                        if file_id in str(content):
                            item_id = item.get('id')
                            if item_id:
                                try:
                                    vn.remove_training_data(id=item_id)
                                    deleted_vector_count += 1
                                except Exception as ve:
                                    errors.append(f"删除向量 {item_id} 失败: {str(ve)}")
                        
        except Exception as e:
            errors.append(f"获取 Vanna 实例失败: {str(e)}")
        
        # 删除本地文件
        for record in records:
            file_path = record.get('file_path')
            if file_path:
                full_path = PROJECT_ROOT / file_path
                if full_path.exists():
                    try:
                        os.remove(full_path)
                        deleted_file_count += 1
                    except Exception as fe:
                        errors.append(f"删除文件 {file_path} 失败: {str(fe)}")
        
        # 删除数据库记录
        cursor_del = conn.cursor()
        if req.delete_all:
            cursor_del.execute("DELETE FROM training_files")
        else:
            placeholders = ','.join(['%s'] * len(req.ids))
            cursor_del.execute(f"DELETE FROM training_files WHERE id IN ({placeholders})", req.ids)
        
        conn.commit()
        deleted_db_count = cursor_del.rowcount
        cursor_del.close()
        
        return {
            "success": True,
            "message": f"删除完成：数据库 {deleted_db_count} 条，文件 {deleted_file_count} 个，向量 {deleted_vector_count} 条",
            "deleted_count": deleted_db_count,
            "details": {
                "database": deleted_db_count,
                "files": deleted_file_count,
                "vectors": deleted_vector_count
            },
            "errors": errors if errors else None
        }
        
    except HTTPException:
        raise
    except Error as e:
        print(f"[DataManage] 删除失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        conn.close()
