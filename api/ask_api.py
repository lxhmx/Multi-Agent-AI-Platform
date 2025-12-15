"""
Vanna 问答 API (FastAPI 版本)
提供自然语言查询接口，支持真正的异步流式输出
"""
import sys
import json
import traceback
import base64
import math
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import pandas as pd
import mysql.connector

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from common.vanna_instance import get_vanna_instance
from common.langchain_llm import stream_chat_response
from common.conn_mysql import get_mysql_connection
from common.langchain_agent import run_agent_stream_async
from common.dependencies import get_current_user

# 创建路由器
router = APIRouter(prefix="/api", tags=["问答"])


# ==================== Pydantic 模型 ====================

class QueryRequest(BaseModel):
    question: str
    session_id: Optional[str] = None


# ==================== 工具函数 ====================

def convert_value(obj):
    """处理数据库返回值中的特殊类型"""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, bytes):
        return obj.decode('utf-8', errors='ignore')
    return obj


# ==================== 查询接口 ====================

@router.post("/query")
async def query(req: QueryRequest, user=Depends(get_current_user)):
    """
    查询接口 - 根据用户问题生成 SQL 并执行查询，返回人性化的回答
    """
    from api.ask_api import generate_human_answer, generate_table_data, generate_chart_config
    
    try:
        question = req.question.strip()
        
        if not question:
            raise HTTPException(status_code=400, detail="问题不能为空")
        
        vn = get_vanna_instance()
        
        print(f"\n[Query] 用户问题: {question}")
        
        # 生成 SQL
        sql = vn.generate_sql(question)
        print(f"[Query] 生成的 SQL: {sql}")
        
        if not sql or not sql.strip():
            return {
                "success": False,
                "message": "抱歉，我无法理解您的问题。请尝试换一种方式描述。",
                "question": question
            }
        
        sql_upper = sql.strip().upper()
        if not sql_upper.startswith('SELECT'):
            return {
                "success": False,
                "message": "抱歉，我无法理解您的问题。请尝试换一种方式描述。",
                "question": question,
                "detail": sql
            }
        
        if not vn.is_sql_valid(sql):
            return {
                "success": False,
                "question": question,
                "sql": sql,
                "message": "抱歉，您的问题可能涉及数据修改操作，目前仅支持数据查询。"
            }
        
        # 执行 SQL 查询
        try:
            conn = get_mysql_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(sql)
            results = cursor.fetchall()
            cursor.close()
            conn.close()
            
            print(f"[Query] 查询成功，返回 {len(results)} 条记录")
            
            # 转换结果
            converted_results = []
            for row in results:
                converted_row = {k: convert_value(v) for k, v in row.items()}
                converted_results.append(converted_row)
            
            df = pd.DataFrame(converted_results) if converted_results else pd.DataFrame()
            
            # 生成回答和表格
            answer = generate_human_answer(vn, question, sql, df)
            table_data = generate_table_data(df)
            chart_config = generate_chart_config(vn, question, sql, df)
            
            return {
                "success": True,
                "question": question,
                "answer": answer,
                "sql": sql,
                "table": table_data,
                "chart": chart_config,
                "row_count": len(converted_results),
                "user_id": user["id"],
            }
            
        except mysql.connector.Error as db_error:
            print(f"[Query] 数据库错误: {db_error}")
            return {
                "success": False,
                "question": question,
                "sql": sql,
                "message": f"抱歉，查询执行时遇到问题：{str(db_error)}"
            }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Query] 异常: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="处理您的问题时出现错误，请稍后重试。")


