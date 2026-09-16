# 38 - Spring Boot 打包成 War 包部署

> 对应项目模块：`demo-war`
> 前置知识：已学完 `01-SpringBoot入门_HelloWorld`，了解 Spring Boot 默认打 jar 包、内嵌 Tomcat 的运行方式
> 学习目标：理解 Spring Boot 项目如何打包成传统 war 包部署到外部 Tomcat，掌握 jar 与 war 两种部署方式的差异与选型。

---

## 一、本模块要解决什么问题？

在前面的 HelloWorld 模块里，Spring Boot 默认把项目打成一个**可执行 jar**，内嵌 Tomcat，`java -jar` 一键启动。这是 Spring Boot 推荐的现代部署方式。

但有些场景下，你不得不打成 **war 包**部署到**外部 Tomcat**：

1. **公司运维规范**：企业有统一的 Tomcat 集群，所有 Java 应用必须以 war 形式部署，不接受裸 jar。
2. **共享 Tomcat 资源**：多个应用跑在同一个 Tomcat 实例上，节省内存（虽然现代更推荐容器化隔离）。
3. **历史遗留系统**：老项目迁移到 Spring Boot，但部署流程还停留在 war + Tomcat 时代。
4. **特定平台要求**：某些云平台（如传统的 PaaS）只支持 war 包部署。

本模块就演示：如何把一个 Spring Boot 工程从 jar 改成 war，并部署到外部 Tomcat 运行。

> 💡 前端类比：jar 部署像 Vite 打包后用 `vite preview` 自带服务器跑起来（自带 HTTP 服务）；war 部署像把 `dist` 静态文件丢给 Nginx 托管（用外部 Web 服务器）。前者自包含、开箱即用；后者依赖外部容器，但能复用运维基础设施。

---

## 二、项目结构

```
demo-war/
├── pom.xml                      # 打包方式改为 war
├── README.md
└── src/
    ├── main/
    │   ├── java/com/xkcoding/war/
    │   │   └── SpringBootDemoWarApplication.java   # 启动类，继承 SpringBootServletInitializer
    │   └── resources/
    │       └── application.yml    # 配置文件
    └── test/java/com/xkcoding/war/
        └── SpringBootDemoWarApplicationTests.java  # 测试类
```

结构非常简单——和 HelloWorld 几乎一样，只有两处关键改动：pom 的打包方式、启动类的继承关系。这也是本模块的核心：**改动极小，但理解背后的 Servlet 容器启动机制很重要**。

---

## 三、逐行拆解 pom.xml

```xml
<artifactId>demo-war</artifactId>
<version>1.0.0-SNAPSHOT</version>
<!-- 若需要打成 war 包，则需要将打包方式改成 war -->
<packaging>war</packaging>
```

### 3.1 第一处改动：`<packaging>war</packaging>`

这是最关键的一行。前面所有模块都是 `<packaging>jar</packaging>`（或省略，默认就是 jar）。改成 `war` 后，Maven 会用 `maven-war-plugin` 把项目打成 war 包（本质是一个 zip，里面包含 `WEB-INF/classes`、`WEB-INF/lib`、`web.xml` 等 Servlet 规范要求的结构）。

> 💡 前端类比：jar 像打成一个自包含的 `.js` bundle，war 像打成一个符合特定目录规范（`WEB-INF/...`）的压缩包，必须放到能识别这个规范的"宿主"（Tomcat）里才能跑。

### 3.2 第二处改动：Tomcat 依赖设为 `provided`

```xml
<!-- 若需要打成 war 包，则需要将 tomcat 引入，scope 设置为 provided -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-tomcat</artifactId>
    <scope>provided</scope>
</dependency>
```

这一步非常关键，理解它要先搞清楚 `scope`（依赖范围）：

| scope | 含义 | 是否打进包 |
| --- | --- | --- |
| `compile`（默认） | 编译、测试、运行都可用 | 是 |
| `test` | 只在测试时可用 | 否 |
| `provided` | 编译、测试可用，**运行时由容器/环境提供** | **否** |
| `runtime` | 运行和测试可用，编译不需要 | 是 |

为什么 Tomcat 要设成 `provided`？

- `spring-boot-starter-web` 默认传递引入了 `spring-boot-starter-tomcat`（内嵌 Tomcat），用于本地 `java -jar` 启动。
- 但打成 war 部署到外部 Tomcat 时，**外部 Tomcat 自己就是 Servlet 容器**，如果 war 包里还带一份内嵌 Tomcat 的类，会和外部 Tomcat 冲突（类加载冲突、版本不一致）。
- 设成 `provided` 表示："编译时我需要这些类（代码里用到 Servlet API），但打包时别带进去，运行时外部 Tomcat 会提供。"

