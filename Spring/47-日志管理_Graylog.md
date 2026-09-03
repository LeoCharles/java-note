# 47 - Spring Boot 集成 Graylog 日志管理

> 对应项目模块：`demo-graylog`
> 前置知识：已学完 `05-日志集成_Logback`，了解 Logback 配置、Appender、日志级别
> 学习目标：理解集中式日志管理的价值，掌握用 GELF 协议把 Logback 日志推送到 Graylog，能在 Graylog 控制台检索、过滤、告警。

---

## 一、本模块要解决什么问题？

在 `05-日志集成_Logback` 里，我们学会了把日志写到文件、按天滚动。但这在**单体应用**阶段够用，一旦进入微服务/多实例部署，立刻暴露三个痛点：

1. **日志散落各处**：10 个服务实例，每个实例一台机器，日志分别躺在 10 台机器的磁盘上。出了问题要排查，你得逐台 SSH 上去 `grep`——这在大规模集群下几乎不可行。
2. **无法跨服务追踪**：一个用户请求可能经过 A→B→C 三个服务，日志分散在三台机器上，你无法把它们串起来看完整链路。
3. **无法实时检索告警**：文件日志是"死"的，不能搜索、不能统计、不能在 ERROR 日志出现时自动告警。

**Graylog 解决的就是"日志集中化"**：所有服务把日志推送到 Graylog 这个中心节点，Graylog 负责存储、索引、检索、可视化、告警。你在一个 Web 界面里就能搜遍所有服务的日志。

> 💡 前端类比：Graylog 之于后端日志，就像 **Sentry** 之于前端错误监控、**Datadog** 之于全链路监控。前端同学用 Sentry 把所有线上 JS 报错聚合到一个面板查看，Graylog 做的是同样的事，只是面向后端 Java 日志。也可以类比成"日志版的 Kibana"——事实上 Graylog 底层就用 Elasticsearch 做搜索。

**和 ELK（Elasticsearch + Logstash + Kibana）的关系**：两者目标相同（集中式日志），技术栈类似（都用 ES 做存储）。ELK 用 Logstash/Filebeat 采集，Kibana 展示；Graylog 自带采集端点（GELF/Syslog）和 Web 界面，更"开箱即用"。本模块用 Graylog 是因为它的 GELF 协议和 Logback 集成更简洁。

---

## 二、先搞懂 Graylog 的架构

Graylog 自己不是存储引擎，它是一个"日志管理服务器"，依赖两个外部组件：

```
应用服务（Logback + GELF Appender）
        │ UDP/TCP 推送日志
        ▼
   Graylog Server ──→ Elasticsearch（存储 + 全文索引）
        │
        ├──→ MongoDB（存 Graylog 自身的元数据：用户、配置、流规则）
        │
        ▼
   Web 界面（:9000）── 搜索/过滤/告警
```

| 组件 | 作用 | 类比 |
| --- | --- | --- |
| **Graylog Server** | 接收日志、解析、转发存储、提供 Web 界面和 API | 日志版的 Nginx + 应用服务器 |
| **Elasticsearch** | 存储日志原文 + 建倒排索引，支撑全文检索 | 日志版的搜索引擎（见 `39-搜索引擎_ElasticSearch`） |
| **MongoDB** | 存 Graylog 自己的配置（用户、Input、Stream、Dashboard） | Graylog 的"数据库" |
| **GELF** | Graylog Extended Log Format，日志传输协议 | 日志版的 JSON-RPC |

> 💡 前端类比：这就像一个前端监控平台 = 采集 SDK（Logback GELF Appender）+ 数据接收服务（Graylog Server）+ 搜索引擎（ES）+ 配置存储（MongoDB）。你写的业务代码只关心"发日志"，剩下全交给这套基础设施。

---

## 三、项目结构

