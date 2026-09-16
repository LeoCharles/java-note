# 37 - 微服务 RPC 与 Dubbo

> 对应项目模块：`demo-dubbo`
> 前置知识：已学完前面模块，理解 Spring Boot 启动类、配置、`@RestController`、依赖注入
> 学习目标：理解什么是 RPC、什么是服务注册中心，看懂 Dubbo 三模块工程（common/provider/consumer），能跑通一次远程调用。

---

## 一、本模块要解决什么问题？

### 1.1 从单体到微服务

前面所有模块都是**单体应用**——所有代码（Controller、Service、DAO）打成一个 jar，跑在一个进程里，方法调用就是普通的方法调用：

```java
// 单体：直接 new 或注入，同一个进程内调用
HelloService helloService = new HelloServiceImpl();
helloService.sayHello("xkcoding");
```

当业务变大，一个 jar 扛不住时，就要拆成多个独立部署的服务（订单服务、用户服务、商品服务……）。这时"用户服务"想调"订单服务"的方法，两者在**不同进程、不同机器**，没法直接 `new`，必须通过网络远程调用——这就是 **RPC（Remote Procedure Call，远程过程调用）**。

> 💡 前端类比：单体就像一个 SPA 里所有组件直接 import 调用；微服务就像多个独立站点，A 站点要通过 HTTP/fetch 调 B 站点的接口。但 RPC 比 HTTP 更"透明"——它让你**像调本地方法一样调远程方法**，底层网络通信被框架隐藏了。

### 1.2 Dubbo 是什么

Dubbo 是阿里巴巴开源的高性能 Java RPC 框架，核心能力：

| 能力 | 说明 |
| --- | --- |
| **远程通信** | 让 A 进程像调本地方法一样调 B 进程的方法 |
| **服务注册与发现** | 通过注册中心（如 Zookeeper）自动找到服务提供者地址 |
| **负载均衡** | 同一个服务部署多份时，自动分配请求 |
| **容错** | 调用失败时自动重试、降级 |

### 1.3 三个核心角色

本模块拆成三个子模块，正好对应 Dubbo 的三个角色：

| 子模块 | Dubbo 角色 | 职责 | 前端类比 |
| --- | --- | --- | --- |
| `dubbo-common` | 公共契约 | 定义服务接口，provider 和 consumer 都依赖它 | 像 TypeScript 的 `.d.ts` 类型定义，前后端共享 |
| `dubbo-provider` | 服务提供方 | 实现接口，注册到注册中心，等待被调 | 像 API 服务端 |
| `dubbo-consumer` | 服务调用方 | 从注册中心发现服务，发起远程调用 | 像 API 客户端 |

---

## 二、项目结构

```
demo-dubbo/                         ← 父工程（packaging=pom，只聚合）
├── pom.xml
├── dubbo-common/                   ← 公共模块：只放接口
│   └── src/main/java/.../service/HelloService.java
├── dubbo-provider/                 ← 服务提供方
│   ├── pom.xml                     ← 依赖 common + dubbo + zkclient
│   └── src/main/
│       ├── java/.../SpringBootDemoDubboProviderApplication.java  # 启动类
│       ├── java/.../service/HelloServiceImpl.java                # 接口实现
│       └── resources/application.yml                              # 配置
└── dubbo-consumer/                 ← 服务调用方
    ├── pom.xml                     ← 依赖 common + dubbo + zkclient
    └── src/main/
        ├── java/.../SpringBootDemoDubboConsumerApplication.java   # 启动类
        ├── java/.../controller/HelloController.java               # 调用 RPC
        └── resources/application.yml                              # 配置
```

**为什么 common 单独抽出来？** 因为 provider 和 consumer 都要用 `HelloService` 接口：provider 要实现它，consumer 要声明引用它。把接口放公共模块，两边依赖它，保证"契约一致"——就像前后端共享一份 TypeScript 类型定义，避免字段对不上。

---

## 三、父 pom.xml

```xml
<artifactId>demo-dubbo</artifactId>
<packaging>pom</packaging>
<modules>
    <module>dubbo-common</module>
    <module>dubbo-provider</module>
    <module>dubbo-consumer</module>
</modules>

<properties>
    <dubbo.starter.version>2.0.0</dubbo.starter.version>
    <zkclient.version>0.10</zkclient.version>
</properties>
```

- `<packaging>pom</packaging>`：父工程只聚合，不产代码。
- 集中声明 dubbo starter 和 zkclient 的版本，子模块引用时不写版本号。
- 注意：本父 POM 没有在 `<build>` 里配 `spring-boot-maven-plugin`（common 不需要打成可执行 jar，provider/consumer 各自的 pom 里配了）。

