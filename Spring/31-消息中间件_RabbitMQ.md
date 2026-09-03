# 31 - Spring Boot 集成消息中间件 RabbitMQ

> 对应项目模块：`demo-mq-rabbitmq`
> 前置知识：已学完前面 HelloWorld、Properties、Actuator 等基础模块，了解启动类、配置文件、Bean 注入基本用法
> 学习目标：理解消息队列解决什么问题，掌握 RabbitMQ 的核心模型（Exchange/Queue/Binding），能用 Spring Boot 实现直接、分列、主题、延迟四种消息模式。

---

## 一、本模块要解决什么问题？

### 1.1 为什么需要消息队列？

先想一个场景：用户下单后，系统要做一堆事——扣库存、生成订单、发短信通知、送积分、推数据给风控……如果这些全在"下单接口"里同步做完，用户要等好几秒才返回，体验很差；而且其中任何一步（比如短信网关）卡住，整个下单就失败。

**消息队列（Message Queue，MQ）就是解决这类问题的中间件**。它的核心思路是"异步解耦"：

- 下单接口只做最核心的事（扣库存、建订单），然后往 MQ 里丢一条消息"用户下单了"就立刻返回。
- 短信、积分、风控这些下游服务，各自去 MQ 上"订阅"这条消息，慢慢处理，互不阻塞。

> 💡 前端类比：这就像前端的 Event Bus / Pub-Sub 模式。组件 A 触发一个事件 `emit('order-created', data)` 就继续干活，组件 B、C 监听这个事件各自处理。区别是前端的 Event Bus 在同一进程内，而 MQ 是**跨进程、跨服务**的——生产者和消费者甚至可以部署在不同机器上。

### 1.2 消息队列的三大核心价值

| 价值 | 说明 | 本模块体现 |
| --- | --- | --- |
| **异步** | 耗时操作丢给 MQ，主流程立刻返回 | 延迟队列演示 |
| **解耦** | 生产者不用知道有几个消费者，互不影响 | 分列/主题模式演示 |
| **削峰** | 突发流量先堆积在 MQ，消费者按自己节奏处理 | （生产场景，demo 未直接演示） |

### 1.3 为什么是 RabbitMQ？

RabbitMQ 是基于 AMQP（高级消息队列协议）的开源消息中间件，特点是**路由能力强、延迟低、生态成熟**。它用 Erlang 编写，天生适合高并发。本模块演示它的四种经典消息模式。

---

## 二、先搞懂 RabbitMQ 的核心模型

在写代码前，必须先理解 RabbitMQ 的"三件套"，否则代码看不懂。

### 2.1 生产者 → 交换器 → 队列 → 消费者

```
生产者 ──发消息──▶ 交换器(Exchange) ──按规则路由──▶ 队列(Queue) ──取消息──▶ 消费者
```

- **Producer（生产者）**：发消息的一方。
- **Exchange（交换器）**：消息的"中转站"。生产者不直接把消息塞进队列，而是先发给交换器，由交换器按规则路由到队列。
- **Queue（队列）**：真正存消息的地方，先进先出（FIFO）。
- **Binding（绑定）**：交换器和队列之间的"路由规则"。
- **Consumer（消费者）**：从队列取消息处理的一方。

> 💡 前端类比：交换器像 Express 的路由层 `app.post('/webhook', handler)`，队列像处理任务的 Worker。生产者发请求到路由层，路由层按路径规则分发到不同的 Worker 处理。

### 2.2 四种交换器类型（本模块全部演示）

| 类型 | 路由规则 | 本模块对应 |
| --- | --- | --- |
| **Direct（直接）** | 按 RoutingKey 精确匹配 | `DIRECT_MODE_QUEUE_ONE` |
| **Fanout（分列）** | 广播给所有绑定的队列，不看 Key | `FANOUT_MODE_QUEUE` |
| **Topic（主题）** | 按 RoutingKey 通配符模式匹配 | `TOPIC_MODE_QUEUE` |
| **x-delayed-message（延迟）** | 消息延迟指定时间后才投递 | `DELAY_MODE_QUEUE` |

**Topic 通配符规则**（重点，代码注释里反复出现）：

- RoutingKey 用 `.` 分隔，如 `user.email`、`user.aaa.email`
- `*` 匹配**一个**单词：`user.*` 能匹配 `user.email`，不能匹配 `user.aaa.email`
- `#` 匹配**一个或多个**单词：`user.#` 能匹配 `user.email`，也能匹配 `user.aaa.email`

---

## 三、项目结构

