# 45 - 分库分表 ShardingSphere-JDBC

> 对应项目模块：`demo-sharding-jdbc`
> 前置知识：已学完数据库操作系列（13-18），了解 MyBatis-Plus 基本用法
> 学习目标：理解为什么要分库分表，掌握 ShardingSphere-JDBC 的分库分表原理，能看懂并改写本模块的分片配置。

---

## 一、本模块要解决什么问题？

### 1.1 单库单表的瓶颈

随着业务增长，单张表的数据量可能达到千万、亿级，这时会出现明显问题：

- **查询慢**：B+ 树索引在千万级数据下，回表、范围扫描代价急剧上升
- **写入慢**：锁表、索引维护成本高
- **单机容量上限**：磁盘、内存装不下
- **单点故障**：一台数据库挂了，全站不可用

> 💡 前端类比：这就像一个前端数组太大，渲染卡顿，你用"虚拟列表"分片渲染。数据库的"分片"思路类似——把一张大表拆成多张小表，把一个库拆成多个库。

### 1.2 拆分方式

| 拆分维度 | 含义 | 举例 |
| --- | --- | --- |
| **垂直分库** | 按业务拆成不同库 | 订单库、用户库、商品库分开 |
| **垂直分表** | 一张表字段太多，拆成多张 | 把 `user` 的基本信息和扩展信息拆开 |
| **水平分库** | 同一张表的数据按规则分散到多个库 | 按 `user_id % 2` 分到 ds0/ds1 |
| **水平分表** | 同一张表的数据按规则分散到多张表 | 按 `order_id % 3` 分到 t_order_0/1/2 |

本模块演示的是**水平分库 + 水平分表**：2 个库 × 3 张表 = 6 个物理分片。

### 1.3 ShardingSphere-JDBC 是什么？

Apache ShardingSphere 是一套分布式数据库中间件生态，它有三个产品：

| 产品 | 形态 | 特点 |
| --- | --- | --- |
| **ShardingSphere-JDBC** | JDBC 驱动增强 | 嵌入应用，改造成本低，本模块用这个 |
| **ShardingSphere-Proxy** | 独立数据库代理 | 应用无感知，但多一层网络转发 |
| **ShardingSphere-Sidecar** | 旁路 | 云原生场景 |

ShardingSphere-JDBC 的核心思想：**在 JDBC 层拦截 SQL，根据分片规则改写 SQL 路由到正确的物理库/表，再把结果合并返回**。对上层应用来说，它就像一个"虚拟的单一数据源"。

> 💡 前端类比：这像前端在 `axios` 里加了一个请求拦截器，根据 URL 把请求分发到不同后端，但对业务代码来说只调一个 `axios`。ShardingSphere-JDBC 就是数据库层的"请求拦截器"。

---

## 二、项目结构

```
demo-sharding-jdbc/
├── pom.xml
├── sql/schema.sql                  # 建库建表脚本（2库×3表=6张物理表）
└── src/main/java/com/xkcoding/sharding/jdbc/
    ├── SpringBootDemoShardingJdbcApplication.java  # 启动类
    ├── config/
    │   ├── DataSourceShardingConfig.java   # 核心：分库分表配置
    │   └── CustomSnowflakeKeyGenerator.java # 自定义雪花算法主键
    ├── model/
    │   └── Order.java                      # 订单实体（逻辑表 t_order）
    └── mapper/
        └── OrderMapper.java                # MyBatis-Plus Mapper
```

注意：本模块**没有 Controller**，只有测试类验证。ORM 层用 MyBatis-Plus 简化，但 README 明确说可以替换成 JPA、通用 Mapper、JdbcTemplate 甚至原生 JDBC——ShardingSphere-JDBC 在数据源层工作，对上层 ORM 无感知。

---

## 三、逐行拆解 pom.xml

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter</artifactId>
</dependency>

<dependency>
    <groupId>com.baomidou</groupId>
    <artifactId>mybatis-plus-boot-starter</artifactId>
    <version>3.1.0</version>