```
demo-graylog/
├── pom.xml
└── src/main/
    ├── java/com/xkcoding/graylog/
    │   ├── SpringBootDemoGraylogApplication.java   # 启动类
    │   └── (无 Controller，本模块纯演示日志推送)
    └── resources/
        ├── application.yml                          # 只配了应用名
        └── logback-spring.xml                       # 核心：GELF Appender 配置
```

注意：本模块**没有 Controller**，因为它的目的不是演示业务接口，而是演示"日志如何被推送到 Graylog"。启动类启动后，Spring Boot 自身的启动日志、context 初始化日志就会通过 GELF Appender 推送出去，在 Graylog 面板就能看到。

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

    <!-- 提供logback传输日志到graylog的依赖 -->
    <dependency>
        <groupId>de.siegmar</groupId>
        <artifactId>logback-gelf</artifactId>
        <version>2.0.0</version>
    </dependency>
</dependencies>
```

关键就一个第三方依赖：`logback-gelf`。

- Spring Boot 默认自带 Logback（见 `05-日志集成_Logback`），所以不用单独引 Logback。
- `logback-gelf` 是一个第三方库（作者 osiegmar），它提供了 Logback 的 **GELF Appender**——把 Logback 产生的日志事件，按 GELF 协议格式化后，通过 UDP/TCP 发送到 Graylog Server。
- 没有这个依赖，Logback 只能往控制台/文件写；有了它，Logback 就多了一个"往 Graylog 推"的输出通道。

> 💡 前端类比：这就像给 `winston` 加一个 `winston-transport-sentry` 的 transport，日志就能自动上报到 Sentry。`logback-gelf` 就是 Logback 的"Graylog transport"。

---

## 五、逐行拆解 application.yml

```yaml
spring:
  application:
    name: graylog
```

只配了一项：`spring.application.name: graylog`。这个值会在 `logback-spring.xml` 里被读取，作为日志的一个静态字段（`app_name`）推送到 Graylog，方便在 Graylog 里区分"这条日志来自哪个应用"。

> 💡 这体现了集中式日志的一个核心设计：**日志要带"来源标识"**。多个服务往同一个 Graylog 推日志，如果没有 `app_name` 字段，你根本分不清哪条日志属于哪个服务。

---

## 六、核心：逐行拆解 logback-spring.xml

这是本模块的全部精髓。我们在 `05-日志集成_Logback` 学过 Logback 的基本配置（ConsoleAppender、RollingFileAppender），这里新增了一个 **GELF Appender**。

### 6.1 配置文件骨架

```xml
<configuration scan="true" scanPeriod="60 seconds">
```

- `scan="true" scanPeriod="60 seconds"`：开启热加载，每 60 秒检查一次配置文件变更并自动应用。生产环境改日志级别不用重启应用。

### 6.2 日志格式定义

```xml
<!-- 彩色日志格式（控制台用） -->
<property name="CONSOLE_LOG_PATTERN"
          value="${CONSOLE_LOG_PATTERN:-%clr(%d{yyyy-MM-dd HH:mm:ss.SSS}){faint} %clr(${LOG_LEVEL_PATTERN:-%5p}) %clr(${PID:- }){magenta} %clr(---){faint} %clr([%15.15t]){faint} %clr(%-40.40logger{50}){cyan} %clr(:){faint} %file:%line - %m%n${LOG_EXCEPTION_CONVERSION_WORD:-%wEx}}"/>

<!-- graylog全日志格式 -->
<property name="GRAY_LOG_FULL_PATTERN"
          value="%n%d{yyyy-MM-dd HH:mm:ss.SSS} [%thread] [%logger{50}] %file:%line%n%-5level: %msg%n"/>

<!-- graylog简化日志格式 -->
<property name="GRAY_LOG_SHORT_PATTERN"
          value="%m%nopex"/>
