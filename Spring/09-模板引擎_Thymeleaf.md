# 09 - Spring Boot 集成 Thymeleaf 模板引擎

> 对应项目模块：`demo-template-thymeleaf`
> 前置知识：已学完前序模块，了解 `@Controller`、`application.yml`、Maven 依赖基本用法
> 学习目标：理解服务端模板引擎的概念，掌握 Thymeleaf 在 Spring Boot 中的集成方式、常用语法（变量、循环、条件、片段复用），能独立用 Thymeleaf 渲染一个页面。

---

## 一、本模块要解决什么问题？

前面几个模块，控制器返回的都是 JSON（`@RestController` + `@ResponseBody`），这是现代前后端分离架构的主流。但在某些场景下，你仍然需要**服务端渲染页面**——后端把数据填进 HTML 模板，直接返回一个完整的网页给浏览器：

- 后台管理系统（admin 界面、监控面板）
- 邮件模板（欢迎邮件、通知邮件）
- 静态官网、帮助文档
- 报表导出（PDF/HTML）

这些场景如果用纯前端框架（Vue/React）做，反而麻烦——要单独部署前端、处理 SEO、增加一层接口调用。直接用模板引擎在服务端渲染，简单高效。

**Thymeleaf 是 Spring Boot 官方推荐的模板引擎**，它的最大特点是"自然模板"：模板文件本身就是合法的 HTML，可以直接用浏览器打开预览，不像 JSP 那样必须经过容器才能渲染。

> 💡 前端类比：Thymeleaf 类似 Vue 的**服务端渲染（SSR）**，或者更接近的类比是 Pug/EJS/Handlebars 这类模板引擎——在 HTML 里嵌入特殊语法，服务端把数据填进去后输出纯 HTML。区别是 Thymeleaf 用的是 HTML 自定义属性（`th:text`），不破坏 HTML 结构。

本模块的最终效果：访问首页，如果没登录就跳转到登录页，输入用户名密码后登录，再回到首页显示"欢迎登录，xxx！"。

---

## 二、先看项目结构

```
demo-template-thymeleaf/
├── pom.xml
└── src/main/
    ├── java/com/xkcoding/template/thymeleaf/
    │   ├── SpringBootDemoTemplateThymeleafApplication.java  # 启动类
    │   ├── controller/
    │   │   ├── IndexController.java      # 首页：判断登录态
    │   │   └── UserController.java       # 登录页 + 登录处理
    │   └── model/
    │       └── User.java                 # 用户实体
    └── resources/
        ├── application.yml               # 配置（含 thymeleaf 配置）
        └── templates/                    # 模板根目录
            ├── common/
            │   └── head.html             # 公共片段（页头）
            └── page/
                ├── index.html            # 首页
                └── login.html           # 登录页
```

注意几个约定：

1. **模板默认放在 `src/main/resources/templates/` 下**——这是 Spring Boot 对 Thymeleaf 的默认约定，不需要配置，放进去就能被找到。
2. **静态资源（CSS/JS/图片）默认放 `src/main/resources/static/`**——本模块没用，但要知道。
3. 启动类在根包 `com.xkcoding.template.thymeleaf`，`controller`、`model` 是子包，`@ComponentScan` 能扫到。

---

## 三、pom.xml：引入 Thymeleaf 起步依赖

```xml
<dependencies>
    <!-- Thymeleaf 起步依赖 -->
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

    <!-- Hutool 工具类 -->
    <dependency>
        <groupId>cn.hutool</groupId>
        <artifactId>hutool-all</artifactId>
    </dependency>
</dependencies>
```

**`spring-boot-starter-thymeleaf` 一键引入了什么？**

- `thymeleaf-spring5`：Thymeleaf 与 Spring MVC 的整合包
- `thymeleaf`：Thymeleaf 核心引擎
- `thymeleaf-extras-java8time`：Java 8 时间 API 的额外支持

