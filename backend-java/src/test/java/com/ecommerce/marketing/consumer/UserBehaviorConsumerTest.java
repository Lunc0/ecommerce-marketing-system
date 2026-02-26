package com.ecommerce.marketing.consumer;

import com.ecommerce.marketing.dto.UserBehaviorEvent;
import com.ecommerce.marketing.producer.HighIntentProducer;
import com.ecommerce.marketing.service.TrafficFilterService;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class UserBehaviorConsumerTest {

    @Mock
    private TrafficFilterService trafficFilterService;

    @Mock
    private HighIntentProducer highIntentProducer;

    @InjectMocks
    private UserBehaviorConsumer userBehaviorConsumer;

    @Test
    void testConsumeUserBehavior() {
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

        when(trafficFilterService.isHighInterest(userId)).thenReturn(false);

        userBehaviorConsumer.consumeUserBehavior(event, key, topic, partition, offset);

        assertThat(event.getUserId()).isEqualTo(userId);
        assertThat(event.getAction()).isEqualTo("view_item");
        assertThat(event.getSkuId()).isEqualTo("shoe_1024");
        assertThat(event.getPrice()).isEqualTo(299.0);
    }

    @Test
    void testConsumeUserBehavior_DifferentAction() {
        UserBehaviorEvent event = UserBehaviorEvent.builder()
                .userId("user_002")
                .action("add_to_cart")
                .skuId("product_123")
                .price(599.0)
                .timestamp(1234567891L)
                .build();

        when(trafficFilterService.isHighInterest("user_002")).thenReturn(false);

        userBehaviorConsumer.consumeUserBehavior(event, "user_002", "behavior-normal", 1, 101L);

        assertThat(event.getAction()).isEqualTo("add_to_cart");
    }
}