</dependency>

<dependency>
    <groupId>mysql</groupId>
    <artifactId>mysql-connector-java</artifactId>
</dependency>

<dependency>
    <groupId>io.shardingsphere</groupId>
    <artifactId>sharding-jdbc-core</artifactId>
    <version>3.1.0</version>
</dependency>
```

关键点：

1. **`spring-boot-starter`**（不是 web）：本模块只做数据层演示，不需要 Web 接口，所以用最小 starter。
2. **`sharding-jdbc-core` 3.1.0**：注意 groupId 是 `io.shardingsphere`，这是当当维护的老版本。后来 ShardingSphere 进入 Apache，新版本 groupId 变成 `org.apache.shardingsphere`，artifactId 变成 `shardingsphere-jdbc-core`。**版本差异是踩坑重灾区**。
3. **MyBatis-Plus 3.1.0**：这里手写了版本号，因为父 POM 没有管理它。实际项目应该统一在父 POM 管理。

> ⚠️ README 提到"当当官方提供的 starter 存在 bug，因此本 demo 采用手动配置"。意思是没用 `sharding-jdbc-spring-boot-starter`，而是自己写 `@Configuration` 类手动组装数据源。这是 3.1.0 时代的权宜之计，新版本 starter 已经稳定，实际项目推荐用 starter 配置。

---

## 四、SQL 脚本：物理表结构

`sql/schema.sql` 建了 2 个库，每个库 3 张表：

```sql
USE `spring-boot-demo`;          -- 库1：ds0
CREATE TABLE `t_order_0` (...);   -- 表0
CREATE TABLE `t_order_1` (...);   -- 表1
CREATE TABLE `t_order_2` (...);   -- 表2

USE `spring-boot-demo-2`;         -- 库2：ds1
CREATE TABLE `t_order_0` (...);   -- 表0
CREATE TABLE `t_order_1` (...);   -- 表1
CREATE TABLE `t_order_2` (...);   -- 表2
```

每张表结构相同：`id`（主键）、`user_id`、`order_id`、`remark`。

**关键概念：逻辑表 vs 物理表**

- **逻辑表**：`t_order`，你在代码里写的表名，ShardingSphere 看到的
- **物理表**：`t_order_0`、`t_order_1`、`t_order_2`，真实存在的表

应用写 `INSERT INTO t_order ...`，ShardingSphere 根据分片规则改写成 `INSERT INTO t_order_X ...` 路由到具体物理表。

---

## 五、核心：分库分表配置类

`config/DataSourceShardingConfig.java` 是本模块的灵魂。我们逐段拆解。

### 5.1 整体结构

```java
@Configuration
public class DataSourceShardingConfig {
    private static final Snowflake snowflake = IdUtil.createSnowflake(1, 1);

    @Bean
    public DataSourceTransactionManager transactionManager(...) { ... }

    @Bean(name = "dataSource")
    @Primary
    public DataSource dataSource() throws SQLException { ... }

    private TableRuleConfiguration orderTableRule() { ... }

    private Map<String, DataSource> dataSourceMap() { ... }

