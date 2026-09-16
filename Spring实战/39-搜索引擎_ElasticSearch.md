# 39 - Spring Boot 集成 ElasticSearch 搜索引擎

> 对应项目模块：`demo-elasticsearch`
> 前置知识：已学完前 38 个模块，尤其理解 JPA（14 篇）的 Repository 模式、`@Document`/`@Field` 注解、依赖注入
> 学习目标：理解 ElasticSearch 是什么、为什么用它，掌握用 Spring Data ES 完成索引管理、增删改查、复杂查询、聚合查询，并知道 ES 与 MySQL 的本质区别。

---

## 一、本模块要解决什么问题？

### 1.1 为什么 MySQL 做不了全文检索？

假设你有一个商品表，用户在搜索框输入"红色连衣裙"，你用 MySQL 的 `LIKE '%红色连衣裙%'` 去查：

- **慢**：`LIKE '%xxx'` 走不了索引，必须全表扫描，数据量一大就卡死。
- **不准**：搜"红色连衣裙"匹配不到"红色 连衣裙"（中间有空格），也匹配不到"红连衣裙"（少个字）。
- **无相关性排序**：MySQL 只能告诉你"有没有"，不能告诉你"哪个最相关"。

### 1.2 ElasticSearch 是什么？

ElasticSearch（简称 ES）是一个**分布式全文搜索引擎**，底层基于 Lucene。它的核心能力：

| 能力 | 说明 |
| --- | --- |
| 全文检索 | 输入关键词，按相关性打分排序返回结果 |
| 分词 | 中文"红色连衣裙"会被切成"红色""连衣裙"等词，灵活匹配 |
| 模糊匹配 | 容错拼写错误、近义词扩展 |
| 聚合统计 | 类似 SQL 的 GROUP BY，按字段分组统计 |
| 近实时 | 数据写入后约 1 秒可被检索（near real-time） |
| 分布式 | 天然支持集群、分片、副本，水平扩展 |

> 💡 前端类比：ES 之于数据库，有点像 **Algolia / MeiliSearch / ElasticLunr** 之于 MySQL。如果你用过 Algolia 做站内搜索，那 ES 就是它的"重型自托管版"。前端做搜索框联想、商品搜索、日志检索，背后往往是 ES。

### 1.3 本模块做什么？

本模块用 Spring Data Elasticsearch 操作 ES，演示：
1. 创建/删除索引（相当于建表/删表）
2. 增删改查（CRUD）
3. 复杂查询（分词匹配、排序、分页）
4. 聚合查询（分组统计、平均值）

---

## 二、先搞懂 ES 的核心概念（对照 MySQL）

ES 的术语和 MySQL 高度对应，理解这个映射表就懂了一半：

| MySQL | ElasticSearch | 说明 |
| --- | --- | --- |
| Database（数据库） | Index（索引） | ES 7.x 前一个 Index 可含多个 Type，7.x 后取消 Type 概念 |
| Table（表） | Type（类型） | 本模块用 ES 6.x，还有 Type；7.x 后废弃 |
| Row（行） | Document（文档） | 一条记录，JSON 格式 |
| Column（列） | Field（字段） | 文档里的一个键 |
| Schema（表结构） | Mapping（映射） | 定义字段类型、分词器 |
| SQL | Query DSL | ES 用 JSON 描述查询 |

**最关键的概念：倒排索引（Inverted Index）**

传统索引是"文档 → 关键词"（正排），查"含红色的文档"要遍历每篇文档看有没有"红色"。
倒排索引是"关键词 → 文档列表"：

```
红色   → [文档1, 文档3, 文档7]
连衣裙 → [文档1, 文档5]
```

搜"红色"时直接查这个词对应的文档列表，O(1) 级别，这就是 ES 快的本质。

> 💡 前端类比：倒排索引就像一本书后面的"关键词索引页"——你想找"Vue"出现在哪些页，直接查索引页的"Vue"条目，而不是从第一页翻到最后一页。

---

## 三、项目结构

