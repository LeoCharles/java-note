# 04 - Spring Boot 可视化管控（Admin Server & Client）

> 对应项目模块：`demo-admin`（含子模块 `admin-server`、`admin-client`）
> 前置知识：已学完 `01-HelloWorld`、`02-Properties`，了解启动类、配置文件、`@RestController` 基本用法
> 学习目标：理解 Spring Boot Admin 的"服务端收集 + 客户端上报"架构，能搭建 Admin 服务端可视化监控多个 Spring Boot 应用，并让业务应用作为客户端注册上报。

---

## 一、本模块要解决什么问题？

在 `demo-actuator`（上一篇）里，我们用 Actuator 端点拿到了单个应用的运行时数据（健康、内存、线程、日志……）。但 Actuator 返回的是**原始 JSON**，而且每个应用要单独访问，当你的微服务从 1 个变成 10 个、50 个时：

- 你记不清哪个服务跑在哪个端口
- 想看某个服务的健康状态，得手动拼 URL 去访问
- 没有统一的面板对比所有服务的状态
- 服务挂了你不能第一时间发现

**Spring Boot Admin（SBA）** 就是解决这个问题的——它提供一个**可视化 Web 面板**，把所有注册上来的 Spring Boot 应用的 Actuator 数据集中展示，还能做：服务上下线通知、日志级别动态调整、线程 dump、JVM 堆 dump、健康告警等。

> 💡 前端类比：Actuator 像每个服务自带的"devtools"，Spring Boot Admin 像一个"运维大盘（Dashboard）"——把分散在各服务的 devtools 数据聚合成一个统一面板，类似 Grafana 之于 Prometheus。

本模块包含两个子模块，体现典型的 **Server + Client** 架构：

| 子模块 | 角色 | 端口 | 职责 |
| --- | --- | --- | --- |
| `admin-server` | 监控服务端 | 8000 | 提供可视化面板，接收客户端注册、拉取客户端 Actuator 数据 |
| `admin-client` | 被监控的业务应用 | 8080 | 普通业务应用，启动时向 server 注册自己，暴露 Actuator 端点供 server 拉取 |

---

## 二、项目结构

```
demo-admin/
├── pom.xml                          # 父 POM（聚合 + 管控 SBA 版本）
├── admin-server/                    # 监控服务端
│   ├── pom.xml
│   └── src/main/
│       ├── java/com/xkcoding/admin/server/
│       │   └── SpringBootDemoAdminServerApplication.java   # @EnableAdminServer
│       └── resources/application.yml   # port: 8000
└── admin-client/                    # 被监控的客户端
    ├── pom.xml
    └── src/main/
        ├── java/com/xkcoding/admin/client/
        │   ├── SpringBootDemoAdminClientApplication.java   # 普通启动类
        │   └── controller/IndexController.java            # 一个测试接口
        └── resources/application.yml   # 配置 server 地址 + Actuator 暴露
```

注意 `demo-admin/pom.xml` 的 `<packaging>pom</packaging>`——它本身是个聚合工程，不产出代码，只管理两个子模块。这种"父工程聚合 + 子模块分立"的结构，在多角色项目中很常见。

---

## 三、父 POM：统一管控 Spring Boot Admin 版本

`demo-admin/pom.xml`：

```xml
<artifactId>demo-admin</artifactId>
<packaging>pom</packaging>

<properties>
    <spring-boot-admin.version>2.1.0</spring-boot-admin.version>
</properties>

<modules>
    <module>admin-client</module>
    <module>admin-server</module>
</modules>

<dependencyManagement>
    <dependencies>
        <dependency>
            <groupId>de.codecentric</groupId>
            <artifactId>spring-boot-admin-dependencies</artifactId>
            <version>${spring-boot-admin.version}</version>
            <type>pom</type>
            <scope>import</scope>
        </dependency>
    </dependencies>
</dependencyManagement>
```

**关键点：**

1. **`de.codecentric`**：Spring Boot Admin 是第三方（德国 codecentric 公司）开源的，不在 Spring 官方旗下，所以 groupId 不是 `org.springframework.boot`。
2. **`spring-boot-admin-dependencies`**：这是一个 BOM（Bill of Materials），用 `<scope>import</scope>` 导入后，子模块引 SBA 相关依赖时不用写版本号，版本由这里的 `2.1.0` 统一管控。这和 Spring Boot 官方的 `spring-boot-dependencies` 用法完全一样。
3. **版本对齐**：SBA 2.1.0 对应 Spring Boot 2.1.x（本项目根 POM 用的就是 2.1.0.RELEASE）。SBA 版本必须和 Spring Boot 主版本匹配，否则启动报错。这是最常踩的坑之一。