```
demo-mq-rabbitmq/
├── pom.xml
└── src/main/
    ├── java/com/xkcoding/mq/rabbitmq/
    │   ├── SpringBootDemoMqRabbitmqApplication.java   # 启动类
    │   ├── config/
    │   │   └── RabbitMqConfig.java                    # 核心：声明队列、交换器、绑定
    │   ├── constants/
    │   │   └── RabbitConsts.java                      # 队列/交换器名称常量
    │   ├── handler/                                   # 消费者：4 个消息处理器
    │   │   ├── DirectQueueOneHandler.java
    │   │   ├── QueueTwoHandler.java
    │   │   ├── QueueThreeHandler.java
    │   │   └── DelayQueueHandler.java
    │   └── message/
    │       └── MessageStruct.java                     # 消息体（传输对象）
    └── resources/
        └── application.yml                            # RabbitMQ 连接配置
```

注意分层：`config` 放配置类、`constants` 放常量、`handler` 放消费者、`message` 放消息体。这是消息队列项目的标准结构。

---

## 四、逐行拆解 pom.xml

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-amqp</artifactId>
</dependency>
```

核心就这一个依赖：`spring-boot-starter-amqp`。AMQP 是高级消息队列协议，Spring 用它作为所有符合 AMQP 协议的 MQ（主要是 RabbitMQ）的整合入口。

**这个 Starter 自动引入了什么？**

- `spring-rabbit`：Spring 对 RabbitMQ 的封装（`RabbitTemplate`、`@RabbitListener` 等）
- `spring-amqp`：Spring 对 AMQP 协议的抽象
- `amqp-client`：RabbitMQ 官方 Java 客户端
- 自动配置：`RabbitAutoConfiguration` 会根据 `application.yml` 里的 `spring.rabbitmq.*` 自动创建 `CachingConnectionFactory`、`RabbitTemplate` 等 Bean

其他依赖：`spring-boot-starter-web`（提供 Web 环境）、`lombok`（简化样板代码）、`hutool-all`（JSON 工具）、`guava`（`Maps.newHashMap()`）。

> 💡 前端类比：引 `spring-boot-starter-amqp` 就像前端 `npm install amqplib`，但 Spring 的 Starter 还额外帮你把连接、模板、自动配置全做好了，你注入 `RabbitTemplate` 就能用。

---

## 五、逐行拆解配置文件 application.yml

```yaml
server:
  port: 8080
  servlet:
    context-path: /demo
spring:
  rabbitmq:
    host: localhost          # RabbitMQ 服务器地址
    port: 5672               # AMQP 协议端口（注意不是 15672）
    username: guest          # 用户名
    password: guest           # 密码
    virtual-host: /          # 虚拟主机（逻辑隔离，类似 namespace）
    listener:                 # 消费者监听器配置
      simple:
        acknowledge-mode: manual   # 简单容器手动 ACK
      direct:
        acknowledge-mode: manual   # 直接容器手动 ACK
