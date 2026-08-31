package com.cortexo.lab.auth;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.Base64;
import java.util.HashMap;
import java.util.Map;

@Service
public class JwtService {

    private final ObjectMapper objectMapper = new ObjectMapper();
    private final byte[] secret;
    private final long expirationMinutes;

    public JwtService(
            @Value("${cortexo.security.jwt-secret:CHANGE_ME}") String secret,
            @Value("${cortexo.security.jwt-expiration-minutes:120}") long expirationMinutes) {
        this.secret = secret.getBytes(StandardCharsets.UTF_8);
        this.expirationMinutes = expirationMinutes;
    }

    public String createToken(AppUser user) {
        try {
            Map<String, Object> claims = new HashMap<>();
            claims.put("sub", user.getId());
            claims.put("username", user.getUsername());
            claims.put("role", user.getRole().name());
            claims.put("iat", Instant.now().getEpochSecond());
            claims.put("exp", Instant.now().plusSeconds(expirationMinutes * 60).getEpochSecond());

            String header = base64Url(objectMapper.writeValueAsBytes(Map.of("alg", "HS256", "typ", "JWT")));
            String payload = base64Url(objectMapper.writeValueAsBytes(claims));
            String signature = sign(header + "." + payload);
            return header + "." + payload + "." + signature;
        } catch (Exception e) {
            throw new IllegalStateException("unable to sign token", e);
        }
    }

    public JwtClaims parse(String token) {
        try {
            String[] parts = token.split("\\.");
            if (parts.length != 3) {
                throw new IllegalArgumentException("malformed token");
            }
            String expected = sign(parts[0] + "." + parts[1]);
            if (!constantEquals(expected, parts[2])) {
                throw new IllegalArgumentException("bad signature");
            }
            byte[] decoded = Base64.getUrlDecoder().decode(parts[1]);
            JsonNode payload = objectMapper.readTree(decoded);
            long exp = payload.path("exp").asLong(0);
            if (Instant.now().getEpochSecond() >= exp) {
                throw new IllegalArgumentException("expired token");
            }
            return new JwtClaims(
                    payload.path("sub").asText(),
                    payload.path("username").asText(),
                    payload.path("role").asText());
        } catch (Exception e) {
            throw new IllegalArgumentException("invalid token", e);
        }
    }

    private String sign(String data) {
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(secret, "HmacSHA256"));
            return base64Url(mac.doFinal(data.getBytes(StandardCharsets.UTF_8)));
        } catch (Exception e) {
            throw new IllegalStateException("unable to sign", e);
        }
    }

    private static String base64Url(byte[] bytes) {
        return Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);
    }

    private static boolean constantEquals(String a, String b) {
        return java.security.MessageDigest.isEqual(
                a.getBytes(StandardCharsets.UTF_8), b.getBytes(StandardCharsets.UTF_8));
    }

    public record JwtClaims(String userId, String username, String role) {
    }
}