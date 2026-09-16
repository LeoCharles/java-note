# 12 - 文件上传（本地 + 七牛云）

> 对应项目模块：`demo-upload`
> 前置知识：已学完前 11 个模块，了解启动类、配置注入、`@RestController`、Thymeleaf 模板基本用法
> 学习目标：掌握 Spring Boot 处理 `multipart/form-data` 文件上传的机制，能实现本地存储上传和云存储（七牛云）上传，理解 `MultipartFile`、上传配置、第三方 SDK 整合的套路。

---

## 一、本模块要解决什么问题？

文件上传是 Web 应用最常见的需求之一：头像上传、附件上传、图片素材上传……前端工程师对它绝不陌生——就是用 `<input type="file">` 或 UI 组件库的 `Upload` 组件，把文件塞进 `FormData`，再用 `axios` POST 到后端。

但后端要做什么？本模块回答这个问题：

1. **接收文件**：Spring Boot 怎么把 HTTP 请求里的文件解析成 Java 对象（`MultipartFile`）。
2. **本地存储**：把文件写到服务器磁盘，返回访问路径。
3. **云存储**：把文件传到七牛云（对象存储 OSS），返回 CDN 访问地址。
4. **配置管理**：上传大小限制、临时目录、云存储密钥等如何配置。

本模块的最终效果：浏览器访问 `http://localhost:8080/demo/`，看到一个 Vue + iView 写的上传页面，支持「本地上传」和「七牛云上传」两种方式，上传后返回文件路径。

> 💡 前端类比：你以前用 `axios.post(url, formData, {headers: {'Content-Type': 'multipart/form-data'}})` 上传，本模块就是那个 `url` 指向的后端接口的实现。

---

## 二、项目结构

```
demo-upload/
├── pom.xml
└── src/main/
    ├── java/com/xkcoding/upload/
    │   ├── SpringBootDemoUploadApplication.java   # 启动类
    │   ├── config/
    │   │   └── UploadConfig.java                  # 上传 + 七牛云配置类（核心）
    │   ├── controller/
    │   │   ├── IndexController.java               # 首页（返回上传页面）
    │   │   └── UploadController.java             # 上传接口（本地 + 七牛云）
    │   └── service/
    │       ├── IQiNiuService.java                 # 七牛云服务接口
    │       └── impl/QiNiuServiceImpl.java         # 七牛云服务实现
    └── resources/
        ├── application.yml                         # 配置（七牛密钥、上传限制）
        └── templates/index.html                    # 上传页面（Vue + iView）
```

注意分层：`config` 放配置类，`controller` 放接口，`service` 放业务逻辑。七牛云相关被封装成 `IQiNiuService` 接口 + 实现，这是「面向接口编程」的标准做法——将来换阿里云 OSS、AWS S3 时，只需新增一个实现类，控制器不用改。

---

## 三、逐行拆解 pom.xml

```xml
<dependencies>
    <!-- Lombok：自动生成 getter/setter/log 等 -->
    <dependency>
        <groupId>org.projectlombok</groupId>
        <artifactId>lombok</artifactId>
        <optional>true</optional>
    </dependency>

    <!-- Web 起步依赖：内嵌 Tomcat + Spring MVC，文件上传的底层支持也在这里 -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-web</artifactId>
    </dependency>

    <!-- Thymeleaf：用于渲染上传页面 index.html -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-thymeleaf</artifactId>
    </dependency>

    <!-- 测试 -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-test</artifactId>
        <scope>test</scope>
    </dependency>

    <!-- Hutool 工具类：用于字符串处理、日期、文件、JSON -->
    <dependency>
        <groupId>cn.hutool</groupId>
        <artifactId>hutool-all</artifactId>
    </dependency>

    <!-- 七牛云 Java SDK -->
    <dependency>
        <groupId>com.qiniu</groupId>
        <artifactId>qiniu-java-sdk</artifactId>
        <version>[7.2.0, 7.2.99]</version>
    </dependency>
</dependencies>
```

