# 03 - Spring Boot 入门与 HelloWorld 示例

> 对应项目模块：`demo-helloworld`
> 适用读者：有前端开发经验、刚接触 Spring Boot 的同学
> 学习目标：理解 Spring Boot 是什么、为什么用它，并能看懂、跑通、改写第一个 HelloWorld 工程。

---

## 一、先建立认知：Spring Boot 到底解决了什么问题？

在写代码之前，先花一点时间把"为什么"搞清楚。前端同学可以类比一下：Spring Boot 之于 Java 后端，有点像 `create-react-app` / `vite` 脚手架之于前端——它不是一门新语言，而是一套"约定优于配置"的工程化方案，让你不用从零搭脚手架就能快速跑起来一个生产级应用。

### 1.1 没有 Spring Boot 之前，Java Web 是怎么写的？

传统的 Java Web 项目（基于 Spring MVC）大概要经历这些步骤：

1. 用 Maven/Gradle 建工程，手动引入一大堆 jar 包（Spring-core、Spring-web、Spring-webmvc、Jackson、Tomcat 嵌入包……），还要小心处理版本冲突。
2. 写 `web.xml`，配置 `DispatcherServlet`（前端控制器）、各种过滤器、监听器。
3. 写 Spring 的 XML 配置文件（`applicationContext.xml`、`spring-mvc.xml`），用 `<bean>` 标签一个个声明组件。
4. 单独下载安装 Tomcat，把工程打成 war 包，丢进 Tomcat 的 `webapps` 目录启动。
5. 排查各种 ClassNotFoundException、版本不兼容……

这套流程对新手非常不友好。**Spring Boot 的核心价值就是把这些繁琐步骤全部自动化**，让你专注写业务代码。

### 1.2 Spring Boot 的四大核心特性

| 特性 | 一句话解释 | 前端类比 |
| --- | --- | --- |
| **起步依赖（Starter）** | 把某类功能需要的所有 jar 包打包成一个依赖，引入一个就等于引入一组 | 像 `@vue/app` 这种"大礼包"依赖 |
| **自动配置（Auto-Configuration）** | 根据你引入的依赖，自动往 Spring 容器里注册需要的 Bean | 像 Vite 根据你装了 React 就自动配好 JSX |
| **内嵌 Web 容器** | 默认内嵌 Tomcat，直接 `java -jar` 就能跑，不用外部容器 | 像 webpack-dev-server 内嵌一个 HTTP 服务 |
| **生产级 Actuator** | 自带健康检查、监控端点 | 像 Vue/React 的 devtools 面板 |

本模块 HelloWorld 会重点用到前三点，第四点（Actuator）会在后续模块专门讲。

---

## 二、从项目整体结构看起

### 2.1 这是一个 Maven 多模块工程

打开仓库根目录的 `pom.xml`，你会看到 `<packaging>pom</packaging>` 和一长串 `<module>`：

```xml
<groupId>com.xkcoding</groupId>
<artifactId>spring-boot-demo</artifactId>
<version>1.0.0-SNAPSHOT</version>
<packaging>pom</packaging>

<modules>
    <module>demo-helloworld</module>
    <module>demo-properties</module>
    <!-- ... 后面还有几十个 demo 模块 ... -->
</modules>
```

**关键概念：父 POM（parent pom）**

- 根目录这个 `pom.xml` 本身不产出任何代码，它只是一个"管理者"。
- `<packaging>pom</packaging>` 表示它打包类型是 `pom`，意味着它是一个**聚合工程 / 父工程**，用来统一管理子模块。
- 它在 `<properties>` 里集中声明了版本号（Spring Boot 版本、MySQL 版本、Hutool 版本等），再用 `<dependencyManagement>` 统一管控子模块用到的依赖版本，这样**所有子模块都不用写版本号**，既统一又避免冲突。

> 💡 前端类比：这有点像 monorepo 里的根 `package.json`，子包各自独立但共享根的依赖版本约定。Maven 的 `<dependencyManagement>` 类似于 pnpm 的 `pnpm-workspace` + `package.json` 里的版本锁定。

### 2.2 子模块 `demo-helloworld` 的目录结构

