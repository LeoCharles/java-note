# 条件装配与 Profile

上一篇学了 Bean 的完整生命周期。但实际开发中，"注册哪些 Bean"往往不是死的——开发环境连本地数据库、生产环境连线上数据库；引入了 Redis jar 包就自动配 Redis，没引入就跳过。这些"根据条件决定是否注册 Bean"的机制，就是**条件装配**。Spring Boot 的"自动配置"就是靠它实现的。

> 💡 条件装配是"智能容器"的关键——容器不再傻傻地注册所有配置的 Bean，而是根据环境、依赖、配置属性聪明地决定"注册谁、不注册谁"。

---

## 一、@Profile：环境切换

### 1.1 什么是 Profile

同一个应用在不同环境（开发/测试/生产）需要不同的 Bean 配置。`@Profile` 让容器**根据当前激活的环境来决定注册哪个 Bean**。

```java
@Configuration
public class DataSourceConfig {

    @Bean
    @Profile("dev")   // 只在 dev 环境下注册
    public DataSource devDataSource() {
        HikariConfig config = new HikariConfig();
        config.setJdbcUrl("jdbc:mysql://localhost:3306/dev_db");
        config.setUsername("root");
        config.setPassword("dev123");
        return new HikariDataSource(config);
    }

    @Bean
    @Profile("prod")  // 只在 prod 环境下注册
    public DataSource prodDataSource() {
        HikariConfig config = new HikariConfig();
        config.setJdbcUrl("jdbc:mysql://prod-cluster:3306/prod_db");
        config.setUsername("prod_user");
        config.setPassword("${DB_PASSWORD}"); // 从环境变量获取
        return new HikariDataSource(config);
    }
}
```

### 1.2 激活 Profile

**方式一：`application.yml` / `application.properties`**

```yaml
# application.yml
spring:
  profiles:
    active: dev
```

**方式二：启动参数**

```bash
java -jar myapp.jar --spring.profiles.active=prod
```

**方式三：环境变量**

```bash
export SPRING_PROFILES_ACTIVE=prod
```

**方式四：代码中设置（测试用）**

```java
AnnotationConfigApplicationContext ctx = new AnnotationConfigApplicationContext();
ctx.getEnvironment().setActiveProfiles("dev");
ctx.register(AppConfig.class);
ctx.refresh();
```

### 1.3 @Profile 的高级用法

```java
// 1. 取反：非 prod 环境下注册
@Bean
@Profile("!prod")
public DataSource nonProdDataSource() { ... }

// 2. 多个环境：dev 或 test 都注册
@Bean
@Profile({"dev", "test"})
public DataSource devOrTestDataSource() { ... }

// 3. 类级别 + 方法级别组合
@Configuration
@Profile("dev")  // 整个类只在 dev 环境生效
public class DevConfig {

    @Bean
    @Profile("mysql")  // dev + mysql 两个条件都满足才注册
    public DataSource devMysqlDataSource() { ... }

    @Bean
    @Profile("h2")     // dev + h2 两个条件都满足才注册
    public DataSource devH2DataSource() { ... }
}
```

### 1.4 多环境配置文件的命名约定

Spring Boot 支持按 `application-{profile}.yml` 命名配置文件，启动时自动加载对应环境的配置：

```
src/main/resources/
├── application.yml              # 公共配置
├── application-dev.yml          # 开发环境
├── application-test.yml         # 测试环境
└── application-prod.yml         # 生产环境
```

```yaml
# application-dev.yml
server:
  port: 8080
spring:
  datasource:
    url: jdbc:mysql://localhost:3306/dev_db

# application-prod.yml
server:
  port: 80
spring:
  datasource:
    url: jdbc:mysql://prod-cluster:3306/prod_db
```

> 💡 同名配置项，`application-{profile}.yml` 会覆盖 `application.yml` 中的值。公共的放公共文件，差异的放 Profile 文件。

---

## 二、@Conditional：条件装配基础

### 2.1 Spring 原生的 @Conditional

`@Profile` 本质上就是 `@Conditional` 的特例。`@Conditional` 是更通用的条件注解，**根据自定义条件决定是否注册 Bean**：

