# 34 - SocketIO 实时通信

> 对应项目模块：`demo-websocket-socketio`
> 前置知识：已学完前序模块，了解 Spring Boot 启动类、配置注入、`@RestController`、AOP 基本用法
> 学习目标：理解 WebSocket 与 SocketIO 的关系，掌握用 `netty-socketio` 在 Spring Boot 中搭建实时双向通信服务，实现连接鉴权、私聊、群聊、广播、ACK 应答。

---

## 一、本模块要解决什么问题？

传统 HTTP 是"请求-响应"模型：客户端问一句，服务器答一句，**服务器无法主动给客户端推消息**。但很多场景需要服务器主动推送：

- 聊天室：A 发消息，B 的屏幕要立刻显示
- 实时通知：后台审核通过，前端要弹个提示
- 在线协作：多人编辑同一文档，变更要同步
- 股票/比赛比分：数据实时刷新

前端同学最熟悉的解法是 **WebSocket**——一个在单个 TCP 连接上进行全双工通信的协议。浏览器原生支持 `new WebSocket(url)`，但原生 WebSocket 有几个痛点：

1. **不支持自动重连**：网络抖动断开后不会自动恢复，要自己写重连逻辑。
2. **不支持事件分发**：原生只有 `onmessage` 一个回调，所有消息挤在一起，要自己用 JSON 字段区分"这是聊天消息还是系统通知"。
3. **不支持房间/分组**：要做群聊，得自己维护"谁在哪个群"的映射。
4. **不支持 ACK 应答**：发出去不知道对方收没收到。
5. **老浏览器兼容性**：部分环境不支持 WebSocket。

**Socket.IO** 就是为解决这些痛点而生——它在 WebSocket 之上封装了一层，提供：事件机制（`socket.emit('chat', data)` / `socket.on('chat', cb)`）、自动重连、房间（room）、命名空间（namespace）、ACK 应答、降级兼容。本模块用的 `netty-socketio` 是 Socket.IO 协议的 Java 服务端实现，前端可以直接用官方 `socket.io.js` 客户端连接。

> 💡 前端类比：原生 WebSocket 像 `fetch`——基础能力够用但要自己包一层；Socket.IO 像 `axios`——封装了拦截器、重试、取消等工程能力。前端项目里 `import io from 'socket.io-client'` 连的就是这种服务端。

本模块最终实现一个聊天室：多浏览器打开页面，能私聊、群聊、广播，连接时带 token 鉴权。

---

## 二、先看项目结构

```
demo-websocket-socketio/
├── pom.xml
└── src/main/
    ├── java/com/xkcoding/websocket/socketio/
    │   ├── SpringBootDemoWebsocketSocketioApplication.java  # 启动类
    │   ├── config/
    │   │   ├── ServerConfig.java        # SocketIOServer + 鉴权 + 注解扫描
    │   │   ├── WsConfig.java            # 配置属性（host、port）
    │   │   ├── Event.java               # 事件名常量
    │   │   └── DbTemplate.java         # 模拟数据库（userId↔sessionId）
    │   ├── handler/
    │   │   └── MessageEventHandler.java # 核心：连接/断开/消息事件处理
    │   ├── init/
    │   │   └── ServerRunner.java        # 启动时开启 SocketIOServer
    │   ├── controller/
    │   │   └── MessageController.java   # HTTP 接口触发广播
    │   └── payload/                     # 消息载体 DTO
    │       ├── BroadcastMessageRequest.java
    │       ├── GroupMessageRequest.java
    │       ├── JoinRequest.java
    │       └── SingleMessageRequest.java
    └── resources/
        ├── application.yml
        └── static/                       # 前端测试页面 + socket.io.js
            ├── index.html
            └── js/...
```

注意一个关键点：本模块有**两个端口**。`application.yml` 里 `server.port=8080` 是 Spring Boot 内嵌 Tomcat（HTTP 接口 + 静态页面），`ws.server.port=8081` 是 netty-socketio 的 WebSocket 端口。前端页面从 8080 加载，然后连到 8081 建立 WebSocket。

---

## 三、逐行拆解 pom.xml

