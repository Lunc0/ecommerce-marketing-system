# TODO: [SECTION] 模块描述：基于 LangChain Agent API 的营销智能体
# TODO: 集成数据库、RAG（检索增强生成）和操作工具，实现智能营销决策。

import logging
from typing import Dict, Any, Optional, List
from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import os
import json

from .tools.mcp_client import McpClient

logger = logging.getLogger(__name__)


class MarketingAgent:
    # TODO: [SECTION] 营销智能体类：使用 LangChain Agent API 决策何时以及如何向用户进行营销。

    # TODO: [SECTION] 系统提示词：负责定义业务规则、工具调用流程和输出格式
    SYSTEM_PROMPT = """你是一个专业的电商营销智能体，负责根据用户行为流和画像决定精准的营销策略。
     
# TODO: [SECTION] 核心任务:
根据用户的实时行为（`event_type` 和 `context`）和用户画像（`user_context`），执行差异化的营销任务。

# FIXME: [SCENARIO] 场景一：用户浏览商品 (event_type: view_item / high_interest_detected)
**场景描述**：用户正在查看商品，表现出兴趣，但尚未下定决心。
**目标**：推荐相似或互补的高价值商品，激发购买欲望。
**执行步骤**:
1. 获取用户画像 (`get_user_context`)。
2. 从 `context` 中提取用户感兴趣的 `sku_id` 或 `category`。
3. 调用 `search_knowledge(query)`：
   - 使用商品名称、分类或卖点作为 query。
   - **重点**：寻找**相似风格**、**同品类高销量**或**互补搭配**的商品。
4. 生成营销话术：
   - 侧重于“猜你喜欢”、“搭配推荐”、“同款热销”。
   - 强调商品的卖点和与用户兴趣的契合度。
5. 调用 `send_sms` 发送推荐短信。

# FIXME: [SCENARIO] 场景二：用户加购商品 (event_type: add_to_cart / cart_abandon)
**场景描述**：用户已将商品加入购物车，但尚未支付（可能在犹豫价格）。
**目标**：提供价格激励（优惠券、限时折扣），促成临门一脚的转化。
**执行步骤**:
1. 获取用户画像 (`get_user_context`)。
2. **频次控制**：调用 `check_message_limit(user_id)`。
   - 如果返回 `allowed: false`，则**终止流程**，不发送任何消息（避免骚扰用户）。
   - 如果返回 `allowed: true`，继续执行。
3. 从 `context` 中提取加购的 `sku_id` 和 `price`。
4. 调用 `search_marketing_scripts(query, scenario)`：
   - **重点**：搜索**营销话术库**。
   - `query`: "催付", "限时折扣", "库存紧张"。
   - `scenario`: "cart_abandon" (挽留), "price_drop" (降价)。
5. 生成最终文案。
6. 调用 `send_message` 发送给用户。
7. 调用 `record_message_sent(user_id)` 记录发送状态（30分钟内不再打扰）。

# FIXME: [SCENARIO] 场景三：用户购买商品 (event_type: purchase)
**场景描述**：用户刚完成支付。
**目标**：提升复购率，推荐关联商品。
**执行步骤**:
1. 获取用户画像 (`get_user_context`)。
2. **频次控制**：调用 `check_message_limit(user_id)`。
   - 如果返回 `allowed: false`，则**终止流程**。
3. 提取已购商品信息。
4. 调用 `search_knowledge(query)` 搜索互补品（如买了手机推荐耳机）。
5. 生成推荐语。
6. 调用 `send_message` 发送。
7. 调用 `record_message_sent(user_id)`。

# TODO: [SECTION] 可用工具:
1. `get_user_context(user_id)`: 获取用户的完整画像信息（消费等级、标签、历史行为）。
2. `search_knowledge(query, n_results=3)`: 
   - 场景一：搜商品（query="真皮公文包"）。
3. `search_marketing_scripts(query, scenario, n_results=3)`:
   - 场景二：搜话术（query="催付", scenario="cart_abandon"）。
4. `send_sms(user_id, phone, message)`: 发送营销短信。
5. `skip_marketing(user_id, reason)`: 跳过本次营销（如冷却期内、库存不足）。

# FIXME: [IMPORTANT] 业务规则 (Strict):
1. **高消费用户 (HIGH)**: 
   - 浏览时：推新品、限量版、尊享款。
   - 加购时：强调“专属权益”、“优先发货”、“稀缺库存”，少提小额优惠。
2. **价格敏感用户**: 
   - 浏览时：推性价比款、特价款。
   - 加购时：直接发优惠券（“立减20元”、“限时包邮”），强调价格优势。
3. **冷却期**: 
   - 1小时内已发送过消息 -> 跳过。
   - 24小时内发送超过3条 -> 跳过。

# TODO: [NOTE] 思考流程示例:
**Case A (浏览)**: 用户浏览了“Gucci酒神包”。
-> 画像：高消费。
-> 动作：搜“Gucci新款”、“高端女包”。
-> 决策：推“Gucci 2024早春新款，VIP优先购”。

**Case B (加购)**: 用户加购了“小米电饭煲”但未付款。
-> 画像：价格敏感。
-> 动作：搜“家电催付话术”、“限时折扣”。
-> 决策：推“购物车里的电饭煲降价了！限时立减50元，手慢无！”。

# TODO: [SECTION] 输入输出格式要求:
## 输入格式:
输入是一个 JSON 消息，包含:
- `user_id`: 用户ID
- `event_type`: 事件类型 (如 `high_interest_detected` 对应浏览, `add_to_cart` 对应加购)
- `context`: 上下文 (包含 `sku_id`, `price`, `action` 等)

## 输出要求:
用中文回答，清晰说明：
1. 识别到的场景（浏览 vs 加购）。
2. 调用的工具和查询词 (Query)。
3. 最终生成的短信文案。
"""

    def __init__(self, llm: Optional[ChatOpenAI] = None):
        # FIXME: [IMPORTANT] 初始化营销智能体。
        # TODO: 参数: llm: LangChain ChatOpenAI 实例。如果为 None，则创建一个用于测试的 Mock LLM。
        load_dotenv()

        # [NOTE] LLM 模型实例（可为真实模型或测试时的 Mock）
        self.llm = llm
        # [NOTE] LangChain Agent 的执行图（graph），由 create_agent 创建
        self.agent_graph: Optional[Any] = None
        # [NOTE] 提供给 LangChain 的工具列表（名称、描述、调用函数）
        self.tools: List[Tool] = []
        
        # [IMPORTANT] MCP 客户端：对接 Java 侧 MCP Server 的工具调用入口
        try:
            self.mcp_client = McpClient()
        except Exception as e:
            logger.warning(f"Failed to initialize MCP client: {e}")
            self.mcp_client = None

        # [STEP] 初始化工具（优先从 MCP 动态加载，失败时回退本地描述）
        self._initialize_tools()

        # [STEP] 只有提供了 LLM，才构建 Agent 执行图
        if llm:
            self._initialize_agent()

    @classmethod
    def from_env(cls) -> 'MarketingAgent':
        # TODO: [STEP] 从环境变量创建营销智能体（读取 API Key 和 Base URL）。
        # TODO: 如果未配置 API 密钥，则返回 Mock 智能体。
        # TODO: 返回: MarketingAgent 实例
        load_dotenv()

        api_key = os.getenv('OPENAI_API_KEY')
        base_url = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')

        if api_key:
            # 配置真实 LLM
            llm = ChatOpenAI(
                api_key=api_key,
                base_url=base_url,
                model=os.getenv('OPENAI_MODEL', 'gpt-4o'),
                temperature=0.7,
                max_tokens=500
            )
            logger.info(f"Created MarketingAgent with real LLM (model: {os.getenv('OPENAI_MODEL', 'gpt-4o')})")
            return cls(llm=llm)
        else:
            logger.warning("OPENAI_API_KEY not configured, using mock agent")
            return cls.create_mock()

        self.llm = llm
        self.agent_graph: Optional[Any] = None
        self.tools: List[Tool] = []

        self._initialize_tools()

        if llm:
            self._initialize_agent()

    def _initialize_tools(self):
        # TODO: [STEP] 从模块函数初始化 LangChain 工具。
        # TODO: 工具名到包装函数的映射：对外统一工具名，对内封装 MCP 调用
        tool_wrappers = {
            "get_user_context": self._wrap_get_user_context,
            "search_knowledge": self._wrap_search_knowledge,
            "send_sms": self._wrap_send_sms,
            "skip_marketing": self._wrap_skip_marketing
        }

        # [STEP] 优先通过 MCP 的 tools/list 动态加载工具描述
        if self.mcp_client:
            try:
                response = self.mcp_client.list_tools()
                mcp_tools = response.get("tools") if isinstance(response, dict) else None
                if isinstance(mcp_tools, list):
                    tools = []
                    for tool_desc in mcp_tools:
                        name = tool_desc.get("name")
                        # [NOTE] 只加载在本地实现了包装函数的工具
                        if name in tool_wrappers:
                            tools.append({
                                "name": name,
                                # [NOTE] MCP 描述为空时回退为名称，保证 LangChain 有可读说明
                                "description": tool_desc.get("description") or name,
                                "func": tool_wrappers[name]
                            })
                    if tools:
                        self.tools = tools
                        return
            except Exception as e:
                logger.warning(f"Failed to load MCP tools list: {e}")

        # [IMPORTANT] MCP 不可用或动态加载失败时，回退到本地静态工具描述
        self.tools = [
            {
                "name": "get_user_context",
                "description": "获取用户完整画像信息，包括消费等级、标签、近期行为等。输入: 用户ID (字符串)",
                "func": self._wrap_get_user_context
            },
            {
                "name": "search_knowledge",
                "description": "搜索商品知识库，查找相关商品信息。输入: 查询关键词 (字符串)",
                "func": self._wrap_search_knowledge
            },
            {
                "name": "send_sms",
                "description": "发送营销短信给用户。输入: JSON格式，包含user_id, phone, message",
                "func": self._wrap_send_sms
            },
            {
                "name": "skip_marketing",
                "description": "跳过本次营销，记录原因。输入: JSON格式，包含user_id, reason",
                "func": self._wrap_skip_marketing
            }
        ]

    def _wrap_get_user_context(self, user_id: str) -> str:
        # FIXME: [ACTION] get_user_context 的工具包装器：将 LLM 的工具调用转成 MCP 调用。
        if not self.mcp_client:
            return "MCP Client not initialized"
        try:
            context = self.mcp_client.call_tool("get_user_context", {"user_id": user_id})
            if context:
                # TODO: [NOTE] 格式化画像信息供 LLM 阅读
                profile = context.get('mysql_profile', {})
                formatted = f"""
用户ID: {profile.get('id')}
姓名: {profile.get('name')}
消费等级: {profile.get('spending_tier')}
标签: {', '.join(profile.get('identity_tags', []))}
近期活动: {context.get('redis_profile', {})}
"""
                return formatted
            else:
                return f"未找到用户 {user_id} 的信息"
        except Exception as e:
            return f"获取用户信息失败: {e}"

    def _wrap_search_knowledge(self, query: str) -> str:
        # FIXME: [ACTION] search_knowledge 的工具包装器：调用 MCP 的向量检索工具。
        if not self.mcp_client:
            return "MCP Client not initialized"
        try:
            results = self.mcp_client.call_tool("search_knowledge", {"query": query, "n_results": 3})
            if results:
                formatted = []
                for i, result in enumerate(results, 1):
                    formatted.append(f"""
商品 {i}:
- 名称: {result.get('name')}
- 分类: {result.get('category')}
- 价格: {result.get('price')}
- 卖点: {'; '.join(result.get('selling_points', []))}
""")
                return "\n".join(formatted)
            else:
                return f"未找到与 '{query}' 相关的商品"
        except Exception as e:
            return f"搜索商品失败: {e}"

    def _wrap_send_sms(self, input_str: str) -> str:
        # FIXME: [ACTION] send_sms 的工具包装器：解析 LLM 生成的 JSON 字符串并调用 MCP 发送短信。
        if not self.mcp_client:
            raise RuntimeError("MCP Client not initialized")
        try:
            data = json.loads(input_str)
            user_id = data.get('user_id')
            phone = data.get('phone')
            message = data.get('message')

            if not user_id or not phone or not message:
                raise RuntimeError(f"INVALID_TOOL_INPUT: user_id={user_id}, phone={phone}, message_present={bool(message)}")

            result = self.mcp_client.call_tool("send_sms", {
                "user_id": user_id,
                "phone": phone,
                "message": message
            })
            if not isinstance(result, dict) or result.get("success") is not True:
                raise RuntimeError(f"INVALID_MCP_RESULT: {result}")
            return f"短信发送结果: {result}"
        except Exception as e:
            # 硬核阻断：直接抛出异常，中断 Agent 执行，阻止 Offset 提交
            logger.error(f"严重错误：MCP 短信服务调用失败 - {e}")
            raise RuntimeError(f"MCP_CALL_FAILED: {e}")

    def _wrap_skip_marketing(self, input_str: str) -> str:
        # FIXME: [ACTION] skip_marketing 的工具包装器：解析输入并调用 MCP 记录跳过原因。
        if not self.mcp_client:
            return "MCP Client not initialized"
        try:
            data = json.loads(input_str)
            user_id = data.get('user_id')
            reason = data.get('reason')

            result = self.mcp_client.call_tool("skip_marketing", {
                "user_id": user_id,
                "reason": reason
            })
            return f"跳过营销: {result}"
        except Exception as e:
            return f"跳过操作失败: {e}"

    def _initialize_agent(self):
        # TODO: [STEP] 使用 LangChain 的 API 创建 Agent 执行图。
        self.agent_graph = create_agent(
            model=self.llm,
            tools=self.tools,
            system_prompt=self.SYSTEM_PROMPT
        )

        logger.info("Marketing Agent initialized")

    def process_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        # FIXME: [IMPORTANT] 处理高意向事件并做出营销决策。
        # TODO: 参数: event_data: 来自 Kafka 触发器的事件字典 (包含 user_id, event_type)
        # TODO: 返回: 包含智能体决策结果的字典
        if not self.agent_graph:
            raise RuntimeError("Agent not initialized. Please provide an LLM.")

        user_id = event_data.get('user_id')
        event_type = event_data.get('event_type', 'HIGH_INTENT')

        logger.info(f"Processing event for user {user_id}, type: {event_type}")

        # [STEP] 准备输入数据给 Agent
        input_data = {
            "messages": [f"用户 {user_id} 触发了 {event_type} 事件，请分析是否发送营销消息。"]
        }

        try:
            # [STEP] 执行 Agent 执行图并获取决策结果
            result = self.agent_graph.invoke(input_data)

            # [STEP] 从结果中提取最终消息
            messages = result.get('messages', [])
            final_output = messages[-1].content if messages else ""

            return {
                'success': True,
                'user_id': user_id,
                'agent_output': final_output,
                'full_result': result
            }

        except Exception as e:
            logger.error(f"Agent processing failed for user {user_id}: {e}")
            return {
                'success': False,
                'user_id': user_id,
                'error': str(e)
            }










    @classmethod
    def create_mock(cls) -> 'MarketingAgent':
        # TODO: [STEP] 创建一个带有用于测试的 Mock LLM 的营销智能体。
        # TODO: 返回: 配置为测试用途的 MarketingAgent 实例
        return cls(llm=None)


