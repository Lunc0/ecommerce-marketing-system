package com.ecommerce.marketing.consumer;

import com.ecommerce.marketing.dto.UserBehaviorEvent;
import com.ecommerce.marketing.producer.HighIntentProducer;
import com.ecommerce.marketing.service.TrafficFilterService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.kafka.support.KafkaHeaders;
import org.springframework.messaging.handler.annotation.Header;
import org.springframework.messaging.handler.annotation.Payload;
import org.springframework.stereotype.Component;

import java.util.Map;

/**
 * 用户行为消费者
 * 监听 'behavior-normal' topic，接收并处理用户行为事件
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class UserBehaviorConsumer {

        private final TrafficFilterService trafficFilterService;
        private final HighIntentProducer highIntentProducer;

        /**
         * 消费用户行为事件
         *
         * @param event     用户行为事件
         * @param key       Kafka 消息 Key (userId)
         * @param topic     Topic 名称
         * @param partition 分区号
         * @param offset    消息偏移量
         */
        @KafkaListener(topics = "behavior-normal", groupId = "marketing-consumer-group", containerFactory = "kafkaListenerContainerFactory")
        public void consumeUserBehavior(
                        @Payload UserBehaviorEvent event,
                        @Header(KafkaHeaders.RECEIVED_KEY) String key,
                        @Header(KafkaHeaders.RECEIVED_TOPIC) String topic,
                        @Header(KafkaHeaders.RECEIVED_PARTITION) int partition,
                        @Header(KafkaHeaders.OFFSET) long offset) {
                log.info("Received user behavior event - Key: {}, Topic: {}, Partition: {}, Offset: {}, Event: {}",
                                key, topic, partition, offset, event);

                boolean isHighInterest = trafficFilterService.isHighInterest(event.getUserId());

                if (isHighInterest) {
                        log.info("High interest detected for user: {}", event.getUserId());
                        highIntentProducer.sendHighInterestDetected(
                                        event.getUserId(),
                                        "clicked_10_times_in_5min",
                                        Map.of(
                                                        "last_action",
                                                        event.getAction() != null ? event.getAction() : "unknown",
                                                        "sku_id",
                                                        event.getSkuId() != null ? event.getSkuId() : "unknown",
                                                        "price", event.getPrice() != null ? event.getPrice() : 0.0));
                }
        }
}
