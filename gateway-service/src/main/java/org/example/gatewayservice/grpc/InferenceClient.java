package org.example.gatewayservice.grpc;

import com.thesis.proto.InferenceServiceGrpc;
import com.thesis.proto.PriorityRequest;
import com.thesis.proto.PriorityResponse;
import com.thesis.proto.Priority;
import io.grpc.ManagedChannel;
import io.grpc.ManagedChannelBuilder;
import jakarta.annotation.PreDestroy;
import lombok.extern.slf4j.Slf4j;
import org.example.gatewayservice.config.GrpcClientConfig;
import org.springframework.stereotype.Service;

import java.util.concurrent.TimeUnit;

@Slf4j
@Service
public class InferenceClient {

    private final ManagedChannel channel;
    private final InferenceServiceGrpc.InferenceServiceBlockingStub blockingStub;

    public InferenceClient(GrpcClientConfig config) {
        this.channel = ManagedChannelBuilder.forAddress(config.getHost(), config.getPort())
                .usePlaintext()
                .build();
        this.blockingStub = InferenceServiceGrpc.newBlockingStub(channel);
    }

    public PriorityResponse getPriority(PriorityRequest request) {
        try {
            return blockingStub.withDeadlineAfter(3, TimeUnit.SECONDS)
                    .getPriority(request);
        } catch (Exception e) {
            log.error("Error calling InferenceEngine, falling back to Java rule-based logic", e);
            Priority fallbackPriority = computeFallbackPriority(request);
            return PriorityResponse.newBuilder()
                    .setPriority(fallbackPriority)
                    .setScore(0.5)
                    .setReason("Java Fallback due to error: " + e.getMessage())
                    .build();
        }
    }

    private Priority computeFallbackPriority(PriorityRequest request) {
        com.thesis.proto.Transaction tx = request.getTransaction();
        com.thesis.proto.SystemState state = request.getCurrentState();
        
        double baseScore = 0.5;
        switch (tx.getType()) {
            case PAYMENT:
                double amountScore = Math.min(tx.getAmount() / 5000.0, 1.0);
                baseScore = 0.60 + amountScore * 0.30;
                break;
            case REFUND:
                baseScore = 0.70;
                break;
            case BALANCE_UPDATE:
                baseScore = 0.40;
                break;
            case ADMIN_ACTION:
                baseScore = 0.85;
                break;
            case HEALTH_CHECK:
            default:
                baseScore = 0.15;
                break;
        }

        double cpu = state.getCpuUsage();
        double lag = state.getConsumerLag();
        double pressure = (cpu / 100.0) * 0.4 + (lag / 5000.0) * 0.3;
        
        double retryBoost = Math.min(tx.getRetryCount() * 0.12, 0.36);
        double finalScore = Math.max(0.0, Math.min(1.0, baseScore - pressure * 0.25 + retryBoost));

        if (finalScore >= 0.82) {
            return Priority.CRITICAL;
        } else if (finalScore >= 0.58) {
            return Priority.HIGH;
        } else if (finalScore >= 0.32) {
            return Priority.STANDARD;
        } else {
            return Priority.LOW;
        }
    }

    @PreDestroy
    public void shutdown() {
        try {
            channel.shutdown().awaitTermination(5, TimeUnit.SECONDS);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            log.warn("Thread interrupted during gRPC channel shutdown");
        }
    }
}
