# 21 - Spring Boot 邮件服务

> 对应项目模块：`demo-email`
> 前置知识：已学完配置读取（`@Value`）、构造器注入、Thymeleaf 模板引擎（`demo-template-thymeleaf`）
> 学习目标：掌握 Spring Boot 整合邮件发送，能发送纯文本、HTML、附件、内嵌静态资源四种邮件，理解邮件密码加密、模板邮件的工程实践。

---

## 一、本模块要解决什么问题？

实际开发中，邮件是非常常见的后端能力，典型场景：

- **用户注册/找回密码**：发送验证码邮件
- **系统告警**：服务异常时通知运维人员
- **业务通知**：订单状态变更、审批结果推送
- **报表推送**：定时把生成的报表以附件形式发给业务方

这些场景下，后端需要程序化地连接 SMTP 服务器、构造邮件内容并发送。如果用原生 JavaMail API，要手写一堆连接、认证、构造 MIME 消息的代码。Spring Boot 的 `spring-boot-starter-mail` 把这些封装好了，引一个依赖、写几行配置就能发邮件。

本模块演示四种邮件形态：**纯文本邮件、HTML 邮件（含模板邮件）、附件邮件、正文内嵌静态资源邮件**，并额外演示了**邮件密码加密**这一生产级实践。

> 💡 前端类比：前端调第三方邮件服务（如 SendGrid、阿里云邮件推送）是发 HTTP 请求到对方 API。Spring Boot 整合邮件则是直接用 SMTP 协议连邮件服务器，不依赖第三方中转——相当于你自己实现了 SendGrid 的客户端。

---

## 二、项目结构

```
demo-email/
├── pom.xml
└── src/
    ├── main/
    │   ├── java/com/xkcoding/email/
    │   │   ├── SpringBootDemoEmailApplication.java   # 启动类
    │   │   └── service/
    │   │       ├── MailService.java                  # 邮件服务接口
    │   │       └── impl/MailServiceImpl.java         # 邮件服务实现
    │   └── resources/
    │       ├── application.yml                        # 邮件服务器配置
    │       ├── email/test.html                        # 自定义目录的邮件模板
    │       ├── templates/welcome.html                 # 默认目录的邮件模板
    │       └── static/xkcoding.png                    # 邮件内嵌图片资源
    └── test/java/com/xkcoding/email/
        ├── SpringBootDemoEmailApplicationTests.java   # 测试基类
        ├── PasswordTest.java                          # 密码加密测试
        └── service/MailServiceTest.java              # 邮件发送测试
```

注意本模块的分层：`service` 包下定义接口 `MailService`，`impl` 子包放实现类 `MailServiceImpl`。这是 Java 后端的标准分层——**面向接口编程**，好处是调用方依赖接口而非实现，便于切换实现和单元测试 mock。

---

## 三、逐行拆解 pom.xml

```xml
<dependencies>
    <!-- 1. Spring Boot 邮件依赖 -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-mail</artifactId>
    </dependency>

    <!-- 2. jasypt 配置文件加解密 -->
    <dependency>
        <groupId>com.github.ulisesbocchio</groupId>
        <artifactId>jasypt-spring-boot-starter</artifactId>
        <version>${jasypt.version}</version>
    </dependency>

    <!-- 3. 测试依赖 -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-test</artifactId>
        <scope>test</scope>
    </dependency>

    <!-- 4. Hutool 工具类 -->
    <dependency>
        <groupId>cn.hutool</groupId>
        <artifactId>hutool-all</artifactId>
    </dependency>

    <!-- 5. Thymeleaf 模板引擎 -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-thymeleaf</artifactId>
    </dependency>
</dependencies>
```

### 3.1 `spring-boot-starter-mail`

这是邮件功能的核心起步依赖，它传递引入了：

- `spring-context`：提供邮件相关的抽象（`MailSender`、`MailMessage` 等接口）
- `jakarta.mail`（旧版 `com.sun.mail:javax.mail`）：JavaMail 的参考实现，真正干 SMTP 通信的底层库

