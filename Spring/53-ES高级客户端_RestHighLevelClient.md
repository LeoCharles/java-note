# 53 - Elasticsearch 高级 REST 客户端

> 对应项目模块：`demo-elasticsearch-rest-high-level-client`
> 前置知识：已学完 `39-搜索引擎_ElasticSearch`（Spring Data ES 方式），了解 ES 基本概念（索引、文档、Mapping、倒排索引）
> 学习目标：掌握用官方 `RestHighLevelClient` 操作 ES 7.x 的完整 CRUD，理解它与 Spring Data ES 的差异，能独立封装一套 ES 服务层。

---

## 一、本模块要解决什么问题？

在 `39-搜索引擎_ElasticSearch` 模块里，我们用 **Spring Data Elasticsearch** 操作 ES——写个 `@Document` 实体、继承 `ElasticsearchRepository`，像写 JPA 一样增删改查。这种方式简单，但有两个局限：

1. **能力受限**：Spring Data ES 封装的是"常用操作"，一旦要做复杂的聚合、脚本、批量操作、索引生命周期管理，它的 API 就不够用，得退回到原生客户端。
2. **版本耦合**：Spring Data ES 和 ES 版本强绑定，Spring Boot 2.1 对应的 Spring Data ES 只支持 ES 2.x/5.x，要用 ES 7.x 就得绕开它的版本管理。

本模块的解法是：**直接用官方提供的 `RestHighLevelClient`**（Java High Level REST Client）。它是 Elastic 官方维护的、基于 HTTP REST 的 Java 客户端，API 完整、版本与 ES 严格对齐，是 ES 7.x 时代 Java 生态的主流选择。

> 💡 前端类比：Spring Data ES 像 ORM 框架（Prisma/TypeORM），封装好了常用 CRUD，开发快但灵活性低；`RestHighLevelClient` 像直接用 axios/fetch 调 REST API，什么都能做但要自己写更多代码。本模块演示的就是后者——自己封装一套 ES 服务层。

> ⚠️ 时效说明：`RestHighLevelClient` 在 ES 7.15+ 之后被官方标记为 deprecated，新官方客户端是 `Elasticsearch Java Client`（8.x）。但 7.x 仍是大量存量系统的主流版本，本模块基于 7.3.0，学懂它的 API 思想，迁移到 8.x 客户端也只是语法变化。

---

## 二、项目结构

```
demo-elasticsearch-rest-high-level-client/
├── pom.xml
└── src/main/java/com/xkcoding/elasticsearch/
    ├── ElasticsearchApplication.java          # 启动类
    ├── config/
    │   ├── ElasticsearchAutoConfiguration.java  # 手动注册 RestHighLevelClient Bean
    │   └── ElasticsearchProperties.java         # ES 配置属性绑定
    ├── contants/
    │   └── ElasticsearchConstant.java            # 索引名常量
    ├── model/
    │   └── Person.java                           # 实体（普通 POJO，无 @Document）
    ├── common/
    │   ├── Result.java                           # 统一响应体
    │   └── ResultCode.java                        # 状态码枚举
    ├── exception/
    │   └── ElasticsearchException.java            # 自定义异常
    └── service/
        ├── PersonService.java                     # 服务接口
        ├── base/BaseElasticsearchService.java     # 基类：封装通用 ES 操作
        └── impl/PersonServiceImpl.java            # 实现
└── src/main/resources/application.yml
└── src/test/.../ElasticsearchApplicationTests.java  # 测试类
```

注意和 39 篇的关键区别：这里**没有 `@Document` 注解、没有 `Repository` 接口**，`Person` 是个纯 POJO，所有 ES 操作都靠 `BaseElasticsearchService` 里手写的 `RestHighLevelClient` 调用完成。这是两种方案最直观的代码差异。

---

## 三、逐行拆解 pom.xml

