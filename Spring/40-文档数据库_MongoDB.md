# 40 - 文档数据库 MongoDB

> 对应项目模块：`demo-mongodb`
> 前置知识：已学完前序 ORM 模块（JdbcTemplate / JPA / MyBatis），理解 Spring Boot 数据访问的基本套路
> 学习目标：理解 MongoDB 与关系型数据库的差异，掌握 Spring Data MongoDB 的两种数据访问方式（Repository 与 MongoTemplate），能独立完成文档的增删改查。

---

## 一、本模块要解决什么问题？

前面几个数据库模块（JdbcTemplate / JPA / MyBatis）操作的都是**关系型数据库**（MySQL），它们用表、行、列来组织数据，强调严格的表结构和外键关联。但实际开发中，有一类数据用关系型数据库并不顺手：

- 文章内容、评论嵌套结构不固定，每篇文章的"扩展属性"可能不一样
- 日志、埋点数据量极大，写入频繁，关系型数据库的 JOIN 和事务反而是负担
- 配置信息、商品规格等半结构化数据，天然就是"一个 JSON 对象"

**MongoDB** 就是为这类场景设计的**文档型 NoSQL 数据库**。它用"集合（Collection）"存"文档（Document）"，一个文档就是一个类 JSON 的 BSON 对象，字段可以嵌套、可以动态变化，没有固定表结构。

> 💡 前端类比：MongoDB 对前端工程师特别友好，因为它的数据模型就是你天天打交道的东西——**JSON 对象**。MySQL 的表像 Excel 表格（固定列），MongoDB 的集合像一个 JSON 数组（`[{...}, {...}, {...}]`），每个对象的字段可以不一样。你可以把它理解成一个"远程的、可查询的 JSON 数组仓库"。这跟前端 localStorage 存 JSON 很像，但 MongoDB 支持强大的查询、索引、分片。

本模块演示：用 Spring Boot 集成 MongoDB，对"文章"做增删改查、分页排序、模糊查询，并对比两种数据访问方式。

---

## 二、项目结构

```
demo-mongodb/
├── pom.xml
└── src/
    ├── main/
    │   ├── java/com/xkcoding/mongodb/
    │   │   ├── SpringBootDemoMongodbApplication.java   # 启动类（注册雪花算法 Bean）
    │   │   ├── model/
    │   │   │   └── Article.java                        # 文章实体（@Document 文档）
    │   │   └── repository/
    │   │       └── ArticleRepository.java              # DAO（继承 MongoRepository）
    │   └── resources/
    │       └── application.yml                          # MongoDB 连接配置
    └── test/java/com/xkcoding/mongodb/
        ├── SpringBootDemoMongodbApplicationTests.java  # 测试基类
        └── repository/
            └── ArticleRepositoryTest.java              # 增删改查测试（含 MongoTemplate）
```

注意本模块**没有 Controller 和 Service**——所有操作都在测试类里演示。这是因为重点在"数据访问层"，业务层和 Web 层的套路和前面 ORM 模块完全一样，这里省略以聚焦 MongoDB 本身。

---

## 三、环境准备：用 Docker 启动 MongoDB

本模块依赖一个运行中的 MongoDB 实例。README 给出了 Docker 启动方式：

```sh
# 1. 下载镜像
docker pull mongo:4.1

# 2. 运行容器，映射 27017 端口，挂载数据目录
docker run -d -p 27017:27017 \
  -v /Users/yangkai.shen/docker/mongo/data:/data/db \
  --name mongo-4.1 mongo:4.1

# 3. 停止 / 启动
docker stop mongo-4.1
docker start mongo-4.1
```

关键参数解释：

- `-p 27017:27017`：把容器内 MongoDB 默认端口 27017 映射到宿主机，应用才能连上。
- `-v .../data:/data/db`：把容器内的数据目录挂载到宿主机，**容器删了数据还在**。NoSQL 数据库的数据目录挂载和关系型数据库一样重要。
- `--name mongo-4.1`：给容器起名，方便后续 start/stop。

> 💡 前端类比：这就像前端开发时用 Docker 起一个本地 MySQL/Redis，不污染宿主机环境，随用随起。如果你没装 Docker，也可以直接下载 MongoDB 安装包本地装一个，或用 MongoDB Atlas（云服务）。

---

## 四、逐行拆解 `pom.xml`

