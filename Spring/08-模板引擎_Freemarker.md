# 08 - Spring Boot 集成 Freemarker 模板引擎

> 对应项目模块：`demo-template-freemarker`
> 前置知识：已学完前 7 个模块，了解 `@Controller`、`@RestController`、`application.yml`、构造器注入等基础
> 学习目标：理解服务端模板渲染的概念，掌握 Spring Boot 集成 Freemarker 的配置与用法，能用 `ModelAndView` 渲染页面、用 `<#include>` 复用模板片段。

---

## 一、本模块要解决什么问题？

前面几个模块的接口都返回 JSON（`@RestController` + `@ResponseBody`），这是现代前后端分离架构的主流。但在某些场景下，你仍然需要**服务端渲染页面**（SSR）：

- 后台管理系统、内部运营工具——不需要前端工程化，直接出页面最快
- 邮件模板、报表导出——需要把数据填进 HTML 模板
- SEO 要求高的官网首页——服务端渲染对搜索引擎更友好

模板引擎就是干这个的：**后端把数据塞进一个带占位符的 HTML 模板，输出最终 HTML 给浏览器**。

> 💡 前端类比：Freemarker 之于 Java 后端，相当于 EJS / Pug / Handlebars 之于 Node.js。如果你用过 Express 的 `res.render('index', { user })`，那 Spring 的 `ModelAndView` 几乎是同一个东西。也可以类比 Vue 的 SSR（`@vue/server-renderer`），只是这里没有组件化，纯字符串模板。

本模块演示：登录页 → 提交表单 → 把用户信息存进 Session → 主页读取并渲染欢迎语，全程服务端渲染，不写一行前端 JS。

---

## 二、项目结构

```
demo-template-freemarker/
├── pom.xml
└── src/main/
    ├── java/com/xkcoding/template/freemarker/
    │   ├── SpringBootDemoTemplateFreemarkerApplication.java   # 启动类
    │   ├── controller/
    │   │   ├── IndexController.java     # 主页：读 Session 决定渲染还是重定向
    │   │   └── UserController.java     # 登录页 + 登录处理
    │   └── model/
    │       └── User.java               # 用户实体
    └── resources/
        ├── application.yml             # Freemarker 配置
        └── templates/
            ├── common/
            │   └── head.ftl            # 公共 <head> 片段，被各页面 include
            └── page/
                ├── index.ftl           # 主页模板
                └── login.ftl           # 登录页模板
```

注意模板文件放在 `src/main/resources/templates/` 下——这是 Spring Boot 模板引擎的**默认目录约定**，类似前端项目的 `public/` 或 `views/`。

---

## 三、pom.xml：引入 Freemarker 起步依赖

```xml
<dependencies>
    <!-- Freemarker 起步依赖 -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-freemarker</artifactId>
    </dependency>

    <!-- Web 起步依赖 -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-web</artifactId>
    </dependency>

    <!-- 测试 / Lombok / Hutool -->
    ...
</dependencies>
```

**关键点：**

- `spring-boot-starter-freemarker`：一键引入 Freemarker 核心库 + Spring MVC 集成 + 自动配置。引了它，Spring Boot 就会自动注册一个 `FreeMarkerViewResolver`，把 Controller 返回的视图名解析成 `templates/xxx.ftl`。
- 还是要引 `spring-boot-starter-web`：模板引擎本身不启动 Web 服务，它只是 Web 层的一个渲染器，底层仍依赖 Spring MVC + 内嵌 Tomcat。

> 💡 前端类比：这像在 Express 里同时装 `express` 和 `ejs`——`express` 提供 HTTP 服务，`ejs` 提供模板渲染能力，两者配合才能 `res.render()`。

---

## 四、application.yml：Freemarker 配置

```yaml
server:
  port: 8080
  servlet:
    context-path: /demo

spring:
  freemarker:
    suffix: .ftl        # 模板文件后缀
    cache: false        # 是否缓存模板（开发期关掉，改模板即时生效）
    charset: UTF-8      # 模板编码
```

