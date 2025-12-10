"""
Vanna 文档训练 API
提供文档训练接口，支持 DOC/PDF/Excel 等格式
"""
import os
import sys
import hashlib
from pathlib import Path

from flask import Flask, request, jsonify

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from common.vanna_instance import get_vanna_instance


def get_file_hash(file_path: Path) -> str:
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
            content = item.get('content', '') or ''
            if file_id in str(content):
                return True
        
        return False
    except Exception as e:
        print(f"[Train Document] 检查重复失败: {e}")
        return False


def train_document():
    """
    文档训练接口 - 自动读取 train-document 文件夹下的文档进行训练
    
    请求: POST /api/train-document
    Body: {
        "doc_types": ["doc", "pdf", "excel"]  # 可选，默认训练所有类型
    }
    
    响应: {
        "success": true,
        "message": "文档训练完成",
        "stats": {
            "doc_count": 5,
            "pdf_count": 3,
            "excel_count": 2,
            "total": 10
        }
    }
    """
    try:
        data = request.get_json() or {}
        doc_types = data.get('doc_types', ['doc', 'pdf', 'excel'])
        
        vn = get_vanna_instance()
        
        # 延迟导入数据管理函数
        from api.data_manage_api import get_data_manage_functions, get_db_connection
        funcs = get_data_manage_functions()
        update_training_status = funcs['update_training_status']
        
        # 查询数据库中的文件记录
        file_id_map = {}  # file_path -> db_id
        conn = get_db_connection()
        if conn:
            try:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT id, file_path, file_hash FROM training_files WHERE train_type = 'document'")
                for row in cursor.fetchall():
                    file_id_map[row['file_path']] = row['id']
                cursor.close()
                conn.close()
            except Exception as e:
                print(f"[Train Document] 查询文件记录失败: {e}")
        
        # 文档目录路径
        train_doc_root = PROJECT_ROOT / 'train-document'
        
        stats = {
            'doc_count': 0,
            'pdf_count': 0,
            'excel_count': 0,
            'total': 0,
            'errors': []
        }
        
        # 传递额外参数给训练函数
        context = {
            'file_id_map': file_id_map,
            'update_training_status': update_training_status,
            'vn': vn
        }
        
        print(f"\n[Train Document] 开始训练文档...")
        print(f"[Train Document] 文档根目录: {train_doc_root}")
        
        # 递归扫描整个 train-document 目录
        # 训练 DOC/DOCX/TXT 文档
        if 'doc' in doc_types:
            doc_count = train_doc_files_recursive(vn, train_doc_root, ['.doc', '.docx', '.txt'], stats, context)
            stats['doc_count'] = doc_count
            print(f"[Train Document] DOC 文档训练完成: {doc_count} 个文件")
        
        # 训练 PDF 文档
        if 'pdf' in doc_types:
            pdf_count = train_pdf_files_recursive(vn, train_doc_root, stats, context)
            stats['pdf_count'] = pdf_count
            print(f"[Train Document] PDF 文档训练完成: {pdf_count} 个文件")
        
        # 训练 Excel 文档
        if 'excel' in doc_types:
            excel_count = train_excel_files_recursive(vn, train_doc_root, stats, context)
            stats['excel_count'] = excel_count
            print(f"[Train Document] Excel 文档训练完成: {excel_count} 个文件")
        
        stats['total'] = stats['doc_count'] + stats['pdf_count'] + stats['excel_count']
        
        print(f"[Train Document] 文档训练完成，共训练 {stats['total']} 个文件")
        
        return jsonify({
            "success": True,
            "message": f"文档训练完成，共训练 {stats['total']} 个文件",
            "stats": stats
        })
        
    except Exception as e:
        import traceback
        print(f"[Train Document] 训练失败: {traceback.format_exc()}")
        return jsonify({
            "success": False,
            "message": f"文档训练失败: {str(e)}"
        }), 500


