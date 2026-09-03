# Tomcat 与 Web 服务器

要学 Java Web 开发，第一步不是写代码，而是搞懂两件事：**Web 请求是怎么被处理的**、**用什么软件来处理**。本篇从 B/S 架构讲起，带你理解 Web 服务器的角色，然后动手安装 Tomcat、部署第一个 Web 项目、在 IDEA 中集成开发环境。这些是后续 Servlet、Spring Boot 的运行基础——Spring Boot 的内嵌 Tomcat，本质就是这一篇讲的东西。

> 💡 本篇是整个 Java Web 系列的开篇。建议边读边动手：装好 Tomcat、跑通一次启动、用 IDEA 配置好开发环境，亲手走完一遍流程，比看十遍教程都管用。

---

## 一、Web 基础概念

### 1.1 软件架构：C/S 与 B/S

| 架构 | 全称 | 特点 | 典型应用 |
| :--- | :--- | :--- | :--- |
| **C/S** | Client/Server | 需安装客户端，性能好，开发成本高 | QQ、微信桌面版、网游 |
| **B/S** | Browser/Server | 浏览器即客户端，无需安装，易维护 | 网站、OA 系统、管理后台 |

> 💡 **Java Web 开发就是做 B/S 架构**：服务端写 Java 程序，客户端用浏览器访问。本系列以及后续 Spring Boot 都是 B/S 架构。

### 1.2 Web 服务器是什么

Web 服务器是一个**软件**（不是硬件！），它做三件事：

1. **接收**浏览器的 HTTP 请求；
2. **调用**服务端程序（Servlet / 静态资源）处理请求；
3. **返回**HTTP 响应给浏览器。

```
浏览器  ──HTTP 请求──▶  Web 服务器（Tomcat）  ──▶  调用 Servlet 处理
浏览器  ◀──HTTP 响应──  Web 服务器（Tomcat）  ◀──  返回结果
```

常见 Web 服务器对比：

| 服务器 | 语言 | 特点 |
| :--- | :--- | :--- |
| **Tomcat** | Java | 轻量级，Servlet 容器，**本系列主角** |
| Jetty | Java | 更轻量，常用于嵌入式 |
| Nginx | C | 高并发静态资源 + 反向代理，不做 Servlet |
| Apache HTTP Server | C | 老牌静态服务器 |

> 💡 **Nginx 和 Tomcat 的分工**：实际项目常把 Nginx 放前面处理静态资源（HTML/CSS/图片）和反向代理，把动态请求（Servlet）转发给后面的 Tomcat。Spring Boot 内嵌 Tomcat 后，生产环境也常再加一层 Nginx。

### 1.3 为什么是 Tomcat

Tomcat 是 Apache 软件基金会的开源 **Servlet 容器**。它实现了 Servlet/JSP 规范——也就是说，你写的 Servlet 代码，最终是交给 Tomcat 来"装"起来运行的。理解这一点很关键：

> **Servlet 是规范（接口），Tomcat 是实现（容器）。** 就像 JDBC 是接口、MySQL 驱动是实现一样。你写的 Servlet 不自己跑，而是被 Tomcat 加载、调用。

📌 **Spring Boot 对应**：Spring Boot 把 Tomcat **内嵌**进 jar 包里，启动 `main` 方法就启动了 Tomcat——无需单独安装。但原理完全一样，内嵌的也是这个 Tomcat。

---

## 二、Tomcat 安装与目录结构

### 2.1 下载与安装

1. 下载：<https://tomcat.apache.org/>（选 9.x 或 10.x 版本）
2. 安装：**解压即安装**，无需安装程序
3. JDK 要求：Tomcat 9 需 Java 8+；Tomcat 10 需 Java 11+（注意 Tomcat 10 用了 `jakarta.*` 包名，与 `javax.*` 不兼容）

