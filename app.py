"""
Vanna Text2SQL 统一启动入口
整合所有 API 路由到一个服务
"""
import sys
from pathlib import Path
from flask import Flask, jsonify
from flask_cors import CORS

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# 创建 Flask 应用
app = Flask(__name__)

# 启用 CORS 支持
CORS(app, resources={r"/api/*": {"origins": "*"}})

# 导入各个模块的路由注册函数
from api.train_sql_api import register_routes as register_train_sql
from api.train_document_api import register_routes as register_train_document
from api.ask_api import register_routes as register_query
from api.upload_api import register_routes as register_upload
from api.manual_train_api import register_routes as register_manual_train
from api.data_manage_api import register_routes as register_data_manage, init_table

# 初始化数据库表
init_table()

# 注册所有路由
register_train_sql(app)
register_train_document(app)
register_query(app)
register_upload(app)
register_manual_train(app)
register_data_manage(app)


@app.route('/api/health', methods=['GET'])
def health():
    """健康检查"""
    return jsonify({"status": "ok", "service": "vanna-api"})


if __name__ == '__main__':
    print("=" * 60)
    print("Vanna Text2SQL API 服务")
    print("=" * 60)
    print("\n可用接口:")
    print("  训练接口:")
    print("    POST /api/train-sql         - 训练 SQL 文件")
    print("    POST /api/train-document    - 训练文档文件")
    print("    POST /api/train-manual      - 手动输入训练")
    print("    POST /api/upload            - 上传训练文件")
    print("\n  数据管理接口:")
    print("    GET  /api/data-manage/stats    - 获取统计数据")
    print("    GET  /api/data-manage/activity - 获取活跃度")
    print("    GET  /api/data-manage/files    - 获取文件列表")
    print("    DELETE /api/data-manage/files  - 删除文件记录")
    print("\n  查询接口:")
    print("    POST /api/query             - 自然语言查询")
    print("\n  其他:")
    print("    GET  /api/health            - 健康检查")
    print("\n" + "=" * 60)
    app.run(host='0.0.0.0', port=5000, debug=True)