```
demo-helloworld/
├── pom.xml                      # 本模块自己的依赖声明
├── README.md                    # 模块说明
└── src/
    ├── main/
    │   ├── java/com/xkcoding/helloworld/
    │   │   └── SpringBootDemoHelloworldApplication.java   # 启动类（也是控制器）
    │   └── resources/
    │       └── application.yml  # 配置文件
    └── test/java/com/xkcoding/helloworld/
        └── SpringBootDemoHelloworldApplicationTests.java # 测试类
```

**Maven 约定优于配置的目录规范**（非常重要，必须记住）：

| 目录 | 作用 |
| --- | --- |
| `src/main/java` | 放业务源码（`.java`） |
| `src/main/resources` | 放配置文件、静态资源、模板等 |
| `src/test/java` | 放测试代码 |
| `src/test/resources` | 放测试用的配置文件 |

包路径 `com.xkcoding.helloworld` 是 Java 的命名空间，相当于前端的 npm scope，用于避免类名冲突。

---

## 三、逐行拆解 `pom.xml`

`demo-helloworld/pom.xml` 是本模块的核心配置，我们一段段看。

### 3.1 坐标与打包方式

```xml
<artifactId>demo-helloworld</artifactId>
<version>1.0.0-SNAPSHOT</version>
<packaging>jar</packaging>
<name>demo-helloworld</name>
<description>Demo project for Spring Boot</description>
```

- `groupId`（继承自父 POM，是 `com.xkcoding`）+ `artifactId`（`demo-helloworld`）+ `version` 三者合起来叫 **Maven 坐标**，全世界唯一标识这个构件。类比 npm 包名 `@scope/package-name@version`。
- `<packaging>jar</packaging>`：打包成可执行 jar。Spring Boot 默认推荐 jar 包（内嵌 Tomcat），而不是传统的 war 包（war 模块会在后面 `demo-war` 专门讲）。

### 3.2 继承父 POM

```xml
<parent>
    <groupId>com.xkcoding</groupId>
    <artifactId>spring-boot-demo</artifactId>
    <version>1.0.0-SNAPSHOT</version>
</parent>
```

- 本模块声明父工程是根目录的 `spring-boot-demo`。
- 继承后，本模块自动获得父 POM 里 `<properties>`、`<dependencyManagement>`、`<pluginManagement>` 中定义的内容，所以下面引依赖时**不用写版本号**。

> ⚠️ 注意：本模块的 parent 是项目根的 `spring-boot-demo`，而**不是** `spring-boot-starter-parent`。很多 Spring Boot 教程会用 `spring-boot-starter-parent` 作为父，效果类似（都通过 `spring-boot-dependencies` 管版本）。本项目选择自己当父，再通过 `dependencyManagement` 导入 `spring-boot-dependencies`（见根 POM），是另一种等价写法。

### 3.3 依赖声明

```xml
<dependencies>
    <!-- 1. Spring Boot Web 起步依赖 -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-web</artifactId>
    </dependency>

    <!-- 2. 测试起步依赖 -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-test</artifactId>
        <scope>test</scope>
    </dependency>

    <!-- 3. Hutool 工具类 -->
    <dependency>
        <groupId>cn.hutool</groupId>
        <artifactId>hutool-all</artifactId>
    </dependency>
</dependencies>
```

**重点理解 Starter（起步依赖）**：

- `spring-boot-starter-web` 这一个依赖，实际上传递引入了：Spring MVC、内嵌 Tomcat、Jackson（JSON 序列化）、Spring Boot 自动配置支持等十几个 jar。你只需要引一个，就拥有了写 Web 接口的全部能力。
- `spring-boot-starter-test` 包含 JUnit、Hamcrest、AssertJ、Mockito 等测试工具，`<scope>test</scope>` 表示只在测试时用到，不会打进最终产物。
- `hutool-all` 是一个国产 Java 工具类库，类似前端的 lodash，本模块用了它的 `StrUtil` 做字符串判空和格式化。

