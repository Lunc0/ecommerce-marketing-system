package com.ecommerce.marketing.service;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.redis.core.SessionCallback;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.ValueOperations;

import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.Arrays;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class TrafficFilterServiceTest {

    @Mock
    private StringRedisTemplate stringRedisTemplate;

    @Mock
    private ValueOperations<String, String> valueOperations;

    private TrafficFilterService trafficFilterService;

    @BeforeEach
    void setUp() {
        lenient().when(stringRedisTemplate.opsForValue()).thenReturn(valueOperations);
        Clock clock = Clock.fixed(Instant.parse("2026-02-20T00:00:00Z"), ZoneOffset.UTC);
        trafficFilterService = new TrafficFilterService(stringRedisTemplate, clock);
    }

    @Test
    void isHighInterestReturnsTrueOnlyOnceDueToCooldown() {
        String userId = "test_user_cooldown";

        // 模拟第 10 次和第 11 次点击都超过阈值
        when(stringRedisTemplate.executePipelined(any(SessionCallback.class)))
                .thenReturn(Arrays.asList(null, null, 10L, null),
                        Arrays.asList(null, null, 11L, null));

        // 模拟第一次设置冷却锁成功，第二次失败
        when(valueOperations.setIfAbsent(eq("user:cooldown:" + userId), eq("1"), any(Duration.class)))
                .thenReturn(true) // 第 10 次点击
                .thenReturn(false); // 第 11 次点击

        // 第 10 次点击：触发
        boolean result10 = trafficFilterService.isHighInterest(userId);
        assertThat(result10).isTrue();

        // 第 11 次点击：防抖拦截，不触发
        boolean result11 = trafficFilterService.isHighInterest(userId);
        assertThat(result11).isFalse();

        verify(valueOperations, times(2)).setIfAbsent(eq("user:cooldown:" + userId), eq("1"), any(Duration.class));
    }

    @Test
    void isHighInterestReturnsTrueWhenTenClicksInWindow() {
        String userId = "test_user_010";

        when(stringRedisTemplate.executePipelined(any(SessionCallback.class)))
                .thenReturn(Arrays.asList(null, null, 1L, null),
                        Arrays.asList(null, null, 2L, null),
                        Arrays.asList(null, null, 3L, null),
                        Arrays.asList(null, null, 4L, null),
                        Arrays.asList(null, null, 5L, null),
                        Arrays.asList(null, null, 6L, null),
                        Arrays.asList(null, null, 7L, null),
                        Arrays.asList(null, null, 8L, null),
                        Arrays.asList(null, null, 9L, null),
                        Arrays.asList(null, null, 10L, null));

        // 只有达到阈值时才会调用 setIfAbsent
        when(valueOperations.setIfAbsent(anyString(), anyString(), any(Duration.class)))
                .thenReturn(true);

        boolean result = false;
        for (int i = 0; i < 10; i++) {
            result = trafficFilterService.isHighInterest(userId);
        }

        assertThat(result).isTrue();
        verify(stringRedisTemplate, times(10)).executePipelined(any(SessionCallback.class));
        verify(valueOperations, times(1)).setIfAbsent(anyString(), anyString(), any(Duration.class));
    }

    @Test
    void isHighInterestReturnsFalseWhenSingleClick() {
        String userId = "test_user_001";

        List<Object> pipelineResult = Arrays.asList(null, null, 1L, null);
        when(stringRedisTemplate.executePipelined(any(SessionCallback.class))).thenReturn(pipelineResult);

        boolean result = trafficFilterService.isHighInterest(userId);

        assertThat(result).isFalse();
        verify(stringRedisTemplate, times(1)).executePipelined(any(SessionCallback.class));
    }
}
