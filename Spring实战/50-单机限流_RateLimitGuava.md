# 50 - 单机限流保护 API（Guava RateLimiter）

> 对应项目模块：`demo-ratelimit-guava`
> 前置知识：已学完 AOP 模块（`06-AOP请求日志_LogAop`），了解自定义注解 + 切面的基本套路
> 学习目标：理解限流的意义与常见算法，掌握用 Guava RateLimiter + AOP 实现声明式限流，能独立为接口加限流保护。

---

## 一、本模块要解决什么问题？

### 1.1 为什么需要限流？

想象一个场景：你写了一个查询用户信息的接口，正常情况下每秒几十次请求没问题。但某天有人写了个脚本，每秒发来一万次请求，你的数据库瞬间被拖垮，整个服务瘫痪——这就是**流量攻击**或**突发流量**。

限流（Rate Limiting）就是在请求到达业务逻辑之前，先控制住流量：超过阈值的请求直接拒绝（返回错误或提示"稍后再试"），保护后端服务不被压垮。

> 💡 前端类比：限流就像前端的 **节流（throttle）** 函数。`lodash.throttle(fn, 1000)` 保证一个函数一秒最多执行一次，多余的调用被丢弃。后端限流是同样的思想，只是作用在服务端接口上，而且通常用 QPS（每秒请求数）作为阈值。防抖（debounce）则是"等停止触发才执行"，和限流思想不同。

### 1.2 限流 vs 熔断 vs 降级

这三个常被混淆，先区分清楚：

| 概念 | 作用 | 触发条件 | 前端类比 |
| --- | --- | --- | --- |
| **限流** | 控制请求速率，超过阈值拒绝 | QPS 超标 | throttle 节流 |
| **熔断** | 下游服务故障时，主动切断调用，快速失败 | 下游错误率/超时超标 | try-catch 里直接返回兜底值 |
| **降级** | 服务不可用时返回简化/默认结果 | 资源紧张或依赖故障 | 图片加载失败显示占位图 |

本模块只讲**限流**，而且是**单机限流**（只保护当前这台服务器），用 Guava 的 RateLimiter 实现。

### 1.3 常见限流算法

理解算法才能选对工具。主流限流算法有四种：

**① 计数器算法（固定窗口）**

把时间分成固定窗口（如每秒一个窗口），窗口内每来一个请求计数 +1，超过阈值拒绝，窗口结束时清零。

缺点：有**临界突刺**问题。比如阈值 100/秒，在 0.9 秒时来了 100 个，1.0 秒（新窗口）又来 100 个——0.9~1.0 这 0.1 秒内实际通过了 200 个请求，瞬间流量翻倍。

**② 滑动窗口算法**

把窗口切细（比如 1 秒分成 10 个 100ms 的格子），窗口随时间滑动，统计当前时刻往前 1 秒内的总请求数。解决了临界突刺问题，Sentinel 用的就是滑动窗口。

**③ 漏桶算法（Leaky Bucket）**

请求像水倒进漏桶，桶以固定速率漏水（处理请求）。桶满了则新请求被丢弃。特点是**流量整形**：不管来多猛的请求，出去的速率恒定。适合需要平滑流量的场景。

**④ 令牌桶算法（Token Bucket）**

以固定速率往桶里放令牌，请求来了先拿令牌，拿到才处理，拿不到就等或拒绝。桶满了多余的令牌丢弃。特点是允许一定程度的**突发流量**：桶里攒的令牌可以应对短时高峰。**Guava RateLimiter 用的就是令牌桶。**

> 💡 前端类比：令牌桶像游戏里的"体力值"——每 5 分钟恢复 1 点体力，做任务消耗体力。你平时攒着不用，攒到 10 点时可以连续做 10 个任务（突发）；但长期看，你 5 分钟最多做 1 个任务（平均速率）。漏桶则像水龙头滴水，不管你接水的速度，它就是恒速滴。

**令牌桶 vs 漏桶的核心区别**：令牌桶允许突发（攒令牌），漏桶强制匀速。大多数接口限流用令牌桶更合适。

---

## 二、项目结构

