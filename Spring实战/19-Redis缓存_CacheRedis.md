# 19 - Redis 缓存集成

> 对应项目模块：`demo-cache-redis`
> 前置知识：已学完 `01-12` 基础模块，了解 Spring Boot 启动、配置、分层架构；了解 `demo-cache-ehcache` 中的 Spring Cache 抽象（`@Cacheable`/`@CachePut`/`@CacheEvict`）更佳，但非必须
> 学习目标：掌握 Spring Boot 整合 Redis 的两种用法——用 `RedisTemplate` 直接操作 Redis 数据结构，以及用 Spring Cache 注解做声明式缓存；理解序列化、连接池、缓存一致性等核心问题。

---

## 一、本模块要解决什么问题？

### 1.1 为什么需要缓存？

后端最常见的性能瓶颈是**数据库**。一个用户查询接口，如果每次都打数据库，QPS（每秒请求数）高起来数据库就扛不住。缓存的核心思路是：**把昂贵计算/查询的结果存到更快的存储里，下次直接取，不打数据库**。

> 💡 前端类比：前端也有缓存，但层次不同——
> - 浏览器 HTTP 缓存（Cache-Control / ETag）：服务端响应带的，浏览器自己存
> - localStorage / sessionStorage / IndexedDB：浏览器本地存
> - 前端内存缓存（Map / WeakMap / React Query 的 cache）：进程内
>
> 后端的 Redis 缓存是**服务端进程外的远程缓存**——多个应用实例共享同一份缓存数据，这是和前端最大的区别。你可以把它理解成一个"所有后端服务都能访问的、超快的、远程的 localStorage"。

### 1.2 为什么是 Redis？

| 缓存类型 | 速度 | 是否共享 | 容量 | 典型代表 |
| --- | --- | --- | --- | --- |
| 进程内缓存 | 极快（纳秒级） | 否（各实例独立） | 受限于堆内存 | Guava Cache、Caffeine、Ehcache |
| 远程缓存 | 快（毫秒级，走网络） | 是（多实例共享） | 大（独立部署） | Redis、Memcached |

- **进程内缓存**（如 `demo-cache-ehcache`）：快，但每个服务实例各存一份，数据不一致、内存占用高。
- **Redis**：独立部署，所有实例共享，天然解决分布式缓存问题，是生产环境的事实标准。

本模块演示两件事：
1. **直接操作 Redis**：用 `RedisTemplate` 存取各种 Redis 数据结构（String/Hash/List/Set/ZSet）。
2. **声明式缓存**：用 Spring Cache 注解（`@Cacheable` 等）让方法自动走 Redis 缓存，业务代码零侵入。

---

## 二、项目结构

```
demo-cache-redis/
└── src/main/java/com/xkcoding/cache/redis/
    ├── SpringBootDemoCacheRedisApplication.java   # 启动类
    ├── config/
    │   └── RedisConfig.java                        # Redis 配置（序列化 + CacheManager）
    ├── entity/
    │   └── User.java                               # 用户实体（实现 Serializable）
    └── service/
        ├── UserService.java                        # 服务接口
        └── impl/UserServiceImpl.java               # 实现（含 @Cacheable 等注解）
```

注意：本模块**没有 Controller**，因为重点是缓存机制，用单元测试验证即可。真实项目里会在 Controller 调 Service，Service 走缓存。

---

## 三、逐行拆解 pom.xml

```xml
<!-- 1. 基础起步依赖（不含 Web，因为不需要 HTTP 接口） -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter</artifactId>
</dependency>

<!-- 2. Redis 起步依赖（核心） -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-data-redis</artifactId>
</dependency>

<!-- 3. 对象池，使用 redis 时必须引入 -->
<dependency>
    <groupId>org.apache.commons</groupId>
    <artifactId>commons-pool2</artifactId>
</dependency>

<!-- 4. Jackson，用于 JSON 序列化 -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-json</artifactId>
</dependency>
```

### 3.1 `spring-boot-starter-data-redis` 引入了什么？