def train_doc_files_recursive(vn, root_dir: Path, extensions: list, stats: dict, context: dict = None) -> int:
    """递归训练 DOC/DOCX/TXT 文档（带去重）"""
    count = 0
    skipped = 0
    
    file_id_map = context.get('file_id_map', {}) if context else {}
    update_training_status = context.get('update_training_status') if context else None
    
    for ext in extensions:
        for file_path in root_dir.rglob(f'*{ext}'):
            db_file_id = file_id_map.get(str(file_path))
            
            try:
                # 计算文件哈希作为唯一 ID
                file_hash = get_file_hash(file_path)
                file_id = f"doc_{file_path.name}_{file_hash[:8]}"
                
                # 检查是否已训练
                if is_already_trained(vn, file_id):
                    print(f"[Train Document] ⊙ {file_path.name} 已训练过，跳过")
                    skipped += 1
                    if db_file_id and update_training_status:
                        update_training_status(db_file_id, 'success', '已训练（跳过重复）', 1)
                    continue
                
                print(f"[Train Document] 训练文档: {file_path.name}")
                content = read_doc_file(file_path)
                
                if content:
                    content_with_meta = f"文件名: {file_path.name}\n文件ID: {file_id}\n\n{content}"
                    vn.train(documentation=content_with_meta)
                    count += 1
                    print(f"[Train Document] ✓ {file_path.name} 训练成功")
                    
                    if db_file_id and update_training_status:
                        update_training_status(db_file_id, 'success', '训练成功 (doc)', 1)
                else:
                    print(f"[Train Document] ✗ {file_path.name} 内容为空，跳过")
                    if db_file_id and update_training_status:
                        update_training_status(db_file_id, 'failed', '文件内容为空')
                    
            except Exception as e:
                error_msg = f"{file_path.name}: {str(e)}"
                stats['errors'].append(error_msg)
                print(f"[Train Document] ✗ {file_path.name} 训练失败: {e}")
                if db_file_id and update_training_status:
                    update_training_status(db_file_id, 'failed', str(e))
    
    if skipped > 0:
        print(f"[Train Document] 跳过 {skipped} 个已训练的文档")
    
    return count


def train_pdf_files_recursive(vn, root_dir: Path, stats: dict, context: dict = None) -> int:
    """递归训练 PDF 文档（带去重）"""
    count = 0
    skipped = 0
    
    file_id_map = context.get('file_id_map', {}) if context else {}
    update_training_status = context.get('update_training_status') if context else None
    
    for file_path in root_dir.rglob('*.pdf'):
        db_file_id = file_id_map.get(str(file_path))
        
        try:
            file_hash = get_file_hash(file_path)
            file_id = f"pdf_{file_path.name}_{file_hash[:8]}"
            
            if is_already_trained(vn, file_id):
                print(f"[Train Document] ⊙ {file_path.name} 已训练过，跳过")
                skipped += 1
                if db_file_id and update_training_status:
                    update_training_status(db_file_id, 'success', '已训练（跳过重复）', 1)
                continue
            
            print(f"[Train Document] 训练 PDF: {file_path.name}")
            content = read_pdf_file(file_path)
            
            if content:
                content_with_meta = f"文件名: {file_path.name}\n文件ID: {file_id}\n\n{content}"
                vn.train(documentation=content_with_meta)
                count += 1
                print(f"[Train Document] ✓ {file_path.name} 训练成功")
                
                if db_file_id and update_training_status:
                    update_training_status(db_file_id, 'success', '训练成功 (pdf)', 1)
            else:
                print(f"[Train Document] ✗ {file_path.name} 内容为空，跳过")
                if db_file_id and update_training_status:
                    update_training_status(db_file_id, 'failed', '文件内容为空')
                
        except Exception as e:
            error_msg = f"{file_path.name}: {str(e)}"
            stats['errors'].append(error_msg)
            print(f"[Train Document] ✗ {file_path.name} 训练失败: {e}")
            if db_file_id and update_training_status:
                update_training_status(db_file_id, 'failed', str(e))
    
    if skipped > 0:
        print(f"[Train Document] 跳过 {skipped} 个已训练的 PDF")
    
    return count