```

GELF 协议里每条日志分 **short_message（短消息）** 和 **full_message（完整消息）** 两部分：

- `GRAY_LOG_SHORT_PATTERN` → 映射到 short_message，只放核心内容 `%m`（消息本身），`%nopex` 表示不附加异常堆栈（避免短消息过长）。
- `GRAY_LOG_FULL_PATTERN` → 映射到 full_message，包含时间、线程、logger、文件行号、级别、完整消息，在 Graylog 点开一条日志时看到的就是这个。

> 💡 前端类比：这就像 Sentry 里每条 error 既有"标题"（short）又有"详情堆栈"（full）。短消息用于列表预览，全消息用于深入排查。

### 6.3 读取应用名作为日志字段

```xml
<springProperty scope="context" name="APP_NAME" source="spring.application.name"/>
```

- `<springProperty>` 是 Logback 对 Spring Boot 的扩展标签，能从 `application.yml` 读取配置值到 Logback 上下文变量。
- 这里把 `spring.application.name`（值为 `graylog`）读到变量 `APP_NAME`，后面 GELF Appender 会把它作为静态字段推送。

### 6.4 控制台 Appender（复习）

```xml
<appender name="STDOUT" class="ch.qos.logback.core.ConsoleAppender">
    <encoder class="ch.qos.logback.classic.encoder.PatternLayoutEncoder">
        <pattern>${CONSOLE_LOG_PATTERN}</pattern>
        <charset>utf8</charset>
    </encoder>
</appender>
```

这个在 `05-日志集成_Logback` 讲过，控制台彩色输出，不再赘述。

### 6.5 GELF Appender（本模块核心）

```xml
<appender name="GELF" class="de.siegmar.logbackgelf.GelfUdpAppender">
    <graylogHost>localhost</graylogHost>
    <graylogPort>12201</graylogPort>
    <maxChunkSize>508</maxChunkSize>
    <useCompression>true</useCompression>
    <encoder class="de.siegmar.logbackgelf.GelfEncoder">
        <includeRawMessage>true</includeRawMessage>
        <includeMarker>true</includeMarker>
        <includeMdcData>true</includeMdcData>
        <includeCallerData>false</includeCallerData>
        <includeRootCauseData>false</includeRootCauseData>
        <includeLevelName>true</includeLevelName>
        <shortPatternLayout class="ch.qos.logback.classic.PatternLayout">
            <pattern>${GRAY_LOG_SHORT_PATTERN}</pattern>
        </shortPatternLayout>
        <fullPatternLayout class="ch.qos.logback.classic.PatternLayout">
            <pattern>${GRAY_LOG_FULL_PATTERN}</pattern>
        </fullPatternLayout>
        <staticField>app_name:${APP_NAME}</staticField>
        <staticField>os_arch:${os.arch}</staticField>
        <staticField>os_name:${os.name}</staticField>
        <staticField>os_version:${os.version}</staticField>
    </encoder>
</appender>
```

逐段拆解：

**传输层**：
- `class="de.siegmar.logbackgelf.GelfUdpAppender"`：用 UDP 传输（还有个 `GelfTcpAppender` 用 TCP）。UDP 快但不保证送达，TCP 可靠但有额外开销。
- `<graylogHost>localhost</graylogHost>`：Graylog Server 地址。
- `<graylogPort>12201</graylogPort>`：GELF UDP 监听端口（Graylog 默认）。
- `<maxChunkSize>508</maxChunkSize>`：GELF over UDP 有分块（chunk）机制，因为单条 UDP 数据报有大小限制（约 65507 字节），大日志要拆成多个 chunk 发送。508 是一个保守值，避免 IP 分片。
- `<useCompression>true</useCompression>`：压缩日志再发送，节省带宽。

**编码器 GelfEncoder**（把 Logback 日志事件转成 GELF 格式）：
- `includeRawMessage`：是否包含原始消息。
- `includeMarker`：是否包含 Logback Marker（标记，用于分类）。
- `includeMdcData`：是否包含 MDC（Mapped Diagnostic Context，线程上下文映射）数据。MDC 非常重要——你可以在 MDC 里放 `traceId`、`userId`，日志就会带上这些字段，在 Graylog 里能按 traceId 检索一条请求的全部日志。
- `includeCallerData`：是否包含调用者信息（类名、方法名、行号）。**关闭**了，因为获取调用者信息要用反射，性能开销大，生产环境一般关。
- `includeRootCauseData`：是否包含根因分析。关闭。
- `includeLevelName`：是否包含级别名（INFO/ERROR 等）。

**消息格式**：
- `shortPatternLayout` → short_message，用前面定义的 `GRAY_LOG_SHORT_PATTERN`。
- `fullPatternLayout` → full_message，用 `GRAY_LOG_FULL_PATTERN`。

**静态字段**（staticField）：
- `<staticField>app_name:${APP_NAME}</staticField>`：每条日志都带上 `app_name=graylog`。
- `os_arch`、`os_name`、`os_version`：系统信息，JVM 系统属性。

这些静态字段在 Graylog 里就成了日志的"字段"（field），可以用来过滤——比如"只看 app_name 是 graylog 的日志"。

### 6.6 Root Logger 绑定两个 Appender

```xml
<root level="INFO">
    <appender-ref ref="STDOUT"/>
    <appender-ref ref="GELF" />