> 💡 为什么不写版本号？因为父 POM 的 `<dependencyManagement>` 已经锁定了版本（Spring Boot 2.1.0.RELEASE、Hutool 5.4.5）。子模块只声明"我要用这个"，版本由父统一管。这避免了多个模块版本不一致的问题。

### 3.4 构建配置

```xml
<build>
    <finalName>demo-helloworld</finalName>
    <plugins>
        <plugin>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-maven-plugin</artifactId>
        </plugin>
    </plugins>
</build>
```

- `<finalName>` 指定打出的 jar 包名字（`demo-helloworld.jar`）。
- `spring-boot-maven-plugin` 是 Spring Boot 的打包插件。它的 `repackage` 目标（在根 POM 的 `pluginManagement` 里配置过）会把普通 jar 重新打包成**可执行 jar**——把所有依赖的 class 都塞进去，并指定启动类的 `main` 方法作为入口。这样最终 `java -jar demo-helloworld.jar` 就能直接启动整个 Web 应用。

---

## 四、逐行拆解启动类

`src/main/java/com/xkcoding/helloworld/SpringBootDemoHelloworldApplication.java`：

```java
@SpringBootApplication
@RestController
public class SpringBootDemoHelloworldApplication {

    public static void main(String[] args) {
        // 启动内嵌 Tomcat、初始化 Spring 容器、加载自动配置
        SpringApplication.run(SpringBootDemoHelloworldApplication.class, args);
    }

    @GetMapping("/hello")
    public String sayHello(@RequestParam(required = false, name = "who") String who) {
        if (StrUtil.isBlank(who)) {
            who = "World";
        }
        return StrUtil.format("Hello, {}!", who);
    }
}
```

这个类同时承担了两个角色：**应用启动入口** + **Web 控制器**。我们逐个注解看。

### 4.1 `@SpringBootApplication` —— 最核心的注解

它是一个组合注解，等价于：

```java
@SpringBootConfiguration      // = @Configuration，标记这是一个配置类，会被 Spring 容器管理
@EnableAutoConfiguration      // 开启自动配置：根据 classpath 上的依赖，自动注册需要的 Bean
@ComponentScan                // 组件扫描：自动扫描该类所在包及其子包下的 @Component/@Service/@Controller 等
public class SpringBootDemoHelloworldApplication { ... }
```

**三件事一句话总结**：告诉 Spring —— "这是一个配置类"（1），"你帮我自动配置"（2），"从这个包开始扫描组件"（3）。

> 💡 前端类比：`@SpringBootApplication` 有点像 `app.vue` 或 `main.ts` 的入口标记 + 自动路由加载 + 自动插件注册的合体。

**为什么启动类要放在根包 `com.xkcoding.helloworld` 下？**
因为 `@ComponentScan` 默认从启动类所在包开始向下扫描。如果把启动类放得很深（比如 `com.xkcoding.helloworld.controller`），那同级的 `service`、`dao` 包就扫不到，Bean 就注入不进来。**约定：启动类放在根包下**，这是 Spring Boot 的最佳实践。

### 4.2 `SpringApplication.run(...)` —— 启动入口

```java
public static void main(String[] args) {
    SpringApplication.run(SpringBootDemoHelloworldApplication.class, args);
}
```

- `main` 方法是 Java 程序的标准入口（类似前端 `index.html` 里引入的入口 JS）。
- `SpringApplication.run()` 做了一长串事：创建 `SpringApplication` 实例 → 推断应用类型（Servlet / 响应式）→ 加载 `ApplicationContext`（Spring 容器）→ 读取 `META-INF/spring.factories` 执行自动配置 → 启动内嵌 Tomcat → 注册所有 Bean → 发布启动完成事件。
- 传入的第一个参数 `SpringBootDemoHelloworldApplication.class` 是配置类（也是启动类本身），第二个 `args` 是命令行参数。

### 4.3 `@RestController` —— 写 REST 接口的控制器

```java
@RestController
```

它是 `@Controller` + `@ResponseBody` 的组合：

- `@Controller`：标记这个类为 Spring MVC 的控制器，能处理 HTTP 请求。
- `@ResponseBody`：让方法的返回值**直接写进 HTTP 响应体**（而不是跳转到一个视图页面）。

