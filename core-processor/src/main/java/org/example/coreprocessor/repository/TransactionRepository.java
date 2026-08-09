package org.example.coreprocessor.repository;

import org.example.coreprocessor.entity.Priority;
import org.example.coreprocessor.entity.TransactionEntity;
import org.example.coreprocessor.entity.TransactionStatus;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface TransactionRepository extends JpaRepository<TransactionEntity, String> {
    List<TransactionEntity> findByPriority(Priority priority);

    List<TransactionEntity> findByStatus(TransactionStatus status);

    long countByPriority(Priority priority);
}
