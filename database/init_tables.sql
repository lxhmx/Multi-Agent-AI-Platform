-- 训练文件记录表
-- 用于记录所有上传和训练的文件信息，支持数据管理页面的统计功能

CREATE TABLE IF NOT EXISTS training_files (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    file_name VARCHAR(255) NOT NULL COMMENT '文件名',
    file_path VARCHAR(500) NOT NULL COMMENT '文件完整路径',
    file_type VARCHAR(20) NOT NULL COMMENT '文件类型(sql/doc/docx/pdf/xls/xlsx/csv/txt)',
    train_type VARCHAR(20) NOT NULL COMMENT '训练类型：sql或document',
    file_size BIGINT DEFAULT 0 COMMENT '文件大小(字节)',
    file_hash VARCHAR(64) COMMENT '文件MD5哈希值，用于去重',
    train_status VARCHAR(20) DEFAULT 'pending' COMMENT '训练状态(pending/training/success/failed)',
    train_result TEXT COMMENT '训练结果或错误信息',
    train_count INT DEFAULT 0 COMMENT '训练生成的知识条目数',
    upload_date DATE NOT NULL COMMENT '上传日期',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    INDEX idx_file_type (file_type),
    INDEX idx_train_type (train_type),
    INDEX idx_train_status (train_status),
    INDEX idx_upload_date (upload_date),
    INDEX idx_file_hash (file_hash)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='训练文件记录表';

-- 用户表（鉴权）
CREATE TABLE IF NOT EXISTS users (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(64) NOT NULL UNIQUE,
    email VARCHAR(128),
    password_hash VARCHAR(255) NOT NULL,
    disabled TINYINT(1) DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login DATETIME NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表';
