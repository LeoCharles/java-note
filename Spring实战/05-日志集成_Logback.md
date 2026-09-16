# 05 - Spring Boot 日志集成 Logback

> 对应项目模块：`demo-logback`
> 前置知识：已学完 01-04 模块，了解启动类、配置文件、依赖注入基本用法
> 学习目标：理解 Java 日志体系，掌握 Logback 的配置方法，能独立为项目配置控制台日志 + 按日期/大小滚动的文件日志，并按级别分离 info/error 日志。

---

## 一、本模块要解决什么问题？

前端同学对 `console.log` 很熟悉——开发时随手打，上线前删掉。但后端不能这么干：

- **线上没有浏览器控制台**，程序跑在服务器上，出了问题你看不到现场，必须靠日志文件回溯。
- **日志要持久化**：出 bug 时可能已经过了几小时甚至几天，日志必须落盘保存。
- **日志要分类**：正常流水日志和错误日志要分开存，方便排查和告警。
- **日志要滚动**：不能让日志文件无限增大撑爆磁盘，要按天切分、按大小切分、定期清理。

本模块演示：用 Logback 同时输出**控制台日志**和**文件日志**，文件按日期和大小拆分，并且把 info 和 error 级别分到不同文件。

---

## 二、先搞懂 Java 日志体系（重要背景）

Java 日志比前端复杂得多，历史上出现了多套框架，新手很容易懵。先用一张图理清关系：

```
日志门面（API）：SLF4J  ─── 你代码里调用的接口
                        │
日志实现（Impl）：Logback ─── 真正干活的
```

- **SLF4J（Simple Logging Facade）**：日志门面，只定义接口（`Logger`、`info()`、`debug()` 等），自己不干活，类似前端的 `console` 抽象。
- **Logback**：SLF4J 的一种实现，真正把日志写到控制台/文件。它是 Log4j 的作者写的下一代框架，性能更好。
- **Spring Boot 默认用 Logback**：引入 `spring-boot-starter` 就自带了 Logback + SLF4J，不用额外加依赖。

> 💡 前端类比：SLF4J 像 `winston`/`pino` 的统一接口，Logback 像具体的 transport 实现。或者类比成"接口与实现分离"——你代码面向 SLF4J 接口写，底层实现可以随时换（换成 Log4j2 也不用改业务代码）。

**为什么要分门面和实现？** 解耦。业务代码只依赖 SLF4J 接口，今天用 Logback，明天换 Log4j2，业务代码一行不用改，只换依赖和配置文件。

---

## 三、项目结构

```
demo-logback/
├── pom.xml
└── src/main/
    ├── java/com/xkcoding/logback/
    │   └── SpringBootDemoLogbackApplication.java   # 启动类（演示各级别日志输出）
    └── resources/
        ├── application.yml                          # 基础配置
        └── logback-spring.xml                       # Logback 配置文件（核心）
```

核心就是这个 `logback-spring.xml`——Logback 的所有行为都在这里配。

---

## 四、逐行拆解 pom.xml

```xml
<dependencies>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-web</artifactId>
    </dependency>

    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-test</artifactId>
        <scope>test</scope>
    </dependency>

    <dependency>
        <groupId>org.projectlombok</groupId>
        <artifactId>lombok</artifactId>
        <optional>true</optional>
    </dependency>
</dependencies>
```

**注意：没有显式引入 Logback 依赖！** 因为 `spring-boot-starter`（被 `spring-boot-starter-web` 依赖）里已经传递包含了 `spring-boot-starter-logging`，而后者包含了 Logback + SLF4J 的全部依赖。这就是 Spring Boot "默认日志方案"的便利。

> 💡 前端类比：像 `create-react-app` 默认就内置了 `react-scripts`，不用你再手动装 webpack/babel。

`lombok` 用来生成 `@Slf4j` 注解的 logger 字段（见下文），`<optional>true</optional>` 表示不传递。

---

## 五、逐行拆解启动类

`SpringBootDemoLogbackApplication.java`：