引入这个 Starter 后，Spring Boot 的自动配置会自动注册 `ThymeleafViewResolver`（视图解析器），当控制器返回一个视图名（如 `"page/index"`），解析器就会去 `templates/` 目录下找 `page/index.html` 并渲染。

> 💡 前端类比：这像在 Vite 里 `npm install` 一个模板插件后，自动配置好对应的 loader。Spring Boot 的 Starter 就是"装了就自动配好"。

---

## 四、application.yml：Thymeleaf 配置

```yaml
server:
  port: 8080
  servlet:
    context-path: /demo
spring:
  thymeleaf:
    mode: HTML
    encoding: UTF-8
    servlet:
      content-type: text/html
    cache: false
```

| 配置项 | 作用 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `spring.thymeleaf.mode` | 模板模式 | `HTML` | `HTML`（宽松 HTML5）、`XML`、`TEXT` 等 |
| `spring.thymeleaf.encoding` | 模板文件编码 | `UTF-8` | |
| `spring.thymeleaf.servlet.content-type` | 响应 Content-Type | `text/html` | |
| `spring.thymeleaf.cache` | 是否开启模板缓存 | `true` | **开发时设 `false`**，改模板立即生效 |

**关于 `cache: false`（重要）：**

- Thymeleaf 默认开启缓存，解析过的模板会缓存起来，下次请求直接用，提高性能。
- 但开发时你频繁改模板，如果开了缓存，改了不生效（要重启），所以**开发环境必须设 `false`**。
- **生产环境设 `true`**，提升性能。

> 💡 前端类比：这像 webpack-dev-server 的 HMR（热更新）——开发时要实时刷新，生产时要缓存压缩。同理，Thymeleaf 缓存在生产开、开发关。

---

## 五、Model：用户实体

`model/User.java`：

```java
@Data
public class User {
    private String name;
    private String password;
}
```

- `@Data`：Lombok 自动生成 getter/setter/toString 等。
- 这是一个普通 POJO（Plain Old Java Object），用于承载表单提交的用户名密码。

> 💡 前端类比：这就像一个 TypeScript 的 `interface User { name: string; password: string }`，但在 Java 里要写成类，并由 Lombok 生成访问方法。

---

## 六、Controller：`@Controller` 与 `ModelAndView`

这里和前面的 `@RestController` 有本质区别，必须重点理解。

### 6.1 `@Controller` vs `@RestController`

```java
@Controller   // 注意：不是 @RestController
public class IndexController { ... }
```

| 注解 | 行为 | 适用场景 |
| --- | --- | --- |
| `@Controller` | 方法返回的字符串被当作**视图名**，跳转到模板渲染 | 服务端渲染页面 |
| `@RestController` | 方法返回值直接写进响应体（JSON） | 前后端分离 API |

`@RestController` = `@Controller` + `@ResponseBody`。本模块要去渲染页面，所以用 `@Controller`。如果方法返回字符串 `"page/index"`，Spring 会把它当视图名，去找 `templates/page/index.html` 渲染。

### 6.2 IndexController：首页 + 登录态判断

```java
@Controller
@Slf4j
public class IndexController {

    @GetMapping(value = {"", "/"})
    public ModelAndView index(HttpServletRequest request) {
        ModelAndView mv = new ModelAndView();

        User user = (User) request.getSession().getAttribute("user");
        if (ObjectUtil.isNull(user)) {
            mv.setViewName("redirect:/user/login");
        } else {
            mv.setViewName("page/index");
            mv.addObject(user);
        }

        return mv;
    }
}
```

逐行拆解：

