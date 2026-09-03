# 27 - 权限控制：基于 RBAC 模型与 Spring Security + JWT

> 对应项目模块：`demo-rbac-security`
> 前置知识：已学完前面模块，了解 Spring Boot 基本开发、JPA、Redis、统一异常处理、配置注入
> 学习目标：理解 RBAC 权限模型、Spring Security 的认证授权机制、JWT 无状态认证原理，能看懂并改写一套前后端分离的权限后端。

---

## 一、本模块要解决什么问题？

几乎每个后端系统都要回答三个问题：

1. **你是谁？**（认证 Authentication）——用户登录，证明身份。
2. **你能做什么？**（授权 Authorization）——这个用户能访问哪些接口、看到哪些菜单、点哪些按钮。
3. **怎么管？**（管理）——谁能登录、谁被踢下线、当前有多少人在线。

本模块用 **Spring Security + JWT + Redis** 给出一套前后端分离的完整方案，核心设计是：

- **RBAC 模型**：用户-角色-权限三张表 + 两张关联表，权限可动态配置（不用改代码）。
- **JWT 无状态认证**：登录后发一个 token，前端每次请求带上，后端解析即知身份，不存 Session。
- **Redis 弥补 JWT 缺陷**：JWT 本身无法主动失效，把 token 存 Redis，删掉即"踢下线"；同一用户只允许一个 token，异地登录会让旧 token 失效。
- **动态权限拦截**：根据数据库里配置的"角色-权限-URL-请求方法"，运行时判断当前请求是否放行。

> 💡 前端类比：这套东西你其实见过——前端的路由守卫（`router.beforeEach`）判断能不能进页面、按钮级权限（`v-permission`）判断能不能显示按钮。区别是：**前端权限只是 UX 优化，真正的安全防线在后端**——因为前端代码可被篡改，后端必须对每个接口独立鉴权。本模块讲的就是后端这道防线。

---

## 二、项目结构

```
demo-rbac-security/
├── pom.xml
├── sql/security.sql                         # 建表 + 初始化数据脚本
└── src/main/java/com/xkcoding/rbac/security/
    ├── SpringBootDemoRbacSecurityApplication.java   # 启动类
    ├── common/                                # 通用基础类
    │   ├── ApiResponse.java                   # 统一响应体
    │   ├── Status.java                         # 状态码枚举
    │   ├── Consts.java                         # 常量
    │   └── ...
    ├── config/                                # 配置层（核心）
    │   ├── SecurityConfig.java                # Spring Security 主配置
    │   ├── JwtConfig.java                     # JWT 配置属性
    │   ├── JwtAuthenticationFilter.java       # JWT 过滤器（每请求执行）
    │   ├── RbacAuthorityService.java          # 动态权限校验
    │   ├── CustomConfig.java / IgnoreConfig.java  # 白名单配置
    │   ├── SecurityHandlerConfig.java         # 异常处理
    │   ├── WebMvcConfig.java                   # CORS 跨域
    │   └── RedisConfig.java                   # Redis 序列化
    ├── controller/
    │   ├── AuthController.java                # 登录/登出
    │   ├── MonitorController.java             # 在线用户、踢人
    │   └── TestController.java                # 测试鉴权
    ├── service/
    │   ├── CustomUserDetailsService.java     # 查用户(认证用)
    │   └── MonitorService.java                # 在线用户管理
    ├── model/                                 # 实体(User/Role/Permission + 关联)
    ├── repository/                            # JPA Dao
    ├── payload/LoginRequest.java             # 登录入参 DTO
    ├── vo/                                    # 返回对象(JwtResponse/OnlineUser/UserPrincipal)
    ├── util/                                  # 工具(JwtUtil/RedisUtil/SecurityUtil/ResponseUtil)
    └── exception/                             # 异常 + 全局处理
```

这个模块比前面所有模块都复杂，因为它是一个**完整的业务子系统**。但拆开看，每个组件职责单一，下面逐个讲。

---

## 三、pom.xml：安全相关的依赖

```xml
<!-- 1. Spring Security 起步依赖 -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-security</artifactId>
</dependency>

<!-- 2. JPA（持久层） -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-data-jpa</artifactId>
</dependency>

<!-- 3. Redis（存 JWT） -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-data-redis</artifactId>
</dependency>
<!-- Lettuce 连接池，用 Redis 时建议引入 -->
<dependency>
    <groupId>org.apache.commons</groupId>
    <artifactId>commons-pool2</artifactId>
</dependency>

<!-- 4. JWT 库 -->
<dependency>
    <groupId>io.jsonwebtoken</groupId>
    <artifactId>jjwt</artifactId>
    <version>0.9.1</version>
</dependency>
```

四个核心依赖对应四个能力：**Security 管认证授权、JPA 管数据、Redis 管 token 存活、jjwt 管 token 生成解析**。这是前后端分离权限系统的经典技术栈。

> ⚠️ 注意 pom 里 `<jjwt.veersion>0.9.1</jjwt.veersion>` 这个属性名拼写错了（多了个 e），但不影响功能，因为引用处也用了同样的错拼 `${jjwt.veersion}`。这是真实项目里常见的"将错就错"。