```xml
<!-- elasticsearch 核心 -->
<dependency>
    <groupId>org.elasticsearch</groupId>
    <artifactId>elasticsearch</artifactId>
    <version>7.3.0</version>
</dependency>

<!-- 低级 REST 客户端（基于 Apache HttpClient） -->
<dependency>
    <groupId>org.elasticsearch.client</groupId>
    <artifactId>elasticsearch-rest-client</artifactId>
    <version>7.3.0</version>
</dependency>

<!-- 高级 REST 客户端 -->
<dependency>
    <groupId>org.elasticsearch.client</groupId>
    <artifactId>elasticsearch-rest-high-level-client</artifactId>
    <version>7.3.0</version>
    <exclusions>
        <exclusion>
            <groupId>org.elasticsearch.client</groupId>
            <artifactId>elasticsearch-rest-client</artifactId>
        </exclusion>
        <exclusion>
            <groupId>org.elasticsearch</groupId>
            <artifactId>elasticsearch</artifactId>
        </exclusion>
    </exclusions>
</dependency>
```

**为什么要三个依赖 + 两个 exclusion？**

- `elasticsearch`：ES 核心库，提供 `SearchRequest`、`QueryBuilders` 等请求/响应对象。
- `elasticsearch-rest-client`：低级 REST 客户端，只负责 HTTP 通信，不解析业务对象。
- `elasticsearch-rest-high-level-client`：高级客户端，在低级客户端之上封装了类型安全的 API（接收 `SearchRequest` 返回 `SearchResponse`）。

高级客户端的传递依赖里已经包含了前两者，但**版本可能和我们要的不一致**（它默认带的版本号是它自己构建时的版本）。所以这里显式声明前两个为 `7.3.0`，再在高级客户端里 `exclude` 掉它自带的，保证三者版本完全一致。这是 ES 客户端最经典的版本对齐坑。

> 💡 前端类比：这像你装了 `@vue/reactivity` 又装了 `vue`，但 `vue` 自带的 `@vue/reactivity` 版本和你手动装的不一致，导致运行时两个实例冲突。解决办法就是 exclude 掉传递依赖，显式统一版本。

其他依赖：`spring-boot-configuration-processor`（配置元数据，给 yml 提示）、`hibernate-validator`（校验）、`hutool-all`（工具类，用 `BeanUtil` 做 bean↔map 转换）、`lombok`。

注意本模块引的是 `spring-boot-starter`（不是 `starter-web`），因为 demo 通过测试类演示，没有 Web 接口。

---

## 四、配置属性 `ElasticsearchProperties`

```java
@Data
@Builder
@Component
@NoArgsConstructor
@AllArgsConstructor
@ConfigurationProperties(prefix = "demo.data.elasticsearch")
public class ElasticsearchProperties {
    private String schema = "http";
    private String clusterName = "elasticsearch";
    @NotNull(message = "集群节点不允许为空")
    private List<String> clusterNodes = new ArrayList<>();
    private Integer connectTimeout = 1000;
    private Integer socketTimeout = 30000;
    private Integer connectionRequestTimeout = 500;
    private Integer maxConnectPerRoute = 10;
    private Integer maxConnectTotal = 30;
    private Index index = new Index();
    private Account account = new Account();

    @Data
    public static class Index {
        private Integer numberOfShards = 3;
        private Integer numberOfReplicas = 2;
    }

    @Data
    public static class Account {
        private String username;
        private String password;
    }
}
```

这是典型的 `@ConfigurationProperties` 用法（02 篇详细讲过）。把 `application.yml` 里 `demo.data.elasticsearch` 前缀的配置绑定到这个类的字段。几个关键参数：

| 参数 | 默认值 | 含义 |
| --- | --- | --- |
| `schema` | http | 协议（http/https） |
| `clusterNodes` | - | 集群节点列表，格式 `host:port` |
| `connectTimeout` | 1000ms | 建立 TCP 连接超时 |
| `socketTimeout` | 30000ms | 等待响应数据超时 |
| `connectionRequestTimeout` | 500ms | 从连接池获取连接超时 |
| `maxConnectTotal` | 30 | 连接池最大连接数 |
| `maxConnectPerRoute` | 10 | 单个路由（单节点）最大连接数 |
| `index.numberOfShards` | 3 | 索引分片数 |
| `index.numberOfReplicas` | 2 | 索引副本数 |