</root>
```

- root 级别 INFO。
- 同时引用 STDOUT（控制台）和 GELF（Graylog）两个 Appender——**一条日志既打到控制台，又推送到 Graylog**。这是常见做法：本地开发看控制台，线上靠 Graylog。

### 6.7 各框架日志级别降噪

后面一大段 `<logger name="...">` 是给各种第三方框架（MyBatis、Spring、Druid、Netflix 等）设置级别，减少噪音日志。这部分在 `05-日志集成_Logback` 讲过原理，这里不重复。重点是：

```xml
<!-- 业务日志 -->
<Logger name="com.xkcoding" level="DEBUG"/>
```

业务代码包开 DEBUG，方便排查；框架包压到 INFO/WARN，减少噪音。这是日志治理的基本原则。

---

## 七、Graylog Server 端的环境准备

本模块代码很简单，但要跑通需要先启动 Graylog Server。README 提供了 `docker-compose.yml`：

```yaml
version: '2'
services:
  mongodb:
    image: mongo:3
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch-oss:6.6.1
    environment:
      - http.host=0.0.0.0
      - transport.host=localhost
      - network.host=0.0.0.0
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
    ulimits:
      memlock:
        soft: -1
        hard: -1
    mem_limit: 1g
  graylog:
    image: graylog/graylog:3.0
    environment:
      - GRAYLOG_PASSWORD_SECRET=somepasswordpepper       # 加密盐值，至少16字符
      - GRAYLOG_ROOT_USERNAME=admin
      - GRAYLOG_ROOT_PASSWORD_SHA2=8c6976e5...          # 密码的SHA256
      - GRAYLOG_HTTP_EXTERNAL_URI=http://127.0.0.1:9000/
      - GRAYLOG_ROOT_TIMEZONE=Asia/Shanghai
    ports:
      - 9000:9000      # Web 界面
      - 12201:12201/udp # GELF UDP（应用往这里推日志）
```

关键点：

- **三个服务**：mongodb（元数据）、elasticsearch（日志存储索引）、graylog（主服务）。
- **GRAYLOG_PASSWORD_SECRET**：加密盐值，必须设，否则启动失败。
- **GRAYLOG_ROOT_PASSWORD_SHA2**：admin 密码的 SHA256。默认密码 `admin` 的 SHA256 就是那个固定串。生产环境务必改。
- **端口 12201/udp**：这就是 `logback-spring.xml` 里 `graylogPort` 指向的端口，应用通过它推送 GELF 日志。

> 💡 前端类比：这就像你用 Sentry 要先在 Sentry 平台建一个项目、拿到 DSN，应用端配好 DSN 才能上报。Graylog 这里是先启动 Server、开放 GELF Input 端口，应用端配好 host:port 才能推送。

---

## 八、运行与验证

### 8.1 启动 Graylog Server

```sh
docker-compose up -d
```

等待 mongodb、elasticsearch、graylog 三个容器启动完成（首次拉镜像较慢）。访问 `http://localhost:9000`，用 `admin/admin` 登录。

