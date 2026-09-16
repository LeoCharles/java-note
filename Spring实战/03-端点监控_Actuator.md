# 03 - Spring Boot 端点监控 Actuator

> 对应项目模块：`demo-actuator`
> 前置知识：已学完 `01-SpringBoot入门_HelloWorld`、`02-读取配置文件_Properties`，了解启动类、配置文件、依赖注入基本用法
> 学习目标：理解 Actuator 是什么、能做什么，掌握生产级监控端点的开启与安全配置，能在真实项目中用它做健康检查和运行时诊断。

---

## 一、本模块要解决什么问题？

应用上线后，你总会遇到这些问题：

- 服务还活着吗？数据库连得上吗？Redis 通不通？
- 现在有多少个 Bean？内存用了多少？线程池什么状态？
- 这个配置最终生效的值是什么？被哪个来源覆盖了？
- 接口映射关系是怎样的？哪些路由是活的？

如果没有监控手段，这些问题只能靠"猜"和"看日志"。**Actuator** 就是 Spring Boot 提供的生产级监控工具——它给应用装上一组 HTTP 端点，让你能从外部"窥探"应用内部状态。

> 💡 前端类比：Actuator 有点像 Vue 的 Vue DevTools 面板 + React DevTools + 浏览器的 Performance 面板合体——它不参与业务逻辑，但能让你看到应用内部的"心跳"和"体检报告"。区别是 Vue DevTools 是给开发时用的浏览器插件，Actuator 是给运行时（尤其是生产环境）用的 HTTP 接口。

本模块的最终效果：启动应用后，访问一组带认证的 HTTP 端点，能看到健康状态、Bean 列表、配置信息、路由映射等运行时数据。

---

## 二、先看项目结构

```
demo-actuator/
├── pom.xml
└── src/main/
    ├── java/com/xkcoding/actuator/
    │   └── SpringBootDemoActuatorApplication.java   # 启动类（极简，无业务代码）
    └── resources/
        └── application.yml                            # 配置：端口分离 + 安全 + 端点暴露
└── src/test/java/.../SpringBootDemoActuatorApplicationTests.java  # 冒烟测试
```

注意：本模块**没有写任何业务 Java 代码**——启动类只有 `@SpringBootApplication` + `main`，所有能力都来自依赖和配置。这正是 Actuator 的特点：**它是基础设施，靠配置驱动，不需要写业务代码**。

---

## 三、逐行拆解 `pom.xml`

```xml
<dependencies>
    <!-- 1. Actuator 起步依赖：核心监控能力 -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-actuator</artifactId>
    </dependency>

    <!-- 2. Spring Security：给监控端点加认证 -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-security</artifactId>
    </dependency>

    <!-- 3. Web 起步依赖 -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-web</artifactId>
    </dependency>

    <!-- 4. 测试依赖 -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-test</artifactId>
        <scope>test</scope>
    </dependency>
    <dependency>
        <groupId>org.springframework.security</groupId>
        <artifactId>spring-security-test</artifactId>
        <scope>test</scope>
    </dependency>
</dependencies>
```

**三个核心依赖各司其职：**

| 依赖 | 作用 | 为什么需要 |
| --- | --- | --- |
| `spring-boot-starter-actuator` | 提供监控端点（health、info、beans、env 等） | 这是本模块的主角 |
| `spring-boot-starter-security` | 给端点加用户名/密码认证 | 监控端点含敏感信息，裸奔暴露会泄露内部结构 |
| `spring-boot-starter-web` | 提供 HTTP 传输能力 | Actuator 端点默认通过 HTTP 暴露，需要 Web 容器 |

> 💡 前端类比：这像给一个网站装了"管理后台"（Actuator）+ "登录墙"（Security）+ "Web 服务器"（Web）。没有 Security，管理后台谁都能进，相当于把数据库结构、配置密码全公开。

**关键点：为什么必须配 Security？**

Actuator 默认暴露的端点里，`/env` 能看到所有配置（可能含密码），`/beans` 能看到所有 Bean 结构，`/threaddump` 能看到线程栈。如果直接暴露到公网，等于把应用"扒光"。所以本模块引入 Security，访问端点要输入用户名密码。

---

## 四、逐行拆解 `application.yml`

这是本模块的核心，所有监控行为都靠它配置：

