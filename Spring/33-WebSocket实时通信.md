# 33 - Spring Boot 集成 WebSocket 实现实时通信

> 对应项目模块：`demo-websocket`
> 前置知识：已学完前 32 个模块，了解 Spring Boot 基础、`@RestController`、定时任务 `@Scheduled`
> 学习目标：掌握 Spring Boot 集成 WebSocket + STOMP + SockJS 实现"服务端主动推送"的完整套路，理解端点（endpoint）、消息代理（broker）、订阅（subscribe）三大概念。

---

## 一、本模块要解决什么问题？

### 1.1 为什么需要 WebSocket？

传统的 HTTP 请求-响应模型是"单向、短连接"——前端发请求，后端回响应，连接就断了。如果后端有新数据想**主动**告诉前端，HTTP 做不到，只能靠前端"轮询"（每隔几秒发一次请求问"有新消息吗？"）。

轮询的缺点很明显：

- **浪费资源**：大部分请求的答案是"没有"，白白消耗带宽和服务器连接数。
- **延迟高**：数据产生后，要等下一次轮询才能拿到，平均延迟 = 轮询间隔 / 2。
- **实时性差**：聊天、股票行情、服务器监控这类场景，轮询体验很差。

> 💡 前端类比：你在前端肯定用过 `new WebSocket('ws://...')`。WebSocket 是一个**全双工、长连接**协议，建立连接后，前后端可以随时互发消息，就像打了一通电话，双方都能随时说话。HTTP 轮询则像发短信——发一条等一条回，再发下一条。

### 1.2 本模块做了什么？

网上大部分 WebSocket 例子都是聊天室（前端发消息给后端，后端广播）。本模块换了个场景：**后端定时采集服务器状态（CPU、内存、磁盘、JVM），每 2 秒主动推送给前端**，前端用 Vue + Element-UI 实时展示。这演示的是 WebSocket 最有价值的用法——**服务端推送**。

### 1.3 为什么要 STOMP 和 SockJS？

原生 WebSocket 只是"一根管道"，你往里塞什么字节都行，但它**没有消息格式约定、没有路由、没有订阅机制**。如果直接用原生 WebSocket，你得自己定义消息协议（怎么区分"这条消息是 CPU 数据还是内存数据"）、自己维护"谁订阅了什么"。

Spring Boot 用了两个增强：

| 技术 | 解决的问题 | 前端类比 |
| --- | --- | --- |
| **STOMP** | 给 WebSocket 加上"消息协议"——有 SUBSCRIBE/SEND 等命令，有"主题（topic）"路由 | 像 MQTT/AMQP，或前端的 Pub-Sub 事件总线 |
| **SockJS** | 浏览器不支持 WebSocket 时的降级方案（退回长轮询等），并解决跨域问题 | 像 polyfill，给老浏览器兜底 |

> 💡 前端类比：原生 WebSocket 像 `XMLHttpRequest`，STOMP 像 `fetch` 加上了约定，SockJS 像 axios 的拦截器+降级。三者关系：**SockJS 提供传输层兜底，STOMP 提供应用层协议，WebSocket 是底层通道**。

---

## 二、项目结构

```
demo-websocket/
├── pom.xml
└── src/main/
    ├── java/com/xkcoding/websocket/
    │   ├── SpringBootDemoWebsocketApplication.java   # 启动类（@EnableScheduling）
    │   ├── common/
    │   │   └── WebSocketConsts.java                  # 常量：推送主题路径
    │   ├── config/
    │   │   └── WebSocketConfig.java                  # WebSocket 配置（端点+代理）
    │   ├── controller/
    │   │   └── ServerController.java                 # HTTP 接口：首次查询服务器状态
    │   ├── model/                                    # 服务器信息实体（OSHI 采集）
    │   │   ├── Server.java                           #   聚合：CPU/Mem/Jvm/Sys/SysFile
    │   │   └── server/ (Cpu, Mem, Jvm, Sys, SysFile)
    │   ├── payload/                                  # 给前端的 VO（键值对形式）
    │   │   ├── KV.java                               #   {key, value} 键值对
    │   │   ├── ServerVO.java                         #   聚合 VO
    │   │   └── server/ (CpuVO, MemVO, JvmVO, SysVO, SysFileVO)
    │   ├── task/
    │   │   └── ServerTask.java                       # 定时任务：每 2s 推送服务器状态
    │   └── util/
    │       ├── IpUtil.java                           # 获取主机名/IP
    │       └── ServerUtil.java                       # 实体→VO 转换
    └── resources/
        ├── application.yml
        └── static/
            ├── server.html                           # 前端页面（Vue + Element-UI）
            └── js/ (sockjs.min.js, stomp.js)          # 前端依赖
```