```
demo-elasticsearch/
├── pom.xml
└── src/
    ├── main/java/com/xkcoding/elasticsearch/
    │   ├── SpringBootDemoElasticsearchApplication.java  # 启动类
    │   ├── constants/
    │   │   └── EsConsts.java                             # ES 常量（索引名、类型名）
    │   ├── model/
    │   │   └── Person.java                              # 实体（@Document + @Field）
    │   └── repository/
    │       └── PersonRepository.java                    # DAO（继承 ElasticsearchRepository）
    └── resources/
        └── application.yml                              # ES 连接配置
    └── test/java/com/xkcoding/elasticsearch/
        ├── SpringBootDemoElasticsearchApplicationTests.java  # 测试基类
        ├── template/
        │   └── TemplateTest.java                        # 索引管理测试
        └── repository/
            └── PersonRepositoryTest.java                # 增删改查+聚合测试
```

注意：本模块**没有 Controller 和 Service**，所有操作都在测试类里演示。这是因为 ES 通常作为"搜索基础设施"被 Service 调用，这里为了聚焦 ES 本身，直接在测试里验证。

---

## 四、逐行拆解 pom.xml

```xml
<dependencies>
    <!-- 1. 基础 Starter（不含 Web，因为本模块不提供 HTTP 接口） -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter</artifactId>
    </dependency>

    <!-- 2. ES 起步依赖（核心） -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-data-elasticsearch</artifactId>
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

    <!-- 5. Hutool 工具类（测试里用 DateUtil 解析日期、JSONUtil 打印） -->
    <dependency>
        <groupId>cn.hutool</groupId>
        <artifactId>hutool-all</artifactId>
    </dependency>

    <!-- 6. Guava（测试里用 Lists.newArrayList） -->
    <dependency>
        <groupId>com.google.guava</groupId>
        <artifactId>guava</artifactId>
    </dependency>
</dependencies>
```

重点看第 2 个依赖 `spring-boot-starter-data-elasticsearch`。它引入了：
- Spring Data Elasticsearch（提供 Repository 模式、`@Document` 注解等）
- Elasticsearch Rest 客户端（连接 ES 服务端）

> ⚠️ **版本对应关系（重要）**：Spring Data ES 的版本和 ES 服务端版本必须匹配，否则连不上或报错。本模块 Spring Boot 2.1.0 对应 Spring Data ES 3.1.x，对应 ES 服务端 6.x。这也是 README 里强调要用 `elasticsearch:6.5.3` 镜像的原因。

---

## 五、配置文件 application.yml

```yaml
spring:
  data:
    elasticsearch:
      cluster-name: docker-cluster
      cluster-nodes: localhost:9300
```

- `cluster-name`：ES 集群名，要和 ES 服务端 `elasticsearch.yml` 里的 `cluster.name` 一致（README 里设成了 `docker-cluster`）。
- `cluster-nodes`：ES 节点地址。注意端口是 **9300**（TCP 传输端口），不是 9200（HTTP REST 端口）。

> 💡 端口区别：9200 是给 HTTP 请求用的（curl/浏览器访问），9300 是给 ES 节点间通信和客户端 TCP 连接用的。Spring Data ES 3.x 默认走 9300 的 TransportClient。**新版（4.x+）改用 9200 的 REST 客户端**，配置项也变了。

---

## 六、实体类 Person（核心：@Document + @Field）

`model/Person.java`：

```java
@Document(indexName = EsConsts.INDEX_NAME, type = EsConsts.TYPE_NAME, shards = 1, replicas = 0)
@Data
@NoArgsConstructor
@AllArgsConstructor
public class Person {
    @Id
    private Long id;

    @Field(type = FieldType.Keyword)
    private String name;

    @Field(type = FieldType.Keyword)
    private String country;

    @Field(type = FieldType.Integer)
    private Integer age;

    @Field(type = FieldType.Date)
    private Date birthday;

    @Field(type = FieldType.Text, analyzer = "ik_smart")
    private String remark;
}
```

### 6.1 `@Document` —— 声明索引（相当于"这张表存在哪个库"）

```java
@Document(indexName = "person", type = "person", shards = 1, replicas = 0)
```

| 属性 | 含义 | 前端类比 |
| --- | --- | --- |
| `indexName` | 索引名（库名） | MongoDB 的 collection 名 |
| `type` | 类型名（表名，ES 6.x 有，7.x 废弃） | MongoDB 的 collection 名 |
| `shards` | 主分片数 | 数据分几片存储，决定并发和容量 |
| `replicas` | 副本数 | 每个分片的备份，决定高可用 |

> 💡 分片和副本：假设有 1000 万条数据，分成 5 个主分片，每片 200 万，可以分散在 5 台机器上并行查询。副本是主分片的拷贝，主分片挂了副本顶上。本 demo 单机学习，所以 `replicas = 0`。

