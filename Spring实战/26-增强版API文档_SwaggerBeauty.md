# 26 - 增强版 API 文档（Swagger Beauty）

> 对应项目模块：`demo-swagger-beauty`
> 前置知识：已学完前一篇 `25-接口文档_Swagger`，理解原生 Swagger 的注解体系（`@Api`、`@ApiOperation`、`@ApiImplicitParam` 等）
> 学习目标：理解为什么要用增强版 Swagger，掌握 `swagger-spring-boot-starter`（battcn）的配置方式，对比原生 Swagger 的差异，能在项目中落地一套带登录验证、全局响应码、美化界面的 API 文档。

---

## 一、本模块要解决什么问题？

上一篇的原生 Swagger（`springfox-swagger` + `swagger-ui`）能自动生成接口文档，但有几个痛点：

1. **界面简陋**：原生 `swagger-ui.html` 是纯英文 + 紧凑列表，参数多时阅读体验差，没有分组、搜索、离线文档等功能。
2. **配置繁琐**：原生 Swagger 要手写一个 `SwaggerConfig` 配置类，用 `Docket` Bean 描述扫描规则、文档信息，代码量不小。
3. **无安全控制**：原生 Swagger 文档页面任何人都能访问，生产环境暴露接口结构有安全风险。
4. **全局响应码缺失**：原生 Swagger 默认只展示 200，不告诉你 400/404/500 长什么样，前端联调时对异常返回没有预期。

本模块用第三方封装的 `swagger-spring-boot-starter`（作者 battcn）替代原生方案，它把上述问题都解决了：

- **配置化**：不用写 `SwaggerConfig` 类，全部在 `application.yml` 里配置。
- **美化界面**：内置更友好的 UI（基于 swagger-bootstrap-ui 风格）。
- **登录验证**：内置 Basic 认证，给文档页面加账号密码。
- **全局响应码**：在 yml 里统一配置 GET/POST 的 400/404/500 响应示例。

> 💡 前端类比：这就像用 Storybook 替代手写的组件文档——原生 Swagger 是"能用的基础版"，增强版是"开箱即用、带主题、带权限的进阶版"。类似的还有 Knife4j（前身为 swagger-bootstrap-ui），是目前国内最流行的 Swagger 增强方案。

---

## 二、项目结构

```
demo-swagger-beauty/
├── pom.xml
└── src/main/
    ├── java/com/xkcoding/swagger/beauty/
    │   ├── SpringBootDemoSwaggerBeautyApplication.java   # 启动类
    │   ├── common/
    │   │   └── ApiResponse.java                            # 统一响应体（泛型）
    │   ├── controller/
    │   │   └── UserController.java                         # 用户接口（增删改查+文件上传）
    │   └── entity/
    │       └── User.java                                   # 用户实体
    └── resources/
        └── application.yml                                 # Swagger 配置全在这
```

和原生 Swagger 模块对比：**这里没有 `config/SwaggerConfig.java`**——这是增强版最大的区别，配置全部下沉到 yml。

---

## 三、逐行拆解 pom.xml

```xml
<properties>
    <battcn.swagger.version>2.1.2-RELEASE</battcn.swagger.version>
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

    <!-- 增强 Swagger：一个依赖搞定原生 swagger + 美化 UI + 认证 -->
    <dependency>
        <groupId>com.battcn</groupId>
        <artifactId>swagger-spring-boot-starter</artifactId>
        <version>${battcn.swagger.version}</version>
    </dependency>

    <dependency>
        <groupId>org.projectlombok</groupId>
        <artifactId>lombok</artifactId>
        <optional>true</optional>
    </dependency>
</dependencies>
```

**关键点：**

- `swagger-spring-boot-starter`：这是 battcn 封装的起步依赖，传递引入了原生 `springfox-swagger-ui`、`springfox-swagger2`，并加上了自动配置（`swagger-spring-boot-autoconfigure`）。所以你不用写 `@EnableSwagger2`、不用写 `Docket` Bean，引依赖 + 写 yml 即可。
- Lombok：用于实体类和响应体的样板代码生成（`@Data`、`@Builder` 等）。

