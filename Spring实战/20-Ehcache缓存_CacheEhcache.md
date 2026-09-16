# 20 - Spring Boot 集成 Ehcache 缓存

> 对应项目模块：`demo-cache-ehcache`
> 前置知识：已学完 01-19（尤其建议先看 `19-Redis缓存_CacheRedis`，因为本模块和它高度对称，只是缓存实现换成了本地 Ehcache）
> 学习目标：理解 Spring Cache 抽象的"实现可插拔"思想，掌握 Ehcache 的配置与磁盘持久化，能独立为 Service 方法加缓存。

---

## 一、本模块要解决什么问题？

上一篇 Redis 缓存用**远程缓存**（数据存在独立的 Redis 进程里），适合分布式系统。但有些场景用**本地缓存**（数据存在应用自己进程的内存里）更合适：

- 数据量不大、读极其频繁（如字典表、配置项）——本地内存访问比网络往返快几个数量级。
- 单体应用、不需要多节点共享缓存。
- 不想引入 Redis 这个额外组件，想"零外部依赖"地加缓存。

Ehcache 就是 Java 生态最经典的本地缓存框架。它支持堆内内存、堆外内存、磁盘三级存储，还能配置过期策略、淘汰算法。本模块演示用 Spring Cache 抽象 + Ehcache 实现，**和 Redis 那篇的代码几乎一模一样**——这正是 Spring Cache 抽象的价值：换实现不用改业务代码。

---

## 二、项目结构

```
demo-cache-ehcache/
├── pom.xml
└── src/main/
    ├── java/com/xkcoding/cache/ehcache/
    │   ├── SpringBootDemoCacheEhcacheApplication.java   # 启动类（@EnableCaching）
    │   ├── entity/
    │   │   └── User.java                                # 实体（实现 Serializable）
    │   └── service/
    │       ├── UserService.java                          # 接口
    │       └── impl/UserServiceImpl.java                # 实现（@Cacheable/@CachePut/@CacheEvict）
    └── resources/
        ├── application.yml                               # 指定 cache type=ehcache
        └── ehcache.xml                                  # Ehcache 详细配置
```

对比 Redis 那篇，结构几乎一致，区别只在：启动类多了 `@EnableCaching`、配置文件多了 `ehcache.xml`、pom 换成了 Ehcache 依赖。**业务代码（UserService）一个字都没改**——这就是 Spring Cache 抽象的威力。

---

## 三、pom.xml 依赖拆解

```xml
<!-- 1. 基础起步依赖（不含 web，本模块用测试验证，不需要启动 Web 服务器） -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter</artifactId>
</dependency>

<!-- 2. Spring Cache 抽象支持（提供 @Cacheable 等注解和 CacheManager 接口） -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-cache</artifactId>
</dependency>

<!-- 3. Ehcache 实现（真正的缓存引擎） -->
<dependency>
    <groupId>net.sf.ehcache</groupId>
    <artifactId>ehcache</artifactId>
</dependency>

<!-- 4. Lombok、Guava（Maps.newConcurrentMap）、test -->
<dependency>
    <groupId>org.projectlombok</groupId>
    <artifactId>lombok</artifactId>
    <optional>true</optional>
</dependency>
<dependency>
    <groupId>com.google.guava</groupId>
    <artifactId>guava</artifactId>
</dependency>
```

**关键理解：Spring Cache 是"抽象"，Ehcache 是"实现"。**

- `spring-boot-starter-cache` 只提供注解（`@Cacheable` 等）和 `CacheManager` 接口，本身不存数据。
- `ehcache` 才是真正存数据的引擎。
- 启动时 Spring Boot 根据 `spring.cache.type=ehcache` 自动把 Ehcache 注册成 `CacheManager` 的实现。

> 💡 前端类比：这像 Vue 的"响应式系统抽象"——Vue 2 用 `Object.defineProperty`，Vue 3 用 `Proxy`，业务代码不变。Spring Cache 抽象 = 接口约定，Ehcache/Redis/Caffeine = 不同实现，可插拔。

---

## 四、启动类：`@EnableCaching`