---

## 四、RBAC 数据模型：五张表讲透权限设计

`sql/security.sql` 是理解整个模块的基础。RBAC（Role-Based Access Control，基于角色的访问控制）用五张表：

```
sec_user              用户表
sec_role              角色表
sec_user_role         用户-角色关联表（多对多）
sec_permission        权限表
sec_role_permission   角色-权限关联表（多对多）
```

**为什么要"角色"这一层？** 直接给用户分权限不行吗？当用户多了，逐个分配权限是灾难。引入角色作为中间层：用户绑定角色，角色绑定权限。换人时只改"用户-角色"，调权限时只改"角色-权限"，互不影响。

> 💡 前端类比：这就像 RBAC 是"用户 → 部门 → 权限"，角色就是部门。给整个销售部开"查看订单"权限，比给每个销售员单独开高效得多。

### 4.1 权限表的关键设计

```sql
CREATE TABLE sec_permission (
  id         bigint  NOT NULL,
  name       varchar(50),           -- 权限名，如"测试页面-查询"
  url        varchar(1000),         -- 接口地址，如 /**/test
  type       int,                  -- 类型：1=页面，2=按钮
  permission varchar(50),           -- 权限表达式，如 btn:test:query
  method     varchar(50),           -- 请求方法，如 GET/POST
  sort       int,                  -- 排序
  parent_id  bigint                 -- 父级，构成树形菜单
);
```

**`type` 字段的精妙之处**：它区分"页面权限"和"按钮权限"。

- **页面权限（type=1）**：对应前端路由，如 `/test`、`/monitor`。前端用它渲染菜单、做路由守卫。
- **按钮权限（type=2）**：对应后端接口，如 `/**/test` + `GET`。后端用它做接口鉴权。

同一份权限表既服务前端（菜单/路由）又服务后端（接口鉴权），是前后端分离项目的常见做法。本模块后端只校验按钮权限（接口），页面权限留给前端用。

### 4.2 初始化数据

脚本里预置了两个用户、两个角色、六个权限：

| 用户 | 角色 | 权限 |
| --- | --- | --- |
| admin / 123456 | 管理员 | 测试页面(查/增)、监控页面(查/踢人) 全部 |
| user / 123456 | 普通用户 | 只有测试页面(查/增)，无监控权限 |

密码在数据库里是 `$2a$10$...` 这种乱码——这是 **BCrypt 加密**后的密文，不可逆。即使数据库泄露，攻击者也拿不到明文密码。登录时用 `BCryptPasswordEncoder` 把用户输入的明文加密后比对。

---

## 五、application.yml：配置详解

```yaml
spring:
  datasource:                    # 数据源
    hikari:
      username: root
      password: root
    url: jdbc:mysql://127.0.0.1:3306/spring-boot-demo?...
  jpa:
    show-sql: true               # 打印 SQL，调试用
    hibernate:
      ddl-auto: validate          # 只校验不建表（表用 SQL 脚本建）
  resources:
    add-mappings: false           # 关闭静态资源映射（前后端分离不需要）
  mvc:
    throw-exception-if-no-handler-found: true  # 404 抛异常，交给全局处理
  redis:                          # Redis 配置
    host: localhost
    port: 6379
    timeout: 10000ms
    lettuce:                      # 连接池
      pool:
        max-active: 8
jwt:
  config:
    key: xkcoding                 # JWT 签名密钥
    ttl: 600000                   # 有效期 10 分钟
    remember: 604800000           # 记住我：7 天
custom:
  config:
    ignores:                      # 白名单（不需要认证的接口）
      post:
        - "/api/auth/login"
        - "/api/auth/logout"
      pattern:
        - "/test/*"
```

几个要点：

- `ddl-auto: validate`：JPA 只校验实体和表结构是否一致，不自动建表。表结构由 `security.sql` 管理，更可控。
- `throw-exception-if-no-handler-found: true` + `add-mappings: false`：让 404 走异常处理流程，统一返回 JSON 而不是默认错误页。
- `jwt.config.*` 和 `custom.config.*`：自定义配置，分别绑定到 `JwtConfig` 和 `CustomConfig` 类（`@ConfigurationProperties`）。
- **白名单**：登录、登出接口必须放行（否则还没登录就被拦了），`/test/*` 也放行用于测试。

---

## 六、核心配置类 SecurityConfig：Spring Security 的"总开关"

这是整个模块的心脏，逐段拆解：

```java
@Configuration
@EnableWebSecurity
@EnableConfigurationProperties(CustomConfig.class)
public class SecurityConfig extends WebSecurityConfigurerAdapter {
```

- `@EnableWebSecurity`：开启 Spring Security，禁用默认的表单登录、HTTP Basic 等行为。
- 继承 `WebSecurityConfigurerAdapter`：通过重写 `configure` 方法定制安全策略（Spring Security 5.x 写法）。

### 6.1 密码加密器

```java
@Bean
public BCryptPasswordEncoder encoder() {
    return new BCryptPasswordEncoder();
}
```

注册一个密码加密器 Bean。每次加密会随机生成盐（salt），所以同一密码加密两次结果不同，更安全。登录时 `matches(明文, 密文)` 内部会提取盐来比对。

