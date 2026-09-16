# 32 - 消息中间件 Kafka

> 对应项目模块：`demo-mq-kafka`
> 前置知识：已学完前面基础模块，了解 Spring Boot 启动类、配置文件、`@Component` 注入
> 学习目标：理解 Kafka 的核心概念，掌握 Spring Boot 集成 Kafka 实现消息发送与接收，理解手动提交 offset、批量消费、并发消费等生产级配置。

---

## 一、本模块要解决什么问题？

在分布式系统里，服务之间经常需要"异步通信"。比如用户下单后，要发短信、扣库存、加积分——如果都同步调用，一个慢全拖慢，一个挂全失败。**消息中间件**就是解决这个问题的：发送方把消息丢给中间件就返回，接收方按自己的节奏消费，实现**解耦、异步、削峰**。

本模块演示 Spring Boot 集成 Kafka，实现：用 `KafkaTemplate` 发送消息，用 `@KafkaListener` 接收消息，并用手动提交 offset 保证消息不丢失。

### 1.1 Kafka 是什么？和 RabbitMQ 有什么区别？

Kafka 最初由 LinkedIn 开发，后来成为 Apache 顶级项目。它是一个**分布式流处理平台**，本质是"高吞吐、可持久化、可水平扩展的分布式消息日志"。

| 对比维度 | Kafka | RabbitMQ |
| --- | --- | --- |
| 设计模型 | 追加写入的日志（类似数据库 binlog） | 经典 AMQP 队列（消息消费后即删） |
| 吞吐量 | 极高（百万级/秒） | 较高（万级/秒） |
| 消息可靠性 | 靠多副本 + 持久化 | 靠 ACK + 持久化 |
| 典型场景 | 日志收集、事件溯源、流处理、大数据 | 业务消息、任务队列、RPC 异步 |
| 消息消费 | 拉取（pull），可重复消费 | 推送（push），消费即删 |
| 顺序性 | 单分区有序 | 单队列有序 |

> 💡 前端类比：Kafka 像一个"无限追加的日志文件"，前端同学可以类比 `console.log` 不断写入的日志流，或者类比 Redux 的事件溯源——所有消息按顺序追加，消费者可以回放历史。RabbitMQ 更像前端的 `EventEmitter` / `mitt`，消息发出、监听到就消费、消费完就没了。

### 1.2 Kafka 的核心概念（必须先搞懂）

| 概念 | 类比 | 说明 |
| --- | --- | --- |
| **Broker** | 一个服务器节点 | Kafka 集群由多个 broker 组成 |
| **Topic** | 消息的分类 | 生产者发到某个 topic，消费者订阅某个 topic |
| **Partition** | topic 的分片 | 一个 topic 分成多个 partition，分布在不同 broker 上，实现水平扩展 |
| **Offset** | 消息在 partition 里的序号 | 消费者记录自己消费到第几条，重启后从这继续 |
| **Producer** | 消息生产者 | 往 topic 发消息的客户端 |
| **Consumer** | 消息消费者 | 从 topic 拉消息的客户端 |
| **Consumer Group** | 消费者组 | 同组内一个 partition 只能被一个消费者消费，实现负载均衡 |

> 💡 前端类比：Topic 像一个频道（类似 WebSocket 的 room），Partition 像频道里的多个子队列，Consumer Group 像一组订阅者分工消费。Offset 像播放进度条，记录你"听"到第几条了。

---

## 二、项目结构

```
demo-mq-kafka/
├── pom.xml
└── src/main/java/com/xkcoding/mq/kafka/
    ├── SpringBootDemoMqKafkaApplication.java   # 启动类
    ├── config/
    │   └── KafkaConfig.java                     # Kafka 配置类（核心）
    ├── constants/
    │   └── KafkaConsts.java                     # 常量（topic 名、分区数）
    └── handler/
        └── MessageHandler.java                 # 消息消费者（@KafkaListener）
└── src/test/java/.../
    └── SpringBootDemoMqKafkaApplicationTests.java  # 测试发送消息
└── src/main/resources/
    └── application.yml                          # Kafka 配置
```