```
demo-ratelimit-guava/
├── pom.xml
└── src/main/java/com/xkcoding/ratelimit/guava/
    ├── SpringBootDemoRatelimitGuavaApplication.java   # 启动类
    ├── annotation/
    │   └── RateLimiter.java                # 自定义限流注解
    ├── aspect/
    │   └── RateLimiterAspect.java          # 限流切面（核心）
    ├── controller/
    │   └── TestController.java             # 测试接口
    └── handler/
        └── GlobalExceptionHandler.java     # 全局异常处理
```

这个结构体现了"注解 + 切面"的经典声明式编程模式：

- `annotation/RateLimiter`：定义一个注解，标注在需要限流的接口上，声明限流参数（QPS、超时）。
- `aspect/RateLimiterAspect`：切面拦截带 `@RateLimiter` 的方法，执行限流逻辑。
- `controller/TestController`：用 `@RateLimiter` 标注接口，验证效果。
- `handler/GlobalExceptionHandler`：限流触发时抛异常，这里统一捕获返回友好提示。

> 💡 前端类比：这就像写一个自定义指令（Vue 的 `v-loading`）+ 全局拦截。注解是"标签"，切面是"拦截器"，业务代码只加注解，不关心限流细节——声明式编程，关注点分离。

---

## 三、逐行拆解 pom.xml

```xml
<dependencies>
    <!-- Web 起步依赖 -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-web</artifactId>
    </dependency>

    <!-- AOP 起步依赖：提供 @Aspect、切面代理支持 -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-aop</artifactId>
    </dependency>

    <!-- Hutool 工具类：用 Dict 构造返回结果 -->
    <dependency>
        <groupId>cn.hutool</groupId>
        <artifactId>hutool-all</artifactId>
    </dependency>

    <!-- Guava：核心，提供 RateLimiter 令牌桶实现 -->
    <dependency>
        <groupId>com.google.guava</groupId>
        <artifactId>guava</artifactId>
    </dependency>

    <!-- 测试 -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-test</artifactId>
        <scope>test</scope>
    </dependency>

    <!-- Lombok：@Slf4j 自动注入日志对象 -->
    <dependency>
        <groupId>org.projectlombok</groupId>
        <artifactId>lombok</artifactId>
        <optional>true</optional>
    </dependency>
</dependencies>
```

关键依赖是三个：

1. **`spring-boot-starter-aop`**：没有它，`@Aspect` 注解不生效，切面不会被织入。AOP 限流方案必备。
2. **`guava`**：Google 的 Java 核心库，里面的 `RateLimiter` 是令牌桶的成熟实现。版本由父 POM 统一管理。
3. **`hutool-all`**：用 `Dict`（有序键值对）快速构造 JSON 响应，省得写 DTO。

> 💡 为什么用 Guava 而不是自己实现令牌桶？因为限流算法在并发场景下涉及锁、时间精度等细节，Guava 的实现经过生产验证，稳定可靠。造轮子容易踩坑。

---

## 四、逐行拆解自定义注解 `RateLimiter.java`

```java
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
@Documented
public @interface RateLimiter {
    int NOT_LIMITED = 0;

    /**
     * qps
     */
    @AliasFor("qps") double value() default NOT_LIMITED;

    /**
     * qps
     */
    @AliasFor("value") double qps() default NOT_LIMITED;

    /**
     * 超时时长
     */
    int timeout() default 0;

    /**
     * 超时时间单位
     */
    TimeUnit timeUnit() default TimeUnit.MILLISECONDS;
}
```

### 4.1 元注解（修饰注解的注解）

- `@Target(ElementType.METHOD)`：这个注解只能加在**方法**上（不能加类、字段上）。
- `@Retention(RetentionPolicy.RUNTIME)`：注解保留到运行时，这样切面在运行时能通过反射读到它。如果是 `CLASS`，运行时就读不到了。
- `@Documented`：出现在 Javadoc 里。

> 💡 前端类比：元注解像 TypeScript 装饰器的元数据，`@Target` 限定装饰器能用在什么位置（方法/属性/类），`@Retention` 决定元数据在运行时是否可读。

### 4.2 注解属性