> 💡 对比原生 Swagger 模块：原生要引 `springfox-swagger2` + `springfox-swagger-ui` 两个依赖，还要写配置类。增强版只引一个 starter，配置全在 yml——这就是"约定优于配置"的体现。

---

## 四、逐行拆解 application.yml（核心）

这是本模块的重头戏，所有 Swagger 行为都在这里配置：

```yaml
server:
  port: 8080
  servlet:
    context-path: /demo
spring:
  swagger:
    enabled: true                                          # 1. 总开关
    title: spring-boot-demo                                # 2. 文档标题
    base-package: com.xkcoding.swagger.beauty.controller   # 3. 扫描包
    description: 这是一个简单的 Swagger API 演示            # 4. 文档描述
    version: 1.0.0-SNAPSHOT                                 # 5. 版本号
    contact:                                                # 6. 联系人
      name: Yangkai.Shen
      email: 237497819@qq.com
      url: http://xkcoding.com
    security:                                               # 7. 登录验证
      filter-plugin: true
      username: xkcoding
      password: 123456
    global-response-messages:                              # 8. 全局响应码
      GET[0]:
        code: 400
        message: Bad Request，一般为请求参数不对
      GET[1]:
        code: 404
        message: NOT FOUND，一般为请求路径不对
      GET[2]:
        code: 500
        message: ERROR，一般为程序内部错误
      POST[0]:
        code: 400
        message: Bad Request，一般为请求参数不对
      POST[1]:
        code: 404
        message: NOT FOUND，一般为请求路径不对
      POST[2]:
        code: 500
        message: ERROR，一般为程序内部错误
```

逐项解释：

| 配置项 | 作用 | 对应原生 Swagger |
| --- | --- | --- |
| `enabled` | Swagger 总开关，false 则完全关闭 | 原生无，需删依赖或删配置类 |
| `title` | 文档页面标题 | `Docket.apiInfo().title()` |
| `base-package` | 只扫描这个包下的 Controller | `Docket.apis(RequestHandlerSelectors.basePackage(...))` |
| `description` | 文档描述 | `Docket.apiInfo().description()` |
| `version` | API 版本号 | `Docket.apiInfo().version()` |
| `contact` | 联系人信息（姓名/邮箱/网址） | `new Contact(...)` |
| `security.filter-plugin` | 是否开启文档页 Basic 认证 | 原生无，需自己写过滤器 |
| `security.username/password` | 认证账号密码 | 原生无 |
| `global-response-messages` | 每种 HTTP 方法的全局响应码示例 | `Docket.globalResponses()` |

**注释里提到的可选项**（本模块未启用但支持）：

```yaml
# base-path: 需要处理的 URL 规则，默认 /**
# exclude-path: 需要排除的 URL 规则，默认 空
```

- `base-path`：限定只文档化匹配的 URL（如 `/api/**`）。
- `exclude-path`：排除不想暴露的 URL（如 `/actuator/**`）。

> 💡 前端类比：这就像 Vite 的 `vite.config.ts` 用配置对象描述构建行为，而不是写一堆插件初始化代码。yml 配置化让"改文档标题"从"改 Java 代码重新编译"变成"改 yml 重启即可"。

---

## 五、启动类

```java
@SpringBootApplication
public class SpringBootDemoSwaggerBeautyApplication {
    public static void main(String[] args) {
        SpringApplication.run(SpringBootDemoSwaggerBeautyApplication.class, args);
    }
}
```

注意：**启动类上没有 `@EnableSwagger2`**。因为 `swagger-spring-boot-starter` 的自动配置会根据 `spring.swagger.enabled=true` 自动开启 Swagger，无需手动加注解。这是 Starter 的"自动配置"能力——你配了开关，它就帮你启用。

---

## 六、统一响应体 ApiResponse

`common/ApiResponse.java`：