---

## 四、dubbo-common：公共契约

`HelloService.java`：

```java
public interface HelloService {
    /**
     * 问好
     *
     * @param name 姓名
     * @return 问好
     */
    String sayHello(String name);
}
```

- 只是一个**接口**，没有任何实现。
- 它定义了"服务契约"：方法名 `sayHello`、参数 `String name`、返回 `String`。
- provider 实现它，consumer 引用它，两边都依赖这个公共模块，保证签名一致。

> 💡 前端类比：这就像 `@types/api` 包，前端和 BFF 共享同一份接口类型定义。接口本身不包含实现，只是约定"调这个方法名、传这些参数、返回这个类型"。

common 的 pom 没有任何业务依赖，因为它只定义接口（接口在编译期只需要 JDK）。

---

## 五、dubbo-provider：服务提供方

### 5.1 pom.xml 依赖

```xml
<dependencies>
    <!-- 1. Spring Boot Web -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-web</artifactId>
    </dependency>

    <!-- 2. Dubbo Spring Boot Starter -->
    <dependency>
        <groupId>com.alibaba.spring.boot</groupId>
        <artifactId>dubbo-spring-boot-starter</artifactId>
        <version>${dubbo.starter.version}</version>
    </dependency>

    <!-- 3. 公共契约模块 -->
    <dependency>
        <groupId>${project.groupId}</groupId>
        <artifactId>dubbo-common</artifactId>
        <version>${project.version}</version>
    </dependency>

    <!-- 4. Zookeeper 客户端 -->
    <dependency>
        <groupId>com.101tec</groupId>
        <artifactId>zkclient</artifactId>
        <version>${zkclient.version}</version>
    </dependency>

    <dependency>
        <groupId>org.projectlombok</groupId>
        <artifactId>lombok</artifactId>
        <optional>true</optional>
    </dependency>
</dependencies>
```

四个关键依赖：

1. `spring-boot-starter-web`：让 provider 也是一个 Spring Boot Web 应用（虽然 RPC 不走 HTTP，但启动需要 Spring 容器）。
2. `dubbo-spring-boot-starter`：Dubbo 的 Spring Boot 整合包，自动配置 Dubbo。
3. `dubbo-common`：依赖公共模块，拿到 `HelloService` 接口。
4. `zkclient`：Zookeeper 的客户端，Dubbo 用它连注册中心。

### 5.2 启动类

```java
@EnableDubboConfiguration
@SpringBootApplication
public class SpringBootDemoDubboProviderApplication {
    public static void main(String[] args) {
        SpringApplication.run(SpringBootDemoDubboProviderApplication.class, args);
    }
}
```

- `@SpringBootApplication`：熟悉的 Spring Boot 启动注解。
- `@EnableDubboConfiguration`：**Dubbo 专属注解**，开启 Dubbo 自动配置，扫描 `@Service` 注解把服务注册出去。

### 5.3 接口实现

```java
@Service
@Component
@Slf4j
public class HelloServiceImpl implements HelloService {
    @Override
    public String sayHello(String name) {
        log.info("someone is calling me......");
        return "say hello to: " + name;
    }
}
```

**关键点：这里的 `@Service` 不是 Spring 的 `@Service`，而是 `com.alibaba.dubbo.config.annotation.Service`（Dubbo 的注解）！**

- Dubbo 的 `@Service`：告诉 Dubbo "这是一个对外提供的服务实现，请把它注册到注册中心，暴露为 RPC 服务"。
- Spring 的 `@Component`：让 Spring 也把这个类管理成 Bean（Dubbo 的 `@Service` 不被 Spring 识别，所以要额外加 `@Component`）。
- `@Slf4j`：Lombok 注入日志对象，方便打印日志。

> ⚠️ 新手最容易踩的坑：import 错 `@Service`。如果导了 `org.springframework.stereotype.Service`，服务不会被 Dubbo 注册，consumer 调用时找不到服务报错。**必须用 Dubbo 包下的 `@Service`。**

### 5.4 配置文件

```yaml
server:
  port: 9090
  servlet:
    context-path: /demo

spring:
  dubbo:
    application:
      name: spring-boot-demo-dubbo-provider
      registry: zookeeper://localhost:2181
```

- `server.port: 9090`：provider 跑在 9090 端口（和 consumer 的 8080 错开，方便本机同时跑两个）。
- `spring.dubbo.application.name`：本服务在 Dubbo 里的应用名（注册中心用它标识）。
- `spring.dubbo.application.registry: zookeeper://localhost:2181`：注册中心地址，指向本机的 Zookeeper（端口 2181 是 ZK 默认端口）。