### 6.2 `@Id` —— 主键

```java
@Id
private Long id;
```

标记这个字段是文档的唯一标识。写入时如果指定了 id，就是更新；不指定则 ES 自动生成。

### 6.3 `@Field` —— 字段类型与分词器（最关键）

```java
@Field(type = FieldType.Keyword)
private String name;

@Field(type = FieldType.Text, analyzer = "ik_smart")
private String remark;
```

**`Keyword` vs `Text` 是 ES 最容易踩坑的地方：**

| 类型 | 行为 | 适用场景 | 例子 |
| --- | --- | --- | --- |
| `Keyword` | 不分词，整词匹配 | 精确匹配、聚合、排序 | 姓名、国家、标签、状态码 |
| `Text` | 先分词再索引 | 全文检索 | 文章内容、商品描述、备注 |

- `name` 是 `Keyword`：搜"刘备"只能精确匹配"刘备"，搜"刘"匹配不到。
- `remark` 是 `Text` + `ik_smart` 分词器：搜"东汉"能匹配到 remark 里含"东汉"的文档，因为写入时"东汉末年"被 ik 分词器切成了"东汉""末年"等词分别索引。

> 💡 前端类比：`Keyword` 像 JS 的 `===` 严格相等；`Text` 像模糊搜索 `includes()` 但更智能（带分词）。如果你把本该 `Text` 的字段设成 `Keyword`，全文搜索就失效了——这是新手最常犯的错。

`analyzer = "ik_smart"` 指定中文分词器。ES 默认分词器对中文支持极差（会把"东汉末年"切成"东""汉""末""年"单字），需要装 IK 分词器插件（README 里有安装步骤）。

### 6.4 其他字段类型

```java
@Field(type = FieldType.Integer)
private Integer age;

@Field(type = FieldType.Date)
private Date birthday;
```

ES 的字段类型比 MySQL 严格，写入前要确定类型。常见类型：`Keyword`、`Text`、`Integer`、`Long`、`Double`、`Date`、`Boolean`、`Nested`（嵌套对象）、`Ip` 等。

---

## 七、常量类 EsConsts

```java
public interface EsConsts {
    String INDEX_NAME = "person";
    String TYPE_NAME = "person";
}
```

用接口定义常量（接口里的字段默认 `public static final`）。把索引名、类型名集中管理，避免硬编码散落各处。实际开发中也可以用 `class` + `static final` 或配置类。

---

## 八、Repository（DAO 层）

`repository/PersonRepository.java`：

```java
public interface PersonRepository extends ElasticsearchRepository<Person, Long> {

    /**
     * 根据年龄区间查询
     */
    List<Person> findByAgeBetween(Integer min, Integer max);
}
```

### 8.1 `ElasticsearchRepository<Person, Long>`

继承这个接口后，你**什么都不用写**，就自动有了这些方法：

| 方法 | 功能 |
| --- | --- |
| `save(S entity)` | 新增/更新（id 存在则更新） |
| `saveAll(Iterable<S>)` | 批量新增 |
| `findById(ID)` | 按主键查 |
| `findAll()` | 查全部 |
| `findAll(Sort)` | 查全部并排序 |
| `findAll(Pageable)` | 分页查询 |
| `count()` | 计数 |
| `deleteById(ID)` | 按主键删 |
| `delete(T)` | 按对象删 |
| `deleteAll(Iterable)` | 批量删 |

> 💡 这和 JPA 的 `JpaRepository` 几乎一模一样！Spring Data 的设计哲学：**用统一的 Repository 抽象屏蔽不同数据源的差异**——不管是 MySQL（JPA）、ES、MongoDB、Redis，DAO 接口写法都类似。前端类比：像 Prisma 的 `prisma.user.findMany()`，不同数据库用同一套 API。

### 8.2 方法名查询（派生查询）

```java
List<Person> findByAgeBetween(Integer min, Integer max);
```

**你只写了方法名，没写实现，Spring Data 会自动解析方法名生成查询！**

- `findBy` → 查询动作
- `Age` → 字段名 age
- `Between` → 范围条件（age between ? and ?）

常用关键词：