注意本模块把前端页面放在 `src/main/resources/static/` 下——Spring Boot 会把 `static/` 下的静态资源直接映射成 URL，访问 `http://localhost:8080/demo/server.html` 就能打开页面。

---

## 三、逐行拆解 pom.xml

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-websocket</artifactId>
</dependency>
```

这是核心依赖。`spring-boot-starter-websocket` 一键引入了：

- `spring-websocket`：Spring 的 WebSocket 支持
- `spring-messaging`：STOMP 消息协议支持
- `spring-boot-starter-web`（内嵌 Tomcat，且 Tomcat 支持 WebSocket）

```xml
<dependency>
    <groupId>com.github.oshi</groupId>
    <artifactId>oshi-core</artifactId>
    <version>${oshi.version}</version>
</dependency>
```

`oshi-core` 是一个跨平台的系统信息采集库，能读 CPU、内存、磁盘、操作系统信息。本模块用它采集服务器状态——和 WebSocket 本身无关，只是给推送提供"有意义的业务数据"。

其他依赖（hutool、guava、lombok）前面模块都见过，不赘述。

---

## 四、核心：WebSocketConfig 配置类

`config/WebSocketConfig.java` 是整个模块的灵魂：

```java
@Configuration
@EnableWebSocket
@EnableWebSocketMessageBroker
public class WebSocketConfig implements WebSocketMessageBrokerConfigurer {

    @Override
    public void registerStompEndpoints(StompEndpointRegistry registry) {
        // 注册一个 /notification 端点，前端通过这个端点进行连接
        registry.addEndpoint("/notification")
            //解决跨域问题
            .setAllowedOrigins("*").withSockJS();
    }

    @Override
    public void configureMessageBroker(MessageBrokerRegistry registry) {
        //定义了一个客户端订阅地址的前缀信息，也就是客户端接收服务端发送消息的前缀信息
        registry.enableSimpleBroker("/topic");
    }
}
```

### 4.1 三个关键注解

| 注解 | 作用 |
| --- | --- |
| `@Configuration` | 标记为配置类，会被 Spring 容器管理 |
| `@EnableWebSocket` | 开启 WebSocket 支持（声明式开关） |
| `@EnableWebSocketMessageBroker` | 开启"基于消息代理"的 WebSocket 支持，启用 STOMP |

`@EnableWebSocketMessageBroker` 是关键——它让 WebSocket 从"裸管道"升级成"带消息代理的通信系统"。实现 `WebSocketMessageBrokerConfigurer` 接口后，重写两个方法来配置。

### 4.2 `registerStompEndpoints`：注册端点（前端连接入口）

```java
registry.addEndpoint("/notification")
    .setAllowedOrigins("*")
    .withSockJS();
```

- `addEndpoint("/notification")`：注册一个 WebSocket 端点，路径是 `/notification`。前端连接地址就是 `http://localhost:8080/demo/notification`（加上 context-path `/demo`）。
- `setAllowedOrigins("*")`：允许跨域。WebSocket 连接默认受同源策略限制，这里放开所有来源。**生产环境不要用 `*`**，应指定具体域名。
- `withSockJS()`：启用 SockJS 兜底。如果浏览器不支持 WebSocket，SockJS 会降级用 XHR 流、长轮询等方式模拟。

