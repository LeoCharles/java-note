# AOP 实战：日志、权限与缓存

前两篇学了 AOP 的概念、代理机制和通知类型。本篇用三个企业级实战场景把 AOP 用起来：统一操作日志、方法级权限校验、自定义缓存注解。学完这篇你就具备独立设计生产级切面的能力。

> 💡 AOP 最强大的地方不在于会用 Spring 提供的 `@Transactional`，而在于你能自己写出这种级别的注解。本篇的三个案例就是朝这个目标去的。

---

## 一、实战一：统一操作日志

### 1.1 需求

记录每个业务操作：谁、什么时候、调了什么方法、传了什么参数、花了多少时间、结果是成功还是失败。

### 1.2 自定义注解

```java
@Retention(RetentionPolicy.RUNTIME)
@Target(ElementType.METHOD)
public @interface OperationLog {
    String value();          // 操作描述，如 "创建订单"
    boolean recordArgs() default true;    // 是否记录参数
    boolean recordResult() default false; // 是否记录返回值
}
```

### 1.3 切面实现

```java
@Aspect
@Component
@Order(2)
@Slf4j
public class OperationLogAspect {

    @Around("@annotation(operationLog)")
    public Object around(ProceedingJoinPoint joinPoint, OperationLog operationLog)
            throws Throwable {
        // 1. 获取请求信息
        String operation = operationLog.value();
        String method = joinPoint.getSignature().toShortString();
        Object[] args = joinPoint.getArgs();
        String operator = getCurrentUser();  // 从 SecurityContext 或请求头获取

        // 2. 记录开始日志
        if (operationLog.recordArgs()) {
            log.info("[操作日志] 用户:{} | 操作:{} | 方法:{} | 参数:{}",
                    operator, operation, method, sanitizeArgs(args));
        } else {
            log.info("[操作日志] 用户:{} | 操作:{} | 方法:{}",
                    operator, operation, method);
        }

        long start = System.currentTimeMillis();
        Object result;
        try {
            // 3. 执行业务方法
            result = joinPoint.proceed();

            // 4. 记录成功日志
            long cost = System.currentTimeMillis() - start;
            if (operationLog.recordResult()) {
                log.info("[操作日志] 用户:{} | 操作:{} | 成功 | 耗时:{}ms | 结果:{}",
                        operator, operation, cost, sanitizeResult(result));
            } else {
                log.info("[操作日志] 用户:{} | 操作:{} | 成功 | 耗时:{}ms",
                        operator, operation, cost);
            }
            return result;

        } catch (Exception e) {
            // 5. 记录失败日志
            long cost = System.currentTimeMillis() - start;
            log.error("[操作日志] 用户:{} | 操作:{} | 失败 | 耗时:{}ms | 异常:{}",
                    operator, operation, cost, e.getMessage());
            throw e;  // 不吞异常
        }
    }

    private String getCurrentUser() {
        // 实际项目中从 SecurityContextHolder 或请求头中获取
        return "system";
    }

    /** 脱敏处理：过滤掉密码等敏感字段 */
    private String sanitizeArgs(Object[] args) {
        // 实际项目中反序列化并脱敏，这里简化
        return Arrays.toString(args)
                .replaceAll("password=[^,)]*", "password=****");
    }

    private String sanitizeResult(Object result) {
        if (result == null) return "null";
        // 大结果截断
        String str = result.toString();
        return str.length() > 200 ? str.substring(0, 200) + "..." : str;
    }
}
```

### 1.4 使用

```java
@Service
public class OrderService {

    @OperationLog("创建订单")
    public Order createOrder(CreateOrderRequest request) {
        // 这个方法会自动被日志切面包裹
        return orderDao.save(toOrder(request));
    }

    @OperationLog(value = "取消订单", recordResult = true)
    public void cancelOrder(Long orderId) {
        orderDao.updateStatus(orderId, "CANCELLED");
    }
}
```

**日志输出示例**：
```
[操作日志] 用户:admin | 操作:创建订单 | 方法:OrderService.createOrder(..) | 参数:[{userId=1, items=[{skuId=1001, qty=2}]}]
[操作日志] 用户:admin | 操作:创建订单 | 成功 | 耗时:156ms
```

---

## 二、实战二：方法级权限校验

### 2.1 需求

不同的接口需要不同的权限。不用在每个方法里写 `if (!hasPermission("xxx")) throw new 403`，而是用一个注解搞定。

### 2.2 自定义注解

```java
@Retention(RetentionPolicy.RUNTIME)
@Target(ElementType.METHOD)
public @interface RequirePermission {
    String value();                    // 权限编码，如 "order:create"
    String[] anyOf() default {};       // 满足任一即可（多个权限时）
    String message() default "权限不足";
}
```

### 2.3 切面实现

