package org.example.gatewayservice.controller;

import lombok.RequiredArgsConstructor;
import org.example.gatewayservice.dto.TransactionRequest;
import org.example.gatewayservice.dto.TransactionResponse;
import org.example.gatewayservice.service.TransactionGatewayService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/v1/transactions")
@RequiredArgsConstructor
public class TransactionController {

    private final TransactionGatewayService gatewayService;

    @PostMapping
    public ResponseEntity<TransactionResponse> submitTransaction(@RequestBody TransactionRequest request) {
        TransactionResponse response = gatewayService.processTransaction(request);
        return ResponseEntity.accepted().body(response);
    }

    @PostMapping("/batch")
    public ResponseEntity<List<TransactionResponse>> submitBatch(@RequestBody List<TransactionRequest> requests) {
        List<TransactionResponse> responses = requests.stream()
                .map(gatewayService::processTransaction)
                .toList();
        return ResponseEntity.accepted().body(responses);
    }

    @GetMapping("/health")
    public ResponseEntity<String> health() {
        return ResponseEntity.ok("OK");
    }
}