| 属性 | 类型 | 默认值 | 含义 |
| --- | --- | --- | --- |
| `value` | double | 0 | QPS（每秒允许的请求数），0 表示不限流 |
| `qps` | double | 0 | 和 `value` 互为别名，同一个值 |
| `timeout` | int | 0 | 获取令牌的超时时间，0 表示不等待直接失败 |
| `timeUnit` | TimeUnit | MILLISECONDS | 超时单位 |

### 4.3 `@AliasFor` 的作用与坑

```java
@AliasFor("qps") double value() default NOT_LIMITED;
@AliasFor("value") double qps() default NOT_LIMITED;
```

`@AliasFor` 让 `value` 和 `qps` 互为别名——设置 `value=1.0` 等于设置 `qps=1.0`，两者同步。这样使用者可以写 `@RateLimiter(value=1.0)` 或 `@RateLimiter(qps=1.0)`，都行。

**但有个重要坑**：用了 `@AliasFor` 后，**必须通过 `AnnotationUtils.findAnnotation()` 获取注解**，别名才会正确同步。如果直接用 `Method.getAnnotation(RateLimiter.class)`，别名关系不生效，可能出现 `value` 设了但 `qps` 读出来还是默认值 0 的问题。这是本模块注释里特意强调的点，后面切面代码也确实用了 `AnnotationUtils`。

> 💡 前端类比：`@AliasFor` 像 Vue 的 prop 别名或 TS 的类型映射，让同一个东西有多个名字。但 Spring 的注解别名需要特殊工具类解析，直接反射读不到同步的值。

---

## 五、逐行拆解限流切面 `RateLimiterAspect.java`（核心）

```java
@Slf4j
@Aspect
@Component
public class RateLimiterAspect {
    private static final ConcurrentMap<String, com.google.common.util.concurrent.RateLimiter> RATE_LIMITER_CACHE = new ConcurrentHashMap<>();

    @Pointcut("@annotation(com.xkcoding.ratelimit.guava.annotation.RateLimiter)")
    public void rateLimit() {
    }

    @Around("rateLimit()")
    public Object pointcut(ProceedingJoinPoint point) throws Throwable {
        MethodSignature signature = (MethodSignature) point.getSignature();
        Method method = signature.getMethod();
        // 通过 AnnotationUtils.findAnnotation 获取 RateLimiter 注解
        RateLimiter rateLimiter = AnnotationUtils.findAnnotation(method, RateLimiter.class);
        if (rateLimiter != null && rateLimiter.qps() > RateLimiter.NOT_LIMITED) {
            double qps = rateLimiter.qps();
            if (RATE_LIMITER_CACHE.get(method.getName()) == null) {
                // 初始化 QPS
                RATE_LIMITER_CACHE.put(method.getName(), com.google.common.util.concurrent.RateLimiter.create(qps));
            }

            log.debug("【{}】的QPS设置为: {}", method.getName(), RATE_LIMITER_CACHE.get(method.getName()).getRate());
            // 尝试获取令牌
            if (RATE_LIMITER_CACHE.get(method.getName()) != null && !RATE_LIMITER_CACHE.get(method.getName()).tryAcquire(rateLimiter.timeout(), rateLimiter.timeUnit())) {
                throw new RuntimeException("手速太快了，慢点儿吧~");
            }
        }
        return point.proceed();
    }
}
```

逐段拆解：

### 5.1 切面声明与令牌桶缓存

```java
@Aspect
@Component
public class RateLimiterAspect {
    private static final ConcurrentMap<String, com.google.common.util.concurrent.RateLimiter> RATE_LIMITER_CACHE = new ConcurrentHashMap<>();
```

- `@Aspect`：标记为切面。
- `@Component`：注册成 Spring Bean，Spring 才会管理它、织入切面。
- `RATE_LIMITER_CACHE`：一个**并发安全的 Map**，缓存每个方法对应的 `RateLimiter` 实例。为什么用 `ConcurrentHashMap`？因为多个请求线程会同时读写这个 Map，普通 HashMap 在并发下会丢数据或死循环。

**为什么要缓存 RateLimiter？** 因为 `RateLimiter` 是有状态的（它内部记录了上次发放令牌的时间、积攒的令牌数），同一个接口的多次请求必须共享同一个 `RateLimiter` 实例才能正确限流。每次请求都 new 一个新的，限流就失效了。

### 5.2 切点定义

