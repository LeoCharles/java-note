# 29 - 第三方登录集成（JustAuth）

> 对应项目模块：`demo-social`
> 前置知识：已学完 `01`~`28`，了解 Spring Boot 基本用法、Redis 缓存、Controller 路由
> 学习目标：理解 OAuth2 第三方登录的完整流程，掌握用 JustAuth + `justauth-spring-boot-starter` 集成 QQ、GitHub、微信、谷歌、微软、小米、企业微信等多平台第三方登录。

---

## 一、本模块要解决什么问题？

### 1.1 什么是第三方登录？

你在很多网站见过"用 GitHub 登录""用微信登录""用 QQ 登录"的按钮。点了之后跳到对应平台，授权后回到原网站，你就登录了——不用在原网站单独注册账号。这就是**第三方登录（OAuth2 授权登录）**。

> 💡 前端类比：作为前端工程师，你大概率对接过这类登录按钮。前端负责发起跳转、接收回调，但**真正用授权码换 access_token、再用 token 换用户信息这两步，必须放在后端**（因为涉及 client_secret，不能暴露给浏览器）。本模块讲的就是后端这两步怎么实现。

### 1.2 不用 JustAuth 之前，第三方登录有多麻烦？

每接一个平台，你都要：

1. 读该平台的 OAuth2 文档（QQ、微信、GitHub 文档风格各异）。
2. 手动拼授权 URL（含 `client_id`、`redirect_uri`、`state`、`scope`）。
3. 在回调里拿 `code`，发 HTTP 请求换 `access_token`。
4. 再用 `access_token` 发请求拿用户信息。
5. 每个平台的接口地址、参数名、返回格式都不一样，要一个个适配。

接 7 个平台 = 写 7 套几乎重复又略有差异的代码。**JustAuth 把这套流程抽象统一**，一个 `AuthRequest` 接口搞定所有平台，配置化接入，API 极简。

### 1.3 本模块的最终效果

访问 `GET http://oauth.xkcoding.com/demo/oauth`，返回一个 JSON，列出所有支持的登录方式及对应链接：

```json
{
  "qq登录": "http://oauth.xkcoding.com/demo/oauth/login/qq",
  "github登录": "http://oauth.xkcoding.com/demo/oauth/login/github",
  ...
}
```

点击某个链接 → 跳到对应平台授权 → 授权后回调到本应用 → 返回用户信息（昵称、头像、openid 等）。

---

## 二、先搞懂 OAuth2 授权码流程（核心理论）

在写代码前，必须理解 OAuth2 的**授权码模式（Authorization Code）**，这是绝大多数第三方登录的底层流程。整个流程分 5 步：

```
用户                你的应用(后端)           第三方平台(GitHub等)
 |                      |                        |
 |--点"GitHub登录"------>|                        |
 |                      |---1.重定向到授权页----->|
 |<-----------------------------------------------| (展示授权页)
 |--2.点"同意授权"------>|                        |
 |                      |<---3.带code回调--------|
 |                      |---4.用code换token------>|
 |                      |<---返回access_token-----|
 |                      |---5.用token换用户信息--->|
 |                      |<---返回用户信息----------|
 |<---登录成功(发JWT)----|                        |
```

**5 个关键概念：**

| 概念 | 说明 | 前端类比 |
| --- | --- | --- |
| `client_id` | 应用在第三方注册后拿到的"身份证号" | 像 AppKey |
| `client_secret` | 应用的密钥，**只能放后端**，不能泄露 | 像 AppSecret |
| `redirect_uri` | 授权后回调的地址，必须在第三方后台预先登记 | 像 webhook 回调 URL |
| `code`（授权码） | 用户同意后第三方返回的一次性凭证，有效期很短（通常10分钟） | 像一次性 ticket |
| `state` | 随机串，防 CSRF 攻击，回调时原样带回校验 | 像 CSRF token |
| `access_token` | 用 code 换来的访问令牌，代表用户授权 | 像 JWT |