    private KeyGenerator customKeyGenerator() { ... }
}
```

这个类做了三件事：配置真实数据源、定义分片规则、组装成 ShardingSphere 的虚拟数据源。

### 5.2 真实数据源 `dataSourceMap()`

```java
private Map<String, DataSource> dataSourceMap() {
    Map<String, DataSource> dataSourceMap = new HashMap<>(16);

    HikariDataSource ds0 = new HikariDataSource();
    ds0.setJdbcUrl("jdbc:mysql://127.0.0.1:3306/spring-boot-demo?...");
    ds0.setUsername("root");
    ds0.setPassword("root");

    HikariDataSource ds1 = new HikariDataSource();
    ds1.setJdbcUrl("jdbc:mysql://127.0.0.1:3306/spring-boot-demo-2?...");
    ds1.setUsername("root");
    ds1.setPassword("root");

    dataSourceMap.put("ds0", ds0);
    dataSourceMap.put("ds1", ds1);
    return dataSourceMap;
}
```

- 配置了两个 HikariCP 连接池，分别连两个库。
- 放进 Map，key 是 `ds0`/`ds1`（数据源逻辑名），后面分片规则用这个名字引用。

> 💡 前端类比：这像在前端定义两个 API baseURL，`apiMap = { ds0: 'http://db0', ds1: 'http://db1' }`，后面路由规则根据 key 选哪个。

### 5.3 分片规则 `dataSource()`

```java
@Bean(name = "dataSource")
@Primary
public DataSource dataSource() throws SQLException {
    ShardingRuleConfiguration shardingRuleConfig = new ShardingRuleConfiguration();
    // 1. 分库策略：按 user_id 取模
    shardingRuleConfig.setDefaultDatabaseShardingStrategyConfig(
        new InlineShardingStrategyConfiguration("user_id", "ds${user_id % 2}"));
    // 2. 绑定表组
    shardingRuleConfig.getBindingTableGroups().add("t_order");
    // 3. 分表规则
    shardingRuleConfig.getTableRuleConfigs().add(orderTableRule());
    // 4. 默认数据源
    shardingRuleConfig.setDefaultDataSourceName("ds0");
    // 5. 默认分表策略：不分表
    shardingRuleConfig.setDefaultTableShardingStrategyConfig(new NoneShardingStrategyConfiguration());

    Properties properties = new Properties();
    properties.setProperty("sql.show", "true");

    return ShardingDataSourceFactory.createDataSource(dataSourceMap(), shardingRuleConfig, new ConcurrentHashMap<>(16), properties);
}
```

逐条解释：

**1. 分库策略**：`InlineShardingStrategyConfiguration("user_id", "ds${user_id % 2}")`

- 分片键是 `user_id` 字段
- 分片算法是行内表达式 `ds${user_id % 2}`：`user_id` 是偶数 → `ds0`，奇数 → `ds1`

**2. 绑定表组**：`add("t_order")`

- 绑定表（Binding Table）指那些分片规则一致、经常 join 的表。声明后，ShardingSphere 保证它们的分片落在同一数据源，避免跨库 join。

**3. 分表规则**：交给 `orderTableRule()` 方法（见下节）。

**4. 默认数据源**：`ds0`。不在分片规则里的表，都走 ds0。

**5. `sql.show=true`**：打印实际路由到的物理 SQL，调试神器。启动后控制台会看到改写后的真实 SQL。

### 5.4 分表规则 `orderTableRule()`

```java
private TableRuleConfiguration orderTableRule() {
    TableRuleConfiguration tableRule = new TableRuleConfiguration();
    tableRule.setLogicTable("t_order");                              // 逻辑表名
    tableRule.setActualDataNodes("ds${0..1}.t_order_${0..2}");       // 物理节点
    tableRule.setTableShardingStrategyConfig(
        new InlineShardingStrategyConfiguration("order_id", "t_order_$->{order_id % 3}"));  // 分表策略
    tableRule.setKeyGenerator(customKeyGenerator());                 // 主键生成器
    tableRule.setKeyGeneratorColumnName("order_id");                 // 主键列
    return tableRule;
}
```

**逻辑表**：`t_order`，代码里写的表名。

**物理节点**：`ds${0..1}.t_order_${0..2}`

这是 Groovy 表达式，展开后表示 2 库 × 3 表 = 6 个物理位置：
- `ds0.t_order_0`、`ds0.t_order_1`、`ds0.t_order_2`
- `ds1.t_order_0`、`ds1.t_order_1`、`ds1.t_order_2`

> 💡 `${0..1}` 是范围展开，`$->{...}` 是新版表达式语法（避免和 Spring 占位符冲突）。

**分表策略**：`InlineShardingStrategyConfiguration("order_id", "t_order_$->{order_id % 3}")`

- 分片键是 `order_id`
- `order_id % 3`：结果 0/1/2 → 路由到 `t_order_0`/`t_order_1`/`t_order_2`

**主键生成**：用自定义雪花算法生成 `order_id`。

### 5.5 路由结果示例

假设插入一条 `user_id=1, order_id=2` 的记录：

- 分库：`1 % 2 = 1` → `ds1`
- 分表：`2 % 3 = 2` → `t_order_2`
- 最终路由到：`ds1.t_order_2`

ShardingSphere 把 `INSERT INTO t_order` 改写成 `INSERT INTO t_order_2`，发往 ds1 数据源。

### 5.6 事务管理器

```java
@Bean
public DataSourceTransactionManager transactionManager(@Qualifier("dataSource") DataSource dataSource) {
    return new DataSourceTransactionManager(dataSource);
}
```

因为手动配置了数据源，Spring Boot 的自动配置不再生效，必须手动声明事务管理器。它绑定的是 ShardingSphere 的虚拟数据源——ShardingSphere 内部会处理跨库事务（注意：3.x 的跨库事务是"尽量保证"，不是严格 XA）。

---

## 六、自定义主键生成器

`config/CustomSnowflakeKeyGenerator.java`：

```java
public class CustomSnowflakeKeyGenerator implements KeyGenerator {
    private Snowflake snowflake;