引入它后，Spring Boot 的自动配置（`MailSenderAutoConfiguration`）会根据 `spring.mail.*` 配置自动创建一个 `JavaMailSender` Bean，你直接注入就能用。

### 3.2 `jasypt-spring-boot-starter` —— 配置加密

邮件密码是敏感信息，明文写在 `application.yml` 里会进 git 仓库，有泄露风险。Jasypt 这个库能在配置文件里放密文，启动时自动解密成明文再注入。本模块用它加密邮件密码，后面会详细讲。

### 3.3 `spring-boot-starter-thymeleaf`

本模块要发 HTML 邮件，而手写 HTML 字符串太痛苦（拼接、转义、变量替换），所以用 Thymeleaf 模板引擎渲染邮件内容。把 HTML 写成 `.html` 模板文件，传入变量，渲染出最终 HTML 字符串作为邮件正文。

---

## 四、逐行拆解配置文件 application.yml

```yaml
spring:
  mail:
    host: smtp.mxhichina.com
    port: 465
    username: spring-boot-demo@xkcoding.com
    password: ENC(OT0qGOpXrr1Iog1W+fjOiIDCJdBjHyhy)
    protocol: smtp
    test-connection: true
    default-encoding: UTF-8
    properties:
      mail.smtp.auth: true
      mail.smtp.starttls.enable: true
      mail.smtp.starttls.required: true
      mail.smtp.ssl.enable: true
      mail.display.sendmail: spring-boot-demo
# 为 jasypt 配置解密秘钥
jasypt:
  encryptor:
    password: spring-boot-demo
```

### 4.1 `spring.mail.*` 邮件服务器配置

| 配置项 | 含义 | 说明 |
| --- | --- | --- |
| `host` | SMTP 服务器地址 | 各邮箱服务商不同，如 QQ 邮箱是 `smtp.qq.com`，网易是 `smtp.163.com`，阿里云企业邮是 `smtp.mxhichina.com` |
| `port` | 端口 | 25（明文）、465（SSL）、587（STARTTLS）常用 |
| `username` | 发件人邮箱账号 | 也是默认发件地址 |
| `password` | 邮箱密码或授权码 | 这里用 `ENC(...)` 包裹的密文，Jasypt 会解密 |
| `protocol` | 协议 | 一般是 `smtp` |
| `test-connection: true` | 启动时测试连接 | 启动时连一下 SMTP，连不上直接报错，fail-fast |
| `default-encoding` | 默认编码 | 中文邮件必须 UTF-8，否则乱码 |

### 4.2 `spring.mail.properties.*` 底层 JavaMail 属性

`properties` 下的键值对会原样传给底层 JavaMail API，用于细粒度控制：

| 属性 | 含义 |
| --- | --- |
| `mail.smtp.auth: true` | 开启 SMTP 认证 |
| `mail.smtp.starttls.enable: true` | 启用 STARTTLS（把明文连接升级为加密） |
| `mail.smtp.starttls.required: true` | 强制要求 STARTTLS |
| `mail.smtp.ssl.enable: true` | 直接用 SSL 加密连接（465 端口常用） |
| `mail.display.sendmail: spring-boot-demo` | 发件人显示名（自定义） |

> 💡 前端类比：这就像 axios 里的 `axios.defaults` 全局配置 + 每个请求的 `config` 选项。`spring.mail.*` 是 Spring 封装的高层配置，`properties.*` 是透传给底层的原始选项。

### 4.3 邮箱授权码（重要！）

注意：**绝大多数邮箱（QQ、163、Gmail）不允许直接用登录密码发邮件**，必须在邮箱后台开启 SMTP 服务并生成一个"授权码"，把授权码当作 `password` 配置。这是邮箱厂商的反垃圾邮件安全措施。

### 4.4 `jasypt.encryptor.password` —— Jasypt 解密秘钥

```yaml
jasypt:
  encryptor:
    password: spring-boot-demo
```