> ⚠️ **Tomcat 9 vs 10 的坑**：Tomcat 10 起，Servlet API 包名从 `javax.servlet` 改为 `jakarta.servlet`。很多老教程和旧依赖仍是 `javax.servlet`，**初学者建议先用 Tomcat 9**，避免包名冲突。Spring Boot 3.x 已全面切换到 `jakarta.*`。

### 2.2 目录结构

解压后目录如下：

```
apache-tomcat-9.x/
├── bin/        启动/关闭脚本（startup.bat、shutdown.bat）
├── conf/       配置文件（server.xml、web.xml）
├── lib/        Tomcat 自身 jar 包（Servlet API 实现等）
├── logs/       运行日志
├── temp/       临时文件
├── webapps/    ★ Web 项目部署目录（把项目放这里）
└── work/       JSP 编译后的 .class（运行时生成）
```

重点记住三个目录：
- **`bin/`**：启动关闭 Tomcat 的脚本。
- **`webapps/`**：你的 Web 项目放这里，Tomcat 启动时自动加载。
- **`conf/`**：改端口、改虚拟路径都在这里。

### 2.3 启动与验证

1. 双击 `bin/startup.bat`（Windows）或 `./bin/startup.sh`（Linux/Mac）启动；
2. 浏览器访问 <http://localhost:8080/>，看到 Tomcat 欢迎页即成功；
3. 双击 `bin/shutdown.bat` 关闭，或在启动窗口按 `Ctrl+C`。

> ⚠️ **启动闪退的两大原因**：
> 1. **没配 JAVA_HOME**：Tomcat 启动需要 JDK，必须配置 `JAVA_HOME` 环境变量指向 JDK 目录。
> 2. **端口被占用**：8080 端口被其他程序占用。用 `netstat -ano | findstr 8080` 查占用，改 `conf/server.xml` 里的端口即可。

### 2.4 修改端口

编辑 `conf/server.xml`，找到 Connector 标签：

```xml
<!-- 把 8080 改成你想要的端口，如 80 -->
<Connector port="8080" protocol="HTTP/1.1"
           connectionTimeout="20000"
           redirectPort="8443" />
```

> 💡 改成 80 端口后，访问时不用加端口号（`http://localhost/`），因为 80 是 HTTP 默认端口。

📌 **Spring Boot 对应**：改端口只需 `server.port=8080` 一行配置，不用动 XML。这就是"约定优于配置"的体现。

---

## 三、Web 项目的部署方式

把一个 Web 项目交给 Tomcat 运行，有三种方式，从简单到规范：

### 3.1 方式一：直接丢 webapps（最简单）

把项目文件夹直接放到 `webapps/` 目录下：

```
webapps/
└── hello/              ← 项目名（也是访问路径）
    ├── WEB-INF/
    │   ├── web.xml     ← Web 应用配置文件
    │   ├── classes/    ← 编译后的 .class
    │   └── lib/        ← 第三方 jar 包
    └── index.html      ← 静态资源
```

启动 Tomcat 后访问 `http://localhost:8080/hello/index.html` 即可。

### 3.2 方式二：打 war 包放 webapps

把项目打成 **war 包**（Web Application Archive），丢到 `webapps/`，Tomcat 启动时**自动解压**并加载。

```bash
# Maven 项目打 war 包
mvn clean package
# 把 target/hello.war 复制到 webapps/
```

> 💡 **war 包 vs jar 包**：jar 是普通 Java 打包；war 是 Web 项目打包，含 `WEB-INF/` 结构，供 Tomcat 识别。Spring Boot 默认打 jar（内嵌 Tomcat 直接跑），也可打 war 部署到外部 Tomcat。

### 3.3 方式三：配置 server.xml（指定路径）

编辑 `conf/server.xml`，在 `<Host>` 标签内加 `<Context>`：

```xml
<Host name="localhost" appBase="webapps" ...>
  <!-- docBase 指项目真实路径，path 指访问路径 -->
  <Context docBase="D:\projects\hello" path="/myapp" />
</Host>
```

访问 `http://localhost:8080/myapp/`。这种方式可以**把项目放在任意目录**，不局限于 webapps。

