package com.ecommerce.marketing.config;

import org.apache.kafka.clients.admin.NewTopic;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.config.TopicBuilder;

/**
 * Kafka Topic 配置类
 * 显式声明所需的 Topic 及其分区和副本配置
 */
@Configuration
public class KafkaConfig {

    /**
     * 普通行为流 Topic
     * 3个分区，1个副本
     * 用于接收所有用户行为数据
     */
    @Bean
    public NewTopic behaviorNormalTopic() {
        return TopicBuilder.name("behavior-normal")
                .partitions(3)
                .replicas(1)
                .build();
    }

    /**
     * 高意图事件 Topic
     * 1个分区，1个副本
     * 用于接收 Java 实时计算产生的高价值信号
     * 单分区保证同一用户的事件顺序性
     */
    @Bean
    public NewTopic intentHighTopic() {
        return TopicBuilder.name("intent-high")
                .partitions(1)
                .replicas(1)
                .build();
    }
}