> 💡 前端类比：端点就像"电话总机号码"。前端拨这个号（连接端点），才能接入通信系统。没有端点，前端连不上。

### 4.3 `configureMessageBroker`：配置消息代理

```java
registry.enableSimpleBroker("/topic");
```

- `enableSimpleBroker("/topic")`：启用一个**简单消息代理**（基于内存），它处理所有以 `/topic` 开头的订阅。
- 含义：前端可以订阅 `/topic/xxx`，后端往 `/topic/xxx` 发消息，代理会转发给所有订阅者。

**消息流向（重点理解）：**

```
后端 ServerTask                              前端浏览器
    │                                            │
    │  wsTemplate.convertAndSend("/topic/server", data)
    │           ↓                                │
    │      简单消息代理（/topic 前缀）            │
    │           ↓                                │
    │           └──── 通过 WebSocket 推送 ──────→│
    │                                            │  stompClient.subscribe("/topic/server", cb)
    │                                            │  → 更新页面
```

还有一类路径没在本模块出现，但必须知道：`@MessageMapping` 注解的方法处理**前端发给后端**的消息（前缀默认 `/app`）。本模块只有后端→前端推送，没有前端→后端，所以没用 `@MessageMapping`。

> 💡 前端类比：消息代理像 Redis Pub/Sub 或前端的 EventEmitter。`/topic/server` 是频道名，后端 publish 到这个频道，所有 subscribe 了这个频道的客户端都能收到。

---

## 五、常量类 WebSocketConsts

```java
public interface WebSocketConsts {
    String PUSH_SERVER = "/topic/server";
}
```

定义推送主题路径。用 `interface` 当常量容器是 Java 老写法（接口字段默认 `public static final`），现代代码更推荐 `final class` + `private` 构造器或枚举。这里后端推送和前端订阅都用同一个常量，避免硬编码不一致。

---

## 六、定时推送任务 ServerTask

`task/ServerTask.java` 是"服务端主动推送"的触发点：

```java
@Slf4j
@Component
public class ServerTask {
    @Autowired
    private SimpMessagingTemplate wsTemplate;

    @Scheduled(cron = "0/2 * * * * ?")
    public void websocket() throws Exception {
        log.info("【推送消息】开始执行：{}", DateUtil.formatDateTime(new Date()));
        Server server = new Server();
        server.copyTo();
        ServerVO serverVO = ServerUtil.wrapServerVO(server);
        Dict dict = ServerUtil.wrapServerDict(serverVO);
        wsTemplate.convertAndSend(WebSocketConsts.PUSH_SERVER, JSONUtil.toJsonStr(dict));
        log.info("【推送消息】执行结束：{}", DateUtil.formatDateTime(new Date()));
    }
}
```

### 6.1 `SimpMessagingTemplate`：后端推送的 API

这是 Spring 提供的"消息发送模板"。注入它后，在任意业务代码里都能往 WebSocket 推消息，核心方法：

| 方法 | 作用 |
| --- | --- |
| `convertAndSend(destination, payload)` | 发送到指定主题，所有订阅者都能收到（广播） |
| `convertAndSendToUser(user, destination, payload)` | 发送给指定用户（点对点，需配合用户认证） |

本模块用 `convertAndSend("/topic/server", json)` 广播服务器状态给所有订阅者。

### 6.2 `@Scheduled(cron = "0/2 * * * * ?")`

每 2 秒执行一次。cron 表达式含义：从第 0 秒开始，每 2 秒触发。注意启动类必须加 `@EnableScheduling` 才能让 `@Scheduled` 生效（本模块启动类确实加了）。

### 6.3 推送流程

1. `new Server()` + `server.copyTo()`：用 OSHI 采集当前服务器状态（CPU、内存、JVM、磁盘）。
2. `ServerUtil.wrapServerVO(server)`：把实体转成 VO（给前端用的键值对结构）。
3. `ServerUtil.wrapServerDict(serverVO)`：包装成 Hutool 的 `Dict`（有序键值对，方便序列化）。
4. `wsTemplate.convertAndSend("/topic/server", JSONUtil.toJsonStr(dict))`：把 JSON 字符串推送到 `/topic/server` 主题。

