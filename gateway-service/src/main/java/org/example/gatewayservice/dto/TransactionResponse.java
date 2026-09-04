package org.example.gatewayservice.dto;

public record TransactionResponse(
        String id,
        String priority,
        double score,
        String reason,
        String status,
        long decisionLatencyUs
) {}