```xml
<dependencies>
    <!-- 1. 基础起步依赖（不含 Web，本模块只演示数据访问） -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter</artifactId>
    </dependency>

    <!-- 2. MongoDB 起步依赖（核心） -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-data-mongodb</artifactId>
    </dependency>

    <!-- 3. 测试 -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-test</artifactId>
        <scope>test</scope>
    </dependency>

    <!-- 4. Hutool 工具类（生成随机数据、雪花ID、JSON序列化） -->
    <dependency>
        <groupId>cn.hutool</groupId>
        <artifactId>hutool-all</artifactId>
    </dependency>

    <!-- 5. Guava 工具类 -->
    <dependency>
        <groupId>com.google.guava</groupId>
        <artifactId>guava</artifactId>
    </dependency>

    <!-- 6. Lombok -->
    <dependency>
        <groupId>org.projectlombok</groupId>
        <artifactId>lombok</artifactId>
        <optional>true</optional>
    </dependency>
</dependencies>
```

**重点理解 `spring-boot-starter-data-mongodb`：**

引这一个依赖，Spring Boot 自动给你装配了：

| 自动注册的 Bean | 作用 |
| --- | --- |
| `MongoClient` | MongoDB 的 Java 驱动客户端，负责底层连接 |
| `MongoTemplate` | Spring Data 提供的模板类，直接执行命令式操作 |
| `MappingMongoConverter` | Java 对象 ↔ BSON 文档的转换器 |
| Repository 支持 | 自动扫描 `@Repository` 接口，生成代理实现 |

对比关系型数据库的 Starter：`spring-boot-starter-data-jpa` 对应 `DataSource` + `EntityManager` + Repository；这里 `spring-boot-starter-data-mongodb` 对应 `MongoClient` + `MongoTemplate` + Repository，**套路完全一致**——Spring Data 把不同数据源的访问方式统一抽象了。

> 💡 注意本模块用的是 `spring-boot-starter`（不带 `-web`），因为没有 Web 接口，纯数据访问演示。如果要做 Web 接口，换成 `spring-boot-starter-web` 即可。

---

## 五、配置文件 `application.yml`

```yaml
spring:
  data:
    mongodb:
      host: localhost
      port: 27017
      database: article_db
logging:
  level:
    org.springframework.data.mongodb.core: debug
```

### 5.1 MongoDB 连接配置

| 配置项 | 作用 | 默认值 |
| --- | --- | --- |
| `spring.data.mongodb.host` | MongoDB 主机地址 | localhost |
| `spring.data.mongodb.port` | 端口 | 27017 |
| `spring.data.mongodb.database` | 数据库名（不存在会自动创建） | test |

**MongoDB 与关系型数据库的术语对照：**

| 关系型数据库 | MongoDB | 本模块对应 |
| --- | --- | --- |
| Database（数据库） | Database（数据库） | `article_db` |
| Table（表） | Collection（集合） | `article`（由实体类名推导） |
| Row（行） | Document（文档） | 一篇 Article 对象 |
| Column（列） | Field（字段） | title、content 等 |
| Primary Key（主键） | `_id` 字段 | `@Id` 标注的 id 字段 |

**连接配置的几种写法：**

```yaml
# 写法一：分项配置（本模块用的，清晰）
spring:
  data:
    mongodb:
      host: localhost
      port: 27017
      database: article_db

# 写法二：URI 一行搞定（生产常用，可带账号密码）
spring:
  data:
    mongodb:
      uri: mongodb://user:pass@localhost:27017/article_db

# 写法三：副本集/集群
spring:
  data:
    mongodb:
      uri: mongodb://host1:27017,host2:27017,host3:27017/article_db?replicaSet=rs0
```

### 5.2 日志配置

```yaml
logging:
  level:
    org.springframework.data.mongodb.core: debug
```

把 MongoDB 核心包的日志设为 `debug`，这样执行操作时控制台会打印实际发送给 MongoDB 的查询语句，**调试时非常有用**——你能看到 Spring Data 帮你生成的 BSON 命令长什么样。

> 💡 前端类比：这就像前端开发时打开浏览器的 Network 面板看实际发出的 HTTP 请求。MongoDB 的 debug 日志就是"数据库版 Network 面板"。

---

## 六、实体类 `Article.java`