```xml
<properties>
    <netty-socketio.version>1.7.16</netty-socketio.version>
</properties>

<dependencies>
    <!-- 1. SocketIO 服务端核心 -->
    <dependency>
        <groupId>com.corundumstudio.socketio</groupId>
        <artifactId>netty-socketio</artifactId>
        <version>${netty-socketio.version}</version>
    </dependency>

    <!-- 2. Spring Boot Web -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-web</artifactId>
    </dependency>

    <!-- 3. 配置元数据处理器 -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-configuration-processor</artifactId>
        <optional>true</optional>
    </dependency>

    <!-- 4. 测试 / Hutool / Lombok -->
    ...
</dependencies>
```

- `netty-socketio`：这是关键依赖。它基于 Netty（高性能 NIO 框架）实现了 Socket.IO 协议的服务端。注意它**不是 Spring Boot 官方 starter**，没有自动配置，所以后面要手动写 `@Bean` 把 `SocketIOServer` 注册进容器。版本 1.7.16 对应 Socket.IO 1.x/2.x 协议，前端 `socket.io.js` 版本要匹配，否则握手失败。
- `spring-boot-starter-web`：提供 Tomcat（HTTP）和静态资源服务。
- `spring-boot-configuration-processor`：让 `WsConfig` 的配置项在 yml 里有提示。

> 💡 前端类比：`netty-socketio` 像一个独立的 Node.js WebSocket 服务（如 `socket.io` 的 server 包），它自带一个 Netty 服务器，不依赖 Tomcat。所以它和 Spring MVC 是两套独立的服务，各听各的端口。

---

## 四、配置文件 application.yml

```yaml
server:
  port: 8080
  servlet:
    context-path: /demo
ws:
  server:
    port: 8081
    host: localhost
```

- `server.port=8080`：Tomcat 端口，HTTP 接口（`/demo/send/broadcast`）和静态页面（`/demo/index.html`）走这里。
- `ws.server.port=8081`：netty-socketio 监听端口，WebSocket 连接走这里。
- `ws.server.host=localhost`：绑定主机。生产环境一般设为 `0.0.0.0` 监听所有网卡。

`ws.server` 这个前缀对应下面的 `WsConfig`。

---

## 五、配置属性类 WsConfig

```java
@ConfigurationProperties(prefix = "ws.server")
@Data
public class WsConfig {
    private Integer port;
    private String host;
}
```

把 `ws.server.port` 和 `ws.server.host` 绑定到对象。这是 `@ConfigurationProperties` 的标准用法（详见 `02-读取配置文件_Properties`），把零散配置聚合成一个类型安全的对象，方便注入。

---

## 六、核心：ServerConfig —— 创建 SocketIOServer

```java
@Configuration
@EnableConfigurationProperties({WsConfig.class})
public class ServerConfig {

    @Bean
    public SocketIOServer server(WsConfig wsConfig) {
        com.corundumstudio.socketio.Configuration config = new com.corundumstudio.socketio.Configuration();
        config.setHostname(wsConfig.getHost());
        config.setPort(wsConfig.getPort());

        // 这个 listener 可以用来进行身份验证
        config.setAuthorizationListener(data -> {
            String token = data.getSingleUrlParam("token");
            // 校验 token 合法性，实际业务参考 rbac-security 的 JwtUtil
            return StrUtil.isNotBlank(token);
        });

        return new SocketIOServer(config);
    }

    @Bean
    public SpringAnnotationScanner springAnnotationScanner(SocketIOServer server) {
        return new SpringAnnotationScanner(server);
    }
}
```

### 6.1 创建 SocketIOServer

`SocketIOServer` 是 netty-socketio 的核心对象，相当于一个独立的 WebSocket 服务器。这里用 `@Bean` 把它注册成 Spring Bean，这样到处都能注入。

创建它需要传一个 `Configuration`，设置主机、端口。

### 6.2 鉴权监听器 AuthorizationListener

```java
config.setAuthorizationListener(data -> {
    String token = data.getSingleUrlParam("token");
    return StrUtil.isNotBlank(token);
});
```

这是 Socket.IO 握手阶段的鉴权钩子。前端连接时 URL 带参数 `http://127.0.0.1:8081?token=xxx`，`data.getSingleUrlParam("token")` 取出 token，返回 `true` 允许连接，返回 `false` 触发 `CONNECT_ERROR` 事件拒绝连接。