- `@Controller`：标记为控制器，返回视图名而非 JSON。
- `@Slf4j`：Lombok 注解，自动注入一个 `log` 对象，可以用 `log.info(...)` 打日志，省得手动声明 logger。
- `@GetMapping(value = {"", "/"})`：映射根路径，空字符串和 `/` 都匹配。所以访问 `http://localhost:8080/demo/` 或 `http://localhost:8080/demo` 都进这个方法。
- `ModelAndView`：Spring MVC 的核心对象，**同时承载视图名和数据**。`setViewName` 设视图名，`addObject` 往模板里塞数据。
- `request.getSession().getAttribute("user")`：从 session 取登录用户。这是最原始的登录态判断方式。
- `ObjectUtil.isNull(user)`：Hutool 的判空工具，等价于 `user == null`。
- `mv.setViewName("redirect:/user/login")`：视图名以 `redirect:` 开头表示**重定向**，浏览器会跳转到 `/demo/user/login`。
- `mv.setViewName("page/index")`：不带 `redirect:` 前缀，表示**转发到模板**，找 `templates/page/index.html` 渲染。
- `mv.addObject(user)`：把 user 对象塞进模型，模板里就能用 `${user.name}` 取到。

> 💡 前端类比：`ModelAndView` 有点像 SSR 框架里的 `render(template, data)`——同时指定模板和数据。`addObject` 就是往数据对象里加字段。

### 6.3 UserController：登录页 + 登录处理

```java
@Controller
@RequestMapping("/user")
@Slf4j
public class UserController {

    @PostMapping("/login")
    public ModelAndView login(User user, HttpServletRequest request) {
        ModelAndView mv = new ModelAndView();
        mv.addObject(user);
        mv.setViewName("redirect:/");
        request.getSession().setAttribute("user", user);
        return mv;
    }

    @GetMapping("/login")
    public ModelAndView login() {
        return new ModelAndView("page/login");
    }
}
```

- `@RequestMapping("/user")`：类级别映射，类内所有方法的路径都加 `/user` 前缀。
- `@PostMapping("/login")`：处理 `POST /user/login`，表单提交走这里。
- `@GetMapping("/login")`：处理 `GET /user/login`，显示登录页。**方法重载**——同名方法不同 HTTP 方法，这是 RESTful 的常见写法。
- `public ModelAndView login(User user, ...)`：**表单参数自动绑定到对象**！表单里有 `name="name"` 和 `name="password"` 的 input，Spring MVC 自动把它们组装成 `User` 对象。这叫"命令对象绑定"。
- `request.getSession().setAttribute("user", user)`：把用户存进 session，标记登录态。
- `mv.setViewName("redirect:/")`：登录成功后重定向回首页（`redirect:/` 会跳到 `http://localhost:8080/demo/`）。

> 💡 前端类比：表单参数自动绑定到 `User` 对象，就像前端框架里表单提交时 `new FormData(form)` 自动收集字段，只不过 Spring MVC 把它直接映射成了强类型对象。

> ⚠️ 注意：本 demo 的登录是"假登录"，不校验密码，输入什么都能登录成功。真实项目要用 Spring Security 或 Shiro（后续模块讲）做认证授权。

---

## 七、Thymeleaf 模板：核心语法

这是本模块的重点。Thymeleaf 用 `th:` 命名空间的属性来嵌入逻辑，HTML 本身保持合法。

### 7.1 声明 Thymeleaf 命名空间

每个模板的 `<html>` 标签都要加：

```html
<html lang="en" xmlns:th="http://www.thymeleaf.org">
```

这声明了 `th` 前缀，IDE 才能识别 `th:text` 等属性。它不影响浏览器渲染（浏览器会忽略未知属性）。

### 7.2 公共片段 `head.html`：片段定义

`templates/common/head.html`：

```html
<!DOCTYPE html>
<html xmlns:th="http://www.thymeleaf.org">
<head th:fragment="header">
    <meta charset="UTF-8">
    <meta name="viewport"
          content="width=device-width, user-scalable=no, initial-scale=1.0, maximum-scale=1.0, minimum-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="ie=edge">
    <title>spring-boot-demo-template-thymeleaf</title>
</head>
<body>
</body>
</html>
```