> 💡 前端类比：这像 axios 的 `timeout` + 连接池配置。`maxConnectTotal`/`maxConnectPerRoute` 是 Apache HttpClient 的连接池参数，类似前端 axios 里没有但 Node.js http agent 里有的 `maxSockets`。

对应的 `application.yml`：

```yaml
demo:
  data:
    elasticsearch:
      cluster-name: elasticsearch
      cluster-nodes: 20.20.0.27:9200
      index:
        number-of-replicas: 0
        number-of-shards: 3
```

注意单节点 demo 把副本数设成 0（单机没法副本，否则索引会处于 yellow 状态）。

---

## 五、核心：手动注册 `RestHighLevelClient` Bean

`config/ElasticsearchAutoConfiguration.java` 是本模块的核心，它没有用 Spring Boot 自动配置，而是**手动**创建 `RestHighLevelClient` Bean：

```java
@Configuration
@RequiredArgsConstructor(onConstructor_ = @Autowired)
@EnableConfigurationProperties(ElasticsearchProperties.class)
public class ElasticsearchAutoConfiguration {

    private final ElasticsearchProperties elasticsearchProperties;

    private List<HttpHost> httpHosts = new ArrayList<>();

    @Bean
    @ConditionalOnMissingBean
    public RestHighLevelClient restHighLevelClient() {
        // 1. 解析集群节点 host:port → HttpHost
        List<String> clusterNodes = elasticsearchProperties.getClusterNodes();
        clusterNodes.forEach(node -> {
            String[] parts = StringUtils.split(node, ":");
            Assert.state(parts.length == 2, "Must be defined as 'host:port'");
            httpHosts.add(new HttpHost(parts[0], Integer.parseInt(parts[1]), elasticsearchProperties.getSchema()));
        });
        // 2. 构建 RestClientBuilder
        RestClientBuilder builder = RestClient.builder(httpHosts.toArray(new HttpHost[0]));
        // 3. 配置超时、连接池、认证
        return getRestHighLevelClient(builder, elasticsearchProperties);
    }
}
```

逐步看：

1. `@EnableConfigurationProperties(ElasticsearchProperties.class)`：启用配置属性绑定，把 `ElasticsearchProperties` 注册成 Bean 并注入。
2. `@RequiredArgsConstructor(onConstructor_ = @Autowired)`：Lombok 生成构造器，`onConstructor_` 让构造器参数加上 `@Autowired`，实现构造器注入（02 篇讲过这是推荐写法）。
3. `@Bean @ConditionalOnMissingBean`：注册 `RestHighLevelClient` Bean，`@ConditionalOnMissingBean` 表示"如果容器里还没有这个 Bean 才创建"，允许用户自定义覆盖。

`getRestHighLevelClient` 方法的两个回调：

```java
// 请求级配置：超时
builder.setRequestConfigCallback(requestConfigBuilder -> {
    requestConfigBuilder.setConnectTimeout(...);
    requestConfigBuilder.setSocketTimeout(...);
    requestConfigBuilder.setConnectionRequestTimeout(...);
    return requestConfigBuilder;
});

// 客户端级配置：连接池
builder.setHttpClientConfigCallback(httpClientBuilder -> {
    httpClientBuilder.setMaxConnTotal(...);
    httpClientBuilder.setMaxConnPerRoute(...);
    return httpClientBuilder;
});
```

这两个 callback 是 `RestClientBuilder` 的标准用法——`RequestConfigCallback` 配置单次请求参数（超时），`HttpClientConfigCallback` 配置底层 HttpClient 参数（连接池、认证）。

> ⚠️ 注意一个 bug：认证那段代码 `if (!StringUtils.isEmpty(account.getUsername()) && !StringUtils.isEmpty(account.getUsername()))` 判断了两次 username（应该是 username 和 password），而且创建了 `credentialsProvider` 却**没有传给 builder**（少了 `httpClientBuilder.setDefaultCredentialsProvider(...)`）。所以认证实际不生效。这是学习 demo 的瑕疵，实际项目要修正。

---

## 六、基类 `BaseElasticsearchService`：封装通用 ES 操作

这是本模块的精华——把所有 ES 原生 API 调用封装在抽象基类里，子类直接用。

### 6.1 客户端和请求选项