```

### 5.1 连接配置

- `host`/`port`：RabbitMQ 服务地址。**注意端口**：`5672` 是 AMQP 通信端口（程序用），`15672` 是管理界面端口（浏览器用）。新手常搞混。
- `guest/guest`：RabbitMQ 默认账号，**仅限 localhost 连接**。生产环境必须改密码，且 guest 不允许远程登录。
- `virtual-host`：虚拟主机，用于多租户隔离。不同 vhost 下的队列/交换器互不可见。

### 5.2 ACK 模式（关键概念）

`acknowledge-mode` 决定消息"消费成功后怎么告诉 MQ"：

| 模式 | 行为 | 适用场景 |
| --- | --- | --- |
| `auto` | 消费者方法正常返回就自动 ACK；抛异常就 NACK | 简单场景 |
| `manual` | 必须在代码里手动调 `channel.basicAck()` 确认 | 需要精细控制（重试、拒绝） |
| `none` | 不确认，消息一直留在队列 | 很少用 |

本模块用 `manual`，所以处理器里会看到 `channel.basicAck(deliveryTag, false)` 这种代码。

> 💡 前端类比：ACK 像 Promise 的 resolve，NACK 像 reject。手动 ACK 就像你不自动 resolve，而是在业务逻辑里显式调用，确保消息真的处理完了才告诉 MQ"可以删了"。

---

## 六、逐行拆解常量类 RabbitConsts.java

```java
public interface RabbitConsts {
    String DIRECT_MODE_QUEUE_ONE = "queue.direct.1";   // 直接模式队列名
    String QUEUE_TWO = "queue.2";                       // 队列2
    String QUEUE_THREE = "3.queue";                     // 队列3
    String FANOUT_MODE_QUEUE = "fanout.mode";           // 分列交换器名
    String TOPIC_MODE_QUEUE = "topic.mode";              // 主题交换器名
    String TOPIC_ROUTING_KEY_ONE = "queue.#";           // 主题路由键1
    String TOPIC_ROUTING_KEY_TWO = "*.queue";           // 主题路由键2
    String TOPIC_ROUTING_KEY_THREE = "3.queue";         // 主题路由键3
    String DELAY_QUEUE = "delay.queue";                 // 延迟队列名
    String DELAY_MODE_QUEUE = "delay.mode";             // 延迟交换器名
}
```

**为什么用 interface 放常量？** Java 里 interface 的字段默认是 `public static final`，天然适合做常量池。这样 `RabbitConsts.DIRECT_MODE_QUEUE_ONE` 就是全局常量，避免到处写字符串导致拼写错误。

> 💡 前端类比：这像前端把 API 路径、事件名统一定义在 `constants.ts` 里，而不是各处硬编码字符串。

---

## 七、逐行拆解消息体 MessageStruct.java

```java
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class MessageStruct implements Serializable {
    private static final long serialVersionUID = 392365881428311040L;
    private String message;
}
```

- `implements Serializable`：**必须实现序列化**。消息要经过网络传输，必须能序列化成字节流。不实现会报错。
- `serialVersionUID`：序列化版本号，反序列化时校验用。
- Lombok 四件套：`@Data`（getter/setter）、`@Builder`（链式构造 `MessageStruct.builder().message("x").build()`）、`@NoArgsConstructor` + `@AllArgsConstructor`（无参和全参构造器，反序列化需要无参构造）。

> 💡 前端类比：这像定义一个 TS interface `interface MessageStruct { message: string }`，但 Java 要显式处理序列化。`@Builder` 类似 TS 的对象字面量简写。

---

## 八、逐行拆解核心配置类 RabbitMqConfig.java（本模块最核心）

这个类用 `@Bean` 声明了所有队列、交换器、绑定关系。Spring 启动时会执行这些方法，如果 RabbitMQ 上不存在对应资源就自动创建。

### 8.1 自定义 RabbitTemplate（消息发送模板 + 可靠性回调）

```java
@Bean
public RabbitTemplate rabbitTemplate(CachingConnectionFactory connectionFactory) {
    connectionFactory.setPublisherConfirms(true);   // 开启发送确认
    connectionFactory.setPublisherReturns(true);    // 开启返回确认（消息找不到队列时）
    RabbitTemplate rabbitTemplate = new RabbitTemplate(connectionFactory);
    rabbitTemplate.setMandatory(true);             // 消息找不到队列时强制返回，而不是丢弃
    rabbitTemplate.setConfirmCallback((correlationData, ack, cause) ->
        log.info("消息发送成功:correlationData({}),ack({}),cause({})", correlationData, ack, cause));
    rabbitTemplate.setReturnCallback((message, replyCode, replyText, exchange, routingKey) ->
        log.info("消息丢失:exchange({}),route({}),replyCode({}),replyText({}),message:{}",
                 exchange, routingKey, replyCode, replyText, message));
    return rabbitTemplate;
}
```

**两套可靠性回调（容易混淆，重点理解）：**

| 回调 | 触发时机 | 回答的问题 |
| --- | --- | --- |
| `ConfirmCallback` | 消息**到达交换器**后（无论是否成功路由到队列） | "MQ 收到我的消息了吗？" |
| `ReturnCallback` | 消息到了交换器，但**找不到队列**时 | "我的消息投递到队列了吗？" |

- `setPublisherConfirms(true)`：开启 Confirm 机制，Broker 收到消息后回调 `ConfirmCallback`。
- `setPublisherReturns(true)` + `setMandatory(true)`：消息路由失败时，不静默丢弃，而是回调 `ReturnCallback`。

> 💡 前端类比：`ConfirmCallback` 像 `fetch` 的 `.then()`（请求到达服务器了），`ReturnCallback` 像服务器返回 404（到了服务器但找不到资源）。两者配合实现"消息不丢失"。

### 8.2 直接模式（Direct）

```java
@Bean
public Queue directOneQueue() {
    return new Queue(RabbitConsts.DIRECT_MODE_QUEUE_ONE);
}
```

直接模式最简单：生产者发消息时直接用队列名当 RoutingKey，消息直接进队列。其实 RabbitMQ 有个默认交换器（名字为空字符串 `""`），它就是 direct 类型，自动把所有队列绑定到它上面，RoutingKey 就是队列名。所以 `convertAndSend("queue.direct.1", msg)` 等价于走默认交换器直达队列。

### 8.3 分列模式（Fanout）—— 广播

```java
@Bean
public FanoutExchange fanoutExchange() {
    return new FanoutExchange(RabbitConsts.FANOUT_MODE_QUEUE);
}