本 demo 只判断 token 非空，**真实业务**应该校验 JWT 的有效性（参考 `27-权限控制_RBAC_Security` 的 JwtUtil）。

> 💡 前端类比：这像 axios 的请求拦截器，在连接建立前做一道鉴权。Socket.IO 的鉴权放在握手阶段，比每次消息都校验更高效。

### 6.3 SpringAnnotationScanner

```java
@Bean
public SpringAnnotationScanner springAnnotationScanner(SocketIOServer server) {
    return new SpringAnnotationScanner(server);
}
```

netty-socketio 的事件注解（`@OnConnect`、`@OnEvent`）默认不被 Spring 识别。`SpringAnnotationScanner` 是一个扫描器，让 Spring 容器能管理这些注解标记的方法，使 `MessageEventHandler` 里的 `@OnEvent` 能被 SocketIOServer 正确回调。**这一步必须加，否则事件不触发。**

---

## 七、事件常量 Event

```java
public interface Event {
    String CHAT = "chat";        // 私聊
    String BROADCAST = "broadcast";  // 广播
    String GROUP = "group";      // 群聊
    String JOIN = "join";        // 加入群聊
}
```

用接口定义事件名常量，避免前后端字符串硬编码不一致。前端 `socket.emit('chat', ...)` 和后端 `@OnEvent(Event.CHAT)` 通过这个常量对齐。

> 💡 前端类比：这像前端项目里用 `export const EventType = { CHAT: 'chat' }` 定义事件常量，避免魔法字符串。实际项目建议前后端共享一份事件定义（如生成 TS 类型）。

---

## 八、模拟数据库 DbTemplate

```java
@Component
public class DbTemplate {
    public static final ConcurrentHashMap<String, UUID> DB = new ConcurrentHashMap<>();

    public List<UUID> findAll() { ... }
    public Optional<UUID> findByUserId(String userId) { ... }
    public void save(String userId, UUID sessionId) { ... }
    public void deleteByUserId(String userId) { ... }
}
```

用 `ConcurrentHashMap` 模拟数据库，存 `userId ↔ sessionId` 的映射。私聊时根据目标 userId 查到 sessionId，再通过 sessionId 找到对应的 `SocketIOClient` 推送消息。

**为什么需要这个映射？** SocketIOServer 只认 `sessionId`（连接的唯一 ID），但业务层只知道"给 userId=123 的用户发消息"，所以要维护两者的映射。

> ⚠️ 本 demo 用内存 Map 模拟，**生产环境**必须用 Redis 集中存储，原因见第十章。`ConcurrentHashMap` 在单机没问题，多机部署时各机器的 Map 不共享，私聊会找不到跨机器的在线用户。

---

## 九、消息载体 payload

四个 DTO，都是 `@Data`（Lombok 生成 getter/setter）：

| 类 | 字段 | 用途 |
| --- | --- | --- |
| `JoinRequest` | userId, groupId | 加群请求 |
| `SingleMessageRequest` | fromUid, toUid, message | 私聊消息 |
| `GroupMessageRequest` | fromUid, groupId, message | 群消息 |
| `BroadcastMessageRequest` | message | 广播消息 |

Socket.IO 收发消息时，这些对象会被自动 JSON 序列化/反序列化。前端 `socket.emit('chat', {fromUid, toUid, message})` 发出的 JSON，后端 `@OnEvent` 方法的 `SingleMessageRequest data` 参数自动绑定。

> 💡 前端类比：这像 TypeScript 的接口定义，前后端约定好消息结构。netty-socketio 内部用 Jackson 做序列化，和 REST 接口的 `@RequestBody` 是同一套机制。

---

## 十、核心：MessageEventHandler —— 事件处理

这是整个模块的心脏，处理所有 WebSocket 事件。

### 10.1 连接事件 @OnConnect

```java
@OnConnect
public void onConnect(SocketIOClient client) {
    String token = client.getHandshakeData().getSingleUrlParam("token");
    String userId = client.getHandshakeData().getSingleUrlParam("token"); // 模拟 userId=token
    UUID sessionId = client.getSessionId();
    dbTemplate.save(userId, sessionId);
    log.info("连接成功,【token】= {},【sessionId】= {}", token, sessionId);
}
```

