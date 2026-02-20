package com.ecommerce.marketing.consumer;

import com.ecommerce.marketing.dto.UserBehaviorEvent;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.junit.jupiter.MockitoExtension;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * UserBehaviorConsumer 单元测试
 * 测试消费者方法的基本功能
 */
@ExtendWith(MockitoExtension.class)
class UserBehaviorConsumerTest {

    @InjectMocks
    private UserBehaviorConsumer userBehaviorConsumer;

    @Test
    void testConsumeUserBehavior() {
        // Given
        String userId = "test_user_001";
        UserBehaviorEvent event = UserBehaviorEvent.builder()
                .userId(userId)
                .action("view_item")
                .skuId("shoe_1024")
                .price(299.0)
                .timestamp(1234567890L)
                .build();

        String key = userId;
        String topic = "behavior-normal";
        int partition = 0;
        long offset = 100L;

        // When - 调用消费者方法（日志会输出）
        userBehaviorConsumer.consumeUserBehavior(event, key, topic, partition, offset);

        // Then - 验证事件对象
        assertThat(event.getUserId()).isEqualTo(userId);
        assertThat(event.getAction()).isEqualTo("view_item");
        assertThat(event.getSkuId()).isEqualTo("shoe_1024");
        assertThat(event.getPrice()).isEqualTo(299.0);
    }

    @Test
    void testConsumeUserBehavior_DifferentAction() {
        // Given
        UserBehaviorEvent event = UserBehaviorEvent.builder()
                .userId("user_002")
                .action("add_to_cart")
                .skuId("product_123")
                .price(599.0)
                .timestamp(1234567891L)
                .build();

        // When - 调用消费者方法
        userBehaviorConsumer.consumeUserBehavior(event, "user_002", "behavior-normal", 1, 101L);

        // Then - 验证事件对象
        assertThat(event.getAction()).isEqualTo("add_to_cart");
    }
}
