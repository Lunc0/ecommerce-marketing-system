package com.ecommerce.marketing.component;

import com.ecommerce.marketing.model.User;
import com.ecommerce.marketing.repository.UserRepository;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.CommandLineRunner;
import org.springframework.boot.autoconfigure.condition.ConditionalOnBean;
import org.springframework.context.annotation.Profile;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

import java.util.List;

@Slf4j
@Component
@RequiredArgsConstructor
@ConditionalOnBean(UserRepository.class)
@Profile("!test")
public class DataPreloader implements CommandLineRunner {

    private final UserRepository userRepository;
    private final StringRedisTemplate stringRedisTemplate;
    private final ObjectMapper objectMapper;

    @Override
    public void run(String... args) throws Exception {
        log.info("Starting user profile preheating...");
        List<User> users = userRepository.findAll();
        
        if (users.isEmpty()) {
            log.warn("No users found in MySQL to preheat.");
            return;
        }

        for (User user : users) {
            String key = "user:profile:" + user.getId();
            try {
                String json = objectMapper.writeValueAsString(user);
                stringRedisTemplate.opsForValue().set(key, json);
                log.debug("Preheated user profile for ID: {}", user.getId());
            } catch (Exception e) {
                log.error("Failed to preheat user profile for ID: {}", user.getId(), e);
            }
        }
        
        log.info("User profile preheating completed. Total users: {}", users.size());
    }
}
