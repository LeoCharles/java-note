# 06 - Spring Boot AOP 请求日志

> 对应项目模块：`demo-log-aop`
> 前置知识：已学完 `01`~`05`，了解启动类、配置注入、Logback 日志、统一异常处理
> 学习目标：理解 AOP（面向切面编程）的核心概念，掌握用 `@Aspect` 切面统一记录请求日志（IP、URL、参数、耗时、浏览器等），能在真实项目中复用这套日志方案。

---

## 一、本模块要解决什么问题？

假设你的项目有 50 个 Controller 接口。产品经理说："每个接口都要记录访问日志，包括谁访问的、访问了哪个接口、传了什么参数、耗时多久、用的什么浏览器。"

如果不用 AOP，你只能在每个 Controller 方法里手写日志：

```java
@GetMapping("/test")
public Dict test(String who) {
    long start = System.currentTimeMillis();
    log.info("请求进来，参数 who={}", who);
    // ... 业务逻辑
    log.info("请求结束，耗时 {}ms", System.currentTimeMillis() - start);
    return ...;
}
```

50 个接口写 50 遍，而且日志逻辑和业务逻辑混在一起——这就是**横切关注点（cross-cutting concern）**：日志、权限、限流、缓存这些逻辑，跟核心业务无关，却散落在各个方法里。

**AOP（Aspect-Oriented Programming，面向切面编程）** 就是为解决这类问题而生的：把横切逻辑抽到一个"切面"里，声明"在哪些方法执行前后自动插入"，业务方法本身完全不用改。

本模块最终效果：访问任意接口，控制台自动打印一条结构化请求日志（含线程、IP、URL、方法、参数、返回值、耗时、浏览器、操作系统），而 Controller 里一行日志代码都没写。

> 💡 前端类比：AOP 有点像 axios 拦截器或 Express 的中间件——你定义一个"拦截器/中间件"，所有请求都自动经过它，不用在每个接口里重复写。`@Around` ≈ 包裹式中间件（`next()` 调用前后都能插逻辑）。

---

## 二、项目结构

```
demo-log-aop/
├── pom.xml
└── src/main/
    ├── java/com/xkcoding/log/aop/
    │   ├── SpringBootDemoLogAopApplication.java   # 启动类
    │   ├── aspectj/
    │   │   └── AopLog.java                         # 核心：日志切面
    │   └── controller/
    │       └── TestController.java                 # 测试控制器（被切面拦截）
    └── resources/
        ├── application.yml                         # 基础配置
        └── logback-spring.xml                       # 日志配置（控制台+文件）
```

`aspectj` 包专门放切面类，这是 AOP 相关代码的常见归处（包名取自 AspectJ，Spring AOP 底层用的就是 AspectJ 的注解风格）。

---

## 三、pom.xml：新增 AOP 起步依赖

相比前面的模块，本模块多了两个依赖：

```xml
<!-- AOP 起步依赖 -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-aop</artifactId>
</dependency>

<!-- 解析 UserAgent 信息 -->
<dependency>
    <groupId>eu.bitwalker</groupId>
    <artifactId>UserAgentUtils</artifactId>
</dependency>

<!-- Guava 工具类 -->
<dependency>
    <groupId>com.google.guava</groupId>
    <artifactId>guava</artifactId>
</dependency>
```

- `spring-boot-starter-aop`：引入 Spring AOP + AspectJ + CGLIB。**只要引了这个依赖，Spring Boot 就会自动开启 AOP 支持**（`@EnableAspectJAutoProxy` 自动配置生效），你写的 `@Aspect` 切面就能工作。
- `UserAgentUtils`：用来从 HTTP 请求头 `User-Agent` 解析出浏览器、操作系统信息。
- `guava`：Google 的工具类，本模块用了它的 `Maps.newHashMap()`。

> 💡 前端类比：引 `spring-boot-starter-aop` 就像装一个 axios 插件——装上就有拦截器能力，不用手动初始化。

---

## 四、核心：AopLog 切面逐行拆解

`aspectj/AopLog.java` 是本模块的灵魂。我们分段讲。

### 4.1 类上的注解

```java
@Aspect
@Component
@Slf4j
public class AopLog {
```

