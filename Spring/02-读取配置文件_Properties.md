# 02 - Spring Boot 配置文件与属性注入

> 对应项目模块：`demo-properties`
> 前置知识：已学完 `01-SpringBoot入门_HelloWorld`，了解启动类、`application.yml`、`@RestController` 基本用法
> 学习目标：掌握把 `application.yml` 里的配置值读到 Java 代码里的两种方式，理解多环境配置（Profile）和 Maven 资源过滤，能独立为项目添加自定义配置。

---

## 一、本模块要解决什么问题？

在 HelloWorld 模块里，我们把端口、上下文路径写在 `application.yml`，Spring Boot 自动读取并应用。但实际开发中，你会有大量**自定义配置**需要自己读取，比如：

- 第三方 API 的 appKey、appSecret
- 业务参数：超时时间、重试次数、分页大小
- 环境相关：开发用本地库、生产用线上库，不同环境配置值不同

这些值不能写死在代码里（改一次要重新编译），而应该放在配置文件，程序启动时读取。本模块就演示怎么读、怎么注入到 Java 对象、怎么按环境切换。

本模块的最终效果：访问 `GET http://localhost:8080/demo/property`，返回一段 JSON，里面包含项目配置和开发者信息，且这些值来自 yml 配置文件，还能随环境（dev/prod）变化。

---

## 二、先看项目结构

```
demo-properties/
├── pom.xml
└── src/main/
    ├── java/com/xkcoding/properties/
    │   ├── SpringBootDemoPropertiesApplication.java   # 启动类
    │   ├── controller/
    │   │   └── PropertyController.java                # 控制器：返回配置值
    │   └── property/
    │       ├── ApplicationProperty.java              # 方式一：@Value 注入
    │       └── DeveloperProperty.java                # 方式二：@ConfigurationProperties
    └── resources/
        ├── application.yml                            # 主配置（指定激活哪个环境）
        ├── application-dev.yml                        # 开发环境配置
        ├── application-prod.yml                       # 生产环境配置
        └── META-INF/
            └── additional-spring-configuration-metadata.json  # 配置元数据
```

注意：相比 HelloWorld 模块，这里多了 `controller`、`property` 两个子包——这是真实项目的分层结构，启动类在根包 `com.xkcoding.properties`，业务类按职责分到子包，`@ComponentScan` 能扫到所有子包。

---

## 三、配置文件：主配置 + 多环境配置

### 3.1 主配置 `application.yml`

```yaml
server:
  port: 8080
  servlet:
    context-path: /demo
spring:
  profiles:
    active: prod
```

前两项（port、context-path）和 HelloWorld 一样。新增的关键是 `spring.profiles.active: prod`——它指定**当前激活哪个环境**。这里激活 `prod`，程序启动时会加载 `application-prod.yml` 的内容。

### 3.2 多环境配置文件

`application-dev.yml`（开发环境）：

```yaml
application:
  name: dev环境 @artifactId@
  version: dev环境 @version@
developer:
  name: dev环境 xkcoding
  website: dev环境 http://xkcoding.com
  qq: dev环境 237497819
  phone-number: dev环境 17326075631
```

`application-prod.yml`（生产环境）：

```yaml
application:
  name: prod环境 @artifactId@
  version: prod环境 @version@
developer:
  name: prod环境 xkcoding
  website: prod环境 http://xkcoding.com
  qq: prod环境 237497819
  phone-number: prod环境 17326075631
```

**Profile 的命名规则**：`application-{profile}.yml`，其中 `{profile}` 是环境名（dev、test、prod 等）。主配置 `application.yml` 用 `spring.profiles.active` 指定激活哪个。

**加载优先级**（重要）：

1. 先加载 `application.yml`（公共配置）
2. 再加载 `application-{active}.yml`（环境配置）
3. 环境 yml 里的同名 key 会**覆盖**主 yml 的值

所以公共配置（如端口、context-path）放 `application.yml`，各环境不同的值放 `application-{env}.yml`。

> 💡 前端类比：这像 Vite 的 `.env`、`.env.development`、`.env.production`。`import.meta.env.MODE` 决定加载哪个，原理和 Spring Profile 几乎一样。

### 3.3 `@artifactId@` 和 `@version@` 是什么？—— Maven 资源过滤

注意 yml 里出现了 `@artifactId@` 和 `@version@` 这种用 `@` 包裹的占位符。这不是 Spring 的语法，而是 **Maven 资源过滤（Resource Filtering）**。