> 💡 前端类比：像 `peerDependencies`——"我需要 React，但请宿主环境提供，别重复打包一份"。外部 Tomcat 就是那个"宿主"。

### 3.3 构建插件

```xml
<build>
    <finalName>demo-war</finalName>
    <plugins>
        <plugin>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-maven-plugin</artifactId>
        </plugin>
        <plugin>
            <groupId>org.apache.maven.plugins</groupId>
            <artifactId>maven-war-plugin</artifactId>
            <version>2.6</version>
            <configuration>
                <failOnMissingWebXml>false</failOnMissingWebXml>
            </configuration>
        </plugin>
    </plugins>
</build>
```

- `spring-boot-maven-plugin`：依然保留，它的 `repackage` 目标会把 war 重新打包成"可执行 war"（war 也能 `java -jar` 启动，因为内嵌 Tomcat 类还在 `provided` 不打进 war，但插件会在 war 里加一个 `WebServletInitializer` 入口）。不过部署到外部 Tomcat 时用不到这个特性，保留它只是为了本地开发时还能 `mvn spring-boot:run`。
- `maven-war-plugin`：负责按 Servlet 规范打 war 包。`<failOnMissingWebXml>false</failOnMissingWebXml>` 表示没有 `web.xml` 也不报错——Spring Boot 用 Java 配置取代了传统 `web.xml`，所以工程里没有这个文件，必须告诉插件别报错。

> 💡 传统 Java Web 工程必须有 `src/main/webapp/WEB-INF/web.xml`，里面配置 DispatcherServlet、过滤器等。Spring Boot 用 `@SpringBootApplication` + 自动配置取代了它，所以不需要 `web.xml`。

---

## 四、逐行拆解启动类

```java
@SpringBootApplication
public class SpringBootDemoWarApplication extends SpringBootServletInitializer {

    public static void main(String[] args) {
        SpringApplication.run(SpringBootDemoWarApplication.class, args);
    }

    @Override
    protected SpringApplicationBuilder configure(SpringApplicationBuilder application) {
        return application.sources(SpringBootDemoWarApplication.class);
    }
}
```

### 4.1 第三处改动：继承 `SpringBootServletInitializer`

这是打 war 包必须做的代码改动。`SpringBootServletInitializer` 是 Spring Boot 提供的一个抽象类，实现了 Servlet 3.0 的 `WebApplicationInitializer` 接口。

**它解决什么问题？**

传统 war 包启动靠 `web.xml` 里配置的 `DispatcherServlet`。Spring Boot 没有 `web.xml`，那外部 Tomcat 怎么知道怎么启动 Spring Boot 应用？

Servlet 3.0 规范提供了一个机制：**SPI（Service Provider Interface）**。Tomcat 启动时会扫描 classpath 下所有实现了 `WebApplicationInitializer` 接口的类，调用它的 `onStartup` 方法，由它负责注册 Servlet、启动应用上下文。

`SpringBootServletInitializer` 就是这个接口的实现，它的 `onStartup` 会调用你重写的 `configure` 方法，拿到应用配置，然后启动 Spring 容器。

> 💡 前端类比：这像 Nginx 约定"启动时自动加载 `conf/nginx.conf`"，Spring Boot 约定"Tomcat 启动时自动调用 `WebApplicationInitializer`"。`configure` 方法就是告诉 Tomcat："用这个启动类来配置应用。"

### 4.2 `configure` 方法

```java
@Override
protected SpringApplicationBuilder configure(SpringApplicationBuilder application) {
    return application.sources(SpringBootDemoWarApplication.class);
}
```

- `application.sources(...)` 指定 Spring 应用的配置源（即启动类），等价于 `SpringApplication.run(SpringBootDemoWarApplication.class, args)` 里的第一个参数。
- 返回 `SpringApplicationBuilder` 是为了支持链式调用。

### 4.3 `main` 方法为什么还保留？

```java
public static void main(String[] args) {
    SpringApplication.run(SpringBootDemoWarApplication.class, args);
}
```

保留 `main` 方法是为了**本地开发时还能用 `java -jar` 或 IDE 直接运行启动类**来调试。这样同一个工程：
- 本地开发：直接运行 `main`，用内嵌 Tomcat（`provided` 在编译/测试 classpath 上，本地能跑）。
- 生产部署：打 war 丢外部 Tomcat，走 `SpringBootServletInitializer` 启动。

两种方式共用一套代码，这是 Spring Boot 兼容新旧部署方式的优雅设计。

---

## 五、配置文件与测试类

### 5.1 application.yml

