# 25 - Spring Boot 集成 Swagger 自动生成 API 文档

> 对应项目模块：`demo-swagger`
> 前置知识：已学完前面模块，了解 `@RestController`、`@GetMapping`、`@RequestBody`、`@PathVariable` 等注解用法
> 学习目标：理解 Swagger 是什么、为什么用它，掌握 Spring Boot 集成 Swagger2 的完整流程，能用注解为接口生成可交互的在线 API 文档。

---

## 一、本模块要解决什么问题？

### 1.1 没有文档工具之前的痛点

作为前端工程师，你一定遇到过这种场景：后端写好了接口，甩给你一个 Word/Markdown 文档，或者直接口头说"你调这个 GET /user，传 username"。然后：

- 接口改了，文档没同步更新，你按旧文档调，报错。
- 参数类型、是否必填、返回结构全靠猜，得反复问后端。
- 没有在线测试，要自己拼 curl 或在 Postman 里手填。

**Swagger 解决的就是"文档即代码、文档与代码同步、在线可测试"** 这三件事。它扫描你的 Controller 注解，自动生成一个可视化的 API 文档页面，还能直接在页面上点"Try it out"发请求测试。

### 1.2 Swagger 是什么？

Swagger 是一套围绕 OpenAPI 规范（原 Swagger 规范）的工具集，核心包括：

| 组件 | 作用 |
| --- | --- |
| **Swagger Core** | 扫描 Java 注解，生成接口描述 JSON（OpenAPI 文档） |
| **Swagger UI** | 把那个 JSON 渲染成可交互的 HTML 文档页面 |
| **Swagger Editor** | 在线编辑、预览 OpenAPI YAML/JSON（本模块不用） |

> 💡 前端类比：Swagger 之于后端，就像 Apifox / Postman / Stoplight 之于前端——但它最大的优势是**文档从代码注解自动生成**，不会和代码脱节。你可以把它理解成"后端版的 Storybook + 接口调试工具合体"。

### 1.3 SpringFox 与 SpringDoc 的关系（重要背景）

本模块用的是 **SpringFox**（`io.springfox`），它是 Swagger2 在 Spring 生态的第三方实现，曾长期是事实标准。但要注意：

- **SpringFox 已停止维护**，对 Spring Boot 2.6+ 的路径匹配策略有兼容问题，对 Spring Boot 3.x 完全不支持。
- **现代项目推荐用 SpringDoc-OpenAPI**（支持 OpenAPI 3、Spring Boot 3.x）。
- 本项目用 Spring Boot 2.1.0，SpringFox 2.9.2 能正常工作，所以这里用它演示。**学完原理后，新项目请用 SpringDoc。** 这点会在知识点总结里详细讲。

---

## 二、项目结构

```
demo-swagger/
├── pom.xml
└── src/main/
    ├── java/com/xkcoding/swagger/
    │   ├── SpringBootDemoSwaggerApplication.java   # 启动类
    │   ├── common/
    │   │   ├── ApiResponse.java                    # 统一响应体（泛型）
    │   │   ├── DataType.java                        # 数据类型常量
    │   │   └── ParamType.java                       # 参数位置常量
    │   ├── config/
    │   │   └── Swagger2Config.java                  # Swagger 配置类（核心）
    │   ├── controller/
    │   │   └── UserController.java                  # 接口控制器（演示注解）
    │   └── entity/
    │       └── User.java                           # 用户实体
    └── resources/
        └── application.yml                         # 配置文件
```

相比之前的模块，这里多了 `common`（公共类）、`config`（配置类）、`entity`（实体）三个包，是更接近真实项目的分层。

---

## 三、pom.xml 依赖

```xml
<properties>
    <swagger.version>2.9.2</swagger.version>
</properties>

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

    <!-- Swagger2 核心依赖：扫描注解生成 OpenAPI 文档 JSON -->
    <dependency>
        <groupId>io.springfox</groupId>
        <artifactId>springfox-swagger2</artifactId>
        <version>${swagger.version}</version>
    </dependency>

    <!-- Swagger UI：把 JSON 渲染成可视化页面 -->
    <dependency>
        <groupId>io.springfox</groupId>
        <artifactId>springfox-swagger-ui</artifactId>
        <version>${swagger.version}</version>
    </dependency>

    <dependency>
        <groupId>org.projectlombok</groupId>
        <artifactId>lombok</artifactId>
        <optional>true</optional>
    </dependency>
</dependencies>
```

注意两点：

