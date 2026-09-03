# 07 - Spring Boot 统一异常处理

> 对应项目模块：`demo-exception-handler`
> 前置知识：已学完前 6 个模块，了解 `@RestController`、`@GetMapping`、`application.yml`、Lombok 基本用法
> 学习目标：掌握 Spring Boot 统一异常处理机制，能区分 API 接口（返回 JSON）和页面请求（跳转错误页）两种异常处理方式，理解 `@ControllerAdvice` + `@ExceptionHandler` 的工作原理。

---

## 一、本模块要解决什么问题？

在 HelloWorld 模块里，我们故意访问一个不存在的路径，Spring Boot 会返回一个默认的白板 404 错误页。这在真实项目里是**不可接受**的：

- **前端无法解析**：前端 axios/fetch 期望拿到统一的 JSON 格式 `{ code, message, data }`，结果后端返回一段 HTML 或一段乱七八糟的错误堆栈，前端无法处理，用户看到"白屏"或"undefined"。
- **信息泄露**：直接把异常堆栈抛给前端，可能暴露数据库表名、SQL 语句、内部路径，是安全隐患。
- **体验差**：用户看到一串英文报错或白板页面，完全不知道发生了什么。
- **后端难维护**：异常处理散落在各个 Controller 里，每个方法都 try-catch，代码臃肿、风格不一。

本模块演示如何用 `@ControllerAdvice` + `@ExceptionHandler` 做**集中式统一异常处理**，并区分两种场景：

1. **API 接口异常**：返回统一 JSON 格式 `{ code, message, data }`。
2. **页面请求异常**：统一跳转到一个友好的错误页面。

> 💡 前端类比：这就像 axios 的响应拦截器 `axios.interceptors.response.use(res => res, err => { 统一处理错误 })`。后端在"出口"统一兜底所有异常，前端在"入口"统一处理响应，两边各有一个拦截层。

---

## 二、项目结构

```
demo-exception-handler/
└── src/main/
    ├── java/com/xkcoding/exception/handler/
    │   ├── SpringBootDemoExceptionHandlerApplication.java  # 启动类
    │   ├── constant/
    │   │   └── Status.java                 # 状态码枚举（code + message）
    │   ├── exception/
    │   │   ├── BaseException.java         # 异常基类
    │   │   ├── JsonException.java         # JSON 接口异常
    │   │   └── PageException.java         # 页面请求异常
    │   ├── handler/
    │   │   └── DemoExceptionHandler.java  # 统一异常处理器（核心）
    │   ├── model/
    │   │   └── ApiResponse.java           # 统一响应封装
    │   └── controller/
    │       └── TestController.java         # 测试控制器（故意抛异常）
    └── resources/
        ├── application.yml                 # 配置（含 Thymeleaf 配置）
        └── templates/
            └── error.html                  # 错误页面模板
```

注意分层：`constant`（常量）、`exception`（自定义异常）、`handler`（处理器）、`model`（数据模型）、`controller`（控制器）。这是 Spring Boot 项目的典型分层结构，每层职责单一。

---

## 三、pom.xml 依赖

```xml
<dependencies>
    <!-- Thymeleaf 模板引擎：用于渲染错误页面 -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-thymeleaf</artifactId>
    </dependency>

    <!-- Web 起步依赖 -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-web</artifactId>
    </dependency>

    <!-- 测试 -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-test</artifactId>
        <scope>test</scope>
    </dependency>

    <!-- Lombok -->
    <dependency>
        <groupId>org.projectlombok</groupId>
        <artifactId>lombok</artifactId>
        <optional>true</optional>
    </dependency>
</dependencies>
```

相比前几个模块，新增了 `spring-boot-starter-thymeleaf`。Thymeleaf 是一种服务端模板引擎，用于渲染 HTML 页面。本模块用它来渲染错误页 `error.html`。

> 💡 前端类比：Thymeleaf 类似于早期的 EJS/Pug（服务端渲染 HTML），在后端把数据填进 HTML 模板再发给浏览器。现代前后端分离项目里，Thymeleaf 主要用于错误页、邮件模板等少量场景。模板引擎本身会在 `demo-template-thymeleaf` 模块专门讲，这里只需知道它能渲染 `error.html`。