这个 Starter 会自动引入：
- **Spring Data Redis**：提供 `RedisTemplate`、`StringRedisTemplate` 等高层抽象 API。
- **Redis 客户端驱动**：Spring Boot 2.0+ 默认用 **Lettuce**（基于 Netty，线程安全，支持同步/异步/响应式），而不是老牌的 Jedis。

> 💡 前端类比：`RedisTemplate` 相当于 axios——一个封装了底层 HTTP 的客户端。底层驱动（Lettuce/Jedis）相当于 fetch/XHR 的区别，上层 API 不变。

### 3.2 为什么必须引 `commons-pool2`？

Lettuce 默认用单连接（共享一个 TCP 连接，靠 Netty 多路复用）。如果要启用**连接池**（多个 TCP 连接复用，提升并发），需要 `commons-pool2` 提供的 `GenericObjectPool`。配了 `lettuce.pool.*` 就必须引它，否则启动报错。

### 3.3 为什么引 `spring-boot-starter-json`？

因为我们要用 `GenericJackson2JsonRedisSerializer` 把对象序列化成 JSON 存进 Redis，它依赖 Jackson。这个 Starter 一次性把 Jackson 全家桶引入。

---

## 四、逐行拆解配置文件 application.yml

```yaml
spring:
  redis:
    host: localhost              # Redis 服务器地址
    # database: 0                # Redis 默认 16 个库（0-15），用 database 切换
    timeout: 10000ms             # 连接超时时间（必须带单位 ms）
    lettuce:                     # Lettuce 连接池配置
      pool:
        max-active: 8            # 最大连接数（默认 8）
        max-wait: -1ms           # 获取连接最大等待时间（-1 表示无限等待）
        max-idle: 8              # 最大空闲连接
        min-idle: 0              # 最小空闲连接
  cache:
    type: redis                  # 指定 Spring Cache 用 Redis 实现
logging:
  level:
    com.xkcoding: debug          # 开启 debug 日志，方便看缓存命中
```

### 4.1 关键配置项

| 配置项 | 作用 | 默认值 |
| --- | --- | --- |
| `spring.redis.host` | Redis 服务器地址 | localhost |
| `spring.redis.port` | 端口 | 6379 |
| `spring.redis.password` | 密码（生产必设） | 无 |
| `spring.redis.database` | 库编号（0-15） | 0 |
| `spring.redis.timeout` | 连接超时 | 2000ms |
| `spring.redis.lettuce.pool.*` | 连接池参数 | 见上 |

### 4.2 `spring.cache.type: redis` 的意义

Spring Cache 是一个**缓存抽象**（接口），它不绑定具体实现。`spring.cache.type=redis` 告诉 Spring："用 Redis 作为 Spring Cache 的底层实现"。其实不写也行——Spring Boot 会根据 classpath 上的依赖自动判断（有 Redis 就用 Redis）。显式写上更清晰。

> 💡 这就是 `demo-cache-ehcache` 里 `@Cacheable` 能生效的原因——同一套注解，换个依赖就换底层实现。Spring Cache 是"门面"，Redis/Ehcache/Caffeine 是"实现"。

### 4.3 Duration 写法注意

`timeout: 10000ms` 必须带单位。Spring Boot 2.0+ 用 `Duration` 类型解析，支持 `ms`/`s`/`m`/`h`/`d`。写成 `10000` 会按毫秒解析，但 `timeout: 10s` 更易读。这是和前端 `setTimeout(fn, 10000)` 不同的地方——前端默认毫秒，后端要求显式单位。

---

## 五、逐行拆解 RedisConfig.java（核心配置类）

```java
@Configuration
@AutoConfigureAfter(RedisAutoConfiguration.class)
@EnableCaching
public class RedisConfig {

    @Bean
    public RedisTemplate<String, Serializable> redisCacheTemplate(LettuceConnectionFactory redisConnectionFactory) {
        RedisTemplate<String, Serializable> template = new RedisTemplate<>();
        template.setKeySerializer(new StringRedisSerializer());
        template.setValueSerializer(new GenericJackson2JsonRedisSerializer());
        template.setConnectionFactory(redisConnectionFactory);
        return template;
    }

    @Bean
    public CacheManager cacheManager(RedisConnectionFactory factory) {
        RedisCacheConfiguration config = RedisCacheConfiguration.defaultCacheConfig();
        RedisCacheConfiguration redisCacheConfiguration = config
            .serializeKeysWith(RedisSerializationContext.SerializationPair.fromSerializer(new StringRedisSerializer()))
            .serializeValuesWith(RedisSerializationContext.SerializationPair.fromSerializer(new GenericJackson2JsonRedisSerializer()));
        return RedisCacheManager.builder(factory).cacheDefaults(redisCacheConfiguration).build();
    }
}
```