```java
// 第一步：自定义条件类
public class MySQLDatabaseCondition implements Condition {
    @Override
    public boolean matches(ConditionContext context, AnnotatedTypeMetadata metadata) {
        // 检查 classpath 中是否有 MySQL 驱动
        try {
            Class.forName("com.mysql.cj.jdbc.Driver");
            return true;   // 有 → 注册 Bean
        } catch (ClassNotFoundException e) {
            return false;  // 没有 → 不注册
        }
    }
}

// 第二步：使用 @Conditional
@Configuration
public class DatabaseConfig {

    @Bean
    @Conditional(MySQLDatabaseCondition.class)  // 仅当 MySQL 驱动存在时注册
    public DataSource mysqlDataSource() {
        return mysqlDataSource();
    }
}
```

### 2.2 Spring Boot 的条件注解全家桶

Spring Boot 在 `@Conditional` 基础上，封装了一系列更易用的条件注解——这些就是"自动配置"的砖瓦：

| 注解 | 条件 | 典型用途 |
| :--- | :--- | :--- |
| `@ConditionalOnClass` | classpath 中存在指定类 | 引入 jar 包 → 自动配 |
| `@ConditionalOnMissingClass` | classpath 中不存在指定类 | 没引入 → 跳过 |
| `@ConditionalOnBean` | 容器中存在指定 Bean | 等某个 Bean 注册后再配 |
| `@ConditionalOnMissingBean` | 容器中不存在指定 Bean | "你没配我才帮你配" |
| `@ConditionalOnProperty` | 配置文件中存在指定属性 | `feature.enabled=true` 才生效 |
| `@ConditionalOnExpression` | SpEL 表达式为 true | 复杂条件组合 |
| `@ConditionalOnResource` | classpath 中存在指定资源文件 | 有 mybatis-config.xml 就启用 XML 配置 |
| `@ConditionalOnWebApplication` | 当前是 Web 应用 | Web 环境才注册某些 Bean |
| `@ConditionalOnNotWebApplication` | 当前不是 Web 应用 | 批处理环境才注册 |

### 2.3 Spring Boot 自动配置实战拆解

不贴 Spring Boot 源码，用一个模拟例子展示"自动配置"的工作原理：

```java
@Configuration
@ConditionalOnClass({RedisConnectionFactory.class})
// ↑ 条件1：classpath 中有 RedisConnectionFactory（即引入了 spring-boot-starter-data-redis）
@ConditionalOnMissingBean(RedisTemplate.class)
// ↑ 条件2：用户自己没有注册 RedisTemplate
@EnableConfigurationProperties(RedisProperties.class)
// ↑ 读取 spring.redis.* 的配置
public class RedisAutoConfiguration {

    @Bean
    @ConditionalOnMissingBean   // 用户没配才自动配
    public RedisTemplate<String, Object> redisTemplate(
            RedisConnectionFactory factory) {
        RedisTemplate<String, Object> template = new RedisTemplate<>();
        template.setConnectionFactory(factory);
        // 设置序列化器...
        return template;
    }
}
```

**这段代码说了什么？**

```
如果你引入了 Redis 的 Starter jar 包（@ConditionalOnClass）
      且
你自己没有注册 RedisTemplate（@ConditionalOnMissingBean）
      则
    Spring Boot 自动帮你注册一个 RedisTemplate
      否则
    用你自己配的那个
```

> 💡 这就是"自动配置"的完整逻辑：**引入 jar → 条件满足 → 自动注册 Bean → 用户没配才生效**。Spring Boot 几百个 AutoConfiguration 类，每个都是这套逻辑。

### 2.4 条件注解的优先级（匹配顺序）

多个条件注解可以叠加，必须**全部满足**才注册 Bean：

```java
@Bean
@ConditionalOnClass(DataSource.class)        // 条件1：有数据源
@ConditionalOnMissingBean(DataSource.class)  // 条件2：用户没配
@ConditionalOnProperty(
    prefix = "spring.datasource",
    name = "enabled",
    havingValue = "true",
    matchIfMissing = true                    // 条件3：没配也默认 true
)
public DataSource dataSource() {
    return new HikariDataSource();
}
```

