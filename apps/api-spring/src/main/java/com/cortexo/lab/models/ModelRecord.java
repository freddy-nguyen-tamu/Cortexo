package com.cortexo.lab.models;

import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

@Document(collection = "models")
public class ModelRecord {

    @Id
    private String id;

    private String modelId;
    private String displayName;
    private String family;
    private String technique;
    private String parentModelId;
    private String tokenizerId;
    private Long parameterCount = 0L;
    private Long trainableParameterCount = 0L;
    private Long activeParameterCount = 0L;
    private String precision;
    private Integer contextLength;
    private Map<String, Object> architecture = Map.of();
    private List<String> trainingDatasetIds = new ArrayList<>();
    private List<String> trainingRunIds = new ArrayList<>();
    private String alignmentMethod;
    private String quantization;
    private String license;
    private String artifactUri;
    private String artifactSha256;
    private String gitSha;
    private Map<String, Object> evaluationSummary = Map.of();
    private List<String> knownLimitations = new ArrayList<>();
    private List<String> tags = new ArrayList<>();
    private Map<String, Object> config = Map.of();
    private Instant createdAt = Instant.now();

    public String getId() {
        return id;
    }

    public void setId(String id) {
        this.id = id;
    }

    public String getModelId() {
        return modelId;
    }

    public void setModelId(String modelId) {
        this.modelId = modelId;
    }

    public String getDisplayName() {
        return displayName;
    }

    public void setDisplayName(String displayName) {
        this.displayName = displayName;
    }

    public String getFamily() {
        return family;
    }

    public void setFamily(String family) {
        this.family = family;
    }

    public String getTechnique() {
        return technique;
    }

    public void setTechnique(String technique) {
        this.technique = technique;
    }

    public String getParentModelId() {
        return parentModelId;
    }

    public void setParentModelId(String parentModelId) {
        this.parentModelId = parentModelId;
    }

    public String getTokenizerId() {
        return tokenizerId;
    }

    public void setTokenizerId(String tokenizerId) {
        this.tokenizerId = tokenizerId;
    }

    public Long getParameterCount() {
        return parameterCount;
    }

    public void setParameterCount(Long parameterCount) {
        this.parameterCount = parameterCount;
    }

    public Long getTrainableParameterCount() {
        return trainableParameterCount;
    }

    public void setTrainableParameterCount(Long trainableParameterCount) {
        this.trainableParameterCount = trainableParameterCount;
    }

    public Long getActiveParameterCount() {
        return activeParameterCount;
    }

    public void setActiveParameterCount(Long activeParameterCount) {
        this.activeParameterCount = activeParameterCount;
    }

    public String getPrecision() {
        return precision;
    }

    public void setPrecision(String precision) {
        this.precision = precision;
    }

    public Integer getContextLength() {
        return contextLength;
    }

    public void setContextLength(Integer contextLength) {
        this.contextLength = contextLength;
    }

    public Map<String, Object> getArchitecture() {
        return architecture;
    }

    public void setArchitecture(Map<String, Object> architecture) {
        this.architecture = architecture;
    }

    public List<String> getTrainingDatasetIds() {
        return trainingDatasetIds;
    }

    public void setTrainingDatasetIds(List<String> trainingDatasetIds) {
        this.trainingDatasetIds = trainingDatasetIds;
    }

    public List<String> getTrainingRunIds() {
        return trainingRunIds;
    }

    public void setTrainingRunIds(List<String> trainingRunIds) {
        this.trainingRunIds = trainingRunIds;
    }

    public String getAlignmentMethod() {
        return alignmentMethod;
    }

    public void setAlignmentMethod(String alignmentMethod) {
        this.alignmentMethod = alignmentMethod;
    }

    public String getQuantization() {
        return quantization;
    }

    public void setQuantization(String quantization) {
        this.quantization = quantization;
    }

    public String getLicense() {
        return license;
    }

    public void setLicense(String license) {
        this.license = license;
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

    public String getGitSha() {
        return gitSha;
    }

    public void setGitSha(String gitSha) {
        this.gitSha = gitSha;
    }

    public Map<String, Object> getEvaluationSummary() {
        return evaluationSummary;
    }

    public void setEvaluationSummary(Map<String, Object> evaluationSummary) {
        this.evaluationSummary = evaluationSummary;
    }

    public List<String> getKnownLimitations() {
        return knownLimitations;
    }

    public void setKnownLimitations(List<String> knownLimitations) {
        this.knownLimitations = knownLimitations;
    }

    public List<String> getTags() {
        return tags;
    }

    public void setTags(List<String> tags) {
        this.tags = tags;
    }

    public Map<String, Object> getConfig() {
        return config;
    }

    public void setConfig(Map<String, Object> config) {
        this.config = config;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(Instant createdAt) {
        this.createdAt = createdAt;
    }
}