- `@OnConnect`：客户端连接成功时触发（在鉴权通过后）。
- `client.getHandshakeData()`：握手数据，能取到 URL 参数、请求头等。
- `client.getSessionId()`：本次连接的唯一 ID（UUID）。
- 把 `userId ↔ sessionId` 存进 DbTemplate，供后续私聊查找。

### 10.2 断开事件 @OnDisconnect

```java
@OnDisconnect
public void onDisconnect(SocketIOClient client) {
    String userId = client.getHandshakeData().getSingleUrlParam("token");
    dbTemplate.deleteByUserId(userId);
    client.disconnect();
}
```

客户端断开时清理映射。**这一步很重要**：不清理会导致 DbTemplate 里残留失效 sessionId，私聊时按失效 ID 找客户端返回 null 报错。

### 10.3 加群事件 @OnEvent(JOIN)

```java
@OnEvent(value = Event.JOIN)
public void onJoinEvent(SocketIOClient client, AckRequest request, JoinRequest data) {
    client.joinRoom(data.getGroupId());
    server.getRoomOperations(data.getGroupId()).sendEvent(Event.JOIN, data);
}
```

- `@OnEvent(Event.JOIN)`：监听前端 `socket.emit('join', ...)` 发的事件。
- `client.joinRoom(groupId)`：把该客户端加入名为 `groupId` 的房间。Socket.IO 的 room 是服务端分组机制，`getRoomOperations(room).sendEvent(...)` 能向房间内所有客户端推送。
- 第二行向全房间广播"有人加入了"。

> 💡 前端类比：room 像 Socket.IO 的"频道"或 Redis Pub/Sub 的 channel。`joinRoom` 相当于 `subscribe`，`sendEvent` 相当于 `publish`。一个客户端可以同时在多个房间。

### 10.4 私聊事件 @OnEvent(CHAT)

```java
@OnEvent(value = Event.CHAT)
public void onChatEvent(SocketIOClient client, AckRequest request, SingleMessageRequest data) {
    Optional<UUID> toUser = dbTemplate.findByUserId(data.getToUid());
    if (toUser.isPresent()) {
        sendToSingle(toUser.get(), data);
        request.sendAckData(Dict.create().set("flag", true).set("message", "发送成功"));
    } else {
        request.sendAckData(Dict.create().set("flag", false).set("message", "发送失败，对方不在线"));
    }
}
```

- 根据 `toUid` 查目标用户的 sessionId。
- 在线就调 `sendToSingle` 推送，离线就回失败。
- `request.sendAckData(...)`：**ACK 应答**。前端 `socket.emit('chat', data, callback)` 的第三个参数是回调，服务端 `request.sendAckData(返回值)` 触发它。这让前端能立刻知道"发送成功/失败"。

> 💡 前端类比：ACK 像 HTTP 的响应，但复用在同一条 WebSocket 连接上。前端写法：
> ```js
> socket.emit('chat', msg, (ack) => { console.log(ack.flag ? '成功' : '失败') })
> ```

### 10.5 群聊事件 @OnEvent(GROUP)

```java
@OnEvent(value = Event.GROUP)
public void onGroupEvent(SocketIOClient client, AckRequest request, GroupMessageRequest data) {
    Collection<SocketIOClient> clients = server.getRoomOperations(data.getGroupId()).getClients();
    boolean inGroup = false;
    for (SocketIOClient socketIOClient : clients) {
        if (ObjectUtil.equal(socketIOClient.getSessionId(), client.getSessionId())) {
            inGroup = true; break;
        }
    }
    if (inGroup) {
        sendToGroup(data);
    } else {
        request.sendAckData("请先加群！");
    }
}
```

先校验发送者是否在群里（防止没加群就发消息），在群里才向全群推送。`sendToGroup` 调 `server.getRoomOperations(groupId).sendEvent(Event.GROUP, data)`，向房间所有成员推群消息。

### 10.6 三个推送方法

```java
// 私聊：按 sessionId 定向推送
public void sendToSingle(UUID sessionId, SingleMessageRequest message) {
    server.getClient(sessionId).sendEvent(Event.CHAT, message);
}

// 广播：遍历所有在线用户推送
public void sendToBroadcast(BroadcastMessageRequest message) {
    for (UUID clientId : dbTemplate.findAll()) {
        if (server.getClient(clientId) == null) continue;
        server.getClient(clientId).sendEvent(Event.BROADCAST, message);
    }
}

// 群聊：向房间推送
public void sendToGroup(GroupMessageRequest message) {
    server.getRoomOperations(message.getGroupId()).sendEvent(Event.GROUP, message);
}
```

