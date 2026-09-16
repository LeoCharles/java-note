# 51 - 分布式限流 Redis + Lua

> 对应项目模块：`demo-ratelimit-redis`
> 前置知识：已学完 `50-单机限流_RateLimitGuava`（Guava RateLimiter 单机限流）、`19-Redis缓存_CacheRedis`（Redis 基础）、`06-AOP请求日志_LogAop`（AOP 切面）
> 学习目标：理解为什么单机限流不够用，掌握 Redis + Lua 实现分布式限流的原理，能看懂并改写基于 ZSet 的滑动窗口限流方案。

---

## 一、本模块要解决什么问题？

### 1.1 单机限流的局限

上一篇 `demo-ratelimit-guava` 用 Guava 的 `RateLimiter` 实现了单机限流。但生产环境通常是**集群部署**——同一个服务部署多份，前面挂负载均衡（Nginx/网关）：

```
用户请求 → Nginx → [服务实例A, 服务实例B, 服务实例C]
```

单机限流的问题在于：每个实例**各自为政**。假设限流规则是"每秒 100 次"，部署了 3 个实例，实际能承受 300 次/秒，限流形同虚设。要真正限制"全局每秒 100 次"，必须有一个**所有实例共享的计数器**——Redis 天然适合干这个。

### 1.2 分布式限流的核心难点

把计数器放到 Redis 就够了？没那么简单。限流是典型的"读-判断-写"复合操作：

1. 读当前计数 `count`
2. 判断 `count + 1 > max` 是否超限
3. 没超则写入 `count + 1`

这三步必须**原子执行**。如果两个请求同时读到 `count=99`（max=100），都判断没超限，就都写 100，实际放过了 101 个——限流不准。这就是并发场景下的**竞态条件**。

> 💡 前端类比：这就像多个浏览器标签页同时操作同一个 localStorage 计数器，没有锁就会出现计数错乱。前端单线程不存在这个问题，但后端是多线程并发，必须处理。

### 1.3 本模块的方案：Redis + Lua

Redis 执行 Lua 脚本时，保证**整个脚本作为一个原子操作执行**，中间不会被其他命令打断。把"读-判断-写"逻辑写进 Lua 脚本，一次性发给 Redis 执行，就完美解决了竞态问题。本模块还用 Redis 的 **ZSet（有序集合）** 实现了更精确的**滑动窗口**限流，比固定窗口更平滑。

---

## 二、项目结构

```
demo-ratelimit-redis/
├── pom.xml
└── src/main/
    ├── java/com/xkcoding/ratelimit/redis/
    │   ├── SpringBootDemoRatelimitRedisApplication.java   # 启动类
    │   ├── annotation/
    │   │   └── RateLimiter.java              # 自定义限流注解
    │   ├── aspect/
    │   │   └── RateLimiterAspect.java        # AOP 切面（核心逻辑）
    │   ├── config/
    │   │   └── RedisConfig.java              # 加载 Lua 脚本为 Bean
    │   ├── controller/
    │   │   └── TestController.java           # 测试接口
    │   ├── handler/
    │   │   └── GlobalExceptionHandler.java  # 全局异常处理
    │   └── util/
    │       └── IpUtil.java                   # 获取真实 IP
    └── resources/
        ├── application.yml                    # Redis 配置
        └── scripts/redis/
            └── limit.lua                      # 限流 Lua 脚本（核心）
```

整体思路：**自定义注解 `@RateLimiter` 标记需要限流的接口 → AOP 切面拦截 → 执行 Redis Lua 脚本判断是否放行 → 超限则抛异常被全局异常处理器捕获返回友好提示**。这套"注解 + AOP + Lua"的组合是分布式限流的经典实现。

---

## 三、逐行拆解 `pom.xml`

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-web</artifactId>
</dependency>

<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-aop</artifactId>
</dependency>

<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-data-redis</artifactId>
</dependency>

<!-- 对象池，使用redis时必须引入 -->
<dependency>
    <groupId>org.apache.commons</groupId>
    <artifactId>commons-pool2</artifactId>
</dependency>

<dependency>
    <groupId>cn.hutool</groupId>
    <artifactId>hutool-all</artifactId>
