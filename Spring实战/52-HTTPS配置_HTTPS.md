# 52 - Spring Boot 集成 HTTPS

> 对应项目模块：`demo-https`
> 前置知识：已学完前 51 个模块，了解启动类、`application.yml`、内嵌 Tomcat、`@Configuration` 配置类的基本用法
> 学习目标：理解 HTTPS / SSL / TLS 的基本原理，掌握在 Spring Boot 中启用 HTTPS 的完整流程，能实现 HTTP 自动跳转 HTTPS，并知道生产环境证书管理的正确姿势。

---

## 一、本模块要解决什么问题？

到目前为止，我们所有的接口都是走 HTTP（明文传输）。但在真实生产环境，尤其是涉及登录、支付、个人信息的场景，**必须用 HTTPS**——否则密码、token 在传输途中被抓包就是明文，等于裸奔。

本模块演示：如何让 Spring Boot 内嵌的 Tomcat 监听 HTTPS（443 端口），并实现"用户访问 HTTP 80 端口时自动跳转到 HTTPS 443"。

### 1.1 HTTP vs HTTPS 到底差在哪？

| 维度 | HTTP | HTTPS |
| --- | --- | --- |
| 传输方式 | 明文 | 加密（SSL/TLS） |
| 默认端口 | 80 | 443 |
| 证书 | 无 | 需要 SSL 证书 |
| 安全性 | 可被中间人窃听/篡改 | 加密 + 身份认证 + 防篡改 |
| 浏览器标识 | `不安全` | 🔒 锁形图标 |
| 性能 | 略快 | 握手有开销，但现代可忽略 |

> 💡 前端类比：HTTP 就像明信片，内容裸露在邮递途中；HTTPS 就像密封信封 + 防伪邮戳，既加密又证明发件人身份。前端同学部署 Vite/Vue 项目到 Vercel/Nginx 时，HTTPS 证书通常是平台自动配的；但后端 Spring Boot 自己当服务时，需要自己配证书。

### 1.2 SSL / TLS / 证书是什么关系？

- **SSL（Secure Sockets Layer）**：早期的安全协议，已废弃。
- **TLS（Transport Layer Security）**：SSL 的继任者，现在说的 HTTPS 实际用的是 TLS（TLS 1.2 / 1.3）。
- **证书（Certificate）**：由 CA（证书颁发机构）签名的数字文件，里面包含公钥和持有者身份。浏览器信任 CA，所以信任你用该证书搭建的 HTTPS 服务。

本模块用的是**自签名证书**（自己当 CA），浏览器会提示"不安全"，但功能完全正常。生产环境要用权威 CA（Let's Encrypt 免费申请，或阿里云/腾讯云付费）签发的证书。

---

## 二、项目结构

```
demo-https/
├── pom.xml
├── README.md
├── ssl.png                              # keytool 命令截图
└── src/main/
    ├── java/com/xkcoding/https/
    │   ├── SpringBootDemoHttpsApplication.java   # 启动类
    │   └── config/
    │       └── HttpsConfig.java          # HTTPS 配置类（HTTP→HTTPS 跳转）
    └── resources/
        ├── application.yml               # SSL 证书配置
        ├── server.keystore               # 证书文件（JKS 格式）
        └── static/
            └── index.html                # 测试页面
```

注意几个关键文件：

- `server.keystore`：这是用 JDK 自带的 `keytool` 工具生成的证书库文件，放在 `resources` 下随项目一起打包。
- `HttpsConfig.java`：配置 HTTP 80 端口的 Connector，并设置安全约束实现强制跳转。
- `application.yml`：声明 SSL 证书的位置、密码、类型。

---

## 三、第一步：用 keytool 生成证书

在配置 HTTPS 之前，必须先有证书。JDK 自带 `keytool` 工具，可以生成自签名证书。

### 3.1 生成命令

```bash
keytool -genkeypair -alias tomcat -keyalg RSA -keystore server.keystore -validity 36500
```

参数解释：