### 6.2 认证管理器

```java
@Override
@Bean
public AuthenticationManager authenticationManagerBean() throws Exception {
    return super.authenticationManagerBean();
}
```

把 `AuthenticationManager` 暴露为 Bean。它在 `AuthController` 登录时被注入，用来执行认证（调 `UserDetailsService` 查用户、比对密码）。默认它不在容器里，需要这样暴露。

### 6.3 用户认证来源

```java
@Override
protected void configure(AuthenticationManagerBuilder auth) throws Exception {
    auth.userDetailsService(customUserDetailsService).passwordEncoder(encoder());
}
```

告诉 Security："查用户用我写的 `CustomUserDetailsService`，密码比对用 `BCryptPasswordEncoder`"。这样登录时，Security 会调我们的 `loadUserByUsername` 拿到用户信息。

### 6.4 HTTP 安全策略（核心）

```java
@Override
protected void configure(HttpSecurity http) throws Exception {
    http.cors()                                              // 开启 CORS
        .and().csrf().disable()                              // 关闭 CSRF（前后端分离不需要）
        .formLogin().disable()                               // 关闭默认登录页
        .httpBasic().disable()                               // 关闭 HTTP Basic

        .authorizeRequests()
        .anyRequest().authenticated()                        // 所有请求都要登录
        .anyRequest()
        .access("@rbacAuthorityService.hasPermission(request,authentication)")  // 动态鉴权

        .and().logout().disable()                            // 登出自己实现
        .sessionManagement()
        .sessionCreationPolicy(SessionCreationPolicy.STATELESS)  // 无状态，不用 Session

        .and().exceptionHandling()
        .accessDeniedHandler(accessDeniedHandler);           // 权限不足的处理

    http.addFilterBefore(jwtAuthenticationFilter, UsernamePasswordAuthenticationFilter.class);
}
```

逐行理解：

- **关闭 CSRF**：CSRF 防御依赖 Session + Cookie，前后端分离用 JWT 不需要它。
- **关闭 formLogin / httpBasic**：默认的登录页和弹窗认证都不要，我们用自己的 `AuthController` 处理登录。
- **`anyRequest().authenticated()`**：兜底规则，没明确放行的都要登录。
- **`@rbacAuthorityService.hasPermission(...)`**：SpEL 表达式，调用我们写的 Bean 做动态权限校验。这是 RBAC 的入口。
- **`STATELESS`**：不创建 Session，完全靠 JWT，符合无状态认证。
- **`addFilterBefore`**：把 JWT 过滤器插到 `UsernamePasswordAuthenticationFilter` 之前，让每个请求先经过 JWT 解析。

### 6.5 白名单（WebSecurity）

```java
@Override
public void configure(WebSecurity web) {
    WebSecurity and = web.ignoring().and();
    customConfig.getIgnores().getGet().forEach(url -> and.ignoring().antMatchers(HttpMethod.GET, url));
    // ... 对 POST/PUT/DELETE/... 逐个放行
    customConfig.getIgnores().getPattern().forEach(url -> and.ignoring().antMatchers(url));
}
```

`WebSecurity.ignoring()` 配置的请求**完全跳过 Security 过滤链**，连 JWT 过滤器都不进。适合登录、登出这种本来就还没登录的接口。与 `HttpSecurity.permitAll()` 的区别：后者仍走过滤链只是不拦截，前者直接绕过。

---

## 七、JWT 工具类 JwtUtil：token 的生老病死

`util/JwtUtil.java` 是 JWT 的核心，封装了生成、解析、失效三个操作。

### 7.1 生成 JWT

```java
public String createJWT(Boolean rememberMe, Long id, String subject, List<String> roles, Collection<? extends GrantedAuthority> authorities) {
    Date now = new Date();
    JwtBuilder builder = Jwts.builder()
        .setId(id.toString())              // JWT ID（用户id）
        .setSubject(subject)               // 主体（用户名）
        .setIssuedAt(now)                  // 签发时间
        .signWith(SignatureAlgorithm.HS256, jwtConfig.getKey())  // 签名
        .claim("roles", roles)             // 自定义声明：角色
        .claim("authorities", authorities); // 自定义声明：权限

    Long ttl = rememberMe ? jwtConfig.getRemember() : jwtConfig.getTtl();
    if (ttl > 0) {
        builder.setExpiration(DateUtil.offsetMillisecond(now, ttl.intValue()));
    }

    String jwt = builder.compact();
    // 关键：把 JWT 存进 Redis，设置同样的过期时间
    stringRedisTemplate.opsForValue().set(Consts.REDIS_JWT_KEY_PREFIX + subject, jwt, ttl, TimeUnit.MILLISECONDS);
    return jwt;
}
```

**JWT 三段式**：生成出来的 token 长这样 `xxx.yyy.zzz`，分别是 Header（算法）、Payload（载荷，含 subject/roles 等）、Signature（签名）。前两段是 Base64 编码可解，第三段用密钥签名防篡改。

**为什么存 Redis？** 这是本模块的精髓。纯 JWT 有个硬伤：**一旦签发就无法撤销**——token 在过期前一直有效，用户"退出登录"也没用。把 token 存 Redis 后：