看 `pom.xml` 里的这段：

```xml
<build>
    <finalName>demo-properties</finalName>
    <plugins>...</plugins>
    <resources>
        <resource>
            <directory>src/main/resources</directory>
            <filtering>true</filtering>   <!-- 关键：开启资源过滤 -->
        </resource>
    </resources>
</build>
```

`<filtering>true</filtering>` 告诉 Maven：在把资源文件拷到 `target/classes` 时，把里面的 `@xxx@` 占位符替换成 pom 里对应的属性值。

- `@artifactId@` → 替换成 pom 的 `<artifactId>`，即 `demo-properties`
- `@version@` → 替换成 pom 的 `<version>`，即 `1.0.0-SNAPSHOT`

所以最终生效的 `application-prod.yml` 实际是：

```yaml
application:
  name: prod环境 demo-properties
  version: prod环境 1.0.0-SNAPSHOT
```

> 💡 前端类比：这就像 webpack/Vite 的 `DefinePlugin` 或 `import.meta.env.VITE_*`，在构建时把占位符替换成实际值。Maven 用 `@...@`（Spring Boot 默认改成了 `@`，传统 Maven 是 `${...}`，但 `${}` 会和 Spring 的占位符冲突，所以 Spring Boot 父 POM 把它改成了 `@`）。

---

## 四、读取配置的两种方式

### 4.1 方式一：`@Value` —— 单个值注入

`property/ApplicationProperty.java`：

```java
@Data
@Component
public class ApplicationProperty {
    @Value("${application.name}")
    private String name;
    @Value("${application.version}")
    private String version;
}
```

逐个看：

- `@Component`：把这个类注册成 Spring Bean，Spring 启动时会创建它的实例放进容器。只有是 Bean，Spring 才会帮你注入配置值。
- `@Value("${application.name}")`：把 yml 里 `application.name` 的值注入到这个字段。`${...}` 是 Spring 的属性占位符语法。
- `@Data`：Lombok 注解，自动生成 getter、setter、toString、equals、hashCode 等方法，省得手写一堆样板代码。

**`@Value` 适合什么场景？** 配置项很少、零散，或者只需要读一两个值时，用 `@Value` 最快。

**`@Value` 的高级用法：**

```java
@Value("${application.name:默认名}")   // 冒号后是默认值，配置缺失时不报错
private String name;

@Value("${app.timeout:30}")            // 注入数字，自动类型转换
private int timeout;

@Value("${app.supported-types}")       // 注入 List（yml 里写成数组或逗号分隔）
private List<String> types;
```

### 4.2 方式二：`@ConfigurationProperties` —— 批量绑定

`property/DeveloperProperty.java`：

```java
@Data
@ConfigurationProperties(prefix = "developer")
@Component
public class DeveloperProperty {
    private String name;
    private String website;
    private String qq;
    private String phoneNumber;
}
```

- `@ConfigurationProperties(prefix = "developer")`：告诉 Spring，把 yml 里 `developer` 前缀下的所有配置，按属性名一一绑定到这个类的字段。
- yml 里是 `developer.phone-number`，类里字段是 `phoneNumber`——Spring Boot 用"松散绑定"（Relaxed Binding）自动匹配：kebab-case（`phone-number`）、camelCase（`phoneNumber`）、下划线（`phone_number`）都能对应上同一个字段。
- `@Component`：同样要注册成 Bean。

**对应关系**：

| yml 配置 | 绑定到字段 |
| --- | --- |
| `developer.name` | `name` |
| `developer.website` | `website` |
| `developer.qq` | `qq` |
| `developer.phone-number` | `phoneNumber`（松散绑定） |

**`@ConfigurationProperties` 适合什么场景？** 配置项成组、数量多时，用一个类统一承载，比写一堆 `@Value` 清晰得多，而且能整体传递、整体校验。这是实际开发中**更推荐**的方式。

### 4.3 两种方式对比

| 维度 | `@Value` | `@ConfigurationProperties` |
| --- | --- | --- |
| 适用场景 | 零散的单个值 | 成组的、结构化配置 |
| 写法 | 每个字段一个注解 | 类上一个注解 + prefix |
| 松散绑定 | 支持 | 支持 |
| 类型转换 | 支持（但单个字段） | 支持（可绑定 List/Map/嵌套对象） |
| 校验 | 不支持 | 配合 `@Validated` 支持 JSR-303 校验 |
| 元数据提示 | 无 | 配合配置处理器有提示 |
| 推荐度 | 简单场景用 | **生产首选** |