```yaml
server:
  port: 8080
  servlet:
    context-path: /demo

# 若要访问端点信息，需要配置用户名和密码
spring:
  security:
    user:
      name: xkcoding
      password: 123456

management:
  # 端点信息接口使用的端口，为了和主系统接口使用的端口进行分离
  server:
    port: 8090
    servlet:
      context-path: /sys
  # 端点健康情况，默认值"never"，设置为"always"可以显示硬盘使用情况和线程情况
  endpoint:
    health:
      show-details: always
  # 设置端点暴露的哪些内容，默认["health","info"]，设置"*"代表暴露所有可访问的端点
  endpoints:
    web:
      exposure:
        include: '*'
```

分三块理解：

### 4.1 主应用端口（业务接口）

```yaml
server:
  port: 8080
  servlet:
    context-path: /demo
```

业务接口跑在 `8080`，前缀 `/demo`。这部分和前两模块一样。

### 4.2 安全认证（访问端点的账号密码）

```yaml
spring:
  security:
    user:
      name: xkcoding
      password: 123456
```

引入 `spring-boot-starter-security` 后，Spring Boot 自动配置一个 HTTP Basic 认证。这里配置默认用户的账号密码。访问任何被 Security 保护的端点，浏览器会弹出登录框，输入 `xkcoding` / `123456` 才能进。

> ⚠️ 这是 Spring Boot 2.x 的简化写法，仅用于演示。**生产环境绝不能把密码明文写进 yml**，应该用环境变量 `spring.security.user.password=${ADMIN_PASSWORD}`，或用更完整的 Security 配置（JWT、OAuth2 等，后续 `demo-rbac-security` 模块会讲）。

### 4.3 Actuator 端点配置（核心）

```yaml
management:
  server:
    port: 8090              # 监控端点用独立端口
    servlet:
      context-path: /sys   # 监控端点前缀
  endpoint:
    health:
      show-details: always  # 健康检查显示详情
  endpoints:
    web:
      exposure:
        include: '*'         # 暴露所有端点
```

**逐项解释：**

| 配置项 | 作用 | 默认值 |
| --- | --- | --- |
| `management.server.port` | 监控端点监听的端口 | 与主应用同端口 |
| `management.server.servlet.context-path` | 监控端点的前缀 | `""`（空） |
| `management.endpoint.health.show-details` | 健康检查是否显示细节 | `never` |
| `management.endpoints.web.exposure.include` | 暴露哪些端点 | `["health","info"]` |

**为什么端口要分离？**

本模块让业务接口跑 `8080`，监控端点跑 `8090`，这是生产环境的**最佳实践**：

1. **安全隔离**：监控端点可以只对内网开放，外网网关只转发 `8080`，`8090` 不暴露。
2. **避免干扰**：监控请求（可能很重，如 `/heapdump` 导出堆）不会占用业务线程。
3. **便于治理**：监控流量和业务流量分开统计、限流。

> 💡 前端类比：这像把管理后台和用户前台部署在不同端口/域名，前台对所有人开放，后台只对内网开放。Nginx 可以配置 `location /sys { allow 10.0.0.0/8; deny all; }` 实现同样的隔离。

**`show-details: always` 的作用：**

`/health` 端点默认只返回 `{"status":"UP"}`，不告诉你具体哪个组件健康。设成 `always` 后会显示磁盘、数据库、Redis 等各组件的详细状态：

```json
{
  "status": "UP",
  "details": {
    "db": { "status": "UP", "database": "MySQL", "..." },
    "diskSpace": { "status": "UP", "free": 123456789, "threshold": 10485760 }
  }
}
```

这对排查"应用活着但某个依赖挂了"非常有用。

**`exposure.include: '*'` 的作用：**

Actuator 有几十个端点，但默认只暴露 `health` 和 `info` 两个（安全考虑）。设成 `*` 表示暴露全部。下表列出常用的：