**为什么需要 `state`？** 防止攻击者伪造回调。流程是：跳转前生成随机 `state` 存起来（本模块存 Redis），回调时校验 `state` 是否一致，不一致就拒绝。本模块用 `AuthStateUtils.createState()` 生成，用 Redis 缓存校验。

> 💡 前端类比：`state` 的作用和你在 axios 里发请求带的 `X-CSRF-Token` 一样，都是防跨站请求伪造。

---

## 三、项目结构

```
demo-social/
├── pom.xml
└── src/main/
    ├── java/com/xkcoding/social/
    │   ├── SpringBootDemoSocialApplication.java   # 启动类
    │   └── controller/
    │       └── OauthController.java                # 第三方登录控制器
    └── resources/
        └── application.yml                         # 配置(各平台密钥 + Redis + JustAuth)
```

结构非常简洁——核心就一个 `OauthController`，因为复杂的 OAuth2 流程被 JustAuth 和它的 Spring Boot Starter 封装了，你只需要配置 + 调几个方法。

---

## 四、逐行拆解 pom.xml

```xml
<properties>
    <justauth-spring-boot.version>1.1.0</justauth-spring-boot.version>
</properties>

<dependencies>
    <!-- 1. Web 起步依赖 -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-web</artifactId>
    </dependency>

    <!-- 2. Redis 起步依赖：用于缓存 state -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-data-redis</artifactId>
    </dependency>

    <!-- 3. 对象池，使用 redis 时必须引入 -->
    <dependency>
        <groupId>org.apache.commons</groupId>
        <artifactId>commons-pool2</artifactId>
    </dependency>

    <!-- 4. JustAuth 的 Spring Boot Starter（核心） -->
    <dependency>
        <groupId>com.xkcoding</groupId>
        <artifactId>justauth-spring-boot-starter</artifactId>
        <version>${justauth-spring-boot.version}</version>
    </dependency>

    <!-- 5. Lombok -->
    <dependency>
        <groupId>org.projectlombok</groupId>
        <artifactId>lombok</artifactId>
        <optional>true</optional>
    </dependency>

    <!-- 6. Guava、Hutool 工具类 -->
    <dependency>
        <groupId>com.google.guava</groupId>
        <artifactId>guava</artifactId>
    </dependency>
    <dependency>
        <groupId>cn.hutool</groupId>
        <artifactId>hutool-all</artifactId>
    </dependency>
</dependencies>
```

**关键依赖解读：**

1. `spring-boot-starter-web`：提供 Web 能力，接收回调请求。
2. `spring-boot-starter-data-redis`：用 Redis 存储 `state`，防止 CSRF。分布式部署时多个实例共享 state。
3. `commons-pool2`：Lettuce 连接池依赖，用 Redis 连接池时需要。
4. `justauth-spring-boot-starter`：**本模块的灵魂**。它做了两件事：
   - 根据 `application.yml` 里的 `justauth.type.*` 配置，自动创建各平台的 `AuthRequest` Bean。
   - 提供 `AuthRequestFactory` 工厂，注入后可按平台类型获取对应的 `AuthRequest`。
5. Lombok、Guava、Hutool：辅助工具。

> 💡 前端类比：`justauth-spring-boot-starter` 就像一个"第三方登录 SDK 的统一适配层"，类似前端里把多个登录 provider 封装成统一接口的库（如 `next-auth` 把 GitHub/Google/Twitter 登录统一成一套 API）。

---

## 五、逐行拆解配置文件 application.yml