```java
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class Article {
    /**
     * 文章id
     */
    @Id
    private Long id;

    /**
     * 文章标题
     */
    private String title;

    /**
     * 文章内容
     */
    private String content;

    /**
     * 创建时间
     */
    private Date createTime;

    /**
     * 更新时间
     */
    private Date updateTime;

    /**
     * 点赞数量
     */
    private Long thumbUp;

    /**
     * 访客数量
     */
    private Long visits;
}
```

### 6.1 `@Id` —— 文档主键

- `@Id` 来自 `org.springframework.data.annotation.Id`（Spring Data 通用注解，不是 MongoDB 专属）。
- 它标记的字段会映射到 MongoDB 文档的 `_id` 字段。MongoDB 中每个文档**必须有 `_id`**，类似关系型数据库的主键，但默认类型是 `ObjectId`（12 字节）。
- 这里用 `Long` 类型，需要自己赋值（本模块用雪花算法生成）。如果不赋值且类型是 `String` 或 `ObjectId`，MongoDB 驱动会自动生成。

### 6.2 为什么没有 `@Document` 注解？

你可能注意到，这个实体类**没有** `@Document(collection = "article")` 注解。这是可以的——Spring Data MongoDB 会**默认用类名推导集合名**：`Article` → 集合 `article`（首字母小写）。如果想自定义集合名，才需要显式标注：

```java
@Document(collection = "t_article")   // 显式指定集合名
public class Article { ... }
```

### 6.3 Lombok 注解

| 注解 | 作用 |
| --- | --- |
| `@Data` | getter/setter/toString/equals/hashCode |
| `@Builder` | 链式构造器：`Article.builder().title("x").build()` |
| `@NoArgsConstructor` | 无参构造（框架反射实例化需要） |
| `@AllArgsConstructor` | 全参构造（测试里 `new Article(1L, ...)` 用到） |

> 💡 前端类比：MongoDB 存的文档就是把这个 Article 对象序列化成 JSON 后的样子——`{"_id": 1, "title": "...", "content": "...", "createTime": "...", "thumbUp": 0}`。和前端 `JSON.stringify(article)` 一模一样，只是字段名按 Java 驼峰，存进 BSON 后还是驼峰。

---

## 七、DAO 层 `ArticleRepository.java`

```java
public interface ArticleRepository extends MongoRepository<Article, Long> {
    /**
     * 根据标题模糊查询
     */
    List<Article> findByTitleLike(String title);
}
```

### 7.1 `MongoRepository<Article, Long>`

- 继承 `MongoRepository<T, ID>`，T 是实体类型，ID 是主键类型。
- 这是 Spring Data 的**Repository 抽象**——你只定义接口，Spring Data 在运行时用动态代理生成实现类，自动提供增删改查方法。

**`MongoRepository` 自带的方法（不用写实现）：**

| 方法 | 作用 |
| --- | --- |
| `save(entity)` | 新增或更新（有 `_id` 且存在则更新） |
| `saveAll(iterable)` | 批量新增 |
| `findById(id)` | 按主键查 |
| `findAll()` | 查全部 |
| `findAll(pageable)` | 分页查询 |
| `deleteById(id)` | 按主键删 |
| `deleteAll()` | 删全部 |
| `count()` | 计数 |

### 7.2 方法名查询（Derived Query）

```java
List<Article> findByTitleLike(String title);
```

这行**没有实现**，但能工作！这就是 Spring Data 的"方法名查询"魔法：根据方法名推导查询条件。

- `findBy`：查询关键字
- `Title`：按 title 字段
- `Like`：模糊匹配（MongoDB 会转成正则）

Spring Data 会把 `findByTitleLike("更新")` 翻译成 MongoDB 的查询：`{ title: { $regex: "更新" } }`。

**常用方法名关键字：**

| 方法名关键字 | 对应 MongoDB 查询 | 前端类比 |
| --- | --- | --- |
| `findByTitle(String)` | `{ title: value }` 精确匹配 | `arr.filter(x => x.title === value)` |
| `findByTitleLike(String)` | `{ title: { $regex: value } }` | `arr.filter(x => x.title.includes(value))` |
| `findByTitleStartingWith(String)` | `{ title: { $regex: "^value" } }` | `startsWith` |
| `findByThumbUpGreaterThan(Long)` | `{ thumbUp: { $gt: value } }` | `arr.filter(x => x.thumbUp > value)` |
| `findByTitleAndAuthor(...)` | `{ title: ..., author: ... }` | 多条件 AND |
| `findByTitleOrAuthor(...)` | `{ $or: [...] }` | 多条件 OR |
| `countByThumbUpGreaterThan(Long)` | 聚合计数 | `arr.filter(...).length` |