> 💡 前端类比：这就像后端开了个 `setInterval`，每 2 秒采集一次数据，然后 `socket.emit('server', data)` 广播给所有客户端。区别是 Java 里用 `SimpMessagingTemplate` 而非 `io.emit`。

---

## 七、HTTP 接口：ServerController

```java
@RestController
@RequestMapping("/server")
public class ServerController {
    @GetMapping
    public Dict serverInfo() throws Exception {
        Server server = new Server();
        server.copyTo();
        ServerVO serverVO = ServerUtil.wrapServerVO(server);
        return ServerUtil.wrapServerDict(serverVO);
    }
}
```

这是个普通 HTTP 接口（`GET /demo/server`），返回当前服务器状态。**为什么要有它？** 因为 WebSocket 推送是每 2 秒一次，页面刚打开时要等最多 2 秒才有数据。前端在建立 WebSocket 连接前，先调这个 HTTP 接口拿到"初始状态"立即渲染，再用 WebSocket 接收后续更新。这是"HTTP 首屏 + WebSocket 增量"的常见组合。

---

## 八、服务器信息采集：Server 实体与 OSHI

`model/Server.java` 用 OSHI 采集系统信息。核心是 `copyTo()` 方法：

```java
public void copyTo() throws Exception {
    SystemInfo si = new SystemInfo();
    HardwareAbstractionLayer hal = si.getHardware();
    setCpuInfo(hal.getProcessor());    // CPU 使用率
    setMemInfo(hal.getMemory());        // 物理内存
    setSysInfo();                       // 操作系统、主机名、IP
    setJvmInfo();                       // JVM 内存、Java 版本
    setSysFiles(si.getOperatingSystem()); // 磁盘分区
}
```

OSHI 是跨平台的，能读到底层硬件信息。注意 `setCpuInfo` 里有一句 `Util.sleep(OSHI_WAIT_SECOND)`（等待 1 秒）——因为 CPU 使用率需要"两次采样之差"计算，OSHI 要间隔 1 秒读两次 tick 才能算出使用率。

这部分和 WebSocket 无关，只是提供业务数据。**前端同学重点关注的是数据结构**：最终 `ServerUtil.wrapServerDict` 把数据转成 `{cpu:[{key,value}], mem:[...], jvm:[...], sys:[...], sysFile:[...]}` 的键值对数组，方便前端表格渲染。

---

## 九、前端页面 server.html

前端用 Vue 2 + Element-UI + SockJS + STOMP 实现接收。核心 JS：

```javascript
const wsHost = "http://localhost:8080/demo/notification";
const wsTopic = "/topic/server";

// 1. 建立 SockJS 连接，套上 STOMP 协议
this.socket = new SockJS(wsHost);
this.stompClient = Stomp.over(this.socket);

// 2. 连接成功后，订阅主题
this.stompClient.connect({}, (frame) => {
    this.isConnected = true;
    // 订阅 /topic/server，收到消息就更新数据
    this.stompClient.subscribe(wsTopic, (response) => {
        this.server = JSON.parse(response.body);
    });
});

// 3. 断开
this.stompClient.disconnect();
```

**前端同学看这段应该很亲切**——这就是标准的 STOMP 客户端用法：

1. `new SockJS(endpoint)`：连到后端注册的端点 `/notification`。
2. `Stomp.over(socket)`：在 SockJS 连接上套 STOMP 协议。
3. `connect({}, callback)`：握手，成功后回调。
4. `subscribe(topic, callback)`：订阅主题，后端往这个主题发消息，回调就被触发，`response.body` 是消息内容。
5. `disconnect()`：主动断开。

页面用 `mounted()` 自动连接、`beforeDestroy()` 自动断开，符合 Vue 生命周期管理资源的最佳实践。

---

## 十、启动类

