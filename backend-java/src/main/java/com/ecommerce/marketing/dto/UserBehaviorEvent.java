package com.ecommerce.marketing.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.Instant;

/**
 * 用户行为事件 DTO
 * 用于 Kafka topic 'behavior-normal' 消息传递
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class UserBehaviorEvent {

    /**
     * 用户ID - 将作为 Kafka Key 使用
     */
    private String userId;

    /**
     * 行为类型: view_item, add_to_cart, purchase, search
     */
    private String action;

    /**
     * 商品SKU
     */
    private String skuId;

    /**
     * 商品价格
     */
    private Double price;

    /**
     * 时间戳
     */
    private Long timestamp;
}