**关键点：**

1. **文件上传不需要额外引依赖**：`spring-boot-starter-web` 已经内置了文件上传支持（基于 Servlet 3.0 的 `javax.servlet.http.Part` / `StandardServletMultipartResolver`），你不需要像老项目那样引 `commons-fileupload`。
2. **七牛云 SDK**：`qiniu-java-sdk` 是七牛官方提供的 Java 客户端，版本用区间 `[7.2.0, 7.2.99]` 表示取这个范围内的最新版本。实际开发中建议锁定具体版本（如 `7.2.9`），避免每次构建版本漂移。

> ⚠️ 注意：本模块的 `qiniu-java-sdk` 自己写了版本号，没有交给父 POM 管。这是因为父 POM 没有在 `dependencyManagement` 里声明七牛 SDK 的版本。实际项目中最好把所有第三方版本统一到父 POM。

---

## 四、配置文件 application.yml

```yaml
server:
  port: 8080
  servlet:
    context-path: /demo
qiniu:
  accessKey:        # 七牛云 AK（需自己填）
  secretKey:        # 七牛云 SK（需自己填）
  bucket:           # 七牛云存储空间名
  prefix:           # 七牛云绑定域名（如 http://xxx.bkt.clouddn.com）
spring:
  servlet:
    multipart:
      enabled: true                                          # 开启上传支持
      location: /Users/yangkai.shen/.../tmp                 # 临时目录
      file-size-threshold: 5MB                               # 超过 5MB 写磁盘临时文件
      max-file-size: 20MB                                    # 单个文件最大 20MB
```

### 4.1 七牛云配置

`qiniu` 是自定义配置前缀，对应四个值：`accessKey`（公钥）、`secretKey`（私钥）、`bucket`（存储空间名）、`prefix`（绑定的访问域名）。这些值要你在七牛云控制台申请后填入。

> 💡 安全提示：密钥不要硬编码进 yml 提交到 Git！实际项目用环境变量 `${QINIU_ACCESS_KEY}` 注入，或用配置中心管理。本 demo 为演示方便写死在 yml，但留空了。

### 4.2 multipart 配置（重点）

`spring.servlet.multipart` 是 Spring Boot 文件上传的核心配置，常用项：

| 配置项 | 作用 | 默认值 |
| --- | --- | --- |
| `enabled` | 是否开启上传支持 | true |
| `location` | 临时文件目录（文件超过阈值时写盘） | 系统临时目录 |
| `file-size-threshold` | 文件大小阈值，超过则写磁盘临时文件 | 0（全部写磁盘） |
| `max-file-size` | 单个文件最大大小 | 1MB |
| `max-request-size` | 整个请求最大大小（多文件时限制总和） | 10MB |
| `resolve-lazily` | 是否懒加载（真正用时才解析） | false |

**`file-size-threshold` 的意义**：上传的文件，Spring 默认会先放在内存里，如果文件很大，内存撑不住。设置阈值后，超过阈值的部分会写成临时文件到 `location` 指定的目录，避免 OOM（内存溢出）。

> 💡 前端类比：这像前端处理大文件时的「分片」思路——小文件直接内存处理，大文件落盘。区别是 Spring 帮你自动做了这个判断。

**常见坑**：`max-file-size` 默认只有 1MB，很多新手上传个 2MB 图片就报 `Maximum upload size exceeded`，就是这个限制。生产环境要按业务调大，但也不能无限大，否则有 DoS 风险（恶意上传超大文件撑爆磁盘）。

---

## 五、核心配置类 UploadConfig（重点）

`config/UploadConfig.java` 是本模块最复杂的类，它做了两件事：配置 Spring 的上传解析器 + 注册七牛云的 Bean。逐段看。

### 5.1 类上的条件注解

```java
@Configuration
@ConditionalOnClass({Servlet.class, StandardServletMultipartResolver.class, MultipartConfigElement.class})
@ConditionalOnProperty(prefix = "spring.http.multipart", name = "enabled", matchIfMissing = true)
@EnableConfigurationProperties(MultipartProperties.class)
public class UploadConfig {
```