```yaml
server:
  port: 8080
  servlet:
    context-path: /demo
```

- `server.port: 8080`：**注意**，部署到外部 Tomcat 时，端口由外部 Tomcat 决定（通常也是 8080），这个配置**不生效**。
- `server.servlet.context-path: /demo`：**注意**，部署到外部 Tomcat 时，context-path 由 war 包名决定（war 叫 `demo-war.war`，访问路径就是 `/demo-war/...`），这个配置**也不生效**。

> ⚠️ 这是 war 部署最容易踩的坑：你以为 yml 里配的端口和路径生效，实际被外部 Tomcat 覆盖了。jar 部署时这两项才完全由 Spring Boot 控制。

### 5.2 测试类

```java
@RunWith(SpringRunner.class)
@SpringBootTest
public class SpringBootDemoWarApplicationTests {
    @Test
    public void contextLoads() {
    }
}
```

和前面模块一样的冒烟测试，验证上下文能加载。war 模块的测试依然用内嵌 Tomcat（`provided` 在测试 classpath 上可用），所以本地测试不受影响。

---

## 六、运行与验证

### 6.1 打包

```sh
mvn clean package -DskipTests
```

打包后在 `target/` 下生成 `demo-war.war`。

### 6.2 部署到外部 Tomcat

1. 下载并解压 Tomcat（如 `apache-tomcat-9.0.x`，注意版本要和 Servlet 规范匹配：Tomcat 9 = Servlet 4.0）。
2. 把 `demo-war.war` 复制到 Tomcat 的 `webapps/` 目录。
3. 启动 Tomcat：执行 `bin/startup.sh`（Linux/Mac）或 `bin/startup.bat`（Windows）。
4. Tomcat 启动时会自动解压 `demo-war.war` 到 `webapps/demo-war/`，并加载应用。

### 6.3 访问

假设 Tomcat 端口 8080，war 包名 `demo-war`：

```
http://localhost:8080/demo-war/
```

注意路径前缀是 `/demo-war`（war 包名），**不是** yml 里配的 `/demo`。

> 💡 想让访问路径是 `/demo`，把 war 包重命名为 `demo.war` 再部署即可——context-path 由文件名决定。

### 6.4 本地开发模式

不改任何代码，直接运行启动类 `main` 方法或 `mvn spring-boot:run`，用内嵌 Tomcat 跑，此时 yml 的 `port` 和 `context-path` 生效，访问 `http://localhost:8080/demo/`。

---

## 七、动手练习

1. **对比 jar/war 产物**：先 `mvn clean package -DskipTests`，观察 `target/` 下生成的是 `.war` 而不是 `.jar`。用解压软件打开 war，对比目录结构（有 `WEB-INF/`）和 jar 的区别。
2. **部署到 Tomcat**：下载一个 Tomcat 9，把 war 丢进 `webapps/`，启动后访问，验证能跑起来。
3. **改 context-path**：把 war 重命名为 `myapp.war`，重新部署，观察访问路径变成 `/myapp/`，验证 yml 的 `context-path` 不生效。
4. **验证 provided 的作用**：解压 war 包，看 `WEB-INF/lib/` 里有没有 `tomcat-embed-*` 的 jar（应该没有，因为 `provided` 不打进包）。
5. **本地双模式**：同一个工程，先 `mvn spring-boot:run`（内嵌 Tomcat，端口 8080，路径 `/demo`），再部署 war 到外部 Tomcat（端口 8080，路径 `/demo-war`），对比两种模式的差异。
6. **去掉 configure 方法**：把 `configure` 方法注释掉，重新打 war 部署，观察外部 Tomcat 启动日志——应用不会被加载（因为没有 `WebApplicationInitializer` 告诉 Tomcat 怎么启动 Spring Boot）。

---

## 八、本模块知识点总结（结合实际开发详解）

war 部署是 Spring Boot 对传统 Java EE 部署方式的兼容。虽然现代项目越来越少用 war，但理解它背后的 Servlet 容器启动机制，对排查部署问题、理解 Spring Boot 启动原理很有价值。

### 8.1 jar 部署 vs war 部署：怎么选？

**两种方式全景对比：**