---

## 五、控制器：用构造器注入使用配置

`controller/PropertyController.java`：

```java
@RestController
public class PropertyController {
    private final ApplicationProperty applicationProperty;
    private final DeveloperProperty developerProperty;

    @Autowired
    public PropertyController(ApplicationProperty applicationProperty, DeveloperProperty developerProperty) {
        this.applicationProperty = applicationProperty;
        this.developerProperty = developerProperty;
    }

    @GetMapping("/property")
    public Dict index() {
        return Dict.create().set("applicationProperty", applicationProperty).set("developerProperty", developerProperty);
    }
}
```

### 5.1 构造器注入（推荐写法）

注意这里没有用 `@Autowired` 直接加在字段上，而是写了一个构造器，在构造器参数上注入。这是 Spring 官方**推荐**的注入方式。

**为什么推荐构造器注入？**

1. **不可变**：字段可以声明为 `final`，对象构造完成后就不能改，线程安全。
2. **依赖明确**：看构造器参数就知道这个类依赖什么，不会像字段注入那样藏一堆 `@Autowired`。
3. **方便测试**：写单元测试时可以直接 `new PropertyController(mockApp, mockDev)`，不依赖 Spring 容器。
4. **避免循环依赖**：构造器注入如果出现循环依赖，Spring 启动直接报错，逼你重构；字段注入会"偷偷"用三级缓存解决，掩盖设计问题。

> 💡 前端类比：这像 React 里推荐"props 传依赖"而不是组件内部自己 `import` 单例——依赖显式声明，测试和替换都方便。

**小贴士**：如果类只有一个构造器，Spring 4.3+ 可以省略 `@Autowired`，但写上更清晰。

### 5.2 返回 `Dict`（Hutool 的字典对象）

`Dict` 是 Hutool 提供的有序键值对，类似 `Map` 但链式调用更方便：

```java
Dict.create().set("applicationProperty", applicationProperty).set("developerProperty", developerProperty)
```

返回时，Spring Boot 会用 Jackson 把它序列化成 JSON。访问接口会得到：

```json
{
  "applicationProperty": { "name": "prod环境 demo-properties", "version": "prod环境 1.0.0-SNAPSHOT" },
  "developerProperty": { "name": "prod环境 xkcoding", "website": "prod环境 http://xkcoding.com", "qq": "prod环境 237497819", "phoneNumber": "prod环境 17326075631" }
}
```

> 💡 实际开发中一般不直接返回 `Dict`，而是定义专门的 DTO 类或统一响应体。这里用 `Dict` 只是为了演示简洁。

---

## 六、配置元数据：消除 IDE 红线、给配置加提示

`src/main/resources/META-INF/additional-spring-configuration-metadata.json`：

```json
{
    "properties": [
        {
            "name": "application.name",
            "description": "Default value is artifactId in pom.xml.",
            "type": "java.lang.String"
        },
        ...
        {
            "name": "developer.phone-number",
            "description": "The Developer Phone Number.",
            "type": "java.lang.String"
        }
    ]
}
```

### 6.1 它解决什么问题？

当你在 `application.yml` 里写自定义配置（如 `application.name`）时，IDEA 会报红线警告"Cannot resolve configuration property"，因为 Spring Boot 不认识这些自定义 key。这个元数据文件就是告诉 IDE："这些 key 是合法的自定义配置"，红线就消失了。

### 6.2 怎么生效？

需要引入配置处理器依赖（pom 里已有）：

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-configuration-processor</artifactId>
    <optional>true</optional>
</dependency>
```

它是一个**注解处理器**，编译时扫描你的 `@ConfigurationProperties` 类，自动生成元数据。`<optional>true</optional>` 表示这个依赖不会传递给依赖本模块的其他模块（它只在编译期用）。

有了它之后，IDEA 在 yml 里输入 `developer.` 会自动补全字段名，鼠标悬停会显示描述——配置体验大幅提升。

> 💡 前端类比：这像 TypeScript 的 `.d.ts` 声明文件 + JSON Schema，给配置提供类型提示和文档。本模块手写了 `additional-spring-configuration-metadata.json`，但更常见的做法是让处理器自动生成（写好 `@ConfigurationProperties` 类后编译即可）。

---

## 七、pom.xml 里的新依赖

相比 HelloWorld，本模块多了两个依赖：

```xml
<!-- 配置元数据处理器 -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-configuration-processor</artifactId>
    <optional>true</optional>
