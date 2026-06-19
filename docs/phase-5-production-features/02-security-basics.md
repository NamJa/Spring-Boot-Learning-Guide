# Spring Security 7 기초

지금까지 우리의 Book API는 **누구나** 도서를 조회하고, 등록하고, 삭제할 수 있었습니다. 운영 환경에서는 말이 안 되는 일입니다. 최소한 "조회는 누구나, 변경은 인증된 사용자만" 같은 정책이 필요합니다.

이 문서에서는 **Spring Security 7** 의 핵심 개념과, Spring Boot 4 / Security 7에서 권장되는 **컴포넌트 스타일 `SecurityFilterChain`** 구성을 Kotlin DSL로 다룹니다. 그리고 운영의 정석인 JWT / OAuth2 Resource Server로 가는 길을 짚어 줍니다.

## 1. 시작: 스타터만 추가하면 벌어지는 일

```kotlin
// build.gradle.kts
dependencies {
    implementation("org.springframework.boot:spring-boot-starter-security")
}
```

이 한 줄을 추가하고 앱을 띄우면 즉시 다음이 적용됩니다.

- **모든 엔드포인트가 인증을 요구**합니다. `GET /api/books`조차 401이 납니다.
- 사용자명 `user`와 **무작위로 생성된 비밀번호**가 부팅 로그에 출력됩니다.
  ```
  Using generated security password: 8e1c...  (이 값으로 HTTP Basic 인증 가능)
  ```
- 기본적으로 **HTTP Basic**과 **폼 로그인**이 켜집니다.

즉 Spring Security는 "기본은 닫고, 필요한 곳만 연다"는 **secure-by-default** 철학입니다. 이제 이 기본값을 우리 정책으로 덮어써야 합니다.

## 2. `SecurityFilterChain` — 보안 설정의 중심

Spring Security 5.7부터 `WebSecurityConfigurerAdapter`를 상속하는 방식은 **제거**되었습니다. Security 7에서는 오직 **`SecurityFilterChain` 빈을 등록하는 컴포넌트 스타일**만 사용합니다.

```
요청 ──► [SecurityFilterChain]
             ├─ CSRF 필터
             ├─ 인증 필터 (Basic / 폼 / JWT ...)
             ├─ 인가 필터 (authorizeHttpRequests)
             └─ ...
         ──► 디스패처 서블릿 ──► BookController
```

`SecurityFilterChain`은 "어떤 요청 경로에, 어떤 인증/인가 규칙을 적용할지"를 담은 필터 묶음입니다. 빈으로 등록하면 Spring Boot가 기본 체인 대신 우리 것을 씁니다.

## 3. Book API 보안 정책 구성 (Kotlin DSL)

요구사항을 정합시다.

- `GET /api/books`, `GET /api/books/{id}` → **누구나** 허용
- `POST`, `PUT`, `DELETE /api/books/**` → **인증된 사용자만**
- 그 외는 인증 요구
- REST API이므로 **HTTP Basic** 사용, **CSRF는 비활성화**

Kotlin에서는 `http.invoke { ... }` 형태의 **Security Kotlin DSL**을 쓰면 람다 빌더보다 훨씬 읽기 좋습니다.

```kotlin
package com.example.bookapi.config

import org.springframework.context.annotation.Bean
import org.springframework.context.annotation.Configuration
import org.springframework.http.HttpMethod
import org.springframework.security.config.annotation.web.builders.HttpSecurity
import org.springframework.security.config.annotation.web.invoke   // Kotlin DSL 확장 import (중요!)
import org.springframework.security.web.SecurityFilterChain

@Configuration
class SecurityConfig {

    @Bean
    fun securityFilterChain(http: HttpSecurity): SecurityFilterChain {
        http {
            // 순수 REST API → 세션 기반 CSRF 토큰 불필요
            csrf { disable() }

            authorizeHttpRequests {
                // 조회는 누구나
                authorize(HttpMethod.GET, "/api/books/**", permitAll)
                // 변경은 인증 필요
                authorize(HttpMethod.POST, "/api/books/**", authenticated)
                authorize(HttpMethod.PUT, "/api/books/**", authenticated)
                authorize(HttpMethod.DELETE, "/api/books/**", authenticated)
                // Actuator 헬스 체크는 공개 (Phase 5-3 참고)
                authorize("/actuator/health/**", permitAll)
                // 나머지는 모두 인증
                authorize(anyRequest, authenticated)
            }

            httpBasic { }   // HTTP Basic 인증 사용
        }
        return http.build()
    }
}
```

> [!TIP]
> `import org.springframework.security.config.annotation.web.invoke` 를 빼먹으면 `http { ... }` 블록이 컴파일되지 않습니다. 이 확장 함수가 Kotlin DSL의 진입점입니다.

## 4. 사용자와 비밀번호 — `PasswordEncoder`

부팅 때마다 바뀌는 무작위 비밀번호로는 개발조차 불편합니다. 인메모리 사용자를 정의하되, **비밀번호는 절대 평문으로 저장하지 않습니다.** 운영에서는 **BCrypt**가 표준입니다.

