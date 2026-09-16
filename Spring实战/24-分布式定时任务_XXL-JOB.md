# 24 - 分布式定时任务 XXL-JOB

> 对应项目模块：`demo-task-xxl-job`
> 前置知识：已学完 `22-定时任务_Task`、`23-定时任务_Quartz`，了解单机定时任务的实现方式
> 学习目标：理解分布式调度的核心概念，掌握 XXL-JOB 的"调度中心 + 执行器"架构，能独立集成 XXL-JOB 并通过 API 管理任务。

---

## 一、本模块要解决什么问题？

前两个模块我们学了两种单机定时任务方案：

- **Spring Task**（`@Scheduled`）：最简单，但任务信息写死在代码里，改 cron 要重新发版；没有可视化界面；多实例下会重复执行；没有失败重试、没有任务依赖。
- **Quartz**：功能强，支持持久化到数据库、集群部署（靠数据库锁防止重复执行），但配置复杂，原生没有好用的管理界面，动态增删任务要写不少代码。

**当系统演进到分布式部署（一个服务部署多个实例）时，单机方案的痛点被放大：**

| 痛点 | 单机方案的困境 |
| --- | --- |
| 重复执行 | 3 个实例都跑同一个定时任务，同一时刻对同一批数据操作 3 次，数据错乱 |
| 任务管理 | 改 cron 表达式、暂停任务都要改代码重新发版，运维成本高 |
| 可视化 | 没有统一界面查看"有哪些任务、上次什么时候跑的、成功还是失败" |
| 失败处理 | 任务失败后没有自动重试、没有告警、没有日志归集 |
| 任务编排 | 任务 A 跑完才能跑任务 B？单机方案很难做依赖编排 |

**XXL-JOB 就是为解决这些问题而生的分布式任务调度平台。** 它采用"调度中心 + 执行器"分离架构，调度中心负责任务管理、调度、日志、可视化界面，执行器（你的业务服务）只负责接收调度请求并执行任务逻辑。

> 💡 前端类比：这像把"前端定时器"升级成"云端调度平台"。单机 `setInterval` 只能在一个进程里跑；XXL-JOB 像一个独立的"任务控制台服务"（类比 GitHub Actions 的调度器），统一管理分散在多台机器上的任务，谁空闲就让谁跑、跑失败自动重试、全程有日志面板。

### 1.1 XXL-JOB 的核心架构

理解 XXL-JOB 的关键是搞懂它的**两个角色**：

```
┌─────────────────┐         心跳注册 / 任务回调         ┌─────────────────┐
│                 │  ◄──────────────────────────────►  │                 │
│   调度中心       │         下发任务调度请求            │   执行器         │
│  (xxl-job-admin) │  ──────────────────────────────►  │  (你的业务服务)  │
│                 │                                     │                 │
│ - 任务管理       │                                     │ - 执行 JobHandler│
│ - 调度日志       │                                     │ - 回调执行结果   │
│ - 可视化界面     │                                     │ - 写执行日志     │
└─────────────────┘                                     └─────────────────┘
   独立部署，一个                                          你的 Spring Boot 应用
   可部署集群                                              也可多实例部署
```

- **调度中心（Admin）**：一个独立部署的 Web 应用（本身也是 Spring Boot），提供任务管理界面、负责按 cron 触发调度、记录日志。它**不执行业务逻辑**，只负责"到点了，通知执行器去跑"。
- **执行器（Executor）**：你的业务 Spring Boot 应用，集成 XXL-JOB 的 SDK，启动时向调度中心注册自己，收到调度请求后执行对应的 `JobHandler`，把结果回调给调度中心。

> 💡 前端类比：调度中心像"前端项目的 CI 控制台"（GitHub Actions 的 runs 管理页），执行器像"实际跑构建脚本的 runner 机器"。控制台不跑代码，只负责到点触发、收集结果；runner 才是干活的。

### 1.2 它如何解决分布式下的重复执行问题？

调度中心是**唯一触发源**——即使你的执行器部署了 3 个实例，调度请求也只会由调度中心发出**一次**，然后按路由策略（如轮询、故障转移、分片广播）选择一个或多个执行器实例去跑。这样就从根源上避免了"每个实例都重复执行"的问题。

---

## 二、项目结构