> 💡 前端类比：相当于 Express/Koa 里 `app.get('/hello', (req, res) => res.send(...))` 的后端等价物。返回的字符串会被 Jackson 等机制按需转成 JSON/文本写到响应体里。

> ⚠️ 本 demo 把启动类和控制器写在同一个类里，是为了演示简洁。**真实项目**通常会把控制器拆到独立的 `controller` 包下，启动类只负责启动。

### 4.4 `@GetMapping("/hello")` —— 路由映射

```java
@GetMapping("/hello")
public String sayHello(...) { ... }
```

- `@GetMapping` 是 `@RequestMapping(method = RequestMethod.GET)` 的简写，表示这个方法处理 `GET /hello` 请求。
- 同系列还有 `@PostMapping`、`@PutMapping`、`@DeleteMapping`、`@PatchMapping`，对应 RESTful 的增删改查语义。
- 完整访问路径 = `配置的 context-path` + `@GetMapping 的路径`，本例是 `/demo` + `/hello` = `/demo/hello`（context-path 在 `application.yml` 里配，见下节）。

> 💡 前端类比：相当于 Vue Router 里的 `router.get('/hello', handler)`，但这是**服务端路由**，由浏览器发起 HTTP 请求触发。

### 4.5 `@RequestParam` —— 接收查询参数

```java
public String sayHello(@RequestParam(required = false, name = "who") String who) {
```

- `@RequestParam` 用于从 URL 查询串里取参数，比如 `/demo/hello?who=Claude`。
- `required = false`：该参数非必填（不传也不报错）。
- `name = "who"`：URL 上的参数名叫 `who`，绑定到方法变量 `who`。
- 如果不写 `name`，默认用方法变量名作为参数名。

方法体里用 Hutool 的 `StrUtil.isBlank(who)` 判空（比 JDK 的 `String.isBlank` 更宽容，能处理全空格等场景），为空就给默认值 `"World"`，再用 `StrUtil.format("Hello, {}!", who)` 做字符串模板填充（`{}` 是占位符，类似前端的模板字符串 `${}`）。

---

## 五、配置文件 `application.yml`

`src/main/resources/application.yml`：

```yaml
server:
  port: 8080
  servlet:
    context-path: /demo
```

### 5.1 为什么是 `.yml` 而不是 `.properties`？

Spring Boot 支持两种配置文件格式：`application.properties` 和 `application.yml`。本项目统一用 yml。

- `.properties` 是扁平的键值对：`server.port=8080`
- `.yml` 是层级结构，用缩进表示层级，更清晰，还能避免重复前缀：

```yaml
server:
  port: 8080          # server.port = 8080
  servlet:
    context-path: /demo   # server.servlet.context-path = /demo
```

> 💡 前端类比：yml 类似 JSON 但更简洁，没有花括号和引号，靠缩进表达嵌套。注意 yml 对缩进非常敏感，必须用空格（不能 tab）。

### 5.2 这两项配置的含义

| 配置项 | 作用 | 默认值 |
| --- | --- | --- |
| `server.port` | 内嵌 Tomcat 监听端口 | 8080 |
| `server.servlet.context-path` | 应用上下文路径，所有接口 URL 前都会带上这个前缀 | `/`（根） |

所以本应用所有接口的访问基准是 `http://localhost:8080/demo/`，HelloWorld 接口完整地址是 `http://localhost:8080/demo/hello`。

> 💡 前端类比：`context-path` 类似 Vite 配置里的 `base: '/demo/'`，所有资源/接口路径都会加上这个前缀。

---

## 六、运行项目并验证

### 6.1 启动方式

在 `demo-helloworld` 目录下执行（需要本机已装 JDK 8 和 Maven）：

```sh
mvn spring-boot:run
```

或者用 IDE（IntelliJ IDEA）直接右键运行启动类的 `main` 方法。

启动成功后控制台会看到 Spring Boot 的 banner 和类似 `Tomcat started on port(s): 8080` 的日志。

### 6.2 访问接口

| 请求 | 返回 |
| --- | --- |
| `GET http://localhost:8080/demo/hello` | `Hello, World!` |
| `GET http://localhost:8080/demo/hello?who=Claude` | `Hello, Claude!` |