> 💡 前端类比：这就像一个智能的 `Array.filter`——你用方法名描述"我要按什么条件过滤"，Spring Data 帮你生成对应的查询语句。不用写 SQL，不用写 MongoDB 查询语法，方法名就是查询。

---

## 八、启动类 `SpringBootDemoMongodbApplication.java`

```java
@SpringBootApplication
public class SpringBootDemoMongodbApplication {

    public static void main(String[] args) {
        SpringApplication.run(SpringBootDemoMongodbApplication.class, args);
    }

    @Bean
    public Snowflake snowflake() {
        return IdUtil.createSnowflake(1, 1);
    }
}
```

### 8.1 注册雪花算法 Bean

- `@Bean`：把方法的返回值注册成 Spring 容器里的 Bean，之后可以 `@Autowired` 注入。
- `IdUtil.createSnowflake(1, 1)`：Hutool 提供的雪花算法（Snowflake）ID 生成器，参数是机器ID和工作站ID。
- 雪花算法生成**全局唯一、趋势递增**的 64 位整数 ID，适合做分布式主键。

**为什么用雪花算法？**

MongoDB 默认主键是 `ObjectId`（24 位十六进制字符串，如 `507f1f77bcf86cd799439011`）。但业务里常用 `Long` 型自增 ID 更直观、占空间小、便于排序。雪花算法在不依赖数据库自增的前提下，生成全局唯一的 Long ID，是分布式系统的常见选择。

> 💡 前端类比：这就像前端用 `Date.now() + Math.random()` 或 `uuid()` 生成唯一 ID，但雪花算法更严谨——它结合时间戳+机器ID+序列号，保证多台机器同时生成也不重复，且趋势递增（利于 B+树索引和缓存局部性）。

---

## 九、测试类：两种数据访问方式对比

`ArticleRepositoryTest.java` 演示了完整的增删改查，同时对比了 `Repository` 和 `MongoTemplate` 两种方式。

### 9.1 测试基类与依赖注入

```java
@Slf4j
public class ArticleRepositoryTest extends SpringBootDemoMongodbApplicationTests {
    @Autowired
    private ArticleRepository articleRepo;     // 方式一：Repository

    @Autowired
    private MongoTemplate mongoTemplate;        // 方式二：MongoTemplate

    @Autowired
    private Snowflake snowflake;                // 雪花算法 ID 生成器
}
```

- 测试类继承 `SpringBootDemoMongodbApplicationTests`（带 `@SpringBootTest` 的基类），从而获得 Spring 容器环境。
- 同时注入两种数据访问组件，方便对比。

### 9.2 新增：`testSave` / `testSaveList`

```java
@Test
public void testSave() {
    Article article = new Article(1L, RandomUtil.randomString(20), RandomUtil.randomString(150), 
                                  DateUtil.date(), DateUtil.date(), 0L, 0L);
    articleRepo.save(article);
}

@Test
public void testSaveList() {
    List<Article> articles = Lists.newArrayList();
    for (int i = 0; i < 10; i++) {
        articles.add(new Article(snowflake.nextId(), ...));   // 用雪花算法生成 ID
    }
    articleRepo.saveAll(articles);
}
```

- `save()`：有 `_id` 就 upsert（存在则更新，不存在则插入）。
- 批量插入用 `saveAll()`，但注意它底层是循环 `save`，**不是真正的批量 insert**。大批量数据插入应该用 `MongoTemplate.insertAll()` 或 MongoDB 的 `bulkWrite`，性能高得多。

### 9.3 更新：两种方式对比（本模块精华）

**方式一：`save` 全量覆盖更新（不推荐用于计数场景）**

```java
@Test
public void testThumbUp() {
    articleRepo.findById(1L).ifPresent(article -> {
        article.setThumbUp(article.getThumbUp() + 1);
        article.setVisits(article.getVisits() + 1);
        articleRepo.save(article);    // 整个文档覆盖写回
    });
}
```

问题：先查出来、改内存值、再整体写回。**并发下会丢失更新**（两个请求同时读到 thumbUp=10，各自 +1 写回 11，实际应该是 12）。

**方式二：`MongoTemplate` 原子自增更新（推荐）**

