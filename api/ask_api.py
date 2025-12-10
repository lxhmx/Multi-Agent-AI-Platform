"""
Vanna 问答 API
提供自然语言查询接口
"""
import os
import sys
import traceback
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path

from flask import Flask, request, jsonify, Response
import mysql.connector
import pandas as pd

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from common.vanna_instance import get_vanna_instance
from common.langchain_llm import stream_chat_response
from common.conn_mysql import get_mysql_connection
from common.langchain_agent import run_agent_stream


def query():
    """
    查询接口 - 根据用户问题生成 SQL 并执行查询，返回人性化的回答
    
    请求: POST /api/query
    Body: {"question": "查询所有闸门设备"}
    
    响应: {
        "success": true,
        "question": "查询所有闸门设备",
        "answer": "根据查询结果，系统中共有10个闸门设备...",
        "sql": "SELECT * FROM att_irrd_i_st_base",
        "table": {...},
        "chart": {...},
        "row_count": 10
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'question' not in data:
            return jsonify({
                "success": False,
                "message": "请提供 question 参数"
            }), 400
        
        question = data['question'].strip()
        
        if not question:
            return jsonify({
                "success": False,
                "message": "问题不能为空"
            }), 400
        
        vn = get_vanna_instance()
        
        print(f"\n[Query] 用户问题: {question}")
        
        # 生成 SQL
        sql = vn.generate_sql(question)
        
        print(f"[Query] 生成的 SQL: {sql}")
        
        # 检查是否成功生成 SQL（如果返回的是错误说明或空值）
        if not sql or not sql.strip():
            return jsonify({
                "success": False,
                "message": "抱歉，我无法理解您的问题。可能的原因：\n1. 数据库中没有相关的表结构\n2. 问题描述不够清晰，请尝试换一种方式描述您的问题。",
                "question": question
            })
        
        # 检查返回的是否是 SQL 语句（而不是错误说明）
        sql_upper = sql.strip().upper()
        if not sql_upper.startswith('SELECT'):
            # 返回的不是 SQL，而是错误说明
            return jsonify({
                "success": False,
                "message": "抱歉，我无法理解您的问题。可能的原因：\n1. 数据库中没有相关的表结构\n2. 问题描述不够清晰，请尝试换一种方式描述您的问题。",
                "question": question,
                "detail": sql  # 将大模型的详细说明放在 detail 字段
            })
        
        # 检查 SQL 是否有效
        if not vn.is_sql_valid(sql):
            return jsonify({
                "success": False,
                "question": question,
                "sql": sql,
                "message": "抱歉，您的问题可能涉及数据修改操作，目前仅支持数据查询。",
                "data": None,
                "row_count": 0
            })
        
        # 执行 SQL 查询
        try:
            print(f"[Query] 连接数据库并执行查询...")
            conn = get_mysql_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql)
            results = cursor.fetchall()
            cursor.close()
            conn.close()
            
            print(f"[Query] 查询成功，返回 {len(results)} 条记录")
            
            # 处理结果中的特殊类型
            def convert_value(obj):
                if isinstance(obj, (datetime, date)):
                    return obj.isoformat()
                elif isinstance(obj, Decimal):
                    return float(obj)
                elif isinstance(obj, bytes):
                    return obj.decode('utf-8', errors='ignore')
                return obj
            
            # 转换结果
            converted_results = []
            for row in results:
                converted_row = {k: convert_value(v) for k, v in row.items()}
                converted_results.append(converted_row)
            
            # 创建 DataFrame
            df = pd.DataFrame(converted_results) if converted_results else pd.DataFrame()
            
            # ========== 生成人性化回答 ==========
            answer = generate_human_answer(vn, question, sql, df)
            
            # ========== 生成表格数据（精简版） ==========
            table_data = generate_table_data(df)
            
            # ========== 生成图表配置 ==========
            chart_config = generate_chart_config(vn, question, sql, df)
            
            return jsonify({
                "success": True,
                "question": question,
                "answer": answer,
                "sql": sql,
                "table": table_data,
                "chart": chart_config,
                "row_count": len(converted_results)
            })
            
        except mysql.connector.Error as db_error:
            print(f"[Query] 数据库错误: {db_error}")
            return jsonify({
                "success": False,
                "question": question,
                "sql": sql,
                "message": f"抱歉，查询执行时遇到问题：{str(db_error)}",
                "data": None
            })
        
    except Exception as e:
        print(f"[Query] 异常: {traceback.format_exc()}")
        return jsonify({
            "success": False,
            "message": f"抱歉，处理您的问题时出现错误，请稍后重试。"
        }), 500


def generate_human_answer(vn, question: str, sql: str, df) -> str:
    """使用大模型生成人性化的回答"""
    if df.empty:
        return "根据您的查询条件，暂未找到相关数据。您可以尝试调整查询条件后再试。"
    
    try:
        # 构建提示词，让大模型生成人性化回答
        row_count = len(df)
        col_count = len(df.columns)
        
        # 获取数据摘要
        if row_count <= 10:
            data_preview = df.to_markdown(index=False)
        else:
            data_preview = df.head(10).to_markdown(index=False)
            data_preview += f"\n\n... 共 {row_count} 条记录"
        
        # 使用 vn 的 submit_prompt 生成回答
        prompt = [
            vn.system_message(
                "你是一个友好的数据分析助手。用户提出了一个数据查询问题，系统已经执行了SQL查询并获得了结果。"
                "请根据查询结果，用自然、易懂的语言回答用户的问题。"
                "要求：\n"
                "1. 直接回答用户的问题，不要提及SQL或技术细节\n"
                "2. 如果数据量大，给出关键统计信息（如总数、最大值、最小值等）\n"
                "3. 如果有明显的数据特征或趋势，简要说明\n"
                "4. 回答要简洁明了，控制在200字以内\n"
                "5. 使用中文回答"
            ),
            vn.user_message(
                f"用户问题：{question}\n\n"
                f"查询结果（共{row_count}条记录，{col_count}个字段）：\n{data_preview}"
            )
        ]
        
        answer = vn.submit_prompt(prompt)
        print(f"[Query] 生成回答: {answer[:100]}..." if len(answer) > 100 else f"[Query] 生成回答: {answer}")
        return answer
        
    except Exception as e:
        print(f"[Query] 生成回答失败: {e}")
        # 降级处理：返回基础统计信息
        return f"查询完成，共找到 {len(df)} 条相关记录。"


def generate_table_data(df, sql: str = None) -> dict:
    """生成前端友好的表格数据，自动生成中文列名"""
    if df.empty:
        return {"columns": [], "rows": [], "total": 0}
    
    # 限制返回的行数，避免数据量过大
    max_rows = 100
    display_df = df.head(max_rows)
    
    # 生成列定义
    columns = []
    for col in display_df.columns:
        # 自动转换列名为更友好的中文标题
        title = format_column_name(col)
        columns.append({
            "field": col,
            "title": title,
            "sortable": True
        })
    
    # 生成行数据
    rows = display_df.to_dict('records')
    
    return {
        "columns": columns,
        "rows": rows,
        "total": len(df),
        "displayed": len(display_df)
    }


def format_column_name(col_name: str) -> str:
    """
    将数据库列名转换为友好的中文标题
    规则：
    1. 常见缩写转换（id -> 编号, name -> 名称等）
    2. 下划线转空格，首字母大写
    3. 保留原始列名作为备选
    """
    # 常见字段的中文映射（只保留最通用的）
    common_fields = {
        'id': '编号',
        'name': '名称',
        'code': '代码',
        'status': '状态',
        'type': '类型',
        'create_time': '创建时间',
        'update_time': '更新时间',
        'create_by': '创建人',
        'update_by': '更新人',
        'del_flag': '删除标志',
        'tenant_id': '租户ID',
        'dept_id': '部门ID',
        'note': '备注',
        'remark': '备注',
    }
    
    # 如果是常见字段，直接返回中文
    if col_name.lower() in common_fields:
        return common_fields[col_name.lower()]
    
    # 尝试智能转换
    # 例如: irr_name -> 灌区名称, pump_code -> 水泵代码
    if col_name.endswith('_name'):
        prefix = col_name[:-5]
        return f"{prefix.upper()} 名称"
    elif col_name.endswith('_code'):
        prefix = col_name[:-5]
        return f"{prefix.upper()} 代码"
    elif col_name.endswith('_id'):
        prefix = col_name[:-3]
        return f"{prefix.upper()} ID"
    elif col_name.endswith('_time'):
        prefix = col_name[:-5]
        return f"{prefix.replace('_', ' ').title()} 时间"
    
    # 默认：下划线转空格，首字母大写
    return col_name.replace('_', ' ').title()


def generate_chart_config(vn, question: str, sql: str, df) -> dict:
    """生成图表配置"""
    if df.empty or len(df) < 2:
        return None
    
    try:
        # 检查是否适合生成图表
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        
        if not numeric_cols:
            return None
        
        # 使用大模型生成 Plotly 图表代码
        df_info = f"列名: {list(df.columns)}\n数据类型: {df.dtypes.to_dict()}\n行数: {len(df)}"
        
        plotly_code = vn.generate_plotly_code(
            question=question,
            sql=sql,
            df_metadata=df_info
        )
        
        if plotly_code:
            print(f"[Query] 生成图表代码: {plotly_code[:100]}...")
            
            # 执行代码生成图表
            try:
                local_vars = {'df': df}
                exec(plotly_code, {"__builtins__": __builtins__}, local_vars)
                
                if 'fig' in local_vars:
                    fig = local_vars['fig']
                    # 返回 Plotly JSON 配置
                    return {
                        "type": "plotly",
                        "config": fig.to_json()
                    }
            except Exception as exec_error:
                print(f"[Query] 执行图表代码失败: {exec_error}")
        
        # 降级处理：生成简单图表配置
        return generate_simple_chart(df, numeric_cols)
        
    except Exception as e:
        print(f"[Query] 生成图表失败: {e}")
        return None


def generate_simple_chart(df, numeric_cols: list) -> dict:
    """生成简单的图表配置"""
    if df.empty or not numeric_cols:
        return None
    
    # 选择第一个数值列
    value_col = numeric_cols[0]
    
    # 尝试找一个分类列作为 X 轴
    non_numeric_cols = [col for col in df.columns if col not in numeric_cols]
    label_col = non_numeric_cols[0] if non_numeric_cols else df.index.name or 'index'
    
    # 限制数据点数量
    chart_df = df.head(20)
    
    return {
        "type": "bar",
        "data": {
            "labels": chart_df[label_col].tolist() if label_col in chart_df.columns else list(range(len(chart_df))),
            "datasets": [{
                "label": value_col,
                "data": chart_df[value_col].tolist()
            }]
        },
        "options": {
            "responsive": True,
            "title": f"{value_col} 分布"
        }
    }


def query_stream():
    """
    流式查询接口 - 使用 SSE 协议逐字返回回答
    
    请求: POST /api/query-stream
    Body: {"question": "查询所有闸门设备"}
    
    响应: SSE 事件流
    - event: sql       -> SQL 语句
    - event: answer    -> 逐字返回的回答内容
    - event: table     -> 表格数据 (JSON)
    - event: done      -> 完成信号
    - event: error     -> 错误信息
    """
    import json
    
    # 必须在生成器外部获取请求数据，因为生成器延迟执行时请求上下文可能已失效
    data = request.get_json()
    
    if not data or 'question' not in data:
        def error_gen():
            yield f"event: error\ndata: {json.dumps({'message': '请提供 question 参数'}, ensure_ascii=False)}\n\n"
        return Response(error_gen(), mimetype='text/event-stream')
    
    question = data['question'].strip()
    # 获取会话 ID（用于记忆功能，前端传入）
    session_id = data.get('session_id', None)
    
    if not question:
        def error_gen():
            yield f"event: error\ndata: {json.dumps({'message': '问题不能为空'}, ensure_ascii=False)}\n\n"
        return Response(error_gen(), mimetype='text/event-stream')
    
    def generate():
        try:
            vn = get_vanna_instance()
            
            print(f"\n[Query Stream] 用户问题: {question}")
            
            # 1. 生成 SQL
            sql = vn.generate_sql(question)
            print(f"[Query Stream] 生成的 SQL: {sql}")
            
            if not sql or not sql.strip():
                yield f"event: error\ndata: {json.dumps({'message': '抱歉，我无法理解您的问题。请尝试换一种方式描述。'}, ensure_ascii=False)}\n\n"
                return
            
            sql_upper = sql.strip().upper()
            if not sql_upper.startswith('SELECT'):
                yield f"event: error\ndata: {json.dumps({'message': '抱歉，我无法理解您的问题。请尝试换一种方式描述。'}, ensure_ascii=False)}\n\n"
                return
            
            # 2. 执行 SQL 查询
            try:
                conn = get_mysql_connection()
                cursor = conn.cursor(dictionary=True)
                cursor.execute(sql)
                results = cursor.fetchall()
                cursor.close()
                conn.close()
                
                print(f"[Query Stream] 查询成功，返回 {len(results)} 条记录")
                
                # 处理结果中的特殊类型
                def convert_value(obj):
                    if isinstance(obj, (datetime, date)):
                        return obj.isoformat()
                    elif isinstance(obj, Decimal):
                        return float(obj)
                    elif isinstance(obj, bytes):
                        return obj.decode('utf-8', errors='ignore')
                    return obj
                
                converted_results = []
                for row in results:
                    converted_row = {k: convert_value(v) for k, v in row.items()}
                    converted_results.append(converted_row)
                
                df = pd.DataFrame(converted_results) if converted_results else pd.DataFrame()
                
                # 3. 生成表格数据
                table_data = generate_table_data(df)
                
                # 4. 流式生成人性化回答（使用 LangChain）
                if df.empty:
                    yield f"event: answer\ndata: 根据您的查询条件，暂未找到相关数据。您可以尝试调整查询条件后再试。\n\n"
                else:
                    # 构建提示词
                    row_count = len(df)
                    col_count = len(df.columns)
                    
                    if row_count <= 10:
                        data_preview = df.to_markdown(index=False)
                    else:
                        data_preview = df.head(10).to_markdown(index=False)
                        data_preview += f"\n\n... 共 {row_count} 条记录"
                    
                    # 系统提示词
                    system_prompt = (
                        "你是一个友好的数据分析助手。用户提出了一个数据查询问题，系统已经执行了SQL查询并获得了结果。"
                        "请根据查询结果，用自然、易懂的语言回答用户的问题。"
                        "要求：\n"
                        "1. 直接回答用户的问题，不要提及SQL或技术细节\n"
                        "2. 如果数据量大，给出关键统计信息（如总数、最大值、最小值等）\n"
                        "3. 如果有明显的数据特征或趋势，简要说明\n"
                        "4. 回答要简洁明了，控制在200字以内\n"
                        "5. 使用中文回答"
                    )
                    
                    # 用户提示词
                    user_prompt = (
                        f"用户问题：{question}\n\n"
                        f"查询结果（共{row_count}条记录，{col_count}个字段）：\n{data_preview}"
                    )
                    
                    # 使用 LangChain 流式输出回答（传入 session_id 启用记忆）
                    for chunk in stream_chat_response(system_prompt, user_prompt, session_id):
                        yield f"event: answer\ndata: {chunk}\n\n"
                
                # 5. 发送表格数据（处理特殊值并使用 Base64 编码）
                import base64
                import math
                
                def sanitize_value(v):
                    """处理 JSON 不支持的特殊值"""
                    if v is None:
                        return None
                    if isinstance(v, float):
                        if math.isnan(v) or math.isinf(v):
                            return None
                    return v
                
                def sanitize_dict(d):
                    """递归处理字典中的特殊值"""
                    if isinstance(d, dict):
                        return {k: sanitize_dict(v) for k, v in d.items()}
                    elif isinstance(d, list):
                        return [sanitize_dict(item) for item in d]
                    else:
                        return sanitize_value(d)
                
                sanitized_table = sanitize_dict(table_data)
                table_json = json.dumps(sanitized_table, ensure_ascii=False)
                table_b64 = base64.b64encode(table_json.encode('utf-8')).decode('ascii')
                yield f"event: table\ndata: {table_b64}\n\n"
                
                # 6. 发送完成信号
                done_json = json.dumps({'row_count': len(converted_results)})
                yield f"event: done\ndata: {done_json}\n\n"
                
            except mysql.connector.Error as db_error:
                print(f"[Query Stream] 数据库错误: {db_error}")
                yield f"event: error\ndata: {json.dumps({'message': f'查询执行时遇到问题：{str(db_error)}'}, ensure_ascii=False)}\n\n"
                
        except Exception as e:
            print(f"[Query Stream] 异常: {traceback.format_exc()}")
            yield f"event: error\ndata: {json.dumps({'message': '处理您的问题时出现错误，请稍后重试。'}, ensure_ascii=False)}\n\n"
    
    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'
        }
    )


def query_agent():
    """
    Agent 模式查询接口 - 使用 LangChain Agent 自动决定是否调用数据库查询工具
    
    请求: POST /api/query-agent
    Body: {"question": "查询所有闸门设备", "session_id": "xxx"}
    
    响应: SSE 事件流
    - event: answer    -> 逐字返回的回答内容
    - event: done      -> 完成信号
    - event: error     -> 错误信息
    """
    import json
    
    data = request.get_json()
    
    if not data or 'question' not in data:
        def error_gen():
            yield f"event: error\ndata: {json.dumps({'message': '请提供 question 参数'}, ensure_ascii=False)}\n\n"
        return Response(error_gen(), mimetype='text/event-stream')
    
    question = data['question'].strip()
    session_id = data.get('session_id', None)
    
    if not question:
        def error_gen():
            yield f"event: error\ndata: {json.dumps({'message': '问题不能为空'}, ensure_ascii=False)}\n\n"
        return Response(error_gen(), mimetype='text/event-stream')
    
    def generate():
        try:
            print(f"\n[Agent] 用户问题: {question}")
            print(f"[Agent] Session ID: {session_id}")
            
            # 使用 Agent 流式处理
            for chunk in run_agent_stream(question, session_id):
                yield f"event: answer\ndata: {chunk}\n\n"
            
            # 发送完成信号
            yield f"event: done\ndata: {json.dumps({'success': True})}\n\n"
            
        except Exception as e:
            import traceback
            print(f"[Agent] 异常: {traceback.format_exc()}")
            yield f"event: error\ndata: {json.dumps({'message': '处理您的问题时出现错误，请稍后重试。'}, ensure_ascii=False)}\n\n"
    
    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'
        }
    )


def register_routes(app):
    """注册路由到 Flask app"""
    app.route('/api/query', methods=['POST'])(query)
    app.route('/api/query-stream', methods=['POST'])(query_stream)
    app.route('/api/query-agent', methods=['POST'])(query_agent)  # 新增 Agent 模式


# 独立运行时的代码
if __name__ == '__main__':
    app = Flask(__name__)
    register_routes(app)
    
    print("=" * 60)
    print("Vanna 问答 API 服务")
    print("=" * 60)
    print("\n可用接口:")
    print("  POST /api/query  - 自然语言查询 (Body: {\"question\": \"...\"}")
    print("\n" + "=" * 60)
    app.run(host='0.0.0.0', port=5001, debug=True)