- `@Aspect`：声明这是一个**切面**。它本身不改变程序逻辑，只是告诉 Spring："这个类里定义了一些通知（Advice），请在切点匹配的方法上自动织入。"
- `@Component`：注册成 Bean。**`@Aspect` 不会自动注册 Bean**，必须配合 `@Component`（或 `@Bean`）让 Spring 容器管理它，切面才会生效。这是新手常踩的坑。
- `@Slf4j`：Lombok 注解，自动注入一个 `log` 对象（`private static final Logger log`），直接 `log.info(...)` 就能用。

### 4.2 切点（Pointcut）：定义"拦截哪些方法"

```java
@Pointcut("execution(public * com.xkcoding.log.aop.controller.*Controller.*(..))")
public void log() {
}
```

`@Pointcut` 定义切点——一个"方法匹配规则"。这里用的是 `execution` 切点指示器，语法是：

```
execution(修饰符 返回值 包名.类名.方法名(参数))
```

拆解 `execution(public * com.xkcoding.log.aop.controller.*Controller.*(..))`：

| 片段 | 含义 |
| --- | --- |
| `public` | 只匹配 public 方法 |
| `*` | 任意返回值类型 |
| `com.xkcoding.log.aop.controller` | 包路径 |
| `.*Controller` | 该包下所有以 Controller 结尾的类 |
| `.*` | 类里的任意方法 |
| `(..)` | 任意参数（数量、类型不限） |

所以这条规则的意思是：**拦截 `controller` 包下所有 `*Controller` 类的 public 方法**。

`public void log() {}` 是个空方法，纯粹当切点的"名字标签"用——后面通知注解引用 `log()` 就等于引用这条规则，避免重复写长表达式。

**常见切点指示器：**

| 指示器 | 作用 | 示例 |
| --- | --- | --- |
| `execution` | 匹配方法签名（最常用） | `execution(public * com.x..*.*(..))` |
| `within` | 匹配类 | `within(com.x..controller.*)` |
| `@annotation` | 匹配带某注解的方法 | `@annotation(org.springframework.web.bind.annotation.GetMapping)` |
| `bean` | 匹配 Bean 名 | `bean(*Controller)` |

> 💡 前端类比：切点表达式就像 CSS 选择器或 Vue Router 的路由匹配规则——你声明"匹配哪些元素/路由"，框架自动把逻辑织入匹配项。

### 4.3 环绕通知（@Around）：包裹目标方法

```java
@Around("log()")
public Object aroundLog(ProceedingJoinPoint point) throws Throwable {
    // ① 获取请求对象
    ServletRequestAttributes attributes = (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
    HttpServletRequest request = Objects.requireNonNull(attributes).getRequest();

    // ② 记录开始时间，执行目标方法
    long startTime = System.currentTimeMillis();
    Object result = point.proceed();   // ← 关键：调用原方法
    ...
    return result;
}
```

- `@Around("log()")`：环绕通知，引用前面定义的 `log()` 切点。环绕通知是**最强**的通知，能在方法执行前后都插逻辑，甚至决定要不要执行、改不改返回值。
- `ProceedingJoinPoint point`：连接点，代表当前被拦截的方法。`point.proceed()` 就是**执行原方法**——这行之前是"前置逻辑"，这行之后是"后置逻辑"。这跟 Express 的 `(req, res, next) => { next() }` 一模一样。
- `Object result = point.proceed()`：拿到原方法的返回值，最后 `return result` 原样返回（也可以在这里改写返回值，比如加密、包装）。

> ⚠️ **必须调用 `point.proceed()`**，否则原方法不会执行，接口就废了。而且必须 `return` 它的结果，否则调用方拿不到返回值。

### 4.4 五种通知类型对比

Spring AOP 有五种通知，本模块用了最全的 `@Around`：

| 通知 | 时机 | 能否改返回值 | 能否阻止执行 | 参数类型 |
| --- | --- | --- | --- | --- |
| `@Before` | 方法执行前 | 否 | 否 | `JoinPoint` |
| `@After` | 方法执行后（无论是否异常） | 否 | 否 | `JoinPoint` |
| `@AfterReturning` | 方法正常返回后 | 可（`returning` 属性） | 否 | `JoinPoint` + 返回值 |
| `@AfterThrowing` | 方法抛异常后 | 否 | 否 | `JoinPoint` + 异常 |
| `@Around` | 包裹前后 | **能** | **能** | `ProceedingJoinPoint` |