```java
@Aspect
@Component
@Order(1)   // 权限检查优先级最高，在日志之前
public class PermissionAspect {

    @Before("@annotation(requirePermission)")
    public void checkPermission(JoinPoint joinPoint, RequirePermission requirePermission) {
        String permission = requirePermission.value();
        String[] anyOf = requirePermission.anyOf();

        // 获取当前用户的权限列表
        Set<String> userPermissions = getCurrentUserPermissions();

        // 检查权限
        boolean hasPermission = false;
        if (anyOf.length > 0) {
            // 满足任一即可
            hasPermission = Arrays.stream(anyOf).anyMatch(userPermissions::contains);
        } else {
            // 必须有指定权限
            hasPermission = userPermissions.contains(permission);
        }

        if (!hasPermission) {
            throw new AccessDeniedException(requirePermission.message());
        }
    }

    private Set<String> getCurrentUserPermissions() {
        // 实际项目中从 SecurityContext 或 JWT Token 中获取
        return Set.of("order:create", "order:view");
    }
}
```

### 2.4 使用

```java
@RestController
@RequestMapping("/orders")
public class OrderController {

    @PostMapping
    @RequirePermission("order:create")  // 有这个权限才能调
    public Result<Order> create(@RequestBody CreateOrderRequest request) {
        return Result.success(orderService.createOrder(request));
    }

    @DeleteMapping("/{id}")
    @RequirePermission(value = "order:delete",
                       message = "您没有删除订单的权限")
    public Result<Void> delete(@PathVariable Long id) {
        orderService.deleteOrder(id);
        return Result.success();
    }

    @GetMapping("/stats")   // 需要任一权限
    @RequirePermission(anyOf = {"report:view", "admin:all"})
    public Result<StatsVO> stats() {
        return Result.success(orderService.getStats());
    }
}
```

---

## 三、实战三：自定义缓存注解

### 3.1 需求

不引入 Redis 也能给方法加缓存——仿照 `@Cacheable` 做一个简易版的 `@LocalCache`。

### 3.2 自定义注解

```java
@Retention(RetentionPolicy.RUNTIME)
@Target(ElementType.METHOD)
public @interface LocalCache {
    String key();              // 缓存 key，支持 SpEL 表达式
    long ttl() default 300;    // 过期时间（秒），默认 5 分钟
    TimeUnit unit() default TimeUnit.SECONDS;
    long maxSize() default 1000; // 最大缓存条目数
}
```

### 3.3 切面实现

```java
@Aspect
@Component
@Order(3)
@Slf4j
public class LocalCacheAspect {

    private final Cache<String, Object> cache = Caffeine.newBuilder()
            .maximumSize(1000)
            .expireAfterWrite(300, TimeUnit.SECONDS)
            .build();

    @Around("@annotation(localCache)")
    public Object cache(ProceedingJoinPoint joinPoint, LocalCache localCache)
            throws Throwable {
        // 1. 生成缓存 key
        String cacheKey = generateKey(localCache.key(), joinPoint);

        // 2. 查缓存
        Object cachedValue = cache.getIfPresent(cacheKey);
        if (cachedValue != null) {
            log.debug("[缓存命中] key={}", cacheKey);
            return cachedValue;
        }

        // 3. 缓存未命中 → 执行方法
        log.debug("[缓存未命中] key={}", cacheKey);
        Object result = joinPoint.proceed();

        // 4. 存入缓存
        if (result != null) {
            cache.put(cacheKey, result);
        }

        return result;
    }

    /** 生成缓存 key：支持简单 SpEL 表达式 */
    private String generateKey(String keyExpression, ProceedingJoinPoint joinPoint) {
        // 简化版 SpEL 解析：支持 #paramName 引用方法参数
        if (!keyExpression.contains("#")) {
            return keyExpression;
        }

        MethodSignature signature = (MethodSignature) joinPoint.getSignature();
        String[] paramNames = signature.getParameterNames();
        Object[] args = joinPoint.getArgs();

        String key = keyExpression;
        for (int i = 0; i < paramNames.length; i++) {
            key = key.replace("#" + paramNames[i], String.valueOf(args[i]));
        }
        return key;
    }
}
```

### 3.4 使用

```java
@Service
public class ProductService {

    @LocalCache(key = "hot_products", ttl = 600)  // 缓存 10 分钟
    public List<Product> getHotProducts() {
        System.out.println(">>> 从数据库查询热门商品");
        return productDao.findHotProducts();
    }

    @LocalCache(key = "product_#productId", ttl = 300)  // 按 ID 缓存
    public Product getProductById(Long productId) {
        System.out.println(">>> 从数据库查询商品：" + productId);
        return productDao.findById(productId);
    }
}
```

> 💡 这个 `@LocalCache` 就是 `@Cacheable` 的迷你版。理解了它，你就知道 Spring 缓存抽象（`@Cacheable`/`@CacheEvict`/`@CachePut`）的原理了——全是 AOP 的 `@Around` 实现。

---

## 四、生产级切面设计原则

### 4.1 try-catch 必须完整

