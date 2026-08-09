package org.example.coreprocessor.kafka;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.example.coreprocessor.service.TransactionProcessingService;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.kafka.support.KafkaHeaders;
import org.springframework.messaging.handler.annotation.Header;
import org.springframework.messaging.handler.annotation.Payload;
import org.springframework.stereotype.Component;

/**
 * Kafka consumer listening to prioritized transaction topics.
 */
@Component
@Slf4j
@RequiredArgsConstructor
public class TransactionConsumer {

    private final TransactionProcessingService processingService;

    @KafkaListener(topics = "tx.priority.critical", groupId = "core-processor-group", concurrency = "4")
    public void consumeCritical(@Payload String message, @Header(KafkaHeaders.RECEIVED_TOPIC) String topic) {
        processingService.processTransaction(message, topic);
    }

    @KafkaListener(topics = "tx.priority.high", groupId = "core-processor-group", concurrency = "3")
    public void consumeHigh(@Payload String message, @Header(KafkaHeaders.RECEIVED_TOPIC) String topic) {
        processingService.processTransaction(message, topic);
    }

    @KafkaListener(topics = "tx.priority.standard", groupId = "core-processor-group", concurrency = "2")
    public void consumeStandard(@Payload String message, @Header(KafkaHeaders.RECEIVED_TOPIC) String topic) {
        processingService.processTransaction(message, topic);
    }

    @KafkaListener(topics = "tx.priority.low", groupId = "core-processor-group", concurrency = "1")
    public void consumeLow(@Payload String message, @Header(KafkaHeaders.RECEIVED_TOPIC) String topic) {
        processingService.processTransaction(message, topic);
    }
}
