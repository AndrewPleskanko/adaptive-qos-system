package org.example.gatewayservice.controller;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.example.gatewayservice.dto.TransactionRequest;
import org.example.gatewayservice.dto.TransactionResponse;
import org.example.gatewayservice.service.TransactionGatewayService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.*;
import java.util.concurrent.*;
import java.util.stream.IntStream;

@Slf4j
@RestController
@RequestMapping("/api/v1/qos")
@CrossOrigin(origins = "*")
@RequiredArgsConstructor
public class QosController {

    private final TransactionGatewayService gatewayService;

    private final ExecutorService burstExecutor = Executors.newFixedThreadPool(
            Math.max(4, Runtime.getRuntime().availableProcessors()),
            r -> {
                Thread t = new Thread(r);
                t.setName("qos-burst-worker-" + t.getId());
                t.setDaemon(true);
                t.setContextClassLoader(QosController.class.getClassLoader());
                return t;
            }
    );

    @GetMapping("/mode")
    public ResponseEntity<Map<String, String>> getMode() {
        return ResponseEntity.ok(Map.of("mode", gatewayService.getQosMode()));
    }

    @PostMapping("/mode")
    public ResponseEntity<Map<String, String>> setMode(@RequestBody Map<String, String> body) {
        String newMode = body.get("mode");
        if (newMode == null || newMode.isBlank()) {
            return ResponseEntity.badRequest().body(Map.of("error", "Mode parameter is required"));
        }
        gatewayService.setQosMode(newMode.toLowerCase());
        return ResponseEntity.ok(Map.of("mode", gatewayService.getQosMode(), "status", "UPDATED"));
    }

    @PostMapping("/test-burst")
    public ResponseEntity<Map<String, Object>> runTestBurst(@RequestBody Map<String, Object> params) {
        int count = params.containsKey("count") ? Integer.parseInt(params.get("count").toString()) : 50;
        String typeOverride = params.containsKey("type") ? params.get("type").toString() : "MIXED";

        log.info("Starting High-Load benchmark burst: count={}, type={}, mode={}", 
                count, typeOverride, gatewayService.getQosMode());

        String[] types = {"PAYMENT", "REFUND", "BALANCE_UPDATE", "HEALTH_CHECK", "ADMIN_ACTION"};
        long burstStartNano = System.nanoTime();

        record TxBurstItem(String type, TransactionResponse response) {}

        // Process transactions using custom executor with Spring Boot ClassLoader preserved
        List<CompletableFuture<TxBurstItem>> futures = IntStream.range(0, count)
                .mapToObj(i -> CompletableFuture.supplyAsync(() -> {
                    String selectedType = typeOverride.equalsIgnoreCase("MIXED")
                            ? types[ThreadLocalRandom.current().nextInt(types.length)]
                            : typeOverride.toUpperCase();

                    double amount = Math.round(ThreadLocalRandom.current().nextDouble(5.0, 15000.0) * 100.0) / 100.0;
                    // Realistic transactional traffic retry distribution: ~94% 0 retries, ~5% 1 retry, ~1% >=2 retries
                    int retryRoll = ThreadLocalRandom.current().nextInt(100);
                    int retryCount = retryRoll < 94 ? 0 : (retryRoll < 99 ? 1 : ThreadLocalRandom.current().nextInt(2, 4));

                    TransactionRequest req = new TransactionRequest(
                            "user_" + ThreadLocalRandom.current().nextInt(1000, 9999),
                            amount,
                            "USD",
                            "US-EAST",
                            selectedType,
                            Map.of("source", "highload_benchmark_engine"),
                            retryCount
                    );

                    return new TxBurstItem(selectedType, gatewayService.processTransaction(req));
                }, burstExecutor))
                .toList();

        List<TxBurstItem> executed = futures.stream().map(CompletableFuture::join).toList();
        List<TransactionResponse> results = executed.stream().map(TxBurstItem::response).toList();

        long totalDurationNano = System.nanoTime() - burstStartNano;
        double durationSeconds = Math.max(totalDurationNano / 1_000_000_000.0, 0.001);
        double throughputRps = Math.round((count / durationSeconds) * 100.0) / 100.0;

        // Collect priority distribution and latency metrics
        Map<String, Long> priorityDistribution = new HashMap<>();
        List<Long> latencies = new ArrayList<>(count);
        double totalLatencyUs = 0;

        // Initialize structured type breakdown matrix
        Map<String, Map<String, Long>> typeBreakdown = new LinkedHashMap<>();
        for (String t : types) {
            Map<String, Long> m = new LinkedHashMap<>();
            m.put("CRITICAL", 0L);
            m.put("HIGH", 0L);
            m.put("STANDARD", 0L);
            m.put("LOW", 0L);
            m.put("TOTAL", 0L);
            typeBreakdown.put(t, m);
        }

        for (TxBurstItem item : executed) {
            TransactionResponse r = item.response();
            String prio = r.priority();
            priorityDistribution.put(prio, priorityDistribution.getOrDefault(prio, 0L) + 1);
            long latencyUs = r.decisionLatencyUs();
            latencies.add(latencyUs);
            totalLatencyUs += latencyUs;

            String t = item.type();
            Map<String, Long> prioMap = typeBreakdown.computeIfAbsent(t, k -> {
                Map<String, Long> m = new LinkedHashMap<>();
                m.put("CRITICAL", 0L);
                m.put("HIGH", 0L);
                m.put("STANDARD", 0L);
                m.put("LOW", 0L);
                m.put("TOTAL", 0L);
                return m;
            });
            prioMap.put(prio, prioMap.getOrDefault(prio, 0L) + 1L);
            prioMap.put("TOTAL", prioMap.getOrDefault("TOTAL", 0L) + 1L);
        }

        Collections.sort(latencies);
        double avgDecisionLatencyUs = results.isEmpty() ? 0 : Math.round((totalLatencyUs / results.size()) * 100.0) / 100.0;
        long p50LatencyUs = latencies.isEmpty() ? 0 : latencies.get((int) (latencies.size() * 0.50));
        long p95LatencyUs = latencies.isEmpty() ? 0 : latencies.get(Math.min((int) (latencies.size() * 0.95), latencies.size() - 1));
        long p99LatencyUs = latencies.isEmpty() ? 0 : latencies.get(Math.min((int) (latencies.size() * 0.99), latencies.size() - 1));

        // Sample up to first 50 transactions to prevent UI crash on 100k
        List<TransactionResponse> sampleResults = results.stream().limit(50).toList();

        Map<String, Object> response = new HashMap<>();
        response.put("modeUsed", gatewayService.getQosMode());
        response.put("totalTransactions", count);
        response.put("durationSeconds", Math.round(durationSeconds * 1000.0) / 1000.0);
        response.put("throughputRps", throughputRps);
        response.put("avgDecisionLatencyUs", avgDecisionLatencyUs);
        response.put("p50LatencyUs", p50LatencyUs);
        response.put("p95LatencyUs", p95LatencyUs);
        response.put("p99LatencyUs", p99LatencyUs);
        response.put("priorityDistribution", priorityDistribution);
        response.put("typeBreakdown", typeBreakdown);
        response.put("sampleResults", sampleResults);

        log.info("Finished High-Load burst: count={}, duration={}s, rps={}, avgLatency={}us, p99={}us",
                count, durationSeconds, throughputRps, avgDecisionLatencyUs, p99LatencyUs);

        return ResponseEntity.ok(response);
    }
}
