"""
工作时长统计 API
提供财务日常工作时长数据的上传、查询、统计功能
"""
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, Query
import pandas as pd
import re

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from database.mysql_client import MySQLClient

router = APIRouter(prefix="/api/work-time", tags=["工作时长统计"])


def parse_date(date_val):
    """解析各种日期格式"""
    if pd.isna(date_val):
        return None
    if isinstance(date_val, datetime):
        return date_val.date()
    date_str = str(date_val)
    # 尝试中文格式: 2025年12月18
    match = re.match(r'(\d{4})年(\d{1,2})月(\d{1,2})', date_str)
    if match:
        return datetime(int(match.group(1)), int(match.group(2)), int(match.group(3))).date()
    # 尝试标准格式
    try:
        return pd.to_datetime(date_val).date()
    except:
        return None


def init_work_time_table():
    """初始化工作时长表"""
    create_sql = """
    CREATE TABLE IF NOT EXISTS work_time_records (
        id INT AUTO_INCREMENT PRIMARY KEY,
        month VARCHAR(20) COMMENT '月份',
        record_date DATE COMMENT '日期',
        employee_name VARCHAR(50) COMMENT '姓名',
        company VARCHAR(50) COMMENT '公司主体',
        work_type VARCHAR(50) COMMENT '日报类型',
        quantity DECIMAL(10,2) COMMENT '完成条数',
        unit VARCHAR(20) COMMENT '单位',
        work_content TEXT COMMENT '具体工作内容',
        duration_minutes INT COMMENT '耗时(分钟)',
        remark TEXT COMMENT '备注',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_employee (employee_name),
        INDEX idx_month (month),
        INDEX idx_company (company),
        INDEX idx_work_type (work_type),
        INDEX idx_record_date (record_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='工作时长记录表'
    """
    try:
        with MySQLClient() as db:
            db.execute_update(create_sql)
    except Exception as e:
        print(f"[WorkTime] 创建表失败: {e}")


