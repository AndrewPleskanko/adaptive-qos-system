package org.example.coreprocessor.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.example.coreprocessor.entity.Priority;
import org.example.coreprocessor.entity.TransactionEntity;
import org.example.coreprocessor.entity.TransactionStatus;
import org.example.coreprocessor.entity.TransactionType;
import org.example.coreprocessor.repository.TransactionRepository;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.Instant;

@Slf4j
@Service
@RequiredArgsConstructor
public class TransactionProcessingService {

    private final TransactionRepository transactionRepository;
    private final RedisTemplate<String, String> redisTemplate;
    private final ObjectMapper objectMapper;

    @Transactional
    public void processTransaction(String message, String topic) {
        try {
            JsonNode rootNode = objectMapper.readTree(message);

            JsonNode txNode = rootNode.path("transaction");
            String id = txNode.path("id").asText();
            String userId = txNode.has("userId") ? txNode.path("userId").asText() : txNode.path("user_id").asText();
            BigDecimal amount = new BigDecimal(txNode.path("amount").asText("0"));
            String currency = txNode.path("currency").asText();
            String region = txNode.path("region").asText();
            String typeStr = txNode.path("type").asText();
            int retryCount = txNode.has("retryCount") ? txNode.path("retryCount").asInt() : txNode.path("retry_count").asInt(0);

            String priorityStr = rootNode.path("priority").asText();
            double score = rootNode.path("score").asDouble();
            String gatewayInstance = rootNode.has("gatewayInstance") ? rootNode.path("gatewayInstance").asText() : rootNode.path("gateway_instance").asText();

            Priority priority = Priority.valueOf(priorityStr);
            TransactionType type = TransactionType.valueOf(typeStr);

            TransactionEntity entity = TransactionEntity.builder()
                    .id(id)
                    .userId(userId)
                    .amount(amount)
                    .currency(currency)
                    .region(region)
                    .transactionType(type)
                    .priority(priority)
                    .score(score)
                    .status(TransactionStatus.PROCESSING)
                    .gatewayInstance(gatewayInstance)
                    .retryCount(retryCount)
                    .receivedAt(Instant.now())
                    .build();

            transactionRepository.saveAndFlush(entity);

            simulateProcessingDelay(priority);

            entity.setStatus(TransactionStatus.COMPLETED);
            entity.setProcessedAt(Instant.now());
            transactionRepository.save(entity);

            String redisKey = "processed:" + priority.name();
            redisTemplate.opsForValue().increment(redisKey);

            log.info("Processed transaction {} with priority {} from topic {}", id, priority, topic);

        } catch (Exception e) {
            log.error("Failed to process transaction from message: {}", message, e);
            handleFailure(message, e);
        }
    }

    private void handleFailure(String message, Exception originalException) {
        try {
            JsonNode rootNode = objectMapper.readTree(message);
            JsonNode txNode = rootNode.path("transaction");
            String id = txNode.path("id").asText(null);
            if (id != null && !id.isEmpty()) {
                TransactionEntity failedEntity = transactionRepository.findById(id).orElse(new TransactionEntity());
                failedEntity.setId(id);
                failedEntity.setStatus(TransactionStatus.FAILED);
                failedEntity.setReason(originalException.getMessage());
                failedEntity.setProcessedAt(Instant.now());
                transactionRepository.save(failedEntity);
            }
        } catch (Exception ex) {
            log.error("Could not save FAILED state for transaction", ex);
        }
    }

    private void simulateProcessingDelay(Priority priority) throws InterruptedException {
        long delay = switch (priority) {
            case CRITICAL -> 10;
            case HIGH -> 50;
            case STANDARD -> 100;
            case LOW -> 200;
        };
        Thread.sleep(delay);
    }
}

