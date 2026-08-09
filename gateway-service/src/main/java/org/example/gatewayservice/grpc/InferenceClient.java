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
            log.error("Error calling InferenceEngine, falling back to STANDARD priority", e);
            return PriorityResponse.newBuilder()
                    .setPriority(Priority.STANDARD)
                    .setScore(0.5)
                    .setReason("Fallback due to error: " + e.getMessage())
                    .build();
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