> 💡 前端类比：BOM 像 monorepo 根 `package.json` 里的 `dependencies` 版本锁定，子包只写包名不写版本，由根统一管。

---

## 四、Admin Server：搭建监控服务端

### 4.1 依赖 `admin-server/pom.xml`

```xml
<dependencies>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-web</artifactId>
    </dependency>

    <dependency>
        <groupId>de.codecentric</groupId>
        <artifactId>spring-boot-admin-starter-server</artifactId>
    </dependency>

    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-test</artifactId>
        <scope>test</scope>
    </dependency>
</dependencies>
```

- `spring-boot-starter-web`：Server 本身也是个 Web 应用，要提供可视化面板页面。
- `spring-boot-admin-starter-server`：SBA 服务端核心依赖，包含前端面板资源 + 后端注册/拉取逻辑。注意没写版本号——由父 POM 的 BOM 管。

### 4.2 启动类

```java
@EnableAdminServer
@SpringBootApplication
public class SpringBootDemoAdminServerApplication {

    public static void main(String[] args) {
        SpringApplication.run(SpringBootDemoAdminServerApplication.class, args);
    }
}
```

**核心就一个注解 `@EnableAdminServer`**。它开启 SBA 的服务端功能：自动配置注册中心、数据拉取调度、面板控制器等。加了这个注解，这个普通 Spring Boot 应用就变成了 Admin 监控服务端。

> 💡 前端类比：这像在 Express 里 `app.use('/admin', adminPanelMiddleware)`——一个中间件/注解就把面板挂上去了。`@EnableAdminServer` 背后是一组 `@Import` 导入的自动配置类，把面板所需的 Bean 全部注册好。

### 4.3 配置 `admin-server/application.yml`

```yaml
server:
  port: 8000
```

服务端配置极简，只设端口 8000（避开业务应用常用的 8080）。启动后访问 `http://localhost:8000` 就能看到 Admin 面板（此时还没客户端注册，是空的）。

---

## 五、Admin Client：让业务应用被监控

### 5.1 依赖 `admin-client/pom.xml`

```xml
<dependencies>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-web</artifactId>
    </dependency>

    <dependency>
        <groupId>de.codecentric</groupId>
        <artifactId>spring-boot-admin-starter-client</artifactId>
    </dependency>

    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-security</artifactId>
    </dependency>

    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-test</artifactId>
        <scope>test</scope>
    </dependency>
</dependencies>
```

- `spring-boot-admin-starter-client`：客户端依赖，启动时自动向配置的 server 地址注册自己，并周期性上报心跳。它内部依赖了 `spring-boot-starter-actuator`（所以不用单独引 actuator）。
- `spring-boot-starter-security`：Spring Security，这里用来给 Actuator 端点加密码保护——因为 server 要通过 HTTP 拉取 client 的端点数据，端点暴露了敏感信息，必须鉴权。

### 5.2 启动类（普通启动类）

```java
@SpringBootApplication
public class SpringBootDemoAdminClientApplication {

    public static void main(String[] args) {
        SpringApplication.run(SpringBootDemoAdminClientApplication.class, args);
    }
}
```

注意：**客户端启动类没有任何特殊注解**。它就是一个普通 Spring Boot 应用，靠引入 `spring-boot-admin-starter-client` 依赖 + yml 配置就自动具备了注册能力。这就是 Starter 的魔力——"约定优于配置"，引依赖即启用。

### 5.3 测试控制器

```java
@RestController
public class IndexController {
    @GetMapping(value = {"", "/"})
    public String index() {
        return "This is a Spring Boot Admin Client.";
    }
}
```

一个普通接口，证明这是个正常业务应用。`@GetMapping(value = {"", "/"})` 同时映射根路径和空路径，访问 `http://localhost:8080/demo/` 会返回这句话。

### 5.4 配置 `admin-client/application.yml`（核心）

