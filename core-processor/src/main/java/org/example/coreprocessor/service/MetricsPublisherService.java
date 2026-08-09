package org.example.coreprocessor.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import java.lang.management.ManagementFactory;
import java.lang.management.MemoryMXBean;
import java.lang.management.OperatingSystemMXBean;

/**
 * Збирає метрики JVM (CPU, Memory) і публікує їх у Redis кожні 5 секунд.
 * Gateway-service читає ці значення для побудови SystemState,
 * який передається в inference-engine для адаптивного налаштування порогів.
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class MetricsPublisherService {

    private static final String METRIC_CPU_KEY = "metrics:cpu";
    private static final String METRIC_MEMORY_KEY = "metrics:memory";

    private final RedisTemplate<String, String> redisTemplate;

    @Scheduled(fixedDelay = 5000)
    public void publishMetrics() {
        try {
            double cpu = getSystemCpuLoad();
            double memory = getHeapMemoryUsage();

            redisTemplate.opsForValue().set(METRIC_CPU_KEY, String.valueOf(cpu));
            redisTemplate.opsForValue().set(METRIC_MEMORY_KEY, String.valueOf(memory));

            log.debug("Published metrics: cpu={}%, memory={}%", String.format("%.1f", cpu), String.format("%.1f", memory));
        } catch (Exception e) {
            log.warn("Failed to publish metrics to Redis: {}", e.getMessage());
        }
    }

    private double getSystemCpuLoad() {
        OperatingSystemMXBean osBean = ManagementFactory.getOperatingSystemMXBean();
        if (osBean instanceof com.sun.management.OperatingSystemMXBean sunBean) {
            double load = sunBean.getCpuLoad() * 100.0;
            return load < 0 ? 30.0 : load;
        }
        return 30.0;
    }

    private double getHeapMemoryUsage() {
        MemoryMXBean memBean = ManagementFactory.getMemoryMXBean();
        long used = memBean.getHeapMemoryUsage().getUsed();
        long max = memBean.getHeapMemoryUsage().getMax();
        if (max <= 0) return 40.0;
        return ((double) used / max) * 100.0;
    }
}
