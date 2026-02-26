package com.ecommerce.marketing;

import com.ecommerce.marketing.consumer.UserBehaviorConsumer;
import com.ecommerce.marketing.dto.UserBehaviorEvent;
import com.ecommerce.marketing.producer.HighIntentProducer;
import com.ecommerce.marketing.service.TrafficFilterService;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.kafka.core.KafkaTemplate;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class EndToEndFlowTest {

        @Test
        void testEndToEndFlow_Simulate11Clicks() {
                String userId = "test_user_e2e";

                KafkaTemplate<String, Object> kafkaTemplate = mock(KafkaTemplate.class);
                org.springframework.kafka.support.SendResult<String, Object> sendResult = mock(
                                org.springframework.kafka.support.SendResult.class);
                org.apache.kafka.clients.producer.RecordMetadata metadata = new org.apache.kafka.clients.producer.RecordMetadata(
                                new org.apache.kafka.common.TopicPartition("intent-high", 0), 0L, 0L, 0L, 0L, 0, 0);
                when(sendResult.getRecordMetadata()).thenReturn(metadata);

                when(kafkaTemplate.send(anyString(), anyString(), any()))
                                .thenReturn(java.util.concurrent.CompletableFuture.completedFuture(sendResult));

                HighIntentProducer highIntentProducer = new HighIntentProducer(kafkaTemplate);
                TrafficFilterService trafficFilterService = mock(TrafficFilterService.class);
                when(trafficFilterService.isHighInterest(userId))
                                .thenReturn(false, false, false, false, false, false, false, false, false, false)
                                .thenReturn(true);

                UserBehaviorConsumer userBehaviorConsumer = new UserBehaviorConsumer(trafficFilterService,
                                highIntentProducer);

                for (int i = 0; i < 11; i++) {
                        UserBehaviorEvent event = new UserBehaviorEvent();
                        event.setUserId(userId);
                        event.setAction("view_item");
                        event.setSkuId("sku_" + i);
                        event.setPrice(100.0);
                        event.setTimestamp(System.currentTimeMillis());

                        userBehaviorConsumer.consumeUserBehavior(event, userId, "behavior-normal", 0, i);
                }

                verify(trafficFilterService, times(11)).isHighInterest(userId);

                verify(kafkaTemplate, times(1)).send(eq("intent-high"), eq(userId), any());
        }
}