```java
@Pointcut("@annotation(com.xkcoding.ratelimit.guava.annotation.RateLimiter)")
public void rateLimit() {
}
```

切点匹配所有标注了 `@RateLimiter` 注解的方法。`@annotation(全限定类名)` 是 AspectJ 的注解切点写法。

### 5.3 环绕通知（核心逻辑）

```java
@Around("rateLimit()")
public Object pointcut(ProceedingJoinPoint point) throws Throwable {
```

`@Around` 环绕通知能在方法执行前后都插入逻辑，且能控制是否执行原方法。`ProceedingJoinPoint` 是连接点，`point.proceed()` 才真正执行原方法。如果限流不通过，这里直接抛异常，不调 `proceed()`，原方法就不会执行——这就是"拦截"。

### 5.4 获取注解参数

```java
MethodSignature signature = (MethodSignature) point.getSignature();
Method method = signature.getMethod();
RateLimiter rateLimiter = AnnotationUtils.findAnnotation(method, RateLimiter.class);
```

- 从连接点拿到当前被拦截的方法对象 `Method`。
- 用 `AnnotationUtils.findAnnotation()` 而不是 `method.getAnnotation()`，就是为了 `@AliasFor` 别名能正确解析（见 4.3）。

### 5.5 初始化令牌桶

```java
if (rateLimiter != null && rateLimiter.qps() > RateLimiter.NOT_LIMITED) {
    double qps = rateLimiter.qps();
    if (RATE_LIMITER_CACHE.get(method.getName()) == null) {
        RATE_LIMITER_CACHE.put(method.getName(), com.google.common.util.concurrent.RateLimiter.create(qps));
    }
```

- `qps() > 0` 才需要限流（默认 0 表示不限流）。
- `RateLimiter.create(qps)` 创建一个令牌桶，每秒生成 `qps` 个令牌。
- 用方法名 `method.getName()` 作为缓存 key。**这里有隐患**（见知识点总结）。

### 5.6 尝试获取令牌

```java
if (RATE_LIMITER_CACHE.get(method.getName()) != null && !RATE_LIMITER_CACHE.get(method.getName()).tryAcquire(rateLimiter.timeout(), rateLimiter.timeUnit())) {
    throw new RuntimeException("手速太快了，慢点儿吧~");
}
```

- `tryAcquire(timeout, timeUnit)`：尝试获取一个令牌，如果在 `timeout` 时间内拿到返回 true，超时拿不到返回 false。
- `timeout=0` 表示不等待，拿不到立即返回 false。
- 拿不到令牌（`!tryAcquire`）就抛 `RuntimeException`，请求被拒绝。

### 5.7 放行

```java
return point.proceed();
```

拿到令牌了，执行原方法并返回结果。

---

## 六、逐行拆解测试控制器 `TestController.java`

```java
@Slf4j
@RestController
public class TestController {

    @RateLimiter(value = 1.0, timeout = 300)
    @GetMapping("/test1")
    public Dict test1() {
        log.info("【test1】被执行了。。。。。");
        return Dict.create().set("msg", "hello,world!").set("description", "别想一直看到我，不信你快速刷新看看~");
    }

    @GetMapping("/test2")
    public Dict test2() {
        log.info("【test2】被执行了。。。。。");
        return Dict.create().set("msg", "hello,world!").set("description", "我一直都在，卟离卟弃");
    }

    @RateLimiter(value = 2.0, timeout = 300)
    @GetMapping("/test3")
    public Dict test3() {
        log.info("【test3】被执行了。。。。。");
        return Dict.create().set("msg", "hello,world!").set("description", "别想一直看到我，不信你快速刷新看看~");
    }
}
```

三个接口对比：

| 接口 | QPS | 超时 | 效果 |
| --- | --- | --- | --- |
| `/test1` | 1.0 | 300ms | 每秒最多 1 个请求，快速刷新会被拒 |
| `/test2` | 无限流 | - | 随便刷，永远返回 |
| `/test3` | 2.0 | 300ms | 每秒最多 2 个请求 |

`@RateLimiter(value = 1.0, timeout = 300)` 的含义：该接口每秒只放行 1 个请求；如果当前没有令牌，最多等 300ms，等不到就拒绝。