```java
@Slf4j
public abstract class BaseElasticsearchService {
    @Resource
    protected RestHighLevelClient client;

    protected static final RequestOptions COMMON_OPTIONS;

    static {
        RequestOptions.Builder builder = RequestOptions.DEFAULT.toBuilder();
        // 默认缓冲限制100MB，改成30MB
        builder.setHttpAsyncResponseConsumerFactory(
            new HttpAsyncResponseConsumerFactory.HeapBufferedResponseConsumerFactory(30 * 1024 * 1024));
        COMMON_OPTIONS = builder.build();
    }
}
```

- `@Resource` 注入 `RestHighLevelClient`（`@Resource` 是 JSR-250 注解，按名称注入；`@Autowired` 按类型注入，效果类似）。
- `RequestOptions` 是每次请求的公共配置（超时、缓冲区、header）。这里把响应缓冲上限从默认 100MB 改成 30MB，防止大查询结果撑爆堆内存。所有请求都传 `COMMON_OPTIONS`。

### 6.2 索引管理：创建/删除索引

```java
protected void createIndexRequest(String index) {
    CreateIndexRequest request = new CreateIndexRequest(index);
    request.settings(Settings.builder()
        .put("index.number_of_shards", ...)
        .put("index.number_of_replicas", ...));
    CreateIndexResponse response = client.indices().create(request, COMMON_OPTIONS);
    log.info("acknowledged: {}", response.isAcknowledged());
}
```

- `CreateIndexRequest`：创建索引请求（注意 import 的是 `org.elasticsearch.client.indices.CreateIndexRequest`，不是老版的 `org.elasticsearch.action.admin.indices.create.CreateIndexRequest`，7.x 改了包路径）。
- `client.indices()`：获取 `IndicesClient`，专门做索引级操作（创建、删除、是否存在）。
- `Settings.builder()`：索引级设置，分片数和副本数。

删除索引类似：`new DeleteIndexRequest(index)` + `client.indices().delete(...)`。

### 6.3 文档 CRUD

**新增**：

```java
protected static IndexRequest buildIndexRequest(String index, String id, Object object) {
    return new IndexRequest(index).id(id).source(BeanUtil.beanToMap(object), XContentType.JSON);
}
// 调用：client.index(request, COMMON_OPTIONS);
```

- `IndexRequest`：索引一个文档（存在则覆盖）。`.id(id)` 指定文档 id，`.source(map, JSON)` 设置文档内容。
- `BeanUtil.beanToMap`：Hutool 工具，把 Person 对象转成 Map，再以 JSON 格式写入 source。

**更新**：

```java
UpdateRequest updateRequest = new UpdateRequest(index, id).doc(BeanUtil.beanToMap(object), XContentType.JSON);
client.update(updateRequest, COMMON_OPTIONS);
```

- `UpdateRequest`：部分更新，`.doc(...)` 只更新传入的字段，其他字段不变（和新增的"全量覆盖"不同）。

**删除**：

```java
DeleteRequest deleteRequest = new DeleteRequest(index, id);
client.delete(deleteRequest, COMMON_OPTIONS);
```

### 6.4 查询

```java
protected SearchResponse search(String index) {
    SearchRequest searchRequest = new SearchRequest(index);
    SearchSourceBuilder searchSourceBuilder = new SearchSourceBuilder();
    searchSourceBuilder.query(QueryBuilders.matchAllQuery());
    searchRequest.source(searchSourceBuilder);
    return client.search(searchRequest, COMMON_OPTIONS);
}
```

- `SearchRequest`：搜索请求，指定索引。
- `SearchSourceBuilder`：搜索源构建器，组装 query、分页、排序、聚合等。
- `QueryBuilders.matchAllQuery()`：匹配全部（`SELECT *`）。

> 💡 前端类比：`SearchSourceBuilder` 像一个 query DSL 构造器，类似前端拼 GraphQL query 字符串或 MongoDB 的 find 条件对象。`QueryBuilders` 是工厂类，提供 `matchQuery`、`termQuery`、`boolQuery` 等各种查询构造方法。

---

## 七、服务接口与实现

### 7.1 `PersonService` 接口