```java
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@ApiModel(value = "通用API接口返回", description = "Common Api Response")
public class ApiResponse<T> implements Serializable {
    private static final long serialVersionUID = -8987146499044811408L;

    @ApiModelProperty(value = "通用返回状态", required = true)
    private Integer code;

    @ApiModelProperty(value = "通用返回信息", required = true)
    private String message;

    @ApiModelProperty(value = "通用返回数据", required = true)
    private T data;
}
```

**逐个看：**

- `ApiResponse<T>`：泛型响应体，`T` 是数据载荷类型。统一返回 `{ code, message, data }` 三段式结构，这是后端给前端的"标准信封"。
- `@Data` + `@Builder` + `@NoArgsConstructor` + `@AllArgsConstructor`：Lombok 四件套，生成所有 getter/setter、链式构造器（`ApiResponse.builder().code(200)...build()`）、无参/全参构造。
- `@ApiModel`：Swagger 注解，标记这个类是数据模型，在文档里显示为"通用API接口返回"。
- `@ApiModelProperty`：Swagger 注解，描述每个字段的含义和是否必填。`required = true` 在文档里该字段会标红。

**链式构造的用法**（Controller 里会看到）：

```java
return ApiResponse.<User>builder()
    .code(200)
    .message("操作成功")
    .data(new User(1, username, "JAVA"))
    .build();
```

`<User>` 指明泛型 T 是 User，这样 Swagger 文档能正确推断出 `data` 字段是 User 结构。

> 💡 前端类比：这就像 TypeScript 里定义 `interface ApiResponse<T> { code: number; message: string; data: T }`，后端用泛型保证响应结构统一，前端用类型推导拿到具体 data 类型。Swagger 注解相当于给类型加 JSDoc 注释。

---

## 七、用户实体 User

`entity/User.java`：

```java
@Data
@NoArgsConstructor
@AllArgsConstructor
@ApiModel(value = "用户实体", description = "User Entity")
public class User implements Serializable {
    private static final long serialVersionUID = 5057954049311281252L;

    @ApiModelProperty(value = "主键id", required = true)
    private Integer id;

    @ApiModelProperty(value = "用户名", required = true)
    private String name;

    @ApiModelProperty(value = "工作岗位", required = true)
    private String job;
}
```

- `@ApiModel`：实体类在 Swagger 文档里显示为"用户实体"。
- `@ApiModelProperty`：每个字段加中文描述，`required = true` 标记必填。
- `Serializable` + `serialVersionUID`：Java 序列化机制要求，分布式缓存/传输时需要（本 demo 主要是规范写法）。

> 💡 对比原生 Swagger：实体类的注解写法和原生完全一样（`@ApiModel`、`@ApiModelProperty` 都是 springfox 的注解），增强版只是改了配置方式，注解体系不变——所以从原生迁移到增强版，业务代码几乎不用改。

---

## 八、控制器 UserController（核心）

`controller/UserController.java`：