- `@Configuration`：标记为配置类，里面的 `@Bean` 方法会被 Spring 调用注册 Bean。
- `@ConditionalOnClass(...)`：只有 classpath 上存在这些类时，这个配置类才生效。这是 Spring Boot 自动配置的典型手法——条件化装配。
- `@ConditionalOnProperty(prefix = "spring.http.multipart", name = "enabled", matchIfMissing = true)`：只有配置了 `spring.http.multipart.enabled=true`（或不配，默认 true）时才生效。允许用户通过配置关闭上传功能。
- `@EnableConfigurationProperties(MultipartProperties.class)`：启用 `MultipartProperties`，把 `spring.servlet.multipart.*` 配置绑定到一个 `MultipartProperties` 对象，方便代码里读取。

> 💡 这几个 `@ConditionalOnXxx` 注解组合起来，就是 Spring Boot「自动配置」的精髓：根据条件决定是否装配。本模块手动写了一遍上传的自动配置，实际 `spring-boot-starter-web` 已经自带了类似配置，这里相当于「覆盖/演示」一遍原理。

### 5.2 上传解析器 Bean

```java
@Bean
@ConditionalOnMissingBean
public MultipartConfigElement multipartConfigElement() {
    return this.multipartProperties.createMultipartConfig();
}

@Bean(name = DispatcherServlet.MULTIPART_RESOLVER_BEAN_NAME)
@ConditionalOnMissingBean(MultipartResolver.class)
public StandardServletMultipartResolver multipartResolver() {
    StandardServletMultipartResolver multipartResolver = new StandardServletMultipartResolver();
    multipartResolver.setResolveLazily(this.multipartProperties.isResolveLazily());
    return multipartResolver;
}
```

- `MultipartConfigElement`：把 yml 里的 `max-file-size` 等配置转成 Servlet 规范的上传配置对象。
- `StandardServletMultipartResolver`：Spring MVC 的上传解析器，负责把 `multipart/form-data` 请求解析成 `MultipartFile`。`setResolveLazily` 控制是否懒解析。
- `@ConditionalOnMissingBean`：如果用户自己没定义这些 Bean，才用这里的默认实现。这是「用户配置优先于自动配置」的体现。

### 5.3 七牛云 Bean 注册

```java
@Bean
public com.qiniu.storage.Configuration qiniuConfig() {
    return new com.qiniu.storage.Configuration(Zone.zone0());  // 华东机房
}

@Bean
public UploadManager uploadManager() {
    return new UploadManager(qiniuConfig());
}

@Bean
public Auth auth() {
    return Auth.create(accessKey, secretKey);
}

@Bean
public BucketManager bucketManager() {
    return new BucketManager(auth(), qiniuConfig());
}
```

这里把七牛云 SDK 的几个核心对象注册成 Spring Bean：

| Bean | 作用 |
| --- | --- |
| `Configuration` | 七牛云机房配置（`Zone.zone0()` 是华东机房） |
| `UploadManager` | 上传管理器，负责执行文件上传 |
| `Auth` | 认证对象，用 AK/SK 生成上传凭证（token） |
| `BucketManager` | 空间管理器，管理存储空间（查询、删除文件等） |

**为什么注册成 Bean 而不是用时再 new？** 因为这些对象是线程安全的、可复用的，注册成单例 Bean 后，整个应用共享，避免每次上传都重复创建。`accessKey`/`secretKey` 通过 `@Value` 注入。

> 💡 前端类比：这像在 Vue 的 `app.config.globalProperties` 或 Pinia store 里挂一个全局单例服务，所有组件都能用，而不是每个组件自己 `new`。

---

## 六、七牛云服务层

### 6.1 接口 IQiNiuService

```java
public interface IQiNiuService {
    Response uploadFile(File file) throws QiniuException;
}
```