| 配置项 | 作用 | 默认值 |
| --- | --- | --- |
| `spring.freemarker.suffix` | 视图名拼上这个后缀找模板文件 | `.ftl` |
| `spring.freemarker.cache` | 是否缓存编译后的模板 | `true` |
| `spring.freemarker.charset` | 读取模板的字符编码 | `UTF-8` |
| `spring.freemarker.template-loader-path` | 模板目录 | `classpath:/templates/` |

**为什么 `cache: false`？** Freemarker 默认缓存模板编译结果以提升性能。但开发时你会频繁改 `.ftl`，如果开着缓存，每次改完都要重启才能看到效果——所以开发环境关掉，生产环境再开回来（生产模板不变，缓存能省重复编译开销）。

> 💡 前端类比：这像 Vite 的 HMR（热更新）——开发时模板改动即时生效，不用重启。生产环境则用缓存/预编译提升性能。

---

## 五、User 实体

```java
@Data
public class User {
    private String name;
    private String password;
}
```

简单的 POJO，用 Lombok `@Data` 生成 getter/setter。`name` 和 `password` 会和登录表单的 `input name="name"`、`input name="password"` 一一对应（Spring MVC 自动按字段名绑定表单参数）。

---

## 六、IndexController：主页（含重定向逻辑）

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

### 6.1 `@Controller`（注意：不是 `@RestController`）

这里用的是 `@Controller`，**没有** `@ResponseBody`。区别至关重要：

- `@RestController`：方法返回值直接写进响应体（返回 JSON）
- `@Controller`：方法返回值被当成**视图名**，交给视图解析器去找模板渲染

如果这里误用 `@RestController`，返回的 `"page/index"` 字符串会原样输出到页面，而不是渲染模板。

### 6.2 `@GetMapping(value = {"", "/"})`：映射根路径

一个注解映射两个路径——空字符串和 `/`，都映射到这个方法。所以访问 `http://localhost:8080/demo/` 和 `http://localhost:8080/demo` 都会进这里。

### 6.3 `ModelAndView`：模型 + 视图

`ModelAndView` 是 Spring MVC 的核心类，承载两样东西：

- **View（视图名）**：`mv.setViewName("page/index")` 告诉 Spring "去渲染 `page/index` 这个模板"（拼上后缀 `.ftl` 和前缀 `templates/`，实际找 `templates/page/index.ftl`）。
- **Model（模型数据）**：`mv.addObject(user)` 把 user 对象塞进模型，模板里就能用 `${user.name}` 取到。

> 💡 前端类比：这就是 Express 的 `res.render('page/index', { user })`——第一个参数是模板，第二个是数据。`ModelAndView` 把两者打包在一起返回。

### 6.4 重定向 vs 转发

```java
mv.setViewName("redirect:/user/login");   // 重定向
mv.setViewName("page/index");              // 转发（渲染模板）
```

- **`redirect:` 前缀**：告诉浏览器"跳转到这个 URL"，浏览器地址栏会变成 `/demo/user/login`，是**两次请求**。这里未登录就重定向到登录页。
- **无前缀（直接视图名）**：服务端渲染模板，浏览器地址栏不变，是**一次请求**。

> 💡 前端类比：`redirect:` 相当于 HTTP 302 跳转（像 `router.push` 但由服务端发起）；直接视图名相当于服务端把模板渲染好直接返回 HTML。

### 6.5 Session 判断

```java
User user = (User) request.getSession().getAttribute("user");
```

从 Session 取登录用户。没登录就跳登录页，登录了就渲染主页并显示用户名。这是最朴素的登录态管理（后续 `demo-session` 模块会讲 Spring Session 分布式 Session）。

---

## 七、UserController：登录页 + 登录处理

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

### 7.1 类级 `@RequestMapping("/user")`

类上加 `@RequestMapping("/user")`，类里所有方法的路径都会带上 `/user` 前缀。所以：

- `@GetMapping("/login")` → 实际路径 `GET /user/login`（登录页）
- `@PostMapping("/login")` → 实际路径 `POST /user/login`（提交登录）

同路径不同 HTTP 方法，这是 RESTful 的常见写法。

### 7.2 表单对象绑定

```java
public ModelAndView login(User user, ...) {
```

方法参数直接写 `User user`，Spring MVC 会自动把表单里 `name="x"` 的字段按属性名绑定到 User 对象的对应字段。表单提交 `name=alice&password=123`，就得到 `User{name='alice', password='123'}`。