> 💡 注意：`value` 和 `qps` 是别名，写 `@RateLimiter(qps = 1.0)` 效果一样。

---

## 七、全局异常处理 `GlobalExceptionHandler.java`

```java
@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(RuntimeException.class)
    public Dict handler(RuntimeException ex) {
        return Dict.create().set("msg", ex.getMessage());
    }
}
```

- `@RestControllerAdvice`：全局异常处理器，拦截所有 Controller 抛出的异常（`@ControllerAdvice` + `@ResponseBody`）。
- `@ExceptionHandler(RuntimeException.class)`：处理 `RuntimeException`。限流切面抛的正是 `RuntimeException`，这里捕获后返回 JSON `{"msg":"手速太快了，慢点儿吧~"}`，而不是默认的 500 错误页。

> 💡 没有这个处理器，限流触发时用户会看到 Spring Boot 默认的错误页（白板 500），体验很差。统一异常处理让限流拒绝也能返回友好的 JSON 提示。这是 `demo-exception-handler` 模块思想的体现。

---

## 八、配置文件与启动类

`application.yml`：

```yaml
server:
  port: 8080
  servlet:
    context-path: /demo
logging:
  level:
    com.xkcoding: debug
```

`logging.level.com.xkcoding: debug` 把项目包的日志级别调成 debug，这样切面里的 `log.debug("【{}】的QPS设置为: ...")` 才会输出，方便观察限流是否生效。

启动类 `SpringBootDemoRatelimitGuavaApplication` 就是标准的 `@SpringBootApplication` + `main`，没有特殊配置。AOP 切面靠 `@Component` + `@Aspect` 自动被 Spring 识别，不需要额外开启注解（`spring-boot-starter-aop` 已自动开启）。

---

## 九、运行与验证

### 9.1 启动

```sh
mvn spring-boot:run
```

### 9.2 测试限流效果

**正常访问 `/test1`**（间隔大于 1 秒）：

```sh
curl http://localhost:8080/demo/test1
```

返回：

```json
{"msg":"hello,world!","description":"别想一直看到我，不信你快速刷新看看~"}
```

**快速连续访问 `/test1`**（1 秒内多次）：

```sh
# 连续发 5 次请求
for i in 1 2 3 4 5; do curl http://localhost:8080/demo/test1; echo; done
```

部分请求返回：

```json
{"msg":"手速太快了，慢点儿吧~"}
```

说明限流生效，超出的请求被拒绝。

**访问 `/test2`**（无限流）：

无论多快都返回正常结果，不受限流影响。

### 9.3 观察日志

控制台会输出：

```
【test1】的QPS设置为: 1.0
【test1】被执行了。。。。。
```

看到 QPS 设置日志，说明切面正确拦截并初始化了令牌桶。

---

## 十、动手练习

1. **调整 QPS**：把 `/test1` 的 `value` 改成 `5.0`，用脚本快速发 10 个请求，观察有几个被拒。
2. **去掉超时**：把 `timeout` 改成 `0`，对比限流拒绝是否更"干脆"（不等待直接拒）。
3. **用 qps 属性**：把 `@RateLimiter(value=1.0)` 改成 `@RateLimiter(qps=1.0)`，验证别名是否生效（结果应一致）。
4. **加一个新接口**：写一个 `/test4`，QPS 设为 0.5（每 2 秒 1 个），快速刷新观察拒绝频率。
5. **改异常提示**：把切面里的异常消息改成 `{"code":429,"msg":"请求过于频繁"}` 风格，体会自定义限流响应。
6. **测试缓存隐患**：写两个同名方法（不同类）都加 `@RateLimiter`，观察是否互相影响（体会用方法名做 key 的局限）。

---

## 十一、本模块知识点总结（结合实际开发详解）

限流是高并发系统的第一道防线，本模块虽然简单，但涉及 AOP、注解、并发、限流算法多个知识点。下面放到真实开发场景讲透。

### 11.1 限流算法选型：令牌桶 vs 漏桶 vs 滑动窗口

**实际开发中怎么选？**

| 算法 | 适用场景 | 代表实现 |
| --- | --- | --- |
| 令牌桶 | 允许突发流量，大多数接口限流 | Guava RateLimiter、Sentinel |
| 漏桶 | 强制匀速，流量整形 | Nginx limit_req |
| 滑动窗口 | 精确控制，无突发 | Sentinel |

