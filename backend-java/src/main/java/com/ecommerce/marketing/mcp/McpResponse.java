package com.ecommerce.marketing.mcp;

import lombok.AllArgsConstructor;
import lombok.Data;

@Data
@AllArgsConstructor
public class McpResponse {
    private String jsonrpc;
    private String id;
    private Object result;
    private McpError error;
}