这是 Jasypt 解密配置时用的主秘钥。启动时，Jasypt 拦截配置加载，发现 `ENC(...)` 包裹的值，用这个秘钥解密出明文，再注入到 Spring 配置里。

> ⚠️ 本 demo 把解密秘钥也写在 yml 里，这在真实生产是**不安全**的——拿到 yml 就能解密。生产环境应该用环境变量或 JVM 参数传入秘钥：`-Djasypt.encryptor.password=xxx`，秘钥不进代码仓库。后面知识点总结会详细讲。

---

## 五、逐行拆解邮件服务

### 5.1 接口 `MailService.java`

```java
public interface MailService {
    void sendSimpleMail(String to, String subject, String content, String... cc);
    void sendHtmlMail(String to, String subject, String content, String... cc) throws MessagingException;
    void sendAttachmentsMail(String to, String subject, String content, String filePath, String... cc) throws MessagingException;
    void sendResourceMail(String to, String subject, String content, String rscPath, String rscId, String... cc) throws MessagingException;
}
```

定义了四个方法，对应四种邮件形态。注意参数设计：

- `to`：收件人
- `subject`：主题
- `content`：正文
- `String... cc`：可变长参数，表示抄送人（可以传 0 个或多个）。`String...` 是 Java 的可变参数语法，调用时可以 `sendSimpleMail("a@b.com", "主题", "内容")`（不抄送）或 `sendSimpleMail("a@b.com", "主题", "内容", "c1@d.com", "c2@d.com")`（抄送两人）。
- `sendResourceMail` 多了 `rscPath`（静态资源路径）和 `rscId`（资源 ID，正文 HTML 里用 `cid:资源ID` 引用）。

> 💡 前端类比：可变参数 `String...` 类似 JS 的 rest 参数 `...cc`，调用时把多个参数收集成数组。

### 5.2 实现类 `MailServiceImpl.java`

```java
@Service
public class MailServiceImpl implements MailService {
    @Autowired
    private JavaMailSender mailSender;
    @Value("${spring.mail.username}")
    private String from;
    // ...
}
```

- `@Service`：标记为服务层 Bean，Spring 会创建实例注入容器。
- `JavaMailSender mailSender`：Spring Boot 自动配置创建的邮件发送器，所有发送都靠它。这是字段注入（本模块用了 `@Autowired` 字段注入，前面讲过构造器注入更推荐，这里属于历史代码风格）。
- `@Value("${spring.mail.username}")`：把配置里的邮箱账号注入为 `from`，作为默认发件人。

#### 5.2.1 纯文本邮件 `sendSimpleMail`

```java
@Override
public void sendSimpleMail(String to, String subject, String content, String... cc) {
    SimpleMailMessage message = new SimpleMailMessage();
    message.setFrom(from);
    message.setTo(to);
    message.setSubject(subject);
    message.setText(content);
    if (ArrayUtil.isNotEmpty(cc)) {
        message.setCc(cc);
    }
    mailSender.send(message);
}
```

`SimpleMailMessage` 是纯文本邮件模型，只能发文本，不能发 HTML/附件。设置好发件人、收件人、主题、正文、抄送后，调 `mailSender.send(message)` 发送。`ArrayUtil.isNotEmpty` 是 Hutool 的判空工具。

#### 5.2.2 HTML 邮件 `sendHtmlMail`

```java
@Override
public void sendHtmlMail(String to, String subject, String content, String... cc) throws MessagingException {
    MimeMessage message = mailSender.createMimeMessage();
    MimeMessageHelper helper = new MimeMessageHelper(message, true);
    helper.setFrom(from);
    helper.setTo(to);
    helper.setSubject(subject);
    helper.setText(content, true);   // 第二个参数 true 表示内容是 HTML
    if (ArrayUtil.isNotEmpty(cc)) {
        helper.setCc(cc);
    }
    mailSender.send(message);
}
```

要发 HTML 或附件，必须用 `MimeMessage`（MIME 多用途互联网邮件扩展）。但 `MimeMessage` API 繁琐，Spring 提供了 `MimeMessageHelper` 帮你简化操作：