@Bean
public Binding fanoutBinding1(Queue directOneQueue, FanoutExchange fanoutExchange) {
    return BindingBuilder.bind(directOneQueue).to(fanoutExchange);
}

@Bean
public Binding fanoutBinding2(Queue queueTwo, FanoutExchange fanoutExchange) {
    return BindingBuilder.bind(queueTwo).to(fanoutExchange);
}
```

- `FanoutExchange`：分列交换器，**忽略 RoutingKey**，把消息广播给所有绑定的队列。
- 这里把 `directOneQueue`（队列1）和 `queueTwo`（队列2）都绑定到 fanout 交换器。一条消息发过来，两个队列都会收到一份。

> 💡 前端类比：Fanout 就是 `EventBus.emit('event', data)`，所有 `on('event')` 的监听器都触发，不分筛选条件。

### 8.4 主题模式（Topic）—— 模式匹配

```java
@Bean
public TopicExchange topicExchange() {
    return new TopicExchange(RabbitConsts.TOPIC_MODE_QUEUE);
}

// 绑定1：fanout交换器 ← topic交换器，路由键 queue.#
@Bean
public Binding topicBinding1(FanoutExchange fanoutExchange, TopicExchange topicExchange) {
    return BindingBuilder.bind(fanoutExchange).to(topicExchange).with(RabbitConsts.TOPIC_ROUTING_KEY_ONE);
}

// 绑定2：队列2 ← topic交换器，路由键 *.queue
@Bean
public Binding topicBinding2(Queue queueTwo, TopicExchange topicExchange) {
    return BindingBuilder.bind(queueTwo).to(topicExchange).with(RabbitConsts.TOPIC_ROUTING_KEY_TWO);
}

// 绑定3：队列3 ← topic交换器，路由键 3.queue
@Bean
public Binding topicBinding3(Queue queueThree, TopicExchange topicExchange) {
    return BindingBuilder.bind(queueThree).to(topicExchange).with(RabbitConsts.TOPIC_ROUTING_KEY_THREE);
}
```

主题交换器按 RoutingKey 的**通配符模式**匹配。本模块设计得很巧妙——**交换器还能绑定到交换器**（绑定1 把 fanout 交换器绑到 topic 交换器上），形成路由链。

测试用例的三条消息会这样路由：

| 发送的 RoutingKey | 匹配的绑定 | 最终到达的队列 |
| --- | --- | --- |
| `queue.aaa.bbb` | `queue.#`（匹配）→ fanout → 队列1、队列2 | 队列1、队列2 |
| `ccc.queue` | `*.queue`（匹配）→ 队列2 | 队列2 |
| `3.queue` | `*.queue` 和 `3.queue` 都匹配 → 队列2、队列3 | 队列2、队列3 |

> 💡 前端类比：Topic 像 Express 的路径参数路由 `app.get('/user/:id', ...)`，用模式而非精确匹配。`*` 像 `:param`（一段），`#` 像 `*` 通配（多段）。

### 8.5 延迟队列（x-delayed-message）

```java
@Bean
public Queue delayQueue() {
    return new Queue(RabbitConsts.DELAY_QUEUE, true);   // true 表示持久化
}

@Bean
public CustomExchange delayExchange() {
    Map<String, Object> args = Maps.newHashMap();
    args.put("x-delayed-type", "direct");
    return new CustomExchange(RabbitConsts.DELAY_MODE_QUEUE, "x-delayed-message", true, false, args);
}

@Bean
public Binding delayBinding(Queue delayQueue, CustomExchange delayExchange) {
    return BindingBuilder.bind(delayQueue).to(delayExchange).with(RabbitConsts.DELAY_QUEUE).noargs();
}
```

**延迟队列需要安装插件**：`rabbitmq_delayed_message_exchange`（README 里有 Docker 安装步骤）。插件提供 `x-delayed-message` 类型的交换器。

- `new Queue(name, true)`：第二个参数 `true` 表示队列**持久化**，MQ 重启后队列不丢。
- `CustomExchange`：自定义交换器，type 是 `x-delayed-message`，参数 `x-delayed-type: direct` 指定内部用 direct 方式路由。
- `noargs()`：自定义交换器绑定时要加这个，表示不在运行时传参数。

发送延迟消息时，在消息头里塞 `x-delay` 指定延迟毫秒数（见测试类）。