```java
@SpringBootApplication
@Slf4j
public class SpringBootDemoLogbackApplication {

    public static void main(String[] args) {
        ConfigurableApplicationContext context = SpringApplication.run(SpringBootDemoLogbackApplication.class, args);
        int length = context.getBeanDefinitionNames().length;
        log.trace("Spring boot启动初始化了 {} 个 Bean", length);
        log.debug("Spring boot启动初始化了 {} 个 Bean", length);
        log.info("Spring boot启动初始化了 {} 个 Bean", length);
        log.warn("Spring boot启动初始化了 {} 个 Bean", length);
        log.error("Spring boot启动初始化了 {} 个 Bean", length);
        try {
            int i = 0;
            int j = 1 / i;
        } catch (Exception e) {
            log.error("【SpringBootDemoLogbackApplication】启动异常：", e);
        }
    }
}
```

### 5.1 `@Slf4j` —— Lombok 注入 logger

`@Slf4j` 是 Lombok 注解，编译时会在类里自动生成一个 `private static final Logger log = LoggerFactory.getLogger(类名.class);` 字段。所以代码里能直接用 `log.xxx()`，不用手写获取 Logger 的样板代码。

等价于手写：

```java
private static final org.slf4j.Logger log = org.slf4j.LoggerFactory.getLogger(SpringBootDemoLogbackApplication.class);
```

> 💡 这是实际开发中最常用的日志写法——任何需要打日志的类，加 `@Slf4j`，然后 `log.info(...)` 即可。

### 5.2 日志级别

代码里依次调用了 5 个级别，从低到高：

| 级别 | 含义 | 典型用途 |
| --- | --- | --- |
| `trace` | 最详细的跟踪信息 | 极少用，排查疑难杂症时临时开 |
| `debug` | 调试信息 | 开发环境看流程细节 |
| `info` | 重要业务流水 | 正常运行时的关键节点（订单创建、用户登录） |
| `warn` | 警告 | 可恢复的异常（重试、降级） |
| `error` | 错误 | 影响功能的异常（需要人介入） |

**级别有继承性**：配置了 `level="info"`，意味着 `info` 及以上（info/warn/error）都会输出，`debug`/`trace` 被过滤掉。这是日志框架的核心机制。

### 5.3 占位符 `{}`

```java
log.info("Spring boot启动初始化了 {} 个 Bean", length);
```

`{}` 是 SLF4J 的占位符，运行时被 `length` 的值替换。**永远用占位符，不要用字符串拼接**：

```java
// ❌ 错误：即使日志级别不够，也会先拼接字符串，浪费性能
log.debug("用户列表：" + userList.toString());

// ✅ 正确：级别不够时不会计算参数，性能好
log.debug("用户列表：{}", userList);
```

### 5.4 异常日志

```java
try {
    int i = 0;
    int j = 1 / i;
} catch (Exception e) {
    log.error("【SpringBootDemoLogbackApplication】启动异常：", e);
}
```

`log.error(msg, e)` 的第二个参数传异常对象，Logback 会自动打印完整堆栈跟踪。**这是排查线上问题的关键**——异常堆栈能精确定位到出错的类、方法、行号。

> 💡 前端类比：类似 `console.error(err.stack)`，但 Logback 会把它格式化、落盘、带时间戳和线程信息。

---

## 六、核心：逐行拆解 `logback-spring.xml`

这是本模块最核心的文件。Logback 用 XML 配置，结构是：`configuration` → `appender`（输出目的地）+ `root`（全局配置）。

### 6.1 引入 Spring Boot 默认配置

```xml
<include resource="org/springframework/boot/logging/logback/defaults.xml"/>
```

这行引入 Spring Boot 预置的默认配置，里面定义了 `CONSOLE_LOG_PATTERN`、`FILE_LOG_PATTERN` 等变量（日志格式模板），你后面可以直接用 `${CONSOLE_LOG_PATTERN}` 引用，不用从头写格式。这是"站在巨人肩膀上"的写法。

### 6.2 控制台 Appender

```xml
<appender name="CONSOLE" class="ch.qos.logback.core.ConsoleAppender">
    <filter class="ch.qos.logback.classic.filter.LevelFilter">
        <level>INFO</level>
    </filter>
    <encoder>
        <pattern>${CONSOLE_LOG_PATTERN}</pattern>
        <charset>UTF-8</charset>
    </encoder>
</appender>
```

