package com.cortexo.lab.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.reactive.function.client.WebClient;

@Configuration
public class WebConfig {

    public static final String AUTH_ENABLED_PROPERTY = "cortexo.security.auth-enabled";

    @Bean
    public WebClient mlGatewayClient(CortexoConfigProperties props) {
        return WebClient.builder()
                .baseUrl(props.getMlGatewayUrl())
                .build();
    }
}