> 💡 前端类比：这像 Express 的 `body-parser` 把 `application/x-www-form-urlencoded` 解析成对象，但 Spring 更进一步——直接按字段名映射成强类型对象，不用手动取值赋值。

### 7.3 登录流程

1. 用户访问 `GET /demo/` → IndexController 发现 Session 没用户 → 重定向到 `/demo/user/login`
2. `GET /user/login` → 返回 `page/login` 模板（登录表单页）
3. 用户提交表单 → `POST /user/login` → 把 User 存进 Session → 重定向回 `/demo/`
4. 再次进 IndexController → Session 有用户 → 渲染 `page/index`，显示"欢迎登录，{用户名}！"

---

## 八、模板文件

### 8.1 公共片段 `common/head.ftl`

```html
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="...">
    <meta http-equiv="X-UA-Compatible" content="ie=edge">
    <title>spring-boot-template-freemarker</title>
</head>
```

纯 HTML，没有 Freemarker 语法。作为公共的 `<head>` 片段被各页面复用。

### 8.2 登录页 `page/login.ftl`

```html
<!doctype html>
<html lang="en">
<#include "../common/head.ftl">
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

**`<#include "../common/head.ftl">`**：Freemarker 的 include 指令，把另一个模板的内容原样嵌入当前位置。路径相对于当前模板文件。这样所有页面共享同一个 `<head>`，改一处全生效。

> 💡 前端类比：这像 Vue 的组件引入、或 PHP 的 `include`、EJS 的 `<%- include('common/head') %>`。注意表单 `action` 要带上 context-path `/demo`，因为所有接口都有这个前缀。

### 8.3 主页 `page/index.ftl`

```html
<!doctype html>
<html lang="en">
<#include "../common/head.ftl">
<body>
<div id="app" style="margin: 20px 20%">
    欢迎登录，${user.name}！
</div>
</body>
</html>
```

**`${user.name}`**：Freemarker 的插值语法，把模型里 `user` 对象的 `name` 属性值输出到这里。`mv.addObject(user)` 传进来的 user，在这里被读取。注意 `user` 这个 key——`addObject(user)` 不指定 key 时，默认用类名首字母小写（`user`）作为 key。

---

## 九、运行与验证

### 9.1 启动

```sh
mvn spring-boot:run
```

### 9.2 操作流程

1. 浏览器访问 `http://localhost:8080/demo/` → 自动跳转到登录页
2. 输入用户名密码，点登录 → 跳回主页，显示"欢迎登录，{你输入的用户名}！"
3. 直接再访问 `http://localhost:8080/demo/` → 因为 Session 已有用户，直接显示主页（不用再登录）

### 9.3 验证模板缓存效果

把 `application.yml` 的 `spring.freemarker.cache` 改成 `true`（默认值），启动后改 `index.ftl` 的文案，刷新页面——发现改动不生效（需重启）。再改回 `false`，改动即时生效。这就是开发环境关缓存的意义。

---

## 十、动手练习

1. **加一个登出接口**：在 UserController 加 `@GetMapping("/logout")`，清除 Session 后重定向到登录页。
2. **模板加条件渲染**：在 `index.ftl` 里用 `<#if user??>` 判断用户是否存在，存在显示欢迎语，不存在显示"请先登录"。
3. **列表渲染**：在 IndexController 里 `mv.addObject("users", userList)` 传一个用户列表，在 `index.ftl` 里用 `<#list users as u>` 循环渲染所有用户名。
4. **改模板后缀**：把 `spring.freemarker.suffix` 改成 `.html`，模板文件也改成 `.html`，验证仍能渲染（理解后缀配置的作用）。
5. **故意用错注解**：把 IndexController 的 `@Controller` 改成 `@RestController`，访问主页，观察页面直接输出字符串 `page/index` 而不是渲染模板，体会两者区别。

---

## 十一、本模块知识点总结（结合实际开发详解）

模板引擎在前后端分离时代用得少了，但在后台管理、邮件、报表等场景仍是刚需。下面把核心知识点放到真实开发里讲透。