| 方法名关键词 | 生成的查询 | SQL 类比 |
| --- | --- | --- |
| `findByName` | name 精确匹配 | `WHERE name = ?` |
| `findByNameAndAge` | 且 | `WHERE name = ? AND age = ?` |
| `findByNameOrAge` | 或 | `WHERE name = ? OR age = ?` |
| `findByAgeBetween` | 范围 | `WHERE age BETWEEN ? AND ?` |
| `findByAgeLessThan` | 小于 | `WHERE age < ?` |
| `findByNameLike` | 模糊 | `WHERE name LIKE ?` |
| `findByCountryIn` | 包含 | `WHERE country IN (...)` |
| `findByAgeOrderByBirthdayDesc` | 排序 | `ORDER BY birthday DESC` |

> 💡 前端类比：这像 Vue 的"约定式路由"——你按规则命名文件，框架自动生成路由表。这里你按规则命名方法，框架自动生成查询。

---

## 九、索引管理：ElasticsearchTemplate

`TemplateTest.java`：

```java
@Autowired
private ElasticsearchTemplate esTemplate;

@Test
public void testCreateIndex() {
    // 创建索引，会根据 Person 类的 @Document 注解信息来创建
    esTemplate.createIndex(Person.class);
    // 配置映射，会根据 Person 类中的 @Id、@Field 等字段来自动完成映射
    esTemplate.putMapping(Person.class);
}

@Test
public void testDeleteIndex() {
    esTemplate.deleteIndex(Person.class);
}
```

### 9.1 `ElasticsearchTemplate` 是什么？

它是 Spring Data ES 提供的"底层操作入口"，能做 Repository 接口覆盖不到的事：创建/删除索引、配置映射、执行原生 Query DSL 等。

### 9.2 创建索引的两步

1. `createIndex(Person.class)`：根据 `@Document(indexName=...)` 创建空索引（建库）。
2. `putMapping(Person.class)`：根据 `@Field` 注解配置字段类型和分词器（建表结构）。

**为什么分两步？** 因为 ES 的索引（库）和映射（表结构）是分开管理的。你可以先建库，再定义字段类型。如果不显式 `putMapping`，ES 会根据第一条写入的文档**自动推断**字段类型——但推断往往不准（比如把字符串推断成 `Text` 而非你要的 `Keyword`），所以生产环境一定要显式定义 mapping。

> 💡 前端类比：这像 MongoDB 的"无 schema"特性——不定义结构也能写，但生产环境会用 JSON Schema 或 Mongoose 的 Schema 约束类型。ES 的 mapping 就是它的 schema。

---

## 十、增删改查测试：PersonRepositoryTest

这是本模块的核心，演示了从基础 CRUD 到高级聚合的全套操作。

### 10.1 新增（save）

```java
@Test
public void save() {
    Person person = new Person(1L, "刘备", "蜀国", 18, 
        DateUtil.parse("1990-01-02 03:04:05"), "刘备（161年...）");
    Person save = repo.save(person);
}
```

`save` 同时承担新增和更新——**id 在 ES 里不存在就新增，存在就覆盖更新**。这和 JPA 的 `save` 行为一致。

### 10.2 批量新增（saveAll）

```java
@Test
public void saveList() {
    List<Person> personList = Lists.newArrayList();
    personList.add(new Person(2L, "曹操", "魏国", 20, ...));
    personList.add(new Person(3L, "孙权", "吴国", 19, ...));
    personList.add(new Person(4L, "诸葛亮", "蜀国", 16, ...));
    Iterable<Person> people = repo.saveAll(personList);
}
```

`saveAll` 批量写入，比循环 `save` 快得多（减少网络往返）。

### 10.3 更新

```java
@Test
public void update() {
    repo.findById(1L).ifPresent(person -> {
        person.setRemark(person.getRemark() + "\n更新更新更新更新更新");
        repo.save(person);   // id=1 已存在，所以是更新
    });
}
```

ES 的更新是**整文档覆盖**（除非用 `update by script` 部分更新）。这里先查出完整文档，改完再整体写回。

### 10.4 删除

```java
@Test
public void delete() {
    repo.deleteById(1L);                              // 按主键删
    repo.findById(2L).ifPresent(repo::delete);       // 按对象删
    repo.deleteAll(repo.findAll());                   // 批量删
}
```

### 10.5 普通查询（排序）

```java
@Test
public void select() {
    repo.findAll(Sort.by(Sort.Direction.DESC, "birthday"))
        .forEach(person -> log.info("{} 生日: {}", person.getName(), ...));
}
```

`findAll(Sort)` 返回全部并按 birthday 降序。`Sort` 来自 Spring Data 通用排序抽象。

### 10.6 方法名查询（年龄范围）