---

## 三、配置优先级

### 3.1 Spring Boot 配置加载顺序

当多个地方定义了同名配置属性时，**优先级从高到低**：

```
1. 命令行参数          --server.port=9090                   ↑
2. 环境变量            SERVER_PORT=9090                     │ 高
3. application-{profile}.yml                               │ │
4. application.yml                                         │ │
5. @PropertySource 导入的配置文件                            │ 低
6. 代码中的默认值       @Value("${server.port:8080}")        ↓
```

> 💡 口诀：**"命令行 > 环境变量 > profile 文件 > 默认文件 > @PropertySource > 代码默认值"**

### 3.2 @ConfigurationProperties vs @Value

```java
// @Value：逐字段绑定，适合少量配置
@Component
public class AppInfo {
    @Value("${app.name}")
    private String name;
    @Value("${app.version:1.0.0}")  // 默认值
    private String version;
}

// @ConfigurationProperties：批量绑定，适合一组配置
@Component
@ConfigurationProperties(prefix = "app")  // 绑定 app.* 的配置
public class AppProperties {
    private String name;
    private String version;
    private List<String> authors;
    // getter/setter...
}
```

```yaml
app:
  name: myapp
  version: 2.0.0
  authors:
    - 张三
    - 李四
```

| | `@Value` | `@ConfigurationProperties` |
| :--- | :--- | :--- |
| **用法** | 逐字段 | 批量绑定 |
| **SpEL** | ✅ 支持 | ❌ 不支持 |
| **JSR303 校验** | ❌ | ✅ `@Validated` + `@NotNull` |
| **松散绑定** | ❌ | ✅ `app-name` ↔ `appName` |
| **适用** | 少量配置 | 一组相关配置 |

---

## 💻 实战案例

### 案例 1：多数据源的条件装配

模拟一个"多数据库支持"的场景：

```java
@Configuration
public class MultiDatabaseConfig {

    @Bean
    @ConditionalOnClass(name = "com.mysql.cj.jdbc.Driver")
    @ConditionalOnProperty(name = "db.type", havingValue = "mysql")
    public DataSource mysqlDataSource() {
        System.out.println(">>> 注册 MySQL 数据源");
        return createHikariDataSource("com.mysql.cj.jdbc.Driver",
                "jdbc:mysql://localhost:3306/mydb");
    }

    @Bean
    @ConditionalOnClass(name = "org.postgresql.Driver")
    @ConditionalOnProperty(name = "db.type", havingValue = "postgresql")
    public DataSource postgresqlDataSource() {
        System.out.println(">>> 注册 PostgreSQL 数据源");
        return createHikariDataSource("org.postgresql.Driver",
                "jdbc:postgresql://localhost:5432/mydb");
    }

    @Bean
    @ConditionalOnMissingBean(DataSource.class)  // 以上都没匹配才用这个
    public DataSource defaultDataSource() {
        System.out.println(">>> 注册 H2 内存数据库（默认）");
        return createHikariDataSource("org.h2.Driver",
                "jdbc:h2:mem:testdb");
    }
}
```

### 案例 2：功能开关

```java
// application.yml
// feature:
//   cache:
//     enabled: true
//   async:
//     enabled: false

@Configuration
public class FeatureToggleConfig {

    @Bean
    @ConditionalOnProperty(name = "feature.cache.enabled",
                           havingValue = "true", matchIfMissing = true)
    public CacheManager cacheManager() {
        return new ConcurrentMapCacheManager();
    }

    @Bean
    @ConditionalOnProperty(name = "feature.async.enabled",
                           havingValue = "true")
    public AsyncTaskExecutor asyncExecutor() {
        // async.enabled=false 时不会注册，@Async 将失效
        return new ThreadPoolTaskExecutor();
    }
}
```

> 💡 这个模式在微服务架构中非常实用——通过配置文件开关功能，不用改代码就能灵活控制哪些模块生效。

---

## 🎯 面试高频

### Q1：Spring Boot 的自动配置原理是什么？

