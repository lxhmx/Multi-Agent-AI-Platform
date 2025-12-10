"""
文件上传 API
支持上传 .sql, .doc, .docx, .pdf, .xls, .xlsx 文件
文件按日期存储到 train-sql 或 train-document 目录
"""
import os
import sys
import hashlib
from datetime import datetime, date
from pathlib import Path

from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 导入数据管理模块（延迟导入，避免循环依赖）
def get_data_manage_functions():
    """获取数据管理函数"""
    try:
        from api.data_manage_api import insert_training_file, calculate_file_hash
        return insert_training_file, calculate_file_hash
    except ImportError:
        from data_manage_api import insert_training_file, calculate_file_hash
        return insert_training_file, calculate_file_hash

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {
    'sql': ['.sql'],
    'document': ['.doc', '.docx', '.pdf', '.xls', '.xlsx', '.txt', '.csv']
}


def get_file_type(filename: str) -> str:
    """根据文件扩展名判断文件类型"""
    ext = Path(filename).suffix.lower()
    if ext in ALLOWED_EXTENSIONS['sql']:
        return 'sql'
    elif ext in ALLOWED_EXTENSIONS['document']:
        return 'document'
    return None


def get_upload_path(file_type: str) -> Path:
    """
    获取上传路径，按日期创建文件夹
    格式: train-sql/2025-12-09/ 或 train-document/2025-12-09/
    """
    today = datetime.now().strftime('%Y-%m-%d')
    
    if file_type == 'sql':
        base_path = PROJECT_ROOT / 'train-sql' / today
    else:
        base_path = PROJECT_ROOT / 'train-document' / today
    
    # 创建目录
    base_path.mkdir(parents=True, exist_ok=True)
    return base_path


def upload_file():
    """
    文件上传接口
    
    请求: POST /api/upload
    Content-Type: multipart/form-data
    Body: file (文件), train_type (可选，sql/document)
    
    响应: {
        "success": true,
        "message": "上传成功",
        "file_name": "example.sql",
        "file_path": "train-sql/2025-12-09/example.sql",
        "train_type": "sql"
    }
    """
    try:
        # 检查是否有文件
        if 'file' not in request.files:
            return jsonify({
                "success": False,
                "message": "请选择要上传的文件"
            }), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({
                "success": False,
                "message": "请选择要上传的文件"
            }), 400
        
        # 获取原始文件名
        original_filename = file.filename
        
        # 判断文件类型
        file_type = get_file_type(original_filename)
        
        if not file_type:
            return jsonify({
                "success": False,
                "message": f"不支持的文件类型，请上传 .sql, .doc, .docx, .pdf, .xls, .xlsx 格式的文件"
            }), 400
        
        # 可以通过参数强制指定类型
        train_type = request.form.get('train_type')
        if train_type and train_type in ['sql', 'document']:
            file_type = train_type
        
        # 获取上传路径
        upload_path = get_upload_path(file_type)
        
        # 生成安全的文件名（保留原始名称，添加时间戳避免重复）
        timestamp = datetime.now().strftime('%H%M%S')
        filename = secure_filename(original_filename)
        name, ext = os.path.splitext(filename)
        
        # 如果文件名为空（中文文件名可能被清空），使用时间戳
        if not name:
            name = f"file_{timestamp}"
        
        final_filename = f"{name}_{timestamp}{ext}"
        file_path = upload_path / final_filename
        
        # 保存文件
        file.save(str(file_path))
        
        print(f"[Upload] 文件已保存: {file_path}")
        
        # 计算相对路径
        relative_path = file_path.relative_to(PROJECT_ROOT)
        
        # 获取文件信息
        file_size = file_path.stat().st_size
        file_ext = ext.lstrip('.').lower() if ext else 'unknown'
        
        # 插入数据库记录
        try:
            insert_training_file, calculate_file_hash = get_data_manage_functions()
            file_hash = calculate_file_hash(file_path)
            record_id = insert_training_file(
                file_name=final_filename,
                file_path=str(relative_path),
                file_type=file_ext,
                train_type=file_type,
                file_size=file_size,
                file_hash=file_hash,
                upload_date=date.today()
            )
            print(f"[Upload] 数据库记录已插入, ID: {record_id}")
        except Exception as db_err:
            import traceback
            print(f"[Upload] 插入数据库记录失败: {db_err}")
            print(traceback.format_exc())
        
        return jsonify({
            "success": True,
            "message": "上传成功，请点击对应的训练按钮开始训练",
            "file_name": final_filename,
            "file_path": str(relative_path),
            "train_type": file_type,
            "file_size": file_size
        })
        
    except Exception as e:
        import traceback
        print(f"[Upload] 上传失败: {traceback.format_exc()}")
        return jsonify({
            "success": False,
            "message": f"上传失败: {str(e)}"
        }), 500


def register_routes(app):
    """注册路由到 Flask app"""
    app.route('/api/upload', methods=['POST'])(upload_file)


# 独立运行时的代码
if __name__ == '__main__':
    app = Flask(__name__)
    register_routes(app)
    
    print("=" * 60)
    print("文件上传 API 服务")
    print("=" * 60)
    print("\n可用接口:")
    print("  POST /api/upload  - 上传训练文件")
    print("\n" + "=" * 60)
    app.run(host='0.0.0.0', port=5003, debug=True)