</dependency>

<dependency>
    <groupId>org.projectlombok</groupId>
    <artifactId>lombok</artifactId>
    <optional>true</optional>
</dependency>
```

相比单机限流版，多了三个关键依赖：

| 依赖 | 作用 | 为什么需要 |
| --- | --- | --- |
| `spring-boot-starter-aop` | AOP 支持 | 切面拦截带 `@RateLimiter` 的方法 |
| `spring-boot-starter-data-redis` | Redis 客户端 | 共享计数器，实现分布式限流 |
| `commons-pool2` | 连接池 | Lettuce 用连接池时必须引入，否则 `lettuce.pool` 配置不生效 |

> 💡 前端类比：单机限流像每个前端实例自己用 `Map` 记请求次数；分布式限流像把计数器放到 Redis 这个"共享数据中心"，所有实例都来这儿读写。

---

## 四、逐行拆解配置文件 `application.yml`

```yaml
server:
  port: 8080
  servlet:
    context-path: /demo
spring:
  redis:
    host: localhost
    timeout: 10000ms
    lettuce:
      pool:
        max-active: 8
        max-wait: -1ms
        max-idle: 8
        min-idle: 0
```

- `spring.redis.host`：Redis 地址，生产环境换成 Redis 集群地址。
- `spring.redis.timeout: 10000ms`：连接超时，**必须带单位**（`ms`），这是 Spring Boot 2.x 的 `Duration` 类型要求。
- `lettuce.pool.*`：Lettuce 连接池参数。`max-active: 8` 表示最多 8 个连接，`max-wait: -1ms` 表示获取连接时无限等待（不报错）。

> ⚠️ 注意：配了 `lettuce.pool` 就**必须**引 `commons-pool2`，否则连接池配置不生效（Lettuce 会退化为非池化模式，但不报错，容易踩坑）。

---

## 五、核心：Lua 限流脚本 `limit.lua`

这是整个模块的灵魂。先看完整脚本，再逐行拆解：

```lua
-- 下标从 1 开始
local key = KEYS[1]
local now = tonumber(ARGV[1])
local ttl = tonumber(ARGV[2])
local expired = tonumber(ARGV[3])
-- 最大访问量
local max = tonumber(ARGV[4])

-- 清除过期的数据
redis.call('zremrangebyscore', key, 0, expired)

-- 获取 zset 中的当前元素个数
local current = tonumber(redis.call('zcard', key))
local next = current + 1

if next > max then
  -- 达到限流大小 返回 0
  return 0;
else
  -- 往 zset 中添加一个值、得分均为当前时间戳的元素
  redis.call("zadd", key, now, now)
  -- 每次访问均重新设置 zset 的过期时间，单位毫秒
  redis.call("pexpire", key, ttl)
  return next
end
```

### 5.1 Lua 脚本如何接收参数？

Redis 执行 Lua 脚本时，参数分两类：

- `KEYS[1], KEYS[2]...`：操作的 Redis 键名（Redis Cluster 下用于分片路由）
- `ARGV[1], ARGV[2]...`：任意参数值

本脚本接收 1 个 key 和 4 个 arg：

| 参数 | 含义 | 示例 |
| --- | --- | --- |
| `KEYS[1]` | 限流 key | `limit:com.xx.TestController.test1:192.168.1.5` |
| `ARGV[1]` | 当前时间戳（毫秒） | `1570000000000` |
| `ARGV[2]` | 窗口时长 ttl（毫秒） | `60000`（1分钟） |
| `ARGV[3]` | 过期时间戳 = now - ttl | `1569999940000` |
| `ARGV[4]` | 最大请求数 max | `10` |

### 5.2 为什么用 ZSet？—— 滑动窗口限流

Redis 的 **ZSet（有序集合）** 每个元素都有一个 `score`。本脚本把**每次请求的时间戳作为 score 和 value**存入 ZSet。这样 ZSet 里存的就是"时间窗口内的所有请求时间点"。

**滑动窗口 vs 固定窗口**：

- **固定窗口**：把时间切成固定区间（如每分钟一个计数器），1:00-1:01 计数器 A，1:01-1:02 计数器 B。问题：1:00:59 和 1:01:01 各来 100 次（max=100），虽然没超限，但 2 秒内放了 200 次——**临界突刺**。
- **滑动窗口**：以当前时刻为终点，往前推一个窗口（如 1 分钟）。只要这个窗口内请求数超 max 就拒绝。ZSet 天然实现这个——按 score（时间戳）范围查询就是滑动窗口。

> 💡 前端类比：固定窗口像"每小时清零一次计数器"，滑动窗口像"只统计最近 1 小时的请求"，后者更平滑。ZSet 的 `score` 就是时间戳，`zremrangebyscore` 删掉过期请求，`zcard` 统计窗口内请求数。

### 5.3 逐行拆解执行流程

**第一步：清除过期请求**

```lua
redis.call('zremrangebyscore', key, 0, expired)
```

`zremrangebyscore key min max` 删除 score 在 `[min, max]` 的元素。这里删除 score ≤ `expired`（即时间戳早于窗口起点）的请求——它们已经滑出窗口了。这就是"滑动"的体现。

**第二步：统计当前窗口请求数**

```lua
local current = tonumber(redis.call('zcard', key))
local next = current + 1
```

`zcard key` 返回 ZSet 元素个数，即当前窗口内已记录的请求数。`next` 是加上本次请求后的数量。

**第三步：判断是否超限**

```lua
if next > max then
  return 0          -- 超限，返回 0 表示拒绝