def train_excel_files_recursive(vn, root_dir: Path, stats: dict, context: dict = None) -> int:
    """递归训练 Excel 文档（带去重）"""
    count = 0
    skipped = 0
    
    file_id_map = context.get('file_id_map', {}) if context else {}
    update_training_status = context.get('update_training_status') if context else None
    
    for ext in ['.xlsx', '.xls', '.csv']:
        for file_path in root_dir.rglob(f'*{ext}'):
            db_file_id = file_id_map.get(str(file_path))
            
            try:
                file_hash = get_file_hash(file_path)
                file_id = f"excel_{file_path.name}_{file_hash[:8]}"
                
                if is_already_trained(vn, file_id):
                    print(f"[Train Document] ⊙ {file_path.name} 已训练过，跳过")
                    skipped += 1
                    if db_file_id and update_training_status:
                        update_training_status(db_file_id, 'success', '已训练（跳过重复）', 1)
                    continue
                
                print(f"[Train Document] 训练 Excel: {file_path.name}")
                content = read_excel_file(file_path)
                
                if content:
                    content_with_meta = f"文件名: {file_path.name}\n文件ID: {file_id}\n\n{content}"
                    vn.train(documentation=content_with_meta)
                    count += 1
                    print(f"[Train Document] ✓ {file_path.name} 训练成功")
                    
                    if db_file_id and update_training_status:
                        update_training_status(db_file_id, 'success', '训练成功 (excel)', 1)
                else:
                    print(f"[Train Document] ✗ {file_path.name} 内容为空，跳过")
                    if db_file_id and update_training_status:
                        update_training_status(db_file_id, 'failed', '文件内容为空')
                    
            except Exception as e:
                error_msg = f"{file_path.name}: {str(e)}"
                stats['errors'].append(error_msg)
                print(f"[Train Document] ✗ {file_path.name} 训练失败: {e}")
                if db_file_id and update_training_status:
                    update_training_status(db_file_id, 'failed', str(e))
    
    if skipped > 0:
        print(f"[Train Document] 跳过 {skipped} 个已训练的 Excel")
    
    return count


def read_doc_file(file_path: Path) -> str:
    """读取 DOC/DOCX/TXT 文件内容"""
    try:
        if file_path.suffix.lower() in ['.doc', '.docx']:
            # 需要 python-docx 库
            try:
                from docx import Document
                doc = Document(file_path)
                content = '\n'.join([para.text for para in doc.paragraphs if para.text.strip()])
                return content
            except ImportError:
                print(f"[Train Document] 警告: 需要安装 python-docx 库来读取 .docx 文件")
                print(f"[Train Document] 请运行: pip install python-docx")
                return None
        else:
            # TXT 文件
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
    except Exception as e:
        print(f"[Train Document] 读取文件失败 {file_path.name}: {e}")
        return None


def read_pdf_file(file_path: Path) -> str:
    """读取 PDF 文件内容"""
    try:
        # 需要 PyPDF2 或 pdfplumber 库
        try:
            import pdfplumber
            with pdfplumber.open(file_path) as pdf:
                content = []
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        content.append(text)
                return '\n'.join(content)
        except ImportError:
            try:
                from PyPDF2 import PdfReader
                reader = PdfReader(file_path)
                content = []
                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        content.append(text)
                return '\n'.join(content)
            except ImportError:
                print(f"[Train Document] 警告: 需要安装 pdfplumber 或 PyPDF2 库来读取 PDF 文件")
                print(f"[Train Document] 请运行: pip install pdfplumber 或 pip install PyPDF2")
                return None
    except Exception as e:
        print(f"[Train Document] 读取 PDF 失败 {file_path.name}: {e}")
        return None


def read_excel_file(file_path: Path) -> str:
    """读取 Excel 文件内容"""
    try:
        import pandas as pd
        
        if file_path.suffix.lower() == '.csv':
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)
        
        # 将 Excel 内容转换为文档描述
        content = f"文件名: {file_path.name}\n\n"
        content += f"数据表包含 {len(df)} 行，{len(df.columns)} 列\n\n"
        content += f"列名: {', '.join(df.columns.tolist())}\n\n"
        content += "数据示例:\n"
        content += df.head(10).to_string(index=False)
        
        return content
        
    except Exception as e:
        print(f"[Train Document] 读取 Excel 失败 {file_path.name}: {e}")
        return None


def register_routes(app):
    """注册路由到 Flask app"""
    app.route('/api/train-document', methods=['POST'])(train_document)


# 独立运行时的代码
if __name__ == '__main__':
    app = Flask(__name__)
    register_routes(app)
    
    print("=" * 60)
    print("Vanna 文档训练 API 服务")
    print("=" * 60)
    print("\n可用接口:")
    print("  POST /api/train-document  - 训练文档")
    print("\n" + "=" * 60)
    app.run(host='0.0.0.0', port=5002, debug=True)