```yaml
server:
  port: 8080
  servlet:
    context-path: /demo

spring:
  redis:
    host: localhost
    timeout: 10000ms
    lettuce:
      pool:
        max-active: 8
        max-wait: -1ms
        max-idle: 8
        min-idle: 0
  cache:
    type: redis

justauth:
  enabled: true
  type:
    qq:
      client-id: 10******85
      client-secret: 1f7d************************d629e
      redirect-uri: http://oauth.xkcoding.com/demo/oauth/qq/callback
    github:
      client-id: 2d25******d5f01086
      client-secret: 5a2919b************************d7871306d1
      redirect-uri: http://oauth.xkcoding.com/demo/oauth/github/callback
    wechat:
      client-id: wxdcb******4ff4
      client-secret: b4e9dc************************a08ed6d
      redirect-uri: http://oauth.xkcoding.com/demo/oauth/wechat/callback
    google:
      client-id: 716******17-...
      client-secret: 9IBorn************7-E
      redirect-uri: http://oauth.xkcoding.com/demo/oauth/google/callback
    microsoft:
      client-id: 7bdce8...e194ad76c1b
      client-secret: Iu0zZ4...tl9PWan_.
      redirect-uri: https://oauth.xkcoding.com/demo/oauth/microsoft/callback
    mi:
      client-id: 288...2994
      client-secret: nFeTt89...==
      redirect-uri: http://oauth.xkcoding.com/demo/oauth/mi/callback
    wechat_enterprise:
      client-id: ww58...fbc
      client-secret: 8G6PCr00j...AyzaPc78
      redirect-uri: http://oauth.xkcoding.com/demo/oauth/wechat_enterprise/callback
      agent-id: 1******2
  cache:
    type: redis
    prefix: 'SOCIAL::STATE::'
    timeout: 1h
```

### 5.1 Redis 配置

- `spring.redis`：Redis 连接信息，用于存 `state`。
- `lettuce.pool`：Lettuce 连接池参数。Lettuce 是 Spring Boot 2.x 默认的 Redis 客户端（基于 Netty，线程安全）。
- `spring.cache.type: redis`：Spring Cache 用 Redis 作为后端。

### 5.2 JustAuth 配置（核心）

`justauth` 是 Starter 的配置前缀，分三部分：

| 配置项 | 作用 |
| --- | --- |
| `justauth.enabled: true` | 启用 JustAuth 自动配置 |
| `justauth.type.{平台}` | 每个平台的 `client-id`、`client-secret`、`redirect-uri` |
| `justauth.cache` | state 缓存配置：`type`（redis/default）、`prefix`（key 前缀）、`timeout`（过期时间） |

**每个平台三个必填项：**

- `client-id`：在第三方后台注册应用后拿到的应用 ID。
- `client-secret`：应用的密钥（**生产环境必须用环境变量注入，不能写死在 yml 里**）。
- `redirect-uri`：授权后的回调地址，**必须和第三方后台登记的完全一致**。

注意 `wechat_enterprise`（企业微信）多了一个 `agent-id`（应用 ID），因为企业微信的 OAuth 比公众号多一层应用维度。

### 5.3 state 缓存配置

```yaml
justauth:
  cache:
    type: redis              # 用 Redis 存 state
    prefix: 'SOCIAL::STATE::' # Redis key 前缀
    timeout: 1h              # state 过期时间1小时
```

- `type: redis`：生产环境用 Redis，多实例共享 state。开发测试可用 `default`（内存缓存，单机够用）。
- `prefix`：所有 state 的 key 都加这个前缀，避免和其他业务 key 冲突。
- `timeout`：state 有效期，超过自动失效（OAuth2 规范建议 state 短命）。

> 💡 前端类比：state 缓存就像你在 SPA 里把 OAuth state 临时存 sessionStorage，回调后取出校验再删掉。区别是这里存 Redis，跨实例共享。

---

## 六、逐行拆解启动类

```java
@SpringBootApplication
public class SpringBootDemoSocialApplication {
    public static void main(String[] args) {
        SpringApplication.run(SpringBootDemoSocialApplication.class, args);
    }
}
```