| 端点 | 作用 | 默认是否暴露 |
| --- | --- | --- |
| `/actuator/health` | 健康检查（最常用） | 是 |
| `/actuator/info` | 应用信息 | 是 |
| `/actuator/beans` | 所有 Bean 列表 | 否（需 `*`） |
| `/actuator/env` | 所有环境配置 | 否（需 `*`） |
| `/actuator/mappings` | 所有路由映射 | 否（需 `*`） |
| `/actuator/loggers` | 日志级别查看与动态调整 | 否（需 `*`） |
| `/actuator/threaddump` | 线程转储 | 否（需 `*`） |
| `/actuator/heapdump` | 堆转储（下载二进制） | 否（需 `*`） |
| `/actuator/metrics` | 指标列表（内存、线程数等） | 否（需 `*`） |
| `/actuator/configprops` | 所有 `@ConfigurationProperties` 的值 | 否（需 `*`） |

> ⚠️ 生产环境**不建议**直接 `include: '*'`，应该按需暴露：`include: health,info,loggers,metrics`，敏感端点（env、heapdump）不暴露或加更严格权限。

---

## 五、启动类与测试类

### 5.1 启动类

```java
@SpringBootApplication
public class SpringBootDemoActuatorApplication {
    public static void main(String[] args) {
        SpringApplication.run(SpringBootDemoActuatorApplication.class, args);
    }
}
```

极简——只有 `@SpringBootApplication` 和 `main`。Actuator 的能力全部由 `spring-boot-starter-actuator` 依赖触发自动配置，不需要写任何代码。启动后，Actuator 的自动配置类（`EndpointAutoConfiguration` 等）会自动注册所有端点。

### 5.2 测试类

```java
@RunWith(SpringRunner.class)
@SpringBootTest
public class SpringBootDemoActuatorApplicationTests {
    @Test
    public void contextLoads() {
    }
}
```

和前两模块一样的冒烟测试，验证上下文能正常加载。注意：因为引入了 Security，如果后续要写针对端点的测试，需要带上认证（用 `@WithMockUser` 或配置测试安全）。

---

## 六、运行与验证

### 6.1 启动

```sh
mvn spring-boot:run
```

启动后控制台会看到两个端口：业务 `8080`、监控 `8090`。

### 6.2 访问监控端点

浏览器访问 `http://localhost:8090/sys/actuator/health`，弹出登录框，输入 `xkcoding` / `123456`，看到：

```json
{
  "status": "UP",
  "details": { "diskSpace": { "status": "UP", ... } }
}
```

用 curl 带认证访问：

```sh
# 健康检查
curl -u xkcoding:123456 http://localhost:8090/sys/actuator/health

# 查看所有路由映射
curl -u xkcoding:123456 http://localhost:8090/sys/actuator/mappings

# 查看所有 Bean
curl -u xkcoding:123456 http://localhost:8090/sys/actuator/beans

# 查看所有配置来源
curl -u xkcoding:123456 http://localhost:8090/sys/actuator/env
```

### 6.3 端点路径组成

完整路径 = `management端口` + `management context-path` + `/actuator` + `端点名`：

```
http://localhost:8090  /sys  /actuator  /health
└── management.port ──┘ └context-path┘ └固定前缀┘ └端点名┘
```

注意 `/actuator` 是 Actuator 端点的默认基础路径，可以用 `management.endpoints.web.base-path` 修改。

### 6.4 动态调日志级别（实用功能）

`/loggers` 端点支持运行时动态修改日志级别，不用重启：

```sh
# 查看某个 logger 的级别
curl -u xkcoding:123456 http://localhost:8090/sys/actuator/loggers/com.xkcoding

# 动态改成 DEBUG
curl -u xkcoding:123456 -X POST \
  -H "Content-Type: application/json" \
  -d '{"configuredLevel":"DEBUG"}' \
  http://localhost:8090/sys/actuator/loggers/com.xkcoding
```

这是排查线上问题的利器——临时开 DEBUG 日志看细节，排查完再调回 INFO。

---

## 七、动手练习

1. **关掉端口分离**：把 `management.server.port` 注释掉，观察监控端点回到 `8080`，路径变成 `http://localhost:8080/demo/actuator/health`（注意前缀变成主应用的 `/demo`）。
2. **限制暴露**：把 `exposure.include` 从 `*` 改成 `health,info`，重启，访问 `/actuator/beans` 验证返回 404。
3. **隐藏健康详情**：把 `health.show-details` 改回 `never`，访问 `/actuator/health`，对比返回值差异。
4. **动态调日志**：用 POST 请求把 `root` logger 调成 DEBUG，观察控制台日志变多。
5. **看配置来源**：访问 `/actuator/env`，找到某个配置项，观察它的 `propertySources` 列表，理解配置优先级（呼应上一篇的配置优先级全景）。
6. **看指标**：访问 `/actuator/metrics` 拿到指标名列表，再访问 `/actuator/metrics/jvm.memory.used` 看具体值。

