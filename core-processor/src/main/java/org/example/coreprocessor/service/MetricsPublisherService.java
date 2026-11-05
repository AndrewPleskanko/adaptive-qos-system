package org.example.coreprocessor.service;

import com.zaxxer.hikari.HikariDataSource;
import com.zaxxer.hikari.HikariPoolMXBean;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

import javax.sql.DataSource;
import java.lang.management.ManagementFactory;
import java.lang.management.MemoryMXBean;
import java.lang.management.OperatingSystemMXBean;

@Slf4j
@Service
@RequiredArgsConstructor
public class MetricsPublisherService {

    private static final String METRIC_CPU_KEY = "metrics:cpu";
    private static final String METRIC_MEMORY_KEY = "metrics:memory";
    private static final String METRIC_HIKARICP_KEY = "metrics:hikaricp_active";

    private final RedisTemplate<String, String> redisTemplate;
    private final DataSource dataSource;

    @Scheduled(fixedDelay = 2000)
    public void publishMetrics() {
        try {
            double cpu = getSystemCpuLoad();
            double memory = getHeapMemoryUsage();
            double dbPoolActive = getHikariPoolUtilization();

            redisTemplate.opsForValue().set(METRIC_CPU_KEY, String.valueOf(cpu));
            redisTemplate.opsForValue().set(METRIC_MEMORY_KEY, String.valueOf(memory));
            redisTemplate.opsForValue().set(METRIC_HIKARICP_KEY, String.valueOf(dbPoolActive));

            log.debug("Published metrics: cpu={}%, mem={}%, db_pool={}%",
                    String.format("%.1f", cpu), String.format("%.1f", memory), String.format("%.2f", dbPoolActive));
        } catch (Exception e) {
            log.warn("Failed to publish metrics to Redis: {}", e.getMessage());
        }
    }

    private double getHikariPoolUtilization() {
        try {
            if (dataSource instanceof HikariDataSource hikari) {
                HikariPoolMXBean poolBean = hikari.getHikariPoolMXBean();
                if (poolBean != null) {
                    int active = poolBean.getActiveConnections();
                    int max = hikari.getMaximumPoolSize();
                    return max > 0 ? (double) active / max : 0.10;
                }
            }
        } catch (Exception ignored) {}
        return 0.10;
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
