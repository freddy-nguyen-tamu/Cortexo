package com.cortexo.lab.config;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;

@Configuration
@ConfigurationProperties(prefix = "cortexo")
public class CortexoConfigProperties {

    private String mlGatewayUrl = "http://localhost:8000";
    private String frontendOrigin = "http://localhost:5173";

    public String getMlGatewayUrl() {
        return mlGatewayUrl;
    }

    public void setMlGatewayUrl(String mlGatewayUrl) {
        this.mlGatewayUrl = mlGatewayUrl;
    }

    public String getFrontendOrigin() {
        return frontendOrigin;
    }

    public void setFrontendOrigin(String frontendOrigin) {
        this.frontendOrigin = frontendOrigin;
    }
}