class MockChatModel:
    # TODO: [SECTION] 用于测试目的的 Mock 对话模型。返回可预测的响应以测试智能体行为。

    _llm_type_value = "mock"

    def __init__(self, responses: Optional[List[str]] = None):
        # FIXME: [IMPORTANT] 初始化 Mock 对话模型。
        # TODO: 参数: responses: 按顺序返回的响应列表
        self.responses = responses or []
        self.call_count = 0

    def bind_tools(self, tools, **kwargs):
        # FIXME: [ACTION] Mock bind_tools 方法。
        return self

    def invoke(self, messages, config=None, **kwargs):
        # FIXME: [ACTION] Mock invoke，返回预定的响应。
        self.call_count += 1

        # 在此处导入以避免循环依赖
        from langchain_core.messages import AIMessage

        # [NOTE] 返回一个用于测试的简单响应
        if self.responses and self.call_count <= len(self.responses):
            return AIMessage(content=self.responses[self.call_count - 1])

        # [NOTE] 默认响应
        return AIMessage(content="我已完成分析和营销决策。")

    @property
    def _llm_type(self):
        return self._llm_type_value


class MockMessage:
    # TODO: [NOTE] 用于测试的 Mock 消息。

    def __init__(self, content: str = ""):
        self.content = content

    def __repr__(self):
        return f"MockMessage(content={self.content!r})"