---

## 六、dubbo-consumer：服务调用方

### 6.1 pom.xml

依赖和 provider 几乎一样（web、dubbo starter、common、zkclient），区别是它有 Controller，是最终对外的 Web 入口。

### 6.2 启动类

```java
@SpringBootApplication
@EnableDubboConfiguration
public class SpringBootDemoDubboConsumerApplication {
    public static void main(String[] args) {
        SpringApplication.run(SpringBootDemoDubboConsumerApplication.class, args);
    }
}
```

同样要加 `@EnableDubboConfiguration`，开启 Dubbo 自动配置，扫描 `@Reference` 注入远程服务。

### 6.3 Controller：远程调用

```java
@RestController
@Slf4j
public class HelloController {
    @Reference
    private HelloService helloService;

    @GetMapping("/sayHello")
    public String sayHello(@RequestParam(defaultValue = "xkcoding") String name) {
        log.info("i'm ready to call someone......");
        return helloService.sayHello(name);
    }
}
```

**核心是 `@Reference` 注解**：

- `@Reference`（`com.alibaba.dubbo.config.annotation.Reference`）：Dubbo 注解，告诉 Dubbo "这是一个远程服务引用，请从注册中心找到它的地址，生成一个远程代理注入进来"。
- 注入后，`helloService` 看起来是个普通的 `HelloService` 对象，但调 `helloService.sayHello(name)` 时，底层会：
  1. 把方法名、参数序列化成网络报文
  2. 通过网络发给 provider
  3. provider 执行真实实现，把结果序列化返回
  4. consumer 拿到结果返回

**对调用方来说，完全像调本地方法**——这就是 RPC 的"透明性"。

> 💡 前端类比：这像前端用 `axios` 调一个接口，但 Dubbo 更进一步——它连 `axios` 这层都省了，你直接调一个"看起来是本地对象"的方法，框架帮你把请求发出去。类比一下 React Query 或 tRPC：你在客户端写 `sayHello(name)`，框架自动把它变成远程请求并返回结果，类型还一致。

### 6.4 配置文件

```yaml
server:
  port: 8080
  servlet:
    context-path: /demo

spring:
  dubbo:
    application:
      name: spring-boot-demo-dubbo-consumer
      registry: zookeeper://127.0.0.1:2181
```

consumer 跑 8080 端口，注册中心同样指向本机 ZK。**provider 和 consumer 必须连同一个注册中心**，否则 consumer 找不到 provider。

---

## 七、注册中心 Zookeeper 的作用

本模块用 Zookeeper（简称 ZK）做注册中心。理解它的角色是理解 Dubbo 的关键。

### 7.1 为什么需要注册中心？

如果没有注册中心，consumer 要硬编码 provider 的 IP 端口：

```java
// 没有注册中心的写法（硬编码）
HelloService helloService = RpcProxy.create("192.168.1.100", 20880, HelloService.class);
```

问题：provider 换机器、加机器、宕机，consumer 都要改代码。注册中心解决这个——它像一个"电话簿"，provider 启动时把自己的地址登记上去，consumer 调用时从电话簿查地址，provider 挂了电话簿自动删掉它。

### 7.2 工作流程

```
启动阶段：
  1. provider 启动 → 把"我提供 HelloService，地址是 192.168.1.100:20880"写入 ZK
  2. consumer 启动 → 订阅 ZK 上的 HelloService，拿到 provider 地址列表

调用阶段：
  3. consumer 调 helloService.sayHello() → Dubbo 从地址列表选一个 → 发网络请求
  4. provider 收到 → 执行实现 → 返回结果
  5. provider 宕机 → ZK 检测到连接断开 → 删除该地址 → consumer 收到通知更新列表
```

> 💡 前端类比：注册中心像 DNS 或 Service Worker 的路由表，或微前端的"模块联邦"里共享远程模块地址的机制。你不需要记 IP，只记服务名，注册中心帮你解析。

### 7.3 用 Docker 启动 ZK

```sh
docker pull wurstmeister/zookeeper
docker run -d -p 2181:2181 -p 2888:2888 -p 3888:3888 --name zk wurstmeister/zookeeper
```

- 2181：客户端连接端口（provider/consumer 连这个）
- 2888/3888：ZK 集群内部通信端口（单机用不到，集群选举用）

---

## 八、运行与验证

### 8.1 启动顺序（重要）