### 5.1 三个类级注解

- `@Configuration`：标记为配置类，里面的 `@Bean` 方法会被 Spring 调用，产出 Bean 注册进容器。
- `@AutoConfigureAfter(RedisAutoConfiguration.class)`：让本配置类在 Spring Boot 自动配置的 `RedisAutoConfiguration` **之后**加载。因为本类的 `redisCacheTemplate` 依赖 `LettuceConnectionFactory`，而它由 `RedisAutoConfiguration` 创建——必须保证先有连接工厂，再配模板。
- `@EnableCaching`：**开启 Spring Cache 注解支持**。没有它，`@Cacheable` 等注解不生效。这是声明式缓存的总开关。

### 5.2 `redisCacheTemplate`：自定义 RedisTemplate

Spring Boot 自动配置的 `RedisTemplate` 默认用 **JDK 序列化**（`JdkSerializationRedisSerializer`），存进 Redis 的值是一串乱码二进制，用 `redis-cli` 看不懂、跨语言也无法读。本模块自定义一个用 JSON 序列化的模板：

- **Key 序列化**：`StringRedisSerializer`——key 用普通字符串，可读性好（如 `user:1`）。
- **Value 序列化**：`GenericJackson2JsonRedisSerializer`——value 存成 JSON，可读、跨语言、带类型信息。
- **连接工厂**：注入 `LettuceConnectionFactory`，复用 Spring Boot 自动配的连接池。

> 💡 前端类比：默认的 JDK 序列化像 `btoa(serialize(obj))`——存的是 base64 二进制，人看不懂。换成 JSON 序列化就像 `JSON.stringify(obj)`——存的是明文 JSON，`{"id":1,"name":"user1"}`，谁都能读。

### 5.3 `cacheManager`：自定义 Spring Cache 的序列化

这个 Bean 专门给 Spring Cache 注解（`@Cacheable` 等）用。默认情况下，`@Cacheable` 存进 Redis 的值也是 JDK 二进制序列化。这里自定义 `RedisCacheManager`，让注解缓存也用 JSON 序列化，和 `RedisTemplate` 保持一致。

- `RedisCacheConfiguration.defaultCacheConfig()`：默认配置（含默认 TTL、key 前缀等）。
- `serializeKeysWith(...)` / `serializeValuesWith(...)`：分别设置 key 和 value 的序列化器。
- `RedisCacheManager.builder(factory).cacheDefaults(config).build()`：用连接工厂 + 配置构建 CacheManager。

> ⚠️ 注意区分两个 Bean 的职责：
> - `redisCacheTemplate`：给**手动操作 Redis** 的代码用（`redisTemplate.opsForValue().set(...)`）。
> - `cacheManager`：给**注解缓存**用（`@Cacheable` 等）。
> 
> 两者都要配 JSON 序列化，否则会出现"手动存的能读、注解存的读不出"或反过来。

### 5.4 序列化器对比

| 序列化器 | 存储格式 | 可读性 | 跨语言 | 带类型 | 适用 |
| --- | --- | --- | --- | --- | --- |
| `JdkSerializationRedisSerializer`（默认） | 二进制 | 差 | 否 | 是 | 不推荐 |
| `StringRedisSerializer` | 字符串 | 好 | 是 | 否 | Key |
| `GenericJackson2JsonRedisSerializer` | JSON | 好 | 是 | 是（带 `@class`） | Value |
| `Jackson2JsonRedisSerializer` | JSON | 好 | 是 | 否（需指定类型） | Value（类型固定时） |

`GenericJackson2JsonRedisSerializer` 会在 JSON 里加一个 `@class` 字段记录原始类型，反序列化时能自动还原成对应类——代价是体积稍大、且要求类能被类加载器找到。

