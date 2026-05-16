package com.ecommerce.marketing.mcp;

import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
@RequestMapping("/mcp")
@RequiredArgsConstructor
public class McpController {

    private final McpToolService toolService;

    @PostMapping
    public McpResponse handle(@RequestBody McpRequest request) {
        String id = request.getId();
        String method = request.getMethod();
        String jsonrpc = request.getJsonrpc();
        if (jsonrpc != null && !jsonrpc.isBlank() && !"2.0".equals(jsonrpc)) {
            return new McpResponse("2.0", id, null, new McpError(-32600, "Invalid Request", "jsonrpc"));
        }
        if (method == null || method.isBlank()) {
            return new McpResponse("2.0", id, null, new McpError(-32600, "Invalid Request", null));
        }
        try {
            return switch (method) {
                case "tools/list" -> new McpResponse("2.0", id, Map.of("tools", toolService.listTools()), null);
                case "tools/call" -> {
                    Map<String, Object> params = request.getParams();
                    Object toolNameObj = params == null ? null : params.get("name");
                    String toolName = toolNameObj == null ? null : String.valueOf(toolNameObj);
                    if (toolName == null || toolName.isBlank()) {
                        yield new McpResponse("2.0", id, null, new McpError(-32602, "Invalid params", "name"));
                    }
                    if (!toolService.supportsTool(toolName)) {
                        yield new McpResponse("2.0", id, null, new McpError(-32601, "Tool not found", toolName));
                    }

                    Object argumentsObj = params == null ? null : params.get("arguments");
                    Map<String, Object> arguments;
                    if (argumentsObj == null) {
                        arguments = Map.of();
                    } else if (argumentsObj instanceof Map<?, ?> raw) {
                        arguments = (Map<String, Object>) raw;
                    } else {
                        yield new McpResponse("2.0", id, null, new McpError(-32602, "Invalid params", "arguments"));
                    }
                    Object result = toolService.callTool(toolName, arguments);
                    yield new McpResponse("2.0", id, result, null);
                }
                default -> new McpResponse("2.0", id, null, new McpError(-32601, "Method not found", method));
            };
        } catch (IllegalArgumentException e) {
            return new McpResponse("2.0", id, null, new McpError(-32602, "Invalid params", e.getMessage()));
        } catch (Exception e) {
            return new McpResponse("2.0", id, null, new McpError(-32000, "Server error", e.getMessage()));
        }
    }
}
