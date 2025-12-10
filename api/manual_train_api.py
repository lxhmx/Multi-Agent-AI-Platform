"""
手动训练 API
支持手动输入 SQL、DDL 或文档内容进行训练
"""
import sys
from datetime import datetime
from pathlib import Path

from flask import Flask, request, jsonify

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from common.vanna_instance import get_vanna_instance


def train_manual():
    """
    手动输入训练数据
    
    请求: POST /api/train-manual
    Body: {
        "type": "sql",           # sql, ddl, documentation
        "content": "SELECT ...", # 训练内容
        "title": "查询用户",      # 可选，标题
        "keywords": "用户,查询",  # 可选，关键词
        "tags": "用户管理"        # 可选，业务标签
    }
    
    响应: {
        "success": true,
        "message": "训练成功",
        "id": "xxx"
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "success": False,
                "message": "请提供训练数据"
            }), 400
        
        train_type = data.get('type', 'sql')
        content = data.get('content', '').strip()
        title = data.get('title', '').strip()
        keywords = data.get('keywords', '').strip()
        tags = data.get('tags', '').strip()
        
        if not content:
            return jsonify({
                "success": False,
                "message": "训练内容不能为空"
            }), 400
        
        vn = get_vanna_instance()
        
        # 构建元数据
        metadata = []
        if title:
            metadata.append(f"标题: {title}")
        if keywords:
            metadata.append(f"关键词: {keywords}")
        if tags:
            metadata.append(f"标签: {tags}")
        
        metadata_str = '\n'.join(metadata)
        
        # 根据类型训练
        if train_type == 'sql':
            # SQL 查询训练
            question = title if title else f"手动训练_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # 如果有元数据，添加到 SQL 注释中
            if metadata_str:
                content_with_meta = f"-- {metadata_str.replace(chr(10), ' | ')}\n{content}"
            else:
                content_with_meta = content
            
            vn.train(question=question, sql=content_with_meta)
            print(f"[Manual Train] SQL 训练成功: {question}")
            
        elif train_type == 'ddl':
            # DDL 训练
            if metadata_str:
                content_with_meta = f"-- {metadata_str.replace(chr(10), ' | ')}\n{content}"
            else:
                content_with_meta = content
            
            vn.train(ddl=content_with_meta)
            print(f"[Manual Train] DDL 训练成功")
            
        elif train_type == 'documentation':
            # 文档训练
            if metadata_str:
                content_with_meta = f"{metadata_str}\n\n{content}"
            else:
                content_with_meta = content
            
            vn.train(documentation=content_with_meta)
            print(f"[Manual Train] 文档训练成功")
            
        else:
            return jsonify({
                "success": False,
                "message": f"不支持的训练类型: {train_type}"
            }), 400
        
        # 同时保存到文件（按日期存储）
        save_to_file(train_type, content, title)
        
        return jsonify({
            "success": True,
            "message": f"{train_type.upper()} 训练成功",
            "type": train_type
        })
        
    except Exception as e:
        import traceback
        print(f"[Manual Train] 训练失败: {traceback.format_exc()}")
        return jsonify({
            "success": False,
            "message": f"训练失败: {str(e)}"
        }), 500


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
        
        # 生成文件名
        if title:
            # 清理文件名中的非法字符
            safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_title = safe_title[:50]  # 限制长度
            filename = f"{safe_title}_{timestamp}{ext}"
        else:
            filename = f"manual_{train_type}_{timestamp}{ext}"
        
        file_path = base_path / filename
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"[Manual Train] 已保存到文件: {file_path}")
        
    except Exception as e:
        print(f"[Manual Train] 保存文件失败: {e}")


def register_routes(app):
    """注册路由到 Flask app"""
    app.route('/api/train-manual', methods=['POST'])(train_manual)


# 独立运行时的代码
if __name__ == '__main__':
    app = Flask(__name__)
    register_routes(app)
    
    print("=" * 60)
    print("手动训练 API 服务")
    print("=" * 60)
    print("\n可用接口:")
    print("  POST /api/train-manual  - 手动输入训练数据")
    print("\n" + "=" * 60)
    app.run(host='0.0.0.0', port=5005, debug=True)