**最佳实践**：

- **接口限流首选令牌桶**：用户请求有突发性（比如页面加载同时发多个请求），令牌桶攒的令牌能容忍短时高峰，体验更好。
- **下游保护用漏桶**：调用第三方 API（如发短信、支付）时，对方有严格 QPS 限制，用漏桶匀速输出，避免触发对方限流。
- **网关层用滑动窗口**：Nginx/Spring Cloud Gateway 做全局流量控制，需要精确无突发。

**常见坑**：

- 用计数器算法不处理临界突刺，导致窗口切换瞬间流量翻倍。
- 以为令牌桶能无限突发——突发量受桶容量限制（Guava 里桶容量 = 每秒令牌数，即最多攒 1 秒的令牌）。

### 11.2 Guava RateLimiter 的两种获取方式

```java
// 方式一：阻塞获取，拿不到一直等
rateLimiter.acquire();   // 返回等待的秒数

// 方式二：非阻塞获取，拿不到立即返回 false
rateLimiter.tryAcquire();          // 立即尝试
rateLimiter.tryAcquire(timeout, unit);  // 等待一段时间
```

**实际开发怎么选？**

- `acquire()`：适合**后台任务**，宁可等也不拒绝（比如消息队列消费限流，慢一点没关系，但不能丢）。
- `tryAcquire()`：适合**用户请求**，拿不到直接拒绝，快速失败（比如 API 接口，不能让用户卡住）。

本模块用 `tryAcquire(timeout, unit)`，带超时的非阻塞获取，兼顾"稍等一下"和"快速失败"。**最佳实践：用户接口一律用 tryAcquire，避免线程被长时间阻塞。**

**常见坑**：

- 用 `acquire()` 做接口限流，高并发时大量线程阻塞等待，线程池打满，服务反而更慢。
- `tryAcquire(0, ...)` 和 `tryAcquire()` 行为略有差异，注意 timeout=0 是不等待。

### 11.3 `@AliasFor` 与 `AnnotationUtils` 的坑

这是本模块最隐蔽的坑。用了 `@AliasFor` 后，必须用 `AnnotationUtils.findAnnotation()` 读取注解，直接用 JDK 反射 `method.getAnnotation()` 读不出别名的同步值。

**为什么？** Spring 对注解做了增强，`AnnotationUtils` 会处理 `@AliasFor` 的别名映射、元注解继承等，而 JDK 原生反射不认这些。Spring Boot 里大量注解用了 `@AliasFor`（如 `@RequestMapping` 的 `value` 和 `path`），所以**在 Spring 项目里读注解，养成用 `AnnotationUtils` 的习惯**。

**实际开发中的类似场景**：

- 自定义注解想支持多个等价属性名（`value`/`path`/`name`），用 `@AliasFor`。
- 想读元注解（注解上的注解），用 `AnnotatedElementUtils`（更强大，支持递归找元注解）。

**常见坑**：直接 `method.getAnnotation()` 发现属性值是默认值，排查半天不知道是 `@AliasFor` 的锅。

### 11.4 令牌桶缓存设计：key 的选择

本模块用 `method.getName()`（方法名）做缓存 key，**这有隐患**：

- 如果两个不同类有同名方法都加 `@RateLimiter`，它们会共享同一个令牌桶，互相影响限流。
- 如果方法重载（同名不同参数），也会冲突。

**实际开发的正确做法**：

```java
// 用"全限定类名 + 方法名 + 参数"作为 key
String key = method.getDeclaringClass().getName() + "#" + method.getName() + Arrays.toString(method.getParameterTypes());
```

或者更彻底，用方法对象 `Method` 的字符串表示。**最佳实践：缓存 key 要全局唯一，避免不同方法共享限流器。**

**另一个坑**：本模块的 `if (cache.get(key) == null) cache.put(...)` 不是原子操作，并发首次访问时可能创建多个 RateLimiter（虽然最后只保留一个，但短暂会有限流不准）。**正确做法用 `computeIfAbsent`**：

```java
RateLimiter limiter = RATE_LIMITER_CACHE.computeIfAbsent(key, k -> RateLimiter.create(qps));
```