```yaml
server:
  port: 8080
  servlet:
    context-path: /demo
spring:
  application:
    name: spring-boot-demo-admin-client
  boot:
    admin:
      client:
        url: "http://localhost:8000/"
        instance:
          metadata:
            user.name: ${spring.security.user.name}
            user.password: ${spring.security.user.password}
  security:
    user:
      name: xkcoding
      password: 123456
management:
  endpoint:
    health:
      show-details: always
  endpoints:
    web:
      exposure:
        include: "*"
```

逐段拆解：

**① `spring.application.name`**：应用名，注册到 server 后面板上显示的就是这个名字。不设会用随机 ID，难以辨认。**生产必设**。

**② `spring.boot.admin.client.url`**：Admin Server 的地址，客户端启动时往这里发注册请求。这是 client 能找到 server 的关键配置。

**③ `spring.boot.admin.client.instance.metadata`**：注册时携带的元数据，这里是把 client 端点的访问凭证（用户名/密码）告诉 server，server 拉取端点数据时要带上这个凭证。值用 `${spring.security.user.name}` 引用下面的 security 配置，避免重复写。

**④ `spring.security.user`**：Spring Security 默认生成的用户名/密码（`xkcoding` / `123456`）。引入 `spring-boot-starter-security` 后，所有接口（包括 Actuator 端点）默认都要认证，这里配置一个内存用户。

**⑤ `management.endpoints.web.exposure.include: "*"`**：Actuator 端点暴露配置，`*` 表示暴露所有端点（默认只暴露 `health` 和 `info`）。server 要拉取完整数据，必须开放更多端点。

**⑥ `management.endpoint.health.show-details: always`**：健康检查端点显示详情（磁盘、线程池等），默认 `never` 不显示。

> 💡 前端类比：这套配置像给服务装了个"上报 Agent"——启动时往 `url` 那发个注册请求说"我是 `name`，来 `8000` 端口拉我的数据吧，账号密码在这里"。server 收到后周期性 HTTP 请求 client 的 Actuator 端点拉数据展示。

---

## 六、运行与验证

### 6.1 启动顺序（重要！）

**必须先启动 server，再启动 client**。因为 client 启动时会立即向 server 注册，如果 server 没起，client 会重试一段时间后放弃（虽然不影响 client 自身运行，但面板上看不到）。

```sh
# 1. 先启动 server（端口 8000）
cd demo-admin/admin-server
mvn spring-boot:run

# 2. 再启动 client（端口 8080）
cd demo-admin/admin-client
mvn spring-boot:run
```

### 6.2 访问面板

浏览器打开 `http://localhost:8000`，看到 SBA 面板：

- **Wallboard（墙板）**：所有注册应用的状态卡片，绿色=UP，红色=DOWN。
- **Applications**：点进 `spring-boot-demo-admin-client`，能看到详细信息：
  - **Details**：版本、Java 版本、启动时间
  - **Metrics**：JVM 内存、线程数、HTTP 请求统计
  - **Environment**：所有环境变量和配置项
  - **Loggers**：动态调整日志级别（不用重启！）
  - **Threads**：线程 dump
  - **Heap Dump**：一键下载 JVM 堆快照

### 6.3 验证 client 接口

```sh
curl http://localhost:8080/demo/ -u xkcoding:123456
# 返回: This is a Spring Boot Admin Client.
```

注意要带 `-u xkcoding:123456`，因为引了 Spring Security，接口要认证。

---

## 七、动手练习

1. **观察注册过程**：先启动 client 再启动 server，看 client 日志里的注册重试信息；再反过来正确启动，对比面板状态。
2. **改应用名**：把 client 的 `spring.application.name` 改成 `my-service`，重启，看面板显示名变化。
3. **制造 DOWN**：在 client 里加个接口让健康检查返回 DOWN（自定义 HealthIndicator），观察面板变红。
4. **动态调日志级别**：在面板的 Loggers 里把 `root` 日志从 INFO 改成 DEBUG，再请求接口，观察 client 控制台日志变多——体会"不重启改配置"的便利。
5. **加第二个 client**：复制 admin-client 改端口为 8081、名字为 `client-2`，启动后看面板出现两个应用卡片。

---

## 八、本模块知识点总结（结合实际开发详解）

Spring Boot Admin 是生产环境监控的利器，但要用好它需要理解背后的架构和边界。下面把核心知识点放到真实开发场景里讲透。

### 8.1 Server + Client 架构：监控的两种部署模式

**SBA 的两种工作模式：**