- `th:fragment="header"`：定义一个名为 `header` 的**片段**，可以被其他模板引用复用。

> 💡 前端类比：这就像 Vue 的组件或 `<template>` 片段，把公共部分抽出来复用。这里把 `<head>` 里的 meta、title 抽成片段，每个页面引用它，避免重复。

### 7.3 首页 `index.html`：变量输出 + 片段引用

```html
<!doctype html>
<html lang="en" xmlns:th="http://www.thymeleaf.org">
<header th:replace="~{common/head :: header}"></header>
<body>
<div id="app" style="margin: 20px 20%">
    欢迎登录，<span th:text="${user.name}"></span>！
</div>
</body>
</html>
```

两个核心语法：

**① 片段引用 `th:replace`**

```html
<header th:replace="~{common/head :: header}"></header>
```

- `~{common/head :: header}`：引用 `common/head.html` 文件里名为 `header` 的片段。
- `th:replace`：用片段**整体替换**当前标签（当前 `<header>` 标签会被片段内容替换）。
- 还有个类似的 `th:insert`：把片段**插入**当前标签内部（保留当前标签）。区别类似"替换"和"追加"。

**② 变量输出 `th:text`**

```html
<span th:text="${user.name}"></span>
```

- `${user.name}`：OGNL/SpEL 表达式，从模型里取 `user` 对象的 `name` 属性。
- `th:text`：把表达式的值设置为标签的文本内容，渲染后变成 `<span>Claude</span>`。

> 💡 前端类比：`th:text="${user.name}"` 完全等价于 Vue 的 `<span>{{ user.name }}</span>`。`${...}` 是变量插值，`th:text` 是把它设到 DOM 文本上。

### 7.4 登录页 `login.html`：表单

```html
<!doctype html>
<html lang="en" xmlns:th="http://www.thymeleaf.org">
<header th:replace="~{common/head :: header}"></header>
<body>
<div id="app" style="margin: 20px 20%">
    <form action="/demo/user/login" method="post">
        用户名<input type="text" name="name" placeholder="用户名"/>
        密码<input type="password" name="password" placeholder="密码"/>
        <input type="submit" value="登录">
    </form>
</div>
</body>
</html>
```

- 注意 `action="/demo/user/login"`：因为配了 `context-path: /demo`，表单提交路径要带 `/demo` 前缀。
- `name="name"` 和 `name="password"`：input 的 name 必须和 `User` 对象的字段名对应，Spring MVC 才能自动绑定。

### 7.5 Thymeleaf 常用语法速查（扩展）

本模块只用了 `th:text` 和 `th:replace`，但实际开发常用语法还有这些：

| 语法 | 作用 | 示例 |
| --- | --- | --- |
| `th:text` | 设置文本内容 | `<span th:text="${user.name}">默认</span>` |
| `th:utext` | 设置富文本（不转义） | `<div th:utext="${htmlContent}"></div>` |
| `th:if` / `th:unless` | 条件渲染 | `<span th:if="${user != null}">已登录</span>` |
| `th:each` | 循环 | `<li th:each="u : ${users}" th:text="${u.name}"></li>` |
| `th:switch` / `th:case` | 多分支 | `<div th:switch="${user.role}">...</div>` |
| `th:href` | 动态链接 | `<a th:href="@{/user/{id}(id=${user.id})}">详情</a>` |
| `th:src` | 动态资源路径 | `<img th:src="@{/img/logo.png}">` |
| `th:object` | 绑定对象，内部用 `*{}` | `<form th:object="${user}"><input th:field="*{name}"></form>` |
| `th:fragment` | 定义片段 | `<div th:fragment="header">...</div>` |
| `th:replace` / `th:insert` | 引入片段 | `<div th:replace="~{common/head :: header}"></div>` |

**链接表达式 `@{...}`（重要）：**

```html
<a th:href="@{/user/list}">用户列表</a>
<!-- 渲染后自动带上 context-path：/demo/user/list -->
```