- `new MimeMessageHelper(message, true)`：第二个参数 `true` 表示支持 multipart（多部件，即能带附件/内嵌资源）。
- `helper.setText(content, true)`：第二个参数 `true` 是关键，告诉它 `content` 是 HTML，会按 HTML 渲染。

#### 5.2.3 附件邮件 `sendAttachmentsMail`

```java
@Override
public void sendAttachmentsMail(String to, String subject, String content, String filePath, String... cc) throws MessagingException {
    MimeMessage message = mailSender.createMimeMessage();
    MimeMessageHelper helper = new MimeMessageHelper(message, true);
    // ... setFrom/setTo/setSubject/setText/setCc 同上 ...
    FileSystemResource file = new FileSystemResource(new File(filePath));
    String fileName = filePath.substring(filePath.lastIndexOf(File.separator));
    helper.addAttachment(fileName, file);
    mailSender.send(message);
}
```

附件用 `helper.addAttachment(附件名, 资源)` 添加。`FileSystemResource` 是 Spring 对文件系统资源的封装，`addAttachment` 可以多次调用添加多个附件。

#### 5.2.4 内嵌静态资源邮件 `sendResourceMail`

```java
@Override
public void sendResourceMail(String to, String subject, String content, String rscPath, String rscId, String... cc) throws MessagingException {
    MimeMessage message = mailSender.createMimeMessage();
    MimeMessageHelper helper = new MimeMessageHelper(message, true);
    // ... setFrom/setTo/setSubject/setText/setCc 同上 ...
    FileSystemResource res = new FileSystemResource(new File(rscPath));
    helper.addInline(rscId, res);
    mailSender.send(message);
}
```

**附件 vs 内嵌资源的区别**：

- **附件**：文件作为独立附件，收件人要下载查看。
- **内嵌资源**：图片等资源嵌在邮件正文里，用 `cid:资源ID` 在 HTML 的 `<img src="cid:xxx">` 里引用，收件人打开邮件直接看到图片，不用点开附件。

`helper.addInline(rscId, res)` 把资源以指定 ID 内嵌，正文 HTML 里用 `cid:rscId` 引用。测试代码里能看到这种用法：

```java
String content = "<html><body>这是带静态资源的邮件<br/><img src='cid:" + rscId + "' ></body></html>";
```

---

## 六、模板邮件：用 Thymeleaf 渲染 HTML

手写 HTML 字符串拼接变量很痛苦。本模块用 Thymeleaf 模板引擎，把 HTML 写成模板文件，传入变量渲染出最终 HTML。

### 6.1 模板文件 `welcome.html`

```html
<!DOCTYPE html>
<html lang="en" xmlns:th="http://www.thymeleaf.org">
<head><meta charset="UTF-8"><title>...</title></head>
<body>
<div id="welcome">
    <h3>欢迎使用 <span th:text="${project}"></span> - Powered By <span th:text="${author}"></span></h3>
    <span th:text="${url}"></span>
    <a href="#" th:href="@{${url}}" target="_bank">...</a>
</div>
</body>
</html>
```

`th:text="${project}"` 是 Thymeleaf 语法：把变量 `project` 的值填入这个 `<span>` 的文本内容。`th:href="@{${url}}"` 则把 `url` 变量渲染成链接地址。这和 `demo-template-thymeleaf` 模块讲的语法一致。

### 6.2 渲染并发送（测试类里）

```java
@Autowired
private TemplateEngine templateEngine;

@Test
public void sendHtmlMail() throws MessagingException {
    Context context = new Context();
    context.setVariable("project", "Spring Boot Demo");
    context.setVariable("author", "Yangkai.Shen");
    context.setVariable("url", "https://github.com/xkcoding/spring-boot-demo");

    String emailTemplate = templateEngine.process("welcome", context);
    mailService.sendHtmlMail("237497819@qq.com", "这是一封模板HTML邮件", emailTemplate);
}
```