1. **Swagger 没有官方 Spring Boot Starter**（SpringFox 时期），所以要手动引两个依赖：`springfox-swagger2`（生成文档）+ `springfox-swagger-ui`（渲染页面）。版本自己锁，这里用 `2.9.2`。
2. 引入 Lombok 是为了实体类少写样板代码。

> 💡 前端类比：这像你装一个 Vue 插件，核心包 + UI 包分开引。核心包负责"数据"，UI 包负责"展示"。

---

## 四、Swagger 配置类（核心）

`config/Swagger2Config.java`：

```java
@Configuration
@EnableSwagger2
public class Swagger2Config {

    @Bean
    public Docket createRestApi() {
        return new Docket(DocumentationType.SWAGGER_2)
                .apiInfo(apiInfo())
                .select()
                .apis(RequestHandlerSelectors.basePackage("com.xkcoding.swagger.controller"))
                .paths(PathSelectors.any())
                .build();
    }

    private ApiInfo apiInfo() {
        return new ApiInfoBuilder()
                .title("spring-boot-demo")
                .description("这是一个简单的 Swagger API 演示")
                .contact(new Contact("Yangkai.Shen", "http://xkcoding.com", "237497819@qq.com"))
                .version("1.0.0-SNAPSHOT")
                .build();
    }
}
```

这是整个模块的核心，逐段拆解：

### 4.1 `@Configuration` + `@EnableSwagger2`

- `@Configuration`：标记为 Spring 配置类，里面的 `@Bean` 方法会被容器调用注册。
- `@EnableSwagger2`：SpringFox 提供的注解，开启 Swagger2 支持，会自动注入一批 Swagger 相关的 Bean（文档扫描器、UI 资源处理器等）。

### 4.2 `Docket` Bean —— 文档的"配置中心"

`Docket` 是 SpringFox 的核心配置对象，一个 `Docket` 代表一组 API 文档。它的配置用链式调用（Builder 风格）：

```java
new Docket(DocumentationType.SWAGGER_2)   // 1. 文档类型：Swagger 2.0
    .apiInfo(apiInfo())                   // 2. 文档元信息（标题、描述、联系人）
    .select()                              // 3. 进入"选择器"模式，定义扫描范围
    .apis(RequestHandlerSelectors.basePackage("com.xkcoding.swagger.controller"))  // 4. 只扫这个包下的 Controller
    .paths(PathSelectors.any())           // 5. 所有路径都纳入
    .build();                              // 6. 构建
```

**关键：扫描范围控制（`.apis()` + `.paths()`）**

- `RequestHandlerSelectors.basePackage("...")`：按包扫描，只把指定包下的 Controller 生成文档。这是最常用的方式，避免把第三方库的接口也扫进来。
- `PathSelectors.any()`：路径全要。也可以用 `PathSelectors.ant("/user/**")` 只保留特定前缀的接口。

> 💡 前端类比：`.apis()` 像路由配置里"从哪个目录扫描路由文件"，`.paths()` 像"只暴露哪些前缀的路由"。两者一起圈定"文档收录范围"。

### 4.3 `ApiInfo` —— 文档页头信息

```java
new ApiInfoBuilder()
    .title("spring-boot-demo")          // 文档标题
    .description("...")                  // 描述
    .contact(new Contact("名字", "网址", "邮箱"))  // 联系人
    .version("1.0.0-SNAPSHOT")           // 版本
    .build();
```

这些信息会显示在 Swagger UI 页面顶部。`Contact` 三个参数分别是姓名、URL、邮箱。

---

## 五、实体类与统一响应体

### 5.1 `User` 实体

```java
@Data
@NoArgsConstructor
@AllArgsConstructor
@ApiModel(value = "用户实体", description = "User Entity")
public class User implements Serializable {
    @ApiModelProperty(value = "主键id", required = true)
    private Integer id;

    @ApiModelProperty(value = "用户名", required = true)
    private String name;

    @ApiModelProperty(value = "工作岗位", required = true)
    private String job;
}
```

- `@ApiModel`：标记一个类是数据模型，`value` 是模型显示名，`description` 是描述。Swagger 会把这个类的字段结构展示在文档的"数据模型"区。
- `@ApiModelProperty`：标记字段，`value` 是字段说明，`required = true` 表示必填。这些会渲染成字段的注释和是否必填标记。
- `implements Serializable`：实现 Java 序列化接口，是 Java 实体的传统约定（虽然现代项目不一定需要，但很多团队保留）。