`@{...}` 会自动处理 `context-path`，所以**推荐用 `@{}` 而不是写死路径**。本 demo 的 form action 写死了 `/demo/user/login`，更规范的写法是 `th:action="@{/user/login}"`。

> 💡 前端类比：`@{}` 类似 Vue Router 的 `<router-link to="/user/list">`，自动处理 base 路径。写死路径就像硬编码 URL，换 context-path 就全坏了。

---

## 八、运行与验证

### 8.1 启动

```sh
mvn spring-boot:run
```

### 8.2 访问流程

1. 浏览器访问 `http://localhost:8080/demo/` → `IndexController.index()` → session 没 user → 重定向到 `/demo/user/login`
2. 显示登录页 `login.html`，输入用户名密码，点登录
3. 表单 POST 到 `/demo/user/login` → `UserController.login(User)` → user 存进 session → 重定向回 `/demo/`
4. 再次进 `IndexController.index()` → session 有 user → 渲染 `index.html`，显示"欢迎登录，xxx！"

### 8.3 验证模板缓存效果

把 `application.yml` 的 `cache` 改成 `true`（默认值），启动后访问页面，然后改 `index.html` 的文案，刷新——发现没变（用了缓存）。改回 `false` 重启，改模板立即生效。

---

## 九、动手练习

1. **加一个用户列表页**：在 `UserController` 加 `@GetMapping("/list")` 返回一个 `List<User>`，新建 `page/list.html` 用 `th:each` 循环渲染用户名。
2. **用 `th:if` 做条件渲染**：在 `index.html` 里，如果 user 为空显示"请登录"，非空显示"欢迎，xxx"。
3. **用 `@{}` 改造表单**：把 `login.html` 的 `action="/demo/user/login"` 改成 `th:action="@{/user/login}"`，验证效果一样且更健壮。
4. **体验 `th:object` + `th:field`**：用表单绑定语法重写登录页，`<form th:object="${user}" th:action="@{/user/login}" method="post"><input th:field="*{name}"></form>`。
5. **抽一个公共页脚**：仿照 `head.html`，新建 `common/footer.html` 定义 `th:fragment="footer"`，在页面里用 `th:replace` 引入。
6. **故意制造模板错误**：把 `th:text="${user.name}"` 写成 `th:text="${user.age}"`（User 没 age 字段），观察 Thymeleaf 的报错信息，理解它的错误提示。

---

## 十、本模块知识点总结（结合实际开发详解）

模板引擎是服务端渲染的核心，理解它的定位和用法，能帮你应对后台管理、邮件模板等场景。下面把核心知识点放到真实开发里讲透。

### 10.1 什么时候用模板引擎，什么时候用前后端分离？

**实际开发中的架构选型：**

| 场景 | 推荐方案 | 理由 |
| --- | --- | --- |
| 面向终端用户的 C 端应用 | 前后端分离（Vue/React + API） | 交互复杂、需要富客户端体验 |
| 后台管理系统 | 看团队：可前后端分离，也可模板引擎 | 模板引擎开发快，但交互体验一般 |
| 邮件模板、PDF 报表 | Thymeleaf | 需要服务端生成完整 HTML |
| 静态官网、帮助文档 | Thymeleaf | SEO 友好、无需前端工程化 |
| 内部工具、监控面板 | Thymeleaf + 轻量前端 | 快速搭建 |

**最佳实践：**

- **新项目优先前后端分离**：后端只提供 API，前端用框架，职责清晰、体验好、易扩展。
- **模板引擎用于"服务端必须生成完整 HTML"的场景**：邮件、报表、PDF、SEO 页面。这些场景下 Thymeleaf 是首选。
- **不要在一个项目里混用两种模式做同一件事**：要么全 API，要么全模板，混用会导致维护混乱。

**常见坑：**