### 3.4 方式四：独立 XML 文件（推荐，不污染主配置）

在 `conf/Catalina/localhost/` 下新建任意名称的 xml 文件，如 `myapp.xml`：

```xml
<Context docBase="D:\projects\hello" />
```

访问路径就是 xml 文件名：`http://localhost:8080/myapp/`。

> 💡 **IDEA 开发时用的就是这种方式**——IDEA 在 `conf/Catalina/localhost/` 下生成一个临时 xml 指向你的项目源码目录，实现"改代码即部署"。

> ⚠️ **四种方式怎么选**：
> - 学习/快速测试：方式一（丢 webapps）
> - 生产部署：方式二（war 包）
> - IDEA 开发：方式四（IDEA 自动配置，你不用手动管）
> - 方式三（改 server.xml）不推荐：每次改主配置要重启 Tomcat，易出错

---

## 四、IDEA 集成 Tomcat 开发

实际开发不会手动丢 webapps，而是在 IDEA 里配置 Tomcat，实现一键启动/热部署。

### 4.1 配置步骤

1. **IDEA 顶部 → Run → Edit Configurations**；
2. 点左上 `+` → 选 **Tomcat Server → Local**；
3. **Server 标签**：`Application server` 选你安装的 Tomcat 目录；URL 默认 `http://localhost:8080/`；
4. **Deployment 标签**：点 `+` → Artifact → 选你的 Web 项目（war exploded）；
5. Application context 可改访问路径（如 `/hello`）；
6. 点 OK，启动按钮即可一键跑项目。

### 4.2 war vs war exploded

IDEA 部署 Artifact 时有两个选项：

| 选项 | 说明 | 适用场景 |
| :--- | :--- | :--- |
| **war exploded** | 不打包，直接以文件夹形式部署，**改代码即时生效** | 开发阶段首选 |
| **war** | 打成 war 包再部署，每次改动要重新打包 | 接近生产环境 |

> 💡 **开发阶段一定选 war exploded**，配合 `Ctrl+F9`（Build）可实现类热部署，改 JSP/资源不用重启。

### 4.3 热部署配置

在 Tomcat Run Configuration 的 Server 标签里：

- `On 'Update' action`：选 **Update classes and resources**（更新类和资源）
- `On frame deactivation`（切离 IDEA 窗口时）：选 **Update classes and resources**

这样切回浏览器时，修改的静态资源/JSP 自动生效，不用重启。

> ⚠️ **热部署的局限**：改 Java 类的方法体可热更新，但**加方法、改类结构、改配置仍需重启**。真正的热部署要用 JRebel/Spring Loaded，Spring Boot 有 `spring-boot-devtools`。

---

## 五、Web 项目的标准结构

一个规范的 Java Web 项目（Servlet 规范）长这样：

```
hello-project/
├── src/main/java/          ← Java 源码（Servlet 写这里）
├── src/main/resources/     ← 配置文件（properties/xml）
├── src/main/webapp/        ← Web 根目录
│   ├── index.html          ← 静态页面
│   ├── WEB-INF/            ← ★ 核心目录，浏览器无法直接访问
│   │   ├── web.xml         ← 部署描述符（Servlet 3.0+ 可省略）
│   │   ├── classes/        ← 编译后的 .class
│   │   └── lib/            ← 第三方 jar 包
│   └── jsp/                ← JSP 页面
└── pom.xml                 ← Maven 配置（管理依赖）
```

**关键点**：

- **`webapp/` 是 Web 根目录**，里面的静态资源（html/css/js）浏览器可直接访问。
- **`WEB-INF/` 是保护区**，浏览器**无法直接访问**，里面的 class、web.xml 只能由 Tomcat 内部调用。这是安全设计——业务逻辑不暴露。
- **`web.xml` 是部署描述符**：配置 Servlet 映射、Filter、Listener 等。**Servlet 3.0+ 用注解（`@WebServlet`）后可省略**，本系列默认用注解。