定义了六个方法：`createIndex`、`deleteIndex`、`insert`、`update`、`delete`、`searchList`。注意 `delete` 参数用了 `@Nullable`，表示允许传 null（此时删除全量）。

### 7.2 `PersonServiceImpl` 实现

```java
@Service
public class PersonServiceImpl extends BaseElasticsearchService implements PersonService {

    @Override
    public void insert(String index, List<Person> list) {
        try {
            list.forEach(person -> {
                IndexRequest request = buildIndexRequest(index, String.valueOf(person.getId()), person);
                client.index(request, COMMON_OPTIONS);
            });
        } finally {
            client.close();   // ⚠️ 这里有问题，见下文
        }
    }
}
```

实现就是调基类封装的方法。`searchList` 把返回的 `SearchHit[]` 用 `BeanUtil.mapToBean` 转回 Person 对象列表。

> ⚠️ **代码缺陷**（学习时要识别）：`insert` 方法在 `finally` 里调了 `client.close()`，这会把 `RestHighLevelClient` 关闭。因为 client 是单例 Bean，关闭后后续所有操作都会失败。这是 demo 代码的 bug，实际项目绝不能这么做——`RestHighLevelClient` 应该是应用级单例，随应用生命周期存在，不能在每次操作后关闭。

### 7.3 `Person` 实体

```java
@Data @Builder @NoArgsConstructor @AllArgsConstructor
public class Person implements Serializable {
    private Long id;
    private String name;
    private String country;
    private Integer age;
    private Date birthday;
    private String remark;
}
```

纯 POJO，没有任何 ES 注解（对比 39 篇的 `@Document(indexName=...)` `@Field(type=...)`）。因为用的是原生客户端，Mapping 由 ES 自动推断或手动指定，不依赖注解。

> 💡 `@Builder` 是 Lombok 的链式构造器：`Person.builder().id(1L).name("x").build()`，类似前端的对象字面量 `{ id: 1, name: 'x' }`，写测试数据很方便。

---

## 八、统一响应体与异常

`Result<T>` + `ResultCode` + `ElasticsearchException` 是一套标准的响应封装（07 篇异常处理详细讲过）：

- `Result<T>`：泛型响应体，`errcode` + `errmsg` + `data`，提供 `success()` 静态工厂。
- `ResultCode`：状态码枚举（SUCCESS=0, FAILURE=-1）。
- `ElasticsearchException`：自定义运行时异常，携带 errcode/errmsg。

> 💡 前端类比：这就是前端 axios 拦截器里统一的 `{ code, message, data }` 响应格式。后端把所有结果包成这个结构返回，前端拦截器统一处理。

---

## 九、运行与验证

### 9.1 准备 ES 环境

用 Docker 启动 ES 7.3.0（README 提供了 docker-compose）：

```yaml
version: "3"
services:
  es7:
    image: elasticsearch:7.3.0
    ports:
      - "9200:9200"
      - "9300:9300"
    environment:
      cluster.name: elasticsearch
      discovery.type: single-node
```

```sh
docker-compose -f elasticsearch.yaml up -d
```

### 9.2 修改配置

把 `application.yml` 的 `cluster-nodes` 改成本机：`127.0.0.1:9200`。

### 9.3 运行测试

测试类 `ElasticsearchApplicationTests` 按顺序演示了完整 CRUD：

| 测试方法 | 作用 |
| --- | --- |
| `deleteIndexTest` | 先删除旧索引（清理环境） |
| `createIndexTest` | 创建 `person` 索引 |
| `insertTest` | 插入 3 条文档（用 `Person.builder()` 构造） |
| `updateTest` | 更新 id=3 的文档 |
| `deleteTest` | 删除 id=1 的文档 |
| `searchListTest` | 查询全部并打印 |

注意测试要**按顺序执行**（用 `@FixMethodOrder` 或手动控制），因为后面的操作依赖前面的数据。

---

## 十、动手练习