三种推送模式对照：

| 模式 | API | 场景 |
| --- | --- | --- |
| 私聊（定向） | `server.getClient(sessionId).sendEvent(...)` | 一对一 |
| 群聊（房间） | `server.getRoomOperations(room).sendEvent(...)` | 一对多（同群） |
| 广播（全员） | 遍历所有 client 逐个 sendEvent | 一对全部 |

---

## 十一、ServerRunner —— 启动 SocketIOServer

```java
@Component
@Slf4j
public class ServerRunner implements CommandLineRunner {
    @Autowired
    private SocketIOServer server;

    @Override
    public void run(String... args) {
        server.start();
        log.info("websocket 服务器启动成功。。。");
    }
}
```

`SocketIOServer` 虽然注册成了 Bean，但**不会自动启动**。`CommandLineRunner` 是 Spring Boot 的启动回调，在容器就绪后执行 `server.start()` 开启 Netty 监听。

> 💡 前端类比：`CommandLineRunner` 像 React 的 `useEffect(() => { 启动逻辑 }, [])`，在应用启动完成后执行一次。也可以用 `@PostConstruct` 注解在 Bean 初始化后启动，但 `CommandLineRunner` 能确保所有 Bean 都就绪。

---

## 十二、MessageController —— HTTP 触发广播

```java
@RestController
@RequestMapping("/send")
public class MessageController {
    @Autowired
    private MessageEventHandler messageHandler;

    @PostMapping("/broadcast")
    public Dict broadcast(@RequestBody BroadcastMessageRequest message) {
        if (isBlank(message)) {
            return Dict.create().set("flag", false).set("code", 400).set("message", "参数为空");
        }
        messageHandler.sendToBroadcast(message);
        return Dict.create().set("flag", true).set("code", 200).set("message", "发送成功");
    }
}
```

这个 Controller 演示了一个重要模式：**用 HTTP 接口触发 WebSocket 推送**。运维或后台系统调 `POST /demo/send/broadcast`，服务端就向所有在线 WebSocket 客户端广播一条消息。

这体现了 WebSocket 的另一个用法——不只是"用户之间聊天"，后台业务系统也能主动给前端推消息（如审批通知、告警）。`isBlank` 用反射判断 DTO 是否全空字段，是个工具方法。

---

## 十三、前端页面 index.html（关键片段）

```js
const token = 'user' + Math.floor((Math.random() * 1000) + 1);
const url = `http://127.0.0.1:8081?token=${token}`;
const socket = io.connect(url);

socket.on('connect', () => { /* 连接成功 */ });
socket.on('chat', (data) => { /* 收到私聊 */ });
socket.on('group', (data) => { /* 收到群聊 */ });
socket.on('broadcast', (data) => { /* 收到广播 */ });

// 发私聊（带 ACK 回调）
socket.emit('chat', { fromUid, toUid, message }, (ack) => { ... });
// 加群
socket.emit('join', { userId, groupId });
// 发群聊
socket.emit('group', { fromUid, groupId, message }, (ack) => { ... });
```

前端用 `socket.io.js` 客户端，`io.connect(url)` 连接 8081 端口，`socket.on` 监听事件，`socket.emit` 发送事件。注意 `emit` 的第三个参数是 ACK 回调，对应后端 `request.sendAckData`。

广播走 HTTP：`axios.post('/demo/send/broadcast', { message })`，由后端 Controller 触发 `sendToBroadcast`。

---

## 十四、运行与验证

1. 启动 `SpringBootDemoWebsocketSocketioApplication`。
2. 用两个不同浏览器（或一个浏览器两个标签）访问 `http://localhost:8080/demo/index.html`。
3. 两个页面会自动用随机 token 连上 WebSocket。
4. 在 A 页面填 B 的 token 和消息，点"私聊"，B 页面立刻显示悄悄话。
5. 两个页面都点"加入群聊"，然后点"群聊"，双方都能收到群消息。
6. 点"广播消息"（走 HTTP），所有页面收到红色广播。

---

## 十五、动手练习