```
demo-task-xxl-job/
├── pom.xml
├── README.md
└── src/main/java/com/xkcoding/task/xxl/job/
    ├── SpringBootDemoTaskXxlJobApplication.java   # 启动类
    ├── config/
    │   ├── XxlJobConfig.java                       # 执行器自动装配（核心）
    │   └── props/
    │       └── XxlJobProps.java                    # xxl.job 配置属性类
    ├── controller/
    │   └── ManualOperateController.java            # 通过 API 操作任务（绕过 admin 界面）
    └── task/
        └── DemoTask.java                           # 具体任务逻辑（JobHandler）
```

注意：本模块**不包含调度中心**的代码——调度中心是独立项目（`xxl-job-admin`），需要单独部署。本模块只是"执行器"侧的集成。README 里详细写了如何部署调度中心，我们后面运行小节会讲。

---

## 三、逐行拆解 pom.xml

```xml
<properties>
    <xxl-job.version>2.1.0</xxl-job.version>
</properties>

<dependencies>
    <!-- 1. Web 起步依赖 -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-web</artifactId>
    </dependency>

    <!-- 2. 配置元数据处理器 -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-configuration-processor</artifactId>
        <optional>true</optional>
    </dependency>

    <!-- 3. XXL-JOB 核心 SDK -->
    <dependency>
        <groupId>com.xuxueli</groupId>
        <artifactId>xxl-job-core</artifactId>
        <version>${xxl-job.version}</version>
    </dependency>

    <!-- 4. 测试 / 工具类 / Lombok -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-test</artifactId>
        <scope>test</scope>
    </dependency>
    <dependency>
        <groupId>cn.hutool</groupId>
        <artifactId>hutool-all</artifactId>
    </dependency>
    <dependency>
        <groupId>com.google.guava</groupId>
        <artifactId>guava</artifactId>
    </dependency>
    <dependency>
        <groupId>org.projectlombok</groupId>
        <artifactId>lombok</artifactId>
        <optional>true</optional>
    </dependency>
</dependencies>
```

**关键点：**

- `xxl-job-core`（2.1.0）是 XXL-JOB 提供的执行器 SDK，引入它后你的应用就具备"执行器"能力。注意这里**手动写了版本号**（因为父 POM 没有管理 xxl-job 的版本，只有 Spring Boot 相关依赖才由父 POM 统一管）。
- `spring-boot-configuration-processor` 让自定义配置 `xxl.job.*` 在 yml 里有提示（见 `02-读取配置文件_Properties` 模块的讲解）。
- `hutool-all` 在本模块用于 HTTP 调用（`ManualOperateController` 调调度中心 API）和日志格式化；`guava` 提供 `Maps.newHashMap()`。

> ⚠️ 版本对齐：`xxl-job-core` 的版本必须和你部署的 `xxl-job-admin` 调度中心版本一致，否则执行器注册或任务调度可能失败。本模块用的是 2.1.0。

---

## 四、配置属性类 XxlJobProps.java

```java
@Data
@ConfigurationProperties(prefix = "xxl.job")
public class XxlJobProps {
    /** 调度中心配置 */
    private XxlJobAdminProps admin;
    /** 执行器配置 */
    private XxlJobExecutorProps executor;
    /** 与调度中心交互的accessToken */
    private String accessToken;

    @Data
    public static class XxlJobAdminProps {
        private String address;   // 调度中心地址
    }

    @Data
    public static class XxlJobExecutorProps {
        private String appName;          // 执行器名称
        private String ip;               // 执行器 IP
        private int port;                // 执行器端口
        private String logPath;          // 执行器日志路径
        private int logRetentionDays;   // 日志保留天数
    }
}
```

这是典型的 `@ConfigurationProperties` 用法（回顾 `02-读取配置文件_Properties`）：把 `xxl.job` 前缀下的配置批量绑定到一个类，用嵌套静态内部类表达 yml 的层级结构。

对应 yml：

```yaml
xxl:
  job:
    access-token:               # -> XxlJobProps.accessToken
    admin:
      address: http://...        # -> XxlJobProps.admin.address
    executor:
      app-name: ...              # -> XxlJobProps.executor.appName（松散绑定）
      ip:                        # -> XxlJobProps.executor.ip
      port: 9999                 # -> XxlJobProps.executor.port
      log-path: ...              # -> XxlJobProps.executor.logPath
      log-retention-days: -1     # -> XxlJobProps.executor.logRetentionDays
```