1. **加一个条件查询**：在 `BaseElasticsearchService` 加 `searchByName(index, name)` 方法，用 `QueryBuilders.matchQuery("name", name)` 替换 `matchAllQuery`，测试按名字搜索。
2. **加分页**：用 `searchSourceBuilder.from(0).size(10)` 实现分页查询。
3. **加排序**：用 `searchSourceBuilder.sort("age", SortOrder.DESC)` 按年龄降序。
4. **修 bug**：删掉 `insert` 方法里 `finally` 中的 `client.close()`，验证多次调用不再报错。
5. **修认证**：修正 `ElasticsearchAutoConfiguration` 里的认证代码，让 `credentialsProvider` 真正生效（加 `httpClientBuilder.setDefaultCredentialsProvider(credentialsProvider)`），给 ES 加上 basic auth 测试。
6. **对比 Spring Data ES**：参考 39 篇，用 Spring Data ES 实现同样的 CRUD，对比两种方案的代码量和灵活性。

---

## 十一、本模块知识点总结（结合实际开发详解）

本模块演示了"绕开 Spring Data ES、直接用官方客户端"的方案。这是 ES 7.x 时代 Java 项目的常见选择，下面把核心知识点放到真实开发场景里讲透。

### 11.1 Spring Data ES vs RestHighLevelClient：怎么选？

**实际开发中的选择标准：**

| 维度 | Spring Data ES | RestHighLevelClient |
| --- | --- | --- |
| 学习成本 | 低（像 JPA，写接口即可） | 中（要懂原生 API） |
| 开发速度 | 快（自动生成 CRUD） | 慢（手写每步） |
| 灵活性 | 低（复杂查询要绕） | 高（API 完整） |
| 版本管理 | 受 Spring Boot 管控，易冲突 | 自己对齐版本，可控 |
| 适合场景 | 简单 CRUD、快速原型 | 复杂查询、聚合、索引管理 |

**最佳实践**：
- 中小项目、CRUD 为主 → Spring Data ES，省事。
- 复杂搜索（电商商品搜索、日志分析）、需要精细控制 → RestHighLevelClient。
- 大型项目常**混用**：简单操作走 Repository，复杂操作注入 `RestHighLevelClient` 手写。

> 💡 前端类比：Spring Data ES 像 React Query / SWR，封装好了数据获取缓存，简单场景极快；RestHighLevelClient 像直接用 axios，什么都能控制但要自己写更多。两者常在同一项目共存。

### 11.2 ES 客户端的三层架构

理解 ES Java 客户端的三层，排查问题不懵：

1. **Transport 层**：早期是 TCP（`TransportClient`，7.0 废弃），现在是 HTTP REST。
2. **Low Level REST Client**：`elasticsearch-rest-client`，只管 HTTP 收发，不解析业务对象，返回原始字符串。
3. **High Level REST Client**：`elasticsearch-rest-high-level-client`，在低级之上封装类型安全 API，接收 `SearchRequest` 返回 `SearchResponse`。

**实际开发要点**：
- 高级客户端依赖低级客户端，低级依赖 Apache HttpClient。三者版本必须对齐，否则运行时 `NoSuchMethodError`。
- 排查"找不到方法"错误时，先 `mvn dependency:tree` 看这三个 jar 的实际版本是否一致。

### 11.3 `RestHighLevelClient` 的生命周期管理

**实际开发中最容易踩的坑**：把 client 当成"用完即关"的资源。

本模块 demo 在 `insert` 的 `finally` 里调 `client.close()`，这是**错误示范**。正确做法：

- `RestHighLevelClient` 内部维护连接池和异步 HTTP 客户端，**创建成本高、应复用**。
- 它应该是 Spring 容器里的**单例 Bean**，随应用启动而创建、随应用关闭而销毁。
- 用 `@PreDestroy` 或 `@Bean(destroyMethod = "close")` 让容器管理它的关闭：

```java
@Bean(destroyMethod = "close")
public RestHighLevelClient restHighLevelClient() { ... }
```

> 💡 前端类比：这像数据库连接池或 axios 实例——你不会每次请求都 `new axios()` 再 `delete`，而是全局复用一个实例。`RestHighLevelClient` 同理，关早了后续全报错。

### 11.4 `RequestOptions`：被忽视的稳定性配置

