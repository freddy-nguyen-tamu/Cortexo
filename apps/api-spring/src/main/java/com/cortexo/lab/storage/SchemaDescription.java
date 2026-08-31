package com.cortexo.lab.storage;

import java.util.List;

public record SchemaDescription(String id, String dialect, List<String> tables) {
}