```java
@Test
public void testThumbUp2() {
    Query query = new Query();
    query.addCriteria(Criteria.where("_id").is(1L));   // 条件：_id = 1
    Update update = new Update();
    update.inc("thumbUp", 1L);    // thumbUp 字段原子 +1
    update.inc("visits", 1L);     // visits 字段原子 +1
    mongoTemplate.updateFirst(query, update, "article");   // 只更新匹配的第一条
}
```

- `Criteria.where("_id").is(1L)`：构造查询条件，相当于 SQL 的 `WHERE _id = 1`。
- `Update.inc("thumbUp", 1L)`：原子自增操作，相当于 SQL 的 `SET thumbUp = thumbUp + 1`。
- `updateFirst`：只更新匹配的第一条文档。

**为什么方式二更好？**

1. **原子性**：`$inc` 是 MongoDB 的原子操作，并发安全，不会丢失更新。
2. **高效**：不用先查再写，一次请求搞定，减少一次往返。
3. **局部更新**：只改两个字段，不覆盖整个文档。

> 💡 前端类比：方式一像先 `fetch` 拿到对象、改字段、再 `PUT` 整个对象回去——并发不安全。方式二像直接发一条 `PATCH { $inc: { thumbUp: 1 } }`，数据库原子执行。计数器、库存扣减这类场景必须用方式二。

### 9.4 删除：`testDelete`

```java
@Test
public void testDelete() {
    articleRepo.deleteById(1L);   // 按主键删
    articleRepo.deleteAll();      // 删全部（慎用！）
}
```

### 9.5 分页排序查询：`testQuery`

```java
@Test
public void testQuery() {
    Sort sort = Sort.by("thumbUp", "updateTime").descending();   // 按点赞数、更新时间降序
    PageRequest pageRequest = PageRequest.of(0, 5, sort);         // 第0页，每页5条
    Page<Article> all = articleRepo.findAll(pageRequest);
    log.info("【总页数】= {}", all.getTotalPages());
    log.info("【总条数】= {}", all.getTotalElements());
}
```

- `Sort.by("thumbUp", "updateTime").descending()`：多字段排序，先按 thumbUp 降序，相同再按 updateTime 降序。
- `PageRequest.of(0, 5, sort)`：分页参数，页码从 0 开始（注意不是 1），每页 5 条，带排序。
- `Page<T>`：包含当前页数据、总页数、总条数，和前序 JPA 模块的分页完全一致——Spring Data 的分页抽象是通用的。

> 💡 前端类比：这就像前端分页表格传 `page=1&size=10&sort=thumbUp,desc` 给后端，后端返回 `{ list, total, totalPages }`。Spring Data 的 `Page` 就是这个标准结构。

### 9.6 方法名模糊查询：`testFindByTitleLike`

```java
@Test
public void testFindByTitleLike() {
    List<Article> articles = articleRepo.findByTitleLike("更新");
}
```

调用前面定义的 `findByTitleLike`，Spring Data 自动翻译成 `{ title: { $regex: "更新" } }`。

---

## 十、运行与验证

### 10.1 启动 MongoDB

```sh
docker start mongo-4.1
```

### 10.2 运行测试

在 IDE 里右键运行 `ArticleRepositoryTest` 的各个测试方法，或用 Maven：

```sh
mvn test -pl demo-mongodb
```

### 10.3 查看数据

用 MongoDB 客户端（如 Robo 3T / MongoDB Compass / `mongo` shell）连接 `localhost:27017`，查看 `article_db` 库的 `article` 集合，能看到插入的文档：

```json
{
  "_id": 1,
  "title": "随机字符串",
  "content": "...",
  "createTime": ISODate("2018-12-28T08:00:00Z"),
  "updateTime": ISODate("..."),
  "thumbUp": 1,
  "visits": 1
}
```

控制台 debug 日志能看到实际执行的 MongoDB 命令，例如：

```
find using query: { "_id": 1 } in db.article_db.article
update using query: { "_id": 1 } update: { "$inc": { "thumbUp": 1, "visits": 1 } }
```

---

## 十一、动手练习