- `appender` = 输出目的地。`ConsoleAppender` 表示输出到控制台。
- `filter`：过滤器。这里用 `LevelFilter` 配 `INFO`——但注意 `LevelFilter` 默认行为是**只接受精确匹配 INFO 的日志**，不匹配的会被拒绝（onMismatch 默认 DENY）。实际效果是控制台只输出 INFO 级别。
- `encoder`：把日志事件编码成文本。`pattern` 定义格式，`charset` 设 UTF-8 避免中文乱码。

### 6.3 文件 Appender（INFO 级别，滚动归档）

```xml
<appender name="FILE_INFO" class="ch.qos.logback.core.rolling.RollingFileAppender">
    <filter class="ch.qos.logback.classic.filter.LevelFilter">
        <level>ERROR</level>
        <onMatch>DENY</onMatch>
        <onMismatch>ACCEPT</onMismatch>
    </filter>
    <rollingPolicy class="ch.qos.logback.core.rolling.TimeBasedRollingPolicy">
        <FileNamePattern>logs/demo-logback/info.created_on_%d{yyyy-MM-dd}.part_%i.log</FileNamePattern>
        <maxHistory>90</maxHistory>
        <timeBasedFileNamingAndTriggeringPolicy class="ch.qos.logback.core.rolling.SizeAndTimeBasedFNATP">
            <maxFileSize>2MB</maxFileSize>
        </timeBasedFileNamingAndTriggeringPolicy>
    </rollingPolicy>
    <encoder>
        <pattern>${FILE_LOG_PATTERN}</pattern>
        <charset>UTF-8</charset>
    </encoder>
</appender>
```

**过滤器（关键技巧）**：

```xml
<filter class="ch.qos.logback.classic.filter.LevelFilter">
    <level>ERROR</level>
    <onMatch>DENY</onMatch>      <!-- 匹配到 ERROR 就拒绝 -->
    <onMismatch>ACCEPT</onMismatch>  <!-- 不是 ERROR 就接受 -->
</filter>
```

这里用了一个"反向过滤"技巧：匹配到 ERROR 就 DENY（拒绝），不是 ERROR 就 ACCEPT（接受）。效果是 **FILE_INFO 只记录非 ERROR 日志**（即 trace/debug/info/warn）。

为什么不直接过滤 INFO？因为 `LevelFilter` 是精确匹配，配 INFO 会把 warn/error 都过滤掉。而日志级别有继承性，error 比 info 高，正常会一起输出。用这个反向技巧能把 error 排除出去，让 info 文件"干净"。

**滚动策略 `TimeBasedRollingPolicy`**：

- `FileNamePattern`：归档文件命名规则。`%d{yyyy-MM-dd}` 是日期，`%i` 是当天第几个文件（按大小切分时递增）。
  - 当天日志写到 `info.created_on_2026-09-03.part_0.log`
  - 超过 2MB 就新开 `part_1.log`
  - 第二天归档为 `info.created_on_2026-09-04.part_0.log`
- `maxHistory>90</maxHistory>`：只保留最近 90 天的日志，超期自动删除，防止撑爆磁盘。
- `SizeAndTimeBasedFNATP` + `maxFileSize=2MB`：单个文件最大 2MB，超过就切分新文件。本 demo 设 2MB 是为了演示，实际生产常用 50MB-200MB。

### 6.4 文件 Appender（ERROR 级别）

```xml
<appender name="FILE_ERROR" class="ch.qos.logback.core.rolling.RollingFileAppender">
    <filter class="ch.qos.logback.classic.filter.ThresholdFilter">
        <level>Error</level>
    </filter>
    ...
</appender>
```

这里用 `ThresholdFilter` 而不是 `LevelFilter`：

- `ThresholdFilter` 配 `Error` 表示**只接受 ERROR 及以上级别**，低于的拒绝。这是"阈值过滤"，正好用来单独收集错误日志。
- 文件命名 `error.created_on_%d{yyyy-MM-dd}.part_%i.log`，滚动策略和 INFO 一样。

### 6.5 全局 root 配置