---

## 四、状态码枚举 `Status`

`constant/Status.java`：

```java
@Getter
public enum Status {
    OK(200, "操作成功"),
    UNKNOWN_ERROR(500, "服务器出错啦");

    private Integer code;
    private String message;

    Status(Integer code, String message) {
        this.code = code;
        this.message = message;
    }
}
```

用枚举集中管理状态码和提示信息，好处：

- **避免魔法数字**：代码里写 `Status.UNKNOWN_ERROR` 比写 `500` 可读性强得多。
- **统一维护**：所有状态码在一处定义，新增、修改方便。
- **类型安全**：编译期就能发现拼写错误，不像字符串容易写错。

> 💡 前端类比：这就像前端定义 `export const STATUS_CODE = { OK: 200, UNKNOWN_ERROR: 500 }` 常量对象，但 Java 的 enum 更严格，是真正的类型。

实际项目里这个枚举会很长，按业务分类定义几十上百个状态码（用户模块、订单模块、支付模块……）。

---

## 五、自定义异常体系

本模块定义了一个异常继承链：`BaseException` ← `JsonException` / `PageException`。

### 5.1 异常基类 `BaseException`

```java
@Data
@EqualsAndHashCode(callSuper = true)
public class BaseException extends RuntimeException {
    private Integer code;
    private String message;

    public BaseException(Status status) {
        super(status.getMessage());
        this.code = status.getCode();
        this.message = status.getMessage();
    }

    public BaseException(Integer code, String message) {
        super(message);
        this.code = code;
        this.message = message;
    }
}
```

关键点：

1. **继承 `RuntimeException`**：Java 异常分 `Checked Exception`（编译期强制处理，如 `IOException`）和 `Unchecked Exception`（运行时异常，如 `NullPointerException`）。自定义业务异常通常继承 `RuntimeException`，这样方法签名上不用写 `throws`，代码更干净。
2. **携带 `code` 和 `message`**：业务异常不只是"出错了"，还要告诉调用方"错在哪、错误码是多少"，所以扩展了这两个字段。
3. **两个构造器**：一个传 `Status` 枚举（推荐），一个直接传 code/message（灵活）。
4. `@EqualsAndHashCode(callSuper = true)`：Lombok 生成 equals/hashCode 时把父类（`RuntimeException`）的字段也算进来。

> 💡 前端类比：这像自定义一个 `BusinessError extends Error`，里面带 `code` 和 `message`，throw 出来后由上层统一 catch。

### 5.2 两个子类 `JsonException` 和 `PageException`

```java
@Getter
public class JsonException extends BaseException {
    public JsonException(Status status) { super(status); }
    public JsonException(Integer code, String message) { super(code, message); }
}

@Getter
public class PageException extends BaseException {
    public PageException(Status status) { super(status); }
    public PageException(Integer code, String message) { super(code, message); }
}
```

两个子类结构几乎一样，只是类型不同。**为什么要分两个？** 因为异常处理器要根据异常类型决定"返回 JSON 还是跳转页面"，用不同类型区分场景。这是**多态**的典型应用：同一个基类，不同子类走不同处理逻辑。

---

## 六、统一响应封装 `ApiResponse`

`model/ApiResponse.java`：

```java
@Data
public class ApiResponse {
    private Integer code;
    private String message;
    private Object data;

    private ApiResponse() {}

    private ApiResponse(Integer code, String message, Object data) {
        this.code = code;
        this.message = message;
        this.data = data;
    }

    public static ApiResponse of(Integer code, String message, Object data) {
        return new ApiResponse(code, message, data);
    }

    public static ApiResponse ofSuccess(Object data) {
        return ofStatus(Status.OK, data);
    }

    public static ApiResponse ofMessage(String message) {
        return of(Status.OK.getCode(), message, null);
    }

    public static ApiResponse ofStatus(Status status) {
        return ofStatus(status, null);
    }

    public static ApiResponse ofStatus(Status status, Object data) {
        return of(status.getCode(), status.getMessage(), data);
    }

    public static <T extends BaseException> ApiResponse ofException(T t, Object data) {
        return of(t.getCode(), t.getMessage(), data);
    }

    public static <T extends BaseException> ApiResponse ofException(T t) {
        return ofException(t, null);
    }
}
```