else
  redis.call("zadd", key, now, now)    -- 记录本次请求
  redis.call("pexpire", key, ttl)       -- 续期 key，防止内存泄漏
  return next                          -- 返回当前计数，表示放行
end
```

- 超限：直接返回 `0`，**不写入** ZSet（拒绝的请求不占名额）。
- 未超限：`zadd` 把当前时间戳存入 ZSet，`pexpire` 给 key 设过期时间（防止限流 key 永久残留占用内存），返回当前计数。

### 5.4 为什么 Lua 能保证原子性？

Redis 是**单线程**执行命令的。执行 Lua 脚本期间，Redis 不会插入执行其他任何命令——整个脚本作为一个不可分割的整体运行。所以"清除过期 → 统计 → 判断 → 写入"四步之间，不会有其他请求插队读到中间状态。这就是用 Lua 而不是"Java 里先读再写"的根本原因。

---

## 六、加载 Lua 脚本：`RedisConfig.java`

```java
@Configuration
public class RedisConfig {
    @Bean
    @SuppressWarnings("unchecked")
    public RedisScript<Long> limitRedisScript() {
        DefaultRedisScript redisScript = new DefaultRedisScript<>();
        redisScript.setScriptSource(new ResourceScriptSource(new ClassPathResource("scripts/redis/limit.lua")));
        redisScript.setResultType(Long.class);
        return redisScript;
    }
}
```

- 把 `limit.lua` 文件加载成一个 `RedisScript<Long>` Bean，注入到切面里复用。
- `ClassPathResource("scripts/redis/limit.lua")`：从 classpath 读取脚本文件。
- `setResultType(Long.class)`：指定脚本返回值类型，Spring 会自动转换 Lua 返回的数字为 Java `Long`。
- 做成 `@Bean` 而不是每次执行时读文件，是因为 Spring 会用 **EVALSHA** 优化：首次执行用 `EVAL` 加载脚本并缓存 SHA1，后续用 `EVALSHA` 只传哈希值，省带宽。

> 💡 前端类比：这像把一段 SQL 预编译成 PreparedStatement 缓存起来，后续只传参数不传 SQL 全文。

---

## 七、自定义限流注解 `RateLimiter.java`

```java
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
@Documented
public @interface RateLimiter {
    long DEFAULT_REQUEST = 10;