- `TemplateEngine`：Thymeleaf 的模板引擎，Spring Boot 自动配置注入。
- `Context`：Thymeleaf 的变量上下文，用 `setVariable` 放入模板需要的变量。
- `templateEngine.process("welcome", context)`：用 `welcome` 模板 + context 变量，渲染出最终 HTML 字符串。
- 把 HTML 字符串传给 `sendHtmlMail` 发送。

### 6.3 自定义模板目录

默认 Thymeleaf 从 `classpath:/templates/` 找模板。本模块还演示了用自定义目录 `classpath:/email/`（`test.html` 就放在那）：

```java
@Test
public void sendHtmlMail2() throws MessagingException {
    SpringResourceTemplateResolver templateResolver = new SpringResourceTemplateResolver();
    templateResolver.setApplicationContext(context);
    templateResolver.setCacheable(false);
    templateResolver.setPrefix("classpath:/email/");   // 自定义目录
    templateResolver.setSuffix(".html");                // 后缀
    templateEngine.setTemplateResolver(templateResolver);

    // ... 渲染 test 模板 ...
    String emailTemplate = templateEngine.process("test", context);
    mailService.sendHtmlMail("...", "这是一封模板HTML邮件", emailTemplate);
}
```

`TemplateResolver` 决定从哪找模板、叫什么后缀。改 `prefix`/`suffix` 就能切换模板目录。

> 💡 前端类比：这像改 Vite 的 `resolve.alias` 或 webpack 的 `resolve.modules`，调整模块解析路径。

---

## 七、邮件密码加密：Jasypt

### 7.1 为什么加密？

邮件密码（或授权码）是敏感信息。如果明文写在 `application.yml` 里，一旦代码仓库泄露（内部泄露、开源误传），任何人都能登录你的邮箱发邮件，后果严重。Jasypt 让你在配置文件里放密文，启动时解密。

### 7.2 加密流程

`PasswordTest.java` 演示了如何生成密文：

```java
@Autowired
private StringEncryptor encryptor;

@Test
public void testGeneratePassword() {
    String password = "Just4Test!";                    // 你的邮箱密码
    String encryptPassword = encryptor.encrypt(password);  // 加密
    String decryptPassword = encryptor.decrypt(encryptPassword); // 解密验证
    System.out.println("encryptPassword = " + encryptPassword);
}
```

- `StringEncryptor` 是 Jasypt 提供的加解密器，自动配置注入。
- `encrypt(password)` 返回密文，把密文以 `ENC(密文)` 形式填入 yml。
- 启动时 Jasypt 用 `jasypt.encryptor.password` 配置的秘钥解密 `ENC(...)`，还原出明文。

### 7.3 配置联动

```yaml
spring:
  mail:
    password: ENC(OT0qGOpXrr1Iog1W+fjOiIDCJdBjHyhy)   # 密文
jasypt:
  encryptor:
    password: spring-boot-demo                          # 解密秘钥
```

Jasypt 启动时扫描所有配置值，遇到 `ENC(xxx)` 就用秘钥解密。所以 `spring.mail.password` 最终被注入的是明文，`JavaMailSender` 拿到的是真实密码。

---

## 八、运行与验证

### 8.1 准备邮箱

1. 选一个邮箱（如 QQ 邮箱），在设置里开启 SMTP 服务，获取授权码。
2. 运行 `PasswordTest.testGeneratePassword`，把你的授权码加密，得到 `ENC(密文)`。
3. 替换 `application.yml` 里的 `host`、`port`、`username`、`password` 为你自己的。

### 8.2 运行测试

本模块没有 Controller（邮件发送通常在后台任务或定时任务里触发，不直接暴露 HTTP 接口），验证靠测试类：

```java
public class MailServiceTest extends SpringBootDemoEmailApplicationTests {
    @Autowired
    private MailService mailService;
    // ...
}
```

`MailServiceTest` 继承 `SpringBootDemoEmailApplicationTests`（基类带 `@SpringBootTest`），所以子类自动有 Spring 上下文，能注入 `MailService`。

逐个运行测试方法：