注意本模块**没有 Controller**——发送消息是在测试类里做的。实际项目里通常会在 Controller 或 Service 里调用 `KafkaTemplate.send()`。

---

## 三、逐行拆解 pom.xml

```xml
<dependencies>
    <!-- 1. Spring Boot 基础 Starter（注意：不是 starter-web） -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter</artifactId>
    </dependency>

    <!-- 2. Spring Kafka（核心依赖） -->
    <dependency>
        <groupId>org.springframework.kafka</groupId>
        <artifactId>spring-kafka</artifactId>
    </dependency>

    <!-- 3. 测试 -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-test</artifactId>
        <scope>test</scope>
    </dependency>

    <!-- 4. Lombok -->
    <dependency>
        <groupId>org.projectlombok</groupId>
        <artifactId>lombok</artifactId>
        <optional>true</optional>
    </dependency>

    <!-- 5. Hutool 工具类 -->
    <dependency>
        <groupId>cn.hutool</groupId>
        <artifactId>hutool-all</artifactId>
    </dependency>

    <!-- 6. Guava 工具类 -->
    <dependency>
        <groupId>com.google.guava</groupId>
        <artifactId>guava</artifactId>
    </dependency>
</dependencies>
```

**关键点：**

- 这里用的是 `spring-boot-starter`（不是 `spring-boot-starter-web`），因为本 demo 不提供 HTTP 接口，只演示消息收发。但实际项目通常会同时引 web，方便通过接口触发发送。
- `spring-kafka` 是 Spring 对 Apache Kafka 客户端的封装，提供 `KafkaTemplate`（发送）和 `@KafkaListener`（接收）等便利注解。版本由父 POM 的 `spring-boot-dependencies` 统一管理（Spring Boot 2.1.0 对应 spring-kafka 2.2.0）。

> ⚠️ **版本对应关系很重要**：Spring Boot 版本、spring-kafka 版本、kafka-clients 版本、Kafka 服务端版本必须匹配，否则会出现各种诡异问题。README 里给了对应表，升级时务必核对。

---

## 四、配置文件 application.yml

```yaml
server:
  port: 8080
  servlet:
    context-path: /demo
spring:
  kafka:
    bootstrap-servers: localhost:9092          # Kafka 服务地址
    producer:                                   # 生产者配置
      retries: 0                                # 重试次数（0=不重试）
      batch-size: 16384                        # 批量发送大小（字节）
      buffer-memory: 33554432                  # 生产者缓冲区大小（32MB）
      key-serializer: org.apache.kafka.common.serialization.StringSerializer
      value-serializer: org.apache.kafka.common.serialization.StringSerializer
    consumer:                                   # 消费者配置
      group-id: spring-boot-demo                # 消费者组 ID
      enable-auto-commit: false                 # 关闭自动提交 offset
      auto-offset-reset: latest                 # 新消费者从最新位置开始读
      key-deserializer: org.apache.kafka.common.serialization.StringDeserializer
      value-deserializer: org.apache.kafka.common.serialization.StringDeserializer
      properties:
        session.timeout.ms: 60000               # 会话超时（心跳）
    listener:                                   # 监听器配置
      log-container-config: false
      concurrency: 5                            # 并发消费线程数
      ack-mode: manual_immediate               # 手动立即提交
```

### 4.1 生产者配置详解

| 配置项 | 作用 | 默认值 |
| --- | --- | --- |
| `bootstrap-servers` | Kafka broker 地址，多个用逗号分隔 | 无（必填） |
| `retries` | 发送失败重试次数。生产环境建议设为较大值（如 3）保证可靠 | 0 |
| `batch-size` | 批量大小。Kafka 生产者会攒一批再发，提高吞吐 | 16384(16KB) |
| `buffer-memory` | 生产者可用缓冲区总大小 | 32MB |
| `key-serializer` | key 的序列化器。发消息时 key 可有可无 | - |
| `value-serializer` | value 的序列化器。这里用 String | - |