    @AliasFor("max") long value() default DEFAULT_REQUEST;
    @AliasFor("value") long max() default DEFAULT_REQUEST;
    String key() default "";
    long timeout() default 1;
    TimeUnit timeUnit() default TimeUnit.MINUTES;
}
```

逐个属性看：

| 属性 | 含义 | 默认值 |
| --- | --- | --- |
| `value` / `max` | 窗口内最大请求数（两者互为别名） | 10 |
| `key` | 限流 key 前缀，空则用类名+方法名 | `""` |
| `timeout` | 窗口时长 | 1 |
| `timeUnit` | 时间单位 | 分钟 |

### 7.1 `@AliasFor` —— 注解属性互为别名

`value` 和 `max` 互为别名，用 `@AliasFor` 关联。这样 `@RateLimiter(value = 5)` 和 `@RateLimiter(max = 5)` 效果一样，方便书写。

> ⚠️ 注释里特别强调：用了 `@AliasFor` 后，**必须用 `AnnotationUtils.findAnnotation()` 获取注解**，而不能用 JDK 原生的 `method.getAnnotation()`。后者拿不到别名映射后的值。这是 Spring 注解处理的一个关键细节。

### 7.2 元注解说明

- `@Target(ElementType.METHOD)`：只能标在方法上。
- `@Retention(RetentionPolicy.RUNTIME)`：运行时保留（AOP 反射读取必须用 RUNTIME）。
- `@Documented`：生成 javadoc 时包含。

> 💡 前端类比：自定义注解像自定义装饰器（如 React 的 `@observable`、Angular 的 `@Component`），元注解决"能标在哪、保留多久"。

---

## 八、AOP 切面 `RateLimiterAspect.java`（核心逻辑）

这是把"注解 → Lua 脚本 → Redis"串起来的中枢。

```java
@Slf4j
@Aspect
@Component
@RequiredArgsConstructor(onConstructor_ = @Autowired)
public class RateLimiterAspect {
    private final static String SEPARATOR = ":";
    private final static String REDIS_LIMIT_KEY_PREFIX = "limit:";
    private final StringRedisTemplate stringRedisTemplate;
    private final RedisScript<Long> limitRedisScript;
```

- `@Aspect`：标记为切面。
- `@Component`：注册成 Bean。
- `@RequiredArgsConstructor(onConstructor_ = @Autowired)`：Lombok 生成构造器并加 `@Autowired`，实现构造器注入 `StringRedisTemplate` 和 `RedisScript`。

### 8.1 切点：拦截带 `@RateLimiter` 的方法

```java
@Pointcut("@annotation(com.xkcoding.ratelimit.redis.annotation.RateLimiter)")
public void rateLimit() {}
```

切点表达式 `@annotation(...)` 匹配所有标注了 `@RateLimiter` 的方法。

### 8.2 环绕通知：限流判断主流程

```java
@Around("rateLimit()")
public Object pointcut(ProceedingJoinPoint point) throws Throwable {
    MethodSignature signature = (MethodSignature) point.getSignature();
    Method method = signature.getMethod();
    RateLimiter rateLimiter = AnnotationUtils.findAnnotation(method, RateLimiter.class);
    if (rateLimiter != null) {
        String key = rateLimiter.key();
        if (StrUtil.isBlank(key)) {
            key = method.getDeclaringClass().getName() + StrUtil.DOT + method.getName();
        }
        key = key + SEPARATOR + IpUtil.getIpAddr();

        long max = rateLimiter.max();
        long timeout = rateLimiter.timeout();
        TimeUnit timeUnit = rateLimiter.timeUnit();
        boolean limited = shouldLimited(key, max, timeout, timeUnit);
        if (limited) {
            throw new RuntimeException("手速太快了，慢点儿吧~");
        }
    }
    return point.proceed();
}
```

流程：

1. **取注解**：用 `AnnotationUtils.findAnnotation`（而非 `getAnnotation`，因有 `@AliasFor`）。
2. **构造 key**：若用户没指定 `key`，用"类名.方法名"做前缀；再拼上请求者 IP，形成 `类名.方法名:IP`。这样**每个 IP 对每个接口有独立配额**。
3. **调 Lua 判断**：`shouldLimited(...)` 执行脚本，返回 `true` 表示超限。
4. **超限抛异常**：抛 `RuntimeException`，由全局异常处理器捕获。未超限则 `point.proceed()` 放行执行原方法。

> ⚠️ 代码里有个 TODO 注释：用 IP 做 key 在**局域网多用户共用一个出口 IP** 时会把所有人当成一个人限流。生产环境应加上用户 ID 或方法参数来细化 key。

### 8.3 执行 Lua 脚本

```java
private boolean shouldLimited(String key, long max, long timeout, TimeUnit timeUnit) {
    key = REDIS_LIMIT_KEY_PREFIX + key;
    long ttl = timeUnit.toMillis(timeout);
    long now = Instant.now().toEpochMilli();
    long expired = now - ttl;
    Long executeTimes = stringRedisTemplate.execute(
        limitRedisScript,
        Collections.singletonList(key),
        now + "", ttl + "", expired + "", max + ""
    );
    if (executeTimes != null) {
        if (executeTimes == 0) {
            log.error("【{}】在单位时间 {} 毫秒内已达到访问上限，当前接口上限 {}", key, ttl, max);
            return true;
        } else {
            log.info("【{}】在单位时间 {} 毫秒内访问 {} 次", key, ttl, executeTimes);
            return false;
        }
    }
    return false;
}
```

关键点：

- `REDIS_LIMIT_KEY_PREFIX + key`：最终 key 形如 `limit:类名.方法名:IP`，加统一前缀便于 Redis 运维排查。
- `timeUnit.toMillis(timeout)`：统一转毫秒，因为 Lua 里用毫秒时间戳计算。
- `expired = now - ttl`：窗口起点时间戳。
- `stringRedisTemplate.execute(script, keys, args...)`：执行 Lua 脚本。`Collections.singletonList(key)` 是 KEYS 列表，后面是 ARGV。
- **参数必须转 String**：`now + ""` 把 Long 转字符串。注释解释了原因——`StringRedisTemplate` 的序列化器是 String，传 Long 会报 `java.lang.Long cannot be cast to java.lang.String`。
- 返回值 `0` 表示超限（拒绝），其他正数表示当前窗口内第几次访问（放行）。

---

## 九、获取真实 IP `IpUtil.java`

```java
public static String getIpAddr() {
    HttpServletRequest request = ((ServletRequestAttributes) RequestContextHolder.getRequestAttributes()).getRequest();
    String ip = null;
    ip = request.getHeader("x-forwarded-for");
    if (StrUtil.isEmpty(ip) || UNKNOWN.equalsIgnoreCase(ip)) {
        ip = request.getHeader("Proxy-Client-IP");
    }
    // ... 依次尝试多个代理头 ...
    if (StrUtil.isEmpty(ip) || UNKNOWN.equalsIgnoreCase(ip)) {
        ip = request.getRemoteAddr();
    }
    // 多级代理时取第一个 IP
    if (!StrUtil.isEmpty(ip) && ip.length() > MAX_LENGTH) {
        if (ip.indexOf(StrUtil.COMMA) > 0) {
            ip = ip.substring(0, ip.indexOf(StrUtil.COMMA));
        }
    }
    return ip;
}
```

**为什么要这么麻烦？** 因为生产环境几乎都有反向代理（Nginx），`request.getRemoteAddr()` 拿到的是代理服务器的 IP（都是同一个），而不是真实用户 IP。所以要从 HTTP 头里取：

| Header | 代理软件 |
| --- | --- |
| `x-forwarded-for` | Nginx、Squid 等标准代理 |
| `Proxy-Client-IP` | Apache HTTP Server |
| `WL-Proxy-Client-IP` | WebLogic |
| `HTTP_CLIENT_IP` / `HTTP_X_FORWARDED_FOR` | 某些代理 |

多级代理时 `x-forwarded-for` 是一串 IP（`client, proxy1, proxy2`），取第一个就是真实客户端 IP。

> 💡 前端类比：这就像前端从 `X-Real-IP` 头取真实 IP，而不是用 `request.connection.remoteAddress`（那是代理的地址）。

> ⚠️ 安全坑：`x-forwarded-for` 可被伪造。生产环境应在可信代理（Nginx）层覆盖该头，或用 `X-Real-IP`（Nginx 配置 `proxy_set_header X-Real-IP $remote_addr`）。

---

## 十、测试接口与全局异常处理

### 10.1 `TestController.java`

```java
@RestController
public class TestController {