### 6.1 设计要点

1. **构造器私有**：外部不能 `new ApiResponse()`，只能通过静态工厂方法创建，保证创建方式受控。
2. **静态工厂方法**：`ofSuccess`、`ofStatus`、`ofException` 等，方法名表意清晰，调用方代码可读性强。
3. **泛型约束**：`<T extends BaseException>` 限定 `ofException` 只接受业务异常，类型安全。

### 6.2 为什么用静态工厂而不是构造器？

```java
// 静态工厂：语义清晰
return ApiResponse.ofSuccess(user);        // 一看就知道是"成功返回数据"
return ApiResponse.ofException(ex);        // 一看就知道是"异常返回"

// 直接构造器：语义模糊
return new ApiResponse(200, "操作成功", user);   // 200 是啥？得查枚举
```

> 💡 前端类比：这像前端封装 `createSuccessResp(data)`、`createErrorResp(code, msg)` 工厂函数，比直接 `new Resp(...)` 语义清晰。

---

## 七、统一异常处理器（核心）

`handler/DemoExceptionHandler.java`：

```java
@ControllerAdvice
@Slf4j
public class DemoExceptionHandler {
    private static final String DEFAULT_ERROR_VIEW = "error";

    @ExceptionHandler(value = JsonException.class)
    @ResponseBody
    public ApiResponse jsonErrorHandler(JsonException exception) {
        log.error("【JsonException】:{}", exception.getMessage());
        return ApiResponse.ofException(exception);
    }

    @ExceptionHandler(value = PageException.class)
    public ModelAndView pageErrorHandler(PageException exception) {
        log.error("【DemoPageException】:{}", exception.getMessage());
        ModelAndView view = new ModelAndView();
        view.addObject("message", exception.getMessage());
        view.setViewName(DEFAULT_ERROR_VIEW);
        return view;
    }
}
```

这是本模块的核心，逐个注解看。

### 7.1 `@ControllerAdvice` —— 全局控制器增强

`@ControllerAdvice` 把这个类注册成一个"全局拦截器"，它会拦截所有 `@Controller` 抛出的异常。相当于在每个 Controller 上都加了一遍异常处理逻辑，但集中写在一处。

> 💡 前端类比：这就像 axios 的全局响应拦截器，注册一次，所有请求的响应都经过它。`@ControllerAdvice` 是 Spring MVC 层面的全局拦截器。

### 7.2 `@ExceptionHandler` —— 指定处理哪种异常

- `@ExceptionHandler(value = JsonException.class)`：这个方法处理 `JsonException` 类型的异常。
- `@ExceptionHandler(value = PageException.class)`：这个方法处理 `PageException` 类型的异常。

当 Controller 抛出 `JsonException`，Spring 会自动找到对应的 `jsonErrorHandler` 方法执行；抛 `PageException` 则走 `pageErrorHandler`。**按异常类型分发**，这是多态的体现。

### 7.3 两种处理方式的区别

| 维度 | `jsonErrorHandler` | `pageErrorHandler` |
| --- | --- | --- |
| 处理的异常 | `JsonException` | `PageException` |
| 注解 | `@ExceptionHandler` + `@ResponseBody` | `@ExceptionHandler` |
| 返回类型 | `ApiResponse`（对象） | `ModelAndView`（视图） |
| 效果 | 对象序列化成 JSON 返回 | 跳转到 `error` 模板页面 |
| 适用场景 | API 接口（前后端分离） | 传统服务端渲染页面 |

- `@ResponseBody` 让返回的对象直接序列化成 JSON 写进响应体。
- `ModelAndView` 是 Spring MVC 的视图模型对象，`setViewName("error")` 指定跳转到 `templates/error.html`，`addObject("message", ...)` 把数据传给模板。