**答**：核心是 `@Conditional` + 条件注解。每个 Starter 都有一个 `XXXAutoConfiguration` 类，上面标注了多个条件注解：

1. `@ConditionalOnClass`：判断 classpath 中是否有目标类（对应"你引入了这个 Starter 的 jar 包"）
2. `@ConditionalOnMissingBean`：判断容器中是否没有用户自己配的 Bean（对应"你没配我才帮你配"）
3. `@ConditionalOnProperty`：判断配置文件中是否开启了功能

所有条件都满足时，`@Bean` 方法才执行，向容器注册组件。这些 AutoConfiguration 类通过 `spring.factories`（Spring Boot 2.x）或 `spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports`（Spring Boot 3.x）被加载。

### Q2：@ConditionalOnMissingBean 有什么注意事项？

**答**：它判断的是 Bean 的注册顺序。**Spring Boot 会先注册用户自定义的 Bean，再处理自动配置**——所以用户定义的 `@Bean` 会"抢先注册"，自动配置的 `@ConditionalOnMissingBean` 发现已存在就不再注册。

但这个顺序依赖类加载和扫描顺序，复杂的依赖关系中 `@ConditionalOnMissingBean` 可能误判。生产级别建议：能显式配置就不要依赖缺失判断，或者用 `@ConditionalOnProperty` 配合 `matchIfMissing` 更可控。

---

## 📌 在 Spring Boot 中

- **`@SpringBootApplication` 的 `@EnableAutoConfiguration`** 就是条件装配的入口。它的 `@Import(AutoConfigurationImportSelector.class)` 会读取所有 `XXXAutoConfiguration` 类，每个 AutoConfiguration 类内部用 `@ConditionalOnXxx` 决定是否生效。
- **几乎所有 Spring Boot Starter 都是条件装配的实现**：`DataSourceAutoConfiguration`、`RedisAutoConfiguration`、`RabbitAutoConfiguration`、`SecurityAutoConfiguration`……引入 Starter → classpath 中有对应类 → `@ConditionalOnClass` 满足 → 自动注册 Bean。
- **自定义 Starter 的核心就是写 AutoConfiguration 类**。你的 AutoConfiguration 类用 `@ConditionalOnXxx` 控制生效条件，用 `@Bean` 注册组件，用 `@EnableConfigurationProperties` 读取配置——这就是自定义 Starter 的全部套路。
- **排除自动配置**：`@SpringBootApplication(exclude = {DataSourceAutoConfiguration.class})` 或 `spring.autoconfigure.exclude=...` 可以禁用特定自动配置——当你不想用某个 Starter 的默认行为时。

---

## 本章小结

| 知识点 | 要点 |
| :--- | :--- |
| @Profile | 根据环境激活不同 Bean；配合 `spring.profiles.active` 使用 |
| @Conditional | 条件装配的基础注解，自定义 Condition 实现 |
| @ConditionalOnClass | classpath 中有指定类 → 注册（自动配置的核心条件） |
| @ConditionalOnMissingBean | 用户没配 → 自动配（"约定优于配置"的关键） |
| @ConditionalOnProperty | 配置文件中有指定属性 → 注册（功能开关） |
| 配置优先级 | 命令行 > 环境变量 > profile文件 > 默认文件 > @PropertySource > 默认值 |
| @ConfigurationProperties | 批量绑定，支持松散绑定和校验 |

---

## 学习建议

1. **用 @Profile 模拟多数据源切换**：定义三个 DataSource Bean，分别标 `@Profile("dev")` / `@Profile("test")` / `@Profile("prod")`，然后分别激活 dev/test/prod 观察容器中实际注册了哪个。
2. **自己实现一个 @ConditionalOnClass 的模拟**：写一个 Condition，检测 classpath 中是否有某个类，有就注册 Bean、没有就跳过——亲手体验 Spring Boot 自动配置的底层。
3. **找一个 Spring Boot Starter 的 AutoConfiguration 源码看一眼**：比如 `RedisAutoConfiguration`、`DataSourceAutoConfiguration`，看它的类级别注解和 `@Bean` 方法，验证"条件装配"在真实源码中是怎么写的。