`computeIfAbsent` 保证原子性，key 不存在时才执行创建函数。这是并发 Map 的标准用法。

### 11.5 单机限流 vs 分布式限流

本模块是**单机限流**——限流器存在当前 JVM 的内存里（`ConcurrentMap`），只对当前这台机器生效。

**单机限流的局限**：假设你的服务部署了 3 台机器，每台限流 QPS=100，那么总 QPS 其实是 300。如果业务要求总 QPS 不超过 100，单机限流做不到。

**分布式限流方案**（下一个模块 `demo-ratelimit-redis` 会讲）：

| 方案 | 原理 | 特点 |
| --- | --- | --- |
| Redis + Lua | 用 Redis 计数，Lua 脚本保证原子性 | 主流，精确 |
| Nginx limit_req | 网关层限流 | 简单，但粒度粗 |
| Sentinel | 集群限流 | 功能全，但依赖控制台 |
| 网关层限流 | Spring Cloud Gateway | 分布式网关统一限流 |

**实际开发选型**：

- **单机服务**（QPS 不高，单机部署）：用 Guava RateLimiter 就够了，简单高效。
- **集群服务**（多实例，需全局限流）：用 Redis + Lua，或上 Sentinel。
- **入口流量**（防恶意攻击）：在 Nginx/网关层限流，挡在应用前面。

**常见坑**：以为单机限流能保护集群，结果每台机器各自限流，总流量超标。

### 11.6 限流触发后的处理策略

本模块限流触发后抛 `RuntimeException`，被全局异常处理器捕获返回 `{"msg":"手速太快了..."}`。实际开发有几种处理方式：

| 策略 | 实现 | 适用场景 |
| --- | --- | --- |
| 直接拒绝（429） | 抛异常，返回 HTTP 429 | 通用，RESTful 标准 |
| 排队等待 | `acquire()` 阻塞等 | 后台任务 |
| 降级返回 | 返回缓存/默认值 | 非核心接口 |
| 提示稍后重试 | 返回 Retry-After 头 | 用户操作 |

**最佳实践**：

- 限流拒绝应返回 **HTTP 429 Too Many Requests** 状态码（而不是 500），这是 RESTful 标准。
- 响应头加 `Retry-After: 5`，告诉客户端 5 秒后重试。
- 前端配合做"按钮置灰 + 倒计时"，避免用户疯狂点击。

> 💡 前端协作：前端收到 429 可以用 axios 拦截器统一处理，弹"操作太频繁"提示，并禁用按钮几秒。这和后端限流是一套配合。

**常见坑**：限流触发返回 500，前端误以为是服务器错误而重试，反而加重流量。应该用 429 明确告知"你太快了"。

### 11.7 AOP 限流的适用边界与自调用陷阱

AOP 限流靠动态代理实现，这意味着：

- **只有通过 Spring 代理对象调用的方法，限流才生效。**
- **类内部方法自调用（`this.method()`）不经过代理，限流失效。**

```java
@Service
public class OrderService {
    public void createOrder() {
        this.checkStock();  // ❌ 自调用，@RateLimiter 不生效
    }
    @RateLimiter(qps = 10)
    public void checkStock() { ... }
}
```

**最佳实践**：

- 限流注解加在 Controller 方法上（Controller 一定被代理，且从外部调用），最安全。
- 加在 Service 方法上时，确保它不会被同类其他方法直接 `this` 调用。
- 如果必须自调用又想限流，把限流方法拆到另一个 Bean，或用 `AopContext.currentProxy()` 获取代理对象调用。

**常见坑**：把 `@RateLimiter` 加在 Service 内部方法上，自调用后发现限流不生效，排查很久才发现是代理问题。这是所有 AOP 注解（`@Transactional`、`@Async`、`@Cacheable` 等）的通病。

---

> 📌 **学习建议**：限流是后端高并发的入门必修课。建议你把"令牌桶算法 + AOP 注解 + tryAcquire 非阻塞"这套组合理解透，它是生产中最常用的单机限流姿势。同时记住它的边界：单机限流保护不了集群，自调用绕过代理。下一个模块会讲 Redis + Lua 的分布式限流，补上集群这一环。学完两者，你就知道什么场景该用哪种方案了。