### 7.4 `@Slf4j` —— 日志

Lombok 的 `@Slf4j` 自动注入一个 `log` 对象，可以直接 `log.error(...)` 记录日志。异常处理时一定要记日志，否则线上出问题没法排查。

---

## 八、测试控制器

`controller/TestController.java`：

```java
@Controller
public class TestController {

    @GetMapping("/json")
    @ResponseBody
    public ApiResponse jsonException() {
        throw new JsonException(Status.UNKNOWN_ERROR);
    }

    @GetMapping("/page")
    public ModelAndView pageException() {
        throw new PageException(Status.UNKNOWN_ERROR);
    }
}
```

注意这里用的是 `@Controller`（不是 `@RestController`），因为 `/page` 要返回视图。`/json` 单独加了 `@ResponseBody` 返回 JSON。

两个方法都是**直接抛异常**，没有 try-catch。异常抛出后，`DemoExceptionHandler` 会自动接住并处理。这就是统一异常处理的精髓——**业务代码只管抛，处理逻辑集中在一处**。

---

## 九、配置文件与错误页

### 9.1 `application.yml`

```yaml
server:
  port: 8080
  servlet:
    context-path: /demo
spring:
  thymeleaf:
    cache: false        # 关闭模板缓存（开发期方便调试）
    mode: HTML
    encoding: UTF-8
    servlet:
      content-type: text/html
```

`spring.thymeleaf.cache: false` 在开发时关闭缓存，改了模板立刻生效；生产环境要设成 `true` 提升性能。

### 9.2 `templates/error.html`

```html
<!DOCTYPE html>
<html xmlns:th="http://www.thymeleaf.org">
<head lang="en">
    <meta charset="UTF-8"/>
    <title>统一页面异常处理</title>
</head>
<body>
<h1>统一页面异常处理</h1>
<div th:text="${message}"></div>
</body>
</html>
```

`th:text="${message}"` 是 Thymeleaf 语法，把后端 `ModelAndView` 传来的 `message` 变量渲染到这个 `<div>` 里。

---

## 十、运行与验证

启动后访问：

| 请求 | 效果 |
| --- | --- |
| `GET http://localhost:8080/demo/json` | 返回 JSON：`{"code":500,"message":"服务器出错啦","data":null}` |
| `GET http://localhost:8080/demo/page` | 浏览器跳转到错误页，显示"统一页面异常处理"和"服务器出错啦" |

可以看到，无论哪种异常，用户都不会再看到白板错误页或堆栈，而是统一的 JSON 或友好的错误页面。

---

## 十一、动手练习

1. **加一个业务异常**：在 `Status` 枚举里加 `NOT_FOUND(404, "资源不存在")`，在 `TestController` 加一个 `/notfound` 接口抛 `JsonException(Status.NOT_FOUND)`，访问验证返回的 code 和 message。
2. **处理空指针异常**：在 `DemoExceptionHandler` 加一个 `@ExceptionHandler(NullPointerException.class)` 方法，让代码里意外的 NPE 也返回统一 JSON，而不是白板页。
3. **区分 JSON/Page 的自动判断**：思考——如果想让同一个异常根据请求类型（ajax 还是页面跳转）自动决定返回 JSON 还是页面，该怎么实现？（提示：判断 `Request` 的 `Accept` 头或 `X-Requested-With`）
4. **去掉 `@ResponseBody`**：把 `jsonErrorHandler` 上的 `@ResponseBody` 去掉，观察会发生什么（提示：会被当成视图名跳转，报错）。
5. **改成 `@RestControllerAdvice`**：把 `@ControllerAdvice` 换成 `@RestControllerAdvice`，思考这对页面异常处理方法有什么影响（提示：所有方法都默认加 `@ResponseBody`，页面跳转会失效）。

---

## 十二、本模块知识点总结（结合实际开发详解）

统一异常处理是生产级 Spring Boot 项目的必备基础设施。下面把核心知识点放到真实开发场景里讲透。

### 12.1 `@ControllerAdvice` + `@ExceptionHandler`：全局兜底的标准姿势

