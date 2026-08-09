package org.example.coreprocessor;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@EnableScheduling
@SpringBootApplication
public class CoreProcessorApplication {

    public static void main(String[] args) {
        SpringApplication.run(CoreProcessorApplication.class, args);
    }

}
