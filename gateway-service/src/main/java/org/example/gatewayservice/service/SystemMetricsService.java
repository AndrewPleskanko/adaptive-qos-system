package org.example.gatewayservice.service;

import com.thesis.proto.Priority;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;

@Slf4j
@Service
@RequiredArgsConstructor
public class SystemMetricsService {

    private static final String METRIC_CPU_KEY = "metrics:cpu";
    private static final String METRIC_MEMORY_KEY = "metrics:memory";
    private static final double DEFAULT_CPU_USAGE = 30.0;
    private static final double DEFAULT_MEMORY_USAGE = 40.0;

    private final RedisTemplate<String, String> redisTemplate;

    public long getConsumerLag() {
        try {
            long total = 0;
            for (Priority priority : Priority.values()) {
                if (priority == com.thesis.proto.Priority.UNRECOGNIZED) continue;
                String val = redisTemplate.opsForValue().get("processed:" + priority.name());
                if (val != null) {
                    total += Long.parseLong(val);
                }
            }
            return total;
        } catch (Exception e) {
            log.warn("Could not read consumer lag from Redis: {}", e.getMessage());
            return 0L;
        }
    }

    public double getCpuUsage() {
        try {
            String val = redisTemplate.opsForValue().get(METRIC_CPU_KEY);
            return val != null ? Double.parseDouble(val) : DEFAULT_CPU_USAGE;
        } catch (Exception e) {
            return DEFAULT_CPU_USAGE;
        }
    }

    public double getMemoryUsage() {
        try {
            String val = redisTemplate.opsForValue().get(METRIC_MEMORY_KEY);
            return val != null ? Double.parseDouble(val) : DEFAULT_MEMORY_USAGE;
        } catch (Exception e) {
            return DEFAULT_MEMORY_USAGE;
        }
    }

}