只定义一个方法：上传文件，返回七牛的 `Response`。面向接口编程，实现可替换。

### 6.2 实现 QiNiuServiceImpl

```java
@Service
@Slf4j
public class QiNiuServiceImpl implements IQiNiuService, InitializingBean {
    private final UploadManager uploadManager;
    private final Auth auth;

    @Value("${qiniu.bucket}")
    private String bucket;

    private StringMap putPolicy;

    @Autowired
    public QiNiuServiceImpl(UploadManager uploadManager, Auth auth) {
        this.uploadManager = uploadManager;
        this.auth = auth;
    }
    ...
}
```

- `@Service`：注册为 Spring Bean，业务层标记。
- `InitializingBean`：实现这个接口的 Bean，在初始化完成后会调用 `afterPropertiesSet()`，适合做初始化逻辑。
- 构造器注入 `UploadManager` 和 `Auth`（都是上一步注册的 Bean），`@Value` 注入 `bucket` 名。

### 6.3 上传方法（含重试机制）

```java
@Override
public Response uploadFile(File file) throws QiniuException {
    Response response = this.uploadManager.put(file, file.getName(), getUploadToken());
    int retry = 0;
    while (response.needRetry() && retry < 3) {
        response = this.uploadManager.put(file, file.getName(), getUploadToken());
        retry++;
    }
    return response;
}
```

- `uploadManager.put(file, key, token)`：执行上传，参数是文件对象、存储的 key（文件名）、上传凭证。
- **重试机制**：如果七牛返回「需要重试」（`response.needRetry()`），最多重试 3 次。这是网络服务调用的常见容错手段。

### 6.4 上传凭证与回调策略

```java
@Override
public void afterPropertiesSet() {
    this.putPolicy = new StringMap();
    putPolicy.put("returnBody", "{\"key\":\"$(key)\",\"hash\":\"$(etag)\",\"bucket\":\"$(bucket)\",\"width\":$(imageInfo.width), \"height\":${imageInfo.height}}");
}

private String getUploadToken() {
    return this.auth.uploadToken(bucket, null, 3600, putPolicy);
}
```

- `afterPropertiesSet()`：Bean 初始化后执行，配置上传策略 `putPolicy`。
- `returnBody`：上传成功后七牛返回的内容格式，这里配置成返回 JSON，包含 `key`（文件名）、`hash`、`bucket`、图片宽高。
- `getUploadToken()`：用 `Auth` 生成上传凭证，有效期 3600 秒（1 小时）。七牛云上传必须带凭证，用于鉴权。

> 💡 前端类比：上传凭证类似你调第三方 API 时的 `Authorization: Bearer xxx` token，是身份证明。区别是七牛的 token 是后端用 SK 签名生成的，前端拿不到 SK，所以由后端签发。

---

## 七、上传接口 UploadController（核心）

`controller/UploadController.java` 提供两个接口：本地上传和云上传。

### 7.1 类定义与依赖

```java
@RestController
@Slf4j
@RequestMapping("/upload")
public class UploadController {
    @Value("${spring.servlet.multipart.location}")
    private String fileTempPath;

    @Value("${qiniu.prefix}")
    private String prefix;

    private final IQiNiuService qiNiuService;

    @Autowired
    public UploadController(IQiNiuService qiNiuService) {
        this.qiNiuService = qiNiuService;
    }
    ...
}
```

- `@RequestMapping("/upload")`：类级路径，所有接口都以 `/upload` 开头。
- `@Value` 注入临时目录和七牛域名。
- 构造器注入 `IQiNiuService`（面向接口，不依赖具体实现）。

### 7.2 本地上传接口

