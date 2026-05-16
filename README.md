# 电商实时营销系统

一个面向电商场景的双轨实时决策系统。

- 快通道（Java / Spring Boot）：高吞吐流处理与高价值信号识别
- 慢通道（Python / LangGraph）：基于上下文与 RAG/LLM 的智能营销决策

## 项目概览

本项目将实时事件处理与 AI 决策分层解耦：

1. 客户端行为事件（浏览/点击/加购/搜索）发送到 Kafka 主题 `behavior-normal`
2. Java 服务消费全量流量，执行窗口聚合和规则判断
3. 将高价值意图提升（promote）到 Kafka 主题 `intent-high`
4. Python Agent 消费 `intent-high`，加载用户上下文（Redis + MySQL），检索知识（ChromaDB），并产出营销动作

## 系统架构

### 快通道（Java）
- 消费 `behavior-normal`
- 维护滑动窗口指标
- 写入 Redis 实时状态
- 生产高价值信号到 `intent-high`

### 慢通道（Python）
- 消费 `intent-high`
- 从 Redis 与 MySQL 组装用户上下文
- 在 ChromaDB 中执行 RAG 检索
- 调用 LLM 生成最优营销动作

### 基础设施
- Kafka（KRaft）
- Redis
- MySQL 8.0
- ChromaDB（Docker 部署）

## 仓库结构

```text
.
├─ backend-java/           # 快通道服务（流计算 / 信号提升）
├─ agent-python/           # 慢通道 Agent（推理 / 工具 / RAG）
├─ Config/
│  ├─ infrastructure/      # 基础设施配置，如 MySQL 初始化脚本
│  └─ data/                # Docker 挂载的持久化数据（请勿手动修改）
├─ docker-compose.yml      # 本地基础设施编排
├─ architecture.md         # 架构设计说明
├─ task.json               # 任务状态跟踪
└─ progress.txt            # 进度记录
```

## 环境要求

- Docker + Docker Compose
- Java 21+
- Maven 3.9+
- Python 3.10+

## 快速开始

### 1）启动基础设施（在仓库根目录执行）

```bash
docker-compose up -d
docker-compose ps
```

运行服务前请确认以下端口可用：
- Kafka：`9092`
- Redis：`6379`
- MySQL：`3306`

### 2）运行快通道（Java）

```bash
cd backend-java
mvn clean install -DskipTests
mvn test
mvn spring-boot:run
```

### 3）运行慢通道（Python）

```bash
cd agent-python
pip install -r requirements.txt
pytest
python src/main.py
```

## Topic 与事件约定

- `behavior-normal`：全量用户行为流
- `intent-high`：由 Java 识别并产出的高价值意图事件

建议：
- `behavior-normal` 使用 `user_id` 作为 Kafka message key，以尽可能保证单用户事件的局部有序性

## 测试要求

- Java：`mvn test` 必须通过
- Python：`pytest` 必须通过
- 单元测试必须 mock 外部依赖（Kafka/Redis/LLM API）

## 工程规范

- 禁止硬编码密码或 API Key
- 运行配置使用 `.env`
- 代码、任务状态与进度记录保持一致更新

## 为什么采用双轨架构？

- 快通道以低延迟、低成本处理全量流量
- 慢通道仅处理高价值事件，执行更深度的 AI 推理
- 在保证决策质量的同时，有效控制 LLM 成本

## 后续可扩展方向

- 增加更细粒度意图标签（加购未付、价格敏感、库存紧张等）
- 增加闭环指标（发送成功、点击率、转化率）
- 建立离线评估与 A/B 策略实验体系