---

## 九、逐行拆解消费者（消息处理器）

四个处理器结构几乎一样，以 `DirectQueueOneHandler` 为例：

```java
@Slf4j
@RabbitListener(queues = RabbitConsts.DIRECT_MODE_QUEUE_ONE)
@Component
public class DirectQueueOneHandler {

    @RabbitHandler
    public void directHandlerManualAck(MessageStruct messageStruct, Message message, Channel channel) {
        final long deliveryTag = message.getMessageProperties().getDeliveryTag();
        try {
            log.info("直接队列1，手动ACK，接收消息：{}", JSONUtil.toJsonStr(messageStruct));
            channel.basicAck(deliveryTag, false);   // 手动确认
        } catch (IOException e) {
            try {
                channel.basicRecover();   // 处理失败，重新入队
            } catch (IOException e1) {
                e1.printStackTrace();
            }
        }
    }
}
```

### 9.1 两个核心注解

- `@RabbitListener(queues = "...")`：标记这个类（或方法）监听指定队列。队列一有消息就触发。
- `@RabbitHandler`：标记处理消息的方法。一个类可以有多个 `@RabbitHandler`，Spring 按消息类型分发到匹配的方法。

> 💡 前端类比：`@RabbitListener` 像 `EventBus.on('queue.direct.1', handler)`，`@RabbitHandler` 像 handler 函数本体。

### 9.2 方法参数

```java
public void directHandlerManualAck(MessageStruct messageStruct, Message message, Channel channel)
```

- `MessageStruct messageStruct`：消息体，Spring 自动反序列化成这个对象（因为 `MessageStruct` 实现了 Serializable）。
- `Message message`：原始消息对象，包含消息头、deliveryTag 等元数据。
- `Channel channel`：AMQP 通道，用于手动 ACK。

### 9.3 手动 ACK 流程

```java
final long deliveryTag = message.getMessageProperties().getDeliveryTag();
channel.basicAck(deliveryTag, false);
```

- `deliveryTag`：消息的投递标签，同一通道内单调递增，ACK 时用它定位消息。
- `basicAck(deliveryTag, multiple)`：确认消费。`multiple=false` 只确认当前消息；`true` 确认该 tag 及之前所有未确认消息。
- `basicRecover()`：处理失败时，重新把消息入队，让消费者再消费一次。

> ⚠️ 注意：手动 ACK 模式下，如果不调 `basicAck`，消息会一直留在队列里（状态为 Unacked），下次启动还会再消费。这是新手最常踩的坑——忘 ACK 导致消息堆积。

### 9.4 四个处理器对照

| 处理器 | 监听队列 | 对应模式 |
| --- | --- | --- |
| `DirectQueueOneHandler` | `queue.direct.1` | 直接模式 |
| `QueueTwoHandler` | `queue.2` | 分列 + 主题（队列2被两种模式绑定） |
| `QueueThreeHandler` | `3.queue` | 主题模式 |
| `DelayQueueHandler` | `delay.queue` | 延迟队列 |

---

## 十、逐行拆解生产者（测试类）

生产者用 `RabbitTemplate` 发消息，本模块在测试类里演示：

### 10.1 直接模式发送

```java
@Test
public void sendDirect() {
    rabbitTemplate.convertAndSend(RabbitConsts.DIRECT_MODE_QUEUE_ONE, new MessageStruct("direct message"));
}
```

`convertAndSend(routingKey, message)`：走默认交换器，routingKey 直接当队列名，消息进 `queue.direct.1`。

### 10.2 分列模式发送

```java
@Test
public void sendFanout() {
    rabbitTemplate.convertAndSend(RabbitConsts.FANOUT_MODE_QUEUE, "", new MessageStruct("fanout message"));
}
```

`convertAndSend(exchange, routingKey, message)`：发到 fanout 交换器，routingKey 传空串（fanout 忽略它）。绑定的队列1、队列2 都会收到。

### 10.3 主题模式发送

```java
@Test
public void sendTopic1() {
    rabbitTemplate.convertAndSend(RabbitConsts.TOPIC_MODE_QUEUE, "queue.aaa.bbb", new MessageStruct("topic message"));
}
```

发到 topic 交换器，routingKey 是 `queue.aaa.bbb`，按通配符规则匹配到绑定的队列。

### 10.4 延迟队列发送（最特殊）

```java
@Test
public void sendDelay() {
    rabbitTemplate.convertAndSend(RabbitConsts.DELAY_MODE_QUEUE, RabbitConsts.DELAY_QUEUE,
        new MessageStruct("delay message, delay 5s, " + DateUtil.date()),
        message -> {
            message.getMessageProperties().setHeader("x-delay", 5000);
            return message;
        });
}
```