```java
@PostMapping(value = "/local", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
public Dict local(@RequestParam("file") MultipartFile file) {
    if (file.isEmpty()) {
        return Dict.create().set("code", 400).set("message", "文件内容为空");
    }
    String fileName = file.getOriginalFilename();
    String rawFileName = StrUtil.subBefore(fileName, ".", true);
    String fileType = StrUtil.subAfter(fileName, ".", true);
    String localFilePath = StrUtil.appendIfMissing(fileTempPath, "/") + rawFileName + "-" + DateUtil.current(false) + "." + fileType;
    try {
        file.transferTo(new File(localFilePath));
    } catch (IOException e) {
        log.error("【文件上传至本地】失败，绝对路径：{}", localFilePath);
        return Dict.create().set("code", 500).set("message", "文件上传失败");
    }
    log.info("【文件上传至本地】绝对路径：{}", localFilePath);
    return Dict.create().set("code", 200).set("message", "上传成功").set("data", Dict.create().set("fileName", fileName).set("filePath", localFilePath));
}
```

逐行看：

- `@PostMapping(value = "/local", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)`：只接收 `multipart/form-data` 类型的 POST 请求。`consumes` 限制请求的 Content-Type。
- `@RequestParam("file") MultipartFile file`：从前端 `FormData` 中取名为 `file` 的文件，绑定成 `MultipartFile` 对象。`MultipartFile` 是 Spring 封装的上传文件接口，提供 `getOriginalFilename()`、`transferTo()`、`isEmpty()` 等方法。
- `file.isEmpty()`：校验文件是否为空。
- 文件名处理：用 Hutool 的 `StrUtil.subBefore/subAfter` 按 `.` 拆分出文件名和扩展名，再用时间戳 `DateUtil.current(false)` 拼接生成唯一文件名，避免重名覆盖。
- `file.transferTo(new File(localFilePath))`：把上传文件写到目标路径。这是核心 API。
- 返回 `Dict`（Hutool 的有序 Map），会被 Jackson 序列化成 JSON。

> 💡 前端类比：`MultipartFile` 就是你前端 `FormData.append('file', file)` 里那个 file 在后端的化身。`transferTo` 相当于 Node.js 里的 `fs.writeFile`。

### 7.3 七牛云上传接口

```java
@PostMapping(value = "/yun", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
public Dict yun(@RequestParam("file") MultipartFile file) {
    if (file.isEmpty()) {
        return Dict.create().set("code", 400).set("message", "文件内容为空");
    }
    String fileName = file.getOriginalFilename();
    String rawFileName = StrUtil.subBefore(fileName, ".", true);
    String fileType = StrUtil.subAfter(fileName, ".", true);
    String localFilePath = StrUtil.appendIfMissing(fileTempPath, "/") + rawFileName + "-" + DateUtil.current(false) + "." + fileType;
    try {
        file.transferTo(new File(localFilePath));                    // 1. 先存本地临时文件
        Response response = qiNiuService.uploadFile(new File(localFilePath));  // 2. 上传到七牛
        if (response.isOK()) {
            JSONObject jsonObject = JSONUtil.parseObj(response.bodyString());
            String yunFileName = jsonObject.getStr("key");
            String yunFilePath = StrUtil.appendIfMissing(prefix, "/") + yunFileName;
            FileUtil.del(new File(localFilePath));                   // 3. 删除本地临时文件
            log.info("【文件上传至七牛云】绝对路径：{}", yunFilePath);
            return Dict.create().set("code", 200).set("message", "上传成功").set("data", Dict.create().set("fileName", yunFileName).set("filePath", yunFilePath));
        } else {
            FileUtil.del(new File(localFilePath));
            return Dict.create().set("code", 500).set("message", "文件上传失败");
        }
    } catch (IOException e) {
        log.error("【文件上传至七牛云】失败，绝对路径：{}", localFilePath);
        return Dict.create().set("code", 500).set("message", "文件上传失败");
    }
}
```

流程是「先存本地，再传云端，最后删本地」：

1. `file.transferTo(...)`：先把文件写到本地临时目录（因为七牛 SDK 接收 `File` 对象，而不是 `MultipartFile`）。
2. `qiNiuService.uploadFile(...)`：调用服务层上传到七牛云。
3. 成功后解析返回的 JSON，拼出云端访问 URL，`FileUtil.del` 删除本地临时文件。