### 8.2 配置 GELF Input（接收日志来源）

Graylog 启动后，默认没有开放日志接收端点，需要手动添加：

1. 顶部菜单 **System → Inputs**
2. 选择 **GELF UDP**，点 **Launch new input**
3. 填 Title（如 `gelf-udp`）、Port（`12201`）、Bind address（`0.0.0.0`）
4. 保存启动

这一步告诉 Graylog："在 12201 端口监听 UDP，收到的数据按 GELF 解析"。不配这步，应用推送的日志会被 Graylog 丢弃。

### 8.3 启动 Spring Boot 应用

```sh
mvn spring-boot:run
```

应用启动后，Spring Boot 的启动日志（`Starting SpringBootDemoGraylogApplication...` 等）就会通过 GELF Appender 推送到 Graylog。

### 8.4 在 Graylog 查看日志

回到 Graylog Web 界面，顶部 **Search** 菜单，就能看到实时流入的日志条目。每条日志包含：

- `timestamp`：时间戳
- `message`：短消息
- `full_message`：完整消息（点开看）
- `app_name`：`graylog`（我们配的静态字段）
- `os_name`、`os_arch`：系统信息
- `level`：日志级别

可以在搜索框输入 `app_name:graylog` 过滤，或 `level:ERROR` 只看错误。

---

## 九、动手练习

1. **加业务日志**：写一个 Controller，方法里用 `@Slf4j` 打几条不同级别的日志，启动后访问接口，在 Graylog 搜索验证能否看到。
2. **用 MDC 加 traceId**：在拦截器里给每个请求生成 `traceId` 放入 MDC（`MDC.put("traceId", id)`），验证 Graylog 里每条日志是否带 `traceId` 字段，并尝试按 traceId 搜索一条请求的全部日志。
3. **切换 UDP 为 TCP**：把 `GelfUdpAppender` 改成 `GelfTcpAppender`，对比两者差异（UDP 可能丢日志，TCP 不丢但慢）。
4. **加静态字段**：在 GELF Appender 加 `<staticField>env:prod</staticField>`，在 Graylog 按 `env:prod` 过滤。
5. **模拟多应用**：复制一份应用改 `spring.application.name` 为 `order-service`，两个应用同时往 Graylog 推日志，在面板按 `app_name` 区分。
6. **配置告警**（进阶）：在 Graylog 配置 Stream，当某条 `level:ERROR` 日志出现时发邮件告警。

---

## 十、本模块知识点总结（结合实际开发详解）

集中式日志管理是微服务架构的"标配基础设施"。下面把核心知识点放到真实开发场景里讲透。

### 10.1 集中式日志 vs 本地文件日志：何时该上 Graylog？

**实际开发中的选择标准：**

| 场景 | 推荐方案 | 理由 |
| --- | --- | --- |
| 单体应用、1-2 个实例 | Logback 文件日志 | 日志量小，SSH 上去 grep 够用，上 Graylog 是杀鸡用牛刀 |
| 微服务、3+ 实例 | Graylog / ELK | 日志分散，必须集中才能检索 |
| 需要实时告警 | Graylog / ELK | 文件日志无法主动告警 |
| 需要跨服务链路追踪 | Graylog + traceId / Skywalking | 文件日志无法跨服务串联 |

**常见坑：**

- **过早引入**：小项目就上 Graylog，结果维护 Graylog（它依赖 ES+Mongo，本身吃资源）的成本比写业务还高。**先有痛点再上工具**。
- **过晚引入**：微服务已经几十个了还在 grep，排查一个问题要半天。规模到了就该上。
- **只推不治**：日志全推到 Graylog 但没有治理——没有统一格式、没有 traceId、没有字段规范，搜起来还是乱。集中式日志的价值在于**可检索**，而可检索的前提是**日志有结构化字段**。