| 参数 | 含义 |
| --- | --- |
| `-genkeypair` | 生成密钥对（公钥 + 私钥） |
| `-alias tomcat` | 别名，叫 `tomcat`，后续 yml 里要对应 |
| `-keyalg RSA` | 密钥算法，用 RSA |
| `-keystore server.keystore` | 输出的证书库文件名 |
| `-validity 36500` | 有效期 36500 天（约 100 年，演示用，生产别这么长） |

执行后会交互式问你几个问题（姓名、组织、城市等），最重要的是**口令（password）**，本模块用的是 `123456`，生成后把 `server.keystore` 拷到 `src/main/resources/` 下。

### 3.2 keystore 是什么？

`keystore`（密钥库）是一个存储密钥和证书的容器文件，常见格式：

| 格式 | 说明 | 本模块用 |
| --- | --- | --- |
| **JKS**（Java KeyStore） | Java 专属格式，JDK 8 默认 | ✅ |
| **PKCS12** | 国际通用标准，JDK 9+ 默认 | ❌ |

> 💡 前端类比：keystore 有点像前端的 `.env` 证书文件或 webpack 的 `devServer.https.key`，都是存放私钥的容器。区别是 Java 用 JKS/PKCS12 二进制格式，前端常用 PEM 文本格式。

> ⚠️ JDK 8 之后，keytool 默认生成 PKCS12 而非 JKS。本模块显式指定了 `key-store-type: JKS`，如果用新版 JDK 生成时没指定格式，要相应改 yml 的 `key-store-type` 为 `PKCS12`。

---

## 四、逐行拆解 application.yml

```yaml
server:
  ssl:
    key-store: classpath:server.keystore   # 证书路径（classpath 表示从类路径找）
    key-alias: tomcat                       # 证书别名，必须和 keytool 生成时一致
    enabled: true                           # 启用 SSL
    key-store-type: JKS                     # 证书库类型
    key-store-password: 123456              # 证书库密码（keytool 时设的）
  port: 443                                 # 监听 443（HTTPS 默认端口）
```

### 4.1 `server.ssl` 配置项详解

| 配置项 | 作用 | 本模块值 |
| --- | --- | --- |
| `key-store` | 证书库位置，`classpath:` 表示从打包后的 classpath 读 | `classpath:server.keystore` |
| `key-alias` | 证书在 keystore 中的别名 | `tomcat` |
| `enabled` | 是否启用 SSL | `true` |
| `key-store-type` | 证书库格式 | `JKS` |
| `key-store-password` | 证书库密码 | `123456` |

### 4.2 为什么是 443 端口？

443 是 HTTPS 的标准端口（就像 80 是 HTTP 的标准端口）。用 443 后，浏览器访问 `https://localhost` 不用写端口号（默认就是 443）。如果用 8443，则要写 `https://localhost:8443`。

> ⚠️ 用 443 端口在 Windows/Linux 上可能需要管理员权限（小于 1024 的端口是特权端口）。如果启动报权限错误，改成 8443 即可。

### 4.3 关键点：配了 ssl 后，HTTP 就没了

只配 `server.ssl` 后，内嵌 Tomcat **只监听 443（HTTPS）**，原来的 80（HTTP）不再监听。用户如果直接访问 `http://localhost`，会连接被拒绝。这就是为什么还需要 `HttpsConfig`——额外开一个 80 端口的 HTTP Connector，专门用来重定向到 HTTPS。

---

## 五、逐行拆解 HttpsConfig.java（核心）

`config/HttpsConfig.java` 是本模块的灵魂，它做了两件事：开一个 HTTP 80 端口 + 把所有 HTTP 请求重定向到 HTTPS。