启动类极简，没有任何特殊注解。`justauth-spring-boot-starter` 通过 Spring Boot 自动配置机制，在启动时根据 yml 配置自动注册各平台的 `AuthRequest` 和 `AuthRequestFactory` Bean——你什么都不用声明。

这是 Spring Boot"约定优于配置"+ Starter 的典型体现：引依赖 + 写配置 = 自动可用。

---

## 七、逐行拆解 OauthController（核心）

```java
@Slf4j
@RestController
@RequestMapping("/oauth")
@RequiredArgsConstructor(onConstructor_ = @Autowired)
public class OauthController {
    private final AuthRequestFactory factory;

    /**
     * 登录类型
     */
    @GetMapping
    public Map<String, String> loginType() {
        List<String> oauthList = factory.oauthList();
        return oauthList.stream()
            .collect(Collectors.toMap(
                oauth -> oauth.toLowerCase() + "登录",
                oauth -> "http://oauth.xkcoding.com/demo/oauth/login/" + oauth.toLowerCase()
            ));
    }

    /**
     * 登录
     */
    @RequestMapping("/login/{oauthType}")
    public void renderAuth(@PathVariable String oauthType, HttpServletResponse response) throws IOException {
        AuthRequest authRequest = factory.get(getAuthSource(oauthType));
        response.sendRedirect(authRequest.authorize(oauthType + "::" + AuthStateUtils.createState()));
    }

    /**
     * 登录成功后的回调
     */
    @RequestMapping("/{oauthType}/callback")
    public AuthResponse login(@PathVariable String oauthType, AuthCallback callback) {
        AuthRequest authRequest = factory.get(getAuthSource(oauthType));
        AuthResponse response = authRequest.login(callback);
        log.info("【response】= {}", JSONUtil.toJsonStr(response));
        return response;
    }

    private AuthSource getAuthSource(String type) {
        if (StrUtil.isNotBlank(type)) {
            return AuthSource.valueOf(type.toUpperCase());
        } else {
            throw new RuntimeException("不支持的类型");
        }
    }
}
```

### 7.1 类级注解

- `@Slf4j`：Lombok 注入 `log` 对象，用于打日志。
- `@RestController`：返回 JSON。
- `@RequestMapping("/oauth")`：类级路径前缀，所有接口都以 `/oauth` 开头。
- `@RequiredArgsConstructor(onConstructor_ = @Autowired)`：Lombok 生成构造器并加 `@Autowired`，实现构造器注入。`AuthRequestFactory factory` 由 Starter 自动注册，直接注入即可用。

### 7.2 接口一：`GET /oauth` —— 列出所有登录方式

```java
@GetMapping
public Map<String, String> loginType() {
    List<String> oauthList = factory.oauthList();
    return oauthList.stream().collect(Collectors.toMap(...));
}
```

- `factory.oauthList()`：返回所有已配置的平台名列表（如 `["QQ", "GITHUB", "WECHAT", ...]`）。
- 用 Java Stream 把列表转成 Map：key 是 `"github登录"`，value 是登录链接。
- 前端拿到这个 Map 就能渲染登录按钮列表。

> 💡 前端类比：这相当于一个"登录方式清单接口"，前端拿到后 `v-for` 渲染按钮，每个按钮的 `href` 指向对应登录链接。

### 7.3 接口二：`/oauth/login/{oauthType}` —— 发起授权（跳转）

```java
@RequestMapping("/login/{oauthType}")
public void renderAuth(@PathVariable String oauthType, HttpServletResponse response) throws IOException {
    AuthRequest authRequest = factory.get(getAuthSource(oauthType));
    response.sendRedirect(authRequest.authorize(oauthType + "::" + AuthStateUtils.createState()));
}
```

这是 OAuth2 流程的**第 1 步**：

