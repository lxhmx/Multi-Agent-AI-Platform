"""
Vanna 训练 API
提供模型训练接口
"""
import os
import sys
import glob
import hashlib
from pathlib import Path

from flask import Flask, request, jsonify

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from common.vanna_instance import get_vanna_instance


def get_file_hash(file_path: str) -> str:
    """计算文件内容的 MD5 哈希值"""
    md5_hash = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()


def is_already_trained(vn, file_id: str) -> bool:
    """检查文件是否已经训练过"""
    try:
        training_data = vn.get_training_data()
        
        # 转换为列表
        if hasattr(training_data, 'to_dict'):
            all_data = training_data.to_dict('records')
        elif isinstance(training_data, list):
            all_data = training_data
        else:
            return False
        
        # 检查是否存在相同的 file_id
        for item in all_data:
            content = item.get('content', '') or item.get('question', '')
            if file_id in str(content):
                return True
        
        return False
    except Exception as e:
        print(f"[Train SQL] 检查重复失败: {e}")
        return False


def train_sql():
    """
    训练接口 - 读取 train-sql 文件夹下的所有 .sql 文件进行训练
    
    请求: POST /api/train
    响应: {
        "success": true,
        "message": "训练完成",
        "trained_files": ["file1.sql", "file2.sql"],
        "total_count": 2
    }
    """
    try:
        vn = get_vanna_instance()
        
        # 延迟导入数据管理函数
        from api.data_manage_api import get_data_manage_functions, get_db_connection
        funcs = get_data_manage_functions()
        update_training_status = funcs['update_training_status']
        
        # 获取 train-sql 文件夹路径
        train_sql_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'train-sql')
        
        if not os.path.exists(train_sql_path):
            os.makedirs(train_sql_path, exist_ok=True)
            return jsonify({
                "success": False,
                "message": f"train-sql 文件夹为空，请添加 .sql 文件到: {train_sql_path}",
                "trained_files": [],
                "total_count": 0
            })
        
        # 获取所有 .sql 文件（递归扫描子目录）
        sql_files = glob.glob(os.path.join(train_sql_path, '**', '*.sql'), recursive=True)
        sql_files = list(set(sql_files))
        
        if not sql_files:
            return jsonify({
                "success": False,
                "message": "train-sql 文件夹中没有找到 .sql 文件",
                "trained_files": [],
                "total_count": 0
            })
        
        trained_files = []
        skipped_files = []
        errors = []
        
        # 查询数据库中的文件记录（用于更新训练状态）
        conn = get_db_connection()
        file_id_map = {}  # file_path -> db_id
        if conn:
            try:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT id, file_path FROM training_files WHERE train_type = 'sql'")
                for row in cursor.fetchall():
                    file_id_map[row['file_path']] = row['id']
                cursor.close()
                conn.close()
            except Exception as e:
                print(f"[Train SQL] 查询文件记录失败: {e}")
        
        print(f"[Train SQL] 开始训练 SQL 文件，共 {len(sql_files)} 个文件")
        
        # 遍历并训练每个文件
        for sql_file in sql_files:
            file_name = os.path.basename(sql_file)
            db_file_id = file_id_map.get(sql_file)
            
            try:
                # 计算文件哈希
                file_hash = get_file_hash(sql_file)
                file_id = f"sql_{file_name}_{file_hash[:8]}"
                
                # 检查是否已训练
                if is_already_trained(vn, file_id):
                    print(f"[Train SQL] ⊙ {file_name} 已训练过，跳过")
                    skipped_files.append(file_name)
                    if db_file_id:
                        update_training_status(db_file_id, 'success', '已训练（跳过重复）', 1)
                    continue
                
                with open(sql_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                
                if not content:
                    errors.append(f"{file_name}: 文件为空")
                    if db_file_id:
                        update_training_status(db_file_id, 'failed', '文件为空')
                    continue
                
                # 在内容中添加文件标识（用于删除时匹配）
                content_with_id = f"-- 文件ID: {file_id}\n{content}"
                
                # 判断文件类型并训练
                content_upper = content.upper()
                train_type = 'ddl'
                
                if content_upper.startswith('CREATE') or content_upper.startswith('ALTER'):
                    vn.train(ddl=content_with_id)
                    trained_files.append({"file": file_name, "type": "ddl"})
                    train_type = 'ddl'
                    print(f"[Train SQL] ✓ {file_name} (DDL) 训练成功")
                elif content_upper.startswith('--'):
                    doc_content = content.lstrip('-').strip()
                    doc_with_id = f"文件ID: {file_id}\n{doc_content}"
                    vn.train(documentation=doc_with_id)
                    trained_files.append({"file": file_name, "type": "documentation"})
                    train_type = 'documentation'
                    print(f"[Train SQL] ✓ {file_name} (文档) 训练成功")
                elif content_upper.startswith('SELECT'):
                    lines = content.split('\n')
                    if lines[0].strip().startswith('--'):
                        question = lines[0].strip().lstrip('-').strip()
                        sql_content = '\n'.join(lines[1:]).strip()
                    else:
                        sql_content = content
                        question = file_name.replace('.sql', '').replace('_', ' ')
                    
                    sql_with_id = f"-- 文件ID: {file_id}\n{sql_content}"
                    vn.train(question=question, sql=sql_with_id)
                    trained_files.append({"file": file_name, "type": "sql", "question": question})
                    train_type = 'sql'
                    print(f"[Train SQL] ✓ {file_name} (SQL) 训练成功")
                else:
                    vn.train(ddl=content_with_id)
                    trained_files.append({"file": file_name, "type": "ddl"})
                    train_type = 'ddl'
                    print(f"[Train SQL] ✓ {file_name} (DDL) 训练成功")
                
                # 更新数据库状态
                if db_file_id:
                    update_training_status(db_file_id, 'success', f'训练成功 ({train_type})', 1)
                    
            except Exception as e:
                errors.append(f"{file_name}: {str(e)}")
                print(f"[Train SQL] ✗ {file_name} 训练失败: {e}")
                if db_file_id:
                    update_training_status(db_file_id, 'failed', str(e))
        
        # 输出统计信息
        if skipped_files:
            print(f"[Train SQL] 跳过 {len(skipped_files)} 个已训练的文件")
        
        message = f"训练完成：新增 {len(trained_files)} 个"
        if skipped_files:
            message += f"，跳过 {len(skipped_files)} 个已训练"
        
        return jsonify({
            "success": True,
            "message": message,
            "trained_files": trained_files,
            "skipped_files": skipped_files,
            "trained_count": len(trained_files),
            "skipped_count": len(skipped_files),
            "total_files": len(sql_files),
            "errors": errors if errors else None
        })
        
    except Exception as e:
        import traceback
        print(f"[Train SQL] 训练异常: {traceback.format_exc()}")
        return jsonify({
            "success": False,
            "message": f"训练失败: {str(e)}"
        }), 500


def get_training_data():
    """
    获取训练数据统计（支持分页）
    
    请求: GET /api/training-data?page=1&page_size=50&summary_only=true
    参数:
        - page: 页码，默认 1
        - page_size: 每页数量，默认 50，最大 100
        - summary_only: 只返回统计信息，默认 false
    
    响应: {
        "success": true,
        "summary": {
            "total_count": 1000,
            "ddl_count": 50,
            "sql_count": 800,
            "doc_count": 150
        },
        "data": [...],  # summary_only=true 时不返回
        "pagination": {
            "page": 1,
            "page_size": 50,
            "total_pages": 20
        }
    }
    """
    try:
        # 获取查询参数
        page = int(request.args.get('page', 1))
        page_size = min(int(request.args.get('page_size', 50)), 100)  # 最大 100
        summary_only = request.args.get('summary_only', 'false').lower() == 'true'
        
        vn = get_vanna_instance()
        
        # 获取训练数据
        training_data = vn.get_training_data()
        
        # 转换为列表格式
        if hasattr(training_data, 'to_dict'):
            all_data = training_data.to_dict('records')
        elif isinstance(training_data, list):
            all_data = training_data
        else:
            all_data = []
        
        total_count = len(all_data)
        
        # 统计各类型数量
        ddl_count = sum(1 for item in all_data if item.get('training_data_type') == 'ddl')
        sql_count = sum(1 for item in all_data if item.get('training_data_type') == 'sql')
        doc_count = sum(1 for item in all_data if item.get('training_data_type') == 'documentation')
        
        summary = {
            "total_count": total_count,
            "ddl_count": ddl_count,
            "sql_count": sql_count,
            "doc_count": doc_count
        }
        
        # 如果只要统计信息
        if summary_only:
            return jsonify({
                "success": True,
                "summary": summary
            })
        
        # 分页处理
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paged_data = all_data[start_idx:end_idx]
        
        total_pages = (total_count + page_size - 1) // page_size
        
        return jsonify({
            "success": True,
            "summary": summary,
            "data": paged_data,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        })
        
    except Exception as e:
        import traceback
        print(f"[Training Data] 获取失败: {traceback.format_exc()}")
        return jsonify({
            "success": False,
            "message": f"获取训练数据失败: {str(e)}"
        }), 500


def delete_training_data():
    """
    删除训练数据
    
    请求: DELETE /api/training-data
    Body: {
        "ids": ["id1", "id2"],     # 按 ID 删除
        "delete_all": false,       # 删除所有数据
        "type": "sql"              # 按类型删除 (ddl/sql/documentation)
    }
    
    响应: {
        "success": true,
        "message": "已删除 5 条数据",
        "deleted_count": 5
    }
    """
    try:
        data = request.get_json() or {}
        ids = data.get('ids', [])
        delete_all = data.get('delete_all', False)
        data_type = data.get('type')
        
        vn = get_vanna_instance()
        deleted_count = 0
        
        if delete_all:
            # 删除所有数据
            training_data = vn.get_training_data()
            if hasattr(training_data, 'to_dict'):
                all_data = training_data.to_dict('records')
            else:
                all_data = training_data if isinstance(training_data, list) else []
            
            for item in all_data:
                item_id = item.get('id')
                if item_id:
                    try:
                        vn.remove_training_data(item_id)
                        deleted_count += 1
                    except:
                        pass
            
            print(f"[Delete] 已删除所有训练数据: {deleted_count} 条")
            
        elif data_type:
            # 按类型删除
            training_data = vn.get_training_data()
            if hasattr(training_data, 'to_dict'):
                all_data = training_data.to_dict('records')
            else:
                all_data = training_data if isinstance(training_data, list) else []
            
            for item in all_data:
                if item.get('training_data_type') == data_type:
                    item_id = item.get('id')
                    if item_id:
                        try:
                            vn.remove_training_data(item_id)
                            deleted_count += 1
                        except:
                            pass
            
            print(f"[Delete] 已删除类型 '{data_type}' 的训练数据: {deleted_count} 条")
            
        elif ids:
            # 按 ID 删除
            for item_id in ids:
                try:
                    vn.remove_training_data(item_id)
                    deleted_count += 1
                    print(f"[Delete] 已删除: {item_id}")
                except Exception as e:
                    print(f"[Delete] 删除失败 {item_id}: {e}")
        else:
            return jsonify({
                "success": False,
                "message": "请提供 ids、type 或 delete_all 参数"
            }), 400
        
        return jsonify({
            "success": True,
            "message": f"已删除 {deleted_count} 条数据",
            "deleted_count": deleted_count
        })
        
    except Exception as e:
        import traceback
        print(f"[Delete] 删除失败: {traceback.format_exc()}")
        return jsonify({
            "success": False,
            "message": f"删除失败: {str(e)}"
        }), 500


def register_routes(app):
    """注册路由到 Flask app"""
    app.route('/api/train-sql', methods=['POST'])(train_sql)
    app.route('/api/training-data', methods=['GET'])(get_training_data)
    app.route('/api/training-data/delete', methods=['POST'])(delete_training_data)


# 独立运行时的代码
if __name__ == '__main__':
    app = Flask(__name__)
    register_routes(app)
    
    print("="*60)
    print("Vanna SQL 训练 API 服务")
    print("="*60)
    print("\n可用接口:")
    print("  POST   /api/train-sql     - 训练 SQL 文件")
    print("  GET    /api/training-data - 获取训练数据统计")
    print("  DELETE /api/training-data - 删除训练数据")
    print("\n" + "="*60)
    
    app.run(host='0.0.0.0', port=5000, debug=True)
