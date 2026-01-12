-- 员工考勤扣款记录表
-- 基于 attendance_calculator.py 脚本输出的Excel表头字段

CREATE TABLE IF NOT EXISTS employee_attendance_deduction (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    employee_name VARCHAR(50) NOT NULL COMMENT '姓名',
    job_title VARCHAR(100) COMMENT '职务',
    job_level VARCHAR(20) COMMENT '职级',
    level_type VARCHAR(10) COMMENT '职级类型(P/M/D/实习)',
    total_late_count INT DEFAULT 0 COMMENT '总迟到次数',
    late_within_10_count INT DEFAULT 0 COMMENT '10分钟内迟到次数',
    late_over_10_count INT DEFAULT 0 COMMENT '超10分钟迟到次数',
    late_over_60_count INT DEFAULT 0 COMMENT '超1小时迟到次数',
    morning_missing_count INT DEFAULT 0 COMMENT '早上缺卡次数',
    evening_missing_count INT DEFAULT 0 COMMENT '下午缺卡次数',
    early_leave_count INT DEFAULT 0 COMMENT '早退次数',
    total_deduction DECIMAL(10, 2) DEFAULT 0 COMMENT '总扣款金额',
    attendance_month VARCHAR(10) NOT NULL COMMENT '考勤月份(YYYY-MM)',
    row_order INT DEFAULT 0 COMMENT '原始行序号',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    -- 唯一约束：同一月份同一员工只有一条记录
    UNIQUE KEY uk_employee_month (employee_name, attendance_month),
    
    -- 索引
    INDEX idx_attendance_month (attendance_month),
    INDEX idx_employee_name (employee_name),
    INDEX idx_total_deduction (total_deduction)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='员工考勤扣款记录表';
