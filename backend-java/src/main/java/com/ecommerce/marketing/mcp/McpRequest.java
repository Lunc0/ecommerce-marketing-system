package com.ecommerce.marketing.mcp;

import lombok.Data;

import java.util.Map;

@Data
public class McpRequest {
    private String jsonrpc;
    private String id;
    private String method;
    private Map<String, Object> params;
}