```xml
<root level="info">
    <appender-ref ref="CONSOLE"/>
    <appender-ref ref="FILE_INFO"/>
    <appender-ref ref="FILE_ERROR"/>
</root>
```

- `root` 是根 logger，所有未单独配置的类都走这里。
- `level="info"`：全局最低级别设为 info，trace/debug 全局不输出。
- `appender-ref`：挂载三个输出目的地。一条日志会同时发往所有匹配的 appender——所以一条 info 日志会同时进控制台、FILE_INFO；一条 error 日志会同时进控制台、FILE_ERROR（FILE_INFO 的过滤器把它 DENY 了）。

---

## 七、运行与验证

### 7.1 启动

```sh
mvn spring-boot:run
```

### 7.2 观察控制台输出

启动后控制台会看到（因为 CONSOLE 的 LevelFilter 只放行 INFO）：

```
... Spring boot启动初始化了 XX 个 Bean    ← info 级别
... Spring boot启动初始化了 XX 个 Bean    ← warn 级别
... Spring boot启动初始化了 XX 个 Bean    ← error 级别
... 【SpringBootDemoLogbackApplication】启动异常：java.lang.ArithmeticException: / by zero ...
```

trace 和 debug 不会出现在控制台（被 root 的 info 级别和 CONSOLE 的过滤挡掉）。

### 7.3 观察文件输出

项目根目录会生成：

```
logs/demo-logback/
├── info.created_on_2026-09-03.part_0.log     ← info/warn 日志（不含 error）
└── error.created_on_2026-09-03.part_0.log    ← error 日志
```

打开文件能看到带时间戳、线程、类名、行号的完整日志。多打几次日志让文件超过 2MB，会看到 `part_1.log`、`part_2.log` 自动切分。

---

## 八、动手练习

1. **改全局级别**：把 `<root level="info">` 改成 `debug`，重启，观察控制台是否多了 debug 日志。
2. **改文件大小**：把 `maxFileSize` 改成 `1KB`，启动后多次触发日志，观察 `part_0`、`part_1` 快速切分。
3. **改保留天数**：把 `maxHistory` 改成 `7`，理解日志自动清理机制。
4. **自定义日志格式**：把 CONSOLE 的 pattern 改成 `%d{HH:mm:ss} %-5level %msg%n`，观察输出更简洁。
5. **给特定类单独配级别**：在 `logback-spring.xml` 加 `<logger name="com.xkcoding" level="debug"/>`，观察该包下日志变详细。
6. **用 `application.yml` 调级别**：删掉 `logback-spring.xml`，在 `application.yml` 加 `logging.level.com.xkcoding=debug`，体验 Spring Boot 的简化日志配置。

---

## 九、本模块知识点总结（结合实际开发详解）

日志是后端系统最重要的可观测性手段。下面把核心知识点放到真实开发场景里讲透。

### 9.1 日志门面 vs 实现：为什么 SLF4J + Logback 是标配？

**实际开发中怎么用？**

业务代码里**永远面向 SLF4J 接口打日志**（`@Slf4j` 注入的就是 SLF4J 的 `Logger`），不要直接 import Logback 的类。这样底层实现可以随时替换。

**为什么 Spring Boot 默认选 Logback？**

1. 性能比 Log4j 1.x 高数倍，异步日志性能优异。
2. 原生支持 SLF4J（Logback 和 SLF4J 同一作者，天然集成）。
3. 配置灵活，支持条件化、profile 区分环境。
4. Spring Boot 官方默认，开箱即用，零配置就能跑。

**什么时候要换 Log4j2？** 极高并发、对日志性能极致要求的场景，Log4j2 的异步 Logger 性能更好。但 95% 的项目 Logback 足够，没必要换。

**常见坑：**

- 同时引入多个日志实现（Logback + Log4j2），启动报错 `SLF4J: Class path contains multiple SLF4J bindings`。**一个项目只用一个实现。**
- 直接用 `System.out.println` 打日志：无法控制级别、无法落盘、无法格式化，生产环境绝对禁止。

### 9.2 日志级别怎么选？生产环境的级别策略

**实际开发的级别使用规范：**