**实际开发中怎么用？**

真实项目几乎一定会有一个全局异常处理类，典型写法：

```java
@RestControllerAdvice   // 返回 JSON 的项目直接用这个
@Slf4j
public class GlobalExceptionHandler {

    // 1. 业务异常
    @ExceptionHandler(BusinessException.class)
    public ApiResponse handleBusiness(BusinessException e) {
        log.warn("业务异常: {}", e.getMessage());
        return ApiResponse.ofException(e);
    }

    // 2. 参数校验异常
    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ApiResponse handleValid(MethodArgumentNotValidException e) {
        String msg = e.getBindingResult().getFieldError().getDefaultMessage();
        return ApiResponse.of(400, msg, null);
    }

    // 3. 兜底：所有未捕获的异常
    @ExceptionHandler(Exception.class)
    public ApiResponse handleAll(Exception e) {
        log.error("系统异常", e);
        return ApiResponse.of(500, "系统繁忙", null);
    }
}
```

**关键设计原则：**

1. **从具体到通用**：先写具体的异常处理（`BusinessException`），最后用一个 `@ExceptionHandler(Exception.class)` 兜底所有未预料的异常，保证任何异常都不会以原始堆栈暴露给前端。
2. **日志分级**：业务异常用 `warn`（预期内的），系统异常用 `error`（预期外的），方便监控告警。
3. **信息脱敏**：返回给前端的 message 要友好（"系统繁忙"），详细堆栈只记日志，不外泄。

**常见坑：**

- **多个 `@ExceptionHandler` 有继承关系时**：如果同时注册了 `Exception` 和 `NullPointerException` 处理器，抛 NPE 会走最具体的那个（`NullPointerException`），这是 Spring 的"最近匹配"原则。但如果你不小心把通用处理器写在前面、具体处理器写在后面，顺序不影响——Spring 按类型层级匹配，不按代码顺序。
- **`@ControllerAdvice` 扫描范围**：默认扫描所有 Controller。如果只想扫描某个包，用 `@ControllerAdvice("com.xkcoding.web")`；如果只想扫描特定注解，用 `@ControllerAdvice(annotations = RestController.class)`。多模块项目里要注意别让多个 `@ControllerAdvice` 冲突。
- **异常处理方法里又抛异常**：如果 `@ExceptionHandler` 方法自己又抛了异常，Spring 会退化成默认错误处理（白板页），所以处理方法内部要 try-catch 好异常。

### 12.2 `@ControllerAdvice` vs `@RestControllerAdvice`

| 注解 | 等价于 | 适用场景 |
| --- | --- | --- |
| `@ControllerAdvice` | `@Component` + 全局 `@ExceptionHandler` | 既处理 JSON 又处理页面 |
| `@RestControllerAdvice` | `@ControllerAdvice` + `@ResponseBody` | 只处理 JSON（前后端分离项目首选） |

**实际开发建议**：前后端分离项目（绝大多数现代项目）直接用 `@RestControllerAdvice`，所有异常处理方法都返回 JSON，省得每个方法都写 `@ResponseBody`。本模块因为要演示页面跳转，才用 `@ControllerAdvice`。

### 12.3 自定义异常体系设计

本模块用 `BaseException` + `JsonException`/`PageException` 区分场景。但实际项目里，更常见的设计是**按业务领域**划分异常：

```
BaseException
├── UserException        (用户领域)
│   ├── UserNotFoundException
│   └── UserPasswordErrorException
├── OrderException       (订单领域)
│   ├── OrderNotFoundException
│   └── OrderStatusException
└── PaymentException     (支付领域)
```

**设计原则：**

1. **统一基类**：所有业务异常继承 `BaseException`，全局处理器只需捕获 `BaseException` 就能处理所有业务异常，再细分子类做差异化处理。
2. **异常不要滥用**：异常用于"异常情况"（用户不存在、余额不足），不要用于正常流程控制（不要用异常做 if-else），因为异常的性能开销比条件判断大。
3. **携带上下文**：异常里可以加更多字段（如出错的订单号、用户 ID），方便日志追踪。