---

## 八、本模块知识点总结（结合实际开发详解）

Actuator 是 Spring Boot 区别于传统框架的标志性功能之一，它让"应用可观测"变成开箱即用。下面把核心知识点放到真实开发场景里讲透。

### 8.1 Actuator 端点全景：知道有哪些工具可用

**实际开发中常用的端点及场景：**

| 端点 | 解决的实际问题 | 使用频率 |
| --- | --- | --- |
| `/health` | 负载均衡/ K8s 探针判断服务是否存活 | ⭐⭐⭐⭐⭐ |
| `/info` | 展示版本号、构建时间，方便确认部署的是哪个版本 | ⭐⭐⭐ |
| `/env` | 排查"配置为什么没生效"，看所有配置来源和最终值 | ⭐⭐⭐⭐ |
| `/configprops` | 看 `@ConfigurationProperties` 绑定的实际值 | ⭐⭐⭐ |
| `/loggers` | 线上临时开 DEBUG 日志排查，不用重启 | ⭐⭐⭐⭐⭐ |
| `/metrics` | 看 JVM 内存、线程数、HTTP 请求耗时等指标 | ⭐⭐⭐⭐ |
| `/mappings` | 确认某个接口是否真的注册了、路径对不对 | ⭐⭐⭐ |
| `/beans` | 排查"为什么这个 Bean 没注入"，看容器里到底有没有 | ⭐⭐⭐ |
| `/threaddump` | 排查死锁、线程阻塞 | ⭐⭐⭐ |
| `/heapdump` | OOM 时导出堆快照离线分析 | ⭐⭐（按需） |

**最佳实践：**

- **按需暴露**：生产用 `include: health,info,loggers,metrics`，不要 `*`。`env`、`heapdump` 这种敏感端点要么不暴露，要么加 IP 白名单。
- **`/health` 是最重要的端点**：它是 K8s liveness/readiness 探针、负载均衡健康检查的标准接口，务必保证它轻量、快速返回。
- **`/info` 用来标识版本**：配合 `git.properties` 或 `build-info` 目标，能在 `/info` 里看到 git commit、构建时间，排查"线上跑的是哪个版本"。

**常见坑：**

- 暴露了 `*` 又没加 Security，`/env` 把数据库密码泄露出去——**安全红线**。
- `/heapdump` 会下载整个堆（可能几个 GB），频繁调用会拖垮应用，要限制访问。
- `/threaddump` 在高并发时输出很大，建议重定向到文件分析。

### 8.2 端口分离：生产环境的安全标配

本模块把监控端点和业务接口分到不同端口（`8080` vs `8090`），这是生产环境的推荐做法。

**实际部署的典型架构：**

```
                    ┌─── 外网 ────┐
                    │             │
                    │  Nginx/网关  │
                    │             │
                    └──┬──────┬──┘
                       │      │
            外网只转发 8080   8090 不对外
                       │      │（仅内网可访问）
                  ┌────▼──┐ ┌─▼────────┐
                  │ 业务  │ │ 监控端点  │
                  │ :8080 │ │ :8090    │
                  └───────┘ └──────────┘
```

**最佳实践：**

1. **监控端口只对内网开放**：在云上用安全组/防火墙限制 `8090` 只允许运维网段访问。
2. **业务端口走网关**：外网请求经网关转发到 `8080`，网关不转发 `/sys` 前缀。
3. **即使内网也加认证**：本模块配了 Basic Auth，更成熟的做法是用专门的运维 token 或对接统一身份。

**常见坑：**

- 忘了分离端口，监控端点和业务混在一个端口，外网能直接访问 `/actuator/env`。
- 分离端口后，运维忘了开防火墙 `8090`，导致监控平台采不到数据——部署 checklist 要包含端口检查。

### 8.3 健康检查：`/health` 的深度与定制

`/health` 是用得最多的端点，它聚合了多个 `HealthIndicator`（健康指示器）。