> 💡 前端类比：`batch-size` 像 axios 的请求合并/批量请求——攒一批一起发比一条条发效率高。`retries` 像 fetch 的重试逻辑。

### 4.2 消费者配置详解

| 配置项 | 作用 |
| --- | --- |
| `group-id` | 消费者组名。同组内 partition 被均分消费，不同组各自独立消费全量 |
| `enable-auto-commit` | 是否自动提交 offset。本 demo 设 false，改手动提交 |
| `auto-offset-reset` | 消费者首次消费或 offset 失效时从哪开始：`earliest`（从头）/`latest`（只读新消息） |
| `session.timeout.ms` | 心跳超时。超时未心跳则被认为挂了，触发 rebalance |

### 4.3 listener 配置详解

| 配置项 | 作用 |
| --- | --- |
| `concurrency` | 消费线程数。一般等于 partition 数，多了浪费，少了消费不过来 |
| `ack-mode` | 提交 offset 的模式。`manual_immediate` 表示手动调用后立即提交 |

---

## 五、常量类 KafkaConsts

```java
public interface KafkaConsts {
    /** 默认分区大小 */
    Integer DEFAULT_PARTITION_NUM = 3;

    /** Topic 名称 */
    String TOPIC_TEST = "test";
}
```

用接口定义常量是 Java 的一种写法（接口字段默认 `public static final`）。本 demo 里 topic 名是 `test`，分区数 3。实际项目更推荐用 `enum` 或普通常量类，接口常量是老风格。

---

## 六、配置类 KafkaConfig（核心）

```java
@Configuration
@EnableConfigurationProperties({KafkaProperties.class})
@EnableKafka
@AllArgsConstructor
public class KafkaConfig {
    private final KafkaProperties kafkaProperties;

    // 1. 生产者工厂
    @Bean
    public ProducerFactory<String, String> producerFactory() {
        return new DefaultKafkaProducerFactory<>(kafkaProperties.buildProducerProperties());
    }

    // 2. KafkaTemplate（发送消息用）
    @Bean
    public KafkaTemplate<String, String> kafkaTemplate() {
        return new KafkaTemplate<>(producerFactory());
    }

    // 3. 消费者工厂
    @Bean
    public ConsumerFactory<String, String> consumerFactory() {
        return new DefaultKafkaConsumerFactory<>(kafkaProperties.buildConsumerProperties());
    }

    // 4. 监听器容器工厂（批量消费）
    @Bean
    public ConcurrentKafkaListenerContainerFactory<String, String> kafkaListenerContainerFactory() {
        ConcurrentKafkaListenerContainerFactory<String, String> factory = new ConcurrentKafkaListenerContainerFactory<>();
        factory.setConsumerFactory(consumerFactory());
        factory.setConcurrency(KafkaConsts.DEFAULT_PARTITION_NUM);
        factory.setBatchListener(true);                 // 开启批量消费
        factory.getContainerProperties().setPollTimeout(3000);
        return factory;
    }

    // 5. 手动提交的监听器容器工厂
    @Bean("ackContainerFactory")
    public ConcurrentKafkaListenerContainerFactory<String, String> ackContainerFactory() {
        ConcurrentKafkaListenerContainerFactory<String, String> factory = new ConcurrentKafkaListenerContainerFactory<>();
        factory.setConsumerFactory(consumerFactory());
        factory.getContainerProperties().setAckMode(ContainerProperties.AckMode.MANUAL_IMMEDIATE);
        factory.setConcurrency(KafkaConsts.DEFAULT_PARTITION_NUM);
        return factory;
    }
}
```

### 6.1 注解拆解