```java
@Configuration
public class HttpsConfig {

    /**
     * 配置 http(80) -> 强制跳转到 https(443)
     */
    @Bean
    public Connector connector() {
        Connector connector = new Connector("org.apache.coyote.http11.Http11NioProtocol");
        connector.setScheme("http");
        connector.setPort(80);
        connector.setSecure(false);
        connector.setRedirectPort(443);
        return connector;
    }

    @Bean
    public TomcatServletWebServerFactory tomcatServletWebServerFactory(Connector connector) {
        TomcatServletWebServerFactory tomcat = new TomcatServletWebServerFactory() {
            @Override
            protected void postProcessContext(Context context) {
                SecurityConstraint securityConstraint = new SecurityConstraint();
                securityConstraint.setUserConstraint("CONFIDENTIAL");
                SecurityCollection collection = new SecurityCollection();
                collection.addPattern("/*");
                securityConstraint.addCollection(collection);
                context.addConstraint(securityConstraint);
            }
        };
        tomcat.addAdditionalTomcatConnectors(connector);
        return tomcat;
    }
}
```

### 5.1 `connector()` —— 创建 HTTP 80 端口的连接器

```java
Connector connector = new Connector("org.apache.coyote.http11.Http11NioProtocol");
connector.setScheme("http");      // 协议方案是 http
connector.setPort(80);            // 监听 80 端口
connector.setSecure(false);      // 不是安全连接
connector.setRedirectPort(443);  // 重定向到 443（HTTPS）
```

- `Connector` 是 Tomcat 的连接器，负责接收某个端口的请求。一个 Tomcat 可以有多个 Connector（一个监听 80，一个监听 443）。
- `"org.apache.coyote.http11.Http11NioProtocol"` 是 Tomcat 基于 NIO 的 HTTP 协议处理器（NIO = 非阻塞 IO，性能比传统 BIO 好）。
- `setRedirectPort(443)`：当某个请求需要安全传输时（由 SecurityConstraint 判定），Tomcat 会把它重定向到 443 端口。

> 💡 前端类比：这就像 Nginx 配置里开一个 80 端口的 server，里面写 `return 301 https://$host$request_uri`，专门把 HTTP 流量导向 HTTPS。Spring Boot 这里是用 Tomcat 的 Connector 实现同样的事。

### 5.2 `tomcatServletWebServerFactory()` —— 定制内嵌 Tomcat

```java
TomcatServletWebServerFactory tomcat = new TomcatServletWebServerFactory() {
    @Override
    protected void postProcessContext(Context context) {
        SecurityConstraint securityConstraint = new SecurityConstraint();
        securityConstraint.setUserConstraint("CONFIDENTIAL");
        SecurityCollection collection = new SecurityCollection();
        collection.addPattern("/*");
        securityConstraint.addCollection(collection);
        context.addConstraint(securityConstraint);
    }
};
tomcat.addAdditionalTomcatConnectors(connector);
```

逐行看：

- `TomcatServletWebServerFactory`：Spring Boot 用来创建内嵌 Tomcat 的工厂类。通过自定义它，可以往 Tomcat 里塞额外的 Connector 和配置。
- `postProcessContext`：重写这个方法，在 Tomcat 的 Context（一个 Web 应用上下文）创建后做额外处理。
- `SecurityConstraint` + `SecurityCollection`：这是 Servlet 规范的安全约束。`setUserConstraint("CONFIDENTIAL")` 表示这些请求必须走加密通道；`addPattern("/*")` 表示匹配所有路径。
- `addAdditionalTomcatConnectors(connector)`：把前面创建的 80 端口 Connector 加到 Tomcat 上。

**整体效果**：Tomcat 同时监听 80 和 443。任何访问 80 的请求，因为匹配 `/*` 且要求 `CONFIDENTIAL`（机密），Tomcat 自动返回 302 重定向到 443 端口的 HTTPS。

> 💡 `CONFIDENTIAL` 是 Servlet 规范定义的传输保证级别之一，另外两个是 `NONE` 和 `INTEGRAL`。`CONFIDENTIAL` = 数据要加密传输，这正是触发 HTTP→HTTPS 跳转的开关。

---

## 六、启动类与测试页面

### 6.1 启动类

```java
@SpringBootApplication
public class SpringBootDemoHttpsApplication {
    public static void main(String[] args) {
        SpringApplication.run(SpringBootDemoHttpsApplication.class, args);
    }
}
```

启动类没有任何特殊注解，HTTPS 的开启完全靠 `application.yml` 的 `server.ssl` 配置 + `HttpsConfig` 的 Connector，不需要在启动类做什么。

