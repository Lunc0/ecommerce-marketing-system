package com.ecommerce.marketing.service;

import lombok.RequiredArgsConstructor;
import org.springframework.data.redis.core.RedisOperations;
import org.springframework.data.redis.core.SessionCallback;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.ZSetOperations;
import org.springframework.stereotype.Service;

import java.time.Clock;
import java.time.Duration;
import java.util.List;
import java.util.UUID;

@Service
@RequiredArgsConstructor
public class TrafficFilterService {

    private static final long WINDOW_MILLIS = Duration.ofMinutes(5).toMillis();
    private static final long HIGH_INTEREST_THRESHOLD = 10;
    private static final Duration WINDOW_TTL = Duration.ofMinutes(5);
    private static final Duration COOLDOWN_TTL = Duration.ofHours(1);

    private final StringRedisTemplate stringRedisTemplate;
    private final Clock clock;

    public boolean isHighInterest(String userId) {
        String key = "user:window:" + userId + ":click";
        long now = clock.millis();
        long cutoff = now - WINDOW_MILLIS;
        String member = now + "_" + UUID.randomUUID();

        List<Object> results = stringRedisTemplate.executePipelined(
                new SessionCallback<Object>() {
                    @Override
                    @SuppressWarnings("unchecked")
                    public <K, V> Object execute(RedisOperations<K, V> operations) {
                        RedisOperations<String, String> stringOps = (RedisOperations<String, String>) operations;
                        ZSetOperations<String, String> zSetOperations = stringOps.opsForZSet();
                        zSetOperations.removeRangeByScore(key, 0, cutoff);
                        zSetOperations.add(key, member, now);
                        zSetOperations.zCard(key);
                        stringOps.expire(key, WINDOW_TTL);
                        return null;
                    }
                });

        if (results == null || results.size() < 3) {
            return false;
        }

        Object countResult = results.get(2);
        Long count = countResult instanceof Long ? (Long) countResult : null;

        if (count != null && count >= HIGH_INTEREST_THRESHOLD) {
            // 判定通过，检查并设置冷却锁（防抖）
            String cooldownKey = "user:cooldown:" + userId;
            Boolean isFirstTrigger = stringRedisTemplate.opsForValue()
                    .setIfAbsent(cooldownKey, "1", COOLDOWN_TTL);
            return Boolean.TRUE.equals(isFirstTrigger);
        }

        return false;
    }
}
