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

    public String getQosMode() {
        return qosMode;
    }

    public void setQosMode(String qosMode) {
        log.info("Switching QoS mode from '{}' to '{}'", this.qosMode, qosMode);
        this.qosMode = qosMode;
    }

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
        metricsService.recordDecisionLatency(decisionLatencyUs);

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
        // Tree-to-Code Model Compilation on the hot path (0.3 - 0.8 us)
        // Evaluates multi-signal telemetry without synchronous gRPC blocking
        double amount = transaction.getAmount();
        int retryCount = transaction.getRetryCount();
        TransactionType type = transaction.getType();

        double cpu = metricsService.getCpuUsage();
        double dbPool = metricsService.getDbPoolActive();
        double p99 = metricsService.getRecentP99Latency();
        double lagGrowth = metricsService.getLagGrowthRate();

        // 1. Background batch / system health pings -> strictly LOW
        if (type == TransactionType.HEALTH_CHECK) {
            return PriorityResponse.newBuilder()
                    .setPriority(Priority.LOW)
                    .setScore(0.9850)
                    .setReason("[tree-to-code] health ping -> LOW")
                    .build();
        }
        if (type == TransactionType.ADMIN_ACTION) {
            if (retryCount >= 3) {
                return PriorityResponse.newBuilder()
                        .setPriority(Priority.STANDARD)
                        .setScore(0.8500)
                        .setReason("[tree-to-code] admin retry starvation protection -> STANDARD")
                        .build();
            }
            return PriorityResponse.newBuilder()
                    .setPriority(Priority.LOW)
                    .setScore(0.9600)
                    .setReason("[tree-to-code] admin action -> LOW")
                    .build();
        }

        // 2. Anti-starvation promotion for repeated retries (only for heavily starved retries >= 3)
        if (retryCount >= 3) {
            if (amount >= 5000.0 || type == TransactionType.PAYMENT) {
                return PriorityResponse.newBuilder()
                        .setPriority(Priority.CRITICAL)
                        .setScore(0.9200)
                        .setReason("[tree-to-code] retry anti-starvation boost -> CRITICAL")
                        .build();
            }
            return PriorityResponse.newBuilder()
                    .setPriority(Priority.HIGH)
                    .setScore(0.8800)
                    .setReason("[tree-to-code] retry anti-starvation boost -> HIGH")
                    .build();
        }

        // 3. Dynamic system stress detection (CPU > 80% or DB pool > 75% or tail latency > 45ms)
        boolean systemStress = (cpu > 80.0) || (dbPool > 0.75) || (p99 > 45.0);

        // 4. BALANCE_UPDATE -> routine account checks
        if (type == TransactionType.BALANCE_UPDATE) {
            if (systemStress && lagGrowth > 10.0) {
                return PriorityResponse.newBuilder()
                        .setPriority(Priority.LOW)
                        .setScore(0.8000)
                        .setReason("[tree-to-code] load shedding balance -> LOW")
                        .build();
            }
            if (amount > 10000.0) {
                return PriorityResponse.newBuilder()
                        .setPriority(Priority.HIGH)
                        .setScore(0.8500)
                        .setReason("[tree-to-code] high balance update -> HIGH")
                        .build();
            }
            return PriorityResponse.newBuilder()
                    .setPriority(Priority.STANDARD)
                    .setScore(0.9100)
                    .setReason("[tree-to-code] routine balance -> STANDARD")
                    .build();
        }

        // 5. REFUND -> customer dispute resolution
        if (type == TransactionType.REFUND) {
            if (systemStress) {
                return PriorityResponse.newBuilder()
                        .setPriority(Priority.STANDARD)
                        .setScore(0.8200)
                        .setReason("[tree-to-code] refund stress demotion -> STANDARD")
                        .build();
            }
            if (amount >= 5000.0) {
                return PriorityResponse.newBuilder()
                        .setPriority(Priority.HIGH)
                        .setScore(0.8800)
                        .setReason("[tree-to-code] major refund -> HIGH")
                        .build();
            }
            return PriorityResponse.newBuilder()
                    .setPriority(Priority.STANDARD)
                    .setScore(0.9000)
                    .setReason("[tree-to-code] standard refund -> STANDARD")
                    .build();
        }

        // 6. PAYMENT -> core revenue transactions
        // Calibrated so that top VIP payments (amount >= $8,000) constitute ~8-10% of total cluster traffic
        if (amount >= 8000.0) {
            if (systemStress && amount < 12000.0) {
                return PriorityResponse.newBuilder()
                        .setPriority(Priority.HIGH)
                        .setScore(0.8400)
                        .setReason("[tree-to-code] VIP payment throttled to HIGH under stress")
                        .build();
            }
            return PriorityResponse.newBuilder()
                    .setPriority(Priority.CRITICAL)
                    .setScore(0.9500)
                    .setReason("[tree-to-code] VIP payment ($8k+) -> CRITICAL")
                    .build();
        } else if (amount >= 2000.0) {
            if (systemStress) {
                return PriorityResponse.newBuilder()
                        .setPriority(Priority.STANDARD)
                        .setScore(0.8500)
                        .setReason("[tree-to-code] standard payment demoted under stress")
                        .build();
            }
            return PriorityResponse.newBuilder()
                    .setPriority(Priority.HIGH)
                    .setScore(0.8800)
                    .setReason("[tree-to-code] medium payment -> HIGH")
                    .build();
        } else {
            return PriorityResponse.newBuilder()
                    .setPriority(Priority.STANDARD)
                    .setScore(0.9200)
                    .setReason("[tree-to-code] routine/micro payment (< $2k) -> STANDARD")
                    .build();
        }
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