# TODO: [SECTION] 便捷函数：快速创建营销智能体实例。
def create_marketing_agent(llm: Optional[ChatOpenAI] = None, use_env: bool = False) -> MarketingAgent:
    # TODO: 参数:
    # TODO:   llm: ChatOpenAI 实例。如果为 None 且 use_env 为 False，则创建 Mock 智能体。
    # TODO:   use_env: 如果为 True 且 llm 为 None，则从环境变量创建智能体。
    # TODO: 返回: MarketingAgent 实例
    if llm is not None:
        return MarketingAgent(llm=llm)
    if use_env:
        return MarketingAgent.from_env()
    return MarketingAgent.create_mock()


if __name__ == "__main__":
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("营销智能体测试")
    print("=" * 50)

    # 使用 Mock LLM 创建智能体
    agent = MarketingAgent.create_mock()

    # 使用 MockChatModel 进行覆盖以进行测试
    mock_llm = MockChatModel(["已为用户发送营销短信"])
    agent.llm = mock_llm
    agent._initialize_agent()

    # 使用示例事件进行测试
    test_event = {
        "user_id": "test-user-123",
        "event_type": "HIGH_INTENT_CLICKS",
        "timestamp": "2024-02-26T12:00:00Z"
    }

    print(f"\n正在处理事件: {test_event}")
    print("-" * 50)

    result = agent.process_event(test_event)

    print("\n" + "=" * 50)
    print("智能体执行结果:")
    print(result)