### 11.1 `@Controller` vs `@RestController`：一个注解决定返回值去向

这是本模块最关键的概念。同一个方法返回字符串，用不同注解结果天差地别：

| 注解 | 返回值去向 | 典型场景 |
| --- | --- | --- |
| `@Controller` | 视图名 → 视图解析器找模板渲染 | 服务端渲染页面 |
| `@RestController` | 直接写进 HTTP 响应体 | 返回 JSON/数据 API |
| `@Controller` + 方法上 `@ResponseBody` | 直接写进响应体 | 个别方法返回数据，其余返回页面 |

**实际开发中的常见模式：**

- **纯前后端分离项目**：全部用 `@RestController`，返回 JSON，前端用 Vue/React 自己渲染。
- **纯服务端渲染项目**（如老式后台管理）：全部用 `@Controller`，返回模板。
- **混合项目**：类用 `@Controller`，需要返回数据的方法单独加 `@ResponseBody`；或拆成两个 Controller 类。

**常见坑：**

- 误把 `@Controller` 用在应该返回 JSON 的方法上，结果返回的字符串被当成视图名，报 404（找不到模板）。
- 误把 `@RestController` 用在应该渲染页面的方法上，结果模板名原样输出成文本。
- **排查口诀**："页面变文本/404，先查 Controller 注解对不对"。

### 11.2 `ModelAndView` vs `String` 视图名 vs `Model`

Spring MVC 返回视图有三种写法，效果等价：

```java
// 写法一：ModelAndView（数据+视图打包）
ModelAndView mv = new ModelAndView("page/index");
mv.addObject("user", user);
return mv;

// 写法二：方法参数 Model + 返回 String 视图名
@GetMapping("/")
public String index(Model model) {
    model.addAttribute("user", user);
    return "page/index";
}

// 写法三：直接返回 String 视图名（数据用其他方式传）
return "page/index";
```

**实际开发怎么选？**

- `ModelAndView`：数据视图一起返回，直观，适合逻辑简单的场景。本模块用的就是这种。
- `String + Model` 参数：更主流，视图名和数据分离，方法签名清晰，是 Spring 官方更推荐的写法。
- 直接 String：只返回视图名，数据靠 `@ModelAttribute` 方法或 `HttpServletRequest` 传，少用。

**最佳实践**：新项目统一用 `String + Model` 参数写法，配合 `@RequiredArgsConstructor` 注入 Service，代码最简洁。

### 11.3 重定向（redirect）与转发（forward）

```java
mv.setViewName("redirect:/user/login");   // 重定向
mv.setViewName("forward:/user/login");     // 转发
mv.setViewName("page/index");              // 视图渲染（也是转发的一种）
```

| 特性 | redirect 重定向 | forward 转发 |
| --- | --- | --- |
| 请求次数 | 2 次（浏览器再发一次） | 1 次（服务端内部） |
| 地址栏 | 变化 | 不变 |
| Session/Request 数据 | Session 共享，Request 不共享 | Request 共享 |
| 典型场景 | 登录后跳主页、表单提交后 PRG | 内部页面组装 |

**PRG 模式（Post-Redirect-Get）**：本模块登录就是典型——POST 提交表单后用 `redirect:/` 跳转，避免用户刷新页面导致表单重复提交。这是 Web 开发的经典最佳实践。

**常见坑：**

- redirect 路径忘了带 context-path：写 `redirect:/user/login`，但应用有 `context-path: /demo`，实际跳到 `/demo/user/login`。Spring 会自动补 context-path，但如果你写绝对 URL（`redirect:http://...`）就要自己处理。
- forward 到外部 URL 不行：forward 是服务端内部转发，只能转给本应用内的路径。

### 11.4 Freemarker 语法速查（实际开发常用）

| 语法 | 作用 | 示例 |
| --- | --- | --- |
| `${var}` | 输出变量值 | `${user.name}` |
| `<#if cond>...<#else>...</#if>` | 条件判断 | `<#if user??>` |
| `<#list items as item>` | 循环遍历 | `<#list users as u>${u.name}</#list>` |
| `<#include "path">` | 包含其他模板 | `<#include "../common/head.ftl">` |
| `??` | 判断非空 | `<#if user??>` |
| `!` | 默认值 | `${user.name!'匿名'}` |
| `?size` | 集合大小 | `${users?size}` |
| `?date` `?time` `?datetime` | 格式化日期 | `${createTime?datetime}` |