```java
@Test
public void customSelectRangeOfAge() {
    repo.findByAgeBetween(18, 19)
        .forEach(person -> log.info("{} 年龄: {}", person.getName(), person.getAge()));
}
```

调用第八节定义的派生查询方法，查年龄在 18~19 之间的人（孙权 19、刘备 18）。

---

## 十一、高级查询：QueryBuilders + NativeSearchQuery

当方法名查询表达不了复杂逻辑时，用 `QueryBuilders` 构造查询条件。

### 11.1 简单匹配查询

```java
@Test
public void advanceSelect() {
    MatchQueryBuilder queryBuilder = QueryBuilders.matchQuery("name", "孙权");
    repo.search(queryBuilder).forEach(person -> log.info("【person】= {}", person));
}
```

`QueryBuilders.matchQuery("name", "孙权")` 构造一个 match 查询。但注意 `name` 是 `Keyword` 类型，match 对 keyword 是精确匹配，所以只查到 name 恰好是"孙权"的文档。

### 11.2 自定义复杂查询（分词 + 排序 + 分页）

```java
@Test
public void customAdvanceSelect() {
    NativeSearchQueryBuilder queryBuilder = new NativeSearchQueryBuilder();
    // 1. 分词查询：remark 里含"东汉"的
    queryBuilder.withQuery(QueryBuilders.matchQuery("remark", "东汉"));
    // 2. 按 age 降序
    queryBuilder.withSort(SortBuilders.fieldSort("age").order(SortOrder.DESC));
    // 3. 分页：第 0 页，每页 2 条
    queryBuilder.withPageable(PageRequest.of(0, 2));

    Page<Person> people = repo.search(queryBuilder.build());
    log.info("总条数 = {}", people.getTotalElements());
    log.info("总页数 = {}", people.getTotalPages());
}
```

`NativeSearchQueryBuilder` 是构造复杂查询的建造者，链式拼装查询条件、排序、分页、聚合。`remark` 是 `Text` + `ik_smart`，所以搜"东汉"会匹配到 remark 里含"东汉"的曹操、孙权等。

> 💡 前端类比：`NativeSearchQueryBuilder` 像 axios 的 config 对象——你把 params、headers、transformResponse 等配置拼进去，最后发一个请求。这里把 query、sort、page 拼进去，最后 `build()` 发一个 ES 查询。

### 11.3 返回的 `Page<T>`

`Page<Person>` 是 Spring Data 的分页结果，包含：
- 当前页数据 `getContent()`
- 总条数 `getTotalElements()`
- 总页数 `getTotalPages()`

---

## 十二、聚合查询（Aggregation）

聚合是 ES 的杀手锏，类似 SQL 的 `GROUP BY` + 聚合函数。

### 12.1 简单聚合：求平均年龄

```java
@Test
public void agg() {
    NativeSearchQueryBuilder queryBuilder = new NativeSearchQueryBuilder();
    // 不返回文档，只要聚合结果（省流量）
    queryBuilder.withSourceFilter(new FetchSourceFilter(new String[]{""}, null));
    // 求 age 的平均值，聚合名叫 "avg"
    queryBuilder.addAggregation(AggregationBuilders.avg("avg").field("age"));

    AggregatedPage<Person> people = (AggregatedPage<Person>) repo.search(queryBuilder.build());
    double avgAge = ((InternalAvg) people.getAggregation("avg")).getValue();
}
```

- `AggregationBuilders.avg("avg").field("age")`：对 age 字段求平均值，给这个聚合起名 "avg"。
- `withSourceFilter`：不返回文档原文，只要聚合结果（性能优化）。
- 结果强转 `InternalAvg` 取值。

### 12.2 嵌套聚合：按国家分组 + 每组平均年龄

```java
@Test
public void advanceAgg() {
    NativeSearchQueryBuilder queryBuilder = new NativeSearchQueryBuilder();
    queryBuilder.withSourceFilter(new FetchSourceFilter(new String[]{""}, null));

    // 1. 按国家分桶（terms 聚合）
    queryBuilder.addAggregation(
        AggregationBuilders.terms("country").field("country")
            // 2. 每个桶内再求平均年龄（子聚合）
            .subAggregation(AggregationBuilders.avg("avg").field("age"))
    );

    AggregatedPage<Person> people = (AggregatedPage<Person>) repo.search(queryBuilder.build());

    // 3. 解析结果
    StringTerms country = (StringTerms) people.getAggregation("country");
    for (StringTerms.Bucket bucket : country.getBuckets()) {
        log.info("{} 总共有 {} 人", bucket.getKeyAsString(), bucket.getDocCount());
        InternalAvg avg = (InternalAvg) bucket.getAggregations().asMap().get("avg");
        log.info("平均年龄：{}", avg);
    }
}
```