```java
@RestController
@RequestMapping("/user")
@Api(tags = "1.0.0-SNAPSHOT", description = "用户管理", value = "用户管理")
@Slf4j
public class UserController {

    @GetMapping
    @ApiOperation(value = "条件查询（DONE）", notes = "备注")
    @ApiImplicitParams({
        @ApiImplicitParam(name = "username", value = "用户名", dataType = DataType.STRING, paramType = ParamType.QUERY, defaultValue = "xxx")
    })
    public ApiResponse<User> getByUserName(String username) {
        log.info("多个参数用  @ApiImplicitParams");
        return ApiResponse.<User>builder().code(200).message("操作成功").data(new User(1, username, "JAVA")).build();
    }

    @GetMapping("/{id}")
    @ApiOperation(value = "主键查询（DONE）", notes = "备注")
    @ApiImplicitParams({
        @ApiImplicitParam(name = "id", value = "用户编号", dataType = DataType.INT, paramType = ParamType.PATH)
    })
    public ApiResponse<User> get(@PathVariable Integer id) {
        log.info("单个参数用  @ApiImplicitParam");
        return ApiResponse.<User>builder().code(200).message("操作成功").data(new User(id, "u1", "p1")).build();
    }

    @DeleteMapping("/{id}")
    @ApiOperation(value = "删除用户（DONE）", notes = "备注")
    @ApiImplicitParam(name = "id", value = "用户编号", dataType = DataType.INT, paramType = ParamType.PATH)
    public void delete(@PathVariable Integer id) {
        log.info("单个参数用 ApiImplicitParam");
    }

    @PostMapping
    @ApiOperation(value = "添加用户（DONE）")
    public User post(@RequestBody User user) {
        log.info("如果是 POST PUT 这种带 @RequestBody 的可以不用写 @ApiImplicitParam");
        return user;
    }

    @PostMapping("/multipar")
    @ApiOperation(value = "添加用户（DONE）")
    public List<User> multipar(@RequestBody List<User> user) {
        log.info("如果是 POST PUT 这种带 @RequestBody 的可以不用写 @ApiImplicitParam");
        return user;
    }

    @PostMapping("/array")
    @ApiOperation(value = "添加用户（DONE）")
    public User[] array(@RequestBody User[] user) {
        log.info("如果是 POST PUT 这种带 @RequestBody 的可以不用写 @ApiImplicitParam");
        return user;
    }

    @PutMapping("/{id}")
    @ApiOperation(value = "修改用户（DONE）")
    public void put(@PathVariable Long id, @RequestBody User user) {
        log.info("如果你不想写 @ApiImplicitParam 那么 swagger 也会使用默认的参数名作为描述信息 ");
    }

    @PostMapping("/{id}/file")
    @ApiOperation(value = "文件上传（DONE）")
    public String file(@PathVariable Long id, @RequestParam("file") MultipartFile file) {
        log.info(file.getContentType());
        log.info(file.getName());
        log.info(file.getOriginalFilename());
        return file.getOriginalFilename();
    }
}
```

### 8.1 类级注解

- `@Api(tags = "1.0.0-SNAPSHOT", description = "用户管理", value = "用户管理")`：在文档里把这个 Controller 归为"用户管理"分组，`tags` 是分组标签（一个 tag 一个分组）。
- `@Slf4j`：Lombok 注解，自动注入 `log` 对象，直接 `log.info(...)` 打日志，不用手写 `LoggerFactory.getLogger(...)`。

### 8.2 方法级注解

| 注解 | 作用 |
| --- | --- |
| `@ApiOperation(value = "...", notes = "...")` | 接口名称和备注说明 |
| `@ApiImplicitParam` | 描述单个非 body 参数（query/path 里的参数） |
| `@ApiImplicitParams` | 包裹多个 `@ApiImplicitParam` |

**`@ApiImplicitParam` 的关键属性：**

```java
@ApiImplicitParam(
    name = "username",          // 参数名
    value = "用户名",            // 参数描述
    dataType = DataType.STRING, // 数据类型（STRING/INT/LONG...）
    paramType = ParamType.QUERY,// 参数位置（QUERY/PATH/BODY/HEADER/FORM）
    defaultValue = "xxx"        // 默认值
)
```

注意 `DataType` 和 `ParamType` 是 battcn 提供的常量类（`com.battcn.boot.swagger.model.DataType`），比原生字符串 `"string"` 更类型安全，避免拼错。

### 8.3 一个重要规律：`@RequestBody` 参数不用写 `@ApiImplicitParam`

看 `post`、`put` 方法：

```java
@PostMapping
@ApiOperation(value = "添加用户（DONE）")
public User post(@RequestBody User user) { ... }   // 没写 @ApiImplicitParam
```

**规律**：当参数用 `@RequestBody` 标记时，Swagger 会自动解析 `User` 类的 `@ApiModel`/`@ApiModelProperty` 生成文档，不用再手写 `@ApiImplicitParam`。只有 query/path/form 类型的参数（如 `@PathVariable`、`@RequestParam`）才需要手动用 `@ApiImplicitParam` 描述。