```java
@SpringBootApplication
@EnableScheduling
public class SpringBootDemoWebsocketApplication {
    public static void main(String[] args) {
        SpringApplication.run(SpringBootDemoWebsocketApplication.class, args);
    }
}
```

注意 `@EnableScheduling`——没有它，`ServerTask` 里的 `@Scheduled` 不生效，推送就不会触发。这是本模块"能跑起来"的隐藏前提。

---

## 十一、运行与验证

1. 启动 `SpringBootDemoWebsocketApplication`。
2. 浏览器访问 `http://localhost:8080/demo/server.html`。
3. 页面自动连接 WebSocket，每 2 秒表格数据刷新一次（CPU、内存、JVM、磁盘）。
4. 点"断开连接"按钮，数据停止刷新；点"手动连接"恢复。
5. 也可以直接调 HTTP 接口 `GET http://localhost:8080/demo/server` 拿一次性快照。

---

## 十二、动手练习

1. **加一个新主题**：复制 `ServerTask`，加一个每 5 秒推送 JVM 信息的任务，推送到 `/topic/jvm`，前端再订阅这个主题，分开展示。
2. **实现前端发消息给后端**：在后端加一个 `@MessageMapping("/hello")` 方法，前端用 `stompClient.send("/app/hello", {}, JSON.stringify({name:'x'}))` 发消息，后端收到后广播。体会"双向通信"。
3. **改成点对点推送**：用 `convertAndSendToUser` 给指定用户推送（需要配合 Spring Security 的认证用户），体会广播 vs 点对点的区别。
4. **去掉 SockJS**：把 `withSockJS()` 去掉，前端直接用原生 `new WebSocket('ws://...')`，对比两者差异。
5. **跨域测试**：把 `setAllowedOrigins("*")` 改成具体域名，从另一个域名的页面连接，观察是否被拒。
6. **断线重连**：在前端 `stompClient.connect` 的错误回调里实现自动重连，体会生产环境 WebSocket 的可靠性要求。

---

## 十三、本模块知识点总结（结合实际开发详解）

WebSocket 是前端工程师最熟悉的后端技术之一，但 Spring Boot 的 STOMP + SockJS 封装增加了一些概念。下面把核心知识点放到真实开发场景里讲透。

### 13.1 原生 WebSocket vs STOMP：什么时候用哪个？

**原生 WebSocket（`@ServerEndpoint` 或 `WebSocketHandler`）**：

- 优点：简单直接，前后端都只用原生 API，没有额外协议。
- 缺点：没有路由、没有订阅、没有消息格式约定，多人协作时各写各的协议，容易乱。
- 适用场景：简单的一对一通信、自定义二进制协议、性能敏感场景。

**STOMP over WebSocket（`@EnableWebSocketMessageBroker`）**：

- 优点：有标准的 SUBSCRIBE/SEND 命令、有主题路由、有消息代理，天然支持发布-订阅和点对点。
- 缺点：多一层协议，前端要引 stomp.js 库，消息是文本（JSON）。
- 适用场景：**绝大多数业务场景**——聊天、推送、实时通知、协同编辑。

**实际开发建议**：除非有特殊性能需求，**优先用 STOMP**。它把"谁订阅了什么""消息发给谁"这些复杂逻辑交给框架，你只管 `convertAndSend` 和 `subscribe`。本模块就是 STOMP 用法。

> 💡 前端类比：原生 WebSocket 像手写 TCP socket，STOMP 像 Socket.io——多了房间、命名空间、自动重连等上层能力。

### 13.2 端点（endpoint）、主题（topic）、`@MessageMapping` 三者关系

这是 Spring WebSocket 最容易混淆的三层概念：

| 概念 | 作用 | 配置位置 | 前端对应 |
| --- | --- | --- | --- |
| **端点** | WebSocket 连接入口（握手地址） | `registerStompEndpoints` | `new SockJS(endpoint)` 连接 |
| **主题** | 消息广播频道，后端发、前端订阅 | `configureMessageBroker` 的 `/topic` 前缀 | `stompClient.subscribe(topic, cb)` |
| **`@MessageMapping`** | 处理前端发给后端的消息（入站路由） | 方法注解，默认 `/app` 前缀 | `stompClient.send("/app/xxx", ...)` |