---

## 六、逐行拆解实体类 User.java

```java
@Data
@AllArgsConstructor
@NoArgsConstructor
public class User implements Serializable {
    private static final long serialVersionUID = 2892248514883451461L;
    private Long id;
    private String name;
}
```

- `@Data` + `@AllArgsConstructor` + `@NoArgsConstructor`：Lombok 三件套，生成 getter/setter/构造器/toString 等。
- **`implements Serializable`**：实现 Java 序列化接口。即使我们用 JSON 序列化（不需要它），但作为缓存实体养成这个习惯——万一换成 JDK 序列化就靠它，否则会 `NotSerializableException`。
- `serialVersionUID`：序列化版本号，反序列化时校验类是否兼容。

> 💡 前端类比：`Serializable` 像给对象打上"可被序列化"的标记接口，类似 React 组件继承 `React.Component`——是个能力声明。实际序列化用 Jackson（JSON），这个接口更多是"以防万一"。

---

## 七、逐行拆解 UserService 与实现（声明式缓存核心）

### 7.1 接口 UserService.java

```java
public interface UserService {
    User saveOrUpdate(User user);
    User get(Long id);
    void delete(Long id);
}
```

标准的"增改 / 查 / 删"三方法。接口本身不带缓存注解——注解放在实现类上。

### 7.2 实现 UserServiceImpl.java

```java
@Service
@Slf4j
public class UserServiceImpl implements UserService {
    private static final Map<Long, User> DATABASES = Maps.newConcurrentMap();

    static {
        DATABASES.put(1L, new User(1L, "user1"));
        DATABASES.put(2L, new User(2L, "user2"));
        DATABASES.put(3L, new User(3L, "user3"));
    }

    @CachePut(value = "user", key = "#user.id")
    @Override
    public User saveOrUpdate(User user) {
        DATABASES.put(user.getId(), user);
        log.info("保存用户【user】= {}", user);
        return user;
    }

    @Cacheable(value = "user", key = "#id")
    @Override
    public User get(Long id) {
        log.info("查询用户【id】= {}", id);
        return DATABASES.get(id);
    }

    @CacheEvict(value = "user", key = "#id")
    @Override
    public void delete(Long id) {
        DATABASES.remove(id);
        log.info("删除用户【id】= {}", id);
    }
}
```

- `@Service`：注册成 Spring Bean，业务层。
- `DATABASES`：用 `ConcurrentMap` 模拟数据库（真实项目换成 Mapper/Repository 查 MySQL）。
- `@Slf4j`：Lombok 注入 `log` 对象，方便打日志验证缓存是否命中。

**三个缓存注解是本模块的灵魂：**

| 注解 | 作用 | 触发时机 | 典型方法 |
| --- | --- | --- | --- |
| `@Cacheable` | 查缓存，命中则直接返回，不执行方法；未命中则执行方法并存结果 | 方法执行**前** | `get` |
| `@CachePut` | 执行方法，把返回值存入缓存（不影响方法执行） | 方法执行**后** | `saveOrUpdate` |
| `@CacheEvict` | 执行方法后，删除缓存 | 方法执行**后** | `delete` |

**注解参数详解：**

- `value = "user"`：缓存名（命名空间），对应 Redis 的 key 前缀，最终 key 形如 `user::1`。
- `key = "#id"`：SpEL 表达式，`#id` 表示方法参数 `id` 的值。`#user.id` 表示参数 `user` 的 `id` 属性。

**执行流程（以 `get(1L)` 为例）：**

```
调用 userService.get(1)
    ↓
Spring AOP 拦截，查 Redis key = "user::1"
    ↓
命中？ ──是──→ 直接返回缓存值，方法体不执行（日志不打）
    │
    否
    ↓
执行 get 方法体，查"数据库"，返回 User
    ↓
Spring 把返回值存入 Redis（key="user::1"）
    ↓
返回给调用方
```

> 💡 前端类比：`@Cacheable` 像一个 memoize 高阶函数——
> ```js
> const get = memoize(async (id) => {
>   return await db.find(id)
> }, { key: id => `user::${id}`, store: redis })
> ```
> 只是 Spring 用注解声明，不用手写高阶函数。**关键是它基于 AOP 代理**——只有通过 Spring 容器拿到的 Bean 调用才生效，类内部 `this.get()` 不走代理，缓存失效（经典坑，见后文）。

