package com.ecommerce.marketing.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.Map;

/**
 * 高意图事件 DTO
 * 用于 Kafka topic 'intent-high' 消息传递
 * 当用户行为达到特定阈值（如5分钟内点击10次）时触发
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class HighIntentEvent {

    /**
     * 事件类型
     */
    private String eventType;

    /**
     * 用户ID
     */
    private String userId;

    /**
     * 触发原因
     */
    private String reason;

    /**
     * 上下文信息（目标分类、点击次数等）
     */
    private Map<String, Object> context;
}