**数据流向：**

- **后端 → 前端（推送）**：后端 `wsTemplate.convertAndSend("/topic/server", data)` → 代理 → 所有订阅 `/topic/server` 的前端。
- **前端 → 后端（上报）**：前端 `stompClient.send("/app/hello", data)` → 匹配 `@MessageMapping("/hello")` 的方法。

本模块只用了第一条（后端→前端），所以没有 `@MessageMapping`。聊天室场景会两条都用。

**常见坑：**

- 把端点路径和主题路径搞混：端点是 `/notification`（连接用），主题是 `/topic/server`（订阅用），两者完全不同。
- 忘了在 `configureMessageBroker` 里 `enableSimpleBroker("/topic")`，导致订阅了但收不到消息——代理没启用，消息无处转发。
- `@MessageMapping` 的路径默认带 `/app` 前缀，前端 send 时要写 `/app/hello` 而不是 `/hello`，否则匹配不上。

### 13.3 `SimpMessagingTemplate`：后端推送的万能工具

这是实际开发中后端推送消息的核心 API，必须熟练掌握：

```java
// 广播：所有订阅 /topic/notice 的客户端都收到
wsTemplate.convertAndSend("/topic/notice", "系统维护通知");

// 点对点：只发给指定用户（需 Spring Security 认证）
wsTemplate.convertAndSendToUser("user123", "/queue/notify", "你有新消息");
```

**实际开发应用场景：**

- **实时通知**：审批流走到某人，`convertAndSendToUser` 推送"你有待办"。
- **数据大盘**：定时推送实时指标到 `/topic/dashboard`，前端大屏订阅刷新。
- **聊天**：用户发消息 → `@MessageMapping` 接收 → `convertAndSendToUser` 转给接收方。

**常见坑：**

- `convertAndSendToUser` 依赖会话的用户身份，如果没集成 Spring Security，"用户"概念不存在，点对点推送会失败。需要配合 `Principal` 或自定义握手拦截器。
- 推送频率过高（如每 100ms 一次）会压垮前端渲染和带宽，要根据业务合理设置间隔。
- 推送大对象时序列化耗时，建议只推增量数据，而非全量。

### 13.4 SockJS：兜底与跨域

`withSockJS()` 做两件事：

1. **降级兜底**：浏览器不支持 WebSocket 时，自动用 XHR 流、长轮询等模拟，保证可用性。
2. **跨域简化**：配合 `setAllowedOrigins` 处理跨域。

**实际开发要不要用 SockJS？**

- 如果确定目标浏览器都支持 WebSocket（现代浏览器基本都支持），可以不用 SockJS，前端直接 `new WebSocket('ws://...')`，更轻量。
- 如果要兼容老浏览器或复杂网络环境（某些代理会切断 WebSocket），用 SockJS 更稳。
- 用了 SockJS，前端必须引 `sockjs.min.js` 并用 `new SockJS(url)`，不能用原生 `new WebSocket`。

**常见坑：**

- `setAllowedOrigins("*")` 在生产环境是安全隐患，允许任意网站连你的 WebSocket。应改成 `setAllowedOrigins("https://yourdomain.com")`。
- SockJS 的端点 URL 是 `http://` 开头（不是 `ws://`），因为它要先 HTTP 握手再升级，前端写错协议会连不上。

### 13.5 消息代理的选择：SimpleBroker vs 外置 Broker

本模块用 `enableSimpleBroker("/topic")`——这是基于内存的简单代理，够用但有局限：

| 维度 | SimpleBroker（内存） | 外置 Broker（RabbitMQ/ActiveMQ） |
| --- | --- | --- |
| 部署 | 零成本，内置 | 要额外部署消息中间件 |
| 持久化 | 不持久，重启丢消息 | 可持久化 |
| 集群 | 单机，多实例间不共享 | 天然支持集群广播 |
| 适用 | 单机小应用 | 分布式、高可用场景 |

