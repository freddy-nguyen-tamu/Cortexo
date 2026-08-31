package com.cortexo.lab.common;

public record ApiResponse<T>(String status, T data, String message) {

    public static <T> ApiResponse<T> ok(T data) {
        return new ApiResponse<>("ok", data, null);
    }

    public static <T> ApiResponse<T> ok(T data, String message) {
        return new ApiResponse<>("ok", data, message);
    }

    public static <T> ApiResponse<T> error(String message) {
        return new ApiResponse<>("error", null, message);
    }

    public ApiResponse<T> withData(T newData) {
        return new ApiResponse<>(this.status, newData, this.message);
    }
}