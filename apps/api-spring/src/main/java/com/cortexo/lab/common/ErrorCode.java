package com.cortexo.lab.common;

public final class ErrorCode {

    private ErrorCode() {
    }

    public static final String MODEL_LOAD_ERROR = "MODEL_LOAD_ERROR";
    public static final String OUT_OF_MEMORY = "OUT_OF_MEMORY";
    public static final String TOKEN_LIMIT = "TOKEN_LIMIT";
    public static final String INVALID_STRUCTURED_OUTPUT = "INVALID_STRUCTURED_OUTPUT";
    public static final String RETRIEVAL_EMPTY = "RETRIEVAL_EMPTY";
    public static final String RETRIEVAL_WRONG = "RETRIEVAL_WRONG";
    public static final String COMPILE_FAIL = "COMPILE_FAIL";
    public static final String TEST_FAIL = "TEST_FAIL";
    public static final String SANDBOX_TIMEOUT = "SANDBOX_TIMEOUT";
    public static final String SANDBOX_POLICY = "SANDBOX_POLICY";
    public static final String PATCH_APPLY_FAIL = "PATCH_APPLY_FAIL";
    public static final String TOOL_ERROR = "TOOL_ERROR";
    public static final String DATABASE_ERROR = "DATABASE_ERROR";
    public static final String ROUTER_NO_FEASIBLE_MODEL = "ROUTER_NO_FEASIBLE_MODEL";

    public static final String NOT_FOUND = "NOT_FOUND";
    public static final String BAD_REQUEST = "BAD_REQUEST";
    public static final String UNAUTHORIZED = "UNAUTHORIZED";
}