- 第四个参数是 `MessagePostProcessor`，在消息发送前对消息做后处理。
- `setHeader("x-delay", 5000)`：设置延迟 5000 毫秒。插件读到这个头，会把消息"压住"5 秒后才投递到队列。
- 测试连发三条，分别延迟 5s、2s、8s，消费时会按 2s→5s→8s 的顺序收到（按延迟时间到期先后，不是发送顺序）。

> 💡 前端类比：延迟队列像 `setTimeout`——你发消息时指定延迟时间，到点才触发处理。`x-delay` 就是 setTimeout 的毫秒数。

---

## 十一、运行与验证

### 11.1 启动 RabbitMQ

用 Docker（README 提供的步骤，需装延迟插件）：

```sh
docker pull rabbitmq:3.7.7-management
docker run -d -p 5672:5672 -p 15672:15672 --name rabbit-3.7.7 rabbitmq:3.7.7-management
# 进入容器装延迟插件（见 README 步骤 3-8）
```

装好后访问 `http://localhost:15672`（账号 guest/guest）能看到管理界面。

### 11.2 运行测试

启动 Spring Boot 应用（让配置类创建队列、交换器、绑定，并启动消费者监听），然后在 IDE 里逐个跑测试方法：

| 测试方法 | 预期日志 |
| --- | --- |
| `sendDirect` | `直接队列1，手动ACK，接收消息：{"message":"direct message"}` |
| `sendFanout` | 队列1、队列2 各打印一次（广播） |
| `sendTopic1` | 队列1、队列2 各一次（`queue.#` 匹配） |
| `sendTopic3` | 队列2、队列3 各一次（`*.queue` 和 `3.queue` 都匹配） |
| `sendDelay` | 2s 后先收到"delay 2s"，5s 后收到"delay 5s"，8s 后收到"delay 8s" |

### 11.3 管理界面验证

在 `http://localhost:15672` 的 Queues 页面能看到所有队列，Exchanges 页面能看到所有交换器和绑定关系，非常直观。

---

## 十二、动手练习

1. **改 ACK 模式**：把 `application.yml` 的 `acknowledge-mode` 改成 `auto`，把处理器改成不带 `Channel` 参数的简单方法，观察消息仍能正常消费。
2. **故意不 ACK**：在手动模式下注释掉 `channel.basicAck`，重启应用，观察消息状态变成 Unacked，重启后重复消费。
3. **加一个队列**：新建一个队列4，绑到 fanout 交换器，发 fanout 消息，观察队列4也收到。
4. **改通配符**：把 `*.queue` 改成 `#.queue`，发 `a.b.c.queue`，观察是否匹配（应该匹配）。
5. **改延迟时间**：把 `x-delay` 改成 10000（10秒），观察消费延迟。
6. **体验 Confirm 回调**：故意把 host 改错重启，观察 `ConfirmCallback` 里 `ack=false` 的日志。

---

## 十三、本模块知识点总结（结合实际开发详解）

消息队列是后端架构的核心组件之一，掌握它需要理解模型、可靠性、实战场景。下面把核心知识点放到真实开发场景里讲透。

### 13.1 四种交换器怎么选？

**实际开发中的选择标准：**

- **Direct（直接）**：一对一或一对少，且路由规则固定。比如"订单消息发给订单服务"。生产中其实最常用，因为简单可控。
- **Fanout（分列/广播）**：一条消息要被多个服务同时处理。比如"用户注册成功"要同时触发发短信、送积分、推 CRM——发到 fanout，各服务各取所需。
- **Topic（主题）**：按模式路由，灵活但规则复杂。比如日志收集：`log.error.db`、`log.info.api`，不同消费者订阅不同级别的日志。
- **Headers（头交换器，本模块未演示）**：按消息头属性匹配，比 Topic 更灵活但性能略低，用得少。

**最佳实践**：能用 Direct 就不用 Topic（简单优先），需要广播才用 Fanout。Topic 的通配符虽然强大，但规则一旦复杂，排查"消息为什么没到某个队列"会非常痛苦。

**常见坑**：

- Topic 通配符写错：`user.*` 期望匹配 `user.a.b`，实际匹配不了（`*` 只匹配一段）。
- Fanout 模式下还传 RoutingKey 期望它生效：Fanout 根本不看 Key，传了也白传。
- 队列名/交换器名拼错：生产者和消费者的字符串不一致，消息发出去没人消费，还不报错（静默失败）。