```java
@SpringBootApplication
@EnableCaching
public class SpringBootDemoCacheEhcacheApplication {
    public static void main(String[] args) {
        SpringApplication.run(SpringBootDemoCacheEhcacheApplication.class, args);
    }
}
```

`@EnableCaching` 是开启缓存支持的开关。它的作用：

1. 注册缓存相关的后处理器，扫描 `@Cacheable`、`@CachePut`、`@CacheEvict` 注解。
2. 用 AOP 代理被注解的方法，在方法调用前后介入缓存逻辑。

不加 `@EnableCaching`，所有缓存注解都不生效——这是新手最常踩的坑。它和 Redis 那篇完全一样。

---

## 五、配置文件

### 5.1 `application.yml`

```yaml
spring:
  cache:
    type: ehcache          # 指定缓存实现为 ehcache
    ehcache:
      config: classpath:ehcache.xml   # 指定 ehcache 配置文件位置
logging:
  level:
    com.xkcoding: debug    # 开启 debug 日志，方便观察缓存是否命中
```

`spring.cache.type` 可选值：`simple`（默认内存 Map）、`ehcache`、`redis`、`caffeine`、`none`（关闭）。指定 `ehcache` 后，Spring Boot 自动用 `EhCacheCacheManager`。

### 5.2 `ehcache.xml`（Ehcache 引擎自己的配置）

```xml
<ehcache xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:noNamespaceSchemaLocation="http://ehcache.org/ehcache.xsd"
         updateCheck="false">

    <!-- 磁盘存储路径：用户目录下的 base_ehcache 目录 -->
    <diskStore path="user.home/base_ehcache"/>

    <!-- 默认缓存策略（未显式配置的 cache 名都用这个） -->
    <defaultCache
            maxElementsInMemory="20000"      <!-- 内存最多存 2 万个元素 -->
            eternal="false"                   <!-- 是否永久有效（false=会过期） -->
            timeToIdleSeconds="120"           <!-- 空闲 120 秒未访问则过期 -->
            timeToLiveSeconds="120"           <!-- 存活 120 秒后过期 -->
            overflowToDisk="true"             <!-- 内存满了溢出到磁盘 -->
            maxElementsOnDisk="10000000"      <!-- 磁盘最多 1000 万个 -->
            diskPersistent="false"            <!-- 重启后磁盘缓存是否保留 -->
            diskExpiryThreadIntervalSeconds="120"  <!-- 磁盘过期检查间隔 -->
            memoryStoreEvictionPolicy="LRU"/>  <!-- 内存淘汰策略：最近最少使用 -->

    <!-- 名为 user 的缓存（@Cacheable(value="user") 用到它） -->
    <cache name="user"
           maxElementsInMemory="20000"
           eternal="true"                     <!-- user 缓存设为永久有效 -->
           overflowToDisk="true"
           diskPersistent="false"
           timeToLiveSeconds="0"              <!-- 0 配合 eternal=true 表示不过期 -->
           diskExpiryThreadIntervalSeconds="120"/>
</ehcache>
```

**关键参数详解：**

| 参数 | 含义 | 前端类比 |
| --- | --- | --- |
| `maxElementsInMemory` | 内存中最多存多少元素，超出按淘汰策略删 | 类似 Map 设了 maxSize |
| `eternal` | true=永不过期；false=按时间过期 | 类似 localStorage（永久）vs sessionStorage（会话级） |
| `timeToIdleSeconds` | 对象空闲多久没被访问就过期（TTI） | 类似"多久没用就清掉" |
| `timeToLiveSeconds` | 对象存活多久就过期（TTL），不管有没有被访问 | 类似"绝对过期时间" |
| `overflowToDisk` | 内存满了是否溢出到磁盘 | 类似内存满了写文件 |
| `memoryStoreEvictionPolicy` | 淘汰算法：LRU（最近最少用）、LFU（最少用次数）、FIFO（先进先出） | 类似前端 LRU 缓存库的策略 |

> ⚠️ `eternal="true"` 时，`timeToIdleSeconds` 和 `timeToLiveSeconds` 会被忽略（永不过期）。本模块的 `user` 缓存设了 `eternal="true"`，所以缓存永不过期，只能靠 `@CacheEvict` 主动删除。

