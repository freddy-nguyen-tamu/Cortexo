package com.cortexo.lab.storage.redis;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.util.Optional;

@Service
public class CacheService {

    private final StringRedisTemplate redis;
    private final boolean enabled;

    public CacheService(StringRedisTemplate redis,
                        @Value("${REDIS_ENABLED:false}") boolean enabled) {
        this.redis = redis;
        this.enabled = enabled;
    }

    public boolean enabled() {
        return enabled;
    }

    public Optional<String> get(String key) {
        if (!enabled) {
            return Optional.empty();
        }
        try {
            return Optional.ofNullable(redis.opsForValue().get(key));
        } catch (Exception e) {
            return Optional.empty();
        }
    }

    public void put(String key, String value, Duration ttl) {
        if (!enabled) {
            return;
        }
        try {
            redis.opsForValue().set(key, value, ttl);
        } catch (Exception ignored) {
        }
    }

    public void evict(String key) {
        if (!enabled) {
            return;
        }
        try {
            redis.delete(key);
        } catch (Exception ignored) {
        }
    }
}