### 13.2 消息可靠性：如何保证消息不丢？

这是消息队列在生产环境的核心问题。一条消息从生产到消费，要经过三个环节，每个环节都可能丢：

| 环节 | 丢的原因 | 解决方案 |
| --- | --- | --- |
| 生产者 → 交换器 | 网络故障 | `ConfirmCallback`（publisher-confirms） |
| 交换器 → 队列 | 路由键不匹配 | `ReturnCallback` + `mandatory=true` |
| 队列本身 | MQ 宕机重启 | 队列持久化（`durable=true`）+ 消息持久化 |
| 队列 → 消费者 | 消费者处理失败 | 手动 ACK，失败不确认 |

**本模块的可靠性配置（生产级标配）：**

```java
connectionFactory.setPublisherConfirms(true);   // 环节1
connectionFactory.setPublisherReturns(true);     // 环节2
rabbitTemplate.setMandatory(true);              // 环节2
new Queue(name, true);                          // 环节3：队列持久化
acknowledge-mode: manual                        // 环节4：手动ACK
```

**实际开发的进阶做法**：

- 生产者开 Confirm 后，配合"本地消息表"——发消息前先写一条记录到数据库，Confirm 回调来了再更新状态，定时任务补偿未确认的。这是"最终一致性"的常见实现。
- 消费者手动 ACK 时，处理失败要区分"可重试异常"（网络超时，可重试）和"不可重试异常"（参数错误，重试也没用）。后者应该 `basicReject(deliveryTag, false)`（不重新入队）+ 死信队列，避免无限重试。

**常见坑**：

- 只开了 `publisher-confirms` 没处理 `ReturnCallback`：消息到了交换器但路由不到队列，静默丢失。
- 消息没持久化：虽然队列持久化了，但消息默认不是持久化的，MQ 重启后队列在但消息没了。生产中发消息时要设置 `MessageProperties.PERSISTENT_TEXT_PLAIN`。
- ACK 模式选错：`auto` 模式下消费者抛异常，Spring 会自动 NACK 并无限重试，导致"毒消息"——同一条坏消息反复消费卡死队列。

### 13.3 消费者手动 ACK 的正确姿势

本模块的 ACK 代码是基础版，生产环境要更完善：

```java
@RabbitHandler
public void handle(MessageStruct msg, Message message, Channel channel) {
    long deliveryTag = message.getMessageProperties().getDeliveryTag();
    try {
        // 业务处理
        doBusiness(msg);
        channel.basicAck(deliveryTag, false);          // 成功：确认
    } catch (BusinessRetryableException e) {
        // 可重试异常：重新入队
        channel.basicNack(deliveryTag, false, true);
    } catch (Exception e) {
        // 不可重试：拒绝且不重新入队，进死信队列
        channel.basicReject(deliveryTag, false);
    }
}
```

**关键 API：**

| 方法 | 含义 |
| --- | --- |
| `basicAck(tag, multiple)` | 确认消费 |
| `basicNack(tag, multiple, requeue)` | 否认，`requeue=true` 重新入队 |
| `basicReject(tag, requeue)` | 拒绝单条，`requeue=false` 进死信 |
| `basicRecover()` | 重新入队（本模块用的，等价于 nack+requeue） |

**常见坑**：

- `multiple=true` 误用：会一次性确认该 tag 之前所有未确认消息，可能误确认别的消息。
- 忘 ACK：消息卡在 Unacked 状态，消费者断开后又重新投递，导致重复消费。
- ACK 顺序问题：同一通道内必须按 deliveryTag 顺序 ACK，乱序 ACK 会协议错误。

### 13.4 延迟队列的几种实现方式

本模块用插件 `rabbitmq_delayed_message_exchange` 实现延迟，但 RabbitMQ 实现延迟还有其他方式：

| 方式 | 原理 | 优缺点 |
| --- | --- | --- |
| **延迟插件（本模块）** | 交换器暂存消息，到期投递 | 简单，但需装插件；插件本身有性能开销 |
| **TTL + 死信队列** | 消息设过期时间，过期后转死信队列被消费 | 不需插件，但 TTL 队列有"队头阻塞"问题 |
| **延迟队列库** | 业务层用定时任务扫描 | 不依赖 MQ，但精度差、占 DB |

**实际开发场景**：订单超时自动取消（下单30分钟未支付则取消）、定时推送（指定时间发通知）、重试退避（失败后延迟重试）。

**最佳实践**：