- 退出登录 = 删 Redis 里的 token
- 踢人下线 = 删 Redis 里的 token
- 同一用户单点登录 = 新登录覆盖旧 token，旧 token 在 Redis 里对不上，失效

### 7.2 解析 JWT

```java
public Claims parseJWT(String jwt) {
    try {
        Claims claims = Jwts.parser().setSigningKey(jwtConfig.getKey()).parseClaimsJws(jwt).getBody();
        String username = claims.getSubject();
        String redisKey = Consts.REDIS_JWT_KEY_PREFIX + username;

        // 校验1：Redis 里是否还有这个 token（没有=已退出/被踢）
        Long expire = stringRedisTemplate.getExpire(redisKey, TimeUnit.MILLISECONDS);
        if (Objects.isNull(expire) || expire <= 0) {
            throw new SecurityException(Status.TOKEN_EXPIRED);
        }

        // 校验2：Redis 里的 token 和请求带的是否一致（不一致=异地登录）
        String redisToken = stringRedisTemplate.opsForValue().get(redisKey);
        if (!StrUtil.equals(jwt, redisToken)) {
            throw new SecurityException(Status.TOKEN_OUT_OF_CTRL);
        }
        return claims;
    } catch (ExpiredJwtException e) { ... }  // 各种异常转成 SecurityException
}
```

解析做了**三重校验**：签名是否正确（防伪造）、Redis 是否存在（防已失效）、Redis 值是否匹配（防异地登录）。任一不过就抛异常。

### 7.3 失效 JWT（登出/踢人）

```java
public void invalidateJWT(HttpServletRequest request) {
    String jwt = getJwtFromRequest(request);
    String username = getUsernameFromJWT(jwt);
    stringRedisTemplate.delete(Consts.REDIS_JWT_KEY_PREFIX + username);
}
```

删掉 Redis 里的 token 即可。下次该用户请求时，解析时 Redis 校验失败，token 失效。

### 7.4 从请求头取 token

```java
public String getJwtFromRequest(HttpServletRequest request) {
    String bearerToken = request.getHeader("Authorization");
    if (StrUtil.isNotBlank(bearerToken) && bearerToken.startsWith("Bearer ")) {
        return bearerToken.substring(7);
    }
    return null;
}
```

前端请求时在 Header 里带 `Authorization: Bearer <token>`，后端去掉 `Bearer ` 前缀取 token。这是 JWT 的标准传递方式。

> 💡 前端类比：这就像前端用 axios 时设置 `axios.defaults.headers.common['Authorization'] = 'Bearer ' + token`，每个请求自动带 token。后端这里就是解析这个 header。

---

## 八、JWT 过滤器 JwtAuthenticationFilter：每个请求的"门卫"

`config/JwtAuthenticationFilter.java` 继承 `OncePerRequestFilter`（保证每请求只执行一次）：

```java
@Override
protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain filterChain) {
    // 1. 白名单直接放行
    if (checkIgnores(request)) {
        filterChain.doFilter(request, response);
        return;
    }

    // 2. 取 token
    String jwt = jwtUtil.getJwtFromRequest(request);

    if (StrUtil.isNotBlank(jwt)) {
        try {
            // 3. 解析 token 拿用户名，再查用户信息
            String username = jwtUtil.getUsernameFromJWT(jwt);
            UserDetails userDetails = customUserDetailsService.loadUserByUsername(username);

            // 4. 构造认证对象，塞进 SecurityContext
            UsernamePasswordAuthenticationToken authentication =
                new UsernamePasswordAuthenticationToken(userDetails, null, userDetails.getAuthorities());
            authentication.setDetails(new WebAuthenticationDetailsSource().buildDetails(request));
            SecurityContextHolder.getContext().setAuthentication(authentication);

            // 5. 放行
            filterChain.doFilter(request, response);
        } catch (SecurityException e) {
            ResponseUtil.renderJson(response, e);  // token 有问题，返回错误 JSON
        }
    } else {
        ResponseUtil.renderJson(response, Status.UNAUTHORIZED, null);  // 没 token，未登录
    }
}
```

**核心逻辑**：取 token → 解析用户 → 查权限 → 塞进 `SecurityContextHolder`（Security 的"当前用户"上下文）→ 放行。后续代码就能通过 `SecurityContextHolder` 拿到当前登录用户。

`checkIgnores()` 方法用 `AntPathRequestMatcher` 做 ant 风格路径匹配（如 `/test/*` 匹配 `/test/123`），判断当前请求是否在白名单。

> 💡 前端类比：这个过滤器就像 axios 的请求拦截器，每个请求发出前先做一道处理。区别是这里在服务端，是真正的安全门卫。

---

## 九、动态鉴权 RbacAuthorityService：RBAC 的执行者

`config/RbacAuthorityService.java` 的 `hasPermission` 方法是 SecurityConfig 里 `@rbacAuthorityService.hasPermission(...)` 调用的：

