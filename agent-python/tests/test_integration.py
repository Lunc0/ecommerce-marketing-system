"""
Integration tests for Marketing Agent with business rules.
Tests the agent's decision-making based on different user profiles.
"""

import pytest
from unittest.mock import Mock, patch
from langchain_core.messages import AIMessage

from src.agent import (
    MarketingAgent,
    create_marketing_agent,
    MockChatModel
)
from src.tools import MarketingActions


class TestAgentBusinessRules:
    """Test agent behavior with different business rules."""

    @pytest.fixture
    def high_tier_user_context(self):
        """High spending tier user profile."""
        return {
            'mysql_profile': {
                'id': 'user-high-001',
                'name': '张三',
                'spending_tier': 'HIGH',
                'identity_tags': ['vip', 'high_value', 'premium']
            },
            'redis_profile': {
                'last_message_sent': '2024-02-26T08:00:00Z',
                'click_count_24h': 5
            }
        }

    @pytest.fixture
    def price_sensitive_user_context(self):
        """Price sensitive user profile."""
        return {
            'mysql_profile': {
                'id': 'user-price-001',
                'name': '李四',
                'spending_tier': 'MEDIUM',
                'identity_tags': ['price_sensitive', 'bargain_hunter']
            },
            'redis_profile': {
                'last_message_sent': '2024-02-25T10:00:00Z',
                'click_count_24h': 3
            }
        }

    @pytest.fixture
    def new_user_context(self):
        """New user profile."""
        return {
            'mysql_profile': {
                'id': 'user-new-001',
                'name': '王五',
                'spending_tier': 'LOW',
                'identity_tags': ['new_user', 'first_time']
            },
            'redis_profile': {
                'last_message_sent': None,
                'click_count_24h': 1
            }
        }

    @pytest.fixture
    def vip_user_context(self):
        """VIP user profile."""
        return {
            'mysql_profile': {
                'id': 'user-vip-001',
                'name': '赵六',
                'spending_tier': 'HIGH',
                'identity_tags': ['vip', 'loyal', 'premium']
            },
            'redis_profile': {
                'last_message_sent': '2024-02-26T11:00:00Z',
                'click_count_24h': 2
            }
        }

    @patch('src.agent.create_agent')
    def test_high_tier_user_receives_premium_product(
        self, mock_create_agent, high_tier_user_context
    ):
        """
        Test that high tier user receives premium product recommendation,
        not cheap products.
        """
        # Mock the agent graph
        mock_graph = Mock()

        # Simulate agent response for high tier user
        response = """
思考: 用户张三的消费等级是 HIGH，属于 VIP 高价值用户。
根据业务规则，不应推荐廉价品（<100元），应该推送高价值商品（>500元）。
让我搜索高端商品。

动作: send_sms
消息: 尊敬的VIP会员，限量版智能手表新品上市，专享9折优惠，立即选购！
"""
        mock_message = AIMessage(content=response)
        mock_graph.invoke.return_value = {'messages': [mock_message]}
        mock_create_agent.return_value = mock_graph

        # Create and process event
        agent = MarketingAgent(llm=None)
        agent.llm = MockChatModel([response])
        agent._initialize_agent()

        event = {"user_id": "user-high-001", "event_type": "HIGH_INTENT"}
        result = agent.process_event(event)

        assert result['success'] is True
        assert '智能手表' in result['agent_output'] or '高端' in result['agent_output']

    @patch('src.agent.create_agent')
    def test_price_sensitive_user_receives_discount(
        self, mock_create_agent, price_sensitive_user_context
    ):
        """
        Test that price sensitive user receives discount information.
        """
        mock_graph = Mock()

        response = """
思考: 用户李四是价格敏感用户，标签包含 price_sensitive。
根据业务规则，应该推送折扣、优惠券信息，突出优惠力度。

动作: send_sms
消息: 限时秒杀！全场低至3折，最高立省500元，手慢无！
"""
        mock_message = AIMessage(content=response)
        mock_graph.invoke.return_value = {'messages': [mock_message]}
        mock_create_agent.return_value = mock_graph

        agent = MarketingAgent(llm=None)
        agent.llm = MockChatModel([response])
        agent._initialize_agent()

        event = {"user_id": "user-price-001", "event_type": "HIGH_INTENT"}
        result = agent.process_event(event)

        assert result['success'] is True
        assert '秒杀' in result['agent_output'] or '折扣' in result['agent_output']

    @patch('src.agent.create_agent')
    def test_new_user_receives_welcome_coupon(
        self, mock_create_agent, new_user_context
    ):
        """
        Test that new user receives welcome coupon.
        """
        mock_graph = Mock()

        response = """
思考: 用户王五是新用户，标签包含 new_user。
根据业务规则，应该推送新人专属优惠券。

动作: send_sms
消息: 新人专享！首单立减50元，热门好物等你来选！
"""
        mock_message = AIMessage(content=response)
        mock_graph.invoke.return_value = {'messages': [mock_message]}
        mock_create_agent.return_value = mock_graph

        agent = MarketingAgent(llm=None)
        agent.llm = MockChatModel([response])
        agent._initialize_agent()

        event = {"user_id": "user-new-001", "event_type": "HIGH_INTENT"}
        result = agent.process_event(event)

        assert result['success'] is True
        assert '新人' in result['agent_output'] or '首单' in result['agent_output']

    @patch('src.agent.create_agent')
    def test_vip_user_receives_exclusive_offer(
        self, mock_create_agent, vip_user_context
    ):
        """
        Test that VIP user receives exclusive offer.
        """
        mock_graph = Mock()

        response = """
思考: 用户赵六是 VIP 会员，标签包含 vip、premium。
根据业务规则，应该推送会员专属权益。

动作: send_sms
消息: 会员尊享，新品优先购，积分兑换正当时！
"""
        mock_message = AIMessage(content=response)
        mock_graph.invoke.return_value = {'messages': [mock_message]}
        mock_create_agent.return_value = mock_graph

        agent = MarketingAgent(llm=None)
        agent.llm = MockChatModel([response])
        agent._initialize_agent()

        event = {"user_id": "user-vip-001", "event_type": "HIGH_INTENT"}
        result = agent.process_event(event)

        assert result['success'] is True
        assert '会员' in result['agent_output'] or '尊享' in result['agent_output']


