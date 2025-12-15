"""
训练 API (FastAPI 版本)
提供 SQL 训练、文档训练、手动训练接口
"""
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Depends
from fastapi import Query as QueryParam
from pydantic import BaseModel

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from common.vanna_instance import get_vanna_instance
from common.dependencies import get_current_user

# 创建路由器
router = APIRouter(prefix="/api", tags=["训练"])


# ==================== Pydantic 模型 ====================

class TrainManualRequest(BaseModel):
    type: str = "sql"  # sql, ddl, documentation
    content: str
    title: Optional[str] = None
    keywords: Optional[str] = None
    tags: Optional[str] = None

class TrainDocumentRequest(BaseModel):
    doc_types: Optional[List[str]] = ["doc", "pdf", "excel"]

class DeleteTrainingDataRequest(BaseModel):
    ids: Optional[List[str]] = None
    delete_all: bool = False
    type: Optional[str] = None


# ==================== 训练接口 ====================

@router.post("/train-sql")
async def train_sql(user=Depends(get_current_user)):
    """训练 SQL 文件"""
    import os
    import glob
    import hashlib
    from api.data_manage_api import get_db_connection, update_training_status
    
    try:
        vn = get_vanna_instance()
        
        # 获取 train-sql 文件夹路径
        train_sql_path = os.path.join(PROJECT_ROOT, 'train-sql')
        
        if not os.path.exists(train_sql_path):
            os.makedirs(train_sql_path, exist_ok=True)
            return {
                "success": False,
                "message": f"train-sql 文件夹为空，请添加 .sql 文件",
                "trained_files": [],
                "total_count": 0
            }
        
        # 获取所有 .sql 文件
        sql_files = glob.glob(os.path.join(train_sql_path, '**', '*.sql'), recursive=True)
        sql_files = list(set(sql_files))
        
        if not sql_files:
            return {
                "success": False,
                "message": "train-sql 文件夹中没有找到 .sql 文件",
                "trained_files": [],
                "total_count": 0
            }
        
        trained_files = []
        skipped_files = []
        errors = []
        
        def get_file_hash(file_path):
            md5_hash = hashlib.md5()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    md5_hash.update(chunk)
            return md5_hash.hexdigest()
        
        def is_already_trained(file_id):
            try:
                training_data = vn.get_training_data()
                if hasattr(training_data, 'to_dict'):
                    all_data = training_data.to_dict('records')
                elif isinstance(training_data, list):
                    all_data = training_data
                else:
                    return False
                for item in all_data:
                    content = item.get('content', '') or item.get('question', '')
                    if file_id in str(content):
                        return True
                return False
            except:
                return False
        
        print(f"[Train SQL] 开始训练 SQL 文件，共 {len(sql_files)} 个文件")
        
        for sql_file in sql_files:
            file_name = os.path.basename(sql_file)
            
            try:
                file_hash = get_file_hash(sql_file)
                file_id = f"sql_{file_name}_{file_hash[:8]}"
                
                if is_already_trained(file_id):
                    print(f"[Train SQL] ⊙ {file_name} 已训练过，跳过")
                    skipped_files.append(file_name)
                    continue
                
                with open(sql_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                
                if not content:
                    errors.append(f"{file_name}: 文件为空")
                    continue
                
                content_with_id = f"-- 文件ID: {file_id}\n{content}"
                content_upper = content.upper()
                
                if content_upper.startswith('CREATE') or content_upper.startswith('ALTER'):
                    vn.train(ddl=content_with_id)
                    trained_files.append({"file": file_name, "type": "ddl"})
                    print(f"[Train SQL] ✓ {file_name} (DDL) 训练成功")
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
                    print(f"[Train SQL] ✓ {file_name} (SQL) 训练成功")
                else:
                    vn.train(ddl=content_with_id)
                    trained_files.append({"file": file_name, "type": "ddl"})
                    print(f"[Train SQL] ✓ {file_name} (DDL) 训练成功")
                    
            except Exception as e:
                errors.append(f"{file_name}: {str(e)}")
                print(f"[Train SQL] ✗ {file_name} 训练失败: {e}")
        
        message = f"训练完成：新增 {len(trained_files)} 个"
        if skipped_files:
            message += f"，跳过 {len(skipped_files)} 个已训练"
        
        return {
            "success": True,
            "message": message,
            "trained_files": trained_files,
            "skipped_files": skipped_files,
            "trained_count": len(trained_files),
            "skipped_count": len(skipped_files),
            "total_files": len(sql_files),
            "errors": errors if errors else None
        }
        
    except Exception as e:
        print(f"[Train SQL] 训练异常: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"训练失败: {str(e)}")


@router.post("/train-document")
async def train_document(req: TrainDocumentRequest = None, user=Depends(get_current_user)):
    """训练文档文件"""
    import hashlib
    
    try:
        doc_types = req.doc_types if req else ["doc", "pdf", "excel"]
        vn = get_vanna_instance()
        
        train_doc_root = PROJECT_ROOT / 'train-document'
        
        if not train_doc_root.exists():
            train_doc_root.mkdir(parents=True, exist_ok=True)
            return {
                "success": False,
                "message": "train-document 文件夹为空",
                "stats": {"total": 0}
            }
        
        stats = {'doc_count': 0, 'pdf_count': 0, 'excel_count': 0, 'total': 0, 'errors': []}
        
        def get_file_hash(file_path):
            hash_md5 = hashlib.md5()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        
        def is_already_trained(file_id):
            try:
                training_data = vn.get_training_data()
                if hasattr(training_data, 'to_dict'):
                    all_data = training_data.to_dict('records')
                elif isinstance(training_data, list):
                    all_data = training_data
                else:
                    return False
                for item in all_data:
                    content = item.get('content', '') or ''
                    if file_id in str(content):
                        return True
                return False
            except:
                return False
        
        def read_txt_file(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        
        print(f"[Train Document] 开始训练文档...")
        
        # 训练 TXT 文档
        if 'doc' in doc_types:
            for file_path in train_doc_root.rglob('*.txt'):
                try:
                    file_hash = get_file_hash(file_path)
                    file_id = f"doc_{file_path.name}_{file_hash[:8]}"
                    
                    if is_already_trained(file_id):
                        print(f"[Train Document] ⊙ {file_path.name} 已训练过，跳过")
                        continue
                    
                    content = read_txt_file(file_path)
                    if content:
                        content_with_meta = f"文件名: {file_path.name}\n文件ID: {file_id}\n\n{content}"
                        vn.train(documentation=content_with_meta)
                        stats['doc_count'] += 1
                        print(f"[Train Document] ✓ {file_path.name} 训练成功")
                except Exception as e:
                    stats['errors'].append(f"{file_path.name}: {str(e)}")
        
        stats['total'] = stats['doc_count'] + stats['pdf_count'] + stats['excel_count']
        
        print(f"[Train Document] 文档训练完成，共训练 {stats['total']} 个文件")
        
        return {
            "success": True,
            "message": f"文档训练完成，共训练 {stats['total']} 个文件",
            "stats": stats
        }
        
    except Exception as e:
        print(f"[Train Document] 训练失败: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"文档训练失败: {str(e)}")


def save_to_file(train_type: str, content: str, title: str = None):
    """将训练内容保存到文件"""
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        timestamp = datetime.now().strftime('%H%M%S')
        
        if train_type in ['sql', 'ddl']:
            base_path = PROJECT_ROOT / 'train-sql' / today
            ext = '.sql'
        else:
            base_path = PROJECT_ROOT / 'train-document' / today
            ext = '.txt'
        
        base_path.mkdir(parents=True, exist_ok=True)
        
        if title:
            safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_title = safe_title[:50]
            filename = f"{safe_title}_{timestamp}{ext}"
        else:
            filename = f"manual_{train_type}_{timestamp}{ext}"
        
        file_path = base_path / filename
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"[Manual Train] 已保存到文件: {file_path}")
        
    except Exception as e:
        print(f"[Manual Train] 保存文件失败: {e}")


@router.post("/train-manual")
async def train_manual(req: TrainManualRequest):
    """手动输入训练数据"""
    
    try:
        content = req.content.strip()
        
        if not content:
            raise HTTPException(status_code=400, detail="训练内容不能为空")
        
        vn = get_vanna_instance()
        
        # 构建元数据
        metadata = []
        if req.title:
            metadata.append(f"标题: {req.title}")
        if req.keywords:
            metadata.append(f"关键词: {req.keywords}")
        if req.tags:
            metadata.append(f"标签: {req.tags}")
        
        metadata_str = '\n'.join(metadata)
        
        # 根据类型训练
        if req.type == 'sql':
            question = req.title if req.title else f"手动训练_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            if metadata_str:
                content_with_meta = f"-- {metadata_str.replace(chr(10), ' | ')}\n{content}"
            else:
                content_with_meta = content
            vn.train(question=question, sql=content_with_meta)
            print(f"[Manual Train] SQL 训练成功: {question}")
            
        elif req.type == 'ddl':
            if metadata_str:
                content_with_meta = f"-- {metadata_str.replace(chr(10), ' | ')}\n{content}"
            else:
                content_with_meta = content
            vn.train(ddl=content_with_meta)
            print(f"[Manual Train] DDL 训练成功")
            
        elif req.type == 'documentation':
            if metadata_str:
                content_with_meta = f"{metadata_str}\n\n{content}"
            else:
                content_with_meta = content
            vn.train(documentation=content_with_meta)
            print(f"[Manual Train] 文档训练成功")
            
        else:
            raise HTTPException(status_code=400, detail=f"不支持的训练类型: {req.type}")
        
        # 保存到文件
        save_to_file(req.type, content, req.title)
        
        return {
            "success": True,
            "message": f"{req.type.upper()} 训练成功",
            "type": req.type
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Manual Train] 训练失败: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"训练失败: {str(e)}")


# ==================== 训练数据管理接口 ====================

@router.get("/training-data")
async def get_training_data(
    page: int = QueryParam(1, ge=1),
    page_size: int = QueryParam(50, ge=1, le=100),
    summary_only: bool = QueryParam(False)
):
    """获取训练数据统计"""
    try:
        vn = get_vanna_instance()
        training_data = vn.get_training_data()
        
        if hasattr(training_data, 'to_dict'):
            all_data = training_data.to_dict('records')
        elif isinstance(training_data, list):
            all_data = training_data
        else:
            all_data = []
        
        total_count = len(all_data)
        ddl_count = sum(1 for item in all_data if item.get('training_data_type') == 'ddl')
        sql_count = sum(1 for item in all_data if item.get('training_data_type') == 'sql')
        doc_count = sum(1 for item in all_data if item.get('training_data_type') == 'documentation')
        
        summary = {
            "total_count": total_count,
            "ddl_count": ddl_count,
            "sql_count": sql_count,
            "doc_count": doc_count
        }
        
        if summary_only:
            return {"success": True, "summary": summary}
        
        # 分页处理
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paged_data = all_data[start_idx:end_idx]
        total_pages = (total_count + page_size - 1) // page_size
        
        return {
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
        }
        
    except Exception as e:
        print(f"[Training Data] 获取失败: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"获取训练数据失败: {str(e)}")


@router.post("/training-data/delete")
async def delete_training_data(req: DeleteTrainingDataRequest):
    """删除训练数据"""
    try:
        vn = get_vanna_instance()
        deleted_count = 0
        
        if req.delete_all:
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
            
        elif req.type:
            training_data = vn.get_training_data()
            if hasattr(training_data, 'to_dict'):
                all_data = training_data.to_dict('records')
            else:
                all_data = training_data if isinstance(training_data, list) else []
            
            for item in all_data:
                if item.get('training_data_type') == req.type:
                    item_id = item.get('id')
                    if item_id:
                        try:
                            vn.remove_training_data(item_id)
                            deleted_count += 1
                        except:
                            pass
            
            print(f"[Delete] 已删除类型 '{req.type}' 的训练数据: {deleted_count} 条")
            
        elif req.ids:
            for item_id in req.ids:
                try:
                    vn.remove_training_data(item_id)
                    deleted_count += 1
                    print(f"[Delete] 已删除: {item_id}")
                except Exception as e:
                    print(f"[Delete] 删除失败 {item_id}: {e}")
        else:
            raise HTTPException(status_code=400, detail="请提供 ids、type 或 delete_all 参数")
        
        return {
            "success": True,
            "message": f"已删除 {deleted_count} 条数据",
            "deleted_count": deleted_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Delete] 删除失败: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")