注意 `app-name`（kebab-case）绑定到 `appName`（camelCase），靠的是 Spring Boot 的松散绑定。

---

## 五、配置文件 application.yml

```yaml
server:
  port: 8080
  servlet:
    context-path: /demo
xxl:
  job:
    access-token:                                    # [选填] 通讯令牌
    admin:
      address: http://localhost:18080/xxl-job-admin  # 调度中心地址
    executor:
      app-name: spring-boot-demo-task-xxl-job-executor  # 执行器名称
      ip:                                               # [选填] 自动获取
      port: 9999                                        # 执行器端口
      log-path: logs/spring-boot-demo-task-xxl-job/task-log
      log-retention-days: -1                           # -1 不清理
```

**逐项解释：**

| 配置项 | 作用 | 说明 |
| --- | --- | --- |
| `xxl.job.access-token` | 通讯令牌 | 调度中心和执行器之间的鉴权令牌，两边需一致；为空则不鉴权（生产建议设值） |
| `xxl.job.admin.address` | 调度中心地址 | 执行器启动后向这个地址注册心跳；集群部署时多个地址逗号分隔 |
| `xxl.job.executor.app-name` | 执行器名称 | 注册到调度中心的分组依据，调度中心按这个名称找到对应执行器组 |
| `xxl.job.executor.ip` | 执行器 IP | 默认空表示自动获取；多网卡环境手动指定，避免注册了错误 IP |
| `xxl.job.executor.port` | 执行器端口 | 执行器接收调度请求的端口，默认 9999；同机多执行器要配不同端口 |
| `xxl.job.executor.log-path` | 日志路径 | 执行器把任务执行日志写到这个磁盘路径 |
| `xxl.job.executor.log-retention-days` | 日志保留天数 | 大于 3 才生效，启用定期清理；-1 表示不清理 |

> 💡 前端类比：`admin.address` 像 Vite 配置里的 `server.proxy` 目标地址——告诉执行器"调度中心在哪"。`app-name` 像服务注册的服务名（Nacos/Eureka 里的 service name），调度中心靠它路由。

---

## 六、执行器自动装配 XxlJobConfig.java（核心）

```java
@Slf4j
@Configuration
@EnableConfigurationProperties(XxlJobProps.class)
@RequiredArgsConstructor(onConstructor_ = @Autowired)
public class XxlJobConfig {
    private final XxlJobProps xxlJobProps;

    @Bean(initMethod = "start", destroyMethod = "destroy")
    public XxlJobSpringExecutor xxlJobExecutor() {
        log.info(">>>>>>>>>>> xxl-job config init.");
        XxlJobSpringExecutor xxlJobSpringExecutor = new XxlJobSpringExecutor();
        xxlJobSpringExecutor.setAdminAddresses(xxlJobProps.getAdmin().getAddress());
        xxlJobSpringExecutor.setAccessToken(xxlJobProps.getAccessToken());
        xxlJobSpringExecutor.setAppName(xxlJobProps.getExecutor().getAppName());
        xxlJobSpringExecutor.setIp(xxlJobProps.getExecutor().getIp());
        xxlJobSpringExecutor.setPort(xxlJobProps.getExecutor().getPort());
        xxlJobSpringExecutor.setLogPath(xxlJobProps.getExecutor().getLogPath());
        xxlJobSpringExecutor.setLogRetentionDays(xxlJobProps.getExecutor().getLogRetentionDays());
        return xxlJobSpringExecutor;
    }
}
```

这是本模块最核心的类，逐段拆解：

### 6.1 类上的三个注解

- `@Configuration`：标记为配置类，里面的 `@Bean` 方法会被 Spring 调用，把返回的对象注册为 Bean。
- `@EnableConfigurationProperties(XxlJobProps.class)`：启用 `XxlJobProps` 这个配置属性类，让它被 Spring 容器管理（回顾 `02-读取配置文件_Properties`：`@ConfigurationProperties` 类要么加 `@Component`，要么用这种方式启用）。
- `@RequiredArgsConstructor(onConstructor_ = @Autowired)`：Lombok 生成构造器，`onConstructor_` 让构造器带上 `@Autowired`，实现构造器注入 `XxlJobProps`。这是 Lombok + Spring 的惯用写法。