1. `@PathVariable String oauthType`：从路径取平台类型，如 `qq`、`github`。
2. `getAuthSource(oauthType)`：把字符串 `"qq"` 转成枚举 `AuthSource.QQ`（JustAuth 用枚举标识各平台）。
3. `factory.get(...)`：从工厂拿到该平台的 `AuthRequest`。
4. `authRequest.authorize(state)`：**核心方法**，返回第三方平台的授权页 URL，已自动拼好 `client_id`、`redirect_uri`、`state`、`scope` 等参数。
5. `response.sendRedirect(...)`：让浏览器重定向到该 URL，用户就看到第三方的授权页。

**state 的构造：** `oauthType + "::" + AuthStateUtils.createState()`。这里把平台类型和随机串用 `::` 拼接，回调时能从 state 里解析出是哪个平台发起的（巧妙复用 state 字段携带信息）。`AuthStateUtils.createState()` 生成 UUID 随机串。

> ⚠️ 注意：这个方法返回 `void`，靠 `response.sendRedirect` 直接控制 HTTP 响应（302 重定向），不是返回数据。这是发起 OAuth2 跳转的标准写法。

### 7.4 接口三：`/oauth/{oauthType}/callback` —— 回调处理

```java
@RequestMapping("/{oauthType}/callback")
public AuthResponse login(@PathVariable String oauthType, AuthCallback callback) {
    AuthRequest authRequest = factory.get(getAuthSource(oauthType));
    AuthResponse response = authRequest.login(callback);
    log.info("【response】= {}", JSONUtil.toJsonStr(response));
    return response;
}
```

这是 OAuth2 流程的**第 4、5 步**（用户授权后，第三方带 code 回调到这里）：

1. `@PathVariable String oauthType`：从路径知道是哪个平台回调。
2. `AuthCallback callback`：JustAuth 定义的回调参数对象，自动绑定 URL 上的 `code`、`state` 等参数（Spring MVC 的参数绑定机制）。
3. `authRequest.login(callback)`：**核心方法**，一行代码完成"用 code 换 token、再用 token 换用户信息"两步，返回 `AuthResponse`。
4. `AuthResponse` 包含用户信息（`AuthUser`：uuid、username、nickname、avatar、gender 等）和 token 信息。

> 💡 前端类比：这个回调接口就像你前端 OAuth 流程里的 `redirect_uri` 页面，但它在前端只负责把 URL 上的 code 发给后端，真正换 token 的活在这里由后端完成。

### 7.5 辅助方法：`getAuthSource`

```java
private AuthSource getAuthSource(String type) {
    if (StrUtil.isNotBlank(type)) {
        return AuthSource.valueOf(type.toUpperCase());
    } else {
        throw new RuntimeException("不支持的类型");
    }
}
```

把字符串 `"qq"` 转成枚举 `AuthSource.QQ`。`AuthSource` 是 JustAuth 定义的平台枚举，包含各平台的授权 URL、token URL、用户信息 URL 等元数据。

> ⚠️ 这里用 `AuthSource.valueOf(type.toUpperCase())`，如果传了不存在的平台名会抛 `IllegalArgumentException`。生产环境应该捕获并返回友好错误，而不是直接抛 RuntimeException。

---

## 八、运行与验证

### 8.1 环境准备

本模块需要：
1. **Redis 环境**：用于存 state（没有的话把 `justauth.cache.type` 改成 `default` 用内存缓存）。
2. **公网可访问的回调地址**：第三方授权后要回调你的应用，所以 `redirect-uri` 必须公网可达。本地开发用内网穿透（frp / ngrok / 花生壳）。
3. **各平台应用密钥**：在 QQ互联、GitHub Settings、微信开放平台等后台注册应用，拿到 client-id / client-secret，登记回调地址。

### 8.2 启动

```sh
mvn spring-boot:run
```

### 8.3 测试流程

1. 访问 `http://oauth.xkcoding.com/demo/oauth`，拿到登录方式列表。
2. 点击 `github登录`，跳转到 GitHub 授权页。
3. 在 GitHub 点"Authorize"，回调到 `/demo/oauth/github/callback`。
4. 接口返回用户信息 JSON：

