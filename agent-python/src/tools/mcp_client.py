"""
MCP client for calling Java tool services.
"""

import json
import os
import uuid
from typing import Any, Dict, Optional
from urllib.error import URLError
from urllib.request import Request, urlopen

from dotenv import load_dotenv


class McpClient:
    def __init__(self, server_url: Optional[str] = None, timeout: Optional[float] = None):
        load_dotenv()
        self.server_url = server_url or os.getenv("MCP_SERVER_URL", "http://localhost:8080/mcp")
        self.timeout = timeout if timeout is not None else float(os.getenv("MCP_TIMEOUT", "10"))

    def list_tools(self) -> Dict[str, Any]:
        return self._request("tools/list", {})

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        return self._request("tools/call", {"name": name, "arguments": arguments})

    def _request(self, method: str, params: Dict[str, Any]) -> Any:
        request_id = str(uuid.uuid4())
        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params
        }
        body = json.dumps(payload).encode("utf-8")
        request = Request(
            self.server_url,
            data=body,
            headers={"Content-Type": "application/json"}
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                raw = response.read().decode("utf-8")
        except URLError as e:
            raise RuntimeError(f"MCP_REQUEST_FAILED: {e}") from e
        except Exception as e:
            raise RuntimeError(f"MCP_REQUEST_FAILED: {e}") from e

        try:
            data = json.loads(raw)
        except Exception as e:
            raise RuntimeError(f"MCP_INVALID_JSON_RESPONSE: {raw[:300]}") from e

        if not isinstance(data, dict):
            raise RuntimeError(f"MCP_INVALID_RESPONSE: expected object, got {type(data).__name__}")

        jsonrpc = data.get("jsonrpc")
        if jsonrpc is not None and jsonrpc != "2.0":
            raise RuntimeError(f"MCP_INVALID_RESPONSE: jsonrpc={jsonrpc}")

        resp_id = data.get("id")
        if resp_id is not None and resp_id != request_id:
            raise RuntimeError(f"MCP_INVALID_RESPONSE: id_mismatch req={request_id} resp={resp_id}")

        err = data.get("error")
        if err:
            raise RuntimeError(self._format_error(err))

        if "result" not in data:
            raise RuntimeError(f"MCP_INVALID_RESPONSE: missing result/error, keys={list(data.keys())}")

        return data.get("result")

    @staticmethod
    def _format_error(err: Any) -> str:
        if isinstance(err, dict):
            code = err.get("code")
            message = err.get("message")
            data = err.get("data")
            parts = []
            if code is not None:
                parts.append(f"code={code}")
            if message:
                parts.append(f"message={message}")
            if data is not None:
                parts.append(f"data={data}")
            return "MCP_ERROR: " + ", ".join(parts) if parts else f"MCP_ERROR: {err}"
        return f"MCP_ERROR: {err}"