**聚合的"桶（Bucket）"概念：**

- `terms` 聚合把文档按字段值分到不同"桶"里（蜀国一桶、魏国一桶、吴国一桶）。
- 每个桶里可以再嵌套聚合（`subAggregation`），比如求该桶的平均年龄。
- 结果是一棵树：`country 桶 → [蜀国桶 → avg=17, 魏国桶 → avg=20, 吴国桶 → avg=19]`。

> 💡 前端类比：这像 JavaScript 的 `reduce` 分组统计：
> ```js
> const result = persons.reduce((acc, p) => {
>   if (!acc[p.country]) acc[p.country] = { count: 0, sum: 0 };
>   acc[p.country].count++;
>   acc[p.country].sum += p.age;
>   return acc;
> }, {});
> ```
> ES 的聚合就是把这个操作下推到搜索引擎执行，比拉到内存里算快得多。

---

## 十三、运行与验证

### 13.1 准备 ES 环境（Docker）

按 README 步骤：

```sh
# 拉取 ES 6.5.3 镜像
docker pull elasticsearch:6.5.3

# 运行容器
docker run -d -p 9200:9200 -p 9300:9300 --name elasticsearch-6.5.3 elasticsearch:6.5.3

# 进入容器装 IK 分词器（中文分词必需）
docker exec -it elasticsearch-6.5.3 /bin/bash
./bin/elasticsearch-plugin install https://github.com/medcl/elasticsearch-analysis-ik/releases/download/v6.5.3/elasticsearch-analysis-ik-6.5.3.zip
exit

# 修改配置后重启
docker stop elasticsearch-6.5.3 && docker start elasticsearch-6.5.3
```

### 13.2 验证 ES 启动

浏览器访问 `http://localhost:9200`，返回 JSON 含 `cluster_name: "docker-cluster"` 即正常。

### 13.3 运行测试

在 IDE 里依次运行：
1. `TemplateTest.testCreateIndex()` —— 建索引和映射
2. `PersonRepositoryTest.save()` 和 `saveList()` —— 写入数据
3. `PersonRepositoryTest.select()` / `customSelectRangeOfAge()` / `advanceSelect()` —— 查询
4. `PersonRepositoryTest.agg()` / `advanceAgg()` —— 聚合

### 13.4 用 REST 验证

ES 9200 端口支持 REST，可以直接用 curl 查看数据：

```sh
# 查看索引列表
curl http://localhost:9200/_cat/indices?v

# 查询 person 索引里的全部文档
curl http://localhost:9200/person/_search?pretty
```

---

## 十四、动手练习

1. **加一个字段**：给 Person 加 `email` 字段，类型 `Keyword`，重新建索引，验证写入和查询。
2. **改分词器**：把 `remark` 的分词器从 `ik_smart` 改成 `ik_max_word`（细粒度分词），对比搜"东汉末年"的结果差异。
3. **体会 Keyword vs Text**：把 `name` 改成 `Text` 类型，重新建索引写入，然后用 `matchQuery("name", "刘")` 搜，观察能搜到"刘备"（分词后含"刘"）。
4. **加高亮**：用 `NativeSearchQueryBuilder` 加 `withHighlightFields`，让搜索关键词在结果里高亮显示（前端搜索框常见需求）。
5. **写一个 Service**：把测试里的查询逻辑搬到 `PersonService`，再写个 `PersonController` 提供 `GET /search?keyword=xxx` 接口，体会 ES 在真实 Web 项目里的用法。
6. **对比 MySQL**：同样数据存 MySQL，用 `LIKE '%东汉%'` 查，对比 ES 的 `match` 查询速度和相关性排序。

---

## 十五、本模块知识点总结（结合实际开发详解）

ES 是中大型项目的"搜索标配"，下面把核心知识点放到真实开发场景里讲透。

### 15.1 ES vs MySQL：什么时候该用 ES？

**实际开发中的选型标准：**