> 💡 **Maven 管理依赖**：现代 Web 项目用 Maven 的 `pom.xml` 管理依赖（Servlet API、JDBC 驱动等），不再手动往 `lib/` 丢 jar 包。这也是 Spring Boot 的前置基础。

📌 **Spring Boot 对应**：Spring Boot 把 `webapp/WEB-INF/` 这套结构**彻底简化**——没有 web.xml、没有 webapp 目录，一个 `main` 方法 + `application.yml` 就跑起来了。但底层的 Servlet、Tomcat、WEB-INF 机制一个都没少，只是被自动配置封装了。

---

## ⚠️ 重点

1. **Tomcat 是软件不是硬件**：它是运行在 JVM 上的 Servlet 容器，负责加载和调用 Servlet。
2. **Servlet 是规范，Tomcat 是实现**：你写的 Servlet 不自己跑，交给 Tomcat 加载调用——这和"JDBC 接口 / MySQL 驱动实现"是一回事。
3. **`JAVA_HOME` 必须配置**：Tomcat 启动依赖 JDK，没配会闪退。
4. **端口占用用 `netstat -ano | findstr 8080` 排查**，改 `server.xml` 的 Connector port。
5. **`WEB-INF/` 浏览器不可直接访问**：这是安全设计，业务逻辑放这里。
6. **开发用 war exploded**：配合热部署，改资源即时生效，不用重启。
7. **初学者用 Tomcat 9**：Tomcat 10 的 `jakarta.*` 包名与大量旧依赖不兼容，容易踩坑。

---

## 💻 实战案例：部署第一个 Web 项目

**目标**：用 Maven 建一个最简 Web 项目，部署到 Tomcat，浏览器访问看到页面。

### 1. Maven 建项目

`pom.xml` 引入 Servlet API（注意 scope 是 provided，Tomcat 自带实现）：

```xml
<dependencies>
    <dependency>
        <groupId>javax.servlet</groupId>
        <artifactId>javax.servlet-api</artifactId>
        <version>4.0.1</version>
        <scope>provided</scope>   <!-- Tomcat 自带，不打包进去 -->
    </dependency>
</dependencies>
```

> ⚠️ **scope 必须是 provided**：Tomcat 的 `lib/` 已有 Servlet API 实现，若打包进去会冲突。这是初学者高频踩坑点。

### 2. 建静态页面

`src/main/webapp/index.html`：

```html
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>我的第一个 Web 项目</title></head>
<body>
    <h1>Hello, Tomcat!</h1>
    <p>这是部署在 Tomcat 上的第一个 Web 项目。</p>
</body>
</html>
```

### 3. IDEA 配置 Tomcat 部署

1. Run → Edit Configurations → Tomcat Server → Local；
2. Deployment → + → Artifact → 选 `hello:war exploded`；
3. Application context 改成 `/`（这样访问 `http://localhost:8080/` 直接到首页）；
4. 启动。

### 4. 访问验证

浏览器打开 <http://localhost:8080/>，看到 "Hello, Tomcat!" 即成功。

### 5. 进阶：写一个最简 Servlet

下一篇会详细讲 Servlet，这里先来个"Hello"感受一下：

```java
@WebServlet("/hello")   // 注解配置访问路径，无需 web.xml
public class HelloServlet extends HttpServlet {
    @Override
    protected void doGet(HttpServletRequest req, HttpServletResponse resp)
            throws ServletException, IOException {
        resp.setContentType("text/html;charset=utf-8");
        resp.getWriter().write("<h1>Hello, Servlet!</h1>");
    }
}
```

重启 Tomcat，访问 <http://localhost:8080/hello>，看到 "Hello, Servlet!"。这就是 Java Web 的起点——下一篇 [02-Servlet 入门](02Servlet.md) 会深入讲它的原理。

---

## 🚀 新版本补充