### 6.2 测试页面

`static/index.html`：

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>spring boot demo https</title>
</head>
<body>
<h2>spring boot demo https</h2>
</body>
</html>
```

Spring Boot 默认会把 `static/` 下的静态资源映射到根路径，所以访问 `https://localhost/` 会显示这个页面。

---

## 七、pom.xml

```xml
<dependencies>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-web</artifactId>
    </dependency>
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-test</artifactId>
        <scope>test</scope>
    </dependency>
</dependencies>
```

注意：**没有任何额外的 SSL/HTTPS 依赖**。HTTPS 能力是内嵌 Tomcat 自带的，`spring-boot-starter-web` 已经包含。证书管理用的 `keytool` 是 JDK 工具，也不需要依赖。

---

## 八、运行与验证

### 8.1 启动

```sh
mvn spring-boot:run
```

启动后控制台会看到 Tomcat 同时监听 80 和 443。

### 8.2 验证 HTTPS

1. 浏览器访问 `https://localhost`（注意是 https）。
2. 浏览器会警告"证书不受信任"（因为是自签名），点"高级 → 继续访问"。
3. 看到 `spring boot demo https` 页面，说明 HTTPS 生效。

### 8.3 验证 HTTP 跳转

1. 浏览器访问 `http://localhost`（注意是 http）。
2. 浏览器会自动跳转到 `https://localhost`。
3. 这就是 `HttpsConfig` 的 SecurityConstraint + redirectPort 起作用。

### 8.4 用 curl 验证跳转

```sh
curl -v http://localhost
```

会看到 `302 Found` 响应，`Location` 头指向 `https://localhost`。

---

## 九、动手练习

1. **改端口**：把 443 改成 8443，80 改成 8080，重启，验证 `http://localhost:8080` 跳转到 `https://localhost:8443`。
2. **看证书**：浏览器访问 https 后，点地址栏 🔒 图标 → 查看证书，观察颁发者（是你自己）、有效期、算法。
3. **重新生成证书**：用 keytool 重新生成一个别名不同的证书，改 yml 对应配置，验证能正常访问。
4. **PKCS12 格式**：用 `keytool -genkeypair -alias tomcat -keyalg RSA -keystore server.p12 -storetype PKCS12` 生成 PKCS12 证书，改 yml 的 `key-store` 和 `key-store-type`，验证可用。
5. **去掉跳转**：注释掉 `HttpsConfig` 里的 SecurityConstraint 部分，重启，访问 80 端口，观察不再自动跳转（而是 404 或拒绝，因为 80 没有路由）。
6. **只开 HTTPS 不开 HTTP**：删掉 `connector()` Bean 和 `addAdditionalTomcatConnectors`，重启，验证只有 443 能访问，80 直接连不上。

---

## 十、本模块知识点总结（结合实际开发详解）

HTTPS 配置看似简单（一个 yml + 一个配置类），但背后涉及证书、TLS、Tomcat 连接器、Servlet 安全约束等多个知识点。下面放到真实开发场景里讲透。

### 10.1 证书管理：自签名 vs CA 签发 vs 免费证书

**实际开发中证书的三种来源：**

| 来源 | 适用场景 | 特点 |
| --- | --- | --- |
| 自签名（keytool） | 开发测试、内网服务 | 免费，但浏览器报警告，客户端无法自动信任 |
| 权威 CA 付费（阿里云/DigiCert） | 生产环境、企业级 | 浏览器信任，但要花钱，审批需域名验证 |
| Let's Encrypt 免费 | 生产环境、个人项目 | 免费、自动续期、浏览器信任，但有效期只有 90 天 |

**最佳实践：**