@router.post("/upload")
async def upload_work_time(file: UploadFile = File(...)):
    """上传工作时长Excel文件"""
    try:
        if not file.filename.endswith(('.xls', '.xlsx')):
            raise HTTPException(status_code=400, detail="请上传Excel文件(.xls或.xlsx)")
        
        init_work_time_table()
        
        temp_dir = PROJECT_ROOT / 'temp'
        temp_dir.mkdir(exist_ok=True)
        temp_path = temp_dir / f"worktime_{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}"
        
        content = await file.read()
        with open(temp_path, 'wb') as f:
            f.write(content)
        
        try:
            df = pd.read_excel(str(temp_path), engine='calamine')
            
            # 清空旧数据并插入新数据
            with MySQLClient() as db:
                db.execute_update("TRUNCATE TABLE work_time_records")
                
                insert_sql = """
                INSERT INTO work_time_records 
                    (month, record_date, employee_name, company, work_type, quantity, unit, work_content, duration_minutes, remark)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                
                inserted = 0
                for _, row in df.iterrows():
                    try:
                        month_val = str(row.get('月份', ''))[:20] if pd.notna(row.get('月份')) else None
                        date_val = parse_date(row.get('日期'))
                        
                        params = (
                            month_val,
                            date_val,
                            str(row.get('姓名', ''))[:50] if pd.notna(row.get('姓名')) else None,
                            str(row.get('公司主体', ''))[:50] if pd.notna(row.get('公司主体')) else None,
                            str(row.get('日报', ''))[:50] if pd.notna(row.get('日报')) else None,
                            float(row.get('完成条数', 0)) if pd.notna(row.get('完成条数')) else 0,
                            str(row.get('单位', ''))[:20] if pd.notna(row.get('单位')) else None,
                            str(row.get('具体工作内容', '')) if pd.notna(row.get('具体工作内容')) else None,
                            int(row.get('总共实际耗时长（min）', 0)) if pd.notna(row.get('总共实际耗时长（min）')) else 0,
                            str(row.get('备注', '')) if pd.notna(row.get('备注')) else None
                        )
                        db.execute_update(insert_sql, params)
                        inserted += 1
                    except Exception as e:
                        print(f"[WorkTime] 插入行失败: {e}")
                        continue
            
            return {
                "success": True,
                "message": "导入成功",
                "data": {"total_records": inserted}
            }
        finally:
            if temp_path.exists():
                temp_path.unlink()
                
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"[WorkTime] 上传处理失败: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")


@router.get("/stats")
async def get_work_time_stats(
    employee: Optional[str] = Query(None, description="员工姓名"),
    month: Optional[str] = Query(None, description="月份"),
    company: Optional[str] = Query(None, description="公司主体")
):
    """获取工作时长统计数据"""
    try:
        init_work_time_table()
        
        conditions = []
        params = []
        
        if employee:
            conditions.append("employee_name = %s")
            params.append(employee)
        if month:
            conditions.append("month = %s")
            params.append(month)
        if company:
            conditions.append("company = %s")
            params.append(company)
        
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        with MySQLClient() as db:
            # 获取筛选选项
            employees = db.execute_query("SELECT DISTINCT employee_name FROM work_time_records WHERE employee_name IS NOT NULL ORDER BY employee_name")
            months = db.execute_query("SELECT DISTINCT month FROM work_time_records WHERE month IS NOT NULL ORDER BY month DESC")
            companies = db.execute_query("SELECT DISTINCT company FROM work_time_records WHERE company IS NOT NULL ORDER BY company")
            
            # 日报类型统计
            work_type_sql = f"""
                SELECT work_type as name, SUM(duration_minutes) as value
                FROM work_time_records
                WHERE {where_clause} AND work_type IS NOT NULL
                GROUP BY work_type
                ORDER BY value DESC
            """
            work_type_stats = db.execute_query(work_type_sql, tuple(params) if params else None)
            
            # 各人员工作时长统计
            employee_sql = f"""
                SELECT employee_name as name, SUM(duration_minutes) as value
                FROM work_time_records
                WHERE {where_clause} AND employee_name IS NOT NULL
                GROUP BY employee_name
                ORDER BY value DESC
            """
            employee_stats = db.execute_query(employee_sql, tuple(params) if params else None)
            
            # 公司主体统计
            company_sql = f"""
                SELECT company as name, SUM(duration_minutes) as value
                FROM work_time_records
                WHERE {where_clause} AND company IS NOT NULL
                GROUP BY company
                ORDER BY value DESC
            """
            company_stats = db.execute_query(company_sql, tuple(params) if params else None)
            
            # 每日工作时长统计 -> 改为各人员工作类型分布
            employee_type_sql = f"""
                SELECT employee_name, work_type, SUM(duration_minutes) as minutes
                FROM work_time_records
                WHERE {where_clause} AND employee_name IS NOT NULL AND work_type IS NOT NULL
                GROUP BY employee_name, work_type
                ORDER BY employee_name, minutes DESC
            """
            employee_type_stats = db.execute_query(employee_type_sql, tuple(params) if params else None)
            
            # 汇总统计
            summary_sql = f"""
                SELECT 
                    COALESCE(SUM(duration_minutes), 0) as total_minutes,
                    COUNT(*) as total_records,
                    COUNT(DISTINCT record_date) as total_days
                FROM work_time_records
                WHERE {where_clause}
            """
            summary = db.execute_query(summary_sql, tuple(params) if params else None)
            summary_data = summary[0] if summary else {'total_minutes': 0, 'total_records': 0, 'total_days': 0}
            
            total_days = summary_data.get('total_days', 1) or 1
            avg_hours = round((summary_data.get('total_minutes', 0) or 0) / 60 / total_days, 1)
        
        return {
            "success": True,
            "data": {
                "employees": [e['employee_name'] for e in employees] if employees else [],
                "months": [m['month'] for m in months] if months else [],
                "companies": [c['company'] for c in companies] if companies else [],
                "work_type_stats": work_type_stats or [],
                "employee_time_stats": employee_stats or [],
                "company_stats": company_stats or [],
                "employee_type_stats": employee_type_stats or [],
                "summary": {
                    "totalHours": summary_data.get('total_minutes', 0) or 0,
                    "totalRecords": summary_data.get('total_records', 0) or 0,
                    "avgHoursPerDay": avg_hours
                }
            }
        }
    except Exception as e:
        import traceback
        print(f"[WorkTime] 统计失败: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"统计失败: {str(e)}")