**Spring Boot 自带的健康检查：**

| 指示器 | 检查内容 |
| --- | --- |
| `DiskSpaceHealthIndicator` | 磁盘剩余空间 |
| `DataSourceHealthIndicator` | 数据库能否连通（执行简单查询） |
| `RedisHealthIndicator` | Redis 能否 ping 通 |
| `MongoHealthIndicator` | MongoDB 连通性 |
| `ElasticsearchHealthIndicator` | ES 集群状态 |

引入对应依赖后，这些指示器自动生效——这就是自动配置的威力。

**自定义健康检查：**

实际项目中，你可能要检查"能否连到某个第三方 API"这种 Spring 没预置的场景：

```java
@Component
public class ThirdPartyApiHealthIndicator implements HealthIndicator {
    @Override
    public Health health() {
        try {
            // 调用第三方 API，能通就 UP
            boolean ok = checkApi();
            return ok ? Health.up().withDetail("api", "reachable").build()
                      : Health.down().withDetail("api", "unreachable").build();
        } catch (Exception e) {
            return Health.down(e).build();
        }
    }
}
```

注册后，`/health` 会自动聚合这个自定义检查。

**最佳实践：**

1. **健康检查要轻量**：`/health` 被频繁调用（K8s 每几秒探一次），里面的检查逻辑要快，超时设短（如 2 秒），别卡在某个慢调用上。
2. **区分 liveness 和 readiness**：
   - liveness（存活探针）：用 `/health`，挂了就重启。
   - readiness（就绪探针）：可以自定义一个端点，应用启动完成、依赖就绪后才返回 UP，避免启动期被误判。
3. **`show-details` 权限控制**：生产环境对外只返回 `status`，详情只给运维看。Spring Boot 2.x 可以用 `show-details: when-authorized`，认证后才显示。

**常见坑：**

- 健康检查里调了一个慢接口，导致 `/health` 超时，K8s 误判服务挂了反复重启——**健康检查逻辑必须有超时**。
- 数据库健康检查失败导致整个 `/health` 返回 DOWN，但业务其实能跑（读库失败但写库正常）——可以配置 `health group` 分组，不同探针看不同子集。

### 8.4 配置诊断：`/env` 与 `/configprops`

这两个端点是排查配置问题的利器。

**`/env`：看所有配置来源**

访问 `/actuator/env`，能看到配置值来自哪里（命令行、环境变量、yml、系统属性），以及最终生效值。这直接呼应上一篇讲的"配置优先级全景"——眼见为实。

**`/configprops`：看 `@ConfigurationProperties` 绑定结果**

上一篇讲 `@ConfigurationProperties` 把 yml 绑定到 Java 字段，但绑定对不对？访问 `/actuator/configprops`，能看到每个配置类最终绑定的值，排查"为什么字段是 null"。

**最佳实践：**

- 排查"配置没生效"的标准流程：先 `/env` 看原始值对不对 → 再 `/configprops` 看绑定结果对不对 → 定位是配置没读到还是绑定出错。
- 这两个端点含敏感信息（密码），生产环境要么不暴露，要么对密码字段脱敏（Spring Boot 默认会对 `password`、`secret` 等 key 脱敏显示 `******`）。

**常见坑：**

- 以为改了 yml 就生效，结果 `/env` 显示被环境变量覆盖了——这就是为什么生产推荐用环境变量管敏感配置。
- `/configprops` 显示某字段是 null，排查发现是忘了加 `@Component` 或没加 `@Data`（没 setter）——呼应上一篇的常见坑。

### 8.5 动态日志调整：`/loggers` 的实战价值

这是线上排查问题最实用的端点之一。

**典型场景：**

线上出了个偶发 bug，需要 DEBUG 日志看细节，但重启会中断服务。用 `/loggers` 动态调整：

```sh
# 临时把订单服务调 DEBUG
curl -u user:pass -X POST -H "Content-Type: application/json" \
  -d '{"configuredLevel":"DEBUG"}' \
  http://host:8090/sys/actuator/loggers/com.xkcoding.order

# 排查完调回 INFO
curl -u user:pass -X POST -H "Content-Type: application/json" \
  -d '{"configuredLevel":"INFO"}' \
  http://host:8090/sys/actuator/loggers/com.xkcoding.order
```