| 级别 | 用法 | 生产是否开 |
| --- | --- | --- |
| `error` | 影响业务功能的异常、需要告警 | ✅ 开 |
| `warn` | 可恢复的异常、降级、业务边界 | ✅ 开 |
| `info` | 关键业务流水（下单、支付、登录） | ✅ 开，但别滥用 |
| `debug` | 方法入参出参、流程细节 | ❌ 关（生产环境关掉） |
| `trace` | 极细粒度跟踪 | ❌ 关 |

**生产环境的级别策略：**

1. **全局 info，关键包单独调**：`<root level="info">`，对需要排查的包临时开 debug：
   ```xml
   <logger name="com.xkcoding.logback" level="debug"/>
   ```
2. **用 profile 区分环境**：dev 环境开 debug 方便调试，prod 环境只开 info。`logback-spring.xml` 支持 `<springProfile>` 标签：
   ```xml
   <springProfile name="dev">
       <root level="debug">...</root>
   </springProfile>
   <springProfile name="prod">
       <root level="info">...</root>
   </springProfile>
   ```
3. **error 日志接告警**：error 级别日志通常接 ELK/Graylog（后续模块讲），配合告警系统第一时间通知。

**常见坑：**

- `info` 滥用：每行代码都 `log.info`，生产环境日志爆炸。info 只记"有业务意义的事件"，不是调试用。
- 用 `error` 打正常业务异常（如"用户名不存在"）：业务异常应该用 warn 或自定义异常处理，error 留给真正的系统故障。
- 生产环境开 debug：日志量暴增拖慢性能、撑爆磁盘。

### 9.3 文件滚动策略：防止日志撑爆磁盘

**实际开发的标准配置：**

```xml
<rollingPolicy class="ch.qos.logback.core.rolling.SizeAndTimeBasedRollingPolicy">
    <FileNamePattern>logs/app/%d{yyyy-MM-dd}.%i.log</FileNamePattern>
    <maxFileSize>100MB</maxFileSize>      <!-- 单文件最大 100MB -->
    <maxHistory>30</maxHistory>           <!-- 保留 30 天 -->
    <totalSizeCap>10GB</totalSizeCap>     <!-- 总量上限 10GB -->
</rollingPolicy>
```

**三个关键参数：**

- `maxFileSize`：单文件大小上限，超过就切分。生产常用 50-200MB，太小文件碎片多，太大单文件难打开。
- `maxHistory`：按天保留天数，超期自动删。根据合规要求定（金融行业可能要保留 1 年）。
- `totalSizeCap`：所有日志总大小上限，到了删最老的。这是兜底保护，**务必配置**，否则磁盘满了服务直接挂。

**常见坑：**

- 忘配 `totalSizeCap`：maxHistory 只在按天滚动时删过期文件，但如果某天日志暴涨，单天就撑满磁盘。
- `maxFileSize` 设太小（如 1KB）：文件碎片极多，排查时要翻几十个文件。
- 文件名用 `part_%i` 但没配按大小触发：`%i` 永远是 0，不会切分。必须用 `SizeAndTimeBasedFNATP` 或 `SizeAndTimeBasedRollingPolicy`。

### 9.4 日志格式 pattern：每个符号什么意思

本模块用了 `${CONSOLE_LOG_PATTERN}`（Spring Boot 默认），但理解 pattern 符号很重要，因为实际项目常自定义：

| 符号 | 含义 | 示例 |
| --- | --- | --- |
| `%d` 或 `%date` | 时间 | `2026-09-03 14:30:00.123` |
| `%thread` 或 `%t` | 线程名 | `http-nio-8080-exec-1` |
| `%-5level` | 级别（左对齐 5 字符） | `INFO ` |
| `%logger{36}` | logger 名（最长 36 字符） | `com.xkcoding.logback.App` |
| `%file:%line` | 文件名:行号 | `App.java:42` |
| `%msg` 或 `%m` | 日志消息 | `启动完成` |
| `%n` | 换行 | |
| `%clr{...}{green}` | 颜色（控制台用） | 绿色输出 |

**实际开发的 pattern 推荐：**