---

## 八、逐行拆解测试类

### 8.1 基类 SpringBootDemoCacheRedisApplicationTests

```java
@RunWith(SpringRunner.class)
@SpringBootTest
public class SpringBootDemoCacheRedisApplicationTests {
    @Test
    public void contextLoads() {
    }
}
```

所有测试类继承它，复用 `@RunWith` + `@SpringBootTest`，不用每个测试类都写一遍。

### 8.2 RedisTest：直接操作 Redis 数据结构

```java
@Autowired
private StringRedisTemplate stringRedisTemplate;

@Autowired
private RedisTemplate<String, Serializable> redisCacheTemplate;

@Test
public void get() {
    // 1. 测试线程安全：1000 个线程并发自增 count
    ExecutorService executorService = Executors.newFixedThreadPool(1000);
    IntStream.range(0, 1000).forEach(i -> 
        executorService.execute(() -> stringRedisTemplate.opsForValue().increment("count", 1)));

    // 2. 简单存取字符串
    stringRedisTemplate.opsForValue().set("k1", "v1");
    String k1 = stringRedisTemplate.opsForValue().get("k1");

    // 3. 存取对象（用自定义的 JSON 序列化模板）
    String key = "xkcoding:user:1";
    redisCacheTemplate.opsForValue().set(key, new User(1L, "user1"));
    User user = (User) redisCacheTemplate.opsForValue().get(key);
}
```

**两个模板的区别：**

| 模板 | Key/Value 类型 | 序列化 | 用途 |
| --- | --- | --- | --- |
| `StringRedisTemplate` | `String/String` | StringRedisSerializer | 存纯字符串、计数器 |
| `RedisTemplate<String,Serializable>` | `String/Serializable` | 自定义 JSON | 存对象 |

**`opsForXxx()` 对应 Redis 数据结构：**

| 方法 | Redis 类型 | 常用命令 | 前端类比 |
| --- | --- | --- | --- |
| `opsForValue()` | String | SET/GET/INCR | 一个 key 对应一个值，像 localStorage 的键值 |
| `opsForHash()` | Hash | HSET/HGET/HMSET | 像一个 JS 对象 `{field: value}` |
| `opsForList()` | List | LPUSH/RPOP | 像数组，可做队列 |
| `opsForSet()` | Set | SADD/SMEMBERS | 像无序去重数组 |
| `opsForZSet()` | Sorted Set | ZADD/ZRANGE | 带分数的有序集合，做排行榜 |
| `opsForGeo()` | Geo | GEOADD/GEOPOS | 存经纬度，做"附近的人" |

`increment("count", 1)` 是原子操作——1000 个线程并发自增，最终 `count` 精确等于 1000。这体现了 Redis 单线程命令的原子性，比数据库行锁高效得多。

### 8.3 UserServiceTest：验证声明式缓存

```java
@Test
public void getTwice() {
    User user1 = userService.get(1L);   // 第一次：未命中，执行方法，打日志
    User user2 = userService.get(1L);   // 第二次：命中缓存，不执行方法，无日志
    // 看日志只打一次"查询用户"，证明缓存生效
}

@Test
public void getAfterSave() {
    userService.saveOrUpdate(new User(4L, "测试中文"));  // @CachePut 存入缓存
    User user = userService.get(4L);   // 命中刚存的缓存，不查"数据库"
}

@Test
public void deleteUser() {
    userService.get(1L);      // 先让缓存有数据
    userService.delete(1L);  // @CacheEvict 删除缓存
}
```

这三个测试覆盖了缓存生命周期的三个动作：读命中/未命中、写更新、删除。通过观察日志打印次数验证缓存是否生效——这是最直观的验证方式。

---

## 九、运行与验证

### 9.1 前置条件

需要本地启动一个 Redis 服务（默认端口 6379，无密码）。可以用 Docker：

```sh
docker run -d --name redis -p 6379:6379 redis:6
```

### 9.2 运行测试