### 6.2 `@Bean(initMethod = "start", destroyMethod = "destroy")`

这是关键。`XxlJobSpringExecutor` 是 XXL-JOB 提供的执行器核心类，它有两个生命周期方法：

- `start()`：Bean 初始化时调用。内部会启动一个 Netty 服务监听 `port`（9999），并向调度中心发起心跳注册，把自己这个执行器登记上去。
- `destroy()`：容器关闭时调用。释放 Netty 资源、注销注册。

`initMethod` / `destroyMethod` 告诉 Spring：创建这个 Bean 后自动调 `start()`，销毁前自动调 `destroy()`。这样执行器随 Spring 容器启停而启停。

> 💡 前端类比：这像 React 的 `useEffect`——组件挂载时启动副作用（开 Netty、注册心跳），卸载时清理。`initMethod=start` ≈ `useEffect(() => { start(); return () => destroy(); }, [])`。

### 6.3 把配置塞进执行器

方法体里把 `XxlJobProps` 读到的配置一个个 set 到 `XxlJobSpringExecutor`，这就是"把 yml 配置传递给第三方 SDK"的标准做法：Spring 帮你把配置读进 Java 对象，你再手动喂给 SDK。

---

## 七、任务逻辑 DemoTask.java

```java
@Slf4j
@Component
@JobHandler("demoTask")
public class DemoTask extends IJobHandler {

    @Override
    public ReturnT<String> execute(String param) throws Exception {
        log.info("【param】= {}", param);
        XxlJobLogger.log("demo task run at : {}", DateUtil.now());
        return RandomUtil.randomInt(1, 11) % 2 == 0 ? SUCCESS : FAIL;
    }
}
```

**逐行看：**

- `@Component`：注册成 Spring Bean，这样 XXL-JOB 能扫描到它。
- `@JobHandler("demoTask")`：XXL-JOB 的注解，给这个任务处理器起名 `demoTask`。调度中心新增任务时，"执行器路由"字段填的就是这个名字——调度中心下发任务时会带上 handler 名称，执行器按名称找到这个类来执行。
- `extends IJobHandler`：继承 XXL-JOB 的任务处理器基类，实现 `execute` 方法。
- `execute(String param)`：`param` 是调度中心下发的任务参数，可以在 admin 界面动态填写，实现"同一个 handler 用不同参数跑不同逻辑"。
- `XxlJobLogger.log(...)`：把日志写到 XXL-JOB 的日志系统（不是普通的 `log.info`），这样日志能在调度中心界面查看。
- 返回 `ReturnT`：`SUCCESS` 或 `FAIL`，告诉调度中心任务执行结果。这里用随机数模拟成功/失败，方便观察调度中心的日志记录。

> 💡 前端类比：`@JobHandler("demoTask")` 像给一个函数注册了路由名，调度中心像"远程调用"这个 handler。`param` 像请求参数，`ReturnT` 像响应状态码。

> ⚠️ 注意版本差异：XXL-JOB 2.1.0 用的是 `@JobHandler` 注解 + 继承 `IJobHandler` 的写法。**新版（2.3+）改成了 `@XxlJob("demoTask")` 注解 + 普通方法**，不用继承基类，更轻量。实际开发中以你用的版本为准。

---

## 八、手动操作任务 ManualOperateController.java

这个控制器演示了**通过 HTTP API 操作调度中心**，绕过 admin 界面手动管理任务。实际场景：用户在自己的业务页面配置 cron 和参数，后端调 API 自动创建任务。