**常见坑：**

- 自定义异常忘了继承 `RuntimeException`：如果继承 `Exception`（Checked），方法签名要写 `throws`，代码被污染。
- 异常层级太深：5 层以上的继承链会让排查困难，保持 2-3 层即可。
- 一个异常类打天下：所有错误都用一个 `BusinessException`，靠 message 区分，失去了类型安全。应该按业务领域分。

### 12.4 统一响应封装 `ApiResponse`

本模块的 `ApiResponse` 用静态工厂方法封装，是经典设计。实际开发中还要考虑：

**1. 泛型化数据字段：**

```java
@Data
public class ApiResponse<T> {
    private Integer code;
    private String message;
    private T data;          // 泛型，类型安全
}
```

这样 `ApiResponse<User>` 的 data 就是 `User` 类型，比 `Object` 安全。

**2. 分页响应：**

```java
public class PageResponse<T> {
    private Long total;
    private List<T> records;
    // ...
}
```

**3. 成功失败快速构造：**

```java
public static <T> ApiResponse<T> success(T data) { ... }
public static <T> ApiResponse<T> fail(int code, String msg) { ... }
```

**常见坑：** `data` 字段用 `Object` 类型，序列化成 JSON 后类型信息丢失，前端拿到的是泛化对象，不如泛型安全。

### 12.5 Spring Boot 默认错误处理机制

理解 Spring Boot 的默认行为，才能知道为什么要自定义：

1. 当异常没被任何 `@ExceptionHandler` 捕获，Spring Boot 走到 `/error` 端点（由 `BasicErrorController` 处理）。
2. 如果请求头 `Accept: application/json`，返回 JSON 错误信息（含 timestamp、status、error、message、path）。
3. 如果是浏览器请求，返回 `error.html` 白板页（Spring Boot 默认的"Whitelabel Error Page"）。

**自定义默认错误页的几种方式：**

1. 在 `templates/error.html` 放一个页面，会覆盖默认白板页（Spring Boot 自动识别 `error` 视图名）。
2. 在 `templates/error/` 下放 `404.html`、`500.html`，按状态码匹配错误页。
3. 用 `@ControllerAdvice` 完全接管异常处理（本模块方式），绕过默认机制。

**实际开发建议**：前后端分离项目用 `@RestControllerAdvice` 全局接管，所有异常返回统一 JSON；传统多页项目用 `templates/error/` 下的状态码页面。两者结合也行。

### 12.6 异常处理与日志、监控的配合

异常处理不只是返回响应，还要考虑可观测性：

**最佳实践：**

1. **异常处理方法里必须记日志**：`log.error("xxx异常", e)`，把完整堆栈记下来（注意传 `e` 不只传 `e.getMessage()`，前者含堆栈）。
2. **区分日志级别**：业务异常 `warn`，系统异常 `error`，参数错误 `info` 或 `warn`。
3. **接入监控**：`error` 级别日志接入告警系统（如 Prometheus + Grafana、Graylog），线上出异常自动告警。
4. **异常埋点**：给每个异常加 traceId（链路追踪），方便在分布式系统里串联日志。

**常见坑：**

- 只记 `e.getMessage()` 不记堆栈：线上排查时缺少调用链，定位不了问题。正确写法 `log.error("异常", e)`（第二个参数传异常对象，日志框架会打印完整堆栈）。
- 异常被吞掉：`catch (Exception e) { log.error(e.getMessage()); }` 没有重新抛出或处理，业务流程"看似正常"实则出错，是最危险的 bug 来源。

---

> 📌 **学习建议**：统一异常处理是后端"工程化"的标志之一。前端同学要理解的核心差异是——后端的异常不是"弹窗提示用户"，而是"结构化返回错误码 + 记录日志"。建议你把本模块的 `@RestControllerAdvice` + `BaseException` + `ApiResponse` 这套三件套抄进自己的项目模板，它是几乎所有 Spring Boot 项目的标配。后续模块（数据库、缓存、消息队列）抛出的异常，最终都会汇聚到这个全局处理器里统一兜底。