- `@Configuration`：标记为配置类，里面的 `@Bean` 方法会被 Spring 调用，注册返回的对象到容器。
- `@EnableConfigurationProperties({KafkaProperties.class})`：启用 `KafkaProperties`，把 `application.yml` 里 `spring.kafka.*` 的配置绑定到这个对象。这样代码里就能拿到 yml 配置的值。
- `@EnableKafka`：开启 Spring Kafka 的功能，启用 `@KafkaListener` 注解的支持。
- `@AllArgsConstructor`：Lombok 注解，生成全参构造器，配合 Spring 的构造器注入把 `KafkaProperties` 注入进来。

### 6.2 两个工厂

- `ProducerFactory`：创建 Kafka 生产者客户端实例，用 yml 里的生产者配置初始化。
- `ConsumerFactory`：创建 Kafka 消费者客户端实例，用 yml 里的消费者配置初始化。

### 6.3 KafkaTemplate

`KafkaTemplate` 是 Spring 封装的发送消息工具，注入后调用 `send(topic, value)` 即可发消息。它底层用 `ProducerFactory` 创建的生产者。

### 6.4 两个监听器容器工厂

`ConcurrentKafkaListenerContainerFactory` 是 `@KafkaListener` 背后的"容器"，负责创建和管理消费者线程。本 demo 定义了两个：

1. `kafkaListenerContainerFactory`（默认）：开启批量消费（`setBatchListener(true)`），poll 超时 3 秒。
2. `ackContainerFactory`：手动提交 offset 模式（`MANUAL_IMMEDIATE`）。

> 💡 前端类比：`KafkaTemplate` 像 `axios` 实例（发请求），`@KafkaListener` 像一个 `EventEmitter.on('event', handler)`（监听事件）。容器工厂像配置这个监听器的"运行参数"。

> ⚠️ 其实 Spring Boot 的 `KafkaAutoConfiguration` 已经默认注册了 `KafkaTemplate` 和 `kafkaListenerContainerFactory`。本 demo 手写一遍是为了演示自定义配置（批量、手动提交），实际简单场景可以不写配置类，直接用自动配置的。

---

## 七、消费者 MessageHandler

```java
@Component
@Slf4j
public class MessageHandler {

    @KafkaListener(topics = KafkaConsts.TOPIC_TEST, containerFactory = "ackContainerFactory")
    public void handleMessage(ConsumerRecord record, Acknowledgment acknowledgment) {
        try {
            String message = (String) record.value();
            log.info("收到消息: {}", message);
        } catch (Exception e) {
            log.error(e.getMessage(), e);
        } finally {
            // 手动提交 offset
            acknowledgment.acknowledge();
        }
    }
}
```

### 7.1 `@KafkaListener` 详解

- `topics`：监听的 topic 名，这里是 `test`。
- `containerFactory`：用哪个容器工厂。这里指定 `ackContainerFactory`（手动提交模式）。不写则用默认的 `kafkaListenerContainerFactory`。

### 7.2 方法参数

- `ConsumerRecord`：Kafka 的一条消息记录，包含 key、value、topic、partition、offset 等。`record.value()` 拿消息内容。
- `Acknowledgment`：手动提交 offset 的句柄。调用 `acknowledge()` 表示"这条我处理完了，提交 offset"。

### 7.3 手动提交的意义

把 `acknowledge()` 放在 `finally` 里，保证**无论成功还是异常都提交**。这是一种取舍：

- **好处**：不会因为业务异常导致消息一直重试（避免"毒丸消息"卡死消费）。
- **代价**：异常时消息其实没处理成功，但 offset 已提交，消息"丢了"。

> 💡 实际开发更严谨的做法是：成功才提交，失败走重试/死信队列。本 demo 的写法偏简单，知识点总结里会详细讨论。

---

## 八、测试类：发送消息

```java
@RunWith(SpringRunner.class)
@SpringBootTest
public class SpringBootDemoMqKafkaApplicationTests {
    @Autowired
    private KafkaTemplate<String, String> kafkaTemplate;

    @Test
    public void testSend() {
        kafkaTemplate.send(KafkaConsts.TOPIC_TEST, "hello,kafka...");
    }
}
```