```java
@Slf4j
@RestController
@RequestMapping("/xxl-job")
@RequiredArgsConstructor(onConstructor_ = @Autowired)
public class ManualOperateController {
    private final static String baseUri = "http://127.0.0.1:18080/xxl-job-admin";
    private final static String JOB_INFO_URI = "/jobinfo";
    private final static String JOB_GROUP_URI = "/jobgroup";

    // 任务组列表
    @GetMapping("/group")
    public String xxlJobGroup() {
        HttpResponse execute = HttpUtil.createGet(baseUri + JOB_GROUP_URI + "/list").execute();
        return execute.body();
    }

    // 分页任务列表
    @GetMapping("/list")
    public String xxlJobList(Integer page, Integer size) {
        Map<String, Object> jobInfo = Maps.newHashMap();
        jobInfo.put("start", page != null ? page : 0);
        jobInfo.put("length", size != null ? size : 10);
        jobInfo.put("jobGroup", 2);
        jobInfo.put("triggerStatus", -1);
        HttpResponse execute = HttpUtil.createGet(baseUri + JOB_INFO_URI + "/pageList").form(jobInfo).execute();
        return execute.body();
    }

    // 新增任务（核心）
    @GetMapping("/add")
    public String xxlJobAdd() {
        Map<String, Object> jobInfo = Maps.newHashMap();
        jobInfo.put("jobGroup", 2);
        jobInfo.put("jobCron", "0 0/1 * * * ? *");
        jobInfo.put("jobDesc", "手动添加的任务");
        jobInfo.put("author", "admin");
        jobInfo.put("executorRouteStrategy", "ROUND");
        jobInfo.put("executorHandler", "demoTask");
        jobInfo.put("executorParam", "手动添加的任务的参数");
        jobInfo.put("executorBlockStrategy", ExecutorBlockStrategyEnum.SERIAL_EXECUTION);
        jobInfo.put("glueType", GlueTypeEnum.BEAN);
        HttpResponse execute = HttpUtil.createGet(baseUri + JOB_INFO_URI + "/add").form(jobInfo).execute();
        return execute.body();
    }

    // 还有 trigger（手动触发一次）/ remove（删除）/ stop（停止）/ start（启动）
}
```

**新增任务的关键参数：**

| 参数 | 含义 |
| --- | --- |
| `jobGroup` | 执行器分组 ID（在 admin 新增执行器后获得） |
| `jobCron` | cron 表达式，`0 0/1 * * * ? *` 表示每分钟执行 |
| `executorHandler` | 执行器处理器名称，对应 `@JobHandler("demoTask")` |
| `executorParam` | 任务参数，传给 `execute(String param)` |
| `executorRouteStrategy` | 路由策略，`ROUND` 轮询（多执行器实例轮流跑） |
| `executorBlockStrategy` | 阻塞策略，`SERIAL_EXECUTION` 串行（上次没跑完时排队） |
| `glueType` | 任务类型，`BEAN` 表示用代码里定义的 handler |

> 💡 前端类比：这像用 `fetch` 调一个 RESTful API 来管理任务，而不是去点 admin 网页。`executorHandler` 像路由名，`executorRouteStrategy` 像负载均衡策略。

> ⚠️ 本模块的 API 调用能成功，前提是 README 第 4 节描述的"改造 xxl-job-admin"——给相关 Controller 加 `@PermissionLimit(limit = false)` 去掉权限校验。生产环境不建议这么做，应该用 accessToken 鉴权。

---

## 九、运行与验证

### 9.1 部署调度中心（xxl-job-admin）

本模块运行依赖一个已启动的调度中心，按 README 步骤：

1. 克隆 `xxl-job` 仓库，执行 `xxl-job/doc/db/tables_xxl_job.sql` 建库建表。
2. 修改 admin 的 `application.properties`（数据库连接、端口 18080）。
3. 启动 `XxlJobAdminApplication`，访问 `http://localhost:18080/xxl-job-admin`，账号 `admin/123456`。

### 9.2 启动执行器（本模块）

```sh
mvn spring-boot:run
```

启动后执行器会向调度中心注册心跳，在 admin 的"执行器管理"能看到 `spring-boot-demo-task-xxl-job-executor`。

### 9.3 配置并触发任务

1. 在 admin"执行器管理"新增执行器（AppName 填 yml 里的 `app-name`）。
2. "任务管理"新增任务，`JobHandler` 填 `demoTask`，cron 填 `0 0/1 * * * ? *`。
3. 启动任务，到点后执行器执行 `DemoTask.execute`，在 admin"调度日志"查看结果。

### 9.4 用 API 操作

```sh
curl http://localhost:8080/demo/xxl-job/add      # 新增任务
curl http://localhost:8080/demo/xxl-job/list      # 任务列表
curl http://localhost:8080/demo/xxl-job/trigger   # 手动触发一次
```

---

## 十、动手练习