1. **加一个字段**：给 `Article` 加 `author` 字段，重新跑测试，观察文档结构变化（体会 MongoDB 的 schema-free 特性——不用建表、不用改表结构）。
2. **改用 URI 配置**：把 `application.yml` 的分项配置改成 `uri: mongodb://localhost:27017/article_db`，验证效果一致。
3. **写一个方法名查询**：在 `ArticleRepository` 加 `findByThumbUpGreaterThanOrderByUpdateTimeDesc(Long thumbUp)`，测试"查询点赞数大于 N 的文章并按更新时间倒序"。
4. **用 MongoTemplate 做条件查询**：用 `MongoTemplate.find(Query, Class)` 查询 title 包含某关键字且 thumbUp 大于某值的文章，对比方法名查询的写法。
5. **加索引**：给 `title` 字段加索引（`@Indexed`），用 `explain()` 观察查询是否走索引。
6. **嵌套文档**：给 `Article` 加一个 `List<Comment> comments` 字段（Comment 是内部类），体会 MongoDB 存嵌套结构比关系型数据库多表 JOIN 简单多少。

---

## 十二、本模块知识点总结（结合实际开发详解）

MongoDB 是 NoSQL 阵营里最常被 Spring Boot 项目采用的数据库，尤其适合内容管理、日志、配置等场景。下面把核心知识点放到真实开发里讲透。

### 12.1 MongoDB vs 关系型数据库：怎么选？

**实际开发中的选型标准：**

| 维度 | 关系型数据库（MySQL） | MongoDB |
| --- | --- | --- |
| 数据结构 | 固定表结构，强 schema | 灵活文档结构，schema-free |
| 关联查询 | 强，JOIN 高效 | 弱，不鼓励 JOIN，靠嵌套文档 |
| 事务 | 强 ACID 事务 | 4.0+ 支持多文档事务，但不如关系型成熟 |
| 扩展性 | 垂直扩展为主，分库分表复杂 | 水平扩展（分片）原生支持 |
| 适用场景 | 订单、账户、财务等强一致性业务 | 内容、日志、配置、IoT 等半结构化数据 |

**最佳实践：不要"非此即彼"**。很多大型系统是**混合架构**：核心交易用 MySQL（强事务），内容/日志/Feed 流用 MongoDB（灵活+高写入），缓存用 Redis。本系列项目里 `demo-mongodb`、`demo-elasticsearch`、`demo-neo4j` 就是让你体会不同数据存储各擅胜场。

**常见坑：**

- 把 MongoDB 当 MySQL 用：设计成大量关联的"关系型"文档，然后用 `$lookup`（相当于 JOIN）查——性能灾难。MongoDB 的正确姿势是**适度冗余、嵌套存储**，一次查询拿全数据。
- 过度依赖 schema-free：以为字段随便加没问题，结果历史文档字段缺失，查询时 NPE。**最佳实践：在代码层用实体类约束字段，数据库层允许灵活**，两者结合。

### 12.2 Spring Data MongoDB 的两种访问方式

**方式一：`MongoRepository`（声明式，推荐简单 CRUD）**

- 优点：零实现，方法名查询直观，分页排序开箱即用。
- 缺点：复杂查询表达不了，批量操作性能差（`saveAll` 是循环）。
- 适用：标准 CRUD、简单条件查询。

**方式二：`MongoTemplate`（命令式，推荐复杂操作）**

- 优点：灵活，能表达任意查询和更新，支持原子操作（`$inc`、`$set`、`$push`）、聚合管道、批量写入。
- 缺点：要手写 Query/Update，代码量多。
- 适用：原子计数、复杂聚合、批量操作、动态条件查询。

**实际开发的最佳实践：两者混用。** Repository 做日常 CRUD，MongoTemplate 做特殊操作（计数、聚合、批量）。本模块的 `testThumbUp2` 就是典型——Repository 做不了原子 `$inc`，必须用 MongoTemplate。

> 💡 前端类比：Repository 像前端用 ORM（Prisma）的便捷 API，MongoTemplate 像直接写原生 SQL/查询语句。简单查询用便捷 API，复杂操作下探到原生。

### 12.3 方法名查询的边界与陷阱

**实际开发中怎么用？**

方法名查询（Derived Query）适合简单、固定条件的查询，写起来飞快。但要注意边界：

1. **方法名长度限制**：Spring Data 对方法名长度有限制，条件太多时方法名会变得很长且难读。
2. **复杂查询表达不了**：如"字段 A 大于 X 且（字段 B 包含 Y 或字段 C 为 null）"这种嵌套逻辑，方法名写不出来。
3. **性能隐患**：`findByTitleLike` 翻译成 `$regex`，**不走索引**（除非是前缀匹配），全表扫描。大数据量下慢。

