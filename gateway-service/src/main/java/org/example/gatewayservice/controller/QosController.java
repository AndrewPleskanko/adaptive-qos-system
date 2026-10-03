package org.example.gatewayservice.controller;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.example.gatewayservice.dto.TransactionRequest;
import org.example.gatewayservice.dto.TransactionResponse;
import org.example.gatewayservice.service.TransactionGatewayService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.*;
import java.util.concurrent.ThreadLocalRandom;
import java.util.stream.IntStream;

@Slf4j
@RestController
@RequestMapping("/api/v1/qos")
@CrossOrigin(origins = "*")
@RequiredArgsConstructor
public class QosController {

    private final TransactionGatewayService gatewayService;

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

        // Process transactions using parallel stream for true high-load throughput
        List<TransactionResponse> results = IntStream.range(0, count)
                .parallel()
                .mapToObj(i -> {
                    String selectedType = typeOverride.equalsIgnoreCase("MIXED")
                            ? types[ThreadLocalRandom.current().nextInt(types.length)]
                            : typeOverride.toUpperCase();

                    double amount = Math.round(ThreadLocalRandom.current().nextDouble(5.0, 15000.0) * 100.0) / 100.0;
                    int retryCount = ThreadLocalRandom.current().nextInt(0, 4);

                    TransactionRequest req = new TransactionRequest(
                            "user_" + ThreadLocalRandom.current().nextInt(1000, 9999),
                            amount,
                            "USD",
                            "US-EAST",
                            selectedType,
                            Map.of("source", "highload_benchmark_engine"),
                            retryCount
                    );

                    return gatewayService.processTransaction(req);
                })
                .toList();

        long totalDurationNano = System.nanoTime() - burstStartNano;
        double durationSeconds = Math.max(totalDurationNano / 1_000_000_000.0, 0.001);
        double throughputRps = Math.round((count / durationSeconds) * 100.0) / 100.0;

        // Collect priority distribution and latency metrics
        Map<String, Long> priorityDistribution = new HashMap<>();
        List<Long> latencies = new ArrayList<>(count);
        double totalLatencyUs = 0;

        for (TransactionResponse r : results) {
            priorityDistribution.put(r.priority(), priorityDistribution.getOrDefault(r.priority(), 0L) + 1);
            long latencyUs = r.decisionLatencyUs();
            latencies.add(latencyUs);
            totalLatencyUs += latencyUs;
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
        response.put("sampleResults", sampleResults);

        log.info("Finished High-Load burst: count={}, duration={}s, rps={}, avgLatency={}us, p99={}us",
                count, durationSeconds, throughputRps, avgDecisionLatencyUs, p99LatencyUs);

        return ResponseEntity.ok(response);
    }
}
