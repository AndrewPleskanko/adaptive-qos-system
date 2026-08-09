package org.example.gatewayservice.dto;

import java.util.Map;

public record TransactionRequest(
        String userId,
        double amount,
        String currency,
        String region,
        String type,
        Map<String, String> metadata
) {}
