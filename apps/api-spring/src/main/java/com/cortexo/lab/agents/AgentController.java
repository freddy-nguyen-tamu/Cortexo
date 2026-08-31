package com.cortexo.lab.agents;

import com.cortexo.lab.common.ApiResponse;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/agents")
public class AgentController {

    private final AgentService service;

    public AgentController(AgentService service) {
        this.service = service;
    }

    @PostMapping("/runs")
    public ApiResponse<com.cortexo.lab.repositories.AgentRunRecord> create(
            @RequestBody AgentService.AgentRunRequest request) {
        return ApiResponse.ok(service.createRun(request));
    }

    @GetMapping("/runs/{agentRunId}")
    public ApiResponse<com.cortexo.lab.repositories.AgentRunRecord> get(@PathVariable String agentRunId) {
        return ApiResponse.ok(service.get(agentRunId));
    }
}