</dependency>

<!-- Lombok -->
<dependency>
    <groupId>org.projectlombok</groupId>
    <artifactId>lombok</artifactId>
    <optional>true</optional>
</dependency>
```

### 7.1 Lombok 简介

Java 是出了名的"样板代码"多——每个类要写 getter、setter、构造器、toString 等。Lombok 用编译期注解帮你自动生成这些方法，代码量大幅减少。

常用注解：

| 注解 | 生成内容 |
| --- | --- |
| `@Data` | getter + setter + toString + equals + hashCode + 无参构造 |
| `@Getter` / `@Setter` | 仅 getter / setter |
| `@NoArgsConstructor` | 无参构造器 |
| `@AllArgsConstructor` | 全参构造器 |
| `@Builder` | 链式构造器（`User.builder().name("x").build()`） |
| `@Slf4j` | 自动注入 `log` 对象（日志） |

> 💡 前端类比：像 TS 的装饰器或 Babel 插件，在编译期注入代码。本模块的 `ApplicationProperty` 和 `DeveloperProperty` 都用了 `@Data`，所以虽然代码里没写 getter，但 `PropertyController` 能拿到值、Jackson 能序列化，靠的就是 Lombok 生成的 getter。

> ⚠️ 用 Lombok 需要 IDE 装对应插件（IDEA 已内置），否则 IDE 会报"找不到方法"。另外 `<optional>true</optional>` 让它不传递，因为它是编译期工具，运行时不需要（生成的 class 已经包含方法）。

---

## 八、运行与验证

### 8.1 启动

```sh
mvn spring-boot:run
```

### 8.2 访问接口

```sh
curl http://localhost:8080/demo/property
```

因为 `application.yml` 里 `spring.profiles.active: prod`，返回的是 prod 环境的值：

```json
{
  "applicationProperty": {
    "name": "prod环境 demo-properties",
    "version": "prod环境 1.0.0-SNAPSHOT"
  },
  "developerProperty": {
    "name": "prod环境 xkcoding",
    "website": "prod环境 http://xkcoding.com",
    "qq": "prod环境 237497819",
    "phoneNumber": "prod环境 17326075631"
  }
}
```

### 8.3 切换环境

把 `application.yml` 的 `spring.profiles.active` 改成 `dev`，重启，返回值就变成 `dev环境 ...`。

也可以不修改文件，用命令行参数覆盖：

```sh
java -jar demo-properties.jar --spring.profiles.active=dev
```

或用环境变量（生产环境常用）：

```sh
export SPRING_PROFILES_ACTIVE=dev
java -jar demo-properties.jar
```

> 💡 这三种方式的优先级：命令行参数 / 环境变量 > 配置文件。这种"外部覆盖内部"的设计让生产部署时不用改代码、不用改配置文件，靠运行参数就能切环境。

---

## 九、动手练习

1. **加一个配置项**：在 `application-dev.yml` 里给 `developer` 加一个 `email: dev@example.com`，在 `DeveloperProperty` 类里加对应字段，重启访问，观察是否自动绑定。
2. **切换环境**：把 `spring.profiles.active` 改成 `dev`，重启，对比返回值变化。
3. **用命令行切环境**：不改配置文件，用 `--spring.profiles.active=dev` 启动，验证覆盖效果。
4. **加默认值**：给 `ApplicationProperty` 的 `@Value` 加默认值 `@Value("${application.name:unknown}")`，然后故意在 yml 里删掉 `application.name`，验证不报错且用默认值。
5. **体验松散绑定**：在 yml 里把 `phone-number` 改成 `phoneNumber` 和 `phone_number` 两种写法分别试，验证都能绑定到 `phoneNumber` 字段。
6. **写一个 `@ConfigurationProperties` 嵌套对象**：定义一个 `server` 前缀的配置类，包含嵌套的 `timeout` 对象（`connection-time`、`read-time`），在 yml 里配置，验证嵌套绑定。

---

## 十、本模块知识点总结（结合实际开发详解）

配置读取是 Spring Boot 项目的"基础设施"，几乎每个模块都会用到。下面把核心知识点放到真实开发场景里讲透。

### 10.1 `@Value` vs `@ConfigurationProperties`：怎么选？

**实际开发中的选择标准：**

- **1-2 个零散值** → 用 `@Value`，快、直接。比如读个超时时间 `@Value("${api.timeout:3000}")`。
- **成组配置（3 个以上相关字段）** → 用 `@ConfigurationProperties`。比如第三方支付配置（appId、appSecret、回调地址、网关 URL），用一个 `PayProperty` 类承载，清晰且可整体传递。

**为什么生产首选 `@ConfigurationProperties`？**

1. **可维护性**：新增配置项只需加字段，不用再写一个 `@Value`。
2. **可校验**：配合 `@Validated` 能做参数校验，配置错了启动就报错，而不是运行时才暴露。

   ```java
   @Data
   @Validated
   @ConfigurationProperties(prefix = "pay")
   public class PayProperty {
       @NotBlank
       private String appId;
       @NotBlank
       private String appSecret;
       @Min(1) @Max(10000)
       private int timeout = 3000;
   }
   ```

3. **可复用**：一个配置类可以在多处注入，类型安全。
4. **有 IDE 提示**：配合配置处理器，yml 里自动补全。

**常见坑：**

- `@Value` 忘了写 `${}`：写成 `@Value("application.name")` 会把字符串字面量 `application.name` 注入进去，而不是读配置。必须 `@Value("${application.name}")`。
- `@ConfigurationProperties` 忘了加 `@Component`：类不会被注册成 Bean，注入时报 `NoSuchBeanDefinitionException`。要么加 `@Component`，要么用 `@EnableConfigurationProperties(DeveloperProperty.class)` 在配置类上启用。
- `@ConfigurationProperties` 字段没有 setter：绑定靠 setter 注入，没有 setter（或没加 `@Data`）会导致值注入不进去，字段是 null。这是新手最常踩的坑。

### 10.2 多环境配置（Profile）：开发/测试/生产的标配

**实际开发的标准做法：**

```
src/main/resources/
├── application.yml              # 公共配置 + spring.profiles.active
├── application-dev.yml          # 开发环境：本地数据库、本地 Redis、DEBUG 日志
├── application-test.yml         # 测试环境：测试库、测试 Redis
└── application-prod.yml         # 生产环境：线上库、线上 Redis、INFO 日志、关闭调试
```

**激活 Profile 的方式（按优先级从高到低）：**

| 方式 | 示例 | 适用场景 |
| --- | --- | --- |
| 命令行参数 | `--spring.profiles.active=prod` | 临时指定、运维启动 |
| JVM 系统属性 | `-Dspring.profiles.active=prod` | 启动脚本 |
| 环境变量 | `SPRING_PROFILES_ACTIVE=prod` | Docker/K8s 部署 |
| 配置文件 | `application.yml` 里 `spring.profiles.active: prod` | 默认值 |

**生产环境的最佳实践：**

1. **配置文件里不写死 active**：`application.yml` 里可以留 `spring.profiles.active: dev` 作为开发默认，但生产部署时用环境变量覆盖，这样同一个 jar 包能跑不同环境。
2. **敏感信息用环境变量注入**：数据库密码、密钥不要写进 yml（会进 git），用 `${DB_PASSWORD}` 占位，运行时从环境变量读：

   ```yaml
   spring:
     datasource:
       password: ${DB_PASSWORD}   # 从环境变量读
   ```

3. **大型项目用配置中心**：当服务多、配置频繁变更时，yml 文件管不过来，用 Nacos/Apollo 配置中心，支持热更新、灰度发布、版本回滚。

**常见坑：**

- 以为改了 `spring.profiles.active` 就生效，忘了重启——Profile 在启动时确定，运行中改文件不生效（除非用 `spring-cloud-context` 的刷新机制）。
- dev 和 prod 的 yml 文件名写错（如 `application-prod.yml` 写成 `application-production.yml`），导致加载不到，回退到默认值。
- 主 `application.yml` 和环境 yml 有同名 key，以为主 yml 生效，实际被环境 yml 覆盖。

### 10.3 Maven 资源过滤：把 pom 属性注入配置文件

本模块用 `@artifactId@` 把 pom 的构件名注入 yml，这是 Maven 资源过滤。

**实际开发中常用来注入：**

- 项目版本号（`@version@`）——方便接口返回当前运行版本
- 构建时间戳——做版本追踪
- pom 里自定义的 `<properties>` 值

**开启方式**（本模块 pom 已写）：

```xml
<resources>
    <resource>
        <directory>src/main/resources</directory>
        <filtering>true</filtering>
    </resource>