```json
{
  "code": 2000,
  "data": {
    "uuid": "12345",
    "username": "yangkai",
    "nickname": "Yangkai",
    "avatar": "https://avatars.githubusercontent.com/u/12345",
    "blog": "https://xkcoding.com",
    "source": "GITHUB",
    "token": { "accessToken": "gho_xxx", "expireIn": 2592000 }
  }
}
```

> 💡 Google 登录可能因网络问题失败，需自行解决访问。

---

## 九、动手练习

1. **接入一个新平台**：在 yml 的 `justauth.type` 下加一个 `gitee`（码云）配置，去 https://gitee.com/oauth/applications 注册应用，验证能登录。
2. **改用内存缓存**：把 `justauth.cache.type` 改成 `default`，去掉 Redis 依赖，验证单机下 state 仍能校验。
3. **处理登录后业务**：在 callback 接口里，拿到 `AuthResponse` 后查本地用户表，不存在则自动注册，存在则更新登录态，最后签发 JWT 返回前端。
4. **加 state 校验日志**：在 renderAuth 和 callback 里分别打印 state，观察"发起时的 state"和"回调时的 state"是否一致。
5. **错误处理**：用户在授权页点"拒绝授权"时，回调会带 `error` 参数，改造 callback 方法处理这种拒绝场景，返回友好提示。
6. **安全加固**：把 yml 里的 `client-secret` 全部改成 `${XX_CLIENT_SECRET}` 环境变量占位，用环境变量注入，验证仍能工作。

---

## 十、本模块知识点总结（结合实际开发详解）

第三方登录是现代 Web 应用的标配功能。下面把核心知识点放到真实开发场景里讲透。

### 10.1 OAuth2 授权码流程：必须烂熟于心

**实际开发中怎么用？**

第三方登录、单点登录（SSO）、开放 API 授权，底层都是 OAuth2 授权码流程。理解这 5 步是后端工程师的基本功：

1. 用户点登录 → 后端生成 state 存起来，重定向到第三方授权页（带 client_id、redirect_uri、state）。
2. 用户在第三方点同意 → 第三方带 code 和 state 回调 redirect_uri。
3. 后端校验 state → 用 code + client_secret 换 access_token（这步在后端，secret 不外泄）。
4. 后端用 access_token 调第三方 API 拿用户信息。
5. 后端根据用户信息签发自己的登录态（JWT/Session）返回前端。

**最佳实践：**

- **state 必须存且必须校验**：不存 state 等于裸奔，攻击者可伪造回调让用户登录攻击者账号。本模块用 Redis 存 state 是正确做法。
- **client_secret 永远不进前端**：换 token 这步必须后端做。前端只负责发起跳转和接收最终登录态。
- **access_token 不要下发给前端**：用 access_token 换完用户信息后，签发你自己的 JWT 给前端，access_token 留后端即可（除非前端要直接调第三方 API）。

**常见坑：**

- `redirect_uri` 和第三方后台登记的不完全一致（多个斜杠、http vs https）→ 第三方报"redirect_uri mismatch"。
- state 用内存存（单机 Map），多实例部署时 A 实例发起、B 实例回调，state 找不到 → 必须用 Redis 等共享存储。
- 把 client_secret 写在前端代码里 → 密钥泄露，被冒用。

> 💡 前端类比：如果你用过 `next-auth` / `passport`，它们在后端做的就是这套流程。前端只负责跳转和拿最终 token。

### 10.2 JustAuth 的设计：统一抽象屏蔽平台差异

**为什么 JustAuth 值得用？**

各平台 OAuth2 实现细节差异巨大：

- GitHub 用标准 OAuth2，返回 JSON。
- QQ 的 token 接口返回 `application/x-www-form-urlencoded` 格式（不是 JSON）。
- 微信的 access_token 接口要带 `appid` 和 `secret`，而不是 `client_id`。
- 微软返回的 token 是 JWT，用户信息接口要带特定 scope。