1. **新增一个带参任务**：写一个 `@JobHandler("sendEmailTask")`，`execute` 里根据 `param`（邮箱地址）打印"发送邮件给 xxx"，在 admin 配置任务并传参触发。
2. **观察路由策略**：启动两个执行器实例（端口 9999、9998），任务路由策略设为 `ROUND`，触发多次，观察两个实例轮流执行。
3. **模拟失败重试**：在 `execute` 里故意 `throw new RuntimeException`，在 admin 配置失败重试次数为 3，观察重试行为。
4. **用分片广播**：路由策略设为 `SHARDING_BROADCAST`，在 `execute` 里用 `XxlJobHelper.getShardIndex()`/`getShardTotal()` 打印分片号，启动多实例，观察每个实例拿到不同分片。
5. **API 创建任务**：调用 `/xxl-job/add` 创建一个每 10 秒执行的任务，观察效果。

---

## 十一、本模块知识点总结（结合实际开发详解）

XXL-JOB 是国内使用最广的分布式调度方案之一，掌握它对中大型项目很关键。下面把核心知识点放到真实开发场景里讲透。

### 11.1 三种定时任务方案选型：Spring Task vs Quartz vs XXL-JOB

**实际开发中怎么选？**

| 维度 | Spring Task | Quartz | XXL-JOB |
| --- | --- | --- | --- |
| 复杂度 | 极低 | 中 | 中高（需部署 admin） |
| 可视化 | 无 | 无（需自研） | 有，开箱即用 |
| 动态管理 | 改代码重发版 | 需写代码操作 API | admin 界面 / API，天然支持 |
| 分布式防重 | 不支持 | 集群+数据库锁 | 调度中心统一触发，天然支持 |
| 失败重试 | 无 | 需自研 | 内置 |
| 任务依赖编排 | 无 | 弱 | 子任务依赖 |
| 适用场景 | 单机、简单定时 | 单机强功能/集群 | 分布式、需运维管理 |

**最佳实践：**

- **小项目/单机/任务少**：用 Spring Task，最省事。
- **需要持久化、动态增删但不想引入额外服务**：用 Quartz（如 `23-定时任务_Quartz` 模块）。
- **多服务实例、需要统一管理界面、需要告警和重试**：上 XXL-JOB。

**常见坑：** 团队人少、任务简单却硬上 XXL-JOB，多维护一个 admin 服务反而增加运维负担。技术选型要匹配团队和规模。

### 11.2 "调度中心 + 执行器"架构的精髓

**为什么要把调度和执行分离？**

1. **单一触发源**：调度中心是唯一触发点，天然解决多实例重复执行。Quartz 靠数据库锁防重，有锁竞争开销；XXL-JOB 调度中心只发一次请求，无锁。
2. **职责分离**：调度中心专注"什么时候触发、触发谁、记录结果"，执行器专注"干活"。两边可独立扩缩容。
3. **高可用**：调度中心可集群部署（共享数据库），执行器也可多实例，任一节点宕机不影响整体。

**实际开发的部署形态：**

- 调度中心：1~2 台，集群部署共享一个 MySQL。
- 执行器：就是你的业务服务，几个实例就几个执行器，随业务扩缩容。
- 调度中心和执行器之间网络要通（执行器注册心跳、调度中心下发请求）。

**常见坑：**

- 执行器注册的 IP 错误（多网卡自动获取到内网 IP，调度中心访问不到）：手动配 `xxl.job.executor.ip`。
- 执行器端口被占用：同机多执行器要配不同 `port`。
- 调度中心和执行器版本不一致导致通讯失败：务必版本对齐。

### 11.3 路由策略：多执行器实例怎么选？

当执行器有多个实例时，调度中心按"路由策略"决定这次任务交给谁。XXL-JOB 内置多种策略：

| 策略 | 行为 | 适用场景 |
| --- | --- | --- |
| `FIRST`/`LAST` | 固定选第一个/最后一个 | 调试、指定机器 |
| `ROUND` | 轮询 | 负载均衡，均摊 |
| `RANDOM` | 随机 | 简单负载均衡 |
| `CONSISTENT_HASH` | 一致性哈希 | 同任务固定到同机器（利用本地缓存） |
| `LEAST_FREQUENTLY_USED` | 最不经常使用 | 选最空闲的 |
| `SHARDING_BROADCAST` | 分片广播 | 所有实例都执行，各处理一部分数据 |