可以用浏览器直接访问，也可以用 curl / Postman / Apifox 测试。

### 6.3 打包后运行

```sh
mvn clean package -DskipTests
java -jar target/demo-helloworld.jar
```

这就是 Spring Boot "打成一个可执行 jar、`java -jar` 直接跑"的便利——无需预装 Tomcat，部署环境只要 JDK 即可。

---

## 七、测试类

`src/test/java/.../SpringBootDemoHelloworldApplicationTests.java`：

```java
@RunWith(SpringRunner.class)
@SpringBootTest
public class SpringBootDemoHelloworldApplicationTests {

    @Test
    public void contextLoads() {
    }
}
```

- `@RunWith(SpringRunner.class)`：让测试跑在 Spring 的 JUnit 运行器上（JUnit 4 写法）。
- `@SpringBootTest`：启动一个完整的 Spring Boot 应用上下文用于测试，会执行和正式启动一样的自动配置。
- `contextLoads()` 是个空方法，但它的存在本身就在验证：**应用上下文能否正常加载**。如果依赖缺失、配置写错、Bean 注入失败，这个测试就会报错。这是一种"冒烟测试"。

> 💡 前端类比：类似一个 `app.test.ts` 里写 `it('should mount without crashing', () => { mount(App) })`，只验证能不能正常挂载。

---

## 八、动手练习（巩固理解）

建议你按下面的顺序自己改一改代码，观察效果，这是最快的学习方式：

1. **改端口**：把 `application.yml` 的 `server.port` 改成 `9090`，重启，访问 `http://localhost:9090/demo/hello`。
2. **去掉 context-path**：把 `context-path: /demo` 注释掉，观察访问路径变成 `http://localhost:8080/hello`。
3. **加一个新接口**：在启动类里加一个 `@GetMapping("/bye")` 方法，返回 `"Bye!"`，重启访问。
4. **把控制器拆出去**：新建 `controller.HelloController` 类，把 `sayHello` 方法搬过去，启动类只留 `@SpringBootApplication` 和 `main`。验证拆分后仍能正常访问（体会 `@ComponentScan` 的作用）。
5. **故意制造一个 404**：访问一个不存在的路径 `/demo/foo`，观察 Spring Boot 默认的 404 错误页（后续 `demo-exception-handler` 会讲如何统一处理异常）。

---

## 九、本模块知识点总结（结合实际开发详解）

本模块虽然只是个 HelloWorld，但它涵盖了 Spring Boot 工程的"骨架"——后续所有模块都是在这个骨架上加东西。下面把每个知识点放到**真实开发场景**里讲透，包括怎么用、有什么坑、最佳实践是什么。

### 9.1 Maven 多模块工程：大型项目的标配

**实际开发中怎么用？**

真实企业项目很少把所有代码塞进一个工程，通常会按职责拆成多模块，比如：

```
my-project/
├── my-project-common/        # 公共工具、常量、DTO，被其他模块依赖
├── my-project-dao/           # 数据访问层：实体、Mapper
├── my-project-service/       # 业务逻辑层
├── my-project-web/           # Web 控制器、启动类（最终可运行模块）
└── my-project-api/           # 对外暴露的接口 SDK（可选）
```

父 POM 统一管版本，子模块按需互相依赖。这样做的好处：

- **复用**：`common` 模块改一处，所有依赖它的模块都生效。
- **职责清晰**：改 DAO 层不会动到 Web 层代码，符合"高内聚低耦合"。
- **编译隔离**：可以只重新编译变更的模块，加速构建。

**常见坑：**

1. **循环依赖**：A 依赖 B，B 又依赖 A，Maven 会直接报错。解决方法是抽出公共部分到第三个模块，或者重新划分职责。
2. **版本不一致**：如果子模块自己写了版本号，会覆盖父 POM 的 `dependencyManagement`，导致多模块间依赖版本冲突。**最佳实践：子模块永远不写版本号，全交给父 POM 管。**
3. **`<packaging>pom</packaging>` 用错**：父工程和聚合工程必须是 `pom` 类型；只有真正产出代码（jar/war）的模块才用 `jar`/`war`。新手常把启动模块也写成 `pom`，导致打不出 jar 包。