```java
// ❌ 错误：proceed 的异常被吞了
@Around("...")
public Object around(ProceedingJoinPoint jp) {
    try {
        return jp.proceed();
    } catch (Exception e) {
        log.error("错误", e);  // 吞了异常！上层拿不到！
        return null;           // 返回值变成 null，NPE！
    } catch (Throwable e) {
        throw new RuntimeException(e);  // 包一层
    }
}

// ✅ 正确：该抛的必须抛
@Around("...")
public Object around(ProceedingJoinPoint jp) throws Throwable {
    try {
        return jp.proceed();
    } catch (Exception e) {
        log.error("错误", e);
        throw e;  // 原样抛出，让上层处理
    }
}
```

### 4.2 切面要尽量轻量

```java
// ❌ 错误：切面里查数据库
@Before("...")
public void log() {
    auditLogDao.save(...);  // 切面里同步写库，阻塞业务！
}

// ✅ 正确：异步或不影响主流程
@Before("...")
public void log() {
    asyncAuditService.record(...);  // 异步记录
}
```

### 4.3 注意切面顺序

```java
// 权限 → 限流 → 缓存 → 事务 → 日志
@Order(1) PermissionAspect   // 先看有没有权限
@Order(2) RateLimitAspect    // 再看有没有配额
@Order(3) CacheAspect        // 缓存命中直接返回
@Order(4) TransactionAspect  // 没命中走数据库（需要事务）
@Order(5) LogAspect          // 最后记录日志
```

---

## 💻 实战案例

### 案例：组合三个切面完成一个 API 请求的处理链

```java
@RestController
@RequestMapping("/api/orders")
@RequiredArgsConstructor
public class OrderController {
    private final OrderService orderService;

    @PostMapping
    @RequirePermission("order:create")          // – 切面1：权限
    @OperationLog("创建订单")                    // – 切面3：日志
    @LocalCache(key = "order_create_lock", ttl = 1)  // – 切面2：防重（同一秒内）
    public Result<Order> create(@Valid @RequestBody CreateOrderRequest request) {
        return Result.success(orderService.createOrder(request));
    }
}
```

**请求处理链**：

```
HTTP 请求到达 /api/orders
    │
    ▼ @Order(1) PermissionAspect           → 检查 "order:create" 权限，没有直接抛 403
    │
    ▼ @Order(2) LocalCacheAspect           → 检查 "order_create_lock" 缓存（1秒防重）
    │
    ▼ @Order(3) OperationLogAspect         → 记录请求日志
    │
    ▼ OrderService.createOrder(request)
    │
    ▼ OperationLogAspect                   → 记录成功/失败日志
    │
    ▼ Controller 返回 Result<Order>
```

---

## 🎯 面试高频

### Q1：如何自己实现一个类似 @Transactional 的自定义注解？

**答**：三步——
1. 定义注解（`@Retention(RUNTIME)` + `@Target(METHOD)`）
2. 写切面类（`@Aspect` + `@Component`），用 `@Around("@annotation(你的注解)")`
3. 在 `@Around` 方法中写切面逻辑（`proceed` 前做什么、`proceed` 后做什么、异常时怎么处理）

### Q2：AOP 切面在真实项目中有哪些典型应用？

**答**：操作日志、权限校验、缓存处理、接口限流、分布式锁、参数校验（配合 @Valid）、返回值统一包装、异常统一处理、请求重试——这些都是横切逻辑，用 AOP 比在每个方法里写要优雅得多。

---

## 📌 在 Spring Boot 中

- Spring Boot 提供了 `@Transactional`、`@Cacheable`、`@Async` 等 AOP 注解，原理和本章三个自定义注解完全一样
- 自定义 AOP 注解是 Spring Boot 项目中最常用的扩展手段——几乎每个团队都有一组自己的 `@Xxx` 注解
- 切面中需要获取 HttpServletRequest 时，不要在切面类上标注型注入，通过 `RequestContextHolder.getRequestAttributes()` 获取，避免与请求作用域相关的问题

---

## 本章小结

| 知识点 | 要点 |
| :--- | :--- |
| 操作日志切面 | @Around + 自定义注解，记录参数/返回值/耗时/异常 |
| 权限校验切面 | @Before，check 失败抛 AccessDeniedException |
| 缓存切面 | @Around，命中直接 return（不调 proceed），未命中执行后缓存 |
| 切面设计原则 | 异常必须原样抛出、切面逻辑要轻量、控制好 @Order 顺序 |
| 自定义注解 3 步 | 定义注解 → 写 @Aspect 切面 → @Around/@Before 绑定 @annotation |

---

## 学习建议

1. **把三个案例都敲一遍**。不需要完整的业务代码，就写切面 + 注解 + 一个简单的 Service，验证切面是否生效。
2. **从第一个切面开始积累**。每个项目都应该有一套自己的 AOP 工具箱：`@OperationLog`、`@RequirePermission`、`@RateLimit`、`@DistributedLock`……这个工具箱是你作为后端开发的核心竞争力之一。
3. **不要过度切面化**。如果一个逻辑只在一个方法里用到，就别抽切面——直接写代码比切面更直观。切面适用于"至少 3 个方法都要用"的横切逻辑。