**分片广播是重点**：处理大数据量任务时，让 3 个实例各处理 1/3 数据，并行提速。代码里用 `XxlJobHelper.getShardIndex()`（当前分片号）和 `getShardTotal()`（总片数）取模分流：

```java
int index = XxlJobHelper.getShardIndex();
int total = XxlJobHelper.getShardTotal();
// 只处理 id % total == index 的数据
list.stream().filter(x -> x.getId() % total == index).forEach(this::process);
```

**常见坑：** 用了分片广播但代码里没按分片号分流，导致每个实例都处理全量数据，反而重复执行。

### 11.4 阻塞策略：上次任务还没跑完，下次又到点了

当任务执行时间长，超过了一个调度周期，新的调度请求到来时怎么办？XXL-JOB 的阻塞策略：

| 策略 | 行为 |
| --- | --- |
| `SERIAL_EXECUTION` | 串行，排队等上次跑完 |
| `DISCARD_LATER` | 丢弃后来的，本次不执行 |

**最佳实践：** 大多数场景用 `SERIAL_EXECUTION`（保证不丢任务）。只有"实时性任务、宁可丢也不重跑"才用 `DISCARD_LATER`。

**常见坑：** 任务执行时间远超调度间隔还用串行，导致任务越积越多，最终拖垮系统。应该优化任务执行效率或拉长调度间隔。

### 11.5 任务日志：`XxlJobLogger` vs 普通 `log`

本模块用了两种日志：

- `log.info(...)`：写到执行器自己的日志文件（logback），只在执行器机器上能看。
- `XxlJobLogger.log(...)`：写到 XXL-JOB 的日志系统，会随任务回调上传到调度中心，在 admin 界面"调度日志"里能查看。

**最佳实践：** 关键业务节点（开始、结束、异常、关键中间结果）用 `XxlJobLogger.log`，方便在 admin 统一排查；详细的调试日志用普通 `log`。这样既能在 admin 看摘要，又不至于把 admin 日志撑爆。

**常见坑：** 只用普通 `log`，结果任务失败后在 admin 看不到任何线索，还得登机器翻日志，运维体验差。

### 11.6 动态任务管理：API vs 界面

本模块 `ManualOperateController` 演示了用 API 管理任务。**实际开发中 API 方式更常见**，因为：

- 业务系统需要让用户在前端页面配置 cron 和参数，后端调 API 自动建任务。
- 任务和业务数据绑定（如"每个租户一个对账任务"），需程序化管理。

**最佳实践：**

- 封装一个 `XxlJobClient` 服务类，统一调 admin API，处理鉴权（accessToken）、重试、异常。
- 任务参数用 JSON，handler 里解析，灵活传复杂对象。
- 任务描述、作者等元数据填清楚，方便 admin 界面辨识。

**常见坑：** 直接硬编码 `baseUri` 在 Controller 里（本模块为演示如此）。生产应抽到配置类，支持不同环境不同 admin 地址。

### 11.7 Glue 模式：在线写代码

本模块 `glueType` 用的是 `BEAN`（代码里定义 handler）。XXL-JOB 还支持 `GLUE` 模式——直接在 admin 界面写代码，调度时动态编译执行，不用发版。

**实际开发评价：**

- 优点：紧急修复、临时任务不用发版，运维灵活。
- 缺点：代码不在版本库，没有 review，是"魔法代码"，难维护、有安全风险。

**最佳实践：** 生产环境**慎用 Glue**，坚持 `BEAN` 模式让任务代码进版本库、走正常 CI/CD。Glue 只用于临时排查或非关键任务。

---

> 📌 **学习建议**：XXL-JOB 是"调度中心 + 执行器"分离架构的典型代表，理解了它，你就理解了所有分布式调度系统的共性（注册中心、统一触发、路由策略、日志归集）。建议重点掌握三点：架构图能画出来、路由策略（尤其分片广播）会用、动态 API 管理任务会封装。另外，定时任务的本质是"到点触发业务逻辑"，所以任务代码本身要保证幂等（重复执行不产生副作用）、可重入、有超时保护——这些是任务可靠性的根基，比会用框架更重要。