| 测试方法 | 效果 |
| --- | --- |
| `sendSimpleMail` | 发一封纯文本邮件 |
| `sendHtmlMail` | 用 `templates/welcome.html` 渲染发 HTML 邮件 |
| `sendHtmlMail2` | 用 `email/test.html` 渲染发 HTML 邮件（自定义目录） |
| `sendAttachmentsMail` | 发带 `xkcoding.png` 附件的邮件 |
| `sendResourceMail` | 发正文内嵌 `xkcoding.png` 的邮件 |

去收件箱查看效果。

---

## 九、动手练习

1. **换自己的邮箱**：配置自己的 QQ/163 邮箱，跑通 `sendSimpleMail`，收到第一封邮件。
2. **加一个 Controller**：写一个 `@RestController`，加 `@PostMapping("/mail")` 接口，接收收件人、主题、内容参数，调用 `mailService.sendSimpleMail`，实现"HTTP 触发发邮件"。
3. **自定义模板**：写一个验证码邮件模板 `verify-code.html`，用 Thymeleaf 渲染一个 6 位随机验证码，发 HTML 邮件。
4. **群发**：`sendSimpleMail` 的 `to` 改成支持多个收件人（`String... to`），实现群发。
5. **异步发送**：把 `sendSimpleMail` 改成异步（加 `@Async`，后续 `demo-async` 会讲），体会"发邮件不阻塞主流程"。
6. **安全加固**：把 `jasypt.encryptor.password` 从 yml 移到环境变量，用 `-Djasypt.encryptor.password=xxx` 启动，验证仍能解密。

---

## 十、本模块知识点总结（结合实际开发详解）

邮件服务是后端的常见能力，但生产级使用有不少门道。下面把核心知识点放到真实开发场景里讲透。

### 10.1 `JavaMailSender` 与自动配置：Spring Boot 怎么简化邮件发送

**Spring Boot 做了什么？**

引入 `spring-boot-starter-mail` 后，`MailSenderAutoConfiguration` 自动配置类生效，它根据 `spring.mail.*` 配置创建一个 `JavaMailSender` Bean。你只需要注入 `JavaMailSender`，调 `send()` 方法，不用管 SMTP 连接、认证、协议握手这些底层细节。

**实际开发中的使用模式：**

```java
@Service
public class MailServiceImpl implements MailService {
    private final JavaMailSender mailSender;
    
    public MailServiceImpl(JavaMailSender mailSender) {  // 构造器注入
        this.mailSender = mailSender;
    }
}
```

**常见坑：**

1. **自动配置不生效**：`MailSenderAutoConfiguration` 有个条件——classpath 上必须有 `jakarta.mail` 的类。如果只引了 `spring-boot-starter`（不含 mail），自动配置不会触发，注入 `JavaMailSender` 会报找不到 Bean。必须引 `spring-boot-starter-mail`。
2. **`test-connection: true` 导致启动失败**：这个配置在启动时测试 SMTP 连接，如果邮箱配置错或网络不通，应用直接起不来。开发时可以设 `false`，生产设 `true` 以 fail-fast。
3. **多账号发邮件**：默认自动配置只创建一个 `JavaMailSender`。如果要用多个邮箱发，需要手动定义多个 `JavaMailSender` Bean，分别配置，再用 `@Qualifier` 指定注入哪个。

> 💡 前端类比：这像 axios 实例——Spring Boot 帮你创建好一个配置好的 `JavaMailSender`（相当于一个配好 baseURL 和拦截器的 axios 实例），你直接拿来用。

### 10.2 四种邮件形态的选型

| 形态 | API | 适用场景 |
| --- | --- | --- |
| 纯文本 | `SimpleMailMessage` | 验证码、简单通知 |
| HTML | `MimeMessage` + `setText(html, true)` | 营销邮件、精美通知 |
| 附件 | `MimeMessage` + `addAttachment` | 报表、对账单 |
| 内嵌资源 | `MimeMessage` + `addInline` | 邮件正文带图表/Logo |

**实际开发最佳实践：**

