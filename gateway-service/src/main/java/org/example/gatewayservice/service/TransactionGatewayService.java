package org.example.gatewayservice.service;

import com.thesis.proto.PrioritizedTransaction;
import com.thesis.proto.Priority;
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

    @Value("${app.qos.mode:adaptive}")
    private String qosMode;

    public TransactionResponse processTransaction(TransactionRequest request) {
        long dispatchStart = System.nanoTime();
        String txId = UUID.randomUUID().toString();

        Transaction.Builder txBuilder = Transaction.newBuilder()
                .setId(txId)
                .setUserId(request.userId() != null ? request.userId() : "anonymous")
                .setAmount(request.amount())
                .setCurrency(request.currency() != null ? request.currency() : "USD")
                .setRegion(request.region() != null ? request.region() : "DEFAULT")
                .setTimestamp(System.currentTimeMillis())
                .setRetryCount(request.retryCount());

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

        PriorityResponse priorityResponse = switch (qosMode.toLowerCase()) {
            case "fifo" -> dispatchFifo();
            case "static" -> dispatchStatic(transaction);
            default -> dispatchAdaptive(transaction);
        };

        long decisionLatencyUs = (System.nanoTime() - dispatchStart) / 1_000;

        PrioritizedTransaction prioritizedTransaction = PrioritizedTransaction.newBuilder()
                .setTransaction(transaction)
                .setPriority(priorityResponse.getPriority())
                .setScore(priorityResponse.getScore())
                .setAssignedAt(System.currentTimeMillis())
                .setGatewayInstance(instanceName)
                .build();

        transactionProducer.sendTransaction(prioritizedTransaction);

        log.info("Transaction {} processed: mode={}, priority={}, score={}, latency={}us",
                txId, qosMode, priorityResponse.getPriority().name(),
                priorityResponse.getScore(), decisionLatencyUs);

        return new TransactionResponse(
                txId,
                priorityResponse.getPriority().name(),
                priorityResponse.getScore(),
                priorityResponse.getReason(),
                "ACCEPTED",
                decisionLatencyUs
        );
    }

    private PriorityResponse dispatchFifo() {
        return PriorityResponse.newBuilder()
                .setPriority(Priority.STANDARD)
                .setScore(0.5)
                .setReason("[fifo] No priority evaluation")
                .build();
    }

    private PriorityResponse dispatchStatic(Transaction transaction) {
        Priority priority = transaction.getType() == TransactionType.PAYMENT
                ? Priority.CRITICAL
                : Priority.LOW;
        return PriorityResponse.newBuilder()
                .setPriority(priority)
                .setScore(priority == Priority.CRITICAL ? 0.95 : 0.2)
                .setReason("[static] type=" + transaction.getType().name())
                .build();
    }

    private PriorityResponse dispatchAdaptive(Transaction transaction) {
        SystemState systemState = buildSystemState();

        PriorityRequest priorityRequest = PriorityRequest.newBuilder()
                .setTransaction(transaction)
                .setCurrentState(systemState)
                .build();

        return inferenceClient.getPriority(priorityRequest);
    }

    private SystemState buildSystemState() {
        double cpu = metricsService.getCpuUsage();
        double memory = metricsService.getMemoryUsage();
        long lag = metricsService.getConsumerLag();
        double lagGrowthRate = metricsService.getLagGrowthRate();
        double dbPoolActive = metricsService.getDbPoolActive();
        double p99Latency = metricsService.getRecentP99Latency();

        return SystemState.newBuilder()
                .setCpuUsage(cpu)
                .setMemoryUsage(memory)
                .setConsumerLag(lag)
                .setLagGrowthRate(lagGrowthRate)
                .setDbPoolActive(dbPoolActive)
                .setRecentP99Latency(p99Latency)
                .setDynamicThreshold(0.5 + ((cpu + memory) / 200.0) * 0.3)
                .setActiveConsumers(2)
                .build();
    }
}
