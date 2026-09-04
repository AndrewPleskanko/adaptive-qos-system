package org.example.gatewayservice.kafka;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.thesis.proto.PrioritizedTransaction;
import com.thesis.proto.Priority;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Service;

import java.util.HashMap;
import java.util.Map;

@Slf4j
@Service
@RequiredArgsConstructor
public class TransactionProducer {

    private final KafkaTemplate<String, String> kafkaTemplate;
    private final ObjectMapper objectMapper;

    public void sendTransaction(PrioritizedTransaction prioritizedTransaction) {
        String topic = getTopicForPriority(prioritizedTransaction.getPriority());
        String key = prioritizedTransaction.getTransaction().getId();

        try {
            Map<String, Object> transaction = new HashMap<>();
            transaction.put("id", prioritizedTransaction.getTransaction().getId());
            transaction.put("user_id", prioritizedTransaction.getTransaction().getUserId());
            transaction.put("amount", prioritizedTransaction.getTransaction().getAmount());
            transaction.put("currency", prioritizedTransaction.getTransaction().getCurrency());
            transaction.put("region", prioritizedTransaction.getTransaction().getRegion());
            transaction.put("type", prioritizedTransaction.getTransaction().getType().name());
            transaction.put("metadata", prioritizedTransaction.getTransaction().getMetadataMap());
            transaction.put("timestamp", prioritizedTransaction.getTransaction().getTimestamp());
            transaction.put("retry_count", prioritizedTransaction.getTransaction().getRetryCount());

            Map<String, Object> payload = new HashMap<>();
            payload.put("transaction", transaction);
            payload.put("priority", prioritizedTransaction.getPriority().name());
            payload.put("score", prioritizedTransaction.getScore());
            payload.put("assigned_at", prioritizedTransaction.getAssignedAt());
            payload.put("gateway_instance", prioritizedTransaction.getGatewayInstance());

            String json = objectMapper.writeValueAsString(payload);
            kafkaTemplate.send(topic, key, json);

            log.info("Sent transaction {} to topic {} (priority={})", key, topic,
                    prioritizedTransaction.getPriority().name());
        } catch (JsonProcessingException e) {
            log.error("Failed to serialize transaction {}", key, e);
        }
    }

    private String getTopicForPriority(Priority priority) {
        return switch (priority) {
            case CRITICAL -> "tx.priority.critical";
            case HIGH -> "tx.priority.high";
            case STANDARD -> "tx.priority.standard";
            case LOW, UNRECOGNIZED -> "tx.priority.low";
        };
    }
}