> 💡 前端类比：`@ApiModel` + `@ApiModelProperty` 类似 TypeScript 的 interface 加上 JSDoc 注释——给数据结构加文档说明。Swagger 读这些注解生成"数据模型"Schema，相当于 TS 的类型定义。

### 5.2 `ApiResponse<T>` 统一响应体

```java
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@ApiModel(value = "通用API接口返回", description = "Common Api Response")
public class ApiResponse<T> implements Serializable {
    @ApiModelProperty(value = "通用返回状态", required = true)
    private Integer code;
    @ApiModelProperty(value = "通用返回信息", required = true)
    private String message;
    @ApiModelProperty(value = "通用返回数据", required = true)
    private T data;
}
```

这是一个**泛型**统一响应体，所有接口返回 `{ code, message, data }` 结构，`data` 是泛型 `T`，可以是 `User`、`List<User>` 等。`@Builder` 是 Lombok 的链式构造：`ApiResponse.<User>builder().code(200).message("ok").data(user).build()`。

> 💡 这是真实项目的标准做法——统一响应体让前端处理逻辑一致：先看 `code`，再取 `data`。后续 `demo-exception-handler` 模块会更系统地讲这套机制。

### 5.3 `DataType` 与 `ParamType` 常量类

```java
public final class DataType {
    public final static String STRING = "String";
    public final static String INT = "int";
    // ...
}
public final class ParamType {
    public final static String QUERY = "query";
    public final static String PATH = "path";
    public final static String BODY = "body";
    // ...
}
```

这两个类纯粹是**字符串常量**，方便在 `@ApiImplicitParam` 注解里引用，避免手写字符串拼错。比如用 `ParamType.PATH` 代替手写 `"path"`。这是工程化的小技巧——用常量替代魔法字符串。

---

## 六、Controller 注解详解（重点）

`controller/UserController.java` 是 Swagger 注解的主战场，逐个方法看：

### 6.1 类级注解

```java
@RestController
@RequestMapping("/user")
@Api(tags = "1.0.0-SNAPSHOT", description = "用户管理", value = "用户管理")
@Slf4j
public class UserController { ... }
```

- `@Api(tags = "...", description = "...")`：标记 Controller，`tags` 用于在 Swagger UI 里给接口分组（左侧菜单按 tag 分类），`description` 是分组描述。前端类比：相当于给一组路由打个"模块标签"，文档里按标签折叠展示。

### 6.2 GET 条件查询（多个参数用 `@ApiImplicitParams`）

```java
@GetMapping
@ApiOperation(value = "条件查询（DONE）", notes = "备注")
@ApiImplicitParams({
    @ApiImplicitParam(name = "username", value = "用户名", dataType = DataType.STRING, paramType = ParamType.QUERY, defaultValue = "xxx")
})
public ApiResponse<User> getByUserName(String username) { ... }
```

- `@ApiOperation`：描述这个接口，`value` 是接口名，`notes` 是补充备注。显示在文档每个接口的标题。
- `@ApiImplicitParams`：包裹多个 `@ApiImplicitParam`，用于**多个简单参数**（不是 `@RequestBody` 对象）的场景。
- `@ApiImplicitParam`：描述单个参数：
  - `name`：参数名
  - `value`：参数说明
  - `dataType`：数据类型（`String`/`int`/`long`...）
  - `paramType`：参数位置（`query`=查询串、`path`=路径、`body`=请求体、`header`=请求头、`form`=表单）
  - `defaultValue`：默认值（文档里会预填，方便测试）

> ⚠️ 注意：`getByUserName(String username)` 方法参数没有加 `@RequestParam`，Swagger 默认按 `query` 类型、用参数名 `username` 识别。`@ApiImplicitParam` 是给这个参数**补充文档说明**，不是绑定参数（绑定靠 Spring MVC 的注解）。

### 6.3 GET 主键查询（路径参数）

```java
@GetMapping("/{id}")
@ApiOperation(value = "主键查询（DONE）", notes = "备注")
@ApiImplicitParams({
    @ApiImplicitParam(name = "id", value = "用户编号", dataType = DataType.INT, paramType = ParamType.PATH)
})
public ApiResponse<User> get(@PathVariable Integer id) { ... }
```

这里 `paramType = ParamType.PATH`，因为 `id` 来自 URL 路径 `/{id}`，配合 `@PathVariable`。这是路径参数的标准文档写法。

### 6.4 DELETE 删除（单个参数用 `@ApiImplicitParam`）