**怎么选？** 只需要前置日志用 `@Before`；需要拿返回值或耗时用 `@AfterReturning`；需要同时控制前后、改返回值用 `@Around`。本模块要算耗时（前后都要）+ 拿返回值，所以用 `@Around`。

> 💡 前端类比：`@Before` ≈ axios 请求拦截器；`@AfterReturning` ≈ 响应拦截器；`@Around` ≈ Express 包裹式中间件（`next()` 前后都能写）。

### 4.5 收集日志信息：构建 Log 对象

```java
final Log l = Log.builder()
    .threadId(Long.toString(Thread.currentThread().getId()))
    .threadName(Thread.currentThread().getName())
    .ip(getIp(request))
    .url(request.getRequestURL().toString())
    .classMethod(String.format("%s.%s", point.getSignature().getDeclaringTypeName(),
        point.getSignature().getName()))
    .httpMethod(request.getMethod())
    .requestParams(getNameAndValue(point))
    .result(result)
    .timeCost(System.currentTimeMillis() - startTime)
    .userAgent(header)
    .browser(userAgent.getBrowser().toString())
    .os(userAgent.getOperatingSystem().toString()).build();

log.info("Request Log Info : {}", JSONUtil.toJsonStr(l));
```

用 Lombok 的 `@Builder` 链式构造一个 `Log` 对象，包含 12 个字段（线程、IP、URL、方法、参数、返回值、耗时、浏览器等），最后用 Hutool 的 `JSONUtil` 序列化成 JSON 打印。

- `point.getSignature()`：拿到方法签名，能取到类名、方法名。
- `getIp(request)`：从请求头取真实 IP（下面单独讲）。
- `timeCost = System.currentTimeMillis() - startTime`：`proceed()` 前后各取一次时间，差值就是接口耗时。

### 4.6 获取方法参数名和值

```java
private Map<String, Object> getNameAndValue(ProceedingJoinPoint joinPoint) {
    final Signature signature = joinPoint.getSignature();
    MethodSignature methodSignature = (MethodSignature) signature;
    final String[] names = methodSignature.getParameterNames();
    final Object[] args = joinPoint.getArgs();
    ...
    Map<String, Object> map = Maps.newHashMap();
    for (int i = 0; i < names.length; i++) {
        map.put(names[i], args[i]);
    }
    return map;
}
```

`joinPoint.getArgs()` 只能拿到参数值数组（`[arg0, arg1]`），不知道参数名。要拿到参数名（如 `who`），需要强转成 `MethodSignature`，调用 `getParameterNames()`。两者按下标配对，组装成 `{参数名: 参数值}` 的 Map，日志才可读。

> ⚠️ 拿参数名依赖编译时保留参数名信息。Java 8 默认不保留，需要加 `-parameters` 编译参数；Spring Boot 的 `spring-boot-starter-parent` 默认帮你加好了，所以能拿到。

### 4.7 获取真实 IP：穿透代理

```java
public static String getIp(HttpServletRequest request) {
    String ip = request.getHeader("x-forwarded-for");
    if (ip == null || ip.length() == 0 || UNKNOWN.equalsIgnoreCase(ip)) {
        ip = request.getHeader("Proxy-Client-IP");
    }
    if (ip == null || ip.length() == 0 || UNKNOWN.equalsIgnoreCase(ip)) {
        ip = request.getHeader("WL-Proxy-Client-IP");
    }
    if (ip == null || ip.length() == 0 || UNKNOWN.equalsIgnoreCase(ip)) {
        ip = request.getRemoteAddr();
    }
    ...
}
```

为什么不直接用 `request.getRemoteAddr()`？因为生产环境通常有 Nginx/网关反向代理，`getRemoteAddr()` 拿到的是代理服务器的 IP（如 `127.0.0.1`），不是用户真实 IP。

代理服务器会把真实 IP 放在 `X-Forwarded-For`、`Proxy-Client-IP` 等请求头里，所以要依次尝试这些头。`X-Forwarded-For` 可能是 `真实IP, 代理1, 代理2` 的链式格式，取第一个就是真实 IP。

> 💡 前端类比：这就像前端拿 token——不能只看 cookie，还要看 `Authorization` 头、URL 参数，因为 token 可能放在不同地方。

