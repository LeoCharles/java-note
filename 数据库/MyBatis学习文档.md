# MyBatis / MyBatis-Plus 学习文档

> MyBatis 是国内 Java 后端**事实上的 ORM 标准**。它不像 JPA 那样完全屏蔽 SQL，而是"**SQL 由你写，映射由它做**"——这个定位正好契合国内互联网"SQL 要可控、要能优化"的诉求。
> MyBatis-Plus 是 MyBatis 的增强工具，核心承诺是"**只做增强不做改变**"。
> 本篇以 **MyBatis 3.5.x + MyBatis-Plus 3.5.x + Spring Boot 3.x** 为基准，从原理讲到工程实践，包含大量"实际开发才踩得到"的坑。
> 思路：**痛点 → 配置 → 用法 → 原理 → 性能 → 实战**。带 ⭐ 的是开发高频/面试重点。

---

## 📖 目录

1. [为什么是 MyBatis](#一为什么是-mybatis)
2. [快速上手：从 0 到 1 跑通 CRUD](#二快速上手从-0-到-1-跑通-crud)
3. [核心原理：Mapper 为什么不用写实现类 ⭐](#三核心原理mapper-为什么不用写实现类-)
4. [`#{}` 与 `${}`：SQL 注入的第一道防线 ⭐⭐](#四-与-sql-注入的第一道防线-)
5. [参数处理与结果映射 ⭐](#五参数处理与结果映射-)
6. [动态 SQL ⭐⭐](#六动态-sql-)
7. [缓存机制](#七缓存机制)
8. [插件与拦截器](#八插件与拦截器)
9. [分页：PageHelper 与 MP 分页插件 ⭐](#九分页pagehelper-与-mp-分页插件-)
10. [MyBatis-Plus 核心能力 ⭐](#十mybatis-plus-核心能力-)
11. [注解 vs XML：怎么选](#十一注解-vs-xml怎么选)
12. [批量操作的性能问题 ⭐⭐](#十二批量操作的性能问题-)
13. [事务与 MyBatis](#十三事务与-mybatis)
14. [代码生成器](#十四代码生成器)
15. [多数据源与读写分离](#十五多数据源与读写分离)
16. [性能优化与 SQL 排查 ⭐](#十六性能优化与-sql-排查-)
17. [实际开发规范与踩坑清单](#十七实际开发规范与踩坑清单)
18. [📌 在 Spring Boot 中](#-在-spring-boot-中)
19. [本章小结](#本章小结)

---

## 一、为什么是 MyBatis

### 1.1 原生 JDBC 的痛点

```java
// 原生 JDBC 查一个用户
Connection conn = null;
PreparedStatement ps = null;
ResultSet rs = null;
try {
    conn = dataSource.getConnection();
    ps = conn.prepareStatement("SELECT id, name, age FROM student WHERE id = ?");
    ps.setLong(1, id);
    rs = ps.executeQuery();
    if (rs.next()) {
        Student s = new Student();
        s.setId(rs.getLong("id"));
        s.setName(rs.getString("name"));
        s.setAge(rs.getInt("age"));
        return s;
    }
} catch (SQLException e) {
    throw new RuntimeException(e);
} finally {
    if (rs != null) try { rs.close(); } catch (SQLException ignored) {}
    if (ps != null) try { ps.close(); } catch (SQLException ignored) {}
    if (conn != null) try { conn.close(); } catch (SQLException ignored) {}
}
```

**五个痛点**：

1. 连接/语句/结果的**资源管理**重复且易漏
2. **结果集映射**手写，字段一多就是体力活
3. **SQL 散落**在 Java 代码里，无法复用、难以审阅
4. **参数绑定**手写下标，容易错位
5. **动态条件**只能疯狂拼接字符串

### 1.2 MyBatis 解决了什么

| 痛点 | MyBatis 的解法 |
| :--- | :--- |
| 资源管理 | `SqlSession` 自动管理，Spring 集成后完全透明 |
| 结果映射 | `resultType`/`resultMap` 自动映射 |
| SQL 位置 | XML 文件集中管理（也可注解） |
| 参数绑定 | `#{name}` 按名字绑定 |
| 动态 SQL | `<if>` `<where>` `<foreach>` 标签 |

### 1.3 MyBatis vs JPA vs JdbcTemplate

| 维度 | JdbcTemplate | MyBatis | JPA / Hibernate |
| :--- | :--- | :--- | :--- |
| SQL 控制 | 全手写 | 全手写（可优化） | 自动生成，难调优 |
| 学习曲线 | 低 | 中 | 高 |
| 单表 CRUD | 手写 | 手写（MP 免写） | 自动 |
| 复杂查询 | 手写 | 强 | 弱（原生 SQL 兜底） |
| 数据库迁移 | 需改 SQL | 需改 SQL | 方言适配较好 |
| 国内使用率 | 低 | **高** | 中低 |

> 💡 **实际选型**：国内业务系统（尤其有复杂报表/多表关联）**首选 MyBatis-Plus**；出海/内部工具、领域模型清晰的系统可以用 JPA。两者也可以共存（JPA 管单表，MyBatis 管复杂查询），但要统一事务管理器。

### 1.4 MyBatis 的层次

```text
应用代码
   ↓
Mapper 接口（你定义，无实现类）
   ↓ 动态代理
MapperProxy → MapperMethod → SqlSession
   ↓
Executor（SimpleExecutor / ReuseExecutor / BatchExecutor）
   ↓
StatementHandler（PreparedStatement 组装 + 参数绑定）
   ↓
ParameterHandler / ResultSetHandler（入参 / 出参映射）
   ↓
JDBC Driver → 数据库
```

**理解这条链，才能定位"为什么 SQL 没执行""为什么参数是 null""为什么返回类型不对"。**

### 1.5 版本选择

| 组件 | 推荐版本 | 说明 |
| :--- | :--- | :--- |
| MyBatis | 3.5.19+ | 3.5.x 稳定 |
| MyBatis-Spring-Boot-Starter | 3.0.x | 适配 Spring Boot 3 |
| MyBatis-Plus | 3.5.9+（`mybatis-plus-spring-boot3-starter`） | **Spring Boot 3 必须用 `boot3` 版本** |
| PageHelper | 6.1.x（`pagehelper-spring-boot-starter`） | 5.x 不适配 Boot 3 |

> ⚠️ **Spring Boot 3 最大的坑**：`mybatis-plus-boot-starter` 是基于 `javax.*` 的，Boot 3 用的是 `jakarta.*`，必须换 `mybatis-plus-spring-boot3-starter`，否则启动报 `ClassNotFoundException: javax.servlet.*` 或自动配置不生效。

---

## 二、快速上手：从 0 到 1 跑通 CRUD

### 2.1 依赖

```xml
<dependencies>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-web</artifactId>
    </dependency>

    <!-- MyBatis + Spring Boot 3 -->
    <dependency>
        <groupId>org.mybatis.spring.boot</groupId>
        <artifactId>mybatis-spring-boot-starter</artifactId>
        <version>3.0.4</version>
    </dependency>

    <!-- 数据库驱动 -->
    <dependency>
        <groupId>com.mysql</groupId>
        <artifactId>mysql-connector-j</artifactId>
        <scope>runtime</scope>
    </dependency>

    <!-- 连接池：mybatis-spring-boot-starter 已传递引入 spring-boot-starter-jdbc（含 HikariCP），
         这里显式声明只是为了表明依赖关系，可省略 -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-jdbc</artifactId>
    </dependency>
</dependencies>

<build>
    <resources>
        <!-- 确保 XML 被打包 -->
        <resource>
            <directory>src/main/java</directory>
            <includes>
                <include>**/*.xml</include>
            </includes>
        </resource>
        <resource>
            <directory>src/main/resources</directory>
        </resource>
    </resources>
</build>
```

> ⚠️ **XML 放在 `src/main/java` 下必须配置 `<resources>`**，否则 Maven 默认不打包 Java 目录里的 XML，运行时报 `Invalid bound statement (not found)`。

### 2.2 表结构

```sql
CREATE TABLE student (
    id          BIGINT PRIMARY KEY AUTO_INCREMENT,
    name        VARCHAR(20)  NOT NULL,
    age         INT,
    sex         CHAR(1)      DEFAULT '1',
    class_id    BIGINT,
    score       DECIMAL(5,2),
    deleted     TINYINT      DEFAULT 0,
    create_time DATETIME     DEFAULT CURRENT_TIMESTAMP,
    update_time DATETIME     DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY idx_class_id (class_id),
    KEY idx_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 2.3 application.yml

```yaml
spring:
  datasource:
    url: jdbc:mysql://127.0.0.1:3306/study?useUnicode=true&characterEncoding=utf8&serverTimezone=Asia/Shanghai&useSSL=false&allowPublicKeyRetrieval=true
    username: root
    password: root
    driver-class-name: com.mysql.cj.jdbc.Driver
    hikari:
      minimum-idle: 5
      maximum-pool-size: 20
      connection-timeout: 30000
      idle-timeout: 600000
      max-lifetime: 1800000
      pool-name: StudyHikariPool
  sql:
    init:
      mode: never          # 生产不要自动执行 SQL

mybatis:
  mapper-locations: classpath*:mapper/**/*.xml
  type-aliases-package: com.example.study.entity
  configuration:
    map-underscore-to-camel-case: true    # 下划线转驼峰
    cache-enabled: false                   # 二级缓存默认关闭
    lazy-loading-enabled: false
    default-statement-timeout: 30
    log-impl: org.apache.ibatis.logging.stdout.StdOutImpl   # 开发环境打印 SQL

mybatis-plus:
  mapper-locations: classpath*:mapper/**/*.xml
  type-aliases-package: com.example.study.entity
  global-config:
    banner: false
    db-config:
      id-type: auto
      logic-delete-field: deleted
      logic-delete-value: 1
      logic-not-delete-value: 0
  configuration:
    map-underscore-to-camel-case: true
```

> ⚠️ **生产不要用 `StdOutImpl`**，SQL 日志会被打到 stdout 且无法分级；应该用 `org.apache.ibatis.logging.slf4j.Slf4jImpl` 并给 Mapper 包单独设 `debug` 级别。
>
> ⚠️ **时区**：`serverTimezone=Asia/Shanghai` 少了会在时间字段上出现 8 小时偏差。`useSSL=false` 只是开发省事，生产应开启。

### 2.4 实体类

```java
@Data
public class Student {
    private Long id;
    private String name;
    private Integer age;
    private String sex;
    private Long classId;      // 自动映射 class_id
    private BigDecimal score;
    private Integer deleted;
    private LocalDateTime createTime;
    private LocalDateTime updateTime;
}
```

> **映射规则**：开启 `map-underscore-to-camel-case` 后，`class_id` 自动映射到 `classId`。**前提是列名与属性名只有下划线差异**，否则必须写 `resultMap`。

### 2.5 Mapper 接口

```java
@Mapper
public interface StudentMapper {

    Student selectById(@Param("id") Long id);

    List<Student> selectByCondition(@Param("name") String name,
                                    @Param("minAge") Integer minAge);

    int insert(Student student);

    int updateById(Student student);

    int deleteById(@Param("id") Long id);
}
```

`@Mapper` 也可以用启动类上的 `@MapperScan("com.example.study.mapper")` 批量替代——**实际项目推荐 `@MapperScan`**，避免每个接口都写注解。

### 2.6 XML

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE mapper PUBLIC "-//mybatis.org//DTD Mapper 3.0//EN"
        "https://mybatis.org/dtd/mybatis-3-mapper.dtd">
<mapper namespace="com.example.study.mapper.StudentMapper">

    <resultMap id="BaseResultMap" type="com.example.study.entity.Student">
        <id property="id" column="id"/>
        <result property="name" column="name"/>
        <result property="classId" column="class_id"/>
        <result property="createTime" column="create_time"/>
        <result property="updateTime" column="update_time"/>
    </resultMap>

    <sql id="Base_Column_List">
        id, name, age, sex, class_id, score, deleted, create_time, update_time
    </sql>

    <select id="selectById" resultMap="BaseResultMap">
        SELECT <include refid="Base_Column_List"/>
        FROM student
        WHERE id = #{id} AND deleted = 0
    </select>

    <select id="selectByCondition" resultType="Student">
        SELECT <include refid="Base_Column_List"/>
        FROM student
        <where>
            deleted = 0
            <if test="name != null and name != ''">
                AND name LIKE CONCAT('%', #{name}, '%')
            </if>
            <if test="minAge != null">
                AND age &gt;= #{minAge}
            </if>
        </where>
        ORDER BY id DESC
    </select>

    <insert id="insert" useGeneratedKeys="true" keyProperty="id">
        INSERT INTO student (name, age, sex, class_id, score)
        VALUES (#{name}, #{age}, #{sex}, #{classId}, #{score})
    </insert>

    <update id="updateById">
        UPDATE student
        <set>
            <if test="name != null">name = #{name},</if>
            <if test="age != null">age = #{age},</if>
            <if test="sex != null">sex = #{sex},</if>
            <if test="classId != null">class_id = #{classId},</if>
            <if test="score != null">score = #{score},</if>
            update_time = NOW()
        </set>
        WHERE id = #{id}
    </update>

    <delete id="deleteById">
        DELETE FROM student WHERE id = #{id}
    </delete>

</mapper>
```

### 2.7 Service 与 Controller

```java
@Service
@RequiredArgsConstructor
public class StudentService {

    private final StudentMapper studentMapper;

    public Student get(Long id) {
        return studentMapper.selectById(id);
    }

    @Transactional(rollbackFor = Exception.class)
    public Long create(Student student) {
        studentMapper.insert(student);
        return student.getId();       // useGeneratedKeys 回填主键
    }
}
```

```java
@RestController
@RequestMapping("/students")
@RequiredArgsConstructor
public class StudentController {

    private final StudentService studentService;

    @GetMapping("/{id}")
    public Student get(@PathVariable Long id) {
        return studentService.get(id);
    }

    @PostMapping
    public Long create(@RequestBody Student student) {
        return studentService.create(student);
    }
}
```

---

## 三、核心原理：Mapper 为什么不用写实现类 ⭐

这是 MyBatis 面试第一问。答案链条是：**`@MapperScan` → `MapperFactoryBean` → JDK 动态代理 → `MapperProxy`**。

### 3.1 启动时发生了什么

1. `@MapperScan("com.example.study.mapper")` 导入 `MapperScannerConfigurer`（或 Boot 3 下的 `MapperScannerRegistrar`）
2. 扫描包下所有接口，把每个接口注册为 `MapperFactoryBean`
3. Spring 创建 Bean 时调用 `MapperFactoryBean.getObject()`：

```java
// 简化版
public T getObject() throws Exception {
    return getSqlSession().getMapper(this.mapperInterface);
}

public <T> T getMapper(Class<T> type) {
    return configuration.getMapper(type, this);
}

public <T> T getMapper(Class<T> type, SqlSession sqlSession) {
    return mapperRegistry.getMapper(type, sqlSession);
}

// MapperRegistry
public <T> T getMapper(Class<T> type, SqlSession sqlSession) {
    MapperProxyFactory<T> factory = knownMappers.get(type);
    return factory.newInstance(sqlSession);
}
```

4. `MapperProxyFactory.newInstance` 用 **JDK 动态代理** 生成一个实现了该接口的代理对象：

```java
protected T newInstance(MapperProxy<T> mapperProxy) {
    return (T) Proxy.newProxyInstance(
            mapperInterface.getClassLoader(),
            new Class[]{mapperInterface},
            mapperProxy);
}
```

5. 调用接口方法时，进入 `MapperProxy.invoke()`：

```java
public Object invoke(Object proxy, Method method, Object[] args) throws Throwable {
    if (Object.class.equals(method.getDeclaringClass())) {
        return method.invoke(this, args);       // toString/equals 等直接走
    }
    return cachedInvoker(method).invoke(proxy, method, args, sqlSession);
}

// PlainMethodInvoker
public Object invoke(..., SqlSession sqlSession) {
    MapperMethod mapperMethod = cachedMapperMethod(method);
    return mapperMethod.execute(sqlSession, args);   // 这里的 args 就是业务参数，不是 proxy
}
```

6. `MapperMethod.execute` 根据 `SqlCommand.getType()`（INSERT/UPDATE/DELETE/SELECT/FLUSH）分发到 `sqlSession.insert/update/delete/selectOne/selectList`。

### 3.2 为什么 Mapper 接口中的方法不能重载

`MapperMethod` 的缓存 key 是 `Method` 对象本身，但**真正决定 SQL 的是 `namespace + methodName`**。两个同名不同参的方法会映射到同一个 `<select id="xxx">`，参数类型无法区分，必然出错。

> ⚠️ **不要在 Mapper 接口里写重载方法**（如 `selectById(Long)` 和 `selectById(String)`），要么换名字，要么用 `@Param` + 动态参数对象。

### 3.3 `Invalid bound statement (not found)` 排查清单

这是 MyBatis 最常见的启动/运行异常，**99% 是配置问题**：

| 排查项 | 检查方法 |
| :--- | :--- |
| `namespace` 是否等于 Mapper 全限定名 | 拼写、大小写 |
| `id` 是否等于方法名 | 一字不差 |
| `mapper-locations` 是否覆盖 XML 路径 | `classpath*:mapper/**/*.xml`（注意 `classpath*`） |
| XML 是否被打包进 target | 看 `target/classes` 下有没有 |
| XML 是否在 java 目录且未配 `<resources>` | 最常见 |
| Mapper 接口是否被扫描 | `@MapperScan` 包路径 |
| 多模块下路径是否正确 | `classpath*:` 能跨 jar 扫描 |

```bash
# 快速验证 XML 是否被打包
ls target/classes/mapper/student/StudentMapper.xml
```

### 3.4 一个方法调用的完整流程

```text
studentMapper.selectById(1L)
  └─ MapperProxy.invoke()
       └─ MapperMethod.execute()
            └─ sqlSession.selectOne("com...StudentMapper.selectById", 1L)
                 └─ DefaultSqlSession.selectList()
                      └─ executor.query(ms, param, rowBounds, resultHandler)
                           ├─ BoundSql 生成（动态 SQL 解析）
                           ├─ 一级缓存 / 二级缓存检查
                           ├─ StatementHandler 创建 PreparedStatement
                           ├─ ParameterHandler 绑定参数
                           ├─ ResultSetHandler 映射结果
                           └─ 执行 SQL
```

---

## 四、`#{}` 与 `${}`：SQL 注入的第一道防线 ⭐⭐

### 4.1 本质区别

| 写法 | 底层行为 | 安全 |
| :--- | :--- | :--- |
| `#{name}` | 编译为 `?`，用 `PreparedStatement.setString()` 绑定 | **安全**（防注入） |
| `${name}` | **字符串直接拼接**到 SQL 里 | **危险**（可注入） |

```xml
<!-- 安全 -->
SELECT * FROM student WHERE name = #{name}
-- 实际执行：SELECT * FROM student WHERE name = ?

<!-- 危险 -->
SELECT * FROM student ORDER BY ${orderBy}
-- 传入 orderBy = "id; DROP TABLE student"
-- 实际执行：SELECT * FROM student ORDER BY id; DROP TABLE student
```

### 4.2 为什么 `${}` 还是有存在的必要

有些位置**不能用占位符**，因为 SQL 的语法结构不能参数化：

- 表名、列名：`SELECT * FROM ${table}`
- 排序字段：`ORDER BY ${sortField} ${sortOrder}`
- `LIKE` 的通配符（其实可以 `CONCAT('%', #{x}, '%')` 解决）

### 4.3 必须用 `${}` 时的防护

```java
private static final Set<String> ALLOWED_SORT_FIELDS =
        Set.of("id", "name", "age", "score", "create_time");
private static final Set<String> ALLOWED_ORDERS = Set.of("ASC", "DESC");

public List<Student> list(String sortField, String order) {
    // 白名单校验：不在白名单就用默认值，绝不直接透传
    String field = ALLOWED_SORT_FIELDS.contains(sortField) ? sortField : "id";
    String direction = ALLOWED_ORDERS.contains(order.toUpperCase()) ? order : "ASC";
    return studentMapper.list(field, direction);
}
```

```xml
<select id="list" resultType="Student">
    SELECT * FROM student
    ORDER BY ${sortField} ${order}
</select>
```

**额外防线**：

1. 用 `@SortDefault` 或 DTO 枚举替代字符串
2. 接口层做参数校验（`@Validated` + 自定义校验器）
3. 数据库账号**最小权限**（业务账号无 DDL 权限）
4. 开启 WAF / 代码扫描（SonarQube 规则：`SQL injection`）

### 4.4 LIKE 查询的正确姿势

```xml
<!-- ❌ 用 ${} 拼接，有注入风险 -->
AND name LIKE '%${name}%'

<!-- ✅ 推荐：CONCAT -->
AND name LIKE CONCAT('%', #{name}, '%')

<!-- ✅ 或者在 Java 侧拼好通配符，但仍用 #{} 绑定 -->
```

```java
// Java 侧处理
String likeName = "%" + StringUtils.trim(name) + "%";
```

### 4.5 IN 查询的正确姿势

```xml
<!-- ✅ foreach -->
<select id="selectByIds" resultType="Student">
    SELECT * FROM student
    WHERE id IN
    <foreach collection="ids" item="id" open="(" separator="," close=")">
        #{id}
    </foreach>
</select>
```

> ⚠️ **`IN` 列表不能无限大**。MySQL 的 `max_allowed_packet`、Oracle 的 1000 限制、执行计划选择都会出问题。**超过 1000 个 ID 建议分批查或改用临时表**。

> ⚠️ **`IN` 参数为空集合会生成 `IN ()`，语法错误**。必须在外层判断 `ids != null and ids.size() > 0`。

---

## 五、参数处理与结果映射 ⭐

### 5.1 单参数 / 多参数 / 对象参数

```java
// 单参数：可以直接 #{任意名字}，因为只有一个参数
Student selectById(Long id);
// XML 里 #{id} 或 #{value} 都行，甚至 #{abc} 也可以——容易误导，建议统一用有意义的名字

// 多参数：必须 @Param，否则只能用 #{param1}/#{arg0}
List<Student> select(String name, Integer age);
// XML 必须写 #{param1} #{param2}（或 #{arg0} #{arg1}）

// 推荐：显式 @Param
List<Student> select(@Param("name") String name, @Param("age") Integer age);

// 对象参数：直接取属性
int insert(Student student);
// XML: #{name} 对应 student.getName()
```

> ⚠️ **不用 `@Param` 时，MyBatis 3.4.3+ 会把参数命名为 `param1...paramN` 和 `arg0...argN-1`**。**生产代码一律用 `@Param`**，可读性和重构友好度都高出一截。

### 5.2 特殊参数类型

```xml
<!-- Java 8 时间类型 -->
<if test="startTime != null">
    AND create_time &gt;= #{startTime, jdbcType=TIMESTAMP}
</if>

<!-- 枚举：默认用 name()，可用 typeHandler 自定义 -->
AND status = #{status, typeHandler=com.example.MyEnumTypeHandler}

<!-- 集合：foreach 遍历 -->
<foreach collection="list" item="item" index="index" open="(" separator="," close=")">
    #{item.name}
</foreach>
```

**`collection` 属性的取值规则**：

| 参数形式 | `collection` 怎么写 |
| :--- | :--- |
| `List<T>` 直接作参数 | `list` 或 `collection` |
| 数组 `T[]` | `array` |
| `@Param("ids") List` | `ids` |
| 对象属性 `dto.getIds()` | `ids` |
| `Map` | key 名 |

> ⚠️ **`List` 传参不写 `@Param` 时，`collection="list"` 和 `collection="collection"` 都能用，但数组只能用 `array`**。统一用 `@Param` 就能避免这套规则。

### 5.3 jdbcType 什么时候必须写

**结论：只有字段值为 `null` 时，Oracle 等严格数据库需要显式 `jdbcType`**，MySQL 在大多数配置下不需要。

```xml
<insert id="insert">
    INSERT INTO student (name, age)
    VALUES (#{name, jdbcType=VARCHAR}, #{age, jdbcType=INTEGER})
</insert>
```

全局配置：

```yaml
mybatis:
  configuration:
    jdbc-type-for-null: 'NULL'
```

> ⚠️ Oracle 报 `ORA-01400: cannot insert NULL` 或 `无效的列类型` 时，先查 `jdbcType`。

### 5.4 结果映射：resultType vs resultMap

| 方式 | 适用 | 说明 |
| :--- | :--- | :--- |
| `resultType` | 列名与属性名能对上（含下划线转驼峰） | 简单查询首选 |
| `resultMap` | 需要显式映射、关联查询、类型转换 | 复杂查询必备 |

**`resultType` 的坑**：

1. **列名重复会覆盖**：`SELECT a.id, b.id FROM ...` 两个 `id` 只有一个能映射
2. **别名必须与属性名一致**：`SELECT name AS studentName` 才能映射到 `studentName`
3. **`SELECT *` 在联表时容易冲突**：显式列清单

```xml
<!-- 联表查询：显式别名 -->
<select id="selectDetail" resultType="StudentDetailVO">
    SELECT
        s.id           AS id,
        s.name         AS name,
        c.name         AS className,
        c.id           AS classId
    FROM student s
    LEFT JOIN class c ON c.id = s.class_id
    WHERE s.id = #{id}
</select>
```

### 5.5 一对多 / 多对一（`association` / `collection`）

```xml
<resultMap id="StudentWithScores" type="Student">
    <id property="id" column="id"/>
    <result property="name" column="name"/>

    <!-- 多对一：学生 → 班级 -->
    <association property="clazz" javaType="Class">
        <id property="id" column="class_id"/>
        <result property="name" column="class_name"/>
    </association>

    <!-- 一对多：学生 → 成绩列表 -->
    <collection property="scores" ofType="Score">
        <id property="id" column="score_id"/>
        <result property="subject" column="subject"/>
        <result property="mark" column="mark"/>
    </collection>
</resultMap>

<select id="selectStudentWithScores" resultMap="StudentWithScores">
    SELECT
        s.id, s.name,
        c.id AS class_id, c.name AS class_name,
        sc.id AS score_id, sc.subject, sc.mark
    FROM student s
    LEFT JOIN class c ON c.id = s.class_id
    LEFT JOIN score sc ON sc.student_id = s.id
    WHERE s.id = #{id}
</select>
```

> ⚠️ **`<collection>` 在联表查询中会产生笛卡尔积**。一个学生 10 条成绩、班级 1 条，结果仍是 10 行，但若同时关联两个一对多，就会膨胀成 N×M 行。**两个以上一对多推荐"主表分页 + 子查询"或 `@BatchSize`（懒加载批量）**。

### 5.6 嵌套查询 + 懒加载（N+1 问题）

```xml
<resultMap id="StudentMap" type="Student">
    <id property="id" column="id"/>
    <result property="name" column="name"/>
    <collection property="scores"
                ofType="Score"
                column="id"
                select="com.example.mapper.ScoreMapper.selectByStudentId"
                fetchType="lazy"/>
</resultMap>
```

- 优点：SQL 简单、复用性强
- 缺点：**N+1 查询**（1 次主查询 + N 次子查询），而且在封装/序列化时触发懒加载可能导致 `LazyInitializationException`

> 💡 **实战建议**：**能 join 就 join，不要滥用嵌套查询**。确实需要时，把 `lazyLoadingEnabled` 打开并配合 `aggressiveLazyLoading=false`，同时确保在 Service 层（事务内/`SqlSession` 未关闭）完成数据组装。

---

## 六、动态 SQL ⭐⭐

动态 SQL 是 MyBatis 的杀手锏，也是"XML 比注解强"的根本原因。

### 6.1 `<if>`

```xml
<select id="search" resultType="Student">
    SELECT * FROM student
    WHERE deleted = 0
    <if test="name != null and name != ''">
        AND name LIKE CONCAT('%', #{name}, '%')
    </if>
    <if test="minAge != null">
        AND age &gt;= #{minAge}
    </if>
</select>
```

**`test` 表达式注意点**：

- `!= ''` 只能用于 String，**对 Integer 写 `age != ''` 会报 `NumberFormatException`**（OGNL 会把 `''` 转数字）
- **数字 0 判断**：`status != null and status != ''` 在 `status=0` 时会被当成 false，导致条件丢失！正确写法 **只判断 `!= null`**
- 布尔值：`enabled` 直接写 `test="enabled"` 可能因为 OGNL 把字符串 `"true"` 忽略，建议写成 `test="enabled != null and enabled"`

```xml
<!-- ✅ 数字条件只判 null -->
<if test="status != null">
    AND status = #{status}
</if>

<!-- ❌ 会漏掉 status=0 -->
<if test="status != null and status != ''">
    AND status = #{status}
</if>
```

> ⚠️ **这是国内开发者踩得最多的一条**：状态字段 `0` 被 `!= ''` 误判为"空"，导致"查询全部状态"变成了"查询所有状态"。**面试也爱问。**

### 6.2 `<where>` / `<set>` / `<trim>`

```xml
<!-- where：自动去掉开头多余 AND/OR，并且在有条件时才输出 WHERE -->
<where>
    <if test="name != null">AND name = #{name}</if>
    <if test="age != null">AND age = #{age}</if>
</where>

<!-- set：自动去掉末尾多余的逗号 -->
<set>
    <if test="name != null">name = #{name},</if>
    <if test="age != null">age = #{age},</if>
</set>

<!-- trim：等价于 where / set 的通用形式 -->
<trim prefix="WHERE" prefixOverrides="AND |OR ">
    ...
</trim>
<trim prefix="SET" suffixOverrides=",">
    ...
</trim>
```

### 6.3 `<choose>` / `<when>` / `<otherwise>`

```xml
<choose>
    <when test="type == 'name'">ORDER BY name</when>
    <when test="type == 'score'">ORDER BY score DESC</when>
    <otherwise>ORDER BY id DESC</otherwise>
</choose>
```

> ⚠️ OGNL 中字符串比较用 **单引号**：`type == 'name'`。若用双引号，`"name"` 会被当成变量，返回 null。

### 6.4 `<foreach>`

```xml
<!-- IN 查询 -->
<foreach collection="ids" item="id" open="(" separator="," close=")">
    #{id}
</foreach>

<!-- 批量插入 -->
<insert id="insertBatch">
    INSERT INTO student (name, age, class_id)
    VALUES
    <foreach collection="list" item="s" separator=",">
        (#{s.name}, #{s.age}, #{s.classId})
    </foreach>
</insert>

<!-- 批量更新：需要唯一键 -->
<update id="updateBatch">
    UPDATE student
    <trim prefix="SET" suffixOverrides=",">
        <foreach collection="list" item="s">
            <trim prefix="name = CASE id" suffix="END,">
                WHEN #{s.id} THEN #{s.name}
            </trim>
        </foreach>
    </trim>
    WHERE id IN
    <foreach collection="list" item="s" open="(" separator="," close=")">
        #{s.id}
    </foreach>
</update>
```

> ⚠️ **`foreach` 的 `index` 对 List/数组是下标，对 Map 是 key**。

### 6.5 `<bind>`

```xml
<select id="search" resultType="Student">
    <bind name="pattern" value="'%' + name + '%'"/>
    SELECT * FROM student
    WHERE name LIKE #{pattern}
</select>
```

### 6.6 `<sql>` 片段复用

```xml
<sql id="Base_Column_List">
    id, name, age, sex, class_id, score, create_time, update_time
</sql>

<include refid="Base_Column_List"/>
<!-- 通过属性传参 -->
<include refid="someSql">
    <property name="alias" value="s"/>
</include>
```

> ⚠️ **`<sql>` 的 `id` 在同一 namespace 内必须唯一**（跨 namespace 需加前缀）。多人协作时容易冲突，建议用 `模块_表_列` 命名。

### 6.7 动态 SQL 的执行效率

动态 SQL 在每次查询时都会解析 `<if>` 等标签生成 `BoundSql`。对同一 Mapper 方法、相同参数结构，MyBatis 会缓存 `SqlSource`（`RawSqlSource` / `DynamicSqlSource`），但**动态部分仍需逐次求值**。

> ⚠️ **不要写超大的动态 SQL**（几百个 `<if>`）：一是不易维护，二是每次解析都有开销。**查询条件超过 8 个，考虑用 QueryWrapper 或专门的查询对象 + 索引覆盖**。

---

## 七、缓存机制

### 7.1 一级缓存（SqlSession 级）

- 默认开启，作用域是 `SqlSession`
- Spring 集成后，**一次请求/事务内**共享（`SqlSessionTemplate` 每次数据库操作复用同一个 Session）
- 执行 `INSERT/UPDATE/DELETE` 会**清空整个一级缓存**
- `sqlSession.clearCache()` 手动清空

> ⚠️ **一级缓存在 Spring 下反而容易出问题**：同一事务内先查后改再查，可能拿到旧值。**分布式环境下更不能依赖它**。

### 7.2 二级缓存（namespace 级）

```yaml
mybatis:
  configuration:
    cache-enabled: true
```

```xml
<cache eviction="LRU" flushInterval="60000" size="1024" readOnly="true"/>
```

**开启条件（缺一不可）**：

1. 全局 `cache-enabled: true`
2. XML 中声明 `<cache/>`
3. 返回对象**可序列化**（`readOnly=false` 时）
4. 提交事务后才写入

**二级缓存的坑**：

- 跨 namespace 的更新无法自动失效（关联表更新，另一个 Mapper 的缓存仍是旧的）
- 多表关联查询的缓存最容易脏
- 集群部署下多个 JVM 各有各的缓存，**数据不一致**

> 💡 **实战结论：MyBatis 的二级缓存基本不要开**。需要缓存请用 Redis（统一、可控、可失效）。开启二级缓存的项目，后期一定有人为此 debug 一整天。

### 7.3 缓存失效顺序

```text
任意增删改
  → 清空当前 SqlSession 一级缓存
  → 清空当前 namespace 二级缓存
  → 其他 namespace 的二级缓存不受影响（这就是脏数据根源）
```

---

## 八、插件与拦截器

MyBatis 允许拦截四个核心对象：

| 拦截对象 | 可拦截的方法 | 典型用途 |
| :--- | :--- | :--- |
| `Executor` | `update/query/commit/rollback` | 分页、读写分离、慢 SQL 监控 |
| `StatementHandler` | `prepare/parameterize/query` | 分页改写 SQL、SQL 打印 |
| `ParameterHandler` | `getParameterObject/setParameters` | 参数加密 |
| `ResultSetHandler` | `handleResultSets` | 返回值脱敏、多租户 |

### 8.1 自定义插件：SQL 耗时监控

```java
@Intercepts({
    @Signature(type = Executor.class, method = "query",
            args = {MappedStatement.class, Object.class, RowBounds.class, ResultHandler.class}),
    @Signature(type = Executor.class, method = "update",
            args = {MappedStatement.class, Object.class})
})
@Component
@Slf4j
public class SqlCostInterceptor implements Interceptor {

    private static final long SLOW_MS = 1000;

    @Override
    public Object intercept(Invocation invocation) throws Throwable {
        long start = System.currentTimeMillis();
        try {
            return invocation.proceed();
        } finally {
            long cost = System.currentTimeMillis() - start;
            MappedStatement ms = (MappedStatement) invocation.getArgs()[0];
            if (cost > SLOW_MS) {
                log.warn("[慢SQL] {} 耗时 {}ms", ms.getId(), cost);
            }
        }
    }

    @Override
    public Object plugin(Object target) {
        return Plugin.wrap(target, this);
    }
}
```

```java
@Configuration
public class MyBatisConfig {
    @Bean
    public SqlCostInterceptor sqlCostInterceptor() {
        return new SqlCostInterceptor();
    }
}
```

> ⚠️ **插件是有顺序的**，多个插件会形成责任链（`InterceptorChain`）。分页插件必须在其他改写 SQL 的插件之前/之后明确排序，否则会互相踩。

### 8.2 MyBatis-Plus 的内置插件

| 插件 | 作用 |
| :--- | :--- |
| `PaginationInnerInterceptor` | 物理分页 |
| `OptimisticLockerInnerInterceptor` | 乐观锁（`@Version`） |
| `BlockAttackInnerInterceptor` | 阻止全表 update/delete |
| `IllegalSQLInnerInterceptor` | 检查 SQL 是否走索引（3.5.3+） |
| `TenantLineInnerInterceptor` | 多租户自动拼接租户条件 |
| `DynamicTableNameInnerInterceptor` | 分表 |

---

## 九、分页：PageHelper 与 MP 分页插件 ⭐

### 9.1 逻辑分页 vs 物理分页

| 方式 | 原理 | 问题 |
| :--- | :--- | :--- |
| 逻辑分页（`RowBounds`） | 查出全部数据，内存中截取 | 数据量大时 OOM |
| 物理分页 | 改写 SQL 加 `LIMIT` | 推荐 |

> ⚠️ **`RowBounds` 只适合数据量很小的场景**。10 万行数据查第 100 页，它会把 10 万行全部拉回内存。

### 9.2 MyBatis-Plus 分页（推荐）

```java
@Configuration
public class MybatisPlusConfig {

    @Bean
    public MybatisPlusInterceptor mybatisPlusInterceptor() {
        MybatisPlusInterceptor interceptor = new MybatisPlusInterceptor();

        PaginationInnerInterceptor pagination = new PaginationInnerInterceptor(DbType.MYSQL);
        pagination.setMaxLimit(500L);          // 单页最大条数，防止恶意传 100000
        pagination.setOverflow(false);          // 页码超过总页数时返回空而不是第一页
        interceptor.addInnerInterceptor(pagination);

        interceptor.addInnerInterceptor(new OptimisticLockerInnerInterceptor());
        interceptor.addInnerInterceptor(new BlockAttackInnerInterceptor());
        return interceptor;
    }
}
```

```java
Page<Student> page = new Page<>(1, 10);        // 第 1 页，每页 10 条
Page<Student> result = studentMapper.selectPage(page,
        Wrappers.<Student>lambdaQuery()
                .eq(Student::getClassId, 1L)
                .orderByDesc(Student::getScore));

System.out.println(result.getTotal());       // 总条数
System.out.println(result.getRecords());     // 当前页数据
```

**多表联查分页**：MP 生成的 count SQL 可能不准，需要自定义：

```java
Page<StudentDetailVO> page = new Page<>(1, 10);
studentMapper.selectDetailPage(page, query);
```

```xml
<select id="selectDetailPage" resultType="StudentDetailVO">
    SELECT s.id, s.name, c.name AS className
    FROM student s
    LEFT JOIN class c ON c.id = s.class_id
</select>
```

> ⚠️ **MP 分页插件对 `LEFT JOIN + 一对多` 的 count 会偏大**（笛卡尔积），需要手写 count 方法或设置 `page.setOptimizeJoin(true)`（有误伤风险）。

### 9.3 PageHelper

```xml
<dependency>
    <groupId>com.github.pagehelper</groupId>
    <artifactId>pagehelper-spring-boot-starter</artifactId>
    <version>2.1.0</version>
</dependency>
```

```yaml
pagehelper:
  helper-dialect: mysql
  reasonable: true          # 页码合理化
  support-methods-arguments: true
  params: count=countSql
```

```java
PageHelper.startPage(1, 10);
List<Student> list = studentMapper.selectByCondition("张", 18);
PageInfo<Student> pageInfo = new PageInfo<>(list);
System.out.println(pageInfo.getTotal());
```

> ⚠️ **PageHelper 的 `startPage` 只对"紧跟着的下一个 Mapper 查询"生效**。中间插了别的查询，分页就会打到错误的 SQL 上。**线程池复用线程时如果分页没清理干净，还会污染下一次查询**（本质是 `ThreadLocal`）。

> 💡 **选型建议**：新项目直接用 **MP 分页插件**，不要混用 PageHelper。

---

## 十、MyBatis-Plus 核心能力 ⭐

### 10.1 依赖与配置

```xml
<dependency>
    <groupId>com.baomidou</groupId>
    <artifactId>mybatis-plus-spring-boot3-starter</artifactId>
    <version>3.5.9</version>
</dependency>
```

```java
@SpringBootApplication
@MapperScan("com.example.study.mapper")
public class StudyApplication {
    public static void main(String[] args) {
        SpringApplication.run(StudyApplication.class, args);
    }
}
```

### 10.2 实体注解

```java
@Data
@TableName(value = "student", autoResultMap = true)
public class Student {

    @TableId(type = IdType.AUTO)          // 自增；ASSIGN_ID 雪花；INPUT 手动
    private Long id;

    @TableField("name")
    private String name;

    @TableField(value = "class_id")
    private Long classId;

    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createTime;

    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updateTime;

    @TableLogic                            // 逻辑删除
    private Integer deleted;

    @Version                               // 乐观锁
    private Integer version;

    @TableField(exist = false)             // 非表字段
    private String className;
}
```

| 注解 | 作用 |
| :--- | :--- |
| `@TableName` | 表名映射（可加 `keepGlobalPrefix`、`resultMap`） |
| `@TableId` | 主键策略 |
| `@TableField` | 列名、自动填充、非表字段、类型处理器 |
| `@TableLogic` | 逻辑删除 |
| `@Version` | 乐观锁 |
| `@TableField(typeHandler = XxxTypeHandler.class)` | JSON 字段、枚举字段 |

### 10.3 BaseMapper：单表 CRUD 白嫖

```java
public interface StudentMapper extends BaseMapper<Student> {
}
```

```java
// 新增
studentMapper.insert(student);                       // 回填自增 ID

// 删除
studentMapper.deleteById(1L);
studentMapper.deleteBatchIds(List.of(1L, 2L));
studentMapper.deleteByMap(Map.of("class_id", 1L));

// 修改
studentMapper.updateById(student);                   // 只更新非 null 字段
studentMapper.update(student, wrapper);              // 条件更新

// 查询
studentMapper.selectById(1L);
studentMapper.selectBatchIds(List.of(1L, 2L));
studentMapper.selectList(Wrappers.<Student>lambdaQuery().eq(Student::getAge, 18));
studentMapper.selectOne(wrapper);
studentMapper.selectCount(wrapper);
studentMapper.selectPage(page, wrapper);
```

> ⚠️ **`updateById` 只更新非 null 字段**。想把字段**置空**（`UPDATE ... SET name = NULL`），`updateById` 做不到，必须用 `LambdaUpdateWrapper.set(Student::getName, null)` 或手写 XML。
>
> ⚠️ **`updateById` 不传 `id` 会报错**；传了 id 但对象里其他字段全是 null，会变成 `UPDATE student SET WHERE id=?` 语法错误。

### 10.4 条件构造器

```java
// LambdaQueryWrapper：类型安全，推荐
LambdaQueryWrapper<Student> wrapper = Wrappers.lambdaQuery();
wrapper.eq(Student::getClassId, 1L)
       .ge(Student::getAge, 18)
       .like(StringUtils.hasText(name), Student::getName, name)  // 条件成立才拼
       .in(CollectionUtils.isNotEmpty(ids), Student::getId, ids)
       .orderByDesc(Student::getScore)
       .last("LIMIT 10");                                        // 慎用

List<Student> list = studentMapper.selectList(wrapper);
```

**常用方法**：

| 方法 | SQL |
| :--- | :--- |
| `eq/ne` | `=` / `<>` |
| `gt/ge/lt/le` | `>` `>=` `<` `<=` |
| `like/likeLeft/likeRight` | `LIKE '%x%'` / `'%x'` / `'x%'` |
| `in/notIn` | `IN` / `NOT IN` |
| `between/notBetween` | `BETWEEN` |
| `isNull/isNotNull` | `IS NULL` |
| `inSql/exists` | 子查询 |
| `and/or` | 嵌套条件 |
| `orderByAsc/Desc` | 排序 |

**复杂嵌套条件**：

```java
// WHERE class_id = 1 AND (age > 18 OR score > 90)
wrapper.eq(Student::getClassId, 1L)
       .and(w -> w.gt(Student::getAge, 18)
                  .or()
                  .gt(Student::getScore, 90));
```

> ⚠️ **`or()` 不加括号是经典 bug**：`A.eq(...).or().eq(...)` 会把条件串成 `A AND ... OR ...`，导致查询范围被放大。**一定要用 `and(w -> ...)` / `or(w -> ...)` 包一层**。

> ⚠️ **`wrapper.last("ORDER BY ${sort}")` 也是注入点**，`last` 只是拼接，不校验内容。

> ⚠️ **`QueryWrapper` 的字符串列名容易写错且重构不安全**，一律用 `LambdaQueryWrapper`。

### 10.5 IService / ServiceImpl

```java
public interface StudentService extends IService<Student> {
    List<Student> topN(int n);
}

@Service
public class StudentServiceImpl extends ServiceImpl<StudentMapper, Student>
        implements StudentService {

    @Override
    public List<Student> topN(int n) {
        return lambdaQuery()
                .orderByDesc(Student::getScore)
                .last("LIMIT " + n)          // n 来自内部，可接受
                .list();
    }
}
```

```java
// IService 提供的常用方法
save(entity);
saveBatch(list);
saveOrUpdate(entity);
updateById(entity);
removeById(id);
removeByIds(ids);
getById(id);
list(wrapper);
page(page, wrapper);
count(wrapper);
lambdaQuery().eq(...).list();
lambdaUpdate().eq(...).set(...).update();
```

> ⚠️ **`saveBatch` 底层是 JDBC 批处理 + 逐条 `insert`**，不是"一条 SQL 插多条"。它会开事务、分批提交（默认 1000 条/批）。**数据量大时性能仍不如手写多值 `INSERT`**，见第十二章。

### 10.6 自动填充

```java
@Component
public class MetaObjectHandlerImpl implements MetaObjectHandler {

    @Override
    public void insertFill(MetaObject metaObject) {
        strictInsertFill(metaObject, "createTime", LocalDateTime.class, LocalDateTime.now());
        strictInsertFill(metaObject, "updateTime", LocalDateTime.class, LocalDateTime.now());
        strictInsertFill(metaObject, "deleted", Integer.class, 0);
    }

    @Override
    public void updateFill(MetaObject metaObject) {
        strictUpdateFill(metaObject, "updateTime", LocalDateTime.class, LocalDateTime.now());
    }
}
```

> ⚠️ **`strictInsertFill` 只在字段值为 `null` 时填充**；`setFieldValByName` 则强制覆盖。**`updateById(null 对象)` 不会触发填充**，因为整个对象为空。
>
> ⚠️ **批量插入 `saveBatch` 也会触发填充**（走 `insert` 流程），但**手写 XML 的批量插入不会**。

### 10.7 逻辑删除

```yaml
mybatis-plus:
  global-config:
    db-config:
      logic-delete-field: deleted
      logic-delete-value: 1
      logic-not-delete-value: 0
```

```java
studentMapper.deleteById(1L);
// 实际执行：UPDATE student SET deleted = 1 WHERE id = 1 AND deleted = 0

studentMapper.selectById(1L);
// 实际执行：SELECT ... WHERE id = 1 AND deleted = 0
```

> ⚠️ **逻辑删除后，唯一索引会冲突**。一个用户被逻辑删除后，同名用户无法再插入（唯一索引还占着）。解决方案：唯一索引加 `deleted` 列，或用"删除时间"作为区分。
>
> ⚠️ **手写 XML 不会自动加 `deleted = 0`**，必须自己写。
>
> ⚠️ **逻辑删除会让表无限增长**，需配合归档任务。

### 10.8 乐观锁

```java
@Version
private Integer version;
```

```java
Student s = studentMapper.selectById(1L);
s.setScore(new BigDecimal("95"));
int rows = studentMapper.updateById(s);
if (rows == 0) {
    throw new BizException("数据已被其他用户修改，请刷新后重试");
}
```

> ⚠️ **`@Version` 必须配合 `OptimisticLockerInnerInterceptor`**，且**必须是 `updateById` 或 `update(entity, wrapper)`**，手写 XML 不生效。
>
> ⚠️ **版本号初值建议设为 0 或 1，且 `version` 字段不允许为 null**，否则第一次更新不生效。

### 10.9 主键策略

| 策略 | 说明 | 适用 |
| :--- | :--- | :--- |
| `AUTO` | 数据库自增 | 单库单表，最简单 |
| `ASSIGN_ID`（默认） | 雪花算法 `Long` | 分布式、分表 |
| `ASSIGN_UUID` | UUID 字符串 | 非自增主键 |
| `INPUT` | 手动赋值 | 业务自定义 |

> ⚠️ **雪花算法生成的 `Long` 前端会丢精度**（JS 的 `Number` 最大安全整数是 2^53）。必须在序列化时转 `String`：
>
> ```java
> @JsonSerialize(using = ToStringSerializer.class)
> private Long id;
> ```

### 10.10 多租户与动态表名

```java
// 多租户：自动给所有 SQL 加 tenant_id 条件
interceptor.addInnerInterceptor(new TenantLineInnerInterceptor(
        new TenantLineHandler() {
            @Override
            public Expression getTenantId() {
                return new LongValue(TenantContext.getTenantId());
            }
            @Override
            public String getTenantIdColumn() {
                return "tenant_id";
            }
            @Override
            public boolean ignoreTable(String tableName) {
                return "sys_dict".equals(tableName);   // 字典表不分租户
            }
        }));
```

> ⚠️ **多租户插件对 `UNION`、子查询、`INSERT ... SELECT` 支持有限**，复杂 SQL 需要手动 `@InterceptorIgnore(tenantLine = "true")` 跳过。

---

## 十一、注解 vs XML：怎么选

| 场景 | 推荐 |
| :--- | :--- |
| 简单单表 CRUD | BaseMapper（连 SQL 都不用写） |
| 简单的 1~2 表查询 | 注解 `@Select` |
| 动态 SQL（`<if>/<foreach>`） | **XML** |
| 复杂联表、嵌套映射 | **XML** |
| 需要复用的 SQL 片段 | **XML** |
| 需要 DBA 审 SQL | **XML** |

```java
@Select("SELECT * FROM student WHERE id = #{id}")
Student selectById(@Param("id") Long id);

@Insert("INSERT INTO student(name, age) VALUES(#{name}, #{age})")
@Options(useGeneratedKeys = true, keyProperty = "id")
int insert(Student student);

@Update("<script>" +
        "UPDATE student " +
        "<set>" +
        "  <if test='name != null'>name = #{name},</if>" +
        "  <if test='age != null'>age = #{age},</if>" +
        "</set>" +
        "WHERE id = #{id}" +
        "</script>")
int updateDynamic(Student student);
```

> ⚠️ **注解里写 `<script>` 是灾难**：字符串拼接、无语法高亮、无格式化、无法复用 `<sql>`、`<` 和 `>` 需要转义。**超过 3 行 SQL 就挪到 XML。**

### 11.1 XML 的组织方式

```text
src/main/resources/mapper/
├── student/
│   ├── StudentMapper.xml
│   └── StudentExtMapper.xml
├── class/
│   └── ClassMapper.xml
└── common/
    └── CommonSql.xml         # 公共 SQL 片段（注意 namespace 冲突）
```

**命名空间**：`namespace` 必须等于 Mapper 接口全限定名。**多个 XML 指向同一个 Mapper 是允许的**（`namespace` 相同，`id` 不重复），这样可以把基础 CRUD 和复杂查询拆开。

---

## 十二、批量操作的性能问题 ⭐⭐

这是实际开发中**最能体现水平**的一块。

### 12.1 三种批量插入方式对比

```java
// 方式 1：循环单条插入（最慢）
for (Student s : list) {
    studentMapper.insert(s);
}
// 1000 条 = 1000 次网络往返 + 1000 次事务

// 方式 2：MP saveBatch（较好，仍是逐条 PreparedStatement）
studentService.saveBatch(list, 1000);

// 方式 3：一条多值 INSERT（最快）
studentMapper.insertBatch(list);
```

```xml
<insert id="insertBatch">
    INSERT INTO student (name, age, class_id)
    VALUES
    <foreach collection="list" item="s" separator=",">
        (#{s.name}, #{s.age}, #{s.classId})
    </foreach>
</insert>
```

**性能对比（1 万条，参考值）**：

| 方式 | 耗时 | 说明 |
| :--- | :--- | :--- |
| 循环单条 | ~30s | 受网络往返和事务开销拖累 |
| `saveBatch` | ~3s | 批处理，一条 SQL 一条记录 |
| 多值 INSERT | ~0.3s | 一条 SQL 多条记录 |
| `rewriteBatchedStatements=true` + `saveBatch` | ~0.5s | **MySQL 驱动优化，强烈推荐** |

### 12.2 MySQL 的 `rewriteBatchedStatements`

```text
jdbc:mysql://...?rewriteBatchedStatements=true
```

开启后，JDBC 把多条 `INSERT ... VALUES (...)` 合并成一条多值 SQL。**不开这个参数，`saveBatch` 的性能优势会大打折扣**。

> ⚠️ `rewriteBatchedStatements=true` 只对 `INSERT`/`UPDATE` 的批处理有效，且**要求 `useServerPrepStmts=false`**（默认就是 false）。开启后要注意 `max_allowed_packet`，单批次不要超过几百 KB。

### 12.3 批量更新的坑

```xml
<!-- 方式 1：CASE WHEN（推荐，单条 SQL） -->
<update id="updateBatchById">
    UPDATE student
    <trim prefix="SET" suffixOverrides=",">
        <foreach collection="list" item="s">
            <trim prefix="name = CASE id" suffix="END,">
                WHEN #{s.id} THEN #{s.name}
            </trim>
        </foreach>
    </trim>
    WHERE id IN
    <foreach collection="list" item="s" open="(" separator="," close=")">
        #{s.id}
    </foreach>
</update>
```

> ⚠️ **`ON DUPLICATE KEY UPDATE` 不要滥用**：它会隐式锁更多行，且在高并发下容易死锁。**批量更新前先按 id 排序**，降低死锁概率。
>
> ⚠️ **每次批量不要超过 1000 条**，否则 SQL 会非常长，`max_allowed_packet` 和 binlog 写入都会成为瓶颈。

### 12.4 大事务问题

批量操作如果在一个 `@Transactional` 里执行 10 万条：

- **Undo Log 膨胀**，回滚极慢
- **锁持有时间长**，阻塞其他事务
- **主从延迟**（binlog 大量写入）
- **连接池被占满**（长事务不释放连接）

**方案**：分批提交（每 1000 条一个事务），或用 `TransactionTemplate` 手动控制。

```java
public void batchInsert(List<Student> list) {
    int batchSize = 1000;
    for (int i = 0; i < list.size(); i += batchSize) {
        List<Student> sub = list.subList(i, Math.min(i + batchSize, list.size()));
        transactionTemplate.executeWithoutResult(status -> studentMapper.insertBatch(sub));
    }
}
```

> ⚠️ **分批后就不是"全成功或全失败"了**，需要幂等设计（重复插入用唯一索引忽略）。

### 12.5 批量查询的 `IN` 陷阱

```java
// ❌ 10000 个 ID 一次 IN
studentMapper.selectBatchIds(ids);   // SQL 可能超过 1MB

// ✅ 分批
List<List<Long>> partitions = Lists.partition(ids, 500);
List<Student> result = partitions.stream()
        .flatMap(p -> studentMapper.selectBatchIds(p).stream())
        .toList();
```

---

## 十三、事务与 MyBatis

### 13.1 Spring 管理事务

```java
@Service
@RequiredArgsConstructor
public class StudentService {

    private final StudentMapper studentMapper;
    private final ScoreMapper scoreMapper;

    @Transactional(rollbackFor = Exception.class)
    public void createWithScore(Student student, Score score) {
        studentMapper.insert(student);
        score.setStudentId(student.getId());
        scoreMapper.insert(score);
    }
}
```

**关键点**：

1. `@Transactional` 必须作用在 **public 方法**上
2. **同类内部调用不生效**（不走代理）
3. **默认只回滚 `RuntimeException`**，受检异常需要 `rollbackFor = Exception.class`
4. **异步方法（`@Async`）和事务不共用线程**，异步里的操作不在原事务中
5. **事务只在 Spring 管理的 Bean 上生效**，`new` 出来的对象没有代理

### 13.2 MyBatis 的 `SqlSession` 与连接释放

Spring 集成后：

- 非事务方法：每次操作从 `SqlSessionTemplate` 拿连接，**执行完立即归还**
- 事务方法：连接绑定到 `TransactionSynchronizationManager`，**事务提交后才归还**

> ⚠️ **没有 `@Transactional` 的方法里连续查 100 次，会获取并归还 100 次连接**（虽然连接池复用，但仍有开销）。**需要多次数据库操作的方法必须加 `@Transactional`**（哪怕只读，也需要保证 `SqlSession` 复用）。

### 13.3 事务传播与 MyBatis

| 传播行为 | 说明 | 常见误用 |
| :--- | :--- | :--- |
| `REQUIRED`（默认） | 有事务就加入，没有就新建 | — |
| `REQUIRES_NEW` | 总是新建事务，挂起外层 | **连接池小时容易耗尽** |
| `NESTED` | 嵌套事务（savepoint） | MyBatis 支持，但注意动态数据源切换会失效 |

### 13.4 事务内切换数据源不生效

```java
@Transactional
public void wrong() {
    DynamicDataSourceContextHolder.push("slave");
    studentMapper.selectById(1L);   // 仍在主库！
}
```

**原因**：`@Transactional` 开启时，`SqlSession` 已绑定连接，**连接在事务开始时确定，中途不会切换**。

**解决**：读走从库的方法**不要加 `@Transactional`**，或用 `@DS` 注解在方法级切换（`dynamic-datasource` 的实现是 AOP 在方法执行前切）。

---

## 十四、代码生成器

### 14.1 MyBatis-Plus Generator

```xml
<dependency>
    <groupId>com.baomidou</groupId>
    <artifactId>mybatis-plus-generator</artifactId>
    <version>3.5.9</version>
</dependency>
<dependency>
    <groupId>org.apache.velocity</groupId>
    <artifactId>velocity-engine-core</artifactId>
    <version>2.3</version>
</dependency>
```

```java
public class CodeGenerator {
    public static void main(String[] args) {
        FastAutoGenerator.create(
                "jdbc:mysql://127.0.0.1:3306/study?serverTimezone=Asia/Shanghai",
                "root", "root")
            .globalConfig(builder -> builder
                    .author("leo")
                    .outputDir(System.getProperty("user.dir") + "/src/main/java")
                    .disableOpenDir())
            .packageConfig(builder -> builder
                    .parent("com.example.study")
                    .moduleName("system")
                    .entity("entity")
                    .mapper("mapper")
                    .service("service")
                    .serviceImpl("service.impl")
                    .controller("controller")
                    .xml("mapper"))
            .strategyConfig(builder -> builder
                    .addInclude("student", "class")
                    .addTablePrefix("t_", "sys_")
                    .entityBuilder()
                        .enableLombok()
                        .enableTableFieldAnnotation()
                        .logicDeleteColumnName("deleted")
                        .versionColumnName("version")
                    .controllerBuilder()
                        .enableRestStyle()
                    .mapperBuilder()
                        .enableBaseResultMap()
                        .enableBaseColumnList())
            .execute();
    }
}
```

**生成后仍需要人工调整**：

- 补充业务字段的 `@TableField`（JSON、枚举）
- 检查主键策略
- 调整注释和校验注解
- 删除不需要的字段

> 💡 **代码生成器只解决"样板"，不解决"设计"**。表结构设计错了，生成的代码只会错得更规整。

### 14.2 模板定制

把 `templates/entity.java.vm` 拷到 `src/main/resources/templates`，修改即可。**实际项目会把公司规范（包名、注释格式、Swagger 注解、参数校验）固化到模板里**，这是团队效率的关键。

---

## 十五、多数据源与读写分离

### 15.1 `dynamic-datasource-spring-boot-starter`

```xml
<dependency>
    <groupId>com.baomidou</groupId>
    <artifactId>dynamic-datasource-spring-boot3-starter</artifactId>
    <version>4.3.0</version>
</dependency>
```

```yaml
spring:
  datasource:
    dynamic:
      primary: master
      strict: false
      datasource:
        master:
          url: jdbc:mysql://127.0.0.1:3306/study
          username: root
          password: root
        slave_1:
          url: jdbc:mysql://127.0.0.1:3307/study
          username: root
          password: root
        slave_2:
          url: jdbc:mysql://127.0.0.1:3308/study
          username: root
          password: root
```

```java
@Service
public class StudentService {

    @DS("slave_1")                       // 方法级指定数据源
    public Student queryById(Long id) {
        return studentMapper.selectById(id);
    }
}
```

```java
// 方法级 > 类级 > 默认
@DS("master")
@Service
public class OrderService {
    @DS("slave")
    public List<Order> list() { ... }
}
```

**读写分离方案**：

1. **`@DS` 显式指定**（推荐，可控）
2. **AOP 自动路由**：根据方法名 `select/list/get/count` 前缀走从库
3. **中间件**：ShardingSphere、MyCat

> ⚠️ **主从延迟**：写后立刻读，可能读到旧数据。**"写后读"场景必须强制走主库**。
>
> ⚠️ **事务内不能切换数据源**（见 13.4），跨库事务需要 Seata 等分布式事务框架。

---

## 十六、性能优化与 SQL 排查 ⭐

### 16.1 打开 SQL 日志（生产可用）

```yaml
logging:
  level:
    com.example.study.mapper: debug      # 只打印业务 Mapper
```

```yaml
mybatis-plus:
  configuration:
    log-impl: org.apache.ibatis.logging.slf4j.Slf4jImpl
```

> ⚠️ **不要用 `StdOutImpl`**。它绕过日志框架，没法按环境关闭、没法采集到 ELK。

### 16.2 用 P6Spy 打印带参数的完整 SQL

```xml
<dependency>
    <groupId>p6spy</groupId>
    <artifactId>p6spy</artifactId>
    <version>3.9.1</version>
</dependency>
```

```yaml
spring:
  datasource:
    driver-class-name: com.p6spy.engine.spy.P6SpyDriver
    url: jdbc:p6spy:mysql://127.0.0.1:3306/study
```

```properties
# spy.properties
appender=com.p6spy.engine.spy.appender.Slf4JLogger
logMessageFormat=com.p6spy.engine.spy.appender.CustomLineFormat
customLogMessageFormat=%(currentTime) | %(executionTime) ms | %(sql)
```

输出：`2026-11-01 10:00:00 | 12 ms | select * from student where id=1`

> ⚠️ P6Spy 只建议在**测试/预发环境**开启，生产会带来额外开销。

### 16.3 常见性能问题

| 问题 | 表现 | 解决 |
| :--- | :--- | :--- |
| N+1 查询 | 一条列表查询触发 N 条子查询 | join / 批量查 / `@BatchSize` |
| 全表扫描 | `type=ALL` | 加索引，检查 `WHERE` 是否用到索引列 |
| 索引失效 | `type=ALL` 但明明有索引 | 函数、隐式转换、`LIKE '%x'`、`OR` |
| 深分页 | `LIMIT 1000000, 20` 很慢 | 游标分页（`WHERE id > lastId`） |
| 大结果集 | 一次查 10 万行 | 分页 / 流式查询 |
| 大事务 | 锁等待、主从延迟 | 拆批 |
| 连接泄漏 | 连接池打满 | 检查 `@Transactional` 范围和异步线程 |

### 16.4 深分页优化

```sql
-- ❌ 深分页：扫描 100 万行再丢弃
SELECT * FROM student ORDER BY id LIMIT 1000000, 20;

-- ✅ 游标分页（要求 id 有序）
SELECT * FROM student WHERE id > 1000000 ORDER BY id LIMIT 20;

-- ✅ 延迟关联（子查询先拿主键）
SELECT s.* FROM student s
JOIN (SELECT id FROM student ORDER BY id LIMIT 1000000, 20) t ON s.id = t.id;
```

### 16.5 流式查询（大数据导出）

```java
@Select("SELECT * FROM student")
@Options(fetchSize = 1000, resultSetType = ResultSetType.FORWARD_ONLY)
Cursor<Student> selectCursor();

// 使用
try (Cursor<Student> cursor = studentMapper.selectCursor()) {
    cursor.forEach(student -> writeToExcel(student));
}
```

> ⚠️ **流式查询必须在事务中**，且不能提前关闭 `SqlSession`，否则会报 `Streaming result set is closed`。

### 16.6 SQL 执行计划速查

```sql
EXPLAIN SELECT * FROM student WHERE class_id = 1 AND age > 18;

-- 重点关注
-- type: ALL(全表) < index < range < ref < eq_ref < const
-- key: 实际使用的索引
-- rows: 预估扫描行数
-- Extra: Using filesort / Using temporary 需要警惕
```

---

## 十七、实际开发规范与踩坑清单

### 17.1 编码规范

1. **Mapper 接口只定义方法，SQL 全部放 XML**（复杂项目）
2. **一律使用 `#{}`**，`${}` 必须白名单校验
3. **多参数一律 `@Param`**
4. **禁止 `SELECT *`**（尤其是联表）
5. **`resultMap` 显式声明**，不要依赖自动映射做复杂场景
6. **动态 SQL 的 `test` 判空要区分数值 0 和空字符串**
7. **`<sql>` 片段命名带模块前缀**，避免冲突
8. **`foreach` 前判空**，避免 `IN ()`
9. **分页必须限制最大条数**
10. **Mapper 方法不要重载**

### 17.2 踩坑清单

| # | 坑 | 现象 | 解决 |
| :--- | :--- | :--- | :--- |
| 1 | Boot 3 用 boot2 的 starter | 自动配置不生效 | 换 `mybatis-plus-spring-boot3-starter` |
| 2 | XML 未打包 | `Invalid bound statement` | 配 `<resources>` |
| 3 | `test="status != null and status != ''"` | `status=0` 时条件丢失 | 只判 `!= null` |
| 4 | 多参数未加 `@Param` | `Parameter 'xxx' not found` | 加 `@Param` |
| 5 | `resultType` 遇到同名列 | 数据被覆盖 | 显式别名 / `resultMap` |
| 6 | `condition` 为空的 `IN` | SQL 语法错误 | `<if>` 判空 |
| 7 | `updateById` 无法置 null | 字段改不成空 | 用 `UpdateWrapper.set(field, null)` |
| 8 | 雪花 ID 前端精度丢失 | 末尾变 0 | `ToStringSerializer` |
| 9 | `@Cacheable` + 事务顺序 | 缓存写入后事务回滚 | `transactionAware()` 或先删缓存 |
| 10 | 二级缓存跨 namespace | 读到旧数据 | 不开启二级缓存 |
| 11 | `selectOne` 查到多条 | `TooManyResultsException` | 加 `LIMIT 1` 或用 `selectList` |
| 12 | `PageHelper` 作用到错误 SQL | 分页结果错乱 | 紧跟查询 / 换 MP 分页 |
| 13 | 逻辑删除 + 唯一索引 | 无法插入同名数据 | 唯一索引带 deleted |
| 14 | `saveBatch` 未开 `rewriteBatchedStatements` | 批量插入慢 | 连接串加参数 |
| 15 | 大事务批量 | 锁等待、主从延迟 | 分批提交 |
| 16 | `foreach` 超 1000 条 | SQL 超长报错 | 分批 |
| 17 | 事务内切换数据源 | 仍走原库 | 方法级 `@DS` + 不加事务 |
| 18 | `@Transactional` 自调用 | 事务不生效 | 拆类 / 注入自身代理 |
| 19 | `LocalDateTime` 未注册 | 反序列化异常 | 配置 Jackson `JavaTimeModule` |
| 20 | 字段全 null 的 `updateById` | SQL 语法错误 | 先判断 / 用 Wrapper |
| 21 | `MAPPER` 在异步线程使用 | `SqlSession` 已关闭 | 在同一线程完成数据准备 |
| 22 | 多租户插件 + 复杂 SQL | 租户条件漏加 | `@InterceptorIgnore` |
| 23 | 乐观锁未加插件 | 版本号不生效 | 加 `OptimisticLockerInnerInterceptor` |
| 24 | 自动填充在 XML 不生效 | `createTime` 为 null | XML 手动赋值或 DB 默认值 |

### 17.3 DBA 视角的规范

- 索引：单表索引不超过 5 个，联合索引遵循最左前缀
- 字段：不用 `NULL` 表示业务含义，用默认值
- 金额用 `DECIMAL`，不用 `FLOAT/DOUBLE`
- 时间用 `DATETIME`，不用 `TIMESTAMP`（2038 问题）
- 主键用 `BIGINT UNSIGNED AUTO_INCREMENT` 或雪花 ID
- **禁止在 SQL 中对索引列做函数运算**（`DATE(create_time) = '2026-11-01'` 会失效）

---

## 📌 在 Spring Boot 中

| 本篇概念 | Spring Boot 中的对应 |
| :--- | :--- |
| 数据源 | `spring.datasource.*` + HikariCP 自动配置 |
| Mapper 扫描 | `@MapperScan` |
| SQL 日志 | `logging.level.<mapper 包>: debug` |
| 事务 | `@Transactional` + `DataSourceTransactionManager` |
| 分页 | MP `PaginationInnerInterceptor` / PageHelper |
| 多数据源 | `dynamic-datasource-spring-boot3-starter` + `@DS` |
| 读写分离 | `@DS` 或 ShardingSphere |
| 代码生成 | `mybatis-plus-generator` |
| 数据库版本控制 | **Liquibase** / Flyway（见 [Liquibase学习文档](Liquibase学习文档.md)） |
| 复杂查询 | MyBatis XML，而不是 JPA 的 Specification |
| 慢 SQL 排查 | P6Spy + `EXPLAIN` |

**和本仓库其他文档的关系**：

- [MySQL 学习文档](MySQL学习文档.md) → SQL 语法基础，MyBatis 只是"SQL 的 Java 封装"
- [JDBC](JDBC.md) → MyBatis 底层就是 JDBC
- [Redis学习文档](Redis学习文档.md) → 缓存层通常加在 Service 之上，注意与事务的顺序
- [15-数据库操作_MyBatis](../Spring实战/15-数据库操作_MyBatis.md) → 完整模块示例
- [17-数据库操作_MyBatisPlus](../Spring实战/17-数据库操作_MyBatisPlus.md) → MP 完整模块示例
- [44-多数据源_MyBatis](../Spring实战/44-多数据源_MyBatis.md) / [49-动态数据源_DynamicDataSource](../Spring实战/49-动态数据源_DynamicDataSource.md) → 多数据源工程化
- [54-数据库版本控制_Flyway](../Spring实战/54-数据库版本控制_Flyway.md) → Flyway 与 Liquibase 对比

> 一句话：**MyBatis 的价值不是"少写 JDBC 样板"，而是"让你对 SQL 拥有完全的掌控权"**。掌控权越大，责任越大——索引、分页、动态条件、批量、事务，每一个都要你自己想清楚。

---

## 本章小结

1. **定位**：MyBatis = "你写 SQL，它做映射"；MyBatis-Plus = "单表 CRUD 免写，动态查询更爽"。
2. **原理**：Mapper 接口无实现类是因为 **JDK 动态代理 + MapperProxy**；`Invalid bound statement` 基本都是配置问题。
3. **安全**：`#{}` 编译为占位符（安全），`${}` 直接拼接（危险），必须用白名单。
4. **动态 SQL**：`<if>/<where>/<set>/<foreach>/<choose>` 是 XML 的核心价值；判空时**数字 0 不能和空字符串一起判断**。
5. **缓存**：一级缓存事务内有效，二级缓存**基本不要开**，需要缓存用 Redis。
6. **分页**：用 MP 分页插件，限制 `maxLimit`，注意联表 count 的准确性。
7. **MP 核心**：`BaseMapper` + `IService` + `LambdaWrapper` + 自动填充 + 逻辑删除 + 乐观锁 + 多租户。
8. **批量**：`rewriteBatchedStatements=true` + 多值 INSERT 是性能关键，且要防大事务。
9. **事务**：`@Transactional` 的代理机制、传播行为、数据源切换，都是线上事故高发区。
10. **优化**：N+1、深分页、索引失效、流式查询、P6Spy + EXPLAIN。

**动手练习**：

1. 不写实现类，用 `@MapperScan` + XML 完成一个学生的完整 CRUD，并复现一次 `Invalid bound statement` 后修复。
2. 写一个"多条件动态查询"：姓名模糊、年龄区间、班级、状态（状态 0/1/2），验证状态 0 不会被漏掉。
3. 对比 `saveBatch` 与多值 INSERT 在 1 万条数据下的耗时，观察 `rewriteBatchedStatements` 开启前后的差异。
4. 用 MP 的条件构造器实现"班级 = 1 且 (年龄 > 18 或 分数 > 90)"，并验证 `or()` 不加括号的错误写法。
5. 配置逻辑删除 + 乐观锁，验证删除后的查询过滤和并发更新的版本控制。
6. 用 `@DS` 配置一主一从，验证 `@Transactional` 方法内切换到从库是否生效，并解释原因。