```java
@DeleteMapping("/{id}")
@ApiOperation(value = "删除用户（DONE）", notes = "备注")
@ApiImplicitParam(name = "id", value = "用户编号", dataType = DataType.INT, paramType = ParamType.PATH)
public void delete(@PathVariable Integer id) { ... }
```

单个参数时，直接用 `@ApiImplicitParam`（不用 `@ApiImplicitParams` 包裹）。注意返回 `void`，Swagger 会标记"无返回体"。

### 6.5 POST 添加（`@RequestBody` 不用写 `@ApiImplicitParam`）

```java
@PostMapping
@ApiOperation(value = "添加用户（DONE）")
public User post(@RequestBody User user) { ... }
```

**关键点**：当参数是 `@RequestBody User`（请求体对象）时，**不需要**写 `@ApiImplicitParam`。因为 Swagger 会自动从 `User` 类的 `@ApiModel`/`@ApiModelProperty` 注解读取参数结构，生成请求体 Schema。注释里的 `log.info("如果是 POST PUT 这种带 @RequestBody 的可以不用写 @ApiImplicitParam")` 就是在强调这一点。

### 6.6 POST 集合/数组参数

```java
@PostMapping("/multipar")
public List<User> multipar(@RequestBody List<User> user) { ... }

@PostMapping("/array")
public User[] array(@RequestBody User[] user) { ... }
```

演示请求体是集合或数组的情况，Swagger 同样能自动识别泛型 `List<User>` 和 `User[]` 的结构。

### 6.7 PUT 修改（混合参数）

```java
@PutMapping("/{id}")
@ApiOperation(value = "修改用户（DONE）")
public void put(@PathVariable Long id, @RequestBody User user) { ... }
```

路径参数 `id` + 请求体 `user` 混合。这里没写 `@ApiImplicitParam`，注释说明"swagger 也会使用默认的参数名作为描述信息"——即不写注解时 Swagger 用参数名当默认描述，但**强烈建议写**，否则文档可读性差。

### 6.8 文件上传

```java
@PostMapping("/{id}/file")
@ApiOperation(value = "文件上传（DONE）")
public String file(@PathVariable Long id, @RequestParam("file") MultipartFile file) { ... }
```

`MultipartFile` 是 Spring MVC 处理文件上传的类型，`@RequestParam("file")` 对应前端 FormData 里字段名为 `file` 的文件。Swagger 会把它识别为 `formData` 类型参数，UI 上会出现"选择文件"按钮。

> 💡 前端类比：前端用 `FormData` 上传文件时，`formData.append('file', fileObj)`，这里的 `@RequestParam("file")` 就是后端接收那个名为 `file` 字段。

---

## 七、配置文件

`application.yml`：

```yaml
server:
  port: 8080
  servlet:
    context-path: /demo
```

和之前模块一样，端口 8080，上下文路径 `/demo`。所以 Swagger UI 的访问地址是 `http://localhost:8080/demo/swagger-ui.html`。

---

## 八、运行与验证

### 8.1 启动

```sh
mvn spring-boot:run
```

### 8.2 访问 Swagger UI

浏览器打开：`http://localhost:8080/demo/swagger-ui.html`

页面会显示：
- 顶部：`spring-boot-demo` 标题、描述、联系人、版本（来自 `ApiInfo`）
- 左侧/主区：按 `@Api(tags=...)` 分组的接口列表（这里只有"用户管理"一组）
- 每个接口：`@ApiOperation` 的标题、`@ApiImplicitParam` 描述的参数表
- 底部：数据模型区，展示 `User`、`ApiResponse` 的字段结构

### 8.3 在线测试

点开某个接口 → 点 "Try it out" → 填参数（如 `id=1`）→ 点 "Execute" → 页面下方显示请求 URL、响应状态码、响应体。整个过程不用 Postman，直接在文档页调试。

### 8.4 查看原始 JSON

访问 `http://localhost:8080/demo/v2/api-docs`，返回一个大的 JSON——这就是 OpenAPI 文档的原始内容，Swagger UI 正是读取它渲染页面。前端可以用这个 JSON 做二次开发（比如生成 TS 类型、Mock 服务）。

---

## 九、动手练习