    public CustomSnowflakeKeyGenerator(Snowflake snowflake) {
        this.snowflake = snowflake;
    }

    @Override
    public Number generateKey() {
        return snowflake.nextId();
    }
}
```

为什么不用 ShardingSphere 自带的 `DefaultKeyGenerator`？注释说：

> 避免 DefaultKeyGenerator 生成的 id 大几率是偶数

这是个真实存在的坑：ShardingSphere 默认雪花算法的 workerId 和时钟位设计，导致生成的 ID 偶数概率偏高。而本模块分表策略是 `order_id % 3`，如果 ID 分布不均，会导致数据倾斜（某些表数据多，某些少）。

所以这里换成 Hutool 的 `Snowflake`，它生成的 ID 分布更均匀。`IdUtil.createSnowflake(1, 1)` 的两个参数是 workerId 和 dataCenterId。

> 💡 前端类比：这像你用 `Math.random()` 做哈希分片，如果随机数分布不均，某些分片会过载。主键生成器的均匀性直接影响分片均衡。

---

## 七、实体与 Mapper

### 7.1 Order 实体

```java
@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
@TableName(value = "t_order")
public class Order {
    private Long id;
    private Long userId;
    private Long orderId;
    private String remark;
}
```

- `@TableName("t_order")`：MyBatis-Plus 的逻辑表名，对应 ShardingSphere 的逻辑表。
- 注意有 `id`、`user_id`、`order_id` 三个 ID 字段：`id` 是物理主键，`user_id` 是分库键，`order_id` 是分表键。实际业务中通常用一个字段既做主键又做分片键，这里为了演示拆开了。

### 7.2 OrderMapper

```java
@Component
public interface OrderMapper extends BaseMapper<Order> {
}
```

继承 MyBatis-Plus 的 `BaseMapper`，自动获得 `insert`/`update`/`delete`/`selectList` 等方法。**关键点：Mapper 层完全不知道分库分表的存在**——它只对逻辑表 `t_order` 操作，分片由 ShardingSphere 在数据源层透明处理。这就是 ShardingSphere-JDBC 的价值：**对 ORM 零侵入**。

---

## 八、启动类

```java
@SpringBootApplication
@EnableTransactionManagement(proxyTargetClass = true)
@MapperScan("com.xkcoding.sharding.jdbc.mapper")
public class SpringBootDemoShardingJdbcApplication {
    public static void main(String[] args) {
        SpringApplication.run(SpringBootDemoShardingJdbcApplication.class, args);
    }
}
```

- `@EnableTransactionManagement(proxyTargetClass = true)`：显式开启事务，`proxyTargetClass` 强制用 CGLIB 代理（兼容无接口的类）。
- `@MapperScan`：扫描 Mapper 接口包。

---

## 九、测试类：验证分库分表

```java
@Test
public void testInsert() {
    for (long i = 1; i < 10; i++) {        // user_id: 1-9
        for (long j = 1; j < 20; j++) {    // order_id: 1-19
            Order order = Order.builder().userId(i).orderId(j).remark(RandomUtil.randomString(20)).build();
            orderMapper.insert(order);
        }
    }
}
```

插入 9 × 19 = 171 条记录。因为 `sql.show=true`，控制台会打印每条 SQL 实际路由到的库和表。你会看到数据均匀分布在 6 张物理表里。

```java
@Test
public void testSelect() {
    List<Order> orders = orderMapper.selectList(Wrappers.<Order>query().lambda().in(Order::getOrderId, 1, 2));
    log.info("【orders】= {}", JSONUtil.toJsonStr(orders));
}
```

查询 `order_id IN (1, 2)`。ShardingSphere 会把这条 SQL **广播**到所有匹配的分片（这里 order_id 不确定，会路由到所有 6 张表），合并结果返回。这就是分库分表后查询代价上升的原因——一条逻辑 SQL 变成多条物理 SQL。

---

## 十、运行与验证

### 10.1 准备环境

1. 创建两个数据库：`spring-boot-demo` 和 `spring-boot-demo-2`
2. 执行 `sql/schema.sql`，在两个库各建 3 张表（共 6 张）
3. 修改 `DataSourceShardingConfig.dataSourceMap()` 里的数据库连接信息（用户名密码）

### 10.2 运行测试

运行 `SpringBootDemoShardingJdbcApplicationTests`，观察：

- `testInsert`：控制台打印 171 条路由日志，能看到每条记录分到哪个库哪个表
- `testSelect`：查询会广播到多张表，结果合并
- 直接查数据库：6 张表都有数据，分布均匀

---

## 十一、动手练习

1. **观察路由**：运行 `testInsert`，从控制台日志找出 `user_id=3, order_id=5` 这条记录路由到了哪个库哪个表，手动验证 `3%2` 和 `5%3` 的结果。
2. **改分片数**：把分表数从 3 改成 4（`order_id % 4`，物理表加到 4 张），重新建表测试，观察数据分布。
3. **跨分片查询**：写一个不带分片键的查询 `selectList(null)`，观察 ShardingSphere 如何广播到所有分片。
4. **带分片键查询**：写一个 `user_id=2 AND order_id=1` 的精确查询，观察是否只路由到一个分片（精准路由 vs 广播）。
5. **数据倾斜**：把主键生成器换回 ShardingSphere 默认的 `DefaultKeyGenerator`，插入大量数据，统计各表数据量，观察是否倾斜。
6. **加一张分片表**：新建 `t_order_item` 表，用相同的 `user_id` 分库策略，配置成 `t_order` 的绑定表，测试 join 查询是否落在同库。

---

## 十二、本模块知识点总结（结合实际开发详解）

分库分表是数据库架构演进的"最后一道防线"，只有在单库优化（索引、缓存、读写分离）都做完后才考虑。下面把核心知识点放到真实开发场景里讲透。

### 12.1 什么时候该分库分表？

**判断标准（经验值）：**

| 指标 | 阈值 | 说明 |
| --- | --- | --- |
| 单表数据量 | > 1000 万 | B+ 树高度增加，查询性能下降 |
| 单表数据量 | > 5000 万 | 深度分页、复杂查询明显变慢 |
| 单库数据量 | > 100GB | 备份、恢复、DDL 变慢 |
| 单库 QPS | > 5000 | 写入瓶颈、锁竞争 |

**实际开发的演进路径（不要一上来就分）：**

1. **优化 SQL + 索引**：80% 的慢查询是 SQL 写得烂、缺索引
2. **加缓存**：Redis 扛住 80% 读流量
3. **读写分离**：主库写，从库读，扩容读能力
4. **垂直分库**：按业务拆库（订单、用户、商品分开）
5. **水平分库分表**：单表数据量实在太大才用

**常见坑：过早分片**。很多团队表才几十万行就上 ShardingSphere，结果引入复杂度远大于收益。**分片是最后手段，不是第一选择。**

### 12.2 分片键的选择：分库分表的灵魂

分片键（Sharding Key）决定了数据落到哪个分片，选错后果严重。

**好的分片键标准：**

1. **高基数**：取值范围广，能均匀分散数据（如 user_id）
2. **查询频繁**：大部分查询都带这个字段，能做精准路由
3. **不可变**：一旦写入不修改（修改分片键要迁移数据）
4. **单调递增**（可选）：避免页分裂，如自增 ID、时间戳

**本模块的选择**：分库用 `user_id`，分表用 `order_id`。这是典型的"双键分片"。

**常见坑：**

- **选了低基数字段**：如按"性别"分片，只有 2 个值，数据严重倾斜。
- **选了会变的字段**：如按"用户状态"分片，状态变更要跨分片迁移数据。
- **查询不带分片键**：导致全分片广播，性能比单表还差。比如本模块查 `remark LIKE '%xxx%'`，必须扫所有 6 张表。

> 💡 前端类比：分片键像前端分片渲染的 `item.id`，查询时要带上它才能精确定位到某个分片，否则只能遍历所有分片。

### 12.3 分片算法：行内表达式 vs 标准算法

本模块用的是 `InlineShardingStrategyConfiguration`，即行内表达式分片：

```java
new InlineShardingStrategyConfiguration("user_id", "ds${user_id % 2}")
```

**行内表达式的优点**：配置简单，一行搞定取模分片。

**行内表达式的局限**：只能做简单取模/哈希，无法应对复杂场景。ShardingSphere 还提供：

| 算法 | 适用场景 |
| --- | --- |
| **Inline（行内表达式）** | 简单取模，本模块用 |
| **Standard（标准分片）** | 支持 `=`、`IN`、`BETWEEN`，需自己实现 `PreciseShardingAlgorithm` 和 `RangeShardingAlgorithm` |
| **Complex（复合分片）** | 多个分片键，如 `user_id + order_date` |
| **Hint（强制路由）** | 不用 SQL 字段，用代码指定分片 |

**实际开发建议**：简单取模用 Inline；需要范围查询（如按时间范围查某月数据）用 Standard + 范围分片算法；多维度查询用 Complex 或 Hint。

### 12.4 广播表、绑定表、父子表

ShardingSphere 有几个表类型概念，实际开发必懂：

| 类型 | 含义 | 举例 |
| --- | --- | --- |
| **广播表（Broadcast Table）** | 所有库都有一份完整副本，用于小表 join | 字典表、配置表 |
| **绑定表（Binding Table）** | 分片规则一致的表，保证 join 同库 | `t_order` 和 `t_order_item` 都按 `order_id` 分片 |
| **父子表** | 父子表分片一致，支持关联插入 | 订单和订单明细 |

**本模块的 `getBindingTableGroups().add("t_order")`** 声明了绑定表组。如果再加一张 `t_order_item` 用相同分片键，join 时不会跨库笛卡尔积。

**常见坑**：两张表分片键不同却 join，会导致笛卡尔积路由——M 张表 × N 个分片 = M×N 次 SQL，性能灾难。

### 12.5 分布式事务：分库分表后的难题

分库分表后，一个业务操作可能跨多个库，传统本地事务失效。ShardingSphere 支持几种事务类型：

| 事务类型 | 一致性 | 性能 | 适用场景 |
| --- | --- | --- | --- |
| **LOCAL 本地事务** | 尽量保证 | 高 | 对一致性要求不高 |
| **XA 两阶段提交** | 强一致 | 低 | 银行、金融 |
| **BASE 柔性事务** | 最终一致 | 中 | 互联网业务 |

本模块用的是 `DataSourceTransactionManager`，即 LOCAL 事务。它**不能保证跨库强一致**：如果操作 ds0 成功、ds1 失败，ds0 不会回滚。

**实际开发建议**：

- 对强一致要求的场景，用 XA（性能差但安全）
- 对最终一致可接受的场景，用 BASE（Saga/TCC 模式，配合消息队列补偿）
- 大部分互联网业务用最终一致，配合幂等性和对账机制兜底

### 12.6 分页查询：分库分表后的性能陷阱

分库分表后，`LIMIT 10, 20`（深分页）会变成灾难：

ShardingSphere 处理分页的流程：
1. 对每个分片执行 `LIMIT 0, 30`（取前 30 条，因为要合并 3 张表的前 10-20）
2. 内存合并、排序、取第 10-20 条

**深分页问题**：查 `LIMIT 1000000, 20` 时，每个分片要查 1000020 条数据到内存，再合并。内存爆炸、性能崩溃。

**实际开发的解决方案：**

1. **用游标分页（推荐）**：`WHERE id > last_id ORDER BY id LIMIT 20`，每次记住上一页最后一条 id，避免 offset
2. **用 ES 辅助查询**：把需要复杂查询的字段同步到 ES，用 ES 查到 id 再回表
3. **限制最大页数**：产品上限制只能翻前 100 页，避免深分页
4. **用 Hint 强制路由**：如果知道数据在哪个分片，用 Hint 精准路由

> 💡 前端类比：这像前端分页加载列表，`offset` 越大越慢，改用"加载更多"（游标）模式性能更好。

### 12.7 版本选型与迁移：Apache ShardingSphere

本模块用的是 `io.shardingsphere:sharding-jdbc-core:3.1.0`（当当时代）。现在应该用 Apache 版本：

| 版本 | groupId | 说明 |
| --- | --- | --- |
| 3.x（当当） | `io.shardingsphere` | 已停更，本模块用 |
| 4.x（Apache） | `org.apache.shardingsphere` | 过渡版本 |
| 5.x（Apache） | `org.apache.shardingsphere` | 当前主流，API 大改 |

**5.x 的主要变化：**

- API 重构，配置类名变化（`ShardingRuleConfiguration` → `ShardingRuleConfiguration` 仍在但用法变）
- 推荐用 YAML 配置而非 Java 配置
- 增强了分布式事务、读写分离、数据加密

**实际开发建议**：新项目直接上 5.x，用 YAML 配置（比本模块的 Java 配置简洁得多）。老项目迁移要评估 API 改造成本。

**常见坑**：网上很多教程版本混杂，3.x/4.x/5.x 的 API 不兼容，复制代码时先确认版本。本模块的 Java 配置写法在 5.x 已不推荐。

### 12.8 ShardingSphere-JDBC vs Proxy：怎么选？

| 维度 | JDBC | Proxy |
| --- | --- | --- |
| 部署 | 嵌入应用 | 独立部署 |
| 性能 | 高（直连数据库） | 多一层转发 |
| 语言 | 仅 Java | 任意语言 |
| 改造成本 | 需改 Java 配置 | 应用零改造 |
| 运维 | 各应用独立 | 统一管理 |

**实际开发选择：**

- **Java 单体/微服务，追求性能** → 用 JDBC（本模块）
- **多语言混合栈，统一管理** → 用 Proxy
- **大型企业** → 两者结合：JDBC 做分片，Proxy 做统一入口

---

> 📌 **学习建议**：分库分表是数据库架构的"核武器"，威力大但副作用也大。作为前端转后端的工程师，你要建立的认知是：**架构演进有顺序，不要跳级**。先做好索引、缓存、读写分离，单表千万级以下别碰分片。一旦决定分片，分片键的选择是重中之重——它决定了后续所有查询的姿势。建议把本模块的配置类逐行读透，理解"逻辑表→物理表"的路由过程，再去看 5.x 的 YAML 配置，会发现本质完全一样，只是表达方式更简洁。另外，分库分表后最痛的是查询和事务，提前想好分页方案和事务策略，别等上线才踩。
