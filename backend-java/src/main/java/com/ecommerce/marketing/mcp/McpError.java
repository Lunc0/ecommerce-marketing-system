package com.ecommerce.marketing.mcp;

import lombok.AllArgsConstructor;
import lombok.Data;

@Data
@AllArgsConstructor
public class McpError {
    private int code;
    private String message;
    private Object data;
}