1. **加一个接口**：在 `UserController` 加 `@GetMapping("/list")` 返回 `List<User>`，加 `@ApiOperation` 和 `@ApiImplicitParam`，重启看文档是否更新。
2. **改分组**：把 `@Api(tags = "用户管理")` 改成 `tags = "2.0.0-用户管理"`，观察左侧分组变化。
3. **给字段加示例**：在 `User` 的 `name` 字段加 `@ApiModelProperty(value = "用户名", example = "zhangsan", required = true)`，看文档里是否出现示例值预填。
4. **限制扫描范围**：把 `Swagger2Config` 的 `.apis(basePackage(...))` 改成扫描一个不存在的包，重启看文档是否变空（体会扫描范围控制）。
5. **用 `PathSelectors.ant`**：把 `.paths(PathSelectors.any())` 改成 `.paths(PathSelectors.ant("/user/**"))`，观察只有 `/user` 开头的接口出现在文档。
6. **测试文件上传**：在 Swagger UI 上对 `POST /{id}/file` 点 Try it out，选择一个本地文件上传，观察返回的文件名。

---

## 十、本模块知识点总结（结合实际开发详解）

Swagger 是前后端协作的"润滑剂"，但实际开发中有很多坑和选型考量。下面把核心知识点放到真实场景里讲透。

### 10.1 SpringFox vs SpringDoc：新项目怎么选？

**实际开发现状：**

| 维度 | SpringFox（本模块用的） | SpringDoc-OpenAPI（推荐） |
| --- | --- | --- |
| 维护状态 | 已停止维护 | 活跃维护 |
| Swagger 版本 | Swagger 2.0 | OpenAPI 3（新版规范） |
| Spring Boot 2.x | 支持（2.6+ 有兼容问题） | 支持 |
| Spring Boot 3.x | **不支持** | 支持 |
| 注解包名 | `io.swagger.annotations`（`@Api`/`@ApiOperation`） | `io.swagger.v3.oas.annotations`（`@Tag`/`@Operation`） |
| 配置方式 | `@EnableSwagger2` + `Docket` Bean | 自动配置，少量 `@Bean` |

**最佳实践：**

- **新项目（尤其 Spring Boot 3.x）一律用 SpringDoc**，别再用 SpringFox。
- **老项目（Spring Boot 2.x）** 如果 SpringFox 够用就保持，但要升级到 Spring Boot 3 时必须迁移到 SpringDoc。
- 本模块用 SpringFox 是因为项目 Spring Boot 2.1.0，能跑。**你学的是 Swagger 的原理和注解思想**，这些在 SpringDoc 里是相通的（只是注解名和配置方式变了）。

**常见坑：**

- Spring Boot 2.6+ 默认改了路径匹配策略（PathPatternParser），SpringFox 2.x 启动直接报错。要么降级 Spring Boot，要么加 `spring.mvc.pathmatch.matching-strategy=ant_path_matcher`，要么直接换 SpringDoc。
- SpringFox 3.0.0 坑很多，社区不推荐，直接跳到 SpringDoc。

### 10.2 `@ApiImplicitParam` 该不该写？什么时候写？

**实际开发中的判断标准：**

| 参数类型 | 是否写 `@ApiImplicitParam` | 原因 |
| --- | --- | --- |
| `@RequestBody User`（请求体对象） | **不用写** | Swagger 自动从 `@ApiModel` 读结构 |
| `@PathVariable` / `@RequestParam`（简单参数） | **要写** | 否则文档只有参数名，没有说明、类型、是否必填 |
| `MultipartFile`（文件） | 可写可不写 | 不写时 Swagger 也能识别为文件类型 |

**最佳实践：**

- 所有简单参数（query/path/header）都写 `@ApiImplicitParam`，文档才完整。
- 请求体对象别写，写了反而冗余且容易和实体注解冲突。
- 用 `@ApiImplicitParams` 包裹多个简单参数。

**常见坑：**

- `paramType` 写错：把 `path` 参数写成 `paramType = "query"`，文档里参数位置就错了，测试时填的值传不进去。
- `dataType` 和实际 Java 类型不匹配：方法参数是 `Integer`，`dataType` 写成 `String`，文档类型标注错误（虽然不影响运行，但误导前端）。
- 忘了 `@ApiImplicitParam` 的 `name` 和方法参数名不一致：导致 Swagger 找不到对应参数，文档显示异常。

### 10.3 统一响应体与泛型在 Swagger 中的表现

本模块的 `ApiResponse<T>` 是泛型统一响应体，这种设计在真实项目里非常常见。

**Swagger 如何处理泛型？**

当方法返回 `ApiResponse<User>` 时，Swagger 会把 `T` 替换成 `User`，文档里展示的响应结构是 `{ code, message, data: { id, name, job } }`。返回 `ApiResponse<List<User>>` 时，`data` 是数组。这就是泛型统一响应体的威力——一套结构适配所有接口。

