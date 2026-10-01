package org.example.gatewayservice.controller;

import lombok.RequiredArgsConstructor;
import org.example.gatewayservice.dto.TransactionRequest;
import org.example.gatewayservice.dto.TransactionResponse;
import org.example.gatewayservice.service.TransactionGatewayService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.*;
import java.util.concurrent.ThreadLocalRandom;

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
        int count = params.containsKey("count") ? Integer.parseInt(params.get("count").toString()) : 20;
        String typeOverride = params.containsKey("type") ? params.get("type").toString() : "MIXED";

        String[] types = {"PAYMENT", "REFUND", "BALANCE_UPDATE", "HEALTH_CHECK", "ADMIN_ACTION"};
        List<TransactionResponse> results = new ArrayList<>();

        for (int i = 0; i < count; i++) {
            String selectedType = typeOverride.equalsIgnoreCase("MIXED")
                    ? types[ThreadLocalRandom.current().nextInt(types.length)]
                    : typeOverride.toUpperCase();

            double amount = Math.round(ThreadLocalRandom.current().nextDouble(5.0, 5000.0) * 100.0) / 100.0;
            int retryCount = ThreadLocalRandom.current().nextInt(0, 4);

            TransactionRequest req = new TransactionRequest(
                    "user_" + ThreadLocalRandom.current().nextInt(1000, 9999),
                    amount,
                    "USD",
                    "US-EAST",
                    selectedType,
                    Map.of("source", "angular_dashboard_test"),
                    retryCount
            );

            TransactionResponse resp = gatewayService.processTransaction(req);
            results.add(resp);
        }

        Map<String, Long> priorityDistribution = new HashMap<>();
        double totalLatencyUs = 0;

        for (TransactionResponse r : results) {
            priorityDistribution.put(r.priority(), priorityDistribution.getOrDefault(r.priority(), 0L) + 1);
            totalLatencyUs += r.decisionLatencyUs();
        }

        Map<String, Object> response = new HashMap<>();
        response.put("modeUsed", gatewayService.getQosMode());
        response.put("totalTransactions", results.size());
        response.put("avgDecisionLatencyUs", results.isEmpty() ? 0 : Math.round((totalLatencyUs / results.size()) * 100.0) / 100.0);
        response.put("priorityDistribution", priorityDistribution);
        response.put("sampleResults", results);

        return ResponseEntity.ok(response);
    }
}