注入 `KafkaTemplate`，调用 `send(topic, value)` 发送一条消息。运行测试后，如果 Kafka 服务正常、`MessageHandler` 在监听，控制台会打印 `收到消息: hello,kafka...`。

---

## 九、运行与验证

### 9.1 环境准备

需要先启动 Kafka 服务（依赖 ZooKeeper）。用 Docker 最快：

```sh
# 启动 zookeeper
docker run -d --name zookeeper -p 2181:2181 wurstmeister/zookeeper
# 启动 kafka
docker run -d --name kafka -p 9092:9092 \
  -e KAFKA_ZOOKEEPER_CONNECT=zookeeper:2181 \
  -e KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://localhost:9092 \
  wurstmeister/kafka
```

### 9.2 创建 topic

```sh
# 进入 kafka 容器创建 topic
docker exec -it kafka kafka-topics.sh --create \
  --zookeeper zookeeper:2181 \
  --replication-factor 1 --partitions 1 --topic test
```

### 9.3 运行测试

运行 `testSend()` 测试方法，观察 `MessageHandler` 是否打印 `收到消息: hello,kafka...`。

---

## 十、动手练习

1. **改 topic**：把 `KafkaConsts.TOPIC_TEST` 改成 `test2`，重新创建 topic，验证消息收发。
2. **改消费组**：把 yml 的 `group-id` 改成另一个值，观察消费行为（不同组各自消费全量）。
3. **加 Controller**：写一个 `@RestController`，注入 `KafkaTemplate`，提供 `GET /send?msg=xxx` 接口触发发送，用浏览器测试。
4. **批量消费**：用默认的 `kafkaListenerContainerFactory`（开了批量），把方法签名改成 `List<ConsumerRecord> records`，遍历处理。
5. **发对象**：把 value-serializer 换成 `JsonSerializer`，发送一个 User 对象，消费端反序列化成对象。
6. **异常重试**：在 `handleMessage` 里故意抛异常，观察不提交 offset 时消息是否会重投。

---

## 十一、本模块知识点总结（结合实际开发详解）

Kafka 是大数据和高并发场景的"基础设施"，下面把核心知识点放到真实开发场景里讲透。

### 11.1 Kafka vs RabbitMQ：怎么选？

**实际开发中的选择标准：**

- **选 Kafka**：日志收集、用户行为追踪、事件溯源、实时数据流、大数据分析。特点是**高吞吐、消息可回放、顺序写磁盘性能好**。适合"消息量大、允许少量重复、需要历史回放"的场景。
- **选 RabbitMQ**：业务消息（订单、支付、通知）、任务队列、RPC 异步调用。特点是**路由灵活、消息可靠性高、延迟低**。适合"每条消息都很重要、需要复杂路由、要求低延迟"的场景。

**常见误区：** 以为 Kafka 比 RabbitMQ "高级"就什么都用 Kafka。实际上 Kafka 的消息模型（日志追加）不适合做"任务队列"——因为它消息不会消费即删，做工作流时容易重复消费。选型要看场景，不是看热度。

### 11.2 offset 提交策略：消息不丢与不重

这是 Kafka 消费者最核心的配置。本 demo 用了手动提交（`enable-auto-commit: false` + `ack-mode: manual_immediate`）。

**三种提交方式对比：**

| 方式 | 说明 | 风险 |
| --- | --- | --- |
| 自动提交 | 消费者定期自动提交 offset | 可能"消息处理还没完成就提交了"，宕机导致消息丢；或重复消费 |
| 手动同步提交 | `acknowledge()` 同步提交 | 阻塞等待，影响吞吐 |
| 手动立即提交 | 处理完立即提交（本 demo） | 灵活，但要自己控制时机 |

**实际开发的最佳实践：**

1. **可靠场景**（如订单）：处理成功才提交，失败走重试 + 死信队列（DLQ）。
2. **日志场景**（允许丢一点）：自动提交即可，追求高吞吐。
3. **精确一次（exactly-once）**：靠事务或幂等消费，光靠 offset 提交保证不了。

