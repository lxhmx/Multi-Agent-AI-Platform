-- 员工加班记录表
-- 用于存储从考勤表计算出的加班数据

CREATE TABLE IF NOT EXISTS employee_overtime (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    employee_name VARCHAR(100) NOT NULL COMMENT '员工姓名',
    job_title VARCHAR(200) COMMENT '职务',
    job_level VARCHAR(50) COMMENT '职级(P/M/D等)',
    overtime_hours INT DEFAULT 0 COMMENT '加班时长(小时)',
    overtime_minutes INT DEFAULT 0 COMMENT '加班时长(分钟)',
    overtime_days INT DEFAULT 0 COMMENT '加班天数',
    overtime_rate DECIMAL(10,2) DEFAULT 0 COMMENT '加班费用标准(元/小时)',
    overtime_amount DECIMAL(10,2) DEFAULT 0 COMMENT '加班总金额',
    overtime_detail TEXT COMMENT '加班明细(如: 5日:2h, 12日:3h)',
    attendance_month VARCHAR(7) NOT NULL COMMENT '考勤月份(格式: YYYY-MM)',
    row_order INT DEFAULT 0 COMMENT '原始文档中的行序号，用于保持员工排序',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    -- 索引
    INDEX idx_month (attendance_month),
    INDEX idx_name (employee_name),
    INDEX idx_row_order (row_order),
    
    -- 唯一约束: 同一员工同一月份只能有一条记录，重复上传会覆盖
    UNIQUE KEY uk_employee_month (employee_name, attendance_month)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='员工加班记录表';