> 💡 前端类比：这就像 monorepo（pnpm workspace / turborepo），`packages/shared`、`packages/web`、`packages/api` 各自独立又互相引用，根 `package.json` 统一锁版本。Maven 的 `<dependencyManagement>` ≈ pnpm 的 workspace 版本协议。

### 9.2 起步依赖（Starter）：Spring Boot 的灵魂设计

**为什么这是"灵魂"？**

传统 Spring 项目你要手动挑 jar 包、处理版本冲突、确保兼容性。Spring Boot 把"做某件事需要的所有依赖"打包成一个 Starter，引一个顶过去引十几个。比如：

| Starter | 一键引入的能力 |
| --- | --- |
| `spring-boot-starter-web` | Spring MVC + 内嵌 Tomcat + Jackson JSON |
| `spring-boot-starter-data-jpa` | Spring Data JPA + Hibernate |
| `spring-boot-starter-data-redis` | Lettuce 客户端 + Spring Data Redis |
| `spring-boot-starter-test` | JUnit + Mockito + AssertJ + Spring Test |
| `spring-boot-starter-actuator` | 生产级监控端点 |

**实际开发中的最佳实践：**

1. **只引你需要的 Starter**：不要图省事引一堆用不上的，每个 Starter 都会触发对应的自动配置，拖慢启动速度、增加内存占用。
2. **排除不需要的自动配置**：如果引了 `spring-boot-starter-web` 但不想用默认的 JSON 序列化，可以用 `@SpringBootApplication(exclude = {JacksonAutoConfiguration.class})` 精确排除。
3. **版本交给父 POM / `spring-boot-dependencies` 管**：永远不要在业务模块里手写 Spring Boot 相关依赖的版本号，否则升级时灾难。

**常见坑：**

- 引了 `spring-boot-starter-web` 后又手动引一个老版本 `tomcat-embed-core`，导致类冲突启动报错。**原则：Starter 已经给的，不要再手动加。**
- 想用某个新特性，直接升某个依赖版本，结果和 Spring Boot 管理的版本不兼容。**正确做法是升 Spring Boot 版本**，让 BOM 带动所有相关依赖一起升。

### 9.3 `@SpringBootApplication`：启动类的三个职责

这个注解是三个注解的组合，每个都对应实际开发中的一种行为：

```java
@SpringBootConfiguration   // ① 这是一个配置类（本质是 @Configuration）
@EnableAutoConfiguration   // ② 开启自动配置
@ComponentScan             // ③ 组件扫描，默认扫启动类所在包及子包
```

**① `@SpringBootConfiguration` —— 配置类**

它就是 `@Configuration` 的"Spring Boot 版"。被它标记的类里，可以用 `@Bean` 方法往容器里注册对象。实际开发中，当你需要把一个第三方库的对象注册成 Bean（比如配置一个 RestTemplate、一个线程池），就会写一个 `@Configuration` 类，在里面用 `@Bean` 声明。

**② `@EnableAutoConfiguration` —— 自动配置**

这是 Spring Boot 最"魔法"的部分。启动时它会扫描所有依赖 jar 包里的 `META-INF/spring.factories`（Spring Boot 2.x）或 `META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports`（Spring Boot 3.x），找到一堆自动配置类，根据 `@Conditional` 条件决定哪些生效。

比如你引了 `spring-boot-starter-web`，classpath 上就有 `WebMvcAutoConfiguration`，它会自动给你注册 `DispatcherServlet`、各种 `HandlerMapping`、`HandlerAdapter`——你什么都不用配，Web 层就通了。

**实际开发中怎么和自动配置打交道？**

- 大部分时候你不用管它，它默默工作。
- 想看哪些自动配置生效了：启动时加 `--debug` 参数，控制台会打印 `Positive matches`（生效的）和 `Negative matches`（未生效的）。
- 想覆盖某个自动配置：自己写一个同类型的 `@Bean`，Spring Boot 默认"用户配置优先于自动配置"（`@ConditionalOnMissingBean`）。