```xml
<!-- 控制台（带颜色，简洁） -->
<pattern>%d{yyyy-MM-dd HH:mm:ss.SSS} %clr(%5p) --- [%t] %cyan(%logger{40}) : %msg%n</pattern>

<!-- 文件（无颜色，完整，含文件行号方便定位） -->
<pattern>%d{yyyy-MM-dd HH:mm:ss.SSS} [%thread] %-5level %logger{50} %file:%line - %msg%n</pattern>
```

**常见坑：**

- 文件日志用带颜色的 pattern：颜色是 ANSI 转义码，写进文件会变成乱码字符（`[32m` 这种），文件日志**不要用 `%clr`**。
- `%file:%line` 看起来方便但会拖慢性能（要计算调用栈），生产环境可考虑去掉，靠 `%logger` 定位类即可。

### 9.5 `logback.xml` vs `logback-spring.xml`：用哪个？

Spring Boot 项目**必须用 `logback-spring.xml`**，不要用 `logback.xml`。

**区别：**

- `logback.xml`：Logback 原生配置名，被加载时 Spring Boot 还没初始化，**无法用 `<springProfile>`、`${...}` Spring 属性占位符**。
- `logback-spring.xml`：Spring Boot 专属，加载时机更晚，能用 Spring 的 profile 区分环境、能用 `application.yml` 里的变量。

**实际开发最佳实践：**

1. 文件名用 `logback-spring.xml`。
2. 用 `<springProfile>` 区分 dev/prod 的日志级别和输出。
3. 用 `<property>` 引用 `application.yml` 的值，实现"日志路径也走配置"：
   ```xml
   <springProperty name="LOG_PATH" source="logging.file.path" defaultValue="logs"/>
   ```

**常见坑：** 用了 `logback.xml` 然后抱怨 `<springProfile>` 不生效——改名即可。

### 9.6 `application.yml` 简化配置 vs XML 完整配置

Spring Boot 支持只用 `application.yml` 配日志，不用写 XML：

```yaml
logging:
  level:
    root: info
    com.xkcoding: debug
  file:
    name: logs/app.log
    path: /var/log
  pattern:
    console: "%d{HH:mm:ss} %-5level %logger{36} - %msg%n"
```

**怎么选？**

- **简单需求**（调级别、输出到单个文件）：用 `application.yml`，够用且简洁。
- **复杂需求**（多 appender、按级别分文件、复杂滚动策略）：用 `logback-spring.xml`，yml 表达不了。

**实际开发**：小项目用 yml，中大型项目用 XML。本模块用 XML 是因为它演示了 yml 做不到的"按级别分文件 + 复杂滚动"。

**常见坑：** 同时配了 yml 和 XML，两者冲突，以 XML 为准（XML 优先级更高），导致 yml 改了不生效还以为是 bug。

### 9.7 异步日志：高并发场景的必备优化

本模块用的是同步日志（默认），每条日志直接写文件，会阻塞业务线程。高并发场景应该用**异步日志**：

```xml
<appender name="ASYNC_FILE" class="ch.qos.logback.classic.AsyncAppender">
    <queueSize>512</queueSize>          <!-- 队列大小 -->
    <discardingThreshold>0</discardingThreshold>  <!-- 队列满时不丢弃任何级别 -->
    <appender-ref ref="FILE_INFO"/>     <!-- 包装同步 appender -->
</appender>
```

原理：业务线程把日志丢进队列就返回，专门的后台线程负责写文件，业务线程不被 IO 阻塞。

**最佳实践：**

- 普通项目同步够用，别过度优化。
- QPS 高、日志量大的服务用异步，但要注意队列满时的丢弃策略。
- 异步日志的缺点：宕机时队列里没落盘的日志会丢，所以 error 级别关键日志可考虑同步。

---

> 📌 **学习建议**：日志是后端除代码外最重要的资产。养成三个习惯：① 任何类都加 `@Slf4j`，关键业务打 info，异常 catch 里必打 error 带堆栈；② 永远用 `{}` 占位符，不用字符串拼接；③ 上线前检查日志级别和滚动策略，确保磁盘不会被撑爆。后续 `demo-log-aop` 模块会讲如何用 AOP 自动记录请求日志，`demo-graylog` 会讲日志集中收集，都是建立在本模块基础上的。