**最佳实践：**

- 简单查询用方法名，复杂查询用 `@Query` 注解写 MongoDB 查询语句，或直接用 MongoTemplate。
- 模糊查询频繁的字段，考虑用 Elasticsearch 做全文检索（见 `demo-elasticsearch` 模块），而不是 MongoDB 的 `$regex`。

**常见坑：**

- 方法名拼错：`findByTitelLike`（typo）不会报错，但查不到数据，因为 Spring Data 找不到 `titel` 字段。**建议加 `@Query` 显式声明，避免拼写错误。**
- `Like` 的语义：MongoDB 的 `$regex` 默认是包含匹配，不是 SQL 的 `%xxx%` 那么简单，特殊字符（如 `.` `*`）会被当正则元字符，可能查错或报错。用户输入要转义。

### 12.4 主键策略：ObjectId vs 雪花算法 vs 自增

MongoDB 默认主键 `ObjectId` 是 12 字节字符串，包含时间戳、机器ID、进程ID、计数器，天然全局唯一且趋势递增。但本模块用了 `Long` + 雪花算法，为什么？

**三种主键策略对比：**

| 策略 | 类型 | 优点 | 缺点 | 适用 |
| --- | --- | --- | --- | --- |
| ObjectId（默认） | String | 自动生成、全局唯一、趋势递增 | 字符串占空间大、不直观 | 纯 MongoDB 项目 |
| 雪花算法 | Long | 全局唯一、递增、数值型省空间 | 依赖机器时钟，时钟回拨会出问题 | 分布式系统、混合存储 |
| 数据库自增 | Long | 简单直观 | 不适合分片、有锁竞争 | 单机小项目 |

**最佳实践：**

- 纯 MongoDB 项目，直接用 `String` + `ObjectId`，省心。
- 如果业务里 ID 要暴露给前端、参与排序、或和关系型数据库混用，用 `Long` + 雪花算法（本模块做法）。
- 不要用数据库自增 ID 做分布式主键——分片时冲突。

**常见坑：** 雪花算法依赖机器时钟，如果服务器时间回拨（NTP 同步导致），可能生成重复 ID。生产环境要配置 NTP 且容忍小幅回拨，或用 Hutool/Spring 的回拨保护实现。

### 12.5 原子操作：计数器与库存的正确姿势

本模块 `testThumbUp2` 用 `$inc` 做原子自增，这是 MongoDB 的杀手锏之一。

**实际开发中的典型场景：**

- 文章点赞数、浏览量（本模块）
- 商品库存扣减
- 限流计数器（见 `demo-ratelimit-redis` 模块的思路）
- 排行榜分数更新

**为什么必须用原子操作？**

```java
// ❌ 错误：读-改-写，并发不安全
Article a = repo.findById(1L);
a.setThumbUp(a.getThumbUp() + 1);
repo.save(a);

// ✅ 正确：原子 $inc，并发安全
mongoTemplate.updateFirst(
    Query.query(Criteria.where("_id").is(1L)),
    new Update().inc("thumbUp", 1),
    Article.class
);
```

错误写法在并发下会丢失更新（典型竞态条件）。`$inc` 是 MongoDB 服务端原子执行，无论多少并发都不会丢。

**其他常用原子操作符：**

| 操作符 | 作用 | 类比 SQL |
| --- | --- | --- |
| `$inc` | 原子自增/自减 | `SET x = x + 1` |
| `$set` | 设置字段值 | `SET x = value` |
| `$unset` | 删除字段 | `ALTER TABLE DROP COLUMN` |
| `$push` | 数组追加元素 | 无（关系型无数组） |
| `$pull` | 数组移除元素 | 无 |
| `$rename` | 字段重命名 | `ALTER TABLE RENAME` |

> 💡 前端类比：`$inc` 像前端用 `count.value++` 但保证原子性。`$push`/`$pull` 像操作数组 `push`/`filter`，但是数据库级别原子执行——这是 MongoDB 文档模型的优势：数组是一等公民，关系型数据库做不到。

### 12.6 MongoDB 的索引与性能

**实际开发必须关注的：**

MongoDB 也需要建索引，否则查询全表扫描。常用索引：

| 注解/操作 | 作用 |
| --- | --- |
| `@Indexed` | 单字段索引 |
| `@CompoundIndex` | 复合索引 |
| `createIndex()` | 手动建索引 |