1. **Client 主动注册模式**（本模块用法）：每个业务应用引 `admin-starter-client`，启动时主动向 server 发注册请求。server 周期性 HTTP 拉取 client 端点数据。
2. **Server 主动发现模式**：client 不引客户端依赖，server 配合服务发现组件（Eureka/Nacos/Consul）从注册中心自动发现所有应用并监控。

**实际开发怎么选？**

| 模式 | 优点 | 缺点 | 适用场景 |
| --- | --- | --- | --- |
| Client 主动注册 | 简单、不依赖注册中心 | 每个应用要改代码加依赖 | 小型项目、单体应用 |
| Server 服务发现 | client 零侵入 | 依赖注册中心基础设施 | 微服务集群、已有 Eureka/Nacos |

**最佳实践：**

- 微服务架构下优先用**服务发现模式**——业务应用完全无感知，不用每个服务都加 client 依赖和配置。
- 单体或少量服务用**主动注册模式**更直接。
- Server 要**集群部署**：单个 server 是单点，挂了监控全丢。生产环境至少两台 server + Nginx 负载，server 间用 Hazelcast 共享注册状态。

**常见坑：**

- Client 注册了但面板看不到：通常是 client 的 Actuator 端点没暴露（`include: "*"` 没配）或被 Security 拦截，server 拉数据 401/404。
- Server 单点故障：一个 server 挂了所有监控丢失，必须集群。

### 8.2 Actuator 端点暴露：安全与可见的权衡

本模块 client 配了 `management.endpoints.web.exposure.include: "*"` 暴露所有端点。这是 SBA 能工作的前提，但也是**最大安全风险点**。

**为什么危险？**

Actuator 端点包含大量敏感信息：

| 端点 | 暴露的内容 | 风险 |
| --- | --- | --- |
| `/env` | 所有环境变量、配置（含数据库密码） | 凭证泄露 |
| `/heapdump` | JVM 堆内存快照（可还原对象） | 数据泄露 |
| `/threaddump` | 线程栈 | 内部实现暴露 |
| `/loggers` | 可动态改日志级别 | 可被恶意调高日志拖垮磁盘 |
| `/shutdown` | 关闭应用（默认关闭） | 可被恶意关停 |

**实际开发的最佳实践：**

1. **生产环境绝不暴露所有端点**：用精确列表代替 `*`：

   ```yaml
   management:
     endpoints:
       web:
         exposure:
           include: health,info,metrics,prometheus   # 只暴露必要的
   ```

2. **端点必须鉴权**：引 Spring Security（本模块就这么做），给端点加认证。生产用更严格的认证（OAuth2/JWT），不用本模块的硬编码密码。
3. **端点独立端口**：把 Actuator 端点挪到独立的管理端口，不和业务接口混在一起：

   ```yaml
   management:
     server:
       port: 9001   # 管理端口，只在内网开放
   ```

4. **`/shutdown` 永远关闭**：除非有严格网络隔离，否则别开 `enable`。

**常见坑：**

- 暴露 `*` 后 `/env` 里的密码被脱敏显示成 `******`，但 `/heapdump` 能从内存里还原明文——别以为脱敏就安全。
- 忘了给端点鉴权，公网直接能访问 `/env`，造成生产事故（真实案例屡见不鲜）。

### 8.3 Spring Security 与 Admin 的协作：凭证传递

本模块 client 引了 `spring-boot-starter-security`，配置了用户名密码，并在 `spring.boot.admin.client.instance.metadata` 里把凭证告诉 server。这个细节体现了 SBA 的鉴权链路：

**工作流程：**

1. Client 启动，带凭证（metadata）向 server 注册："我是 `spring-boot-demo-admin-client`，我的端点在 `http://localhost:8080/demo/actuator`，拉数据时用这个账号密码"。
2. Server 收到注册，存储 instance + metadata。
3. Server 周期性请求 client 的 `/actuator/health` 等端点，带上 metadata 里的 Basic Auth。
4. Client 的 Spring Security 校验通过，返回数据。

**实际开发的进阶：**

- 生产不用硬编码密码，用 OAuth2 client credentials 或 JWT，server 和 client 共享密钥。
- 如果 client 在网关后面，server 拉数据要走网关，凭证传递更复杂。
- SBA 2.x 支持 `instance.service-path` 等配置适配网关/反代场景。

**常见坑：**