- 用 `@RestController` 却想渲染页面：返回的字符串被当 JSON 写进响应体，不会跳转模板。**渲染页面必须用 `@Controller`**。
- 以为模板引擎能做复杂交互：Thymeleaf 是服务端渲染，输出的是静态 HTML，没有客户端响应式能力。复杂交互还是得靠前端框架。

### 10.2 `@Controller` 与 `@RestController` 的本质区别

这是新手最容易混淆的点，必须彻底搞清。

**`@RestController` = `@Controller` + `@ResponseBody`**

- `@Controller`：方法返回值默认被当**视图名**，跳转模板。
- `@ResponseBody`：覆盖上面的默认行为，把返回值直接写进响应体（JSON）。

**实际开发中的灵活用法：**

1. **同一个类里混用**：用 `@Controller`，需要返回 JSON 的方法上加 `@ResponseBody`：

   ```java
   @Controller
   public class UserController {
       @GetMapping("/login")  // 返回视图名，渲染页面
       public String login() { return "login"; }

       @GetMapping("/info")   // 加了 @ResponseBody，返回 JSON
       @ResponseBody
       public User info() { return new User("x"); }

       @GetMapping("/list")
       @ResponseBody           // 返回 JSON 列表
       public List<User> list() { return ...; }
   }
   ```

2. **类级别用 `@RestController`**：所有方法都返回 JSON，适合纯 API 控制器。
3. **类级别用 `@Controller`**：默认渲染页面，个别方法加 `@ResponseBody` 返回 JSON，适合混合场景。

**最佳实践**：现代项目通常分两个包——`controller`（页面控制器，用 `@Controller`）和 `api`（API 控制器，用 `@RestController`），职责清晰。

### 10.3 `ModelAndView` vs `Model` vs `String` 视图名

控制器向模板传数据有三种写法，本模块用了 `ModelAndView`，但实际开发更常用后两种：

**① `ModelAndView`（本模块用法）：**

```java
public ModelAndView index() {
    ModelAndView mv = new ModelAndView();
    mv.setViewName("page/index");
    mv.addObject("user", user);
    return mv;
}
```

**② `Model` 参数 + 返回视图名字符串（推荐）：**

```java
@GetMapping("/")
public String index(Model model) {
    model.addAttribute("user", user);
    return "page/index";   // 返回视图名
}
```

**③ `@ModelAttribute` 方法：**

```java
@GetMapping("/")
public String index(@ModelAttribute("user") User user) {
    return "page/index";
}
```

**最佳实践**：用 `Model` 参数 + 返回字符串视图名，最简洁。`ModelAndView` 适合需要同时操作视图和数据的复杂场景。Spring 官方文档也推荐 `Model` 写法。

> 💡 前端类比：`Model` 就像 React 的 props 或 SSR 的 `render(context)`，你往里塞数据，框架负责渲染。

### 10.4 Thymeleaf 的"自然模板"优势

Thymeleaf 相比 JSP/Freemarker 的最大卖点是"自然模板"——模板文件本身就是合法 HTML，能直接用浏览器打开。

**实际开发中的好处：**

1. **前端能参与模板开发**：前端同学可以直接用浏览器打开 `.html` 预览静态效果，不用启动 Java 服务。`th:` 属性会被浏览器当未知属性忽略，静态内容正常显示。
2. **设计稿协作**：设计师给的 HTML 稍加改造就能当模板，不用重写成 JSP 那种非标准语法。
3. **降低学习成本**：`th:text` 比 JSP 的 `<c:out>` 或 Freemarker 的 `${}` 更直观，且不破坏 HTML 结构。

**最佳实践：**

- 写模板时，给 `th:text` 等属性配上静态默认值，保证浏览器直开也有内容：

  ```html
  <span th:text="${user.name}">默认用户名</span>
  <!-- 浏览器直开显示"默认用户名"，服务端渲染后显示真实用户名 -->
  ```

- 这叫"原型态"设计，是 Thymeleaf 的核心设计哲学。