**③ `@ComponentScan` —— 组件扫描**

默认从启动类所在包开始，向下扫描所有 `@Component`、`@Service`、`@Repository`、`@Controller`、`@Configuration` 等注解标记的类，注册进容器。

**最经典的坑：启动类放错位置。** 比如启动类放在 `com.xkcoding.helloworld.controller` 包下，那 `com.xkcoding.helloworld.service` 包下的 `@Service` 就扫不到，启动时 `@Autowired` 注入会报 `NoSuchBeanDefinitionException`。

**最佳实践：启动类永远放在最外层根包下**，这样所有业务包都是它的子包，都能扫到。这是 Spring Boot 官方推荐的项目结构：

```
com.xkcoding.helloworld/
├── SpringBootDemoHelloworldApplication.java   ← 启动类在根包
├── controller/
├── service/
├── dao/
└── config/
```

### 9.4 `@RestController` 与路由注解：写 API 的全部套路

**`@RestController` = `@Controller` + `@ResponseBody`**

- `@Controller`：标记为控制器，能接收请求。
- `@ResponseBody`：方法返回值直接写进 HTTP 响应体（而不是跳转页面）。

**实际开发中几乎 100% 用 `@RestController`**，因为现代后端都是返回 JSON 给前端，不再做服务端页面渲染。返回对象时，Spring Boot 会自动用 Jackson 把对象序列化成 JSON：

```java
@GetMapping("/user")
public User getUser() {
    return new User("Claude", 18);   // 自动序列化成 {"name":"Claude","age":18}
}
```

**路由注解全家桶（RESTful 风格）：**

| 注解 | HTTP 方法 | 典型用途 |
| --- | --- | --- |
| `@GetMapping` | GET | 查询 |
| `@PostMapping` | POST | 新增 |
| `@PutMapping` | PUT | 全量更新 |
| `@PatchMapping` | PATCH | 局部更新 |
| `@DeleteMapping` | DELETE | 删除 |

**实际开发最佳实践：**

1. **路径用复数名词、小写、短横线分隔**：`/users`、`/user-profiles`，不要 `/getUser`、`/User`。
2. **用 `@PathVariable` 取路径参数**：`@GetMapping("/users/{id}")` 配合 `@PathVariable Long id`，这是 RESTful 的标准写法。
3. **复杂查询用 `@RequestParam`，请求体用 `@RequestBody`**：GET 查询参数用 `@RequestParam`，POST/PUT 的 JSON body 用 `@RequestBody` 绑定到对象。
4. **统一返回格式**：实际项目不会直接返回字符串，而是包一层统一响应体 `{ code, message, data }`，这会在后续 `demo-exception-handler` 模块详细讲。

**常见坑：**

- 返回值类型和 `@ResponseBody` 没配合好：如果用了 `@Controller`（不是 `@RestController`）又忘了方法上加 `@ResponseBody`，返回的字符串会被当成视图名去跳转页面，报 404。
- 参数名和 URL 参数名对不上：忘了写 `@RequestParam(name = "who")`，而方法变量名又和 URL 参数名不同，导致取不到值。

### 9.5 配置文件 `application.yml`：项目的"控制面板"

Spring Boot 的配置文件是整个应用的"控制面板"，几乎所有可调参数都在这里。配置项有上千个，但实际开发中常用的就那么几类：

```yaml
server:
  port: 8080                      # 端口
  servlet:
    context-path: /demo          # 上下文路径

spring:
  datasource:                     # 数据源
    url: jdbc:mysql://localhost:3306/db
    username: root
    password: 123456
  redis:                           # Redis
    host: localhost
    port: 6379
  profiles:                        # 多环境
    active: dev

logging:                           # 日志
  level: INFO
```

**实际开发要点：**