```sh
mvn test
```

观察控制台日志：
- `RedisTest.get()`：能看到 `count` 自增、`k1` 存取、`user` 对象存取。
- `UserServiceTest.getTwice()`：`查询用户【id】= 1` 只打印一次，第二次走缓存无日志。
- `UserServiceTest.getAfterSave()`：只打印"保存用户"日志，查询未触发日志。

### 9.3 用 redis-cli 验证

测试后连进 Redis 看实际存储：

```sh
redis-cli
> keys *                  # 查看所有 key
> get "user::1"           # 看注解缓存存的值（JSON 格式）
> get "xkcoding:user:1"   # 看 RedisTemplate 存的对象
> get count               # 看 1000 次自增的结果
```

你会看到 `user::1` 的值是 `{"@class":"com.xkcoding.cache.redis.entity.User","id":1,"name":"user1"}`——带 `@class` 类型信息的 JSON，这就是 `GenericJackson2JsonRedisSerializer` 的效果。

---

## 十、动手练习

1. **加 TTL（过期时间）**：在 `RedisConfig` 的 `cacheManager` 里给缓存配默认过期时间 `.entryTtl(Duration.ofMinutes(30))`，测试后用 `redis-cli` 用 `TTL user::1` 看剩余存活秒数。
2. **换 key 前缀**：用 `.prefixCacheNameWith("myapp:")` 给所有缓存 key 加前缀，观察 Redis 里 key 变成 `myapp:user::1`。
3. **存 Hash**：在 `RedisTest` 里用 `redisCacheTemplate.opsForHash().put("user:1", "name", "user1")` 存 Hash，用 `redis-cli HGETALL user:1` 验证。
4. **做排行榜**：用 `opsForZSet().add("rank", "user1", 100)` 存分数，再 `reverseRangeByScore` 查排名，模拟游戏积分榜。
5. **制造缓存穿透**：在 `get` 方法上观察——查一个数据库和缓存都不存在的 id（如 999），每次都打数据库。思考如何用 `@Cacheable(condition = "#id > 0")` 或缓存空值解决。
6. **验证自调用失效**：在 `UserServiceImpl` 里加一个方法 `public void test() { this.get(1L); }`，外部调 `test()` 时观察——`get` 的缓存注解**不生效**（因为 `this` 不走代理）。这是 AOP 缓存最经典的坑。

---

## 十一、本模块知识点总结（结合实际开发详解）

Redis 缓存是后端性能优化的第一利器，但用不好会引入数据不一致、缓存穿透等生产事故。下面把核心知识点放到真实开发场景里讲透。

### 11.1 RedisTemplate vs Spring Cache 注解：怎么选？

**实际开发中两种用法并存，职责不同：**

| 维度 | `RedisTemplate`（手动） | Spring Cache 注解（声明式） |
| --- | --- | --- |
| 控制粒度 | 精细，能操作所有 Redis 数据结构 | 粗粒度，方法级缓存 |
| 业务侵入 | 有侵入（要写 Redis 代码） | 零侵入（加注解即可） |
| 灵活性 | 高（TTL、批量、Lua 脚本都行） | 低（受注解参数限制） |
| 适用场景 | 计数器、排行榜、分布式锁、消息队列 | 实体查询缓存、配置缓存 |

**最佳实践：**
- **方法级缓存**（查实体、查配置）→ 用 `@Cacheable` 注解，业务代码干净。
- **复杂数据结构**（排行榜用 ZSet、计数器用 INCR、队列用 List）→ 用 `RedisTemplate` 手动操作。
- 两者可以共存——注解缓存走 `CacheManager`，手动操作走 `RedisTemplate`，只要序列化配置一致即可。

**常见坑：** 新手用注解缓存存了对象，又用 `RedisTemplate` 去读，发现读不出或类型错乱——原因是两者的序列化器不一致。**统一序列化是关键**，本模块的 `RedisConfig` 同时配了两者用 JSON，就是为此。

### 11.2 序列化方案：为什么默认的 JDK 序列化不能用？

Spring Boot 自动配置的 `RedisTemplate` 默认用 `JdkSerializationRedisSerializer`，存进 Redis 的是二进制乱码。这带来三个问题：

