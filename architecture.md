# 电商实时营销智能体 (E-commerce Real-time Marketing Agent) - 架构设计文档

## 项目概述

基于“双轨消息管道”与“复杂事件处理 (CEP)”的实时决策系统。

**核心逻辑：** 客户端无脑上报全量数据 → Kafka 普通流 → Java 实时计算（清洗/窗口统计/阈值判断） → **Java 识别出高价值意图并生产消息** → Kafka 高优流 → Python Agent (LLM) 被唤醒 → 读取画像(Redis/MySQL) + RAG 检索 → 营销动作。

## 技术栈

| **层级**      | **技术选型**              | **说明**                                                     |
| ------------- | ------------------------- | ------------------------------------------------------------ |
| **流计算层**  | Java (Spring Boot)        | 系统的“过滤器”与“分流器”。消费全量数据，维护时间窗口，识别高优意图。 |
| **决策层**    | Python (LangChain/Native) | 智能体编排，仅响应高优信号，负责推理、工具调用。             |
| **消息队列**  | Kafka (KRaft模式)         | `behavior-normal` (全量入口), `intent-high` (Java 生产的精华出口)。 |
| **缓存/状态** | Redis                     | 存储 Java 计算的实时滑动窗口、热点用户标签。                 |
| **持久化DB**  | MySQL 8.0+                | 存储用户长效画像（消费等级、身份标签）、商品库。             |
| **向量库**    | ChromaDB (本地部署)       | 存储商品卖点向量、SOP 话术向量。                             |
| **LLM**       | GLM-4 (API)               | 负责最终推理与文案生成。                                     |
| **嵌入模型**  | BGE-m3 (本地运行)         | 负责文本转向量 (Embedding)。                                 |

------

## 1. 系统架构图

代码段

```
graph TD
    subgraph "客户端/埋点源"
        UserAction[用户所有行为] -->|点击/浏览/加购/搜索| KafkaNormal[Kafka: 普通流 topic]
    end

    subgraph "Java流计算层 (Filter & Promote)"
        KafkaNormal --> JavaService[Java 消费者服务]
        
        JavaService -->|1.更新实时统计| Redis[(Redis 缓存)]
        JavaService -- 懒加载/同步 --- MySQL[(MySQL 主库)]
        
        JavaService -->|2.逻辑判断: 是否高价值?| Decision{符合阈值?}
        Decision -->|是: 5分钟10次/加购超时| KafkaHigh[Kafka: 高优流 topic]
        Decision -->|否: 仅记录| Log[结束]
    end

    subgraph "Python决策层 (High Intelligence)"
        KafkaHigh --> PythonAgent[Python Agent 服务]
        
        PythonAgent -->|3.获取上下文| ContextGathering
        ContextGathering -->|读长效画像| MySQL
        ContextGathering -->|读实时状态| Redis
        
        PythonAgent -->|4.RAG检索| VectorDB[(本地向量库 ChromaDB)]
        
        VectorDB <.-.|定期更新| MySQL
    end

    subgraph "外部服务"
        PythonAgent -->|5.推理决策| LLM_API[大模型 API]
        PythonAgent -->|6.执行动作| SMS_Service[短信/推送服务]
    end
```

------

## 2. 核心业务流程图 (数据流转)

**场景：** 用户短时间内多次浏览同一品类 -> Java 识别为高兴趣 -> 触发 Agent 介入

代码段

```
sequenceDiagram
    participant User as 用户/前端埋点
    participant KafkaN as Kafka普通流
    participant Java as Java流计算服务
    participant Redis as Redis缓存
    participant KafkaH as Kafka高优流
    participant Agent as Python Agent
    participant MySQL as MySQL数据库
    participant RAG as 本地向量库
    participant LLM as 大模型

    Note over User, Redis: 阶段一：全量数据清洗与积累
    User->>KafkaN: 发送普通日志 (浏览商品A)
    KafkaN->>Java: 消费 `behavior-normal`
    Java->>Redis: 更新滑动窗口 (ZADD/INCR)
    Java->>Java: 逻辑判断 (过去5分钟点击 > 10次?)
    
    Note over Java, KafkaH: 阶段二：意图晋升 (Promotion)
    Java->>KafkaH: **关键步骤：生产高优消息** (High Value Intent)
    
    Note over KafkaH, User: 阶段三：Agent 决策闭环
    KafkaH->>Agent: 消费 `intent-high` (唤醒 Agent)
    
    rect rgb(240, 248, 255)
        Note right of Agent: Agent 思考循环 (ReAct)
        Agent->>Redis: Tool: 获取实时画像 (刚刚的点击统计)
        Agent->>MySQL: Tool: 获取长效画像 (消费等级/身份标签)
        Agent->>Agent: 思考: 用户是高净值人群，且对A商品极度感兴趣
        Agent->>RAG: Tool: 搜索 "商品A 核心卖点 & 高端话术"
        RAG-->>Agent: 返回: "商品A采用顶级材质..."
        Agent->>LLM: 组装 Prompt 进行最终推理
        LLM-->>Agent: 生成最终营销文案
    end
    
    Agent->>User: Action: 发送短信/App推送
```

------

## 3. 数据模型设计

### 3.1 MySQL (持久化数据 & 知识源)

**users (用户基础表 - 长效画像)**

| 字段名 | 类型 | 说明 |

| :--- | :--- | :--- |

| `id` | BIGINT (PK) | 用户ID |

| `name` | VARCHAR | 用户名 |

| `spending_tier` | ENUM | 消费等级: `HIGH`, `MEDIUM`, `LOW` |

| `identity_tags` | JSON | 静态标签: `["tech_lover", "parent"]` |