```java
public boolean hasPermission(HttpServletRequest request, Authentication authentication) {
    checkRequest(request);  // 先校验请求是否存在(404/405)

    Object userInfo = authentication.getPrincipal();
    if (userInfo instanceof UserDetails) {
        UserPrincipal principal = (UserPrincipal) userInfo;
        Long userId = principal.getId();

        // 查用户的所有角色 → 查这些角色的所有权限
        List<Role> roles = roleDao.selectByUserId(userId);
        List<Long> roleIds = roles.stream().map(Role::getId).collect(Collectors.toList());
        List<Permission> permissions = permissionDao.selectByRoleIdList(roleIds);

        // 只看按钮权限(接口)，过滤掉页面权限
        List<Permission> btnPerms = permissions.stream()
            .filter(p -> Objects.equals(p.getType(), Consts.BUTTON))  // type=2
            .filter(p -> StrUtil.isNotBlank(p.getUrl()))
            .filter(p -> StrUtil.isNotBlank(p.getMethod()))
            .collect(Collectors.toList());

        // 用 AntPathRequestMatcher 匹配当前请求是否在权限范围内
        for (Permission btnPerm : btnPerms) {
            AntPathRequestMatcher matcher = new AntPathRequestMatcher(btnPerm.getUrl(), btnPerm.getMethod());
            if (matcher.matches(request)) {
                return true;  // 匹配上，放行
            }
        }
        return false;  // 都没匹配，拒绝
    }
    return false;
}
```

**这是动态权限的核心**：权限不是写死在代码里（如 `@PreAuthorize("hasRole('ADMIN')")`），而是从数据库查。新增一个接口的权限控制，只需在 `sec_permission` 表加一行配置，不用改代码、不用重启。

`checkRequest()` 还做了个贴心的事：用 `RequestMappingHandlerMapping` 拿到所有注册的 URL，判断当前请求是否 404（路径不存在）或 405（方法不对），给出精确错误而非笼统的"权限不足"。

---

## 十、用户查询 CustomUserDetailsService 与 UserPrincipal

### 10.1 CustomUserDetailsService

```java
@Service
public class CustomUserDetailsService implements UserDetailsService {
    @Override
    public UserDetails loadUserByUsername(String usernameOrEmailOrPhone) {
        // 支持用户名/邮箱/手机号登录
        User user = userDao.findByUsernameOrEmailOrPhone(...).orElseThrow(...);
        List<Role> roles = roleDao.selectByUserId(user.getId());
        List<Long> roleIds = roles.stream().map(Role::getId).collect(Collectors.toList());
        List<Permission> permissions = permissionDao.selectByRoleIdList(roleIds);
        return UserPrincipal.create(user, roles, permissions);
    }
}
```

实现 Spring Security 的 `UserDetailsService` 接口。登录时 Security 调它查用户。这里支持**用户名/邮箱/手机号三种方式登录**（一个字段三用），查到用户后连带查角色和权限，封装成 `UserPrincipal`。

### 10.2 UserPrincipal

`vo/UserPrincipal.java` 实现 `UserDetails` 接口——这是 Spring Security 认定的"用户"标准。它把数据库的 `User` 实体转换成 Security 能理解的用户对象，包含：

- 基础信息（id、username、password 等）
- `roles`：角色名列表
- `authorities`：权限表达式列表（`SimpleGrantedAuthority`）
- 几个状态方法：`isEnabled()`（账号是否启用）、`isAccountNonExpired()` 等

`@JsonIgnore` 标在 password 字段上，防止密码被序列化成 JSON 返回给前端——这是个安全细节，容易漏。

---

## 十一、控制器层：登录、监控、测试

### 11.1 AuthController（登录/登出）

```java
@PostMapping("/login")
public ApiResponse login(@Valid @RequestBody LoginRequest loginRequest) {
    // AuthenticationManager 执行认证（调 UserDetailsService 查用户、BCrypt 比对密码）
    Authentication authentication = authenticationManager.authenticate(
        new UsernamePasswordAuthenticationToken(loginRequest.getUsernameOrEmailOrPhone(), loginRequest.getPassword()));

    SecurityContextHolder.getContext().setAuthentication(authentication);

    // 认证成功，生成 JWT
    String jwt = jwtUtil.createJWT(authentication, loginRequest.getRememberMe());
    return ApiResponse.ofSuccess(new JwtResponse(jwt));
}

@PostMapping("/logout")
public ApiResponse logout(HttpServletRequest request) {
    jwtUtil.invalidateJWT(request);  // 删 Redis 里的 token
    return ApiResponse.ofStatus(Status.LOGOUT);
}
```

登录流程：`authenticationManager.authenticate(...)` 会触发 `CustomUserDetailsService.loadUserByUsername` 查用户、`BCryptPasswordEncoder` 比对密码。认证通过后生成 JWT 返回。`@Valid` 触发 `LoginRequest` 上的 `@NotBlank` 校验。

### 11.2 MonitorController（在线用户/踢人）

```java
@GetMapping("/online/user")
public ApiResponse onlineUser(PageCondition pageCondition) {
    PageResult<OnlineUser> pageResult = monitorService.onlineUser(pageCondition);
    return ApiResponse.ofSuccess(pageResult);
}

@DeleteMapping("/online/user/kickout")
public ApiResponse kickoutOnlineUser(@RequestBody List<String> names) {
    if (names.contains(SecurityUtil.getCurrentUsername())) {
        throw new SecurityException(Status.KICKOUT_SELF);  // 不能踢自己
    }
    monitorService.kickout(names);
    return ApiResponse.ofSuccess();
}
```