</resources>
```

**常见坑：**

- 用 `${artifactId}` 而不是 `@artifactId@`：传统 Maven 用 `${}`，但 Spring Boot 父 POM 把占位符改成了 `@`（避免和 Spring 的 `${}` 冲突）。在 Spring Boot 项目里必须用 `@...@`。
- 开了 filtering 后，二进制资源（图片、字体）也被过滤导致损坏：需要把二进制文件排除过滤，或单独配置不过滤的 resource。

> 💡 前端类比：这像 Vite 的 `define` 或 webpack 的 `DefinePlugin`，构建时替换占位符。区别是 Maven 替换的是资源文件里的 `@xxx@`，Vite 替换的是 JS 里的 `process.env.XXX`。

### 10.4 配置元数据：提升团队协作效率

`additional-spring-configuration-metadata.json` 看起来是个小事，但在团队协作中价值很大：

- **消除红线警告**：自定义配置不再被 IDE 标红，避免新手误以为是错误而删除。
- **自动补全**：输入 `developer.` 自动提示可选字段，减少拼写错误。
- **悬停文档**：鼠标移到配置项上显示描述，相当于内嵌文档。

**实际开发的两种生成方式：**

1. **自动生成（推荐）**：引入 `spring-boot-configuration-processor`，写好 `@ConfigurationProperties` 类，编译时自动生成元数据。新增字段后重新编译即可。
2. **手写补充**：对于非 `@ConfigurationProperties` 的配置（如纯 `@Value` 读取的），手写 `additional-spring-configuration-metadata.json` 补充。本模块两种都用了。

**最佳实践**：写公共组件/SDK 给别人用时，一定要配好元数据——这是"专业"和"能用"的区别。

### 10.5 构造器注入：Spring 官方的推荐姿势

本模块的 `PropertyController` 用构造器注入，而不是字段上直接 `@Autowired`。这是 Spring 官方文档明确推荐的写法。

**三种注入方式对比：**

| 方式 | 示例 | 评价 |
| --- | --- | --- |
| 构造器注入（推荐） | 构造器参数 + `@Autowired` | 不可变、显式、易测试、防循环依赖 |
| Setter 注入 | setter 方法 + `@Autowired` | 可选依赖、可重新注入 |
| 字段注入（不推荐） | 字段 + `@Autowired` | 简单但隐藏依赖、难测试、掩盖循环依赖 |

**实际开发建议**：统一用构造器注入。如果用 Lombok，可以简化：

```java
@RestController
@RequiredArgsConstructor   // Lombok 自动生成全参构造器，省去手写
public class PropertyController {
    private final ApplicationProperty applicationProperty;   // final + 构造器注入
    private final DeveloperProperty developerProperty;
    // 不用再写构造器，Lombok 生成
}
```

`@RequiredArgsConstructor` 为所有 `final` 字段生成构造器，配合 Spring 4.3+ 的"单构造器省略 `@Autowired`"，代码极简。这是现代 Spring Boot 项目的标准写法。

### 10.6 配置读取的优先级全景（重要）

Spring Boot 启动时，配置值来自多个地方，按优先级从高到低（高覆盖低）：

1. 命令行参数（`--key=value`）
2. 环境变量（`KEY=value`，对应 `key`）
3. `application-{profile}.yml`（环境配置）
4. `application.yml`（主配置）
5. 默认值（代码里的默认值）

**实际开发应用**：生产部署时，把易变、敏感的值（密码、密钥、环境标识）用环境变量或命令行参数注入，固定不变的放 yml。这样同一个 jar 包，不改任何文件，靠运行参数就能适配不同环境——这是云原生部署的基础。

**常见坑**：以为配置文件改了就生效，结果被环境变量覆盖了。排查时用 Actuator 的 `/env` 端点（后续模块讲）能看到所有配置来源和最终生效值。

---

> 📌 **学习建议**：配置读取看似简单，但它是后续所有模块的基础——数据库连接、Redis 地址、消息队列参数全都从配置文件读。建议把 `@ConfigurationProperties` + 构造器注入 + 多环境 Profile 这套组合拳练熟，它是真实 Spring Boot 项目的标准配置管理姿势。另外养成一个习惯：**任何配置项都给默认值**（`@Value("${x:默认}")` 或字段初始化），这样配置缺失时程序能优雅降级而不是启动崩溃。