**实际开发的集群问题**：如果后端部署 3 台，用户 A 连了机器 1，后端在机器 2 上 `convertAndSend`，机器 1 上的用户 A 收不到——因为 SimpleBroker 是内存级的，不跨实例。解决方法：

1. 用外置 Broker（`enableStompBrokerRelay` 连 RabbitMQ），消息走中间件，所有实例都能收到。
2. 用 Redis Pub/Sub 在实例间转发 WebSocket 消息。
3. 用 Spring Cloud Gateway 做会话亲和（sticky session），让同一用户固定连同一台。

**最佳实践**：单机用 SimpleBroker 够了；一旦上集群，必须换外置 Broker 或加消息转发层，否则推送会"丢"。

### 13.6 WebSocket 的鉴权与安全

WebSocket 连接的鉴权比 HTTP 复杂，因为握手后就是长连接，不能每次消息都带 token。

**实际开发的三种鉴权方式：**

1. **握手时带 token（URL 参数或 Header）**：连接时 `ws://host/endpoint?token=xxx`，后端用 `HandshakeInterceptor` 校验。简单但 token 会进日志。
2. **STOMP CONNECT 帧带 Header**：`stompClient.connect({Authorization: 'Bearer xxx'}, cb)`，后端用 `ChannelInterceptor` 拦截 CONNECT 帧校验。更安全，推荐。
3. **依赖 HTTP 会话**：如果前后端同源且用 Session 认证，WebSocket 握手会自动带上 Cookie，后端直接拿 Session 用户。最简单但限制同源。

**常见坑：**

- 跨域 + token：跨域时浏览器不让加自定义 Header 到 WebSocket 握手，只能放 URL 参数，token 泄露风险增大。生产建议用 SockJS + CONNECT 帧传 token。
- 忘了校验，导致任意人能连 WebSocket 接收敏感数据。WebSocket 不是"连上就能用"，必须鉴权。
- token 过期后 WebSocket 连接不会自动断开，需要在后端定时校验或前端刷新 token 后重连。

### 13.7 断线重连与心跳：生产环境的必修课

本模块的 demo 没有重连机制——断了就断了。但生产环境必须处理：

**断线原因：**

- 网络抖动、切换 WiFi
- 服务器重启
- 代理/防火墙超时断开空闲连接（通常 30-60 秒无数据就断）

**实际开发的应对：**

1. **前端自动重连**：`stompClient.connect` 的错误回调里，用指数退避（1s、2s、4s...）重连，避免雪崩。
2. **心跳保活**：STOMP 协议自带心跳（`stompClient.heartbeat.incoming`/`outgoing`），定期发空帧保持连接活跃，防止被防火墙掐断。Spring 后端也可配 `setHeartbeatTime`。
3. **后端感知断线**：实现 `SessionDisconnectEvent` 监听，用户断开时清理在线状态。

**最佳实践**：把 WebSocket 客户端封装成带自动重连、心跳、订阅恢复的工具类，不要在每个页面手写连接逻辑。前端有现成库如 `@stomp/stompjs` 封装好了这些。

> 💡 前端类比：这和你封装 axios 拦截器处理 401 刷新 token、请求重试是一个道理——网络不可靠，客户端必须自愈。

---

> 📌 **学习建议**：WebSocket 是前端工程师转后端后"最顺手"的技术——你在前端写过 `new WebSocket`、用过 Socket.io，后端这边只是换成了 `SimpMessagingTemplate` 和 STOMP 主题。重点理解 Spring 的三层抽象（端点连接、主题订阅、`@MessageMapping` 入站），以及"SimpleBroker 是单机内存、集群要换外置 Broker"这个生产关键点。建议先把这个 demo 跑起来，然后做练习 2（实现前端发消息给后端），把双向通信跑通，你对 WebSocket 的理解就完整了。
