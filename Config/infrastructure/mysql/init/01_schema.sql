-- ========================================
-- E-commerce Real-time Marketing System
-- MySQL Database Schema
-- ========================================

-- 用户基础表 - 长效画像
CREATE TABLE IF NOT EXISTS users (
    id BIGINT AUTO_INCREMENT PRIMARY KEY COMMENT '用户ID',
    name VARCHAR(255) NOT NULL COMMENT '用户名',
    spending_tier ENUM('HIGH', 'MEDIUM', 'LOW') DEFAULT 'MEDIUM' COMMENT '消费等级',
    identity_tags JSON COMMENT '静态标签，如 ["tech_lover", "parent"]',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '注册时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_spending_tier (spending_tier)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户基础表';

-- 商品表 - RAG的数据源
CREATE TABLE IF NOT EXISTS products (
    sku_id VARCHAR(50) PRIMARY KEY COMMENT '商品SKU',
    name VARCHAR(255) NOT NULL COMMENT '商品名称',
    selling_points TEXT COMMENT '核心卖点 (将被向量化)',
    price DECIMAL(10, 2) NOT NULL COMMENT '当前价格',
    stock INT DEFAULT 0 COMMENT '库存',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='商品表';

-- 促销规则表
CREATE TABLE IF NOT EXISTS promotions (
    rule_id INT AUTO_INCREMENT PRIMARY KEY COMMENT '规则ID',
    description TEXT COMMENT '规则描述 (将被向量化)',
    condition_json JSON COMMENT '机器可读规则，如 {"min_spend": 1000}',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='促销规则表';