### 10.2 GELF 协议：为什么不用普通 JSON？

GELF（Graylog Extended Log Format）是 Graylog 专为日志传输设计的协议，相比直接发 JSON 有几个优势：

- **分块（Chunking）**：UDP 有数据报大小限制，GELF 支持把超大日志自动拆成多个 chunk，Graylog 端自动重组。普通 JSON over UDP 做不到。
- **压缩**：GELF 支持 zlib/gzip 压缩，节省带宽。
- **结构化字段**：GELF 天然支持 `additional fields`（额外字段），Logback 的 `staticField`、MDC 数据都会变成 GELF 的额外字段，在 Graylog 里可检索。

**实际开发建议：**

- 如果用 Graylog，优先用 GELF（本模块的方式），而不是 Syslog 或纯 JSON。
- 如果用 ELK 体系，对应的是用 Logstash/Beats 采集，协议不同但思路一致。

**常见坑：**

- UDP 模式可能丢日志：网络拥堵时 UDP 不保证送达，排查问题时发现"少了几条日志"。**对日志完整性要求高的场景用 TCP**（`GelfTcpAppender`）。
- 端口配错：`logback-spring.xml` 的 `graylogPort` 必须和 Graylog Input 配置的端口、协议（UDP/TCP）完全一致，否则日志发出去 Graylog 收不到。

### 10.3 MDC：集中式日志的"灵魂字段"

本模块 GELF Encoder 开了 `includeMdcData=true`。MDC（Mapped Diagnostic Context）是 Logback 提供的线程级键值对上下文，是集中式日志**最值钱**的特性。

**实际开发中的标准用法：**

```java
@Component
public class TraceInterceptor implements HandlerInterceptor {
    @Override
    public boolean preHandle(HttpServletRequest req, ...) {
        String traceId = UUID.randomUUID().toString();
        MDC.put("traceId", traceId);      // 请求开始放入
        MDC.put("userId", getUserId(req));
        return true;
    }
    @Override
    public void afterCompletion(...) {
        MDC.clear();                       // 请求结束清理，防止线程池复用导致串号
    }
}
```

这样每条日志都会带上 `traceId`、`userId`。在 Graylog 里搜 `traceId:xxx`，就能看到这条请求经过的所有日志——即使它调用了多个服务（只要每个服务都往 MDC 放同一个 traceId 并推到 Graylog）。

> 💡 前端类比：MDC 类似 React 的 Context 或请求级的全局变量，但它是线程绑定的。`traceId` 的作用就像前端给每个 fetch 请求打的 request-id，用来把分散的日志串成一条链路。

**常见坑：**

- **忘清理**：线程池复用线程，上一个请求的 MDC 没清，下个请求的日志会带上别人的 traceId。**务必在 `afterCompletion` 里 `MDC.clear()`**。
- **异步失效**：`@Async` 或线程池里的子线程**不会自动继承**父线程的 MDC。需要用 `MDCContext` 或装饰器把 MDC 传递到子线程，否则异步日志没有 traceId。

### 10.4 日志的"静态字段"与可检索性

本模块用 `<staticField>` 给每条日志加了 `app_name`、`os_name` 等字段。这些字段在 Graylog 里成为可检索的"维度"。

**实际开发的字段设计原则：**

1. **必备字段**：`app_name`（应用名）、`env`（环境）、`instance`（实例号）、`traceId`、`userId`。
2. **业务字段**：`orderId`、`module`（业务模块），方便按业务维度检索。
3. **避免过多**：每多一个字段，ES 索引就多一份开销。不要把整条日志都拆成字段，只拆"需要检索/聚合的"。

**最佳实践：** 在团队层面约定一套**日志字段规范**，所有服务推送日志时都带相同语义的字段，这样在 Graylog 里能跨服务统一检索。