| `created_at` | DATETIME | 注册时间 |

**products (商品表 - RAG的数据源)**

| 字段名 | 类型 | 说明 |

| :--- | :--- | :--- |

| `sku_id` | VARCHAR (PK) | 商品SKU |

| `name` | VARCHAR | 商品名称 |

| `selling_points` | TEXT | 核心卖点 (将被向量化) |

| `price` | DECIMAL | 当前价格 |

| `stock` | INT | 库存 |

**promotions (促销规则表)**

| 字段名 | 类型 | 说明 |

| :--- | :--- | :--- |

| `rule_id` | INT (PK) | 规则ID |

| `description` | TEXT | 规则描述 (将被向量化) |

| `condition_json` | JSON | 机器可读规则 `{min_spend: 1000}` |

### 3.2 Redis (实时状态缓存)

- **实时画像 Key:** `user:profile:{user_id}`
  - Type: `Hash`
  - Fields:
    - `realtime_interest`: "shoes"
    - `price_sensitive`: "true"
    - `last_active_ts`: "1708234567"
  - TTL: 30分钟
- **滑动窗口 Key (Java端维护):** `user:window:{user_id}:{action_type}`
  - Type: `ZSet` 或 `String`
  - 用途: Java 服务用来统计频次，作为判断是否发送 Kafka 高优流的依据。

### 3.3 Kafka 消息契约 (JSON Schema)

**Topic: `behavior-normal` (普通流)**

- **来源：** 客户端/前端埋点全量上报

JSON

```
{
  "user_id": "ding_hl",
  "action": "view_item",
  "sku_id": "shoe_1024",
  "price": 299.00,
  "timestamp": 1708234000
}
```

**Topic: `intent-high` (高优流)**

- **来源：** **Java 实时计算服务** (当满足特定阈值或规则时生成)

JSON

```
{
  "event_type": "high_interest_detected", 
  "user_id": "ding_hl",
  "reason": "clicked_10_times_in_5min",
  "context": {
    "target_category": "shoes",
    "recent_clicks": 12
  }
}
```

------

## 4. Agent Tool (工具) 定义

由于没有前端 API，这里的 API 实际上是 Agent 可调用的 Python 函数。

### 4.1 数据查询类

| **工具名称**           | **对应函数**                  | **描述**                             | **参数示例**      |
| ---------------------- | ----------------------------- | ------------------------------------ | ----------------- |
| **GetRealtimeProfile** | `get_redis_profile(user_id)`  | 从 Redis 读取 Java 计算的最新标签    | `user_id="1001"`  |
| **GetStaticProfile**   | `get_mysql_profile(user_id)`  | 从 MySQL 读取用户长效画像 (消费力等) | `user_id="1001"`  |
| **CheckStock**         | `check_product_stock(sku_id)` | 实时查询库存 (防止推销缺货商品)      | `sku_id="shoe_x"` |

### 4.2 知识检索类 (RAG)

| **工具名称**        | **对应函数**              | **描述**                             | **参数示例**                  |
| ------------------- | ------------------------- | ------------------------------------ | ----------------------------- |
| **SearchKnowledge** | `search_vector_db(query)` | 在本地 ChromaDB 中搜索商品卖点或话术 | `query="高端运动鞋 促销话术"` |

### 4.3 执行类

| **工具名称**         | **对应函数**                     | **描述**               | **参数示例**          |
| -------------------- | -------------------------------- | ---------------------- | --------------------- |
| **SendMarketingMsg** | `send_sms(user_id, content)`     | 发送最终决策的营销短信 | `content="尊贵的..."` |
| **ApplyCoupon**      | `issue_coupon(user_id, rule_id)` | 敏感操作：发放优惠券   | `rule_id=201`         |

------

## 5. 大模型与 Prompt 配置

### 5.1 System Prompt (核心人设)

Plaintext

```
你是一个专业的电商实时营销专家。你的目标是提高转化率，同时保护利润。
你需要根据用户的【实时画像】(Redis) 和【长效画像】(MySQL) 来决定策略。

决策逻辑：
1. 如果用户 `spending_tier` 为 HIGH，禁止推荐廉价打折商品，应强调品质和服务。
2. 只有当 `price_sensitive` 为 True 时，才允许调用 `ApplyCoupon` 工具。
3. 文案风格必须根据 `identity_tags` 调整（例如：对 "tech_lover" 使用技术参数）。

请按照 ReAct (Thought -> Action -> Observation) 的模式进行思考。
```

### 5.2 外部模型集成

- **LLM 推理:** 兼容 OpenAI 接口格式 (Base URL 指向 DeepSeek 或 本地 GLM)。
- **Embedding:** 使用 `Sentence-Transformers` 加载本地 `bge-m3` 模型，不依赖外部 API。

------

## 6. 环境变量 (Environment Variables)

Bash

```
# === Infrastructure ===
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
REDIS_HOST=localhost
REDIS_PORT=6379
MYSQL_URL=jdbc:mysql://localhost:3306/ecommerce_db

# === Agent Configuration ===
# 业务推理模型
LLM_API_KEY=4bc583e484574d9b8845709319bc54e7.fI0uMvuSqashzFBO
LLM_BASE_URL=https://open.bigmodel.cn/api/anthropic
LLM_MODEL_NAME=glm-4.6v-flashx

# 本地向量库
CHROMA_DB_PATH=./data/chroma
EMBEDDING_MODEL_PATH=./models/bge-m3

# === Thresholds ===
# Java端流计算阈值配置
WINDOW_SIZE_SECONDS=300
CLICK_THRESHOLD_HIGH_INTEREST=10
```