1. **不可读**：`redis-cli` 看到的是 `\xac\xed...`，排查问题极困难。
2. **跨语言障碍**：Python/Go/Node 服务读不了 Java 的 JDK 序列化格式。
3. **体积大**：JDK 序列化带大量类信息，比 JSON 大 30%-50%。

**实际开发推荐方案：**
- **Key**：永远用 `StringRedisSerializer`（key 是字符串，可读、可统计）。
- **Value**：
  - 存对象 → `GenericJackson2JsonRedisSerializer`（带类型，自动还原）或 `Jackson2JsonRedisSerializer`（需指定类型，体积小）。
  - 存纯字符串/数字 → `StringRedisSerializer`。

**常见坑：**
- 用 `GenericJackson2JsonRedisSerializer` 存的对象，后来改了包名/类名，反序列化报 `ClassNotFoundException`——因为 JSON 里的 `@class` 指向旧类名。**解法**：保留旧类或迁移数据。
- 存嵌套对象集合时，`GenericJackson2JsonRedisSerializer` 会给每个元素加 `@class`，体积膨胀。**解法**：类型固定时用 `Jackson2JsonRedisSerializer<T>` 指定类型。

### 11.3 连接池：Lettuce vs Jedis

Spring Boot 2.0+ 默认用 **Lettuce**，而非 Jedis。两者对比：

| 维度 | Lettuce（默认） | Jedis |
| --- | --- | --- |
| 线程安全 | 是（基于 Netty，单连接多线程复用） | 否（需连接池） |
| 连接模型 | 共享一个连接，多路复用 | 每线程一个连接 |
| 异步/响应式 | 支持 | 不支持 |
| 性能 | 高 | 中 |

**实际开发建议：** 直接用默认的 Lettuce，不要切 Jedis。Lettuce 的连接池（`lettuce.pool.*`）只在需要大量并发短命令时才开——默认单连接多路复用对多数场景已够用。

**常见坑：**
- 配了 `lettuce.pool.*` 却没引 `commons-pool2`，启动报 `Cannot resolve`——必须引依赖。
- Lettuce 默认连接不主动保活，长时间空闲可能被防火墙断开。**解法**：配 `spring.redis.lettuce.shutdown-timeout` 或开启 `keep-alive`。

### 11.4 缓存一致性：三大经典问题

这是 Redis 缓存在生产环境最棘手的问题——数据库和缓存是两个系统，怎么保证数据一致？

**问题一：缓存穿透**——查一个根本不存在的 key，每次都打数据库（缓存永远不命中）。
- **场景**：恶意攻击，用大量不存在的 id 查询。
- **解法**：缓存空值（`@Cacheable` 命中 null 也存）、布隆过滤器拦截。

**问题二：缓存击穿**——某个热点 key 过期瞬间，大量请求同时打数据库。
- **场景**：秒杀商品的缓存突然过期。
- **解法**：加互斥锁（只让一个线程查库，其他等待）、热点 key 永不过期（后台异步刷新）。

**问题三：缓存雪崩**——大量 key 同时过期，或 Redis 宕机，请求全压数据库。
- **场景**：缓存批量设置了相同 TTL，同时失效。
- **解法**：TTL 加随机扰动（`30min + random(10min)`）、Redis 集群高可用、数据库限流降级。

**数据库-缓存一致性策略：**
- **Cache Aside（旁路缓存，最常用）**：读时先查缓存，未命中查库并回填；写时先更新库再删缓存。
- 为什么是"删缓存"而非"更新缓存"？——避免并发下旧值覆盖新值。删了下次读自然会重新加载。
- `@CachePut` 是"更新缓存"，`@CacheEvict` 是"删缓存"——写操作推荐用 `@CacheEvict`（删），而非 `@CachePut`（更新），更符合 Cache Aside。

> 💡 前端类比：缓存一致性像 React 的 `useMemo` 依赖数组——依赖变了缓存就失效。但后端是分布式，没有 React 那种"自动追踪依赖"的机制，得靠策略保证。

### 11.5 `@Cacheable` 的 AOP 陷阱：自调用失效