1. **开发用自签名，生产用 CA 签发**：本模块的自签名证书只适合演示。生产环境如果用自签名，用户看到"不安全"警告会直接关掉。
2. **证书不要进代码库**：本模块把 `server.keystore` 放在 `resources` 随项目打包，是为了演示方便。**生产环境证书属于敏感信息，不应该提交到 git**，应该用环境变量指定路径或用配置中心管理。
3. **生产用 Let's Encrypt + 自动续期**：用 `certbot` 工具申请，配合定时任务自动续期，零成本实现可信 HTTPS。
4. **大型项目用反向代理终结 SSL**：很多公司不在 Spring Boot 里配 HTTPS，而是在最前面的 Nginx/网关层配证书，Spring Boot 只跑 HTTP。这样证书集中管理、应用无感知、性能更好（Nginx 硬件加速 SSL）。

**常见坑：**

- 证书过期了忘了续，某天突然所有用户访问报错。Let's Encrypt 90 天有效期，务必配自动续期。
- 自签名证书在 Java 客户端调用时会报 `SSLHandshakeException`，需要把证书导入客户端的信任库（truststore），或者代码里关闭证书校验（不推荐）。
- 域名变了证书没更新，浏览器报"证书域名不匹配"。

### 10.2 HTTP→HTTPS 跳转的几种实现方式

本模块用 Tomcat 的 SecurityConstraint + redirectPort 实现跳转，但这不是唯一方式。

**实际开发中的三种跳转方案：**

| 方案 | 实现位置 | 优点 | 缺点 |
| --- | --- | --- | --- |
| Tomcat SecurityConstraint（本模块） | Spring Boot 内嵌 Tomcat | 应用内闭环，不依赖外部 | 只对内嵌 Tomcat 有效 |
| Nginx 301 重定向 | 反向代理层 | 性能好、集中管理、与应用解耦 | 需要额外 Nginx |
| Spring Security 强制 HTTPS | 框架层 | 跨容器通用（Jetty/Undertow 也行） | 需要 Spring Security 依赖 |

**最佳实践：**

1. **有反向代理就用 Nginx 跳转**：生产架构通常前面有 Nginx/网关，在那一层做 `return 301 https://$host$request_uri` 最干净，Spring Boot 完全不用管 HTTPS。
2. **没反向代理就用本模块的方式**：单体应用直接暴露给用户时，本模块的 SecurityConstraint 方式是 Spring Boot 生态下的标准做法。
3. **用 Spring Security 的话**：一个 `.requiresChannel().anyRequest().requiresSecure()` 就能强制 HTTPS，但前提是你已经用了 Spring Security（见第 27 模块）。

**常见坑：**

- 本模块的 `Connector` 写死了 80 端口，如果 80 被占用或无权限，启动失败。生产环境建议用 8080 等非特权端口，前面用 Nginx 转发。
- 配了跳转但 `redirectPort` 写错（比如写成 8443 但实际 HTTPS 在 443），导致跳转到错误端口。
- 反向代理场景下，Spring Boot 拿到的 scheme 是 http（因为 Nginx 转发的是 http），可能导致无限重定向循环。需要配 `server.forward-headers-strategy: native` 让 Spring Boot 信任 Nginx 传来的 `X-Forwarded-*` 头。

### 10.3 Tomcat 多 Connector 机制

本模块的核心是给内嵌 Tomcat 加了第二个 Connector。理解这个机制很重要。

**什么是 Connector？**

Tomcat 的架构里，`Connector` 负责接收网络请求，`Container`（Engine/Host/Context）负责处理请求。一个 Tomcat 可以有多个 Connector，它们共享同一套 Container（业务处理逻辑）。

**实际开发中的多 Connector 场景：**

1. **HTTP + HTTPS 双端口**（本模块）：80 跳 443。
2. **HTTP/2**：开一个 h2 协议的 Connector，提升性能。
3. **AJP**：Tomcat 和 Apache HTTP Server 之间用 AJP 协议通信（生产老架构常见）。
4. **管理端口**：开一个只在内网监听的 Connector 用于管理接口。

**最佳实践：**

- 用 `WebServerFactoryCustomizer` 接口定制 Tomcat 是更 Spring 风格的写法，比直接 `new TomcatServletWebServerFactory(){...}` 更解耦。
- 多 Connector 时注意端口冲突，启动日志会明确报 `Port xxx was already in use`。

### 10.4 SSL/TLS 协议与密码套件