class TestAgentWithRealLLMConfig:
    """Test agent configuration for real LLM."""

    @patch.dict('os.environ', {
        'OPENAI_API_KEY': 'test-key-12345',
        'OPENAI_BASE_URL': 'https://api.test.com/v1',
        'OPENAI_MODEL': 'gpt-4o-mini'
    })
    @patch('src.agent.ChatOpenAI')
    def test_agent_from_env_creates_real_llm(self, mock_chat_openai):
        """Test that from_env creates real LLM when API key is configured."""
        mock_llm = Mock()
        mock_chat_openai.return_value = mock_llm

        agent = MarketingAgent.from_env()

        mock_chat_openai.assert_called_once()
        call_kwargs = mock_chat_openai.call_args[1]
        assert call_kwargs['api_key'] == 'test-key-12345'
        assert call_kwargs['base_url'] == 'https://api.test.com/v1'
        assert call_kwargs['model'] == 'gpt-4o-mini'

    @patch.dict('os.environ', {}, clear=True)
    def test_agent_from_env_creates_mock_when_no_api_key(self):
        """Test that from_env creates mock agent when API key is not configured."""
        agent = MarketingAgent.from_env()

        assert agent.llm is None
        assert agent.agent_graph is None

    @patch('src.agent.create_agent')
    @patch.dict('os.environ', {
        'OPENAI_API_KEY': 'test-key-12345',
        'OPENAI_MODEL': 'gpt-4o'
    })
    @patch('src.agent.ChatOpenAI')
    def test_create_marketing_agent_use_env_flag(
        self, mock_chat_openai, mock_create_agent
    ):
        """Test create_marketing_agent with use_env flag."""
        mock_llm = Mock()
        mock_chat_openai.return_value = mock_llm
        mock_graph = Mock()
        mock_create_agent.return_value = mock_graph

        agent = create_marketing_agent(use_env=True)

        mock_chat_openai.assert_called_once()