JustAuth 用 `AuthSource` 枚举 + `AuthRequest` 接口把这些差异全部封装，你只需要：

```java
AuthRequest authRequest = factory.get(AuthSource.GITHUB);
String authorizeUrl = authRequest.authorize(state);    // 各平台自动拼正确参数
AuthResponse response = authRequest.login(callback);    // 各平台自动换 token、取用户信息
```

**实际开发的最佳实践：**

- **用 Starter 而非裸 SDK**：`justauth-spring-boot-starter` 把配置化、Bean 注册都做好了，比直接用 JustAuth SDK 更省事。
- **平台类型用枚举不用字符串**：`AuthSource.QQ` 比 `"qq"` 安全，编译期就能发现错误。
- **新平台只需加配置**：JustAuth 已支持几十个平台，接新平台时 yml 加一段配置即可，不用写代码。

**常见坑：**

- JustAuth 版本和平台 API 变化：某平台升级 OAuth 接口后，老版本 JustAuth 可能不兼容，需升级 JustAuth。
- 企业微信、钉钉等需要额外参数（agent-id），配置时容易漏。

### 10.3 state 缓存策略：Redis vs 内存

**实际开发怎么选？**

| 缓存类型 | 配置 | 适用场景 | 特点 |
| --- | --- | --- | --- |
| `default`（内存） | `justauth.cache.type: default` | 本地开发、单机部署 | 简单，但多实例不共享 |
| `redis` | `justauth.cache.type: redis` | 生产、集群部署 | 多实例共享，需 Redis 环境 |
| 自定义 | 实现 `AuthStateCache` 接口 | 特殊存储（如 Memcached） | 灵活但需自己写 |

**最佳实践：**

- 开发用 `default`（省去 Redis 依赖），生产用 `redis`（多实例共享）。
- state 过期时间设短（本模块 1h 合理，OAuth 规范建议不超过 10 分钟）。
- key 加前缀（`SOCIAL::STATE::`）避免和其他业务 key 冲突。

**常见坑：**

- 用 `default` 部署到集群，导致 state 校验随机失败（有的请求打到别的实例）。
- state 永不过期（没设 timeout），Redis 堆积垃圾 key。

### 10.4 回调地址与内网穿透：本地开发的拦路虎

**为什么这是坑？**

OAuth2 要求 `redirect-uri` 公网可达，但本地开发跑在 `localhost:8080`，第三方回调不了。解决方案是**内网穿透**：把公网域名映射到本地端口。

**常用工具：**

| 工具 | 特点 |
| --- | --- |
| frp | 开源，需自己有公网服务器，灵活 |
| ngrok | 开箱即用，免费版域名随机变化 |
| 花生壳 / natapp | 国内服务，稳定但收费 |

**最佳实践：**

- 用固定域名的内网穿透（frp + 自己域名），避免 ngrok 随机域名导致每次改 redirect-uri。
- `redirect-uri` 配置成公网域名，第三方后台登记的也用这个域名。
- 生产环境直接用生产域名，不需要穿透。

**常见坑：**

- redirect-uri 用 `localhost`，第三方后台不允许登记 localhost → 必须用公网域名。
- http vs https：微软等平台要求 https 回调，本地用 http 会失败。

### 10.5 密钥管理：client-secret 绝不能进 Git

**实际开发的密钥管理：**

本 demo 为了演示把 `client-secret` 写在 yml 里（还做了脱敏），**生产环境绝不能这样**。正确做法：

```yaml
justauth:
  type:
    github:
      client-id: ${GITHUB_CLIENT_ID}
      client-secret: ${GITHUB_CLIENT_SECRET}
      redirect-uri: ${OAUTH_REDIRECT_URI}
```

用环境变量占位，运行时从环境注入。部署时：