```kotlin
import org.springframework.security.core.userdetails.User
import org.springframework.security.core.userdetails.UserDetailsService
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder
import org.springframework.security.crypto.password.PasswordEncoder
import org.springframework.security.provisioning.InMemoryUserDetailsManager

@Configuration
class UserConfig {

    @Bean
    fun passwordEncoder(): PasswordEncoder = BCryptPasswordEncoder()

    @Bean
    fun userDetailsService(encoder: PasswordEncoder): UserDetailsService {
        val admin = User.withUsername("admin")
            .password(encoder.encode("admin-secret"))  // 저장 시 BCrypt 해시로 변환
            .roles("ADMIN")
            .build()
        return InMemoryUserDetailsManager(admin)
    }
}
```

이제 `POST /api/books`를 호출하려면 `admin / admin-secret` 으로 Basic 인증해야 합니다.

```bash
# 인증 없이 조회 (성공)
curl http://localhost:8080/api/books

# 인증 없이 등록 (401)
curl -X POST http://localhost:8080/api/books -d '{...}'

# 인증하여 등록 (성공)
curl -u admin:admin-secret -X POST http://localhost:8080/api/books \
  -H 'Content-Type: application/json' -d '{"title":"코틀린 인 액션","price":35000}'
```

> [!TIP]
> 실무에서는 사용자가 DB에 있으므로 `UserDetailsService`를 직접 구현해 JPA 리포지토리에서 사용자를 읽어옵니다. 인메모리는 학습·데모용입니다.

## 5. CSRF — 언제 끄고 언제 켜는가

위에서 `csrf { disable() }` 했는데, 함부로 흉내 내면 안 되므로 원리를 짚습니다.

**CSRF(Cross-Site Request Forgery)** 는 브라우저가 자동으로 보내는 **쿠키 기반 세션**을 악용하는 공격입니다. CSRF 토큰은 이 자동 전송을 막는 방어 장치입니다.

| 상황 | CSRF |
|------|------|
| 세션 쿠키 + 서버 렌더링 폼 (브라우저 앱) | **켜야 함** (기본값 유지) |
| 토큰(JWT 등)을 헤더로 보내는 순수 REST API | 비활성화 가능 |

순수 REST API는 보통 쿠키 대신 `Authorization` 헤더로 인증하므로 CSRF 벡터가 없습니다. 그래서 끕니다. 하지만 **쿠키로 세션을 유지하는 SPA**라면 CSRF를 끄면 안 되고, `CookieCsrfTokenRepository`를 쓰는 편이 맞습니다.

## 6. 운영의 정석 — JWT / OAuth2 Resource Server (소개)

HTTP Basic은 학습엔 좋지만 운영 REST API의 표준은 아닙니다. 실무에서는 **토큰 기반 인증**이 정석입니다. 우리 API는 보통 **OAuth2 Resource Server** 역할을 합니다. 즉 인증 서버(Keycloak, Auth0, Cognito 등)가 발급한 **JWT를 검증만** 합니다.

```kotlin
// build.gradle.kts
// implementation("org.springframework.boot:spring-boot-starter-oauth2-resource-server")
```

```kotlin
@Bean
fun securityFilterChain(http: HttpSecurity): SecurityFilterChain {
    http {
        csrf { disable() }
        authorizeHttpRequests {
            authorize(HttpMethod.GET, "/api/books/**", permitAll)
            authorize(anyRequest, authenticated)
        }
        // 들어오는 요청의 Bearer JWT를 검증
        oauth2ResourceServer {
            jwt { }
        }
    }
    return http.build()
}
```

```yaml
spring:
  security:
    oauth2:
      resourceserver:
        jwt:
          # 인증 서버의 JWK 공개키 위치 — 이것만 주면 서명 검증을 자동으로 한다
          issuer-uri: https://auth.example.com/realms/bookapp
```

이렇게 하면 우리 서비스는 비밀번호를 직접 다루지 않고, **토큰의 서명·만료·스코프만** 검증합니다. 권한은 JWT의 클레임(`scope`, `roles`)에서 매핑합니다. 전체 구현은 이 가이드의 범위를 넘지만, **운영에서 가야 할 방향은 거의 항상 이쪽**임을 기억하세요.

## 7. 메서드 수준 보안 (보너스)

URL 규칙 외에 메서드 단위로도 인가할 수 있습니다.

```kotlin
@Configuration
@EnableMethodSecurity   // @PreAuthorize 등 활성화
class MethodSecurityConfig

@Service
class BookService(/* ... */) {
    @PreAuthorize("hasRole('ADMIN')")
    fun delete(id: Long) { /* ... */ }
}
```

서비스 계층 비즈니스 규칙과 가까운 곳에서 인가를 표현할 때 유용합니다.

## 다음 단계

API를 보호했으니, 이제 운영 중 시스템 내부에서 **무슨 일이 벌어지는지 들여다볼** 차례입니다. Actuator와 관측성으로 헬스 체크, 메트릭, 분산 추적을 다룹니다.

→ [Actuator와 관측성](03-actuator-observability.md)