这是 Swagger 的核心设计：**body 参数靠实体类注解自动推断，非 body 参数靠 `@ApiImplicitParam` 手动描述**。

### 8.4 支持的返回类型

这个 Controller 展示了 Swagger 能正确文档化多种返回类型：

- `ApiResponse<User>`：泛型响应体包裹单个对象
- `User`：直接返回对象
- `List<User>`：返回集合
- `User[]`：返回数组
- `void`：无返回
- `String`：返回字符串

Swagger 会根据返回类型自动生成响应示例，泛型 `ApiResponse<User>` 会展开成 `{ code, message, data: { id, name, job } }`。

---

## 九、运行与验证

### 9.1 启动

```sh
mvn spring-boot:run
```

### 9.2 访问文档

浏览器打开：`http://localhost:8080/demo/swagger-ui.html#/`

会弹出 Basic 认证框，输入：

- 用户名：`xkcoding`
- 密码：`123456`

认证通过后看到美化版的 Swagger 文档界面，包含：

- 顶部文档标题、描述、版本、联系人
- 按 `@Api` tags 分组的接口列表（用户管理）
- 每个接口的请求参数、响应示例、全局响应码（400/404/500）
- 在线调试功能（填参数 → 发请求 → 看响应）

### 9.3 测试接口

在文档页面点开"条件查询"，填 `username=Claude`，点"Try it out"，等价于发：

```http
GET http://localhost:8080/demo/user?username=Claude
```

返回：

```json
{
  "code": 200,
  "message": "操作成功",
  "data": { "id": 1, "name": "Claude", "job": "JAVA" }
}
```

---

## 十、动手练习

1. **关闭认证**：把 `spring.swagger.security.filter-plugin` 改成 `false`，重启，验证访问文档不再需要账号密码。
2. **关闭 Swagger**：把 `spring.swagger.enabled` 改成 `false`，重启，访问 `/demo/swagger-ui.html` 应返回 404——体会"配置开关"的便利。
3. **改扫描包**：把 `base-package` 改成一个不存在的包，重启，验证文档里没有任何接口。
4. **加一个接口**：在 UserController 加一个 `@GetMapping("/count")` 返回 `ApiResponse<Long>`，重启，验证文档自动出现新接口（不用改任何配置）。
5. **对比原生**：回头看 `demo-swagger` 模块的 `SwaggerConfig.java`，对比"写配置类"和"写 yml"两种方式的代码量。
6. **加全局响应码**：给 PUT 方法也配置一组 400/404/500 的 `global-response-messages`，验证文档里 PUT 接口也展示了这些响应码。

---

## 十一、本模块知识点总结（结合实际开发详解）

增强版 Swagger 是实际项目里高频使用的方案，下面把核心知识点放到真实开发场景讲透。

### 11.1 原生 Swagger vs 增强版：怎么选？

**实际开发中的选择：**

| 维度 | 原生 springfox | 增强版（battcn/Knife4j） |
| --- | --- | --- |
| 依赖 | springfox-swagger2 + springfox-swagger-ui | 一个 starter |
| 配置方式 | 写 SwaggerConfig + Docket Bean | 全在 yml |
| UI 美观 | 简陋英文界面 | 美化、支持搜索/分组 |
| 登录验证 | 需自己写过滤器 | 内置开关 |
| 全局响应码 | Docket.globalResponses() | yml 配置 |
| 注解体系 | springfox 注解 | **完全相同**（兼容） |
| 社区活跃度 | springfox 已停止维护 | Knife4j 活跃 |

**最佳实践：**

- 新项目直接用增强版（推荐 Knife4j，比 battcn 更主流、更新更勤）。
- 老项目从原生迁移到增强版：业务代码的 `@Api`/`@ApiOperation` 注解不用改，只需删 `SwaggerConfig`、加 starter 依赖、写 yml。
- Spring Boot 2.6+ 用 springfox 会有启动报错（路径匹配策略变化），必须用 Knife4j 或加 `spring.mvc.pathmatch.matching-strategy=ant_path_matcher`。