| 维度 | jar（内嵌 Tomcat） | war（外部 Tomcat） |
| --- | --- | --- |
| 打包方式 | `<packaging>jar</packaging>` | `<packaging>war</packaging>` |
| Tomcat 来源 | 内嵌，打进 jar | 外部独立安装 |
| 启动方式 | `java -jar app.jar` | 丢进 `webapps/`，启动 Tomcat |
| 端口/路径控制 | yml 的 `server.port`/`context-path` | Tomcat 的 `server.xml`/war 包名 |
| 部署环境要求 | 只需 JDK | 需 JDK + Tomcat |
| 多应用共享容器 | 不支持（一应用一进程） | 支持（多 war 一个 Tomcat） |
| 资源隔离 | 好（进程级） | 差（同 JVM，类加载器隔离） |
| 运维复杂度 | 低 | 高（要管 Tomcat 版本、配置） |
| 现代云原生适配 | 好（容器化友好） | 差（war + Tomcat 镜像较重） |

**实际开发的选择标准：**

- **新项目、云原生部署**：无脑选 jar。内嵌 Tomcat、`java -jar`、Docker 友好，是 Spring Boot 的官方推荐。
- **企业遗留环境**：运维只给 Tomcat、必须 war 部署时，才用 war。这是被动选择，不是主动追求。
- **混合部署**：本模块演示的"保留 main + 继承 Initializer"写法，让一个工程同时支持 jar 和 war 两种部署，适合过渡期。

**常见坑：**

- 以为 war 部署后 yml 的端口/路径还生效，结果访问 404。记住：war 部署时这些由外部 Tomcat 决定。
- jar 和 war 混用同一个 `spring-boot-maven-plugin`，war 也能 `java -jar` 启动（插件加了可执行入口），但这不是 war 的正常用法，别在生产这么干。

### 8.2 `<scope>provided</scope>` 的正确理解

`provided` 是 Maven 依赖范围里最容易误解的一个。它的语义是"已提供"——编译和测试时需要，但运行时由运行环境提供，不打进产物。

**实际开发中 `provided` 的典型场景：**

| 场景 | 依赖 | 为什么 provided |
| --- | --- | --- |
| war 部署 | `spring-boot-starter-tomcat` | 外部 Tomcat 提供 Servlet API |
| war 部署 | `javax.servlet-api` | 外部 Tomcat 提供 |
| Lombok | `lombok` | 编译期工具，运行时不需要 |
| 配置处理器 | `spring-boot-configuration-processor` | 编译期生成元数据，运行时不需要 |

**常见坑：**

- 把 `provided` 用在业务依赖上：比如把数据库驱动设成 `provided`，结果打 jar 部署时驱动没进去，启动报 `ClassNotFoundException`。`provided` 只用于"运行环境确实会提供"的依赖。
- war 模块忘了给 Tomcat 设 `provided`：war 里带了一份内嵌 Tomcat，和外部 Tomcat 冲突，启动时各种 `NoClassDefFoundError` 或行为异常。

> 💡 前端类比：`provided` 像 npm 的 `peerDependencies`——"我需要这个包，但请宿主项目装它，我自己不带"。Lombok 和配置处理器更像 `devDependencies`，但 Maven 没有 dev 这个 scope，用 `provided` 或 `optional` 近似表达。

### 8.3 `SpringBootServletInitializer` 与 Servlet 3.0 SPI 机制

这是 war 部署能工作的核心原理，值得深入理解。

**传统 war（Servlet 2.x）的启动流程：**
1. Tomcat 启动，读取 `web.xml`。
2. `web.xml` 里配置 `DispatcherServlet`、`ContextLoaderListener` 等。
3. Tomcat 实例化这些组件，启动 Spring 容器。

**Spring Boot war（Servlet 3.0+）的启动流程：**
1. Tomcat 启动，扫描 `WEB-INF/classes/lib` 下所有 jar 的 `META-INF/services/javax.servlet.ServletContainerInitializer` 文件（SPI 机制）。
2. 找到 `SpringServletContainerInitializer`（Spring 提供），它用 `@HandlesTypes(WebApplicationInitializer.class)` 注解找到所有 `WebApplicationInitializer` 实现。
3. 调用每个 `WebApplicationInitializer` 的 `onStartup`。
4. 你的 `SpringBootServletInitializer` 子类被调用，它的 `onStartup` 调用你重写的 `configure`，拿到启动类，创建 `SpringApplication` 并 run。

**实际开发要点：**

- **启动类必须在根包**：和 jar 模式一样，`@SpringBootApplication` 的 `@ComponentScan` 从启动类所在包开始扫描，放错位置会导致 Bean 扫不到。
- **一个应用一个 Initializer**：如果有多个 `WebApplicationInitializer` 实现，Tomcat 会都执行，可能冲突。一般只保留启动类这一个。
- **Servlet 3.0 是硬性要求**：外部 Tomcat 必须支持 Servlet 3.0+（Tomcat 7+）。用 Tomcat 6 这种老版本会启动失败。

**常见坑：**