1. **先启动 Zookeeper**：`docker start zk`
2. **再启动 provider**：运行 `SpringBootDemoDubboProviderApplication`，控制台看到 Dubbo 注册成功日志。
3. **最后启动 consumer**：运行 `SpringBootDemoDubboConsumerApplication`。

> ⚠️ 顺序不能反：ZK 没起，provider 注册失败；provider 没起，consumer 订阅不到服务。

### 8.2 测试调用

```sh
curl http://localhost:8080/demo/sayHello
# 返回：say hello to: xkcoding

curl "http://localhost:8080/demo/sayHello?name=Claude"
# 返回：say hello to: Claude
```

### 8.3 观察日志

- consumer 控制台：`i'm ready to call someone......`（发起调用前打印）
- provider 控制台：`someone is calling me......`（收到调用时打印）

两条日志分别在两个进程，证明这是一次**跨进程远程调用**。

---

## 九、动手练习

1. **故意停掉 provider**：停掉 provider 后再调接口，观察 consumer 报什么错（体会服务不可用的异常）。
2. **改接口签名**：在 common 的 `HelloService` 加一个参数，只重新编译 provider 不重启 consumer，观察调用是否报错（体会"契约一致"的重要性）。
3. **启动两个 provider**：把第二个 provider 的端口改成 9091，同时启动两个，调用多次观察两个 provider 是否轮流收到请求（体会负载均衡）。
4. **换注册中心地址**：把 ZK 地址改错（如 `zookeeper://localhost:9999`），启动观察报错（体会注册中心不可达的影响）。
5. **加一个新服务**：在 common 定义 `GoodbyeService`，provider 实现并注册，consumer 注入并调用，跑通一次完整的新服务发布。

---

## 十、本模块知识点总结（结合实际开发详解）

Dubbo 是 Java 微服务生态的经典 RPC 框架，理解它就理解了"服务化"的核心思路。下面把关键点放到真实开发场景里讲透。

### 10.1 RPC vs HTTP：到底用哪个？

**实际开发中的选择：**

- **Dubbo RPC**：Java 技术栈内部服务间调用。性能高（自定义二进制协议、长连接），调用透明（像本地方法），但**强依赖 Java**（跨语言不友好）。
- **HTTP/REST**：跨语言调用（Java 调 Go、前端调后端）。通用、易调试，但性能略低（文本协议、短连接）、调用不透明（要手写 HTTP 客户端）。
- **gRPC**：跨语言 RPC，基于 HTTP/2 + Protobuf，兼顾性能和跨语言，是云原生时代的主流选择。

**最佳实践**：同一公司 Java 内部用 Dubbo/gRPC 提速；对外或跨语言用 REST。很多公司是"对外 REST，对内 RPC"的混合架构。

**常见坑**：以为 RPC 万能，结果前端要调服务还得包一层 REST 网关——RPC 服务不适合直接暴露给浏览器。

### 10.2 公共契约模块：微服务的"类型共享"

本模块把接口抽到 `dubbo-common`，这是微服务的标准做法。

**实际开发中契约模块包含什么？**

- 服务接口（`HelloService`）
- 传输的 DTO（如 `UserDTO`、`OrderDTO`）
- 枚举、常量
- 异常定义

**为什么不能 provider 和 consumer 各自定义一份？** 因为 RPC 要序列化方法名、参数类型、参数值，两边类型签名必须完全一致，否则反序列化失败。共享一份契约模块从源头保证一致。

> 💡 前端类比：这就是 TypeScript 的 `@types/shared` 包，前端和 BFF 都装它，接口字段对不对得上编译期就知道了，而不是等运行时才发现字段名拼错。

**常见坑**：契约模块里放了业务逻辑（不只是接口和 DTO），导致 provider/consumer 都依赖一堆用不到的实现，包变大、耦合变高。**契约模块应该只放"约定"，不放"实现"。**

### 10.3 `@Service` vs `@Reference`：Dubbo 的两个核心注解

| 注解 | 所在方 | 作用 | 前端类比 |
| --- | --- | --- | --- |
| `@Service`（Dubbo 包） | provider | 标记"我是服务实现，把我注册出去" | 像后端定义一个路由 handler |
| `@Reference`（Dubbo 包） | consumer | 标记"注入一个远程服务代理" | 像前端 `useFetch` 自动请求远程接口 |

**实际开发要点：**

1. **千万别 import 错**：`@Service` 要用 `com.alibaba.dubbo.config.annotation.Service`，不是 Spring 的。IDE 自动导入常导成 Spring 的，导致服务没注册。最佳实践是给 Dubbo 的 `@Service` 配一个 IDE 模板或 live template。
2. **`@Reference` 默认按接口类型匹配**：如果同一个接口有多个实现版本，要用 `@Reference(version = "1.0.0")` 或 `group` 区分。
3. **`@Reference` 注入的是代理**：调它的方法会触发网络请求，不要在构造器里调（启动时 provider 可能还没注册好），要在业务方法里调。

