-- 对话会话表
CREATE TABLE IF NOT EXISTS chat_sessions (
    id VARCHAR(36) PRIMARY KEY COMMENT 'UUID',
    user_id BIGINT NOT NULL COMMENT '关联用户',
    title VARCHAR(100) COMMENT '会话标题',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_updated_at (updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='对话会话表';

-- 对话消息表
CREATE TABLE IF NOT EXISTS chat_messages (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    session_id VARCHAR(36) NOT NULL COMMENT '关联会话',
    role ENUM('user', 'assistant') NOT NULL COMMENT '消息角色',
    content TEXT NOT NULL COMMENT '消息内容',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE,
    INDEX idx_session_id (session_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='对话消息表';