`MonitorService.onlineUser` 从 Redis 分页查所有 token key（即在线用户），`kickout` 批量删 Redis 里的 token。`SecurityUtil.getCurrentUsername()` 从 `SecurityContextHolder` 拿当前操作者——这就是过滤器里塞进去的。

### 11.3 TestController（测试鉴权）

```java
@RestController
@RequestMapping("/test")
public class TestController {
    @GetMapping
    public ApiResponse list() { ... }      // 需要 btn:test:query 权限

    @PostMapping
    public ApiResponse add() { ... }       // 需要 btn:test:insert 权限

    @PutMapping("/{id}")
    public ApiResponse update(@PathVariable Long id) { ... }
}
```

这个控制器用来验证权限：admin 能访问所有，user 只能 GET/POST 不能 PUT。权限对应 `sec_permission` 表里的配置。

---

## 十二、其他组件

- **WebMvcConfig**：配置 CORS（`allowedOrigins("*")`），让前端跨域能访问。前后端分离必备。
- **RedisConfig**：自定义 `RedisTemplate` 的序列化，key 用 `StringRedisSerializer`，value 用 JSON 序列化。
- **SecurityHandlerConfig**：注册 `AccessDeniedHandler`，权限不足时返回统一 JSON 而非默认 403 页。
- **ApiResponse / Status**：统一响应体和状态码枚举，前面异常处理模块讲过类似设计。
- **ResponseUtil**：在过滤器里直接往 `HttpServletResponse` 写 JSON（因为过滤器里抛异常不走 `@ControllerAdvice`，必须自己写响应）。
- **RedisUtil**：用 `scan` 命令分页查 key（生产禁用 `keys`，会阻塞 Redis）。

---

## 十三、运行与验证

### 13.1 准备环境

1. MySQL 建库 `spring-boot-demo`，执行 `sql/security.sql`。
2. 启动 Redis（`redis-server`）。
3. 启动应用。

### 13.2 测试流程

```sh
# 1. 登录（admin）
curl -X POST http://localhost:8080/demo/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"usernameOrEmailOrPhone":"admin","password":"123456","rememberMe":false}'
# 返回 {"code":200,"data":{"token":"xxx.yyy.zzz"}}

# 2. 带 token 访问测试接口
curl http://localhost:8080/demo/test \
  -H "Authorization: Bearer xxx.yyy.zzz"
# admin 能访问，返回 测试列表查询

# 3. 查在线用户
curl http://localhost:8080/demo/api/monitor/online/user?currentPage=1&pageSize=10 \
  -H "Authorization: Bearer xxx.yyy.zzz"

# 4. 用 user 登录，访问监控接口 → 403 权限不足
```

### 13.3 验证单点登录

用 admin 在浏览器 A 登录拿到 token1，再在浏览器 B 用 admin 登录拿到 token2。此时用 token1 访问会失败（Redis 里已被 token2 覆盖），实现了"同一账号只能一处登录"。

---

## 十四、动手练习

1. **加一个权限**：在 `sec_permission` 表加一行"测试页面-删除"（`btn:test:delete`，`DELETE`，`/**/test`），给管理员角色关联，在 `TestController` 加 `@DeleteMapping`，验证 admin 能访问、user 不能。
2. **改密钥**：把 `jwt.config.key` 改成别的值，重启，观察旧 token 是否失效（签名对不上）。
3. **体验踢人**：admin 登录后，用 `MonitorController` 的 kickout 接口踢掉 user，再用 user 的 token 访问，验证失效。
4. **加记住我**：登录时 `rememberMe: true`，观察 Redis 里 token 的过期时间变成 7 天。
5. **加一个白名单**：在 `custom.config.ignores.pattern` 加 `/test/list`，重启，验证该路径无需 token 可访问。
6. **思考题**：如果 Redis 挂了，整个系统还能登录吗？为什么？（提示：解析 token 时要查 Redis）

---

## 十五、本模块知识点总结（结合实际开发详解）

权限是后端系统的核心安全防线，Spring Security + JWT + RBAC 是当前前后端分离项目的主流方案。下面把关键知识点放到真实开发里讲透。

### 15.1 RBAC 模型：为什么是用户-角色-权限三层？

**实际开发中怎么用？**

RBAC 几乎是所有权限系统的标配。它的核心价值是**解耦**：

- 用户换岗 → 只改"用户-角色"关联
- 权限调整 → 只改"角色-权限"关联
- 新增功能 → 加权限记录，给角色关联

**进阶：RBAC0/1/2/3**

- **RBAC0**：基础三层（本模块用的就是这层）
- **RBAC1**：角色有继承（经理继承员工的权限）
- **RBAC2**：角色有约束（互斥角色、最小权限）
- **RBAC3**：RBAC1 + RBAC2

大型系统会用 RBAC1，角色带父子关系，权限向下继承。本模块的 `parent_id` 字段就预留了树形结构能力。