@router.post("/query-stream")
async def query_stream(req: QueryRequest, user=Depends(get_current_user)):
    """
    流式查询接口 - 使用 SSE 协议逐字返回回答
    """
    from api.ask_api import generate_table_data
    
    question = req.question.strip()
    session_id = req.session_id
    
    if not question:
        async def error_gen():
            yield f"event: error\ndata: {json.dumps({'message': '问题不能为空'}, ensure_ascii=False)}\n\n"
        return StreamingResponse(error_gen(), media_type="text/event-stream")
    
    async def generate():
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
                
                # 转换结果
                converted_results = []
                for row in results:
                    converted_row = {k: convert_value(v) for k, v in row.items()}
                    converted_results.append(converted_row)
                
                df = pd.DataFrame(converted_results) if converted_results else pd.DataFrame()
                
                # 3. 生成表格数据
                table_data = generate_table_data(df)
                
                # 4. 流式生成回答
                if df.empty:
                    yield f"event: answer\ndata: 根据您的查询条件，暂未找到相关数据。您可以尝试调整查询条件后再试。\n\n"
                else:
                    row_count = len(df)
                    col_count = len(df.columns)
                    
                    if row_count <= 10:
                        data_preview = df.to_markdown(index=False)
                    else:
                        data_preview = df.head(10).to_markdown(index=False)
                        data_preview += f"\n\n... 共 {row_count} 条记录"
                    
                    system_prompt = (
                        "你是一个友好的数据分析助手。用户提出了一个数据查询问题，系统已经执行了SQL查询并获得了结果。"
                        "请根据查询结果，用自然、易懂的语言回答用户的问题。"
                        "要求：\n"
                        "1. 直接回答用户的问题，不要提及SQL或技术细节\n"
                        "2. 如果数据量大，给出关键统计信息\n"
                        "3. 回答要简洁明了，控制在200字以内\n"
                        "4. 使用中文回答"
                    )
                    
                    user_prompt = (
                        f"用户问题：{question}\n\n"
                        f"查询结果（共{row_count}条记录，{col_count}个字段）：\n{data_preview}"
                    )
                    
                    for chunk in stream_chat_response(system_prompt, user_prompt, session_id):
                        yield f"event: answer\ndata: {chunk}\n\n"
                
                # 5. 发送表格数据
                def sanitize_value(v):
                    if v is None:
                        return None
                    if isinstance(v, float):
                        if math.isnan(v) or math.isinf(v):
                            return None
                    return v
                
                def sanitize_dict(d):
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
                done_json = json.dumps({'row_count': len(converted_results), 'user_id': user["id"]})
                yield f"event: done\ndata: {done_json}\n\n"
                
            except mysql.connector.Error as db_error:
                print(f"[Query Stream] 数据库错误: {db_error}")
                yield f"event: error\ndata: {json.dumps({'message': f'查询执行时遇到问题：{str(db_error)}'}, ensure_ascii=False)}\n\n"
                
        except Exception as e:
            print(f"[Query Stream] 异常: {traceback.format_exc()}")
            yield f"event: error\ndata: {json.dumps({'message': '处理您的问题时出现错误，请稍后重试。'}, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'
        }
    )


@router.post("/query-agent")
async def query_agent(req: QueryRequest):
    """
    Agent 模式查询接口 - 使用 LangChain Agent 自动决定是否调用数据库查询工具
    真正的异步流式输出
    """
    question = req.question.strip()
    session_id = req.session_id
    
    if not question:
        async def error_gen():
            yield f"event: error\ndata: {json.dumps({'message': '问题不能为空'}, ensure_ascii=False)}\n\n"
        return StreamingResponse(error_gen(), media_type="text/event-stream")
    
    async def generate():
        try:
            print(f"\n[Agent] 用户问题: {question}")
            print(f"[Agent] Session ID: {session_id}")
            
            # 使用真正的异步流式输出
            async for chunk in run_agent_stream_async(question, session_id):
                yield f"event: answer\ndata: {chunk}\n\n"
            
            # 发送完成信号
            yield f"event: done\ndata: {json.dumps({'success': True})}\n\n"
            
        except Exception as e:
            print(f"[Agent] 异常: {traceback.format_exc()}")
            yield f"event: error\ndata: {json.dumps({'message': '处理您的问题时出现错误，请稍后重试。'}, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'
        }
    )