> 💡 为什么先存本地？因为七牛 SDK 的 `put` 方法接收 `File` 或 `InputStream`。也可以直接用 `InputStream` 上传（`uploadManager.put(InputStream, ...)`），避免落盘，但本 demo 选择了先落盘的方案。实际开发中，直接用流上传更高效，省去磁盘 IO。

---

## 八、首页与前端页面

### 8.1 IndexController

```java
@Controller
public class IndexController {
    @GetMapping("")
    public String index() {
        return "index";
    }
}
```

注意这里用的是 `@Controller`（不是 `@RestController`），返回字符串 `"index"` 会被 Thymeleaf 解析成模板路径 `templates/index.html`，渲染成 HTML 返回。这就是模板引擎的用法（详见模块 09）。

### 8.2 前端页面 index.html

页面用 Vue 2 + iView 组件库写的，核心是两个 `Upload` 组件：

```html
<Upload
    :before-upload="handleLocalUpload"
    action="/demo/upload/local"
    ref="localUploadRef"
    :on-success="handleLocalSuccess"
    :on-error="handleLocalError"
>
    <i-button icon="ios-cloud-upload-outline">选择文件</i-button>
</Upload>
```

- `action` 指向后端接口 `/demo/upload/local`。
- `:before-upload` 返回 `false` 阻止自动上传，把文件存到 `data` 里，等点击「上传」按钮再手动调用 `this.$refs.localUploadRef.post(file)` 触发上传。
- `:on-success` / `:on-error` 处理上传结果。

> 💡 这是前端同学最熟悉的部分——后端只管提供接口，前端用任何方式（iView Upload、Element Plus Upload、原生 FormData）调用都行。后端接口和前端组件是解耦的。

---

## 九、运行与验证

### 9.1 准备工作

1. 注册七牛云账号，创建存储空间（bucket），获取 AK/SK 和绑定域名，填入 `application.yml`。
2. 修改 `spring.servlet.multipart.location` 为你本机的临时目录路径（确保目录存在且有写权限）。
3. 如果只测本地上传，七牛配置可以留空（但启动时 `Auth.create(null, null)` 可能报错，需要注释掉七牛相关 Bean 或填占位值）。

### 9.2 启动与访问

```sh
mvn spring-boot:run
```

访问 `http://localhost:8080/demo/`，看到上传页面。选择文件，点「本地上传」，成功后显示文件路径。

### 9.3 用 curl 测试

不依赖前端页面，直接用 curl 上传：

```sh
curl -X POST http://localhost:8080/demo/upload/local \
  -F "file=@/path/to/test.jpg"
```

`-F "file=@文件路径"` 等价于前端的 `FormData.append('file', file)`。

---

## 十、动手练习

1. **改大小限制**：把 `max-file-size` 改成 `1MB`，上传一个 2MB 的文件，观察报错信息。
2. **用流上传**：改造 `QiNiuServiceImpl`，用 `uploadManager.put(InputStream, key, token, ...)` 直接传流，省去本地临时文件。
3. **加文件类型校验**：在控制器里校验扩展名，只允许 jpg/png，其他返回 400。
4. **重命名策略**：把时间戳改成 UUID，观察文件名变化。
5. **换云存储**：新增一个 `AliyunOssServiceImpl` 实现 `IQiNiuService` 接口（或抽个更通用的 `IFileService`），用 `@Primary` 或 `@Qualifier` 切换，体会面向接口编程的好处。
6. **加进度条**：前端用 `on-progress` 事件显示上传百分比（注意：浏览器端能拿到的是上传进度，不是云端处理进度）。

---

## 十一、本模块知识点总结（结合实际开发详解）

文件上传是后端的基本功，下面把核心知识点放到真实开发场景里讲透。

### 11.1 `MultipartFile`：上传文件的核心抽象

**实际开发中怎么用？**

`MultipartFile` 是 Spring 对上传文件的封装，常用方法：