- 物理机/虚拟机：用 systemd 的 EnvironmentFile 或环境变量。
- Docker：`docker run -e GITHUB_CLIENT_SECRET=xxx` 或 docker secrets。
- K8s：用 Secret 挂载环境变量。
- 配置中心：Nacos/Apollo 管理密钥，支持热更新。

**常见坑：**

- 密钥提交到 Git，公开仓库直接泄露 → 用 `.gitignore` 或环境变量，定期轮换密钥。
- 多环境密钥不同（dev/test/prod 的 GitHub App 不同），用 Profile + 环境变量区分。

### 10.6 登录后的业务闭环：拿到用户信息之后做什么

**本模块只演示到拿到 `AuthResponse`，但真实业务还要做闭环：**

1. **查本地用户**：用 `source + uuid`（如 `GITHUB::12345`）查本地用户表，这是第三方用户的唯一标识。
2. **首次登录自动注册**：本地没有就创建用户，把第三方返回的昵称、头像存入。
3. **已存在则更新**：更新头像/昵称（用户可能在第三方改了）。
4. **绑定关系**：一个本地用户可绑定多个第三方（既绑 GitHub 又绑微信），用 `user_oauth` 关联表。
5. **签发登录态**：生成 JWT 返回前端，前端存 localStorage，后续请求带 Authorization 头。

**代码骨架：**

```java
@RequestMapping("/{oauthType}/callback")
public AuthResponse login(@PathVariable String oauthType, AuthCallback callback) {
    AuthRequest authRequest = factory.get(getAuthSource(oauthType));
    AuthResponse response = authRequest.login(callback);
    if (response.getCode() == 2000) {
        AuthUser authUser = response.getData();
        // 1. 查本地用户
        User localUser = userService.findByOauth(authUser.getSource(), authUser.getUuid());
        if (localUser == null) {
            // 2. 不存在则注册
            localUser = userService.registerByOauth(authUser);
        } else {
            // 3. 存在则更新信息
            userService.updateOauthInfo(localUser, authUser);
        }
        // 4. 签发 JWT
        String token = jwtUtil.generate(localUser.getId());
        return new AuthResponse(2000, token);
    }
    return response;
}
```

**最佳实践：**

- 第三方用户的唯一标识用 `source + uuid`，不要用昵称（会变）或 username（可能重复）。
- 绑定关系单独建表，支持一个用户绑多个第三方。
- JWT 里只放 userId，不放敏感信息。

**常见坑：**

- 用第三方昵称做用户名，用户改了昵称后登录不上。
- 没做绑定关系，用户用 GitHub 登录后又用微信登录，创建了两个账号。
- 把 access_token 当登录态返给前端，access_token 过期后用户"掉线"——应该用自己的 JWT。

### 10.7 安全加固清单

生产环境第三方登录要做的安全措施：

| 措施 | 说明 |
| --- | --- |
| state 校验 | 防 CSRF，必须做 |
| client_secret 环境变量 | 防泄露 |
| redirect-uri 白名单 | 回调地址必须匹配预期，防开放重定向 |
| access_token 不下发前端 | 防泄露 |
| 限制 scope | 只申请必要权限（如只读用户信息），不要申请写权限 |
| 日志脱敏 | token、secret 不要打全量日志 |
| 频率限制 | 防止回调接口被刷 |
| HTTPS | 全站 HTTPS，防止 token 被中间人窃取 |

---

> 📌 **学习建议**：第三方登录是 OAuth2 协议的最佳实践场景，建议你把授权码流程的 5 步画在纸上，对着本模块代码走一遍，彻底理解"为什么 state 要存、为什么 secret 不能进前端、为什么换 token 要在后端"。这套理解不仅适用于 JustAuth，也适用于 Spring Security OAuth、Keycloak、自建 SSO。另外，第三方登录只是"认证"（你是谁），后续还要接"授权"（你能做什么），这正是下一个权限模块的延续。