### 4.8 Log 内部类

```java
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
static class Log {
    private String threadId;
    private String threadName;
    private String ip;
    ...
}
```

用 `static` 内部类封装日志数据，`@Builder` 链式构造，`@Data` 生成 getter/setter。定义成内部类是因为它只被 `AopLog` 使用，不需要独立存在。

---

## 五、TestController：被拦截的目标

```java
@Slf4j
@RestController
public class TestController {

    @GetMapping("/test")
    public Dict test(String who) {
        return Dict.create().set("who", StrUtil.isBlank(who) ? "me" : who);
    }

    @PostMapping("/testJson")
    public Dict testJson(@RequestBody Map<String, Object> map) {
        final String jsonStr = JSONUtil.toJsonStr(map);
        log.info(jsonStr);
        return Dict.create().set("json", map);
    }
}
```

注意：**Controller 里完全没有日志逻辑**，只写业务。但因为类名是 `TestController`、在 `controller` 包下、方法是 public，所以匹配切点 `execution(public * com.xkcoding.log.aop.controller.*Controller.*(..))`，AOP 会自动拦截这两个方法，打印请求日志。

这就是 AOP 的价值——**业务代码零侵入，横切逻辑集中管理**。

---

## 六、logback-spring.xml：日志输出配置

本模块带了 `logback-spring.xml`，定义了三个 appender：

| Appender | 作用 |
| --- | --- |
| `CONSOLE` | 输出到控制台，INFO 级别 |
| `FILE_INFO` | 输出到文件，按天+大小滚动，过滤掉 ERROR |
| `FILE_ERROR` | 只输出 ERROR 到单独文件 |

关键配置项：

- `<rollingPolicy>` + `<FileNamePattern>`：按天切分日志文件，文件名带日期。
- `<maxHistory>90</maxHistory>`：只保留 90 天日志，自动清理旧文件。
- `<maxFileSize>2MB</maxFileSize>`：单个文件超过 2MB 就切分。
- `LevelFilter` vs `ThresholdFilter`：前者精确匹配某级别（可 DENY/ACCEPT），后者匹配某级别及以上。

> 💡 这个配置在 `demo-logback` 模块已详细讲过，这里是为了让 AOP 打的日志能落盘到文件，方便排查问题。

---

## 七、运行与验证

### 7.1 启动

```sh
mvn spring-boot:run
```

### 7.2 访问接口

```sh
curl http://localhost:8080/demo/test?who=claude
curl -X POST http://localhost:8080/demo/testJson -H "Content-Type: application/json" -d '{"a":1,"b":2}'
```

### 7.3 观察控制台日志

每次请求，控制台会自动打印一条结构化日志：

```json
Request Log Info : {"threadId":"25","threadName":"http-nio-8080-exec-1","ip":"127.0.0.1","url":"http://localhost:8080/demo/test","httpMethod":"GET","classMethod":"com.xkcoding.log.aop.controller.TestController.test","requestParams":{"who":"claude"},"result":{"who":"claude"},"timeCost":15,"os":"WINDOWS_10","browser":"CHROME","userAgent":"Mozilla/5.0 ..."}
```

同时这条日志会按 `logback-spring.xml` 配置写入 `logs/demo-log-aop/` 下的文件。

---

## 八、动手练习

1. **改切点范围**：把切点改成只拦截 `test` 方法（`execution(* *..test(..))`），验证 `testJson` 不再被拦截。
2. **加 `@Before`**：在 `AopLog` 里加一个 `@Before("log()")` 方法，打印"请求即将进入"，观察它和 `@Around` 的执行顺序。
3. **用注解切点**：定义一个自定义注解 `@LogRecord`，把切点改成 `@annotation(com.xkcoding.log.aop.annotation.LogRecord)`，在需要的方法上加注解才记录日志，体会"精确控制"。
4. **记录异常**：在 `test` 方法里故意 `throw new RuntimeException()`，观察 `@Around` 里 `proceed()` 抛异常后日志是否还能打印（提示：`proceed()` 后的代码不会执行，需要 try-finally 处理）。
5. **优化 IP 获取**：在 `getIp` 里加上 IPv6 处理和 `X-Real-IP` 头的支持。

---

## 九、本模块知识点总结（结合实际开发详解）

