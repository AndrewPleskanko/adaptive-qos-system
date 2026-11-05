package org.example.gatewayservice.service;

import com.thesis.proto.Priority;
import jakarta.annotation.PostConstruct;
import jakarta.annotation.PreDestroy;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Queue;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicLong;

@Slf4j
@Service
@RequiredArgsConstructor
public class SystemMetricsService {

    private static final String METRIC_CPU_KEY = "metrics:cpu";
    private static final String METRIC_MEMORY_KEY = "metrics:memory";
    private static final String METRIC_HIKARICP_KEY = "metrics:hikaricp_active";
    private static final double DEFAULT_CPU_USAGE = 25.0;
    private static final double DEFAULT_MEMORY_USAGE = 35.0;
    private static final double DEFAULT_HIKARICP_UTIL = 0.15;

    private final RedisTemplate<String, String> redisTemplate;

    // Real lag derivative calculation
    private final AtomicLong lastLag = new AtomicLong(0);
    private final AtomicLong lastLagTimestamp = new AtomicLong(System.currentTimeMillis());

    // Cached telemetry snapshot (refreshed at max every 100ms to preserve sub-microsecond decision budget)
    private volatile double cachedCpu = DEFAULT_CPU_USAGE;
    private volatile double cachedMemory = DEFAULT_MEMORY_USAGE;
    private volatile double cachedDbPool = DEFAULT_HIKARICP_UTIL;
    private volatile long cachedLag = 0;
    private volatile double cachedLagGrowth = 0.0;
    private volatile long lastRefreshTimestamp = 0;
    private static final long REFRESH_INTERVAL_MS = 100;

    // Rolling window of recent decision latencies (microseconds) for authentic P99
    private final Queue<Long> recentDecisionLatenciesUs = new ConcurrentLinkedQueue<>();
    private static final int MAX_LATENCY_SAMPLES = 500;

    // Background poller for zero-blocking sub-microsecond in-memory reads
    private ScheduledExecutorService telemetryScheduler;

    @PostConstruct
    public void startPoller() {
        telemetryScheduler = Executors.newSingleThreadScheduledExecutor(r -> {
            Thread t = new Thread(r, "telemetry-bg-poller");
            t.setDaemon(true);
            return t;
        });
        telemetryScheduler.scheduleAtFixedRate(() -> {
            try {
                refreshFromRedis(System.currentTimeMillis());
            } catch (Throwable t) {
                log.debug("Telemetry background poller update: {}", t.getMessage());
            }
        }, 0, 200, TimeUnit.MILLISECONDS);
    }

    @PreDestroy
    public void stopPoller() {
        if (telemetryScheduler != null) {
            telemetryScheduler.shutdownNow();
        }
    }

    public void recordDecisionLatency(long latencyUs) {
        recentDecisionLatenciesUs.offer(latencyUs);
        while (recentDecisionLatenciesUs.size() > MAX_LATENCY_SAMPLES) {
            recentDecisionLatenciesUs.poll();
        }
    }

    private void refreshFromRedis(long now) {
        try {
            String cpuVal = redisTemplate.opsForValue().get(METRIC_CPU_KEY);
            cachedCpu = cpuVal != null ? Double.parseDouble(cpuVal) : DEFAULT_CPU_USAGE;

            String memVal = redisTemplate.opsForValue().get(METRIC_MEMORY_KEY);
            cachedMemory = memVal != null ? Double.parseDouble(memVal) : DEFAULT_MEMORY_USAGE;

            String poolVal = redisTemplate.opsForValue().get(METRIC_HIKARICP_KEY);
            cachedDbPool = poolVal != null ? Double.parseDouble(poolVal) : DEFAULT_HIKARICP_UTIL;

            long totalLag = 0;
            for (Priority priority : Priority.values()) {
                if (priority == Priority.UNRECOGNIZED) continue;
                String val = redisTemplate.opsForValue().get("processed:" + priority.name());
                if (val != null) {
                    totalLag += Long.parseLong(val);
                }
            }
            cachedLag = totalLag;

            long prevLag = lastLag.getAndSet(totalLag);
            long prevTime = lastLagTimestamp.getAndSet(now);
            long deltaMs = Math.max(now - prevTime, 1);
            double ratePerSec = ((double) (totalLag - prevLag) / deltaMs) * 1000.0;
            cachedLagGrowth = Math.round(ratePerSec * 10.0) / 10.0;
        } catch (Exception e) {
            log.debug("Telemetry refresh error: {}", e.getMessage());
        }
    }

    public long getConsumerLag() {
        return cachedLag;
    }

    public double getCpuUsage() {
        return cachedCpu;
    }

    public double getMemoryUsage() {
        return cachedMemory;
    }

    public double getLagGrowthRate() {
        return cachedLagGrowth;
    }

    public double getDbPoolActive() {
        return cachedDbPool;
    }

    public double getRecentP99Latency() {
        if (recentDecisionLatenciesUs.isEmpty()) {
            return 2.5;
        }
        List<Long> samples = new ArrayList<>(recentDecisionLatenciesUs);
        Collections.sort(samples);
        int p99Idx = (int) (samples.size() * 0.99);
        long p99Us = samples.get(Math.min(p99Idx, samples.size() - 1));
        return Math.round((p99Us / 1000.0) * 100.0) / 100.0;
    }
}