1. **能用纯文本就别用 HTML**：纯文本最兼容、最不容易被判垃圾邮件。验证码这类用纯文本即可。
2. **HTML 邮件用模板引擎渲染**：别手拼 HTML 字符串，用 Thymeleaf/Freemarker 写模板，可维护、可预览。本模块的做法是标准实践。
3. **附件别太大**：邮件附件一般限制在 10MB 以内，太大会被拒收或判垃圾。大文件应该用下载链接代替。
4. **内嵌资源注意 CID 一致**：`addInline(rscId, res)` 的 `rscId` 必须和 HTML 里 `cid:rscId` 完全一致，否则图片显示不出来。

**常见坑：**

- HTML 邮件样式不生效：很多邮箱客户端（Outlook、QQ 邮箱）对 CSS 支持有限，复杂样式会丢失。**邮件 HTML 要用内联 style，别用 `<style>` 标签和外部 CSS**，且布局用 table 比 flex 更兼容。
- 附件中文名乱码：附件名含中文时可能乱码，需要用 `MimeUtility.encodeText(fileName)` 编码文件名。
- 内嵌图片在 QQ 邮箱显示为附件：部分客户端不识别 `cid:`，会把内嵌图片当附件。重要图片考虑用外链 URL（但外链图片可能被拦截显示）。

### 10.3 邮件密码加密：Jasypt 的正确用法

**为什么需要？**

配置文件里的明文密码会进 git，泄露即失守。Jasypt 用对称加密（默认 PBE 算法），配置里放密文 `ENC(xxx)`，启动时解密。

**正确用法（生产级）：**

1. **秘钥不能进代码仓库**：本 demo 把 `jasypt.encryptor.password: spring-boot-demo` 写在 yml 里，这是**教学用法，不安全**。生产应该用环境变量或 JVM 参数：

   ```sh
   java -jar app.jar -Djasypt.encryptor.password=真实秘钥
   # 或
   export JASYPT_ENCRYPTOR_PASSWORD=真实秘钥
   java -jar app.jar
   ```

   这样代码仓库里只有密文，秘钥在部署环境注入，拿到代码也解不开。

2. **秘钥管理**：秘钥本身也要妥善保管，可以用 K8s Secret、Vault、云厂商 KMS 管理，不要硬编码在部署脚本里。

3. **自定义加密器**：Jasypt 默认用 PBEWithMD5AndDES，较弱。可以自定义 `StringEncryptor` Bean 用更强算法（如 PBEWithHMACSHA512AndAES_256）。

**常见坑：**

- 秘钥忘了：Jasypt 是对称加密，秘钥丢了密文就无法解密，配置全废。**秘钥要备份**。
- 把秘钥写 yml 还自以为安全：拿到 yml 就能解密所有 `ENC()`，等于没加密。这是最常见的安全误区。
- 加密结果不固定：Jasypt 每次加密同一明文结果不同（带随机盐），但都能用同一秘钥解密，属正常现象。

> 💡 前端类比：这像前端的 `.env.local` 不进 git + 运行时注入环境变量。Jasypt 多了一层"配置文件里的值本身也是密文"，适合配置必须进仓库但又含敏感信息的场景。

### 10.4 邮件发送的可靠性：失败重试与异步

**实际开发的痛点：**

邮件发送依赖外部 SMTP 服务器，可能因网络抖动、限流、服务商故障而失败。直接同步发送有两个问题：

1. **失败无重试**：偶发失败就丢邮件。
2. **阻塞主流程**：发邮件慢（几百毫秒到几秒），同步发送会让接口响应变慢。

**生产级方案：**

1. **异步发送**：用 `@Async` 或消息队列（RabbitMQ/Kafka）把邮件发送解耦出主流程。用户注册接口立即返回，邮件在后台发。

   ```java
   @Async
   public void sendSimpleMail(...) { ... }
   ```

2. **失败重试**：用 Spring Retry 或自己实现重试逻辑，失败时重试 N 次。

   ```java
   @Retryable(value = {MessagingException.class}, maxAttempts = 3, backoff = @Backoff(delay = 1000))
   public void sendSimpleMail(...) { ... }
   ```

