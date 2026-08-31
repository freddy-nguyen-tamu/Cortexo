package com.cortexo.lab.models;

import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.Instant;
import java.util.List;
import java.util.Map;

@Document(collection = "tokenizers")
public class TokenizerRecord {

    @Id
    private String id;

    private String tokenizerId;
    private String family;
    private String algorithm;
    private Integer vocabSize;
    private Integer minFreq;
    private List<String> specialTokens = List.of();
    private Map<String, Object> training = Map.of();
    private Map<String, Object> metrics = Map.of();
    private String artifactUri;
    private String artifactSha256;
    private String license;
    private Instant createdAt = Instant.now();

    public String getId() {
        return id;
    }

    public void setId(String id) {
        this.id = id;
    }

    public String getTokenizerId() {
        return tokenizerId;
    }

    public void setTokenizerId(String tokenizerId) {
        this.tokenizerId = tokenizerId;
    }

    public String getFamily() {
        return family;
    }

    public void setFamily(String family) {
        this.family = family;
    }

    public String getAlgorithm() {
        return algorithm;
    }

    public void setAlgorithm(String algorithm) {
        this.algorithm = algorithm;
    }

    public Integer getVocabSize() {
        return vocabSize;
    }

    public void setVocabSize(Integer vocabSize) {
        this.vocabSize = vocabSize;
    }

    public Integer getMinFreq() {
        return minFreq;
    }

    public void setMinFreq(Integer minFreq) {
        this.minFreq = minFreq;
    }

    public List<String> getSpecialTokens() {
        return specialTokens;
    }

    public void setSpecialTokens(List<String> specialTokens) {
        this.specialTokens = specialTokens;
    }

    public Map<String, Object> getTraining() {
        return training;
    }

    public void setTraining(Map<String, Object> training) {
        this.training = training;
    }

    public Map<String, Object> getMetrics() {
        return metrics;
    }

    public void setMetrics(Map<String, Object> metrics) {
        this.metrics = metrics;
    }

    public String getArtifactUri() {
        return artifactUri;
    }

    public void setArtifactUri(String artifactUri) {
        this.artifactUri = artifactUri;
    }

    public String getArtifactSha256() {
        return artifactSha256;
    }

    public void setArtifactSha256(String artifactSha256) {
        this.artifactSha256 = artifactSha256;
    }

    public String getLicense() {
        return license;
    }

    public void setLicense(String license) {
        this.license = license;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(Instant createdAt) {
        this.createdAt = createdAt;
    }
}