**常见坑：**

- **权限粒度太细**：每个接口一个权限，权限表爆炸。最佳实践是按"资源+操作"建模（如 `user:read`、`user:write`），而不是 `user:selectById`、`user:selectByName`。
- **角色和权限混用**：有人喜欢直接给用户绑权限跳过角色。短期省事，长期维护灾难——用户多了改权限要逐个改。
- **数据权限被忽略**：RBAC 解决"能不能调这个接口"，但"能调不代表能看所有数据"。比如"查询订单"接口，销售员只能看自己的，主管能看全部门的——这叫**数据权限**，需要额外加过滤条件，RBAC 本身不管。实际项目常用 MyBatis 拦截器或 AOP 注解实现。

### 15.2 Spring Security：认证与授权两条线

**实际开发中怎么理解？**

Spring Security 把安全拆成两条线：

1. **认证（Authentication）**：你是谁？→ `AuthenticationManager` + `UserDetailsService`
2. **授权（Authorization）**：你能干啥？→ `AccessDecisionManager` + `RbacAuthorityService`

本模块的认证流程：登录时 `AuthController` 调 `AuthenticationManager.authenticate()`，它调 `CustomUserDetailsService.loadUserByUsername()` 查用户，用 `BCryptPasswordEncoder` 比对密码。授权流程：每个请求经过 `JwtAuthenticationFilter` 解析 token 拿到用户，再经 `RbacAuthorityService.hasPermission()` 查数据库权限做动态判断。

**Spring Security 的过滤链**

Security 本质是一串过滤器（`FilterChainProxy`），每个过滤器管一件事：`SecurityContextPersistenceFilter`（上下文）、`UsernamePasswordAuthenticationFilter`（表单登录）、`ExceptionTranslationFilter`（异常翻译）等。本模块把默认的表单登录全关了，插入自己的 `JwtAuthenticationFilter`，相当于"换芯"。

**常见坑：**

- **`WebSecurity.ignoring()` vs `HttpSecurity.permitAll()` 混淆**：前者完全跳过过滤链（连 JWT 过滤器都不进），适合登录接口；后者仍走过滤链只是放行，适合已登录但免鉴权的接口。用错会导致白名单接口仍被 JWT 过滤器拦截报 401。
- **`SecurityContextHolder` 是 ThreadLocal**：它是线程隔离的，异步线程里拿不到。跨线程要用 `DelegatingSecurityContextRunnable` 包装。
- **`WebSecurityConfigurerAdapter` 已废弃**：Spring Security 5.7+ 不再推荐继承它，改用 `SecurityFilterChain` Bean 的方式。本模块用的是 5.x 老写法，新项目要学新写法。

### 15.3 JWT：无状态认证的利与弊

**JWT 的优点：**

- 无状态：服务端不存 Session，天然支持水平扩展（多实例不需要 Session 共享）
- 跨域：放 Header 里，不依赖 Cookie，适合前后端分离、移动端
- 自包含：token 里有用户信息，减少查库

**JWT 的硬伤：无法主动失效**

这是 JWT 最大的问题。token 一旦签发，在过期前一直有效。用户改密码、退出登录、被踢下线，token 依然能用——这是纯 JWT 方案的致命伤。

**本模块的解法：JWT + Redis**

把 token 存一份到 Redis，解析时双重校验：Redis 有 + 值匹配。这样：

- 退出 = 删 Redis → token 失效
- 踢人 = 删 Redis → token 失效
- 单点登录 = 新 token 覆盖旧 token → 旧 token 失效

**这其实让 JWT 变成了"有状态"**——又回到依赖 Redis 了。那为什么不直接用 Session + Redis？因为 JWT 还保留了"自包含"的优势：解析 token 拿用户信息不用查库（Redis 只做存在性校验，不查用户详情）。实际开发中这是常见的折中。

**常见坑：**

- **密钥泄露 = 全军覆没**：`jwt.config.key` 是签名密钥，泄露后任何人都能伪造 token。生产环境必须用强随机密钥，从环境变量注入，不写死在 yml。本模块用 `xkcoding` 这种弱密钥只是演示。
- **token 放哪**：放 Header（推荐）、Cookie、URL 参数？放 Header 最安全（不易被 CSRF 利用），放 URL 参数会进日志泄露。
- **敏感信息别放 token**：JWT 的 Payload 是 Base64 可解的，放用户名可以，放密码/身份证就泄露了。
- **jjwt 版本**：0.9.x 是老版本，API 简单但有些安全问题；0.11+ 重构了 API，更安全。新项目用新版。

### 15.4 密码加密：BCrypt 是标配

**为什么用 BCrypt？**

- **加盐**：每次加密随机生成盐，同密码不同密文，防彩虹表攻击。
- **慢哈希**：计算慢（可调 cost），暴力破解成本高。
- **内置盐**：盐混在密文里（`$2a$10$...`），不用单独存盐字段。

**实际开发最佳实践：**

- 注册时加密存库，**永远不存明文密码**。
- 登录用 `BCryptPasswordEncoder.matches(明文, 密文)` 比对。
- 改密码 = 重新加密覆盖。
- **不要自己实现加密**，用 Spring Security 提供的 `BCryptPasswordEncoder`。