3. **落库 + 定时补偿**：把待发邮件存数据库，发送成功标记已发，失败的定时任务重扫重发。这是最可靠的方案，适合"邮件不能丢"的场景（如订单通知）。

4. **限流**：SMTP 服务器有发送频率限制（如 QQ 邮箱每分钟几十封），群发要限流，否则被封号。

**常见坑：**

- 同步发邮件导致接口超时：用户注册接口里同步发邮件，SMTP 慢时接口卡死。**生产必须异步**。
- 失败不记录：邮件发失败没日志没补偿，用户收不到验证码投诉。**要记录发送结果，失败要重试或告警**。
- 群发被封号：循环调 `send` 群发，触发 SMTP 限流被封。**用批量发送 API 或控制频率**。

### 10.5 邮件模板的工程实践

**手拼 HTML vs 模板引擎：**

手拼 HTML 字符串（`"<html>...<span>" + name + "</span>..."`）不可维护、易出错、难预览。用模板引擎（Thymeleaf）是标准做法。

**模板存放位置：**

- 默认放 `classpath:/templates/`（Thymeleaf 默认目录）。
- 也可以自定义目录（本模块演示了 `classpath:/email/`）。

**实际开发的进阶方案：**

1. **模板与业务解耦**：把邮件模板渲染抽成一个 `MailTemplateService`，业务方只传模板名 + 变量，不关心渲染细节。
2. **模板版本管理**：营销邮件频繁改版，可以把模板存数据库或对象存储，运行时加载，不改代码就能改模板。
3. **预览功能**：提供一个接口，传入模板名 + 变量，返回渲染后的 HTML，方便设计/产品预览邮件效果。
4. **多语言**：配合 i18n（国际化）资源，根据收件人语言渲染不同模板。

**常见坑：**

- 模板改了不生效：Thymeleaf 默认有缓存，开发时改模板要重启或关缓存（`spring.thymeleaf.cache: false`）。本模块 `sendHtmlMail2` 里 `setCacheable(false)` 就是关缓存。
- 模板变量没传全：模板里用了 `${xxx}` 但 context 没传 `xxx`，渲染成空或报错。
- HTML 邮件兼容性：见 10.2，邮件客户端 CSS 支持差，模板要按邮件 HTML 规范写（内联样式、table 布局）。

### 10.6 邮件 vs 短信 vs 站内信：通知渠道选型

实际项目里，通知往往不只邮件一种渠道，要选型：

| 渠道 | 优点 | 缺点 | 适用场景 |
| --- | --- | --- | --- |
| 邮件 | 免费、内容丰富、可带附件 | 到达慢、易进垃圾箱 | 验证码、报表、正式通知 |
| 短信 | 即时、到达率高 | 收费、内容受限 | 验证码、紧急告警 |
| 站内信 | 免费、即时、可交互 | 用户要登录才看到 | 系统消息、业务通知 |
| 推送（App/浏览器） | 即时、免费 | 依赖客户端在线 | App 消息、Web 通知 |

**最佳实践**：抽象一个 `NotificationService` 接口，邮件/短信/站内信各一个实现，按场景选渠道，甚至多渠道并发（验证码同时发短信和邮件）。这比把邮件发送逻辑散落在业务代码里更可维护。

---

> 📌 **学习建议**：邮件发送本身不难，难在"生产级可靠性"。学完本模块，建议重点掌握三件事：① 用 `JavaMailSender` + Thymeleaf 模板发 HTML 邮件这套标准组合；② Jasypt 加密敏感配置的正确姿势（秘钥走环境变量）；③ 异步 + 重试 + 落库补偿的可靠性思维。这三点是从"能发邮件"到"邮件系统稳定可靠"的关键跨越。另外，邮件、短信、站内信这类通知能力，在真实项目里通常抽象成统一的消息服务，而不是各写各的——这种"抽象渠道"的设计思维，对前端工程师理解后端架构很有帮助。