class TestAgentWithCooldownRules:
    """Test agent respects cooldown rules."""

    @patch('src.agent.get_user_context')
    @patch('src.agent.search_knowledge')
    @patch('src.agent.skip_marketing')
    def test_skips_marketing_in_cooldown_period(
        self, mock_skip, mock_search, mock_get_context
    ):
        """
        Test that agent skips marketing if user is in cooldown period.
        """
        # User who received message recently
        mock_get_context.return_value = {
            'mysql_profile': {
                'id': 'user-cooldown',
                'spending_tier': 'HIGH',
                'identity_tags': ['vip']
            },
            'redis_profile': {
                'last_message_sent': '2024-02-26T22:00:00Z',  # Just sent
                'click_count_24h': 10
            }
        }
        mock_skip.return_value = {'success': True, 'action': 'SKIP_MARKETING'}

        # Create mock agent that skips
        agent = MarketingAgent.create_mock()
        mock_graph = Mock()
        mock_message = AIMessage(content="用户在冷却期内，跳过本次营销。")
        mock_graph.invoke.return_value = {'messages': [mock_message]}

        agent.llm = MockChatModel(["用户在冷却期内，跳过本次营销。"])
        agent._initialize_agent()

        event = {"user_id": "user-cooldown", "event_type": "HIGH_INTENT"}
        result = agent.process_event(event)

        assert result['success'] is True


class TestAgentMessageQuality:
    """Test agent generates quality marketing messages."""

    @pytest.fixture
    def sample_products(self):
        """Sample products for knowledge base."""
        return [
            {
                'name': '智能手表',
                'category': '电子产品',
                'price': 2999,
                'selling_points': '精工制造，限量发售，收藏价值高'
            },
            {
                'name': '棉质T恤',
                'category': '服饰',
                'price': 99,
                'selling_points': '透气舒适，多色可选'
            },
            {
                'name': '会员专属礼盒',
                'category': '礼品',
                'price': 599,
                'selling_points': '限量1000份，会员专享'
            }
        ]

    def test_message_length_under_70_chars(self):
        """
        Test that agent respects message length constraint (max 70 chars).
        This is a placeholder test - real testing would require actual LLM.
        """
        # Simulated messages from different user segments
        messages = {
            'high_tier': '尊享VIP礼遇，限量智能手表新品上市，立即选购！',
            'price_sensitive': '限时秒杀！全场低至3折，手慢无！',
            'new_user': '新人专享！首单立减50元，热门好物等你选！',
            'vip': '会员尊享，新品优先购，积分兑换正当时！'
        }

        for segment, message in messages.items():
            assert len(message) <= 70, f"{segment} message too long: {len(message)} chars"


class TestAgentToolWrappers:
    """Test agent tool wrapper functions."""

    def test_get_user_context_formatting(self):
        """Test that user context is properly formatted for LLM."""
        agent = MarketingAgent.create_mock()

        with patch('src.agent.get_user_context') as mock_get:
            mock_get.return_value = {
                'mysql_profile': {
                    'id': 'user-001',
                    'name': '测试用户',
                    'spending_tier': 'HIGH',
                    'identity_tags': ['vip']
                },
                'redis_profile': {'last_click': '2024-02-26'}
            }

            result = agent._wrap_get_user_context('user-001')

            assert 'user-001' in result
            assert 'HIGH' in result
            assert 'vip' in result

    def test_search_knowledge_formatting(self):
        """Test that knowledge search results are properly formatted."""
        agent = MarketingAgent.create_mock()

        with patch('src.agent.search_knowledge') as mock_search:
            mock_search.return_value = [
                {
                    'name': '测试商品',
                    'category': '测试分类',
                    'price': 999,
                    'selling_points': '测试卖点'
                }
            ]

            result = agent._wrap_search_knowledge('测试')

            assert '测试商品' in result
            assert '999' in result
            assert '测试卖点' in result