AOP 是 Spring 两大核心之一（另一个是 IoC），在企业开发中用于日志、权限、限流、缓存、链路追踪等。下面把核心知识点放到真实场景里讲透。

### 9.1 AOP 核心术语：用一句话讲清

初学者最怕 AOP 的术语，其实可以类比前端理解：

| 术语 | 一句话 | 前端类比 |
| --- | --- | --- |
| **Aspect（切面）** | 放横切逻辑的类（`@Aspect`） | axios 拦截器对象 |
| **Advice（通知）** | 切面里具体要插入的逻辑（`@Around` 等） | 拦截器里的函数 |
| **Pointcut（切点）** | 描述"拦截哪些方法"的规则 | 路由匹配规则 |
| **JoinPoint（连接点）** | 被拦截到的那个方法（运行时实例） | 匹配到的那个请求 |
| **Weaving（织入）** | 把切面逻辑插入目标方法的过程 | 中间件挂载 |

**执行流程**：Spring 启动时扫描 `@Aspect` Bean → 解析切点 → 给匹配的 Bean 创建代理对象 → 运行时调用方法走代理 → 代理按通知类型执行切面逻辑 + 原方法。

### 9.2 Spring AOP 的实现原理：动态代理

Spring AOP 底层是**动态代理**。有两种方式：

1. **JDK 动态代理**：目标类实现了接口时用，代理对象实现同样的接口。
2. **CGLIB 代理**：目标类没实现接口时用，代理对象是目标类的子类（生成字节码）。

Spring Boot 2.x 默认用 CGLIB（`spring.aop.proxy-target-class=true`），即使有接口也用 CGLIB，避免代理类型转换问题。

**实际开发影响：**

- `@Autowired` 注入时，如果是被切面代理的 Bean，注入的实际是代理对象，不是原始对象。
- **类内部方法自调用不走代理**：同一个类里方法 A 调方法 B，B 上的切面不生效（因为 `this.B()` 直接调原始对象，绕过代理）。这是 AOP 最经典的坑，解决方法是把 B 拆到另一个类，或注入自身代理（`@Autowired private XxxService self; self.B()`）。
- `final` 方法和类不能被 CGLIB 代理（因为 CGLIB 靠继承，final 不能被继承）。

> 💡 前端类比：这像 Vue 的响应式——Vue 2 用 `Object.defineProperty`（类似 JDK 代理，需要能改属性），Vue 3 用 `Proxy`（类似 CGLIB，直接代理整个对象）。Spring AOP 的代理也是"包一层"。

### 9.3 切点表达式：写对才能拦对

`execution` 是最常用的切点指示器，语法 `execution(修饰符 返回值 包.类.方法(参数))`：

```
execution(public * com.xkcoding..controller.*Controller.*(..))
```

**通配符：**

- `*`：匹配任意（返回值、包名一段、类名、方法名）
- `..`：匹配任意层级包（`com.x..y`）或任意参数（`(..)`）

**实际开发常用写法：**

```java
// 拦截 controller 包下所有类的 public 方法
@Pointcut("execution(public * com.xkcoding..controller..*.*(..))")

// 拦截带 @GetMapping 注解的方法
@Pointcut("@annotation(org.springframework.web.bind.annotation.GetMapping)")

// 拦截 service 层所有方法
@Pointcut("execution(* com.xkcoding..service..*.*(..))")

// 组合：且（&&）、或（||）、非（!）
@Pointcut("log() && !excluded()")
```

**常见坑：**

- 包路径写错（少写一段、拼错），导致切点不匹配，切面不生效，且**不会报错**——方法正常执行，只是没日志，排查极难。
- 想拦截所有方法写成 `execution(* *.*(..))`，会连 Spring 内部方法都拦截，性能暴跌甚至启动失败。**务必限定包范围**。
- `@annotation` 切点要求方法运行时确实有该注解，继承来的注解可能不匹配。

### 9.4 通知执行顺序

多个通知同时存在时，执行顺序（Spring 5.2.7+ 版本）：

```
@Around(前) → @Before → 目标方法 → @AfterReturning → @After → @Around(后)
（若抛异常）@AfterThrowing 替代 @AfterReturning
```

**实际开发要点：**

