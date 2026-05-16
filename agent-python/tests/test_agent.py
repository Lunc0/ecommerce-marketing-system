"""
Unit tests for Marketing Agent module.
Tests LangChain Agent initialization and tool usage with mocks.
"""

import pytest
from unittest.mock import Mock, patch
from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI

from src.agent import MarketingAgent


class TestMarketingAgent:
    """Test cases for MarketingAgent class."""

    @pytest.fixture
    def mock_llm(self):
        """Create a mock LLM for testing."""
        llm = Mock(spec=ChatOpenAI)
        return llm

    @pytest.fixture
    def mock_mcp_client(self):
        with patch('src.agent.McpClient') as MockClient:
            client_instance = MockClient.return_value
            yield client_instance

    def test_initialization_without_llm(self, mock_mcp_client):
        """Test agent initialization without LLM (testing mode)."""
        agent = MarketingAgent(llm=None)

        assert agent.llm is None
        assert agent.agent_graph is None
        assert len(agent.tools) == 4
        assert agent.tools[0]["name"] == "get_user_context"
        assert agent.mcp_client == mock_mcp_client

    def test_tools_initialization(self, mock_llm, mock_mcp_client):
        """Test that all required tools are initialized."""
        agent = MarketingAgent(llm=mock_llm)

        tool_names = [tool["name"] for tool in agent.tools]
        expected_names = ["get_user_context", "search_knowledge", "send_sms", "skip_marketing"]

        assert set(tool_names) == set(expected_names)

    def test_wrap_get_user_context_success(self, mock_llm, mock_mcp_client):
        """Test user context wrapper with successful response."""
        agent = MarketingAgent(llm=mock_llm)

        mock_mcp_client.call_tool.return_value = {
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
        mock_mcp_client.call_tool.assert_called_with("get_user_context", {"user_id": "user-001"})

    def test_wrap_get_user_context_not_found(self, mock_llm, mock_mcp_client):
        """Test user context wrapper when user not found."""
        agent = MarketingAgent(llm=mock_llm)

        mock_mcp_client.call_tool.return_value = None

        result = agent._wrap_get_user_context('user-001')

        assert "未找到用户 user-001 的信息" in result

    def test_wrap_search_knowledge_success(self, mock_llm, mock_mcp_client):
        """Test search knowledge wrapper."""
        agent = MarketingAgent(llm=mock_llm)

        mock_mcp_client.call_tool.return_value = [
            {
                'name': 'Test Product',
                'category': 'Electronics',
                'price': 100.0,
                'selling_points': ['Cheap', 'Good']
            }
        ]

        result = agent._wrap_search_knowledge('phone')

        assert 'Test Product' in result
        assert 'Electronics' in result
        mock_mcp_client.call_tool.assert_called_with("search_knowledge", {"query": "phone", "n_results": 3})

    def test_wrap_send_sms_success(self, mock_llm, mock_mcp_client):
        """Test send sms wrapper."""
        agent = MarketingAgent(llm=mock_llm)

        mock_mcp_client.call_tool.return_value = {'success': True}

        import json
        input_str = json.dumps({
            "user_id": "u1",
            "phone": "123",
            "message": "msg"
        })
        result = agent._wrap_send_sms(input_str)

        assert "短信发送结果" in result
        mock_mcp_client.call_tool.assert_called_with("send_sms", {
            "user_id": "u1",
            "phone": "123",
            "message": "msg"
        })

    def test_wrap_send_sms_invalid_result_raises(self, mock_llm, mock_mcp_client):
        agent = MarketingAgent(llm=mock_llm)

        mock_mcp_client.call_tool.return_value = None

        import json
        input_str = json.dumps({
            "user_id": "u1",
            "phone": "123",
            "message": "msg"
        })

        with pytest.raises(RuntimeError) as e:
            agent._wrap_send_sms(input_str)
        assert "MCP_CALL_FAILED" in str(e.value)

    def test_wrap_send_sms_missing_fields_raises(self, mock_llm, mock_mcp_client):
        agent = MarketingAgent(llm=mock_llm)

        import json
        input_str = json.dumps({
            "user_id": "u1",
            "phone": "123",
            "message": ""
        })

        with pytest.raises(RuntimeError) as e:
            agent._wrap_send_sms(input_str)
        assert "MCP_CALL_FAILED" in str(e.value)