**常见坑：**

- 以为换增强版要重写所有注解——其实注解体系完全兼容，迁移成本极低。
- Spring Boot 版本和 Swagger 增强版不兼容：battcn 2.1.2 配合 Spring Boot 2.1.x，高版本 Spring Boot 要用更新的 Knife4j（如 4.x）。

### 11.2 配置化 vs 代码化：Starter 的设计哲学

本模块最大的启示是：**能用配置解决的，就不要写代码**。

原生 Swagger 要写 `SwaggerConfig`：

```java
@Bean
public Docket api() {
    return new Docket(DocumentationType.SWAGGER_2)
        .apiInfo(new ApiInfoBuilder()
            .title("spring-boot-demo")
            .description("...")
            .version("1.0.0")
            .build())
        .select()
        .apis(RequestHandlerSelectors.basePackage("com.xkcoding"))
        .paths(PathSelectors.any())
        .build();
}
```

增强版只要 yml：

```yaml
spring:
  swagger:
    enabled: true
    title: spring-boot-demo
    base-package: com.xkcoding
```

**实际开发中的意义：**

1. **运维友好**：改文档标题/扫描包不用改代码、不用重新打包，改 yml 重启即可。
2. **环境隔离**：dev 环境开 Swagger，prod 环境用 `spring.swagger.enabled=false` 关掉，配合 Profile 轻松实现。
3. **降低出错**：yml 配置比 Java 代码更"声明式"，不容易写错。

**最佳实践：** 评估一个第三方库是否"Spring Boot 友好"，就看它有没有提供 starter + 自动配置。有 starter 的优先用，没有的再考虑手写配置类。

**常见坑：** starter 的配置项前缀（这里是 `spring.swagger`）容易记错，用 IDE 的配置元数据提示（Ctrl+空格）能避免。battcn 的配置前缀是 `spring.swagger`，Knife4j 是 `knife4j`/`springdoc`，别混淆。

### 11.3 Swagger 注解体系速查

无论原生还是增强版，注解都是 springfox 的同一套，必须记牢：

| 注解 | 作用位置 | 作用 |
| --- | --- | --- |
| `@Api` | Controller 类 | 分组标签 |
| `@ApiOperation` | 方法 | 接口名称/备注 |
| `@ApiImplicitParam` | 方法 | 单个非 body 参数描述 |
| `@ApiImplicitParams` | 方法 | 包裹多个参数描述 |
| `@ApiModel` | 实体类 | 模型名称/描述 |
| `@ApiModelProperty` | 实体字段 | 字段描述/是否必填 |
| `@ApiParam` | 参数 | 直接在参数上描述（替代 ApiImplicitParam） |
| `@ApiResponse` | 方法 | 自定义响应码说明 |

**实际开发的最佳实践：**

1. **body 参数靠实体注解，非 body 参数靠 `@ApiImplicitParam`**：这是核心规律，别在 `@RequestBody` 参数上多此一举写 `@ApiImplicitParam`。
2. **必填字段标 `required = true`**：文档里会标红，前端联调时一眼看出哪些必须传。
3. **用 `notes` 补充复杂说明**：`@ApiOperation(value="简短名", notes="详细说明")`，value 给标题，notes 给正文。
4. **统一响应体**：所有接口返回 `ApiResponse<T>`，文档结构一致，前端封装一次请求库就能通用。

**常见坑：**

- `@ApiImplicitParam` 的 `paramType` 写错：把 PATH 参数写成 QUERY，文档里参数位置不对，前端按文档传参会失败。
- `dataType` 用字符串拼错：写成 `"ing"` 而不是 `"int"`，文档类型显示异常。用 battcn 的 `DataType.INT` 常量可避免。
- 泛型响应体不指定类型参数：`ApiResponse` 不写 `<User>`，Swagger 无法推断 data 结构，文档里 data 显示成 `object`。