本模块只配了证书，没配协议版本和密码套件。但生产环境这些很关键。

**实际开发要点：**

1. **禁用老协议**：SSL 3.0、TLS 1.0/1.1 已不安全，生产只开 TLS 1.2 和 1.3：

   ```yaml
   server:
     ssl:
       enabled-protocols: [TLSv1.2, TLSv1.3]
   ```

2. **指定密码套件**：优先用前向保密的套件，避免用 RC4、3DES 等弱算法：

   ```yaml
   server:
     ssl:
       ciphers: HIGH:!aNULL:!eNULL:!EXPORT:!MD5:!RC4
   ```

3. **用 HTTPS 还要加 HSTS**：光加密不够，还要告诉浏览器"以后这个域名一律走 HTTPS"，防止降级攻击。通过响应头 `Strict-Transport-Security` 实现，Spring Security 一行配置即可。

**常见坑：**

- 配了证书但协议版本没限制，扫描工具报 TLS 1.0 漏洞。
- 用了弱密码套件，被安全扫描标红。
- HSTS 没配，用户第一次访问 HTTP 时仍可能被中间人劫持（首次访问的明文请求是 HTTPS 的盲区）。

### 10.5 双向认证（mTLS）

本模块是单向认证——客户端验证服务端身份（证书）。更高安全级别场景（如银行内部系统、微服务间调用）会用双向认证：服务端也要验证客户端证书。

**实际开发场景：**

- 银行/支付系统：客户端必须装数字证书才能访问。
- 微服务网格：服务间用 mTLS 互信（Istio 自动做）。
- IoT 设备认证：设备证书连服务器。

**配置方式（在单向认证基础上加）：**

```yaml
server:
  ssl:
    client-auth: need           # 强制客户端提供证书
    trust-store: classpath:client-truststore.jks   # 信任的客户端证书库
    trust-store-password: 123456
```

> 💡 前端类比：单向认证就像你登录网站验证它的证书；双向认证就像进公司要刷工牌，公司也要验证你的工牌——双方都要证明身份。

### 10.6 生产环境 HTTPS 的完整姿势

把前面所有知识点串起来，生产环境配 HTTPS 的标准流程：

1. **申请证书**：用 Let's Encrypt（免费）或权威 CA（付费），绑定真实域名。
2. **证书格式转换**：CA 通常给 PEM 格式，Spring Boot 要 JKS/PKCS12，用 `openssl` + `keytool` 转换。
3. **配置 yml**：指定证书路径、密码、协议版本（TLS 1.2+）、密码套件。
4. **配 HTTP 跳转**：用本模块的 Connector 方式，或在 Nginx 层做。
5. **加 HSTS**：响应头 `Strict-Transport-Security`，防降级。
6. **自动续期**：Let's Encrypt 90 天过期，用 cron + certbot 自动续。
7. **监控证书有效期**：用 Actuator 或外部监控，证书快过期时报警。
8. **敏感信息保护**：证书密码用环境变量 `${SSL_PASSWORD}` 注入，不写死在 yml。

**常见坑汇总：**

- 证书和域名不匹配 → 浏览器报错。
- 证书过期没续 → 全站不可用。
- 自签名证书给外部系统调用 → 对方报 SSL 握手失败。
- 反向代理后 scheme 变 http → 无限重定向，要配 forward-headers。
- 用了 HTTP/2 但证书不支持 ALPN → 协议协商失败。

---

> 📌 **学习建议**：HTTPS 是生产环境的"底线安全配置"，没有 HTTPS 的应用不该上线。作为前端转后端的工程师，你对 HTTPS 的前端体验（锁图标、混合内容警告）已经很熟，现在要补的是后端视角：证书从哪来、怎么配进 Tomcat、怎么跳转、怎么续期。建议重点理解"证书 = 公钥 + 身份 + CA 签名"这个本质，以及"生产环境通常在 Nginx 层终结 SSL 而非在应用层"这个架构惯例。把本模块跑通后，试着用 Let's Encrypt 给自己的域名申请一个真证书，体验完整的从申请到部署的流程。
