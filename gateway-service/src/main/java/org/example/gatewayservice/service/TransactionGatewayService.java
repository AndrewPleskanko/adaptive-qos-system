package org.example.gatewayservice.service;

import com.thesis.proto.PrioritizedTransaction;
import com.thesis.proto.PriorityRequest;
import com.thesis.proto.PriorityResponse;
import com.thesis.proto.SystemState;
import com.thesis.proto.Transaction;
import com.thesis.proto.TransactionType;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.example.gatewayservice.dto.TransactionRequest;
import org.example.gatewayservice.dto.TransactionResponse;
import org.example.gatewayservice.grpc.InferenceClient;
import org.example.gatewayservice.kafka.TransactionProducer;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.util.UUID;

@Service
@Slf4j
@RequiredArgsConstructor
public class TransactionGatewayService {

    private final InferenceClient inferenceClient;
    private final TransactionProducer transactionProducer;
    private final SystemMetricsService metricsService;

    @Value("${spring.application.name:gateway-service}")
    private String instanceName;

    public TransactionResponse processTransaction(TransactionRequest request) {
        String txId = UUID.randomUUID().toString();

        Transaction.Builder txBuilder = Transaction.newBuilder()
                .setId(txId)
                .setUserId(request.userId() != null ? request.userId() : "anonymous")
                .setAmount(request.amount())
                .setCurrency(request.currency() != null ? request.currency() : "USD")
                .setRegion(request.region() != null ? request.region() : "DEFAULT")
                .setTimestamp(System.currentTimeMillis())
                .setRetryCount(0);

        if (request.type() != null) {
            try {
                txBuilder.setType(TransactionType.valueOf(request.type()));
            } catch (IllegalArgumentException e) {
                log.warn("Unknown transaction type '{}', defaulting to PAYMENT", request.type());
                txBuilder.setType(TransactionType.PAYMENT);
            }
        } else {
            txBuilder.setType(TransactionType.PAYMENT);
        }

        if (request.metadata() != null) {
            txBuilder.putAllMetadata(request.metadata());
        }

        Transaction transaction = txBuilder.build();

        SystemState systemState = buildSystemState();

        PriorityRequest priorityRequest = PriorityRequest.newBuilder()
                .setTransaction(transaction)
                .setCurrentState(systemState)
                .build();

        PriorityResponse priorityResponse = inferenceClient.getPriority(priorityRequest);

        PrioritizedTransaction prioritizedTransaction = PrioritizedTransaction.newBuilder()
                .setTransaction(transaction)
                .setPriority(priorityResponse.getPriority())
                .setScore(priorityResponse.getScore())
                .setAssignedAt(System.currentTimeMillis())
                .setGatewayInstance(instanceName)
                .build();

        transactionProducer.sendTransaction(prioritizedTransaction);

        log.info("Transaction {} processed: priority={}, score={}, reason={}",
                txId, priorityResponse.getPriority().name(),
                priorityResponse.getScore(), priorityResponse.getReason());

        return new TransactionResponse(
                txId,
                priorityResponse.getPriority().name(),
                priorityResponse.getScore(),
                priorityResponse.getReason(),
                "ACCEPTED"
        );
    }

    private SystemState buildSystemState() {
        double cpu = metricsService.getCpuUsage();
        double memory = metricsService.getMemoryUsage();
        long lag = metricsService.getConsumerLag();

        return SystemState.newBuilder()
                .setCpuUsage(cpu)
                .setMemoryUsage(memory)
                .setConsumerLag(lag)
                .setDynamicThreshold(0.5 + ((cpu + memory) / 200.0) * 0.3)
                .setActiveConsumers(2)
                .build();
    }
}