1. **加鉴权**：把 `AuthorizationListener` 改成校验真实 JWT，token 非法时拒绝连接，前端观察 `connect_error` 事件。
2. **加离线消息**：私聊时如果对方不在线，把消息暂存（内存或 Redis），对方上线时 `@OnConnect` 里检查并补发。
3. **用 Redis 替换 DbTemplate**：把 userId↔sessionId 存 Redis，体会为什么单机 Map 在集群下不行。
4. **加命名空间**：用 `config` 配置 namespace，把"聊天"和"系统通知"分到不同命名空间，体会 namespace 和 room 的区别。
5. **改造前端**：把 jQuery 页面换成 Vue/React，用 `socket.io-client` npm 包连接，体验现代前端如何对接。
6. **加心跳/超时**：配置 `config.setPingInterval` / `setPingTimeout`，断网后观察自动重连行为。

---

## 十六、本模块知识点总结（结合实际开发详解）

实时通信是聊天、通知、协作类应用的核心能力。下面把关键知识点放到真实开发场景里讲透。

### 16.1 HTTP vs WebSocket vs Socket.IO：怎么选？

**三者关系：**

| 技术 | 通信方向 | 特点 | 适用场景 |
| --- | --- | --- | --- |
| HTTP 轮询 | 客户端→服务端 | 定时发请求问"有新消息吗"，浪费资源 | 兼容性兜底，几乎不用了 |
| SSE（Server-Sent Events） | 服务端→客户端单向 | 基于 HTTP，服务器能推，客户端不能发 | 单向通知（股票行情、告警） |
| WebSocket | 双向 | 全双工，协议升级 | 需要双向实时通信 |
| Socket.IO | 双向 | WebSocket 超集，有事件/房间/重连/ACK | 聊天室、多人协作 |

**实际开发选择：**

- **纯推送（服务器→前端）**：用 SSE 更轻量，Spring Boot 原生支持（`SseEmitter`），不用引第三方库。
- **双向实时**：用 WebSocket。简单场景用 Spring Boot 原生 `spring-boot-starter-websocket`（见 `33-WebSocket实时通信`）；需要房间、ACK、重连等工程能力，用 Socket.IO。
- **聊天/协作**：优先 Socket.IO，省去自己造轮子。

**常见坑：** 以为 HTTP 轮询简单就用了，用户一多服务器就被轮询请求打爆。实时场景一定要用 WebSocket/SSE，别用轮询。

> 💡 前端类比：HTTP 轮询像 `setInterval(() => fetch('/msg'), 1000)`——简单但低效；WebSocket 像建了一条管道，数据随时双向流；Socket.IO 像管道+智能调度（断线重连、事件路由）。

### 16.2 netty-socketio 与 Spring Boot 的整合模式

本模块体现了一个典型模式：**把一个独立的服务器（netty-socketio）嵌入 Spring Boot**，两者共享 Spring 容器但各听各的端口。

**整合三步走：**

1. `@Bean` 创建 `SocketIOServer`（配置端口、鉴权）。
2. `SpringAnnotationScanner` 让 Spring 管理事件注解。
3. `CommandLineRunner` 在启动后 `server.start()`。

**实际开发要点：**

- **端口规划**：HTTP（8080）和 WebSocket（8081）分离，避免与 Tomcat 冲突。生产环境一般用 Nginx 反向代理，按路径分流（`/ws` 转发到 8081，其余到 8080），对外只暴露一个端口。
- **生命周期管理**：`server.start()` 在容器就绪后调，关闭时要 `server.stop()`（可用 `@PreDestroy`），否则进程退不干净。
- **Bean 注入**：`MessageEventHandler` 注入 `SocketIOServer`，事件处理方法里能用 Spring 的其他 Bean（Service、Redis 等），实现"WebSocket 事件里调业务逻辑"。

**常见坑：**

- 忘了 `SpringAnnotationScanner`：事件方法不触发，排查半天。
- 忘了 `server.start()`：端口没监听，前端连不上。
- 在 `@PostConstruct` 里 `start()`：此时其他 Bean 可能没就绪，推荐用 `CommandLineRunner`。

### 16.3 鉴权：连接握手阶段校验

本模块用 `AuthorizationListener` 在握手时校验 token。

**实际开发最佳实践：**

