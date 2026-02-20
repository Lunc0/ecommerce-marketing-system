package com.ecommerce.marketing.producer;

import com.ecommerce.marketing.dto.HighIntentEvent;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.kafka.support.SendResult;
import org.springframework.stereotype.Component;

import java.util.Map;
import java.util.concurrent.CompletableFuture;

/**
 * 高意图事件生产者
 * 向 'intent-high' topic 发送高价值信号
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class HighIntentProducer {

    private final KafkaTemplate<String, Object> kafkaTemplate;

    /**
     * 发送高意图事件
     * 注意：必须使用 userId 作为 Kafka 消息的 Key 以保证同一用户的顺序性
     *
     * @param userId 用户ID（作为 Key）
     * @param event  高意图事件
     */
    public void sendHighIntent(String userId, HighIntentEvent event) {
        String topic = "intent-high";
        log.info("Sending high intent event to topic: {}, Key (userId): {}, Event: {}",
                topic, userId, event);

        CompletableFuture<SendResult<String, Object>> future =
                kafkaTemplate.send(topic, userId, event);

        future.whenComplete((result, ex) -> {
            if (ex == null) {
                log.info("Successfully sent high intent event - Key: {}, Topic: {}, Partition: {}, Offset: {}",
                        userId,
                        result.getRecordMetadata().topic(),
                        result.getRecordMetadata().partition(),
                        result.getRecordMetadata().offset());
            } else {
                log.error("Failed to send high intent event - Key: {}, Topic: {}, Error: {}",
                        userId, topic, ex.getMessage(), ex);
            }
        });
    }

    /**
     * 便捷方法：构建并发送高意图事件
     *
     * @param userId      用户ID
     * @param reason      触发原因
     * @param context     上下文信息
     */
    public void sendHighInterestDetected(String userId, String reason, Map<String, Object> context) {
        HighIntentEvent event = HighIntentEvent.builder()
                .eventType("high_interest_detected")
                .userId(userId)
                .reason(reason)
                .context(context)
                .build();

        sendHighIntent(userId, event);
    }
}