**实际开发最佳实践：**

1. **统一响应体**：所有接口返回同一个结构 `{ code, message, data }`，前端处理逻辑统一。
2. **code 用枚举**：不要满地写 `200`，定义 `ResponseCode` 枚举（`SUCCESS(200)`、`PARAM_ERROR(400)`...）。
3. **泛型 + `@ApiModelProperty`**：响应体字段加注解，让文档自动说明每个字段。
4. **配合全局异常处理**：异常时也返回统一响应体（`demo-exception-handler` 模块会讲）。

**常见坑：**

- 泛型擦除导致 Swagger 识别不出 `T` 的真实类型：SpringFox 通过反射方法签名能解析出 `ApiResponse<User>`，但如果返回 `ApiResponse<?>` 或 `Object`，文档就显示不出具体结构。**方法返回类型一定要写明确**，别用 `Object`。
- `ApiResponse<T>` 不加 `@ApiModel`，文档里响应结构缺失。

### 10.4 Swagger 的生产环境安全：要不要暴露？

**实际开发的核心问题：** Swagger UI 暴露了所有接口细节，生产环境如果直接开放，等于把 API 蓝图送给攻击者。

**三种处理策略：**

1. **生产环境直接禁用**（最安全）：用 Profile 控制，生产环境不创建 `Docket` Bean，或 `Docket(...).enable(false)`。

   ```java
   @Profile("!prod")
   @Configuration
   @EnableSwagger2
   public class Swagger2Config { ... }   // 只在非 prod 环境注册
   ```

2. **加密码保护**：给 Swagger UI 路径加 Spring Security 认证，只有内部人员能访问。

3. **保持开放但只暴露只读接口**：用 `.paths()` 限制只文档化查询接口，不文档化增删改接口。

**最佳实践：** 生产环境**默认关闭** Swagger，或加认证。这是安全审计的常见检查项。

**常见坑：**

- 忘了关闭，生产环境 Swagger UI 被搜索引擎收录或被扫描器发现，导致接口泄露。
- 加了认证但用了弱密码，形同虚设。

### 10.5 `Docket` 的扫描范围控制：别把第三方接口扫进来

`.apis()` 和 `.paths()` 决定哪些接口进文档。**实际开发中一定要限制范围**，否则：

- 第三方库（如 Spring Boot Actuator、Spring Data REST）的接口会被扫进文档，污染。
- 文档臃肿，前端找不到重点。

**最佳实践：**

- `.apis(basePackage("你的controller包"))`：按业务包扫描，最精确。
- `.paths(any())` 或 `.paths(not(PathSelectors.regex("/error.*")))`：排除错误页等无关路径。
- 多模块项目可以定义多个 `Docket` Bean，每个对应一组 API（如 `userApi()`、`orderApi()`），文档里分组展示。

**常见坑：**

- `basePackage` 路径写错，文档为空。
- 没限制范围，Actuator 的 `/health`、`/info` 全进了文档。

### 10.6 从 Swagger JSON 到前端工程化

Swagger 生成的 JSON（`/v2/api-docs`）不只是给 UI 看的，它还能驱动前端工程化：

1. **生成 TS 类型**：用 `openapi-typescript` 或 `swagger-typescript-codegen` 把 JSON 转成 TS interface，前端不用手写类型。
2. **生成请求代码**：用 `openapi-generator` 自动生成 axios 请求函数，前端不用手写 API 调用。
3. **Mock 服务**：用 Prism 等工具读 Swagger JSON 启动 Mock 服务，前端在后端没写完时就能联调。

**最佳实践：** 把 Swagger JSON 的获取纳入 CI/CD，后端每次提交自动生成 JSON，前端自动拉取更新类型和请求代码——这就是"接口契约驱动开发"，是现代前后端协作的高效模式。

> 💡 前端类比：这像 GraphQL 的 schema 即契约，或 tRPC 的端到端类型安全——Swagger JSON 就是 REST 时代的"schema"，让前后端类型同步。

---

> 📌 **学习建议**：作为前端转后端的工程师，理解 Swagger 的最大价值在于"文档即代码"——你写的注解既是代码注释又是接口文档，永远和代码同步。这和你前端用 JSDoc/TypeDoc 生成组件文档是一个思路。建议把 Controller 的每个接口都认真写 `@ApiOperation` 和 `@ApiImplicitParam`，这不是负担，而是给未来的自己（和前端同事）留路。另外，新项目记得用 SpringDoc 替代本模块的 SpringFox，注解思想一样，只是包名和写法变了。