| 方法 | 作用 |
| --- | --- |
| `isEmpty()` | 文件是否为空 |
| `getOriginalFilename()` | 获取原始文件名（前端传来的名字） |
| `getContentType()` | 获取 MIME 类型（如 image/jpeg） |
| `getSize()` | 文件大小（字节） |
| `getBytes()` | 获取文件字节数组（小文件用） |
| `getInputStream()` | 获取输入流（大文件用，避免内存爆炸） |
| `transferTo(File)` | 写到目标文件 |

**最佳实践：**

1. **大文件用流，小文件用字节数组**：`getBytes()` 会把整个文件读进内存，大文件会 OOM。超过几 MB 就该用 `getInputStream()` 流式处理。
2. **永远校验 `isEmpty()`**：前端可能传空文件，不校验直接 `transferTo` 会报错。
3. **不要信任 `getOriginalFilename()`**：这是前端传的名字，可能包含路径（`../../etc/passwd`）、特殊字符、甚至恶意脚本名。**永远重新生成文件名**（UUID/时间戳），只用原始名的扩展名。

**常见坑：**

- `getOriginalFilename()` 在不同浏览器/客户端下可能带完整路径（如 `C:\Users\xxx\a.jpg`），直接用会导致路径问题。要用 `FilenameUtils.getName()`（Apache Commons IO）或只取最后一段。
- `transferTo` 传相对路径时，会相对于工作目录，容易找不到文件。**用绝对路径**。

### 11.2 上传配置：大小限制与临时目录

**实际开发的标准配置：**

```yaml
spring:
  servlet:
    multipart:
      max-file-size: 10MB        # 单文件上限
      max-request-size: 100MB    # 请求总上限（多文件场景）
      file-size-threshold: 1MB   # 超过 1MB 落盘
      location: /data/tmp        # 临时目录，确保存在且可写
```

**最佳实践：**

1. **按业务设上限**：头像上传 2MB 够了，视频上传可能要 500MB。上限不是越大越好，过大有 DoS 风险。
2. **临时目录要监控**：`location` 指向的目录如果磁盘满了，上传会失败。生产环境要监控磁盘容量。
3. **异常处理**：超过大小会抛 `MaxUploadSizeExceededException`，要用全局异常处理器（见模块 07）捕获，返回友好提示，而不是给前端一坨堆栈。

**常见坑：**

- Nginx 反向代理时，Nginx 自己也有 `client_max_body_size` 限制（默认 1MB），后端调大了但 Nginx 没调，照样 413 报错。**链路上每一层都要检查**。
- 临时目录不存在或无写权限，启动不报错但上传时报 `IOException`。

### 11.3 本地存储 vs 云存储：怎么选？

**本地存储的适用场景：**

- 内网应用、单机部署、文件量小
- 开发测试环境
- 对文件访问有严格内网隔离要求

**本地存储的问题：**

1. **扩容难**：磁盘空间有限，多台服务器时文件分散，访问要负载均衡到对应机器。
2. **备份难**：服务器挂了文件就丢了。
3. **CDN 加速难**：本地文件无法直接接 CDN。

**云存储（七牛/阿里 OSS/AWS S3）的优势：**

1. **无限容量**：按量付费，不用管磁盘。
2. **自带 CDN**：上传后直接通过域名访问，全球加速。
3. **高可用**：云厂商保证多副本，不怕单点故障。
4. **解耦**：应用服务器不存文件，只处理业务，架构更干净。

**实际开发的推荐方案：**

- 生产环境**首选云存储**（OSS/S3），应用服务器不落盘，直接用流上传到云端。
- 本地存储仅用于临时文件、内网工具系统。
- 大文件（视频）用**分片上传**或**客户端直传**（前端拿后端签发的 token 直接传云端，不经过应用服务器，减轻后端压力）。

### 11.4 第三方 SDK 整合的通用套路

本模块整合七牛云的方式，是整合任何第三方 SDK 的标准模板：