    @RateLimiter(value = 5)
    @GetMapping("/test1")
    public Dict test1() {
        log.info("【test1】被执行了。。。。。");
        return Dict.create().set("msg", "hello,world!").set("description", "别想一直看到我，不信你快速刷新看看~");
    }

    @GetMapping("/test2")
    public Dict test2() { ... }   // 无限流

    @RateLimiter(value = 2, key = "测试自定义key")
    @GetMapping("/test3")
    public Dict test3() { ... }   // 自定义 key，1分钟最多 2 次
}
```

- `/test1`：默认 1 分钟最多 5 次（`value=5`，timeout 默认 1 分钟）。
- `/test2`：无限流，作为对照。
- `/test3`：自定义 key，1 分钟最多 2 次。

### 10.2 `GlobalExceptionHandler.java`

```java
@RestControllerAdvice
public class GlobalExceptionHandler {
    @ExceptionHandler(RuntimeException.class)
    public Dict handler(RuntimeException ex) {
        return Dict.create().set("msg", ex.getMessage());
    }
}
```

切面超限时抛 `RuntimeException("手速太快了，慢点儿吧~")`，这里统一捕获，返回 `{"msg": "手速太快了，慢点儿吧~"}`，而不是让用户看到 Spring 默认的错误页。

> 💡 这就是 `07-统一异常处理_ExceptionHandler` 模块讲过的 `@RestControllerAdvice` + `@ExceptionHandler` 模式的应用。

---

## 十一、运行与验证

### 11.1 准备 Redis

```sh
docker run -d --name redis -p 6379:6379 redis
```

### 11.2 启动并测试

```sh
mvn spring-boot:run
```

**测试 `/test1`（1分钟限5次）**：快速刷新 6 次 `http://localhost:8080/demo/test1`：

- 前 5 次：正常返回 `{"msg":"hello,world!","description":"别想一直看到我..."}`
- 第 6 次：返回 `{"msg":"手速太快了，慢点儿吧~"}`

**观察 Redis**：用 `redis-cli` 连上，`keys limit:*` 能看到限流 key，`zrange limit:com.xkcoding...test1:你的IP 0 -1 withscores` 能看到 ZSet 里存的时间戳。

**测试 `/test2`**：无限流，随便刷都返回正常。

**测试 `/test3`（自定义key，限2次）**：刷新 3 次，第 3 次被拒。

---

## 十二、动手练习

1. **改限流规则**：把 `/test1` 改成 `@RateLimiter(value = 3, timeout = 10, timeUnit = TimeUnit.SECONDS)`（10秒限3次），验证滑动窗口效果。
2. **观察 ZSet**：限流触发后，用 `redis-cli` 的 `ZRANGE key 0 -1 WITHSCORES` 查看 ZSet 内容，理解 score 就是时间戳。
3. **加用户维度**：修改切面，让 key 拼上当前登录用户 ID（可从 SecurityContext 或 token 取），实现"每个用户独立配额"。
4. **换成固定窗口**：把 Lua 脚本改成用 `INCR` + `EXPIRE` 实现固定窗口限流，对比和滑动窗口的差异（故意制造临界突刺测试）。
5. **返回限流信息**：超限时返回剩余可用次数和重置时间（提示：Lua 脚本可以返回更多信息，切面里解析）。
6. **集群验证**：启动两个实例（端口 8080、8081），都用同一个 Redis，从两个实例交替请求 `/test1`，验证共享计数（单机限流做不到）。

---

## 十三、本模块知识点总结（结合实际开发详解）

分布式限流是高并发系统的第一道防线。下面把核心知识点放到真实开发场景里讲透。

### 13.1 单机限流 vs 分布式限流：怎么选？

**实际开发中的判断标准：**

| 维度 | 单机限流（Guava RateLimiter） | 分布式限流（Redis + Lua） |
| --- | --- | --- |
| 部署方式 | 单实例 | 集群多实例 |
| 计数器位置 | 进程内存 | Redis 共享存储 |
| 性能 | 极高（无网络开销） | 较高（多一次 Redis 往返） |
| 准确性 | 单机准确，全局不准 | 全局准确 |
| 依赖 | 无 | 依赖 Redis 可用性 |
| 适用场景 | 单机服务、限流精度要求不高 | 集群部署、需全局精确限流 |

**最佳实践：**

- **网关层限流**：在 Nginx/Spring Cloud Gateway 统一限流，挡在业务服务前面，用分布式限流。
- **服务内兜底**：即使网关限流了，核心服务内部也可加单机限流做兜底（防御网关被绕过的情况）。
- **按需选择**：不是所有接口都需要分布式限流。只对真正有并发压力的接口（如秒杀、登录、短信发送）加，普通查询接口加限流反而增加 Redis 负担。

**常见坑：** 所有接口都加分布式限流，导致 Redis 压力骤增。限流本身是为了保护系统，别让限流成为新的瓶颈。

### 13.2 为什么必须用 Lua 脚本？—— 原子性是底线

**实际开发中常见的错误写法（有竞态）：**

```java
// ❌ 错误：读和写分离，并发下不准
Long count = redis.opsForValue().increment(key);  // 读+1
if (count == 1) redis.expire(key, 60);            // 首次设过期
if (count > max) {                                // 判断
    return "限流";
}
```

这段代码的问题：`increment`、`expire`、判断是分开的命令，并发下可能出现：A 请求 `increment` 得 100，B 请求 `increment` 得 101，但 A 还没设过期 key 就崩了，导致 key 永不过期。或者两个请求都判断"没超限"然后都放行。

**正确做法：** 把所有逻辑塞进一个 Lua 脚本，Redis 保证原子执行。这是分布式限流不可妥协的原则。

> 💡 前端类比：这就像数据库事务——要么全成功要么全失败，不能读到中间状态。Lua 脚本就是 Redis 的"事务"。

**最佳实践：** Lua 脚本要尽量**短小精悍**，只做必要的判断和写入。复杂逻辑放 Java 侧，脚本只负责"读-判-写"这一步。

### 13.3 滑动窗口 vs 固定窗口：精度与成本的权衡

本模块用 ZSet 实现滑动窗口，比固定窗口更精确，但成本更高。

| 维度 | 固定窗口（INCR+EXPIRE） | 滑动窗口（ZSet） |
| --- | --- | --- |
| 实现 | `INCR` 计数 + `EXPIRE` 过期 | ZSet 存每次请求时间戳 |
| 精度 | 有临界突刺 | 平滑，无突刺 |
| 内存 | 极小（一个计数器） | 较大（每次请求存一个元素） |
| 性能 | 高（O(1)） | 中（ZSet 操作 O(logN)） |
| 适用 | 普通接口限流 | 对平滑性要求高的场景 |

**实际开发选择：**

- 大多数场景用**固定窗口**就够了（实现简单、内存省），临界突刺的影响可接受。
- 对平滑性要求极高（如支付、秒杀）才用**滑动窗口**，但要评估 ZSet 内存占用——高 QPS 接口 ZSet 会快速膨胀。
- 折中方案：**滑动窗口日志**（记录最近 N 次请求时间，用 List 或 ZSet），定期清理。

**常见坑：** 滑动窗口在高 QPS 下 ZSet 元素暴涨。本脚本用 `pexpire` 给 key 设过期，且每次 `zremrangebyscore` 清理过期元素，缓解了这个问题，但极端高并发下仍需监控 ZSet 大小。

### 13.4 限流 key 的设计：粒度决定效果

本模块的 key 是 `类名.方法名:IP`，即"每个 IP 对每个接口独立限流"。实际开发中 key 设计有多种粒度：

| key 粒度 | 效果 | 适用场景 |
| --- | --- | --- |
| `接口:IP` | 每 IP 每接口独立配额 | 防止单用户刷某接口 |
| `接口`（全局） | 接口总配额 | 保护下游服务（如第三方 API） |
| `用户ID:接口` | 每用户每接口配额 | 登录用户场景 |
| `IP`（全局） | 每 IP 总配额 | 防爬虫、防刷 |

**最佳实践：**

- **多维度组合**：生产环境常组合多个维度，如"每 IP 每分钟 100 次" + "每用户每分钟 30 次"，分别用不同 key。
- **key 要有业务含义前缀**：如 `limit:api:user:123`，便于 Redis 运维排查和清理。
- **注意 key 粒度别太细**：如按"用户+接口+参数"限流，key 数量爆炸，Redis 内存扛不住。

**本模块的坑：** 用 IP 做 key 在 NAT/局域网下会把多用户合并成一个，代码 TODO 也指出了。生产环境应优先用用户 ID（已登录）或 token，IP 作为未登录场景的兜底。

### 13.5 `@AliasFor` 与 `AnnotationUtils`：注解处理的隐藏陷阱

本模块注解用 `@AliasFor` 让 `value` 和 `max` 互为别名，但注释强调"必须用 `AnnotationUtils` 获取"。

**为什么？** JDK 原生的 `method.getAnnotation(RateLimiter.class)` 不理解 `@AliasFor`，拿到的 `value()` 和 `max()` 是各自独立的默认值，别名映射不生效。Spring 的 `AnnotationUtils.findAnnotation()` 会处理别名关系，保证 `value` 和 `max` 值同步。

**实际开发最佳实践：**

- 用了 `@AliasFor` 的注解，**一律用 `AnnotationUtils`** 获取。
- 跨层继承的注解（如标在类上、方法上生效），用 `AnnotatedElementUtils.findMergedAnnotation()`，它支持 `@AliasFor` 跨层映射。
- 自定义注解时，属性名要语义清晰，别名用于提供简写（如 `value` 是简写，`max` 是全称）。

**常见坑：** 用了 `@AliasFor` 但用 `getAnnotation` 读取，导致拿到的值不对，限流规则失效，排查半天找不到原因。

### 13.6 Redis 不可用时限流怎么办？—— 降级策略

分布式限流依赖 Redis，Redis 挂了怎么办？这是个必须考虑的生产问题。

| 策略 | 行为 | 评价 |
| --- | --- | --- |
| **fail-open（放行）** | Redis 异常时放行请求 | 保护可用性，但限流失效 |
| **fail-close（拒绝）** | Redis 异常时拒绝所有请求 | 保护系统，但误伤正常用户 |
| **本地兜底** | Redis 异常时降级为单机限流 | 折中，推荐 |

**最佳实践：**

- 对**非核心接口**（如评论、点赞）用 fail-open，Redis 挂了也放行，别因限流拖垮可用性。
- 对**核心保护对象**（如第三方付费 API）用 fail-close，宁可拒绝也别打爆下游。
- 理想方案是 fail-open + 本地兜底：Redis 异常时切到 Guava 单机限流，至少有基本保护。

**常见坑：** 没做降级，Redis 一抖动，所有接口都返回限流错误，用户体验灾难。`shouldLimited` 里 `execute` 返回 null 时默认 `return false`（放行），其实就是一种 fail-open 兜底。

### 13.7 限流后的反馈：让用户知道为什么被拒

本模块超限时抛异常，全局处理器返回 `{"msg": "手速太快了，慢点儿吧~"}`。但生产环境应返回更友好的信息：

```json
{
  "code": 429,
  "message": "请求过于频繁，请稍后再试",
  "data": {
    "retryAfter": 30,        // 多少秒后可重试
    "limit": 100,           // 总配额
    "remaining": 0          // 剩余
  }
}
```

**最佳实践：**

- HTTP 状态码用 `429 Too Many Requests`（而非 500），符合规范。
- 返回 `Retry-After` 头，告诉客户端多久后重试。
- 前端配合：收到 429 时禁用按钮、显示倒计时，避免用户疯狂重试（重试本身又触发限流）。

> 💡 前端类比：这就像 axios 拦截器里判断 `error.response.status === 429`，弹出"操作太频繁"提示并禁用提交按钮 30 秒。前后端配合才能让限流体验不突兀。

---

> 📌 **学习建议**：分布式限流是"注解 + AOP + Lua"三件套的经典应用，这个模式在日志、缓存、权限等场景反复出现，务必吃透。重点理解两点：一是**为什么用 Lua**（原子性），二是**滑动窗口的 ZSet 实现**（score=时间戳）。另外养成习惯：任何依赖外部中间件（Redis）的逻辑，都要想"它挂了怎么办"，提前设计降级策略。下一篇 `52-HTTPS` 会转向传输层安全，和限流是不同维度的防护。
