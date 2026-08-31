package com.cortexo.lab.auth;

import com.cortexo.lab.common.ApiException;
import com.cortexo.lab.common.ApiResponse;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

@RestController
@RequestMapping("/api/auth")
public class AuthController {

    private final AppUserRepository users;
    private final PasswordEncoder passwordEncoder;
    private final JwtService jwtService;

    public AuthController(AppUserRepository users, PasswordEncoder passwordEncoder, JwtService jwtService) {
        this.users = users;
        this.passwordEncoder = passwordEncoder;
        this.jwtService = jwtService;
    }

    @PostMapping("/register")
    public ApiResponse<AuthResponse> register(@Valid @RequestBody RegisterRequest req) {
        if (users.findByUsername(req.username()).isPresent()) {
            throw ApiException.badRequest("username already exists");
        }
        if (req.email() != null && users.findByEmail(req.email()).isPresent()) {
            throw ApiException.badRequest("email already exists");
        }

        AppUser user = new AppUser();
        user.setUsername(req.username());
        user.setEmail(req.email());
        user.setPasswordHash(passwordEncoder.encode(req.password()));
        AppUser saved = users.save(user);

        return ApiResponse.ok(new AuthResponse(jwtService.createToken(saved), saved.getUsername(), saved.getRole().name()));
    }

    @PostMapping("/login")
    public ApiResponse<AuthResponse> login(@Valid @RequestBody LoginRequest req) {
        AppUser user = users.findByUsername(req.username())
                .orElseThrow(() -> ApiException.badRequest("invalid credentials"));
        if (!passwordEncoder.matches(req.password(), user.getPasswordHash())) {
            throw ApiException.badRequest("invalid credentials");
        }
        return ApiResponse.ok(new AuthResponse(jwtService.createToken(user), user.getUsername(), user.getRole().name()));
    }

    public record RegisterRequest(
            @NotBlank @Size(min = 3, max = 64) String username,
            String email,
            @NotBlank @Size(min = 8, max = 128) String password) {
    }

    public record LoginRequest(
            @NotBlank String username,
            @NotBlank String password) {
    }

    public record AuthResponse(String token, String username, String role) {
    }
}