### 11.4 文档安全：生产环境必须关 Swagger

Swagger 把所有接口结构、参数、甚至实体字段都暴露出来，生产环境开放有严重安全风险（攻击者能据此构造请求）。

**本模块的内置 Basic 认证**：

```yaml
spring:
  swagger:
    security:
      filter-plugin: true
      username: xkcoding
      password: 123456
```

但这只是"挡住文档页面"，接口本身还是能调。生产环境更彻底的做法：

**最佳实践（按严格度递增）：**

1. **Profile 隔离**：`application-prod.yml` 里 `spring.swagger.enabled: false`，生产完全不加载 Swagger。
2. **网关拦截**：在 Nginx/Gateway 层把 `/swagger-*`、`/v2/api-docs`、`/v3/api-docs` 路径在生产环境返回 403。
3. **内网-only**：Swagger 只在内网/VPN 可达环境开放，公网完全屏蔽。

**常见坑：**

- 只关了 `swagger-ui.html` 页面，但 `/v2/api-docs`（JSON 接口）仍开放，攻击者直接抓 JSON 拿到全部接口结构。**必须连 JSON 接口一起关。**
- Basic 认证用弱口令（如本 demo 的 `xkcoding/123456`），生产必须用强密码或改用 OAuth。

### 11.5 全局响应码：给前端完整的异常预期

本模块在 yml 配置了 GET/POST 的 400/404/500 响应示例，这是原生 Swagger 默认没有的。

```yaml
global-response-messages:
  GET[0]:
    code: 400
    message: Bad Request，一般为请求参数不对
```

**实际开发中的价值：**

- 前端联调时，文档里直接能看到"参数错了返回 400 长这样"，不用等真出 bug 才知道异常结构。
- 配合统一异常处理（`demo-exception-handler` 模块），异常返回的 `{ code, message }` 结构和正常返回一致，前端用同一套逻辑处理。

**最佳实践：** 给每个 HTTP 方法配齐 400（参数错）、401（未认证）、403（无权限）、404（找不到）、500（服务器错）的全局响应码，文档才完整。

**常见坑：** 全局响应码的 message 写得太技术化（如 `NullPointerException`），前端看不懂。message 要写用户能理解的业务描述。

### 11.6 Swagger 的演进：从 springfox 到 springdoc

本模块用的是 Swagger 2（OpenAPI 2.0）+ springfox 体系。但业界已在向 OpenAPI 3 迁移：

| 体系 | 规范 | 库 | 状态 |
| --- | --- | --- | --- |
| Swagger 2 | OpenAPI 2.0 | springfox + 增强版 | 停止维护 |
| OpenAPI 3 | OpenAPI 3.0 | springdoc-openapi | 主流 |
| Knife4j 4.x | OpenAPI 3 | knife4j + springdoc | 国内主流 |

**实际开发的建议：**

- 新项目（Spring Boot 2.6+ / 3.x）直接用 springdoc-openapi + Knife4j 4.x，注解从 `@Api` 换成 `@Tag`、`@Operation` 等。
- 老项目（Spring Boot 2.1~2.5）可继续用本模块的 springfox + battcn 方案，够用。
- 本模块的价值在于理解"Swagger 的本质"——注解描述接口 + 自动生成文档，换库只是换注解名，思想不变。

> 💡 前端类比：这就像从 RESTful 文档工具（swagger）演进到 GraphQL 的 schema 自文档——核心都是"接口即文档"，让前后端协作不再靠口头约定。

---

> 📌 **学习建议**：Swagger 是前后端协作的"契约"。作为前端转后端的工程师，你以前是 Swagger 文档的"消费者"（看文档调接口），现在要成为"生产者"（写注解生成文档）。养成习惯：**每写一个接口，立刻补全 `@ApiOperation` 和参数注解**，别等接口写完一堆才补——注释和代码一起写，才不会遗漏。另外记住生产环境关 Swagger 这条铁律，这是线上事故的常见来源。