- **Tomcat 10+**：Servlet API 包名从 `javax.servlet` 改为 `jakarta.servlet`，对应 Jakarta EE 9+。Spring Boot 3.x 已跟进。
- **Servlet 3.0+**：支持注解配置（`@WebServlet`/`@WebFilter`），可省略 `web.xml`；支持异步 Servlet、文件上传注解。
- **Servlet 4.0**：支持 HTTP/2。
- **Spring Boot 内嵌 Tomcat**：Spring Boot 2.x 内嵌 Tomcat 9；Spring Boot 3.x 内嵌 Tomcat 10（`jakarta.*`）。

---

## 📌 在 Spring Boot 中

> 本篇讲的 Tomcat 安装、端口、部署、目录结构，在 Spring Boot 中被大幅简化。下面逐一对照，给出**实际开发中的配置和代码**，以及"出问题怎么回到原理排查"。实际开发用的是 Spring Boot，但理解了本篇原理，出问题才知道往哪查。

### 1. Tomcat：从"手动安装"到"内嵌启动"

**原生**：下载 Tomcat → 解压 → 配 `JAVA_HOME` → IDEA 集成。
**Spring Boot**：引入一个依赖，Tomcat 内嵌进 jar，`main` 方法启动即启动 Tomcat。

```xml
<!-- 引入这个 starter，Tomcat + Spring MVC 全自动配好 -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-web</artifactId>
</dependency>
```

```java
@SpringBootApplication
public class App {
    public static void main(String[] args) {
        SpringApplication.run(App.class, args);  // 这一行就启动了内嵌 Tomcat
    }
}
```

启动日志会看到：`Tomcat started on port(s): 8080 (http)`——说明内嵌 Tomcat 已起来。

> 💡 **原理对应**：Spring Boot 启动时，`ServletWebServerFactory` 发现 classpath 有 Tomcat 依赖，就自动创建 Tomcat 实例、注册 `DispatcherServlet`、绑定端口。你不用装 Tomcat，但跑的还是这个 Tomcat——`spring-boot-starter-web` 默认内嵌 `tomcat-embed-core`。

> 💡 **换容器**：想换 Jetty/Undertow？排除 Tomcat 依赖，引入对应 starter 即可。这正体现了"面向接口"——Servlet 容器是可替换的实现，和本篇讲的"Servlet 是规范、Tomcat 是实现"一脉相承。

### 2. 端口：从"改 server.xml"到"一行配置"

**原生**：编辑 `conf/server.xml` 的 `<Connector port="8080">`，重启 Tomcat。
**Spring Boot**：`application.yml`：

```yaml
server:
  port: 8080                    # 改端口（对应 Connector port）
  servlet:
    context-path: /api          # 改项目路径（对应 webapps 下的项目名）
  tomcat:
    uri-encoding: UTF-8         # 对应 server.xml 的 URIEncoding
    max-threads: 200            # Tomcat 最大工作线程数
    accesslog:
      enabled: true             # 开启访问日志（对应 Tomcat logs/）
```

> 💡 **原理排查**：端口被占用？原生看 `server.xml`，Spring Boot 看启动日志 `Tomcat started on port(s): 8080`。改 `server.port`，或用 `netstat -ano | findstr 8080` 杀占用进程——排查思路和原生完全一样，因为底层是同一个 Tomcat。

### 3. 部署：从"war 丢 webapps"到"jar 直接跑"

**原生**：打 war 包丢 `webapps/`，Tomcat 启动时自动解压加载。
**Spring Boot**：默认打 jar，`java -jar app.jar` 直接启动内嵌 Tomcat。

```xml
<!-- 默认 jar 打包：内嵌 Tomcat，独立运行 -->
<packaging>jar</packaging>

<!-- 也可打 war 部署到外部 Tomcat -->
<packaging>war</packaging>
```

```java
// 打 war 时需要这个类，让外部 Tomcat 知道怎么启动 Spring Boot
public class WarStarter extends SpringBootServletInitializer {
    @Override
    protected SpringApplicationBuilder configure(SpringApplicationBuilder builder) {
        return builder.sources(App.class);
    }
}
```