**最佳实践：**

- **精准到包名**：别把 `root` 调成 DEBUG（日志爆炸），只调出问题的包。
- **排查完立刻调回**：DEBUG 日志量大，长期开着会拖慢性能、撑满磁盘。
- **配合日志收集**：调出的 DEBUG 日志会被 Logback/Log4j2 正常输出，如果接了 ELK，能在 Kibana 里直接搜。

**常见坑：**

- 调了日志级别但没看到 DEBUG 日志——可能是 `logback.xml` 里硬编码了级别，覆盖了 Actuator 的动态调整。配置文件里的级别优先级高于 Actuator 动态设置，需要改成 `<root level="${LOG_LEVEL:-INFO}">` 这种可被覆盖的写法。

### 8.6 指标监控：`/metrics` 与 Prometheus 集成

`/metrics` 端点提供 JVM、HTTP 请求等指标，但它返回的是指标名列表，具体值要看 `/metrics/{metric-name}`。

**常用指标：**

| 指标 | 含义 |
| --- | --- |
| `jvm.memory.used` | JVM 已用内存 |
| `jvm.threads.live` | 活跃线程数 |
| `http.server.requests` | HTTP 请求耗时分布 |
| `process.cpu.usage` | CPU 使用率 |
| `process.uptime` | 进程运行时间 |

**实际生产的进阶用法：**

Actuator 自带的 `/metrics` 是 JSON 接口，适合人看。生产环境通常把它对接到 **Prometheus + Grafana** 做长期存储和可视化：

1. 引入 `micrometer-registry-prometheus` 依赖。
2. Actuator 自动暴露 `/actuator/prometheus` 端点，输出 Prometheus 格式文本。
3. Prometheus 定时抓取这个端点，存进时序数据库。
4. Grafana 配置仪表盘展示。

> 💡 前端类比：这像把浏览器的 Performance 数据导出给 Lighthouse CI 持续监控。Actuator 是"数据源"，Prometheus 是"采集+存储"，Grafana 是"可视化"。

**最佳实践：**

- 生产环境一定要接 Prometheus + Grafana，光靠人手动 curl 端点看不过来。
- 自定义业务指标（如订单量、支付成功率）用 `MeterRegistry` 注册，能在监控大盘里看到业务健康度，不只看技术指标。

### 8.7 安全加固：Actuator 的权限治理

Actuator 端点含敏感信息，安全治理是重中之重。

**三层防护：**

1. **网络层**：监控端口只对内网开放（安全组/防火墙）。
2. **认证层**：Basic Auth / 专门 token / 对接统一身份（本模块用了最简单的 Basic Auth）。
3. **端点层**：按需暴露，敏感端点（env、heapdump）额外限制。

**Spring Boot 2.x 的端点权限配置：**

```yaml
management:
  endpoint:
    env:
      enabled: true
    heapdump:
      enabled: false   # 直接禁用
  endpoints:
    web:
      exposure:
        include: health,info,loggers,metrics,env
```

**最佳实践：**

- **最小暴露原则**：只暴露运维必须的端点。
- **敏感端点单独授权**：用 Security 配置，`/actuator/env`、`/actuator/heapdump` 需要更高权限角色。
- **生产用 HTTPS**：Basic Auth 的密码是 Base64 明文传输，必须走 HTTPS（后续 `demo-https` 模块会讲）。

**常见坑：**

- 引入 `spring-boot-starter-security` 后，Actuator 端点默认被保护，但**业务接口也被保护了**——本模块没有业务接口所以无感，真实项目要配置 Security 放行业务接口、只保护 Actuator。这个配置在 `demo-rbac-security` 会系统讲。

---

> 📌 **学习建议**：Actuator 是 Spring Boot "生产级"三个字的直接体现。作为前端转后端的同学，要建立"应用上线后需要可观测"的意识——前端有浏览器 DevTools、有 Sentry、有 Performance 面板，后端的"DevTools"就是 Actuator + 日志 + Prometheus。建议把 `/health`、`/env`、`/loggers`、`/metrics` 这四个端点用熟，它们覆盖了 80% 的日常运维诊断场景。另外记住一条红线：**Actuator 端点必须加认证 + 网络隔离**，裸奔等于把应用内部结构公开给攻击者。