- 改了 security 密码但忘了同步 metadata，server 拉数据 401，面板显示 client 离线。
- Security 默认拦截所有路径，包括 Actuator，需要配 `permitAll` 或用 SBA 提供的默认安全配置。

### 8.4 动态日志级别调整：不重启改配置

SBA 面板的 Loggers 功能能动态调整日志级别，这是生产排障的利器——线上出问题但日志是 INFO 看不到细节，传统做法要重启改配置，SBA 直接面板改 DEBUG，看完再改回去。

**原理：** Actuator 的 `/loggers` 端点支持 `POST` 修改日志级别，底层调用 Logback/Log4j2 的运行时 API，立即生效。SBA 面板只是对这个端点做了可视化封装。

**实际开发应用：**

- 线上排查时临时开某个包的 DEBUG 日志，定位完立刻关掉。
- 配合日志采集（ELK/Graylog，后续模块会讲）做全链路排查。

**最佳实践：**

- 生产默认 INFO，出问题用 SBA 临时调 DEBUG，**调完务必调回**，否则日志量爆炸撑爆磁盘。
- 关键业务包（如 `com.xkcoding.service`）可以默认 DEBUG，但要有日志采样避免量太大。

**常见坑：** 调了 DEBUG 忘了调回，磁盘被日志写满导致服务挂掉——这是真实事故。

### 8.5 SBA 的能力边界：它不是 APM

**SBA 能做什么：** 应用级监控（健康、JVM、线程、日志、配置）、运维操作（dump、改日志级别）、上下线通知。

**SBA 不能做什么：**

- **链路追踪**：跨服务的调用链看不到（要用 SkyWalking/Zipkin）。
- **业务指标**：订单量、QPS 趋势图没有（要用 Prometheus + Grafana）。
- **日志聚合**：多个服务的日志不能在一个地方搜（要用 ELK/Graylog）。
- **告警**：只能邮件/钉钉通知上下线，不能复杂告警规则（要用 Prometheus Alertmanager）。

**实际开发的监控体系分层：**

| 层次 | 工具 | 关注点 |
| --- | --- | --- |
| 应用级 | Spring Boot Admin | 单应用运行时、运维操作 |
| 指标级 | Prometheus + Grafana | 业务指标、趋势、告警 |
| 链路级 | SkyWalking / Zipkin | 跨服务调用链 |
| 日志级 | ELK / Graylog | 日志聚合搜索 |

**最佳实践：** SBA 是应用级监控的起点，不是终点。小项目用 SBA 够了；中大型项目要补齐指标、链路、日志三层。本项目后面的 `demo-graylog` 就是日志层的补充。

**常见坑：** 把 SBA 当全能监控用，发现做不了趋势图和告警就否定它——其实定位错了，它是"应用运维面板"不是"指标大盘"。

### 8.6 版本对齐：SBA 与 Spring Boot 的对应关系

SBA 版本必须和 Spring Boot 主版本严格匹配：

| SBA 版本 | Spring Boot 版本 |
| --- | --- |
| 2.1.x | 2.1.x |
| 2.2.x | 2.2.x |
| 2.3.x | 2.3.x |
| 2.4.x+ | 2.4.x+ |

本项目 SBA 2.1.0 + Spring Boot 2.1.0.RELEASE，匹配。如果升 Spring Boot 到 2.3 但 SBA 不升，启动会因 API 变化报错。

**最佳实践：** 升级 Spring Boot 时同步查 SBA 的 release notes，确认有对应版本再升。SBA 通常比 Spring Boot 慢半拍，新 Spring Boot 出来后要等 SBA 适配。

**常见坑：** 盲目升 Spring Boot，SBA 没跟上，编译通过但运行时 `ClassNotFoundException` 或端点路径变了（如 Spring Boot 2.x 把 `/health` 改成 `/actuator/health`，老 SBA 还找老路径）。

---

> 📌 **学习建议**：Spring Boot Admin 是你接触"运维监控"的敲门砖。作为前端转后端的工程师，你可以把它类比成一个"后端版的 Grafana + devtools"——它让你直观看到每个服务内部在发生什么。建议先把本模块跑通，在面板上点遍每个 tab（Metrics/Environment/Loggers/Threads），建立对"一个运行中的 JVM 长什么样"的直觉。这种直觉对后续排查内存泄漏、线程死锁等问题极有帮助。记住：监控不是装饰，是生产环境的眼睛。