这是新手必踩的坑：**同一个类内部方法互相调用，缓存注解不生效。**

```java
@Service
public class UserServiceImpl {
    @Cacheable(value = "user", key = "#id")
    public User get(Long id) { ... }

    public void test() {
        this.get(1L);   // ❌ 缓存不生效！
    }
}
```

**原因：** Spring Cache 基于 AOP 代理。外部调用 `userService.get()` 时，走的是代理对象，代理拦截后查缓存；但类内部 `this.get()` 是直接调用原始对象，绕过了代理，注解不生效。

**解法：**
1. 把方法拆到不同类（推荐，符合单一职责）。
2. 注入自身代理：`@Autowired private UserService self;` 然后 `self.get(1L)`。
3. 用 `AopContext.currentProxy()` 拿当前代理（需开启 `@EnableAspectJAutoProxy(exposeProxy = true)`）。

**最佳实践：** 缓存注解只放在"被外部调用"的公开方法上，不要依赖类内自调用。这也是为什么推荐把缓存方法放 Service 层入口，内部辅助方法不加注解。

### 11.6 缓存 key 设计与命名规范

Redis 是单 key 查找的，key 设计直接影响性能和可维护性。

**命名规范：** 用冒号 `:` 分隔层级，业务名打头，形成命名空间：

```
myapp:user:1            # 业务:实体:ID
myapp:user:1:name       # 单独存某个字段
myapp:rank:daily         # 业务:用途
```

Redis 会把 `:` 当作目录分隔符（在 Redis Cluster 和某些客户端里按 `:` 分槽位），`keys user:*` 也能按前缀模糊查。

**`@Cacheable` 的 key 设计：**
- `key = "#id"`：用方法参数。
- `key = "#user.id"`：用参数对象的属性。
- `key = "#root.methodName + ':' + #id"`：方法名 + 参数（避免不同方法 key 冲突）。
- 不写 `key`：默认用参数拼接，但建议显式写，更可控。

**常见坑：**
- 不同业务用了相同 `value` 和 `key`，缓存互相覆盖。**解法**：`value` 用业务名隔离命名空间。
- key 太长（如把整个对象序列化当 key），浪费内存且查询慢。**解法**：用 id 等短标识。
- 大量 key 用 `keys *` 模糊查，阻塞 Redis（单线程，O(N) 阻塞）。**解法**：用 `SCAN` 迭代查，或维护一个 key 集合。

### 11.7 生产环境 Redis 配置清单

实际项目上线时，`application.yml` 至少要配齐这些：

```yaml
spring:
  redis:
    host: ${REDIS_HOST:localhost}        # 用环境变量，不硬编码
    port: 6379
    password: ${REDIS_PASSWORD}         # 生产必设密码
    database: 0
    timeout: 5s                         # 超时别太长，避免线程阻塞
    lettuce:
      pool:
        max-active: 16                  # 根据并发调，别用默认 8
        max-idle: 8
        min-idle: 2
        max-wait: 3s                   # 获取连接等待上限，超时抛异常而非死等
      shutdown-timeout: 100ms
  cache:
    type: redis
```

**最佳实践：**
- 密码、地址用环境变量注入，不进 git。
- `max-active` 根据并发量调（默认 8 在高并发下不够）。
- `max-wait` 设上限，避免获取不到连接时无限等待拖垮服务。
- 生产用 Redis 集群（主从/哨兵/Cluster），单点 Redis 是隐患。
- 监控缓存命中率（用 Actuator 或 Redis 自带 `INFO stats`），低于 90% 要排查。

---

> 📌 **学习建议**：Redis 是后端工程师的必备技能，远不止"缓存"一个用途——分布式锁、排行榜、限流、消息队列、会话存储都靠它。建议先把本模块的两种用法（RedisTemplate 手动操作 + Spring Cache 注解）都跑通，重点理解**序列化**和**缓存一致性**这两个生产事故高发点。后续模块（`demo-session` 分布式 Session、`demo-ratelimit-redis` 分布式限流、`demo-zookeeper` 对比分布式锁）会反复用到 Redis，这里打牢基础很重要。另外养成习惯：**任何缓存都要设 TTL**，不设过期时间的缓存是内存炸弹。