### 10.5 模板缓存：开发关、生产开

**实际开发的标准配置：**

```yaml
# application-dev.yml（开发环境）
spring:
  thymeleaf:
    cache: false   # 关闭缓存，改模板立即生效

# application-prod.yml（生产环境）
spring:
  thymeleaf:
    cache: true    # 开启缓存，提升性能
```

**原理**：Thymeleaf 解析模板后会把解析结果缓存，下次请求直接用缓存，跳过解析步骤。生产环境模板不变，开缓存能显著降低 CPU 和延迟。开发环境模板频繁改，关缓存才能热更新。

**常见坑：**

- 开发时忘了关缓存，改了模板不生效，以为代码写错了，debug 半天。
- 生产开了缓存但模板从外部加载（如数据库存模板），改了模板不生效——需要调用 `templateEngine.clearCache()` 手动清。

### 10.6 片段复用：`th:fragment` / `th:replace` / `th:insert`

这是 Thymeleaf 模板复用的核心，类似前端组件化。

**三种引入方式区别：**

| 语法 | 行为 | 类比 |
| --- | --- | --- |
| `th:replace` | 用片段**替换**当前标签（当前标签消失） | Vue 的 `<component :is>` 替换 |
| `th:insert` | 把片段**插入**当前标签内部（保留当前标签） | 保留外层 div |
| `th:include`（已废弃） | 只插入片段的内容（不含片段外层标签） | 旧用法，不推荐 |

**实际开发的标准布局：**

```
templates/
├── layout/
│   └── default.html     # 布局骨架（header + content + footer）
├── fragment/
│   ├── header.html     # 页头片段
│   ├── footer.html     # 页脚片段
│   └── sidebar.html    # 侧边栏片段
└── page/
    └── user-list.html  # 具体页面，引用布局
```

用 `th:fragment` 定义布局插槽，具体页面用 `th:replace` 填充内容，实现"装饰器模式"的页面复用。这是后台管理系统的标准模板组织方式。

**最佳实践：**

- 公共部分（页头、页脚、导航）抽成片段，避免每个页面重复。
- 用布局模板统一页面骨架，具体页面只写内容区域。
- 片段命名要语义化（`header`、`footer`），不要用 `fragment1`。

### 10.7 链接表达式 `@{}`：必须用，别写死路径

**实际开发铁律：模板里的所有链接都用 `@{}`，不要写死路径。**

```html
<!-- ❌ 错误：写死路径，换 context-path 全坏 -->
<a href="/demo/user/list">列表</a>

<!-- ✅ 正确：用 @{} 自动处理 context-path -->
<a th:href="@{/user/list}">列表</a>
```

`@{}` 会自动加上 `context-path` 前缀，还支持路径变量和查询参数：

```html
<a th:href="@{/user/{id}(id=${user.id},tab=info)}">详情</a>
<!-- 渲染：/demo/user/123?tab=info -->
```

**常见坑：**

- 本 demo 的 form action 写死了 `/demo/user/login`，如果 context-path 改了，表单就提交到错误地址。正确写法是 `th:action="@{/user/login}"`。
- 静态资源（CSS/JS）路径也要用 `@{}`：`<link th:href="@{/css/style.css}">`，否则换 context-path 后资源 404。

---

> 📌 **学习建议**：作为前端工程师，你可能觉得"都前后端分离了，学模板引擎干嘛"。但实际工作中，邮件模板、PDF 报表、后台管理页、SEO 页面这些场景，模板引擎仍是最高效的方案。把 Thymeleaf 当成"服务端版本的 Vue 模板"来理解——`th:text` 是 `{{}}`，`th:each` 是 `v-for`，`th:if` 是 `v-if`，`th:replace` 是组件引入。掌握这套映射后，Thymeleaf 的学习成本极低。重点是记住：**渲染页面用 `@Controller`，返回 JSON 用 `@RestController`，别搞混**。