- 外部 Tomcat 版本太老（Servlet 2.5），不支持 SPI，应用根本不启动。必须 Tomcat 7+（推荐 9+）。
- 打 war 时 `SpringBootServletInitializer` 的类没进去（比如被 `provided` 排除了），Tomcat 找不到启动入口。

### 8.4 context-path 与端口控制权的转移

这是 war 部署和 jar 部署行为差异最大的地方，新手最容易困惑。

| 配置项 | jar 部署 | war 部署 |
| --- | --- | --- |
| `server.port` | 生效，控制内嵌 Tomcat 端口 | **不生效**，端口由外部 Tomcat 的 `server.xml` 决定 |
| `server.servlet.context-path` | 生效，控制访问路径前缀 | **不生效**，路径前缀由 war 包名决定 |

**war 部署时怎么控制端口和路径？**

- **端口**：改外部 Tomcat 的 `conf/server.xml` 里的 `<Connector port="8080" />`。
- **路径**：重命名 war 包文件（`demo.war` → 访问 `/demo/`；`ROOT.war` → 访问 `/` 根路径）。

**实际开发的最佳实践：**

- 如果必须 war 部署，把 war 命名为 `ROOT.war` 部署到 `webapps/ROOT`，这样访问路径是根 `/`，和 jar 部署的默认行为更接近，前端不用改请求前缀。
- 或者在 Tomcat 的 `conf/Catalina/localhost/` 下建一个 `<path>.xml`，用 `<Context>` 标签指定 docBase，精确控制路径。

**常见坑：**

- 前端配的请求前缀是 `/demo`（按 yml 的 context-path），war 部署后实际路径是 `/demo-war`，前端全部 404。部署前必须和前端对齐路径。

### 8.5 `spring-boot-maven-plugin` 在 war 模块的作用

war 模块保留了 `spring-boot-maven-plugin`，它做了两件事：

1. **repackage**：把 war 重新打包成"可执行 war"——在标准 war 结构基础上，加一个 `org.springframework.boot.loader.WarLauncher` 入口，让 war 也能 `java -jar demo-war.war` 启动（用内嵌 Tomcat，因为 `provided` 的类在 `target` 下还在）。
2. **本地开发支持**：`mvn spring-boot:run` 依然能用内嵌 Tomcat 跑起来调试。

**实际开发要点：**

- 部署到外部 Tomcat 时，用不到"可执行 war"特性，但保留插件无害，且方便本地开发。
- 如果确定只走外部 Tomcat 部署、不需要本地 `java -jar`，可以移除这个插件，只留 `maven-war-plugin`，产物更干净。

**常见坑：**

- 以为 `java -jar demo.war` 启动的是外部 Tomcat 部署模式——不是，它用的是内嵌 Tomcat，和外部 Tomcat 部署是两套机制，端口/路径行为也不同。

### 8.6 现代部署方式演进：war 正在被淘汰

理解 war 是为了兼容遗留环境，但趋势是 jar + 容器化：

**部署方式演进时间线：**

| 阶段 | 方式 | 特点 |
| --- | --- | --- |
| 传统 Java EE | war + 外部 Tomcat | 多应用共享容器，运维重 |
| Spring Boot 早期 | jar + 内嵌 Tomcat | 自包含，但裸 jar 难管理 |
| 云原生 | jar + Docker | 容器隔离，镜像即部署单元 |
| 云原生 + 编排 | jar + Docker + K8s | 弹性伸缩、滚动发布 |

**为什么 jar + Docker 胜出？**

1. **隔离性**：每个应用一个容器，类加载、资源完全隔离，不像 war 共享 Tomcat 容易互相影响。
2. **一致性**：开发、测试、生产用同一个镜像，环境差异消灭。
3. **轻量**：jar + JRE 镜像比 Tomcat 镜像小，启动快。
4. **编排友好**：K8s 管理的是 Pod/容器，jar 容器天然契合，war + Tomcat 要额外处理。

**实际开发建议：**

- 新项目直接 jar + Docker，别碰 war。
- 老项目迁移：先用本模块的"双模式"写法（jar/war 都能跑），过渡期 war 部署到老 Tomcat，新环境用 jar + Docker，最终统一到 jar。

---

> 📌 **学习建议**：作为前端转后端的工程师，理解 war 部署的关键不是记住那几行配置改动，而是建立"应用和 Web 容器的关系"这个心智模型——jar 模式下应用自带容器（自给自足），war 模式下应用寄生在外部容器上（依赖宿主）。这和前端"自带 dev server" vs "构建产物丢给 Nginx"是同一个道理。现代后端部署的主流是 jar + 容器化，war 只是兼容遗留环境的过渡技能，了解原理即可，新项目别主动选它。