**常见坑：**

- 自动提交 + 异步处理：消息刚拉下来还没处理完，offset 自动提交了，宕机导致消息丢。
- 手动提交放 finally 里无脑提交：异常也提交，等于消息"被消费但没处理"，数据不一致。本 demo 就是这种简化写法，**生产环境要改成"成功才提交"**。

### 11.3 消费者组与 rebalance

**Consumer Group 的核心规则**：同一个 group 内，一个 partition 只能被一个消费者消费。所以：

- 消费者数 < partition 数：有的消费者消费多个 partition。
- 消费者数 = partition 数：每个消费者一个 partition，负载均衡。
- 消费者数 > partition 数：多余的消费者闲置（浪费）。

**rebalance（重平衡）**：当消费者加入/退出/宕机时，partition 重新分配。rebalance 期间消费者短暂停止消费。

**实际开发的坑：**

- 消费者频繁上下线导致频繁 rebalance，消费卡顿。排查 `session.timeout.ms` 和 `heartbeat.interval.ms`。
- 消费逻辑太慢导致被判定为"假死"而踢出 group。Kafka 2.x 后用 `max-poll-interval` 控制两次 poll 间隔。

### 11.4 partition 与顺序性

**Kafka 只保证单 partition 内有序**，跨 partition 不保证顺序。

**实际开发应用：**

- 需要顺序的消息（如同一订单的状态变更），用同一个 key（如 orderId），Kafka 会按 key 哈希到同一 partition，保证这个订单的消息有序。
- 不需要顺序的消息，随机 key 或不设 key，均匀分布到各 partition，并行消费提高吞吐。

**常见坑：** 以为整个 topic 有序，结果多 partition 下消息乱序。需要顺序就一定要用 key 路由。

### 11.5 批量消费与并发

本 demo 的 `kafkaListenerContainerFactory` 开了 `setBatchListener(true)`，可以一次拉一批消息处理。`concurrency` 控制消费线程数。

**实际开发权衡：**

- 批量消费：减少每条消息的开销，吞吐高，适合日志、埋点等批量场景。
- 单条消费：实时性好，适合订单等需要即时处理的场景。
- 并发数：一般设为 partition 数，超过 partition 数没意义（多余的线程分不到 partition）。

### 11.6 Spring Kafka 的自动配置

Spring Boot 有 `KafkaAutoConfiguration`，引入 `spring-kafka` 后自动注册 `KafkaTemplate` 和默认的监听器容器工厂。本 demo 手写配置类是为了演示自定义（批量、手动提交）。

**实际开发建议：**

- 简单场景：不写配置类，直接用自动配置，yml 配好就行，注入 `KafkaTemplate` 发消息，`@KafkaListener` 收消息。
- 复杂场景（多套配置、批量、手动提交、事务）：写配置类自定义，像本 demo 这样。
- 生产环境：务必关闭自动提交、开启重试、配置死信队列。

### 11.7 消息可靠性全景

Kafka 消息可靠性靠三层保障：

1. **生产端**：`retries > 0` + `acks=all`（所有副本确认才算成功），保证消息不丢。
2. **broker 端**：多副本（`replication-factor >= 3`）+ 持久化，保证 broker 宕机不丢。
3. **消费端**：手动提交 + 成功才提交 + 失败重试，保证消息被正确处理。

**常见坑：** 只配了消费端手动提交，生产端 `acks=1` 甚至 `acks=0`，broker 宕机时消息丢失。可靠性要全链路考虑。

---

> 📌 **学习建议**：Kafka 的学习曲线比 RabbitMQ 陡，因为它不只是"队列"，而是"分布式日志"。建议先把 partition/offset/consumer group 这三个概念彻底搞懂，再动手。作为前端转后端的同学，可以把 Kafka 类比成"一个可以回放的、分布式的 console.log 日志流"——生产者往里写，消费者按进度条（offset）读，读到哪里可以记录和回退。理解了这个心智模型，后面的配置项就都有意义了。