- 延迟精度要求高、量不大 → 用插件（本模块方式）。
- 量极大、且允许误差 → 用 TTL+死信，或直接上专业的延迟方案（如 Redis ZSet、定时任务）。
- 延迟消息要保证幂等：同一条消息可能因重试被消费多次，消费者必须能处理重复消息。

**常见坑**：

- 插件没装：启动报错"unknown exchange type x-delayed-message"。
- `x-delay` 设错单位：它是毫秒，不是秒，5000 = 5秒。
- 延迟消息丢了：插件交换器本身不持久化消息的话，MQ 重启延迟消息会丢，生产要确保持久化。

### 13.5 Spring AMQP 的自动配置与 RabbitTemplate

`spring-boot-starter-amqp` 的自动配置做了很多事，理解它能少踩坑：

- 根据 `spring.rabbitmq.*` 自动创建 `CachingConnectionFactory`（连接池封装）。
- 自动创建 `RabbitTemplate`（发送模板）和 `AmqpAdmin`（管理队列/交换器）。
- `@RabbitListener` 注解的消费者，自动创建监听容器，并发消费。

**实际开发的常用配置（application.yml）：**

```yaml
spring:
  rabbitmq:
    host: rabbitmq.prod
    port: 5672
    username: ${MQ_USER}        # 生产用环境变量注入
    password: ${MQ_PASSWORD}
    virtual-host: /order       # 按业务隔离 vhost
    publisher-confirms: true   # 开启确认
    publisher-returns: true
    template:
      mandatory: true
      retry:                    # 发送失败重试
        enabled: true
        max-attempts: 3
    listener:
      simple:
        acknowledge-mode: manual
        prefetch: 5             # 每个消费者预取5条（控制并发和压力）
        concurrency: 3          # 3个并发消费者
        max-concurrency: 10     # 最大10个
```

**`prefetch` 是关键**：控制消费者一次预取多少条未 ACK 的消息。设太大→消费者内存压力大、消息处理不均；设太小→吞吐低。默认无限，生产必须设。

> 💡 前端类比：`prefetch` 像 React 的批量更新窗口大小，或像数据库连接池的池大小——控制"一次拿多少活儿干"。

### 13.6 消息序列化：为什么收到的是乱码？

Spring AMQP 默认用 `SimpleMessageConverter`，它把对象序列化成 Java 原生序列化字节流（所以 `MessageStruct` 要 `implements Serializable`）。但这种方式有两个问题：

1. 跨语言不友好：如果生产者是 Python/Go，看不懂 Java 序列化。
2. 可读性差：管理界面里看消息是一串乱码。

**生产环境推荐用 JSON 序列化**，自定义配置：

```java
@Bean
public MessageConverter jsonMessageConverter() {
    return new Jackson2JsonMessageConverter();
}
```

这样消息在 MQ 里就是可读的 JSON，跨语言也能消费。

**常见坑**：

- 消费者反序列化失败：生产者改了消息类加字段，消费者还是老类，反序列化报错。解决：用 JSON（宽松）+ 版本兼容设计。
- `MessageStruct` 忘 `implements Serializable`：用默认转换器时直接报错。

### 13.7 消息重复消费与幂等性

MQ 保证"至少一次"投递，不保证"恰好一次"。也就是说，同一条消息可能被消费多次（网络抖动重试、消费者宕机重投）。所以**消费者必须设计成幂等的**——处理同一条消息一次和多次，结果一致。

**实现幂等的常见方案：**

1. **唯一约束**：消息带业务 ID，处理时先查数据库是否已处理，处理过就跳过。
2. **状态机**：订单从"待支付"→"已支付"，重复消息来时已是"已支付"，直接忽略。
3. **Redis 去重**：用 `SETNX` 记录已处理的消息 ID，设过期时间。

> 💡 前端类比：像 React 的 `useEffect` 依赖数组防止重复执行，或防抖/节流。后端幂等是"同一输入多次处理结果不变"。

**常见坑**：以为 MQ 会保证不重复，不做幂等，结果用户收到两条短信、扣了两次库存。这是生产事故的高发区。

---

> 📌 **学习建议**：消息队列是前端转后端最容易"看不懂用途"的组件——因为前端没有真正等价物（Event Bus 是进程内的，MQ 是跨进程的）。建议先把本模块跑通，在管理界面里观察消息的流动，建立"生产者→交换器→队列→消费者"的直观感受。然后重点理解三件事：**可靠性（消息不丢）、ACK 机制（消费确认）、幂等性（重复消费）**——这三点是 MQ 在生产环境的命脉。后续 Kafka 模块会对比另一种 MQ 设计哲学（Kafka 是日志模型，RabbitMQ 是队列模型），学完两者能对消息中间件有完整认知。