### 10.4 注册中心：服务发现的核心

**主流注册中心对比：**

| 注册中心 | 特点 | 适用场景 |
| --- | --- | --- |
| Zookeeper | 强一致性（CP）、成熟稳定 | 传统 Dubbo 架构 |
| Nacos | 既可 AP 也可 CP、自带配置中心 | Spring Cloud Alibaba 生态（现代首选） |
| Eureka | AP、已停止维护 | 老 Spring Cloud Netflix |
| Consul | 多数据中心、支持健康检查 | HashiCorp 生态 |

**最佳实践**：新项目用 Nacos（一个组件同时做注册中心和配置中心，省事），老项目维护用 ZK。Dubbo 3.x 已原生支持 Nacos。

**常见坑**：ZK 是 CP 系统，强调一致性，网络分区时可能短暂不可用；Nacos 默认 AP，强调可用性，更适合大规模服务发现。选型时别只看"能不能用"，要看 CAP 取舍是否符合业务。

### 10.5 Dubbo 的负载均衡与容错

本模块 provider 只有一个，看不出负载均衡。实际生产同一个服务会部署多个实例，Dubbo 内置多种负载策略：

| 策略 | 说明 |
| --- | --- |
| Random（默认） | 加权随机 |
| RoundRobin | 加权轮询 |
| LeastActive | 选活跃数最少的（处理慢的少分） |
| ConsistentHash | 一致性哈希（相同参数请求落同一台） |

**容错策略**（调用失败时怎么办）：

| 策略 | 说明 |
| --- | --- |
| Failover（默认） | 失败自动重试，切换服务器重试 |
| Failfast | 快速失败，不重试（适合非幂等写操作） |
| Failsafe | 失败忽略，不报错（适合日志等次要操作） |
| Forking | 同时调多台，一台成功就返回 |

**最佳实践**：查询用 Failover（重试无副作用），写操作用 Failfast（避免重复写入）。重试次数别设太大（默认 2 次），否则雪崩。

### 10.6 Dubbo 版本与 Spring Boot 整合的演进

本模块用的是老版本（`dubbo-spring-boot-starter` 2.0.0，阿里巴巴时期的包名 `com.alibaba`）。实际开发要了解版本演进：

| 阶段 | 包名 | 说明 |
| --- | --- | --- |
| Dubbo 2.x（阿里） | `com.alibaba.dubbo` | 老版本，本模块用的就是 |
| Dubbo 2.6+（Apache） | `org.apache.dubbo` | 捐给 Apache 后 |
| Dubbo 3.x | `org.apache.dubbo` | 云原生，支持 Triple 协议（基于 HTTP/2） |

**最佳实践**：新项目直接上 Dubbo 3.x + Nacos，用 `dubbo-spring-boot-starter`（Apache 版）。本模块的老写法理解原理即可，别照抄依赖版本。

**常见坑**：老教程的包名 `com.alibaba` 和新版的 `org.apache` 混用，导致类冲突。**一个项目里只用一个版本的包名。**

### 10.7 微服务架构的取舍：什么时候才该上 RPC？

**实际开发判断标准：**

- **单体能扛住就别拆**：团队小、业务简单时，单体开发快、部署简单、调试容易。微服务是解决"规模"问题的，不是炫技。
- **拆的时机**：团队超过 10 人、部署频率互相阻塞、某模块要独立扩容（如秒杀）时，才拆。
- **拆的代价**：网络调用比本地调用慢百倍、调试困难（一个请求跨多个服务）、要管服务治理（注册、限流、熔断、链路追踪）。

> 💡 前端类比：别一上来就微前端。单体 SPA 能搞定就别拆，拆了之后共享状态、样式隔离、部署协调都是成本。微服务/微前端是规模到了的妥协，不是默认选项。

---

> 📌 **学习建议**：作为前端转后端的工程师，理解 RPC 的关键是抓住"透明性"——框架把网络通信伪装成本地方法调用，让你不用关心序列化、网络、重试。但"透明"不等于"免费"，每次调用都是一次网络 IO，比本地方法慢得多，别在循环里无脑调远程服务。另外，Dubbo 这套"契约模块 + 注册中心 + 提供者/消费者"的架构，和前端的"类型共享 + API 网关 + 前端调用"是同构的，用这个映射来理解会快很多。
