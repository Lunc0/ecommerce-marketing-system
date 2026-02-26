"""
Unit tests for Marketing Agent module.
Tests LangChain Agent initialization and tool usage with mocks.
"""

import pytest
from unittest.mock import Mock, patch
from langchain_openai import ChatOpenAI
from langchain_core.messages import AIMessage

from src.agent import (
    MarketingAgent,
    create_marketing_agent,
    MockChatModel
)
from src.tools.action import MarketingActions


class TestMarketingAgent:
    """Test cases for MarketingAgent class."""

    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM for testing."""
        llm = Mock(spec=ChatOpenAI)
        return llm

    @pytest.fixture
    def sample_event(self):
        """Sample event data from Kafka."""
        return {
            "user_id": "test-user-123",
            "event_type": "HIGH_INTENT_CLICKS",
            "timestamp": "2024-02-26T12:00:00Z"
        }

    def test_initialization_without_llm(self):
        """Test agent initialization without LLM (testing mode)."""
        agent = MarketingAgent(llm=None)

        assert agent.llm is None
        assert agent.agent_graph is None
        assert len(agent.tools) == 4
        assert agent.tools[0]["name"] == "get_user_context"

    def test_create_mock(self):
        """Test creating agent with mock LLM."""
        agent = MarketingAgent.create_mock()

        assert agent.llm is None
        assert len(agent.tools) == 4

    def test_tools_initialization(self, mock_llm):
        """Test that all required tools are initialized."""
        agent = MarketingAgent(llm=mock_llm)

        tool_names = [tool["name"] for tool in agent.tools]
        expected_names = ["get_user_context", "search_knowledge", "send_sms", "skip_marketing"]

        assert set(tool_names) == set(expected_names)

    @patch('src.agent.create_agent')
    def test_agent_initialization(self, mock_create_agent, mock_llm):
        """Test that agent is created with LangChain."""
        mock_graph = Mock()
        mock_graph.invoke.return_value = {'messages': [AIMessage(content="测试结果")]}
        mock_create_agent.return_value = mock_graph

        agent = MarketingAgent(llm=mock_llm)

        mock_create_agent.assert_called_once()
        assert agent.agent_graph == mock_graph

    def test_wrap_get_user_context_success(self, mock_llm):
        """Test user context wrapper with successful response."""
        agent = MarketingAgent(llm=mock_llm)

        with patch('src.agent.get_user_context') as mock_get_context:
            mock_get_context.return_value = {
                'mysql_profile': {
                    'id': 'user-001',
                    'name': '测试用户',
                    'spending_tier': 'HIGH',
                    'identity_tags': ['vip', 'high_value']
                },
                'redis_profile': {'last_click': '2024-02-26'}
            }

            result = agent._wrap_get_user_context('user-001')

            assert 'user-001' in result
            assert 'HIGH' in result
            assert 'vip' in result

    def test_wrap_get_user_context_not_found(self, mock_llm):
        """Test user context wrapper when user not found."""
        agent = MarketingAgent(llm=mock_llm)

        with patch('src.agent.get_user_context') as mock_get_context:
            mock_get_context.return_value = None

            result = agent._wrap_get_user_context('nonexistent-user')

            assert '未找到' in result

    def test_wrap_search_knowledge_success(self, mock_llm):
        """Test knowledge search wrapper with successful response."""
        agent = MarketingAgent(llm=mock_llm)

        with patch('src.agent.search_knowledge') as mock_search:
            mock_search.return_value = [
                {
                    'name': '智能手表',
                    'category': '电子产品',
                    'price': 2999,
                    'selling_points': '高端，智能'
                }
            ]

            result = agent._wrap_search_knowledge('手表')

            assert '智能手表' in result
            assert '2999' in result

    def test_wrap_search_knowledge_empty(self, mock_llm):
        """Test knowledge search wrapper when no results."""
        agent = MarketingAgent(llm=mock_llm)

        with patch('src.agent.search_knowledge') as mock_search:
            mock_search.return_value = []

            result = agent._wrap_search_knowledge('不存在的商品')

            assert '未找到' in result

    def test_wrap_send_sms_success(self, mock_llm):
        """Test SMS wrapper with successful send."""
        agent = MarketingAgent(llm=mock_llm)

        with patch('src.agent.send_sms') as mock_send:
            mock_send.return_value = {'success': True, 'action': 'SMS_SENT'}

            result = agent._wrap_send_sms('{"user_id": "user-001", "phone": "13800138000", "message": "test"}')

            assert 'success' in result or '短信' in result

    def test_wrap_send_sms_invalid_json(self, mock_llm):
        """Test SMS wrapper with invalid JSON."""
        agent = MarketingAgent(llm=mock_llm)

        result = agent._wrap_send_sms('invalid json')

        assert '失败' in result or '错误' in result

    def test_wrap_skip_marketing(self, mock_llm):
        """Test skip marketing wrapper."""
        agent = MarketingAgent(llm=mock_llm)

        with patch('src.agent.skip_marketing') as mock_skip:
            mock_skip.return_value = {'success': True, 'action': 'SKIP_MARKETING'}

            result = agent._wrap_skip_marketing('{"user_id": "user-001", "reason": "已发送过"}')

            assert 'skip' in result.lower() or '跳过' in result

    def test_process_event_without_agent_executor(self, mock_llm):
        """Test process event when agent not initialized."""
        agent = MarketingAgent(llm=None)

        with pytest.raises(RuntimeError, match="Agent not initialized"):
            agent.process_event({"user_id": "test-user"})


class TestMockChatModel:
    """Test cases for MockChatModel class."""

    def test_initialization(self):
        """Test MockChatModel initialization."""
        llm = MockChatModel()

        assert llm.call_count == 0
        assert llm._llm_type == "mock"

    def test_invoke(self):
        """Test MockChatModel invoke method."""
        llm = MockChatModel(["响应1", "响应2"])

        result1 = llm.invoke("test message 1")
        result2 = llm.invoke("test message 2")

        assert llm.call_count == 2
        assert isinstance(result1, AIMessage)
        assert result1.content == "响应1"
        assert result2.content == "响应2"

    def test_invoke_default_response(self):
        """Test MockChatModel invoke with default response."""
        llm = MockChatModel()

        result = llm.invoke("test message")

        assert llm.call_count == 1
        assert isinstance(result, AIMessage)
        assert len(result.content) > 0

    def test_bind_tools(self):
        """Test bind_tools returns self."""
        llm = MockChatModel()
        result = llm.bind_tools([])

        assert result is llm


class TestCreateMarketingAgent:
    """Test cases for create_marketing_agent convenience function."""

    def test_create_with_llm(self):
        """Test creating agent with provided LLM."""
        mock_llm = Mock(spec=ChatOpenAI)
        agent = create_marketing_agent(llm=mock_llm)

        assert isinstance(agent, MarketingAgent)
        assert agent.llm == mock_llm

    def test_create_without_llm(self):
        """Test creating agent without LLM (mock mode)."""
        agent = create_marketing_agent(llm=None)

        assert isinstance(agent, MarketingAgent)
        assert agent.llm is None


class TestAgentIntegration:
    """Integration tests for agent workflow."""

    @patch('src.agent.create_agent')
    def test_full_workflow_with_mock_llm(self, mock_create_agent):
        """Test full agent workflow from event to decision."""
        # Setup mocks
        mock_graph = Mock()
        mock_message = AIMessage(content="已为用户发送营销短信")
        mock_graph.invoke.return_value = {'messages': [mock_message]}
        mock_create_agent.return_value = mock_graph

        # Create agent with MockChatModel
        agent = MarketingAgent(llm=None)
        mock_llm = MockChatModel()
        agent.llm = mock_llm
        agent._initialize_agent()

        # Process event
        event = {"user_id": "test-user-123", "event_type": "HIGH_INTENT"}
        result = agent.process_event(event)

        assert result['success'] is True
        assert result['user_id'] == "test-user-123"
        assert 'agent_output' in result
        assert result['agent_output'] == "已为用户发送营销短信"

    def test_process_event_error_handling(self):
        """Test error handling in process_event."""
        agent = MarketingAgent(llm=None)
        mock_llm = MockChatModel()
        agent.llm = mock_llm

        # Mock _initialize_agent to raise an exception
        agent._initialize_agent = Mock(side_effect=Exception("Connection error"))

        with pytest.raises(RuntimeError):
            agent.process_event({"user_id": "test-user"})


class TestToolDescriptions:
    """Test that tool descriptions are properly set."""

    def test_tool_descriptions(self):
        """Test that all tools have descriptions."""
        agent = MarketingAgent(llm=None)

        for tool in agent.tools:
            assert tool["name"]
            assert tool["description"]
            assert len(tool["description"]) > 10

    def test_tool_names_match_expected(self):
        """Test tool names match expected values."""
        agent = MarketingAgent(llm=None)

        tool_names = [t["name"] for t in agent.tools]
        assert "get_user_context" in tool_names
        assert "search_knowledge" in tool_names
        assert "send_sms" in tool_names
        assert "skip_marketing" in tool_names
