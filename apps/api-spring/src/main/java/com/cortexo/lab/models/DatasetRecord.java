package com.cortexo.lab.models;

import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;

import java.time.Instant;
import java.util.List;
import java.util.Map;

@Document(collection = "datasets")
public class DatasetRecord {

    @Id
    private String id;

    private String datasetId;
    private String version;
    private List<String> sourceManifest = List.of();
    private List<String> sourceLicenses = List.of();
    private String pipelineGitSha;
    private Map<String, Object> transformationConfig = Map.of();
    private Long fileCount = 0L;
    private Long tokenCount = 0L;
    private Map<String, Object> languageDistribution = Map.of();
    private Map<String, Object> dedupStatistics = Map.of();
    private Map<String, Object> splitHashes = Map.of();
    private String artifactHash;
    private Instant createdAt = Instant.now();

    public String getId() {
        return id;
    }

    public void setId(String id) {
        this.id = id;
    }

    public String getDatasetId() {
        return datasetId;
    }

    public void setDatasetId(String datasetId) {
        this.datasetId = datasetId;
    }

    public String getVersion() {
        return version;
    }

    public void setVersion(String version) {
        this.version = version;
    }

    public List<String> getSourceManifest() {
        return sourceManifest;
    }

    public void setSourceManifest(List<String> sourceManifest) {
        this.sourceManifest = sourceManifest;
    }

    public List<String> getSourceLicenses() {
        return sourceLicenses;
    }

    public void setSourceLicenses(List<String> sourceLicenses) {
        this.sourceLicenses = sourceLicenses;
    }

    public String getPipelineGitSha() {
        return pipelineGitSha;
    }

    public void setPipelineGitSha(String pipelineGitSha) {
        this.pipelineGitSha = pipelineGitSha;
    }

    public Map<String, Object> getTransformationConfig() {
        return transformationConfig;
    }

    public void setTransformationConfig(Map<String, Object> transformationConfig) {
        this.transformationConfig = transformationConfig;
    }

    public Long getFileCount() {
        return fileCount;
    }

    public void setFileCount(Long fileCount) {
        this.fileCount = fileCount;
    }

    public Long getTokenCount() {
        return tokenCount;
    }

    public void setTokenCount(Long tokenCount) {
        this.tokenCount = tokenCount;
    }

    public Map<String, Object> getLanguageDistribution() {
        return languageDistribution;
    }

    public void setLanguageDistribution(Map<String, Object> languageDistribution) {
        this.languageDistribution = languageDistribution;
    }

    public Map<String, Object> getDedupStatistics() {
        return dedupStatistics;
    }

    public void setDedupStatistics(Map<String, Object> dedupStatistics) {
        this.dedupStatistics = dedupStatistics;
    }

    public Map<String, Object> getSplitHashes() {
        return splitHashes;
    }

    public void setSplitHashes(Map<String, Object> splitHashes) {
        this.splitHashes = splitHashes;
    }

    public String getArtifactHash() {
        return artifactHash;
    }

    public void setArtifactHash(String artifactHash) {
        this.artifactHash = artifactHash;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(Instant createdAt) {
        this.createdAt = createdAt;
    }
}