1. **引依赖**：在 pom 里引 SDK。
2. **写配置**：密钥、端点等放 yml，用 `@Value` 或 `@ConfigurationProperties` 读。
3. **注册核心对象为 Bean**：在 `@Configuration` 类里用 `@Bean` 把 SDK 的核心对象（Client/Manager/Auth）注册成单例。
4. **封装服务层**：写 `IXxxService` 接口 + 实现，把 SDK 的调用细节封装起来，对外提供业务方法。
5. **控制器调用服务**：控制器只依赖接口，不直接碰 SDK 类。

**为什么这么分？**

- Bean 单例复用，避免重复创建开销。
- 接口隔离，换 SDK 时只改实现，控制器和配置不动。
- 配置外置，密钥不写死，多环境切换方便。

**常见坑：**

- SDK 版本和 Spring Boot 版本不兼容（如 SDK 依赖的 HTTP 客户端和 Spring Boot 冲突），要排查依赖树。
- SDK 对象不是线程安全的却注册成单例，并发时出问题。注册前查文档确认线程安全性。
- 密钥写死在代码里提交到 Git，泄露后被人盗刷。**密钥必须用环境变量或配置中心管理**。

### 11.5 上传安全：必须考虑的防护

文件上传是安全重灾区，实际开发必须做防护：

1. **文件类型校验**：不能只校验扩展名（可伪造），要校验 `Content-Type` 甚至文件头（magic number）。比如 JPG 文件头是 `FF D8 FF`。
2. **文件重命名**：用 UUID/时间戳重命名，避免覆盖和路径穿越攻击（`../../etc/passwd`）。
3. **存储隔离**：上传目录不要有执行权限，避免上传 `.jsp`/`.php` 被当脚本执行。
4. **大小限制**：防止超大文件 DoS。
5. **权限控制**：上传接口要鉴权，不能匿名上传（除非是公开图床）。
6. **病毒扫描**：对上传文件做病毒扫描（企业级要求）。

**常见坑：**

- 只校验扩展名，攻击者把 `.jsp` 改名 `.jpg` 绕过，上传后访问触发执行。
- 上传目录在 Web 容器可访问路径下，导致上传的文件能被直接访问执行。
- 文件名用用户传的原名，导致路径穿越（`../../../`）覆盖系统文件。

### 11.6 前后端协作：上传接口的契约

本模块前端用 iView Upload 组件，后端提供 `/upload/local` 和 `/upload/yun` 两个接口。前后端的契约是：

- 请求方法：POST
- Content-Type：`multipart/form-data`
- 参数名：`file`（前端 `FormData.append('file', ...)`，后端 `@RequestParam("file")`）
- 响应：`{ code, message, data: { fileName, filePath } }`

**实际开发的最佳实践：**

1. **统一响应格式**：用统一响应体（见模块 07），前端按统一逻辑处理。
2. **返回可访问 URL**：本地上传返回的 `filePath` 是服务器绝对路径，前端无法直接访问。生产环境要返回一个 HTTP 可访问的 URL（如 `http://cdn.example.com/xxx.jpg`）。
3. **进度反馈**：大文件上传时，前端需要进度条。后端可以用异步任务 + 轮询/WebSocket 反馈进度，或让前端直传云端拿云端进度。
4. **断点续传/分片上传**：超大文件（>1GB）用分片上传，前端切片逐个传，后端合并。这是高级场景，云存储 SDK 通常自带分片上传支持。

---

> 📌 **学习建议**：文件上传看似简单，但涉及安全、性能、存储架构多个维度。建议你重点掌握三点：`MultipartFile` 的流式处理（避免 OOM）、第三方 SDK 整合的「配置类 + 服务层」套路、以及上传安全的防护清单。实际项目中，绝大多数文件上传会直接对接云存储（OSS/S3），本地存储只在特定场景用。理解了本模块的七牛云整合方式，换成阿里 OSS、AWS S3 只是换 SDK 和配置，套路完全一致。