| 场景 | 用 MySQL | 用 ES | 理由 |
| --- | --- | --- | --- |
| 按主键查单条 | ✅ | ❌ | MySQL 主键索引极快，没必要搬 ES |
| 精确等值查询（status=1） | ✅ | ❌ | MySQL 索引足够 |
| 多条件过滤（WHERE a=? AND b=?） | ✅ | 视情况 | MySQL 复合索引能搞定 |
| 全文检索（搜文章内容） | ❌ | ✅ | MySQL LIKE 全表扫描，ES 倒排索引秒查 |
| 模糊搜索、容错搜索 | ❌ | ✅ | ES 支持 fuzzy、纠错 |
| 相关性排序 | ❌ | ✅ | ES 按打分排序，MySQL 无相关性概念 |
| 聚合统计（GROUP BY） | ✅（数据小） | ✅（数据大） | ES 聚合在分布式上并行，大数据更快 |
| 事务、强一致 | ✅ | ❌ | ES 不支持事务，近实时（1 秒延迟） |

**最佳实践：MySQL 作为主存储（保证数据一致性和事务），ES 作为搜索副本（通过 Canal/Logstash 同步数据到 ES，专门负责搜索）。** 这是电商、内容平台的标配架构。

**常见坑：**

- 把 ES 当主数据库用：ES 不支持事务，写入后约 1 秒才可检索（refresh interval），强一致场景会出问题。
- 以为 ES 和 MySQL 数据实时一致：ES 写入有延迟，且同步链路可能失败，重要业务要查 MySQL。
- 小项目也上 ES：ES 部署运维成本高（集群、内存、调优），数据量小用 MySQL LIKE 或加索引就够了。

### 15.2 Mapping 设计：字段类型决定一切

**实际开发中 Mapping 设计的要点：**

1. **Keyword vs Text 选错是头号坑**：
   - 需要精确匹配、聚合、排序的字段（状态、分类、标签、ID）→ `Keyword`
   - 需要全文检索的字段（标题、内容、描述）→ `Text`
   - 一个字段既要检索又要聚合？用 `fields` 多字段类型：
     ```json
     "title": { "type": "text", "fields": { "keyword": { "type": "keyword" } } }
     ```

2. **数字类型别用字符串**：年龄、金额用 `Integer`/`Long`/`Double`，才能范围查询和聚合。设成 `Keyword` 会导致 `age > 18` 这种查询失效。

3. **日期类型**：用 `Date`，ES 支持多种格式，能做时间范围查询和日期直方图聚合（按天/月统计）。

4. **嵌套对象**：用户有多个标签，用 `Nested` 类型而非 `Object`，否则数组里的对象会被"打平"导致查询错乱。

5. **生产环境一定要显式定义 Mapping**：不要依赖 ES 自动推断，自动推断的类型往往不符合预期。

**常见坑：**

- 字段类型定错后**不能直接改**！ES 不支持修改已有字段的 mapping，只能新建索引、reindex 迁移数据、再切别名。所以设计阶段要想清楚。
- `Text` 字段默认不能聚合和排序（因为分词了），要聚合得加 `.keyword` 子字段。

### 15.3 Spring Data ES 的两层 API

本模块用了两层 API，实际开发中要分清：

| 层 | API | 适用场景 |
| --- | --- | --- |
| 高层 | `ElasticsearchRepository`（接口） | 标准 CRUD、方法名查询、简单分页 |
| 底层 | `ElasticsearchTemplate` / `RestHighLevelClient` | 索引管理、复杂 Query DSL、聚合、批量操作 |

**实际开发建议：**

- 简单 CRUD 用 Repository 接口，零代码。
- 复杂查询用 `NativeSearchQueryBuilder`（本模块演示）或直接用 `RestHighLevelClient`（更灵活，后续 `demo-elasticsearch-rest-high-level-client` 模块会讲）。
- Service 层封装，Controller 调 Service，不要让 Controller 直接碰 Repository。

> 💡 前端类比：Repository 像 React Query 的 `useQuery` 封装，开箱即用；Template/Client 像 `fetch` 原始调用，灵活但要自己处理细节。

### 15.4 聚合查询：ES 的杀手锏

**实际开发中聚合的典型应用：**

- **电商**：按品牌、价格区间、规格分面（facet）筛选，左侧筛选栏的数据来源。
- **日志分析**：按时间直方图统计错误数（ELK 的核心能力）。
- **报表**：按地区分组统计用户数、按渠道分组统计转化率。

**最佳实践：**