本模块用 `RequestOptions` 把响应缓冲上限从 100MB 改成 30MB。这个细节在生产环境很重要：

- ES 查询结果可能很大（几万条文档），默认 100MB 堆缓冲在高并发下会 OOM。
- `HeapBufferedResponseConsumerFactory` 控制单次响应在堆内存中的缓冲上限，超了直接报错而不是默默吃光内存。

**最佳实践**：
- 生产环境根据查询规模设一个合理上限（如 30-50MB），用错误换稳定。
- 大结果集用 `scroll` 或 `search_after` 分批拉取，不要一次性查全量。

### 11.5 索引 Mapping：自动推断 vs 手动定义

本模块创建索引时只设了分片/副本数，**没定义 Mapping**，ES 会根据第一条文档自动推断字段类型。这在 demo 里方便，生产环境是坑：

- 自动推断可能把 `id` 推成 `long` 而非 `keyword`，导致后续无法用于聚合。
- `text` 和 `keyword` 类型混用（39 篇详细讲过），自动推断常把字符串推成 `text`，无法精确匹配。

**最佳实践**：
- 生产环境**创建索引时手动定义 Mapping**：

```java
String mapping = "{\n" +
    "  \"properties\": {\n" +
    "    \"name\": {\"type\": \"text\", \"analyzer\": \"ik_max_word\"},\n" +
    "    \"country\": {\"type\": \"keyword\"},\n" +
    "    \"age\": {\"type\": \"integer\"}\n" +
    "  }\n" +
    "}";
request.mapping(mapping, XContentType.JSON);
```

- 字段类型一旦定下不能改（只能 reindex 重建），所以 Mapping 设计要一次到位。

### 11.6 批量操作：用 `BulkRequest` 而非循环单条

本模块 `insert` 用 `list.forEach` 循环调 `client.index()`，每条一次 HTTP 请求。数据量大时性能很差。

**最佳实践**：用 `BulkRequest` 批量提交：

```java
BulkRequest bulkRequest = new BulkRequest();
list.forEach(person -> {
    bulkRequest.add(new IndexRequest(index).id(String.valueOf(person.getId()))
        .source(BeanUtil.beanToMap(person), XContentType.JSON));
});
client.bulk(bulkRequest, COMMON_OPTIONS);
```

一次 HTTP 请求提交全部操作，网络开销从 N 次降到 1 次。生产环境写 ES 几乎必用 Bulk。

### 11.7 ES 客户端的版本演进与迁移

**实际开发要关注的版本路线**（截至 2026 年）：

| ES 版本 | 推荐客户端 | 状态 |
| --- | --- | --- |
| 2.x - 6.x | TransportClient | 已废弃 |
| 5.x - 7.14 | RestHighLevelClient | 主流 |
| 7.15+ | RestHighLevelClient | 官方标记 deprecated |
| 8.x | Elasticsearch Java Client（新） | 官方推荐 |

**迁移建议**：
- 存量 7.x 项目：继续用 RestHighLevelClient 没问题，官方仍维护安全补丁。
- 新项目或升 8.x：用新的 `co.elastic.clients.elasticsearch.ElasticsearchClient`，API 风格变为 Builder + 流式，更类型安全。
- 本模块学的 `SearchSourceBuilder`、`QueryBuilders` 思想在新客户端里延续，迁移成本主要是语法。

> 💡 前端类比：这像 axios 0.x → 1.x 的迁移，API 变了但核心概念（请求/响应/拦截器）不变。学懂 7.x 的思想，迁移到 8.x 主要是查文档改语法。

---

> 📌 **学习建议**：ES 是前端转后端最容易"上手"的中间件之一——因为它就是存 JSON 的搜索引擎，和前端处理 JSON 对象的思维高度一致。难点不在语法，而在**搜索建模**：怎么把业务需求翻译成 Mapping 设计 + 查询 DSL。建议把 39 篇（Spring Data ES）和本篇对照着学，理解"自动配置 vs 手动封装"两种风格的取舍，这是 Spring Boot 集成第三方组件的核心能力。另外，识别 demo 代码里的 bug（如 `client.close()`、认证未生效）本身就是很好的学习——读代码不只是模仿，还要能判断对错。
