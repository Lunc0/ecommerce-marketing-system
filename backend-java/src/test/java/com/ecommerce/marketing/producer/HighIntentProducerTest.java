package com.ecommerce.marketing.producer;

import com.ecommerce.marketing.dto.HighIntentEvent;
import org.apache.kafka.clients.producer.RecordMetadata;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.kafka.support.SendResult;

import java.util.Map;
import java.util.concurrent.CompletableFuture;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

/**
 * HighIntentProducer 单元测试
 * 使用 Mockito 模拟 KafkaTemplate，避免真实连接依赖
 */
@ExtendWith(MockitoExtension.class)
class HighIntentProducerTest {

    @Mock
    private KafkaTemplate<String, Object> kafkaTemplate;

    @Mock
    private SendResult<String, Object> sendResult;

    @Mock
    private RecordMetadata recordMetadata;

    private HighIntentProducer highIntentProducer;

    @BeforeEach
    void setUp() {
        // 使用 @RequiredArgsConstructor，只包含 final 字段 kafkaTemplate
        highIntentProducer = new HighIntentProducer(kafkaTemplate);
    }

    @Test
    void testSendHighIntent_Success() {
        // Given
        String userId = "test_user_001";
        HighIntentEvent event = HighIntentEvent.builder()
                .eventType("high_interest_detected")
                .userId(userId)
                .reason("test_reason")
                .build();

        CompletableFuture<SendResult<String, Object>> future = CompletableFuture.completedFuture(sendResult);

        when(kafkaTemplate.send(eq("intent-high"), eq(userId), eq(event)))
                .thenReturn(future);

        when(sendResult.getRecordMetadata()).thenReturn(recordMetadata);
        when(recordMetadata.topic()).thenReturn("intent-high");
        when(recordMetadata.partition()).thenReturn(0);
        when(recordMetadata.offset()).thenReturn(100L);

        // When
        highIntentProducer.sendHighIntent(userId, event);

        // Then
        verify(kafkaTemplate, times(1)).send(eq("intent-high"), eq(userId), eq(event));
    }

    @Test
    void testSendHighInterestDetected_ConvenienceMethod() {
        // Given
        String userId = "test_user_002";
        String reason = "clicked_10_times_in_5min";
        Map<String, Object> context = Map.of("target_category", "shoes", "recent_clicks", 12);

        CompletableFuture<SendResult<String, Object>> future = CompletableFuture.completedFuture(sendResult);

        when(kafkaTemplate.send(anyString(), eq(userId), any(HighIntentEvent.class)))
                .thenReturn(future);

        // When
        highIntentProducer.sendHighInterestDetected(userId, reason, context);

        // Then
        ArgumentCaptor<HighIntentEvent> eventCaptor = ArgumentCaptor.forClass(HighIntentEvent.class);
        verify(kafkaTemplate, times(1)).send(eq("intent-high"), eq(userId), eventCaptor.capture());

        HighIntentEvent capturedEvent = eventCaptor.getValue();
        assertThat(capturedEvent.getUserId()).isEqualTo(userId);
        assertThat(capturedEvent.getEventType()).isEqualTo("high_interest_detected");
        assertThat(capturedEvent.getReason()).isEqualTo(reason);
        assertThat(capturedEvent.getContext()).containsEntry("target_category", "shoes");
        assertThat(capturedEvent.getContext()).containsEntry("recent_clicks", 12);
    }
}