1. 聚合字段必须是 `Keyword` 或数字/日期类型，`Text` 不能直接聚合（要加 `.keyword`）。
2. 大数据量聚合用 `cardinality`（去重计数）要注意精度（HyperLogLog 算法有误差）。
3. 嵌套聚合层数别太深，性能会急剧下降。
4. 聚合结果配合 `size: 0`（不返回文档），只取聚合值，省网络。

**常见坑：**

- 在 `Text` 字段上聚合报错或结果不对——改成 `Keyword` 或 `.keyword` 子字段。
- 聚合的 `size` 默认只返回 10 个桶，想要更多要显式设 `size`。

### 15.5 分词器：中文搜索的关键

**实际开发要点：**

- ES 默认分词器对中文是"逐字切分"（"东汉末年"→"东""汉""末""年"），基本不可用。
- 装中文分词器插件（IK 最常用），有两种模式：
  - `ik_smart`：粗粒度，"东汉末年"切成"东汉""末年"，适合搜索。
  - `ik_max_word`：细粒度，切成"东汉""汉末""末年"等更多词，适合索引。
- 生产常用组合：**索引时用 `ik_max_word`（多切词，召回率高），搜索时用 `ik_smart`（少切词，精准）**：
  ```json
  "remark": {
    "type": "text",
    "analyzer": "ik_max_word",
    "search_analyzer": "ik_smart"
  }
  ```
- 自定义词库：人名、品牌名、专业术语，IK 默认词典没有，要配置扩展词典。

**常见坑：**

- 装了 IK 但忘重启 ES，分词器不生效。
- 索引和搜索用不同分词器，导致搜不到——要保证分词结果有交集。

### 15.6 版本对应：Spring Data ES 最大的坑

**这是实际开发中最容易踩的坑，没有之一。**

Spring Data ES 的版本和 ES 服务端版本有严格对应关系：

| Spring Boot | Spring Data ES | ES 服务端版本 |
| --- | --- | --- |
| 2.1.x（本模块） | 3.1.x | 6.x |
| 2.2~2.5 | 4.x | 7.x |
| 3.x | 5.x | 8.x |

**版本不匹配的后果：**

- 客户端连不上服务端（协议变了）。
- 注解 API 变了（如 ES 7.x 后 `@Document` 的 `type` 属性废弃）。
- `ElasticsearchTemplate` 在 4.x 被废弃，换成 `ElasticsearchRestTemplate`。
- 配置项变了（`cluster-nodes` 9300 换成 `uris` 9200）。

**最佳实践：**

- 先确定 ES 服务端版本，再反查该用哪个 Spring Boot / Spring Data ES 版本。
- 新项目直接用 ES 7.x+ 和 Spring Boot 2.5+，走 REST 客户端（9200 端口），TransportClient（9300）已废弃。
- 本模块用的是 6.x + TransportClient，属于"老写法"，后续 `demo-elasticsearch-rest-high-level-client` 模块会演示新版 REST 客户端写法。

### 15.7 数据同步：MySQL 到 ES

实际项目里数据通常存在 MySQL，搜索走 ES，需要把 MySQL 数据同步到 ES。常见方案：

| 方案 | 原理 | 优缺点 |
| --- | --- | --- |
| 同步双写 | 代码里写 MySQL 的同时写 ES | 简单但侵入业务，性能差，不推荐 |
| 异步 MQ | 写 MySQL 后发 MQ，消费者写 ES | 解耦，但要保证消息可靠 |
| Canal 同步 | 监听 MySQL binlog，解析后写 ES | 对业务零侵入，最主流方案 |
| Logstash 定时拉 | 定时 SQL 查 MySQL 写 ES | 简单但有延迟，适合非实时场景 |

**最佳实践：** 中大型项目用 Canal 监听 binlog 实时同步，小项目用定时任务批量同步。搜索服务挂了不能影响主业务（MySQL 依然可用），这是"搜索副本"架构的韧性所在。

---

> 📌 **学习建议**：作为前端工程师，理解 ES 最重要的是建立"倒排索引"和"分词"两个概念——它们和前端熟悉的"数组 filter"完全不同，是 ES 速度和智能的根源。建议先把本模块的 CRUD 和聚合测试跑通，再用 curl 直接访问 9200 端口看 ES 返回的原始 JSON，你会对"文档型存储"有更直观的感受。另外，ES 的版本对应关系是实战大坑，新项目务必走 REST 客户端 + ES 7.x+ 的路线，别照搬本模块的 6.x 老写法。