### 10.5 Graylog 的 Input / Stream / Dashboard 三层概念

**实际开发中你会用到的 Graylog 三层能力：**

| 概念 | 作用 | 类比 |
| --- | --- | --- |
| **Input** | 定义日志接收端点（端口+协议） | 日志版的"监听端口" |
| **Stream** | 按规则把日志分流（如 ERROR 流、订单服务流） | 日志版的"路由/过滤器" |
| **Dashboard** | 把常用查询聚合成图表 | 日志版的"Grafana 面板" |

**典型工作流：**

1. 配 Input 接收日志。
2. 建 Stream 把 `level:ERROR` 的日志分流，并配告警（邮件/钉钉）。
3. 建 Dashboard 统计"每小时 ERROR 数量""各服务日志量占比"。

**常见坑：** 很多人只配了 Input 就完事，没用 Stream 做告警，结果线上报错要等用户投诉才知道。**集中式日志不上告警等于白搭**。

### 10.6 Graylog vs ELK vs 云服务：怎么选？

| 方案 | 优点 | 缺点 | 适用场景 |
| --- | --- | --- | --- |
| **Graylog** | 开箱即用、GELF 集成简单、自带 UI | 生态比 ELK 小、扩展性一般 | 中小规模、自建 |
| **ELK** | 生态丰富、可定制性强、和 ES 深度整合 | 搭建复杂、资源消耗大、学习曲线陡 | 大规模、需要深度定制 |
| **云服务**（阿里云 SLS、AWS CloudWatch） | 免运维、开箱即用、按量付费 | 数据上云、长期成本高、有厂商锁定 | 不想运维、中小项目 |
| **Loki**（Grafana 出品） | 轻量、和 Prometheus/Grafana 一体化、成本低 | 全文检索能力弱于 ES | 已用 Grafana 体系、日志量不大 |

**实际开发建议：** 中小团队自建优先选 Graylog（比 ELK 简单）；不想运维直接用云服务（SLS/CloudWatch）；已经在用 Grafana 监控的，Loki 是顺手的补充。

### 10.7 日志推送的性能考量

把日志推送到远程 Graylog 会增加应用的开销，实际开发要注意：

1. **异步推送**：GELF Appender 默认是同步发送（UDP 相对快，TCP 会阻塞）。高并发下建议用 Logback 的 `AsyncAppender` 包一层，把网络 IO 放到独立线程，避免拖慢业务。
2. **关闭 CallerData**：本模块 `includeCallerData=false`，获取调用栈要用反射+遍历栈帧，开销很大，生产环境务必关。
3. **控制日志量**：不要把 DEBUG 日志全推到 Graylog（会撑爆 ES），生产环境只推 INFO 以上，DEBUG 留本地文件。
4. **网络故障容错**：Graylog 挂了，应用不能因为日志发不出去而崩溃。UDP 模式天然容错（发不出去就丢），TCP 模式要配好超时和重试策略，避免阻塞主流程。

**常见坑：** 上线后发现应用变慢，排查发现是 GELF TCP Appender 同步发送、Graylog 所在机器负载高导致网络阻塞，拖慢了所有打日志的线程。**日志 IO 永远不能阻塞业务线程**，务必异步化。

---

> 📌 **学习建议**：集中式日志是后端"可观测性"（Observability）三大支柱之一（日志、指标、链路追踪）。本模块学的 Graylog 解决的是"日志"这一支柱。建议你把它和前面的 `05-日志集成_Logback`、`03-端点监控_Actuator` 串起来理解：Logback 负责产生日志，GELF Appender 负责传输日志，Graylog 负责存储和检索日志，Actuator 负责暴露运行时指标——四者合起来就是一个完整的后端可观测性体系。作为前端转后端的工程师，把这套"日志从产生到消费"的全链路搞清楚，你排查线上问题的能力就会有质的提升。