1. **用 JWT**：前端连接时 URL 带 `?token=<jwt>`，后端解析校验签名和过期。参考 `27-权限控制_RBAC_Security`。
2. **鉴权放握手阶段**：比每条消息都校验高效，一次连接只校验一次。
3. **拒绝时给前端明确事件**：返回 false 触发 `connect_error`，前端监听它提示"登录失效"。

**常见坑：**

- token 放 URL 参数有泄露风险（日志、Referer），敏感场景可用握手时的自定义 Header（netty-socketio 支持 `setAuthorizationListener` 取 Header）。
- 只在连接时校验，token 过期后连接不会自动断。需要配合"token 续期或主动踢人"机制。

### 16.4 房间（Room）与命名空间（Namespace）

Socket.IO 两个分组机制：

| 机制 | 粒度 | 场景 |
| --- | --- | --- |
| Room | 连接分组 | 群聊、按主题分组 |
| Namespace | 连接隔离 | 多业务模块（聊天/通知各自独立） |

**实际开发：**

- **群聊用 Room**：用户加群 `client.joinRoom(groupId)`，发群消息 `getRoomOperations(groupId).sendEvent()`。
- **多业务用 Namespace**：如 `/chat` 和 `/notify` 两个命名空间，互不干扰，各自一套事件。
- **踢人**：`client.leaveRoom(groupId)` 或 `server.getRoomOperations(room).getClients()` 遍历踢。

**常见坑：** 以为 room 能跨服务器——单机 room 没问题，多机部署时 room 信息不共享，需要用 Redis adapter（`RedisBroadcastHandler`）把 room 消息广播到所有节点。

### 16.5 ACK 应答：可靠消息的保障

`request.sendAckData(...)` + 前端 `emit` 第三参数回调，实现了"请求-响应"语义。

**实际开发：**

- **需要确认的场景用 ACK**：如"消息是否送达""加群是否成功"。前端回调里处理结果。
- **不需要确认的场景直接 emit**：如普通群消息广播，发了就发了。

**常见坑：** ACK 只能回一次，且必须在事件处理方法里同步或异步调一次。重复调或漏调都会让前端回调卡住。

### 16.6 在线状态管理：单机 vs 集群

本模块用 `DbTemplate`（内存 Map）存 userId↔sessionId。

**单机够用，集群致命**：多机部署时，用户 A 连到节点1，用户 B 连到节点2，节点1 的 Map 里没有 B，私聊找不到 B。

**生产方案：**

1. **Redis 集中存储**：所有节点把 userId↔sessionId↔节点 写 Redis，私聊时查 Redis 知道用户在哪个节点。
2. **Redis adapter**：netty-socketio 配 `RedisBroadcastHandler`，消息自动跨节点广播，room 和广播在集群下生效。
3. **消息队列**：用 Redis Pub/Sub 或 RabbitMQ 做节点间消息分发。

**常见坑：** 单机开发没问题，一上集群私聊/群聊就丢消息。一定要在架构设计阶段就考虑集群方案。

### 16.7 离线消息与消息可靠性

本模块私聊时对方不在线直接回"发送失败"，消息丢失。真实聊天系统要保证消息不丢。

**生产方案：**

- **离线消息存储**：对方不在线时，消息存数据库/Redis，对方上线后 `@OnConnect` 拉取补发。
- **消息确认机制**：接收方收到后回 ACK，发送方未收到 ACK 则重发。
- **消息顺序**：单聊用 sessionId 做队列保证顺序；群聊用房间内序列号。

**常见坑：** 以为 WebSocket 可靠传输就不丢消息——网络抖动、客户端崩溃都会丢。关键业务要自己加应用层确认和持久化。

---

> 📌 **学习建议**：作为前端工程师，你对 Socket.IO 客户端（`socket.io-client`）应该不陌生，本模块就是它的服务端 counterpart。学习时重点理解三件事：①WebSocket 解决了 HTTP 不能主动推送的问题；②Socket.IO 在 WebSocket 上加了事件/房间/重连/ACK 等工程能力；③服务端整合的关键是"创建 Server→扫描注解→启动监听"三步。做实时功能时，先想清楚是"纯推送"（用 SSE）还是"双向"（用 WebSocket/Socket.IO），再想清楚"单机够不够"（集群要用 Redis adapter），能避免后期大改。
