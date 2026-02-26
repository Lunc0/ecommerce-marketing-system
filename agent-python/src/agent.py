"""
Marketing Agent based on LangChain Agent API.
Integrates database, RAG, and action tools to make intelligent marketing decisions.
"""

import logging
from typing import Dict, Any, Optional, List
from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import os

from .tools import (
    get_user_context,
    search_knowledge,
    send_sms,
    skip_marketing
)

logger = logging.getLogger(__name__)


class MarketingAgent:
    """
    Marketing Agent using LangChain Agent API.
    Makes intelligent decisions about when and how to market to users.
    """

    # System Prompt with business rules
    SYSTEM_PROMPT = """你是一个电商营销智能体，负责根据用户行为决定是否发送营销消息。

## 可用工具:
1. get_user_context(user_id): 获取用户的完整画像信息（Redis 和 MySQL）
   - 输入: 用户ID (字符串)
   - 返回: 包含消费等级、标签、近期行为等信息

2. search_knowledge(query, n_results=3): 搜索商品知识库
   - 输入: 查询关键词 (字符串)
   - 返回: 相关商品信息（名称、卖点、价格等）

3. send_sms(user_id, phone, message): 发送营销短信
   - 输入: JSON格式，包含user_id, phone, message
   - 返回: 发送结果

4. skip_marketing(user_id, reason): 跳过本次营销
   - 输入: JSON格式，包含user_id, reason
   - 返回: 跳过记录

## 业务规则 (IMPORTANT):
- 高消费用户 (spending_tier=HIGH): 不推荐廉价品，只推送高价值商品
- 价格敏感用户 (标签包含 price_sensitive): 可以推送折扣、优惠信息
- 新用户 (标签包含 new_user): 推送新人优惠券
- 累计消费高的用户: 推送会员权益、专属商品

## 思考流程:
1. 首先调用 get_user_context() 了解用户画像
2. 根据用户画像调用 search_knowledge() 查找合适商品
3. 判断是否应该营销:
   - 如果符合条件，调用 send_sms() 发送消息
   - 如果不符合条件（如刚发送过、用户画像不匹配），调用 skip_marketing()
4. 返回最终决策和结果

## 输入格式:
输入是一个 JSON 字符串，包含:
- user_id: 用户ID (必需)
- event_type: 事件类型 (可选)

## 输出格式:
用中文回答，说明你的思考过程和最终决策。
"""

    def __init__(self, llm: Optional[ChatOpenAI] = None):
        """
        Initialize the Marketing Agent.

        Args:
            llm: LangChain ChatOpenAI instance. If None, creates a mock LLM for testing.
        """
        load_dotenv()

        self.llm = llm
        self.agent_graph: Optional[Any] = None
        self.tools: List[Tool] = []

        self._initialize_tools()

        if llm:
            self._initialize_agent()

    def _initialize_tools(self):
        """Initialize LangChain tools from our module functions."""
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
        """Tool wrapper for get_user_context."""
        try:
            context = get_user_context(user_id)
            if context:
                # Format context for LLM readability
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
        """Tool wrapper for search_knowledge."""
        try:
            results = search_knowledge(query, n_results=3)
            if results:
                formatted = []
                for i, result in enumerate(results, 1):
                    formatted.append(f"""
商品 {i}:
- 名称: {result.get('name')}
- 分类: {result.get('category')}
- 价格: {result.get('price')}
- 卖点: {result.get('selling_points')}
""")
                return "\n".join(formatted)
            else:
                return f"未找到与 '{query}' 相关的商品"
        except Exception as e:
            return f"搜索商品失败: {e}"

    def _wrap_send_sms(self, input_str: str) -> str:
        """Tool wrapper for send_sms."""
        try:
            import json
            data = json.loads(input_str)
            user_id = data.get('user_id')
            phone = data.get('phone')
            message = data.get('message')

            result = send_sms(user_id, phone, message)
            return f"短信发送结果: {result}"
        except Exception as e:
            return f"发送短信失败: {e}"

    def _wrap_skip_marketing(self, input_str: str) -> str:
        """Tool wrapper for skip_marketing."""
        try:
            import json
            data = json.loads(input_str)
            user_id = data.get('user_id')
            reason = data.get('reason')

            result = skip_marketing(user_id, reason)
            return f"跳过营销: {result}"
        except Exception as e:
            return f"跳过操作失败: {e}"

    def _initialize_agent(self):
        """Initialize the Agent with LangChain."""
        # Create agent using new LangChain API
        self.agent_graph = create_agent(
            model=self.llm,
            tools=self.tools,
            system_prompt=self.SYSTEM_PROMPT
        )

        logger.info("Marketing Agent initialized")

    def process_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a high-intent event and make marketing decision.

        Args:
            event_data: Event dictionary from Kafka trigger
                - user_id: User identifier (required)
                - event_type: Event type (optional)

        Returns:
            Dictionary containing the agent's decision and result
        """
        if not self.agent_graph:
            raise RuntimeError("Agent not initialized. Please provide an LLM.")

        user_id = event_data.get('user_id')
        event_type = event_data.get('event_type', 'HIGH_INTENT')

        logger.info(f"Processing event for user {user_id}, type: {event_type}")

        # Prepare input for agent
        input_data = {
            "messages": [f"用户 {user_id} 触发了 {event_type} 事件，请分析是否发送营销消息。"]
        }

        try:
            # Execute agent graph
            result = self.agent_graph.invoke(input_data)

            # Extract final message from result
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
        """
        Create a Marketing Agent with mock LLM for testing.

        Returns:
            MarketingAgent instance configured for testing
        """
        return cls(llm=None)


class MockChatModel:
    """
    Mock Chat Model for testing purposes.
    Returns predictable responses for testing agent behavior.
    """

    _llm_type_value = "mock"

    def __init__(self, responses: Optional[List[str]] = None):
        """
        Initialize Mock Chat Model.

        Args:
            responses: List of responses to return in order
        """
        self.responses = responses or []
        self.call_count = 0

    def bind_tools(self, tools):
        """Mock bind_tools method."""
        return self

    def invoke(self, messages, config=None, **kwargs):
        """Mock invoke that returns predetermined response."""
        self.call_count += 1

        # Return a simple response for testing
        if self.responses and self.call_count <= len(self.responses):
            return MockMessage(content=self.responses[self.call_count - 1])

        # Default response
        return MockMessage(content="我已完成分析和营销决策。")

    @property
    def _llm_type(self):
        return self._llm_type_value


class MockMessage:
    """Mock message for testing."""

    def __init__(self, content: str = ""):
        self.content = content


# Convenience function
def create_marketing_agent(llm: Optional[ChatOpenAI] = None) -> MarketingAgent:
    """
    Create a Marketing Agent instance.

    Args:
        llm: ChatOpenAI instance. If None, creates mock agent.

    Returns:
        MarketingAgent instance
    """
    if llm is None:
        return MarketingAgent.create_mock()
    return MarketingAgent(llm=llm)


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("Marketing Agent Test")
    print("=" * 50)

    # Create agent with mock LLM
    agent = MarketingAgent.create_mock()

    # Override with MockChatModel for testing
    mock_llm = MockChatModel(["已为用户发送营销短信"])
    agent.llm = mock_llm
    agent._initialize_agent()

    # Test with sample event
    test_event = {
        "user_id": "test-user-123",
        "event_type": "HIGH_INTENT_CLICKS",
        "timestamp": "2024-02-26T12:00:00Z"
    }

    print(f"\nProcessing event: {test_event}")
    print("-" * 50)

    result = agent.process_event(test_event)

    print("\n" + "=" * 50)
    print("Agent Result:")
    print(result)