> 💡 **何时打 war**：公司有统一的外部 Tomcat 集群要求时打 war；否则一律 jar，运维更简单（一个 jar 包含 Tomcat，`java -jar` 就跑）。

### 4. 目录结构：从"webapp/WEB-INF"到"约定目录"

**原生**：手动建 `webapp/`、`WEB-INF/`、`web.xml`、`classes/`、`lib/`。
**Spring Boot**：约定优于配置，固定目录：

```
src/main/
├── java/              ← Java 代码（Servlet/Controller）
└── resources/
    ├── static/        ← 静态资源（对应 webapp 根的 html/css/js，浏览器可直接访问）
    ├── templates/     ← 模板（对应 WEB-INF 里的 JSP，受保护，框架渲染后返回）
    ├── public/        ← 静态资源（优先级低于 static）
    └── application.yml  ← 配置（对应 web.xml + server.xml 的合体）
```

> 💡 **原理对应**：`static/` 的资源浏览器可直接访问（等同 webapp 根目录）；`templates/` 的模板由框架渲染后返回（等同 `WEB-INF/` 的保护机制，浏览器不能直接访问）。**你本篇学的 `WEB-INF` 保护原理，在 Spring Boot 里变成了 `templates/` 的保护机制**。

> 💡 **原理排查**：静态资源访问 404？检查文件是否在 `static/`（或 `public/`）下、文件名是否对。模板访问 404？检查是否在 `templates/` 下、是否用了模板引擎（Thymeleaf 等）。排查逻辑和原生"资源放对目录"一样。

### 5. web.xml：从"XML 配置"到"注解 + 自动配置"

**原生**：`web.xml` 配置 Servlet 映射、Filter、Listener、全局参数。
**Spring Boot**：完全抛弃 web.xml。

| 原生 web.xml 配置 | Spring Boot 方式 |
| :--- | :--- |
| `<servlet>` + `<servlet-mapping>` | `@RestController` + `@GetMapping` |
| `<filter>` + `<filter-mapping>` | `FilterRegistrationBean` 注册 / `@WebFilter` |
| `<listener>` | `@EventListener` / `CommandLineRunner` |
| `<context-param>` 全局参数 | `application.yml` + `@Value` |

### 6. 热部署：从"war exploded"到"devtools"

**原生**：IDEA 配 war exploded + `On update action: Update classes and resources`。
**Spring Boot**：

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-devtools</artifactId>
    <scope>runtime</scope>
</dependency>
```

改代码 → 保存 → devtools 触发**类加载器重启**（比 Tomcat 全重启快，只重载应用类）。

> 💡 **原理对应**：原生热部署是"war exploded 不重新打包，Tomcat 重新加载 class"；devtools 是"用单独的类加载器重载应用类，保留容器"。原理都是"只重载变化的类，不重启容器"。

---

> 一句话：**Spring Boot 把"装 Tomcat、配端口、建目录、写 web.xml"压缩成一行配置 + 一个 main 方法。** 但底层跑的还是这个 Tomcat、这些 Servlet——理解了本篇，Spring Boot 的"魔法"就不再神秘。**出了端口占用、路径不对、静态资源访问不了的问题，你仍要回到 Tomcat 原理排查**：端口看 Connector、路径看 context-path、资源访问看 `static/` 目录约定。

## 本章小结

本篇建立了 Java Web 开发的环境认知：B/S 架构下，浏览器发 HTTP 请求，Tomcat 作为 Servlet 容器接收并调用 Servlet 处理。重点掌握 Tomcat 的安装启动、目录结构（尤其 `webapps/` 和 `conf/`）、四种部署方式、IDEA 集成配置，以及 Web 项目的标准结构（`WEB-INF/` 的保护机制）。下一篇 [02-Servlet 入门](02Servlet.md) 将进入 Servlet 的核心原理——它是整个 Java Web 的基石，也是 Spring MVC 的底层。