**常见坑：**

- 用 MD5/SHA 加密密码：这些是快速哈希，暴力破解成本低，已不安全。
- 加盐但盐写死：一个盐用到底，等于没加。BCrypt 每次随机盐才安全。
- 前端 MD5 后传后端：有人以为前端 MD5 一下更安全，其实反而让 MD5 成了"明文"，中间人抓到 MD5 直接用。正确做法是 HTTPS 传明文，后端 BCrypt。

### 15.5 动态权限：配置驱动 vs 注解驱动

**两种鉴权方式对比：**

| 方式 | 示例 | 特点 |
| --- | --- | --- |
| 注解驱动 | `@PreAuthorize("hasRole('ADMIN')")` | 简单直接，但权限写死在代码，改要重新部署 |
| 配置驱动（本模块） | 数据库存 URL+方法+权限，运行时匹配 | 灵活，改权限不改代码，但实现复杂 |

**本模块的配置驱动怎么做？**

`RbacAuthorityService.hasPermission()` 每次请求都查数据库，拿当前用户的所有权限，用 `AntPathRequestMatcher` 匹配请求 URL + 方法。匹配上就放行。

**实际开发的优化：**

本模块每次请求都查库，QPS 高时数据库扛不住。优化方向：

1. **缓存权限**：把用户权限查一次后放 Redis，设短过期时间（如 5 分钟），权限变更时主动清缓存。
2. **启动时加载全量 URL 映射**：`checkRequest` 里的 `allUrlMapping()` 其实可以启动时算一次缓存，不用每请求算。
3. **合并查询**：把"查角色→查权限"两次 SQL 合并成一次联表查询。

**常见坑：**

- `AntPathRequestMatcher` 的 `/**` 匹配多层路径，`/*` 只匹配一层。配权限时搞错会导致该拦的没拦。
- 权限表里的 URL 要和 Controller 实际路径对得上，配错了请求永远 403，排查困难。
- 动态权限每次查库，忘记加缓存，生产环境数据库被打满。

### 15.6 在线用户管理与踢人：Redis 的妙用

**本模块怎么实现？**

- 登录时 token 存 Redis，key 是 `security:jwt:用户名`。
- 在线用户列表 = 用 `scan` 分页查所有 `security:jwt:*` 的 key。
- 踢人 = 删对应 key。

**为什么用 scan 不用 keys？**

`keys security:jwt:*` 会遍历所有 key，Redis 是单线程的，key 多了会阻塞整个 Redis。`scan` 是游标式迭代，不阻塞，生产必用。

**实际开发的局限：**

本模块的"在线用户"其实只能看到"有 token 的用户"，无法感知用户是否真的在操作（token 没过期但用户已关浏览器）。要精确统计在线状态，需要前端定时心跳 + Redis 记录最后活跃时间。

**常见坑：**

- `scan` 返回的 key 数量是近似值，分页可能不准，需要业务上容忍。
- 踢人后旧 token 在 JWT 自身过期前理论上还能解出用户信息（只是 Redis 校验失败），要确保解析时先过 Redis 这关。

### 15.7 前后端分离的安全协作

**完整的安全链路是前后端配合的：**

| 环节 | 前端职责 | 后端职责 |
| --- | --- | --- |
| 登录 | 发账号密码 | 认证、发 token |
| 存 token | localStorage / 内存（不放 cookie 防 CSRF） | — |
| 带 token | axios 拦截器加 `Authorization` Header | — |
| 鉴权 | — | JWT 过滤器 + 动态权限 |
| 401 处理 | 清 token、跳登录页 | 返回 401 JSON |
| 路由守卫 | 按页面权限控制菜单/路由 | — |
| 按钮权限 | `v-permission` 控制按钮显隐 | — |

**关键原则：前端权限只是 UX，后端才是防线。** 前端隐藏按钮、路由守卫拦截，都只是提升体验，不能依赖它做安全——因为前端代码可被改、API 可被直接调用。每个后端接口必须独立鉴权，这是本模块 `RbacAuthorityService` 存在的意义。

**常见坑：**

- 前端把 token 存 localStorage：XSS 攻击能偷走。高安全场景用 HttpOnly Cookie + CSRF Token。
- 忘了处理 401：token 过期后前端不跳登录页，用户看到一堆报错。axios 响应拦截器要统一处理 401。
- CORS 配置 `allowedOrigins("*")` 同时还带凭证：浏览器不允许，要么指定域名要么不用 cookie。

---

> 📌 **学习建议**：权限模块是后端最有"工程感"的部分，也是面试重点。作为前端转后端，你要建立的认知是：**前端权限是体验，后端权限是安全**。学完本模块，建议重点理解三件事——RBAC 五张表为什么这么设计、JWT 为什么需要 Redis 配合、SecurityConfig 里那一长串配置每行在干什么。不用死记 API，理解"认证-授权-过滤链"的主线，遇到具体问题再查文档。这个模块代码量大，别被吓到，它本质就是"登录发 token → 每请求验 token → 查权限放行"三步，所有代码都在服务这三步。