---

## 六、实体类：必须实现 `Serializable`

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

**为什么 Ehcache 要求 `Serializable`？** 因为 Ehcache 的 `overflowToDisk=true` 会把内存放不下的对象写到磁盘，写磁盘需要把对象序列化成字节。Redis 那篇也要求序列化，但那是给 Redis 用的（Redis 自己有序列化机制），Ehcache 这里是给磁盘存储用的。

> 💡 前端类比：类似要把对象存进 `localStorage` 必须先 `JSON.stringify`，因为存储只认字符串/字节。Java 序列化是对象→字节的转换。

---

## 七、Service 层：三个核心缓存注解

`UserServiceImpl` 和 Redis 那篇**完全一样**，这里再讲一遍，重点放在和 Ehcache 的配合：

```java
@Service
@Slf4j
public class UserServiceImpl implements UserService {
    // 模拟数据库
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

### 三个注解回顾

| 注解 | 作用 | 执行时机 |
| --- | --- | --- |
| `@Cacheable` | 查询时先查缓存，命中就返回；没命中才执行方法，结果存入缓存 | 方法执行**前** |
| `@CachePut` | 执行方法，把返回值更新到缓存（不影响方法执行） | 方法执行**后** |
| `@CacheEvict` | 删除缓存中的对应数据 | 方法执行**后**（默认） |

- `value = "user"`：缓存名，对应 `ehcache.xml` 里的 `<cache name="user">`。
- `key = "#id"`：SpEL 表达式，用方法参数 `id` 的值作为缓存 key。
- `key = "#user.id"`：用参数 `user` 对象的 `id` 字段作为 key。

### 缓存命中流程（以 `get(1L)` 为例）

1. 第一次调用 `get(1L)`：缓存里没有 key=`1`，执行方法体（打印"查询用户"日志，查"数据库"），返回结果被存入 Ehcache。
2. 第二次调用 `get(1L)`：缓存里有 key=`1`，直接返回缓存值，**不执行方法体**（没有"查询用户"日志）。

---

## 八、测试类：验证缓存生效

```java
@Slf4j
public class UserServiceTest extends SpringBootDemoCacheEhcacheApplicationTests {

    @Autowired
    private UserService userService;

    @Test
    public void getTwice() {
        User user1 = userService.get(1L);   // 第一次：执行方法，打印日志
        log.debug("【user1】= {}", user1);

        User user2 = userService.get(1L);   // 第二次：命中缓存，不打印日志
        log.debug("【user2】= {}", user2);
    }

    @Test
    public void getAfterSave() {
        userService.saveOrUpdate(new User(4L, "user4"));  // @CachePut 把 user4 存入缓存
        User user = userService.get(4L);                   // 命中缓存，不打印查询日志
        log.debug("【user】= {}", user);
    }