- 多个切面默认按 `@Order` 值（小的先执行）或字母序执行。要控制顺序，给切面加 `@Order(1)`。
- `@Around` 必须调 `proceed()`，否则链断了，后续通知和目标方法都不执行。
- `@Around` 里 `proceed()` 抛异常时，它之后的代码不执行——如果要记录"无论成功失败都记耗时"，用 try-finally 包裹。

### 9.5 请求日志切面的实际应用与坑

本模块的 `AopLog` 是生产级请求日志的雏形，实际项目常在此基础上扩展：

**常见增强：**

1. **加 traceId**：用 MDC（`org.slf4j.MDC`）给每个请求生成唯一 ID，日志带上它，方便全链路追踪。
2. **异步落盘**：日志写入用异步 Appender，避免 IO 阻塞业务线程。
3. **敏感参数脱敏**：参数里有密码、身份证要打码后再记日志。
4. **大对象截断**：返回值是超大 List/文件流，序列化会爆内存，要限制长度。

**常见坑：**

- **参数序列化失败**：`requestParams` 里如果有 `HttpServletRequest`、`MultipartFile` 这类对象，`JSONUtil.toJsonStr` 会报错或死循环。解决：过滤掉不可序列化的参数类型。
- **`@RequestBody` 参数拿不到**：流只能读一次，Controller 读完后切面再读会报错。解决：用 `ContentCachingRequestWrapper` 包装请求缓存 body。
- **切面吞异常**：`@Around` 里 `proceed()` 抛异常没往外抛，导致全局异常处理器收不到异常，前端拿到 200 但无响应。**原则：切面只记录不吞异常，`catch` 后必须 `throw`**。
- **性能**：切面里做重操作（如调外部接口解析 IP 归属地）会拖慢所有接口，放异步线程或只采样记录。

### 9.6 AOP 的典型应用场景

AOP 不止用于日志，企业开发常见场景：

| 场景 | 切点 | 通知 | 说明 |
| --- | --- | --- | --- |
| 请求日志 | controller 方法 | `@Around` | 本模块 |
| 权限校验 | 带 `@RequirePermission` 的方法 | `@Before` | 校验失败抛异常 |
| 接口限流 | 带 `@RateLimit` 的方法 | `@Before` | 见 `demo-ratelimit-*` |
| 缓存 | 带 `@Cacheable` 的方法 | `@Around` | Spring Cache 已封装 |
| 重复提交防护 | controller 方法 | `@Around` | 基于 token/Redis |
| 链路追踪 | 所有 service 方法 | `@Around` | 注入 traceId |
| 操作审计 | 带 `@Audit` 的方法 | `@AfterReturning` | 记录谁做了什么 |

**最佳实践**：能用注解精确控制就别用大范围 `execution`——`@annotation(自定义注解)` 让开发者主动标注需要切面的方法，避免"误伤"和性能浪费。

### 9.7 AOP vs 拦截器（HandlerInterceptor）vs 过滤器（Filter）

这三个都能"拦截请求"，实际开发怎么选？

| 维度 | Filter | Interceptor | AOP |
| --- | --- | --- | --- |
| 层级 | Servlet 容器层 | Spring MVC 层 | Spring 容器层（更细） |
| 拦截粒度 | URL 模式 | URL + Handler | 方法签名（任意 Bean 方法） |
| 能否拿方法参数 | 否 | 部分 | 能（参数名、值、返回值） |
| 能否改返回值 | 否 | 否（后置只能改 view） | 能 |
| 典型场景 | 编码、跨域、安全头 | 登录校验、日志 | 业务级横切（日志、权限、限流） |

**选择建议**：和 HTTP 强相关的（跨域、编码、登录态）用 Filter/Interceptor；和业务方法强相关的（日志、权限注解、限流）用 AOP。本模块要拿方法参数和返回值，Interceptor 做不到，所以用 AOP。

---

> 📌 **学习建议**：AOP 是 Spring 的精华，也是从"写接口"到"做架构"的分水岭。作为前端转后端，你可以把 AOP 理解成"服务端的拦截器/中间件系统，但粒度细到方法级"。建议先把本模块的 `AopLog` 跑通，然后重点理解三件事：**切点（拦谁）、通知（插什么逻辑）、`proceed()`（放行原方法）**。掌握后，后续的限流、权限、缓存模块都是同一套思路——定义切点 + 写通知，区别只是通知里干的事不同。