**最佳实践：**

1. **查询频繁的字段建索引**：如 `title`、`author`、`createTime`。
2. **复合索引注意顺序**：`{ thumbUp: -1, updateTime: -1 }` 支持 `thumbUp` 排序，也支持 `thumbUp + updateTime` 排序，但不支持单独 `updateTime` 排序（最左前缀原则，和关系型一致）。
3. **索引不是越多越好**：每个索引增加写入开销，MongoDB 写入时要更新所有索引。

**常见坑：**

- `$regex` 模糊查询不走索引（除非前缀固定 `^xxx`），大数据量下慢如蜗牛。全文检索用 Elasticsearch。
- 忘了建索引，数据量小时没感觉，上了百万级后突然变慢。**最佳实践：开发期就用 `explain()` 验证查询计划。**

### 12.7 事务：MongoDB 的事务和 MySQL 不一样

**实际开发认知：**

- MongoDB 4.0 之前：单文档操作是原子的，但**不支持多文档事务**。
- MongoDB 4.0+：支持多文档 ACID 事务（副本集），4.2+ 支持分片事务。
- Spring Data MongoDB 通过 `MongoTransactionManager` 支持声明式事务（`@Transactional`）。

**最佳实践：**

- **不要把 MongoDB 当 MySQL 用事务**。MongoDB 的设计哲学是"通过嵌套文档避免事务"，一个聚合根连同子集合存成一个文档，单文档操作天然原子，不需要事务。
- 真正需要跨文档事务时（如转账），才用 `@Transactional`，但要确保 MongoDB 是副本集（单机版不支持事务）。
- 强事务业务（订单、支付）还是用 MySQL，MongoDB 负责弱事务的内容/日志数据。

> 💡 前端类比：MongoDB 的事务理念像前端的"把相关状态放同一个组件/对象里一起更新"，而不是分散在多个地方再协调。适度冗余、嵌套存储，是 NoSQL 的设计哲学。

### 12.8 生产环境配置清单

**实际部署 MongoDB 项目的配置要点：**

1. **连接池**：Spring Data MongoDB 底层用 MongoDB Java Driver 的连接池，通过 `spring.data.mongodb.uri` 的参数调优：
   ```yaml
   spring:
     data:
       mongodb:
         uri: mongodb://localhost:27017/article_db?maxPoolSize=100&minPoolSize=10
   ```

2. **认证**：生产环境必须开启认证：
   ```yaml
   spring:
     data:
       mongodb:
         uri: mongodb://user:password@host:27017/article_db?authSource=admin
   ```
   密码用环境变量注入：`uri: mongodb://user:${MONGO_PWD}@host...`。

3. **副本集**：生产环境至少副本集（一主二从），保证高可用：
   ```yaml
   spring:
     data:
       mongodb:
         uri: mongodb://host1:27017,host2:27017,host3:27017/article_db?replicaSet=rs0
   ```

4. **读写分离**：读多写少的场景，可以配置读偏好为 `secondaryPreferred`，让读请求分摊到从节点。

5. **监控**：开启 Actuator 的 MongoDB 健康检查（见 `demo-actuator` 模块），配合 MongoDB 自带的 `mongostat`/`mongotop` 工具。

**常见坑：**

- 本地开发用单机版，生产用副本集，配置写法不同，切换时容易出错。**最佳实践：统一用 URI 配置，本地也用 `mongodb://localhost:27017/db`，生产替换即可。**
- 连接池大小不当：默认 `maxPoolSize=100`，高并发下不够，要按业务调优。太小导致请求排队，太大会压垮数据库。

---

> 📌 **学习建议**：MongoDB 是前端工程师最容易上手的数据库——因为它的数据模型就是 JSON，你天天写的前端对象存进去几乎原样保留。学这个模块时，重点体会两件事：一是 Spring Data 的 Repository 抽象让 MongoDB 和 JPA/MyBatis 的使用方式高度统一（换数据源几乎不换代码风格），这是 Spring Boot 的魅力；二是 MongoDB 的原子操作符（`$inc`、`$push`）体现了文档模型相对关系型的优势——数组、嵌套是一等公民，很多关系型数据库要 JOIN 多表的东西，MongoDB 一个文档搞定。但也要清醒：MongoDB 不是银弹，强事务、复杂关联还是关系型数据库的领地。技术选型时，先想清楚数据特征，再选存储。