**实际开发要点：**

1. **空值处理**：Freemarker 对 null 极其严格，`${user.name}` 如果 user 为 null 直接报错。生产中养成习惯用 `${user.name!''}`（null 时输出空串）或 `<#if user??>` 先判断。
2. **XSS 防护**：Freemarker 默认不转义 HTML，`${content}` 如果 content 含 `<script>` 会被执行。输出用户输入的内容时，用 `${content?html}` 转义，防 XSS。
3. **日期格式化**：直接 `${date}` 会报错（不知道格式），必须 `${date?string('yyyy-MM-dd')}` 或 `${date?datetime}`。

**常见坑：** 新手最常踩的是"模板报错白屏"——Freemarker 遇到 null 或类型错误会直接抛异常，页面 500。开发时把 `spring.freemarker.cache: false` 关掉，异常信息会实时反映。

### 11.5 模板缓存：开发关、生产开

| 环境 | `spring.freemarker.cache` | 原因 |
| --- | --- | --- |
| 开发 | `false` | 改模板即时生效，不用重启 |
| 生产 | `true`（默认） | 模板不变，缓存编译结果省 CPU |

**进阶**：生产环境如果想改模板不重启，可以用 Spring DevTools（开发期热加载）或配置中心动态刷新。但 Freemarker 模板缓存本质是编译期缓存，改模板文件后需要清缓存——这是模板引擎的局限，也是前后端分离（前端独立打包部署）更流行的原因之一。

### 11.6 模板引擎的选型：Freemarker vs Thymeleaf vs Beetl

Spring Boot 生态有三大模板引擎（本项目都有对应 demo）：

| 引擎 | 特点 | 推荐场景 |
| --- | --- | --- |
| **Freemarker** | 老牌、功能强大、语法像脚本（`<#if>`） | 逻辑复杂的模板、邮件、报表 |
| **Thymeleaf** | Spring Boot 官方推荐、HTML 原生可预览（`th:` 属性） | 需要设计师直接看模板效果的场景 |
| **Beetl** | 国产、性能好、语法接近 JS | 追求性能、国产化要求 |

**实际开发建议：**

- 新项目优先 Thymeleaf（官方支持、生态好、可被浏览器直接预览）。
- 老项目或复杂逻辑模板用 Freemarker。
- 性能敏感场景考虑 Beetl。
- **但更主流的趋势是前后端分离**——后端只出 JSON API，模板引擎只用于邮件、报表等非核心页面。

> 💡 前端类比：选模板引擎就像选 EJS/Pug/Handlebars，各有语法偏好。但现代前端更倾向 SPA + API，模板引擎在主应用中逐渐边缘化，这点 Java 后端和 Node.js 后端趋势一致。

### 11.7 表单对象绑定与数据校验

本模块 `login(User user)` 直接用对象接收表单，Spring 自动按字段名绑定。实际开发中还要加校验：

```java
@PostMapping("/login")
public String login(@Valid User user, BindingResult result, ...) {
    if (result.hasErrors()) {
        return "page/login";   // 校验失败回登录页
    }
    // 校验通过，处理登录
}
```

`@Valid` 触发 JSR-303 校验（User 字段上加 `@NotBlank` 等），错误信息放进 `BindingResult`，模板里用 `<#if>` 或 Spring 标签显示错误。这是服务端表单校验的标准套路，和前端校验互补——前端校验为体验，后端校验为安全。

---

> 📌 **学习建议**：作为前端工程师，模板引擎对你来说应该很亲切——它就是服务端的 EJS/Pug。重点理解 `@Controller`（返回视图）和 `@RestController`（返回数据）的区别，这是新手最容易踩的坑。另外要建立认知：现代 Spring Boot 项目大多前后端分离，后端只返回 JSON，模板引擎主要用于后台管理页、邮件模板、报表导出这些"非交互核心"的场景。学这个模块更多是理解服务端渲染的原理和 Spring MVC 的视图机制，不必在模板语法上钻太深。