1. **yml vs properties 选哪个？** 团队统一即可。yml 层级清晰、适合大量配置；properties 扁平、不容易缩进出错。Spring Boot 都支持，甚至可以混用（yml 为主，properties 覆盖个别项）。
2. **敏感信息不要硬编码进 yml**：数据库密码、API Key 这类，生产环境应该用环境变量 `${DB_PASSWORD}` 或配置中心（Nacos/Apollo）注入，不要明文写死。
3. **多环境配置**：实际项目至少有 dev/test/prod 三套环境，用 `application-dev.yml`、`application-prod.yml` 分文件，再用 `spring.profiles.active=dev` 切换。这会在 `demo-properties` 模块详细讲。
4. **`context-path` 的实际意义**：它让一个端口能跑多个应用（配合反向代理），或者给前端请求统一加前缀方便网关路由。但现代微服务架构更倾向于用网关（Gateway）做前缀，`context-path` 用得越来越少。

**常见坑：**

- yml 缩进用 Tab 导致解析失败：**必须用空格**。
- yml 里冒号后必须有空格：`port: 8080` 对，`port:8080` 错。
- 同一个 key 在多个地方配置，后加载的覆盖先加载的，排查时容易懵。

### 9.6 打包与运行：Spring Boot 的部署哲学

**`spring-boot-maven-plugin` 的 `repackage` 目标**把普通 jar 重新打包成"fat jar"（胖 jar）——把所有依赖的 class 都打进同一个 jar，并指定 `main` 方法入口。这样部署时：

```sh
java -jar demo-helloworld.jar
```

一个命令启动整个 Web 应用，**部署环境只需要 JDK，不需要预装 Tomcat**。这是 Spring Boot 相对传统 Java Web 的革命性改进。

**实际开发的部署方式对比：**

| 方式 | 适用场景 | 特点 |
| --- | --- | --- |
| `java -jar` 裸跑 | 简单部署、演示 | 最简单，但不便管理进程 |
| 脚本 + nohup | 传统服务器 | 后台运行，但重启要手动 |
| systemd / supervisor | 生产服务器 | 进程守护、开机自启、自动重启 |
| Docker 容器 | 云原生、微服务 | 环境隔离、易编排（`demo-docker` 模块会讲） |
| K8s | 大规模微服务 | 容器编排、滚动发布、弹性伸缩 |

**常见坑：**

- 打包时没跳过测试，测试失败导致打不出 jar：用 `mvn clean package -DskipTests`。
- fat jar 太大：所有依赖都打进去了，几十 MB 很正常。如果在意体积，可以排查是否有无用 Starter。
- 多模块工程里，可执行模块（有启动类的）才配 `spring-boot-maven-plugin`，纯库模块不要配，否则 `repackage` 会破坏它被别人依赖时的结构。

### 9.7 测试：`@SpringBootTest` 的轻重之选

本模块的测试用了 `@SpringBootTest`，它会启动**完整的应用上下文**，跑一遍自动配置，验证容器能否正常加载。

**实际开发中，测试分两个层次：**

1. **单元测试**：不启动 Spring 容器，直接 `new` 对象测方法，用 Mockito 模拟依赖。速度快，适合测纯逻辑。
2. **集成测试**：用 `@SpringBootTest` 启动容器，测组件协作。速度慢，但能发现"Bean 注入、配置错误"这类问题。

**最佳实践：**

- 大多数测试写单元测试（快），关键链路写集成测试（稳）。
- 测试数据库用内存库（H2）或 Testcontainers，不要污染真实数据库。
- `@SpringBootTest` 默认启动整个上下文较慢，可以用 `@WebMvcTest` 只启动 Web 层、`@DataJpaTest` 只启动 JPA 层，加速测试。

**常见坑：** `@SpringBootTest` 启动慢，全用它跑 CI 会很耗时；但如果完全不写集成测试，配置错误要到运行时才暴露。平衡是关键。

---

> 📌 **学习建议**：作为前端转后端的工程师，最大的思维转变是——后端没有"组件渲染"这一层，核心是**处理 HTTP 请求 → 操作数据 → 返回响应**。Spring Boot 帮你把"接收请求、路由分发、参数解析、响应序列化"这些脏活全包了，你只需要用注解告诉它"这个方法处理哪个路径、要哪些参数"。先建立这个心智模型，后面所有模块都是在往这个骨架上挂不同的能力（数据库、缓存、消息队列、权限……）。