    @Test
    public void deleteUser() {
        userService.get(1L);      // 先查，让缓存里有 key=1
        userService.delete(1L);   // @CacheEvict 删除缓存 key=1
    }
}
```

验证思路和 Redis 那篇一致：通过观察日志里"查询用户"是否打印来判断缓存是否命中。`getTwice` 只打印一次查询日志，证明第二次走缓存。

---

## 九、运行与验证

本模块没有 Web 接口（pom 没引 `spring-boot-starter-web`），用单元测试验证：

```sh
cd demo-cache-ehcache
mvn test
```

观察控制台日志：
- `getTwice`：只出现一次 `查询用户【id】= 1`，第二次查询无此日志 → 缓存命中。
- `getAfterSave`：只有 `保存用户` 日志，没有 `查询用户` 日志 → `@CachePut` 写入缓存后，查询直接命中。
- 同时会在用户目录下生成 `base_ehcache` 文件夹（磁盘存储溢出时）。

---

## 十、动手练习

1. **改过期时间**：把 `ehcache.xml` 里 `user` 缓存的 `eternal` 改成 `false`，`timeToLiveSeconds` 设为 `5`（秒），测试连续两次 `get` 间隔超过 5 秒，观察第二次是否重新执行方法（缓存过期了）。
2. **改淘汰策略**：把 `memoryStoreEvictionPolicy` 从 `LRU` 改成 `LFU`，思考两者区别。
3. **体验磁盘溢出**：把 `maxElementsInMemory` 改成 `2`，插入 5 个用户，观察 `user.home/base_ehcache` 目录是否生成磁盘文件。
4. **对比 Redis**：把本模块的 Ehcache 依赖换成 Redis（参考 19 篇），业务代码不动，验证"实现可插拔"。
5. **故意不实现 Serializable**：把 `User` 的 `implements Serializable` 去掉，开启 `overflowToDisk=true`，观察磁盘溢出时报错（理解序列化的必要性）。

---

## 十一、本模块知识点总结（结合实际开发详解）

缓存是提升性能的关键手段，Ehcache 是本地缓存的代表。下面把核心知识点放到真实开发场景里讲透。

### 11.1 Spring Cache 抽象：实现可插拔的精髓

**实际开发中怎么用？**

Spring Cache 定义了一套统一的缓存抽象（`CacheManager` 接口 + `@Cacheable` 等注解），业务代码只面向抽象，具体实现可切换：

| 实现 | 特点 | 适用场景 |
| --- | --- | --- |
| `simple` | 内存 ConcurrentHashMap | 演示、极简场景 |
| `ehcache` | 堆内+堆外+磁盘，功能全 | 单体应用本地缓存 |
| `caffeine` | 纯内存，性能极高（推荐替代 Ehcache） | 高性能本地缓存 |
| `redis` | 远程分布式缓存 | 微服务、多节点共享 |

**最佳实践：**

1. **业务代码只写注解，不绑定具体实现**：`@Cacheable(value="user", key="#id")` 不含任何 Ehcache/Redis 专属代码，换实现只改 pom 和 yml。
2. **按场景选实现**：单体应用用 Caffeine/Ehcache（本地快）；分布式用 Redis（共享）；混合用"本地+远程"多级缓存。
3. **缓存名要和配置对应**：`@Cacheable(value="user")` 的 `user` 必须在 `ehcache.xml` 里有 `<cache name="user">`，否则用 `defaultCache` 默认策略。

**常见坑：**

- 引了 Ehcache 依赖但没在 yml 指定 `spring.cache.type=ehcache`，Spring Boot 可能用默认的 `simple`，导致 `ehcache.xml` 不生效。
- 换实现时忘了清旧缓存数据（比如从 Redis 换 Ehcache，Redis 里残留的旧 key 不会自动清，但因为是不同 CacheManager，其实互不影响——这里更多是认知澄清）。

### 11.2 Ehcache 的三级存储：堆内→堆外→磁盘

**实际开发中怎么用？**

Ehcache 支持三级存储，按成本从低到高、速度从快到慢：

1. **堆内内存（On-Heap）**：最快，受 GC 影响，容量受 JVM 堆限制。
2. **堆外内存（Off-Heap）**：不受 GC 管理，需手动管理内存，速度略慢于堆内但远快于磁盘。
3. **磁盘（Disk）**：最慢但容量大，重启后是否保留看 `diskPersistent`。

**最佳实践：**

- 热点数据放堆内，温数据放堆外，冷数据落磁盘。
- `overflowToDisk=true` 让内存满了自动溢出，避免 OOM。
- 生产环境慎用 `diskPersistent=true`（重启保留），因为重启后数据结构可能和应用版本不匹配，反而出问题。

**常见坑：**

- 堆内缓存过多导致频繁 Full GC，拖垮应用——要合理设 `maxElementsInMemory`。
- 磁盘存储要求对象 `Serializable`，忘了实现会报 `NotSerializableException`。
- `diskStore path` 用相对路径，不同启动目录下生成不同磁盘文件，缓存"丢失"——建议用绝对路径或 `user.home` 这种稳定路径。

### 11.3 过期策略：TTI vs TTL

**实际开发中怎么用？**

Ehcache 有两种过期时间：

- `timeToIdleSeconds`（TTI）：对象空闲多久没被访问就过期。适合"热点数据"——一直被访问就不过期。
- `timeToLiveSeconds`（TTL）：对象存活多久就过期，不管有没有被访问。适合"数据有绝对时效"——如验证码 5 分钟必过期。

**最佳实践：**

- 字典数据、配置项：用 TTI（长时间没用就清掉，用了就续期）。
- 验证码、token：用 TTL（绝对过期）。
- 两者可同时设，取先到期的为准。
- `eternal=true` 时两者都失效（永不过期），适合"永久缓存 + 主动删除"模式。

**常见坑：**

- 设了 `eternal="true"` 还设了 `timeToLiveSeconds`，以为会过期，实际永不过期——`eternal` 优先级最高。
- 以为改了配置文件重启就立即生效，但旧缓存数据还在内存里按旧策略跑——本地缓存重启即清空，这点和 Redis 不同（Redis 重启可能保留数据）。

### 11.4 淘汰算法：LRU / LFU / FIFO

**实际开发中怎么选？**

| 算法 | 原理 | 适用场景 |
| --- | --- | --- |
| LRU | 淘汰最近最少访问的 | 大多数场景默认选择，假设"最近用的还会用" |
| LFU | 淘汰访问次数最少的 | 热点数据明显（少数 key 被高频访问） |
| FIFO | 先进先出 | 很少用，适合顺序性数据 |

**最佳实践：** 默认 LRU 够用。只有当发现"某些冷数据偶尔被访问一次就挤掉热数据"时，才考虑 LFU。

### 11.5 本地缓存 vs 远程缓存：怎么选？

**实际开发中的决策标准：**

| 维度 | 本地缓存（Ehcache/Caffeine） | 远程缓存（Redis） |
| --- | --- | --- |
| 性能 | 极快（纳秒级，内存访问） | 快（毫秒级，网络往返） |
| 容量 | 受 JVM 内存限制 | 可独立扩展，容量大 |
| 多节点共享 | 不支持（各节点独立缓存） | 支持（所有节点共享） |
| 一致性 | 节点间数据可能不一致 | 单点天然一致 |
| 运维成本 | 无额外组件 | 要维护 Redis 集群 |
| 适用 | 单体应用、读多写少、可容忍短暂不一致 | 微服务、需共享、强一致 |

**最佳实践：多级缓存。** 真实高并发系统常组合使用：

```
请求 → 本地缓存（Caffeine）→ 远程缓存（Redis）→ 数据库
```

本地缓存挡第一波流量，未命中再查 Redis，再未命中查数据库。这样既快又共享。

**常见坑：**

- 分布式系统用本地缓存，各节点数据不一致，导致"在 A 节点更新了，B 节点还读到旧值"——要么用 Redis，要么加广播通知各节点清本地缓存。
- 本地缓存重启即丢，不能当持久存储用。

### 11.6 Ehcache vs Caffeine：现代项目的选择

**实际开发趋势：**

Ehcache 2.x 是经典，但 Spring Boot 2.x 之后，**Caffeine 逐渐成为本地缓存首选**：

| 维度 | Ehcache 2.x | Caffeine |
| --- | --- | --- |
| 性能 | 好 | 极致（基于 W-TinyLFU 算法） |
| API | XML 配置 | 纯代码配置（Builder 链式） |
| 磁盘存储 | 支持 | 不支持（纯内存） |
| Spring Boot 集成 | 支持 | 支持（且更现代） |
| 维护状态 | Ehcache 3 重写，2.x 停滞 | 活跃 |

**最佳实践：** 新项目本地缓存优先选 Caffeine；老项目维护或需要磁盘持久化再用 Ehcache。两者都通过 Spring Cache 抽象接入，业务代码无差别。

---

> 📌 **学习建议**：本模块和上一篇 Redis 缓存是"对照组"——同样的业务代码，换底层实现。建议你把两篇对照着看，深刻体会"面向抽象编程"的好处：业务代码不绑定具体技术，换缓存引擎只改配置。另外记住本地缓存的核心局限——**多节点不共享**，这是它和 Redis 的本质区别，决定了它适合单体应用或作为多级缓存的第一层。
