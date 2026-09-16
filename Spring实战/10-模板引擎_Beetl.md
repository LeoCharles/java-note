# 10 - Spring Boot 集成 Beetl 模板引擎

> 对应项目模块：`demo-template-beetl`
> 前置知识：已学完 01-09，了解启动类、配置、控制器、`@RestController`、统一异常处理等基础
> 学习目标：理解服务端模板渲染的本质，掌握 Beetl 模板引擎的集成与基本语法，能写出"控制器传数据 → 模板渲染 HTML → 浏览器展示"的完整链路。

---

## 一、本模块要解决什么问题？

前面几个模块，控制器返回的都是 JSON（`@RestController` + 对象，Jackson 自动序列化），这是**前后端分离**架构的做法——后端只出数据，前端（Vue/React）自己渲染页面。

但在某些场景下，你仍然需要**服务端渲染（SSR）**页面，让后端直接产出完整的 HTML 返回给浏览器：

- 内网管理系统、后台运营页面（不需要复杂前端工程，几页 HTML 搞定）
- 邮件模板、报表模板、静态页生成
- 给非前端团队用的简单页面

**模板引擎**就是干这个的：你写一个带占位符的 HTML 模板，后端把数据填进去，输出最终 HTML。本模块演示用 **Beetl**（国产高性能模板引擎）做这件事。

> 💡 前端类比：Beetl 之于 Java，就像 EJS / Pug / Handlebars / Nunjucks 之于 Node.js——都是"模板 + 数据 = HTML"的套路。如果你用过 Express 的 `res.render('index', { user })`，那本模块的 `ModelAndView` 几乎是一一对应的。

本模块的最终效果：访问 `http://localhost:8080/demo/`，未登录则跳转到登录页，输入用户名密码后回到主页显示"欢迎登录，xxx！"。

---

## 二、项目结构

```
demo-template-beetl/
├── pom.xml
└── src/main/
    ├── java/com/xkcoding/template/beetl/
    │   ├── SpringBootDemoTemplateBeetlApplication.java   # 启动类
    │   ├── controller/
    │   │   ├── IndexController.java        # 主页控制器（登录态判断）
    │   │   └── UserController.java         # 登录控制器（GET 表单 + POST 提交）
    │   └── model/
    │       └── User.java                   # 用户模型
    └── resources/
        ├── application.yml                 # 配置
        └── templates/
            ├── common/
            │   └── head.html               # 公共头部片段（被 include）
            └── page/
                ├── index.btl               # 主页模板
                └── login.btl              # 登录页模板
```

注意几个约定：

- 模板放在 `src/main/resources/templates/` 下，这是 Spring Boot 对模板文件的默认查找路径。
- Beetl 模板后缀是 `.btl`（公共片段 `head.html` 用 `.html` 也能被 include，因为 Beetl 不强制后缀）。
- 控制器返回的视图名（如 `page/index.btl`）就是相对 `templates/` 的路径。

---

## 三、逐行拆解 `pom.xml`

```xml
<properties>
    <ibeetl.version>1.1.63.RELEASE</ibeetl.version>
</properties>

<dependencies>
    <!-- 1. Beetl 的 Spring Boot Starter -->
    <dependency>
        <groupId>com.ibeetl</groupId>
        <artifactId>beetl-framework-starter</artifactId>
        <version>${ibeetl.version}</version>
    </dependency>

    <!-- 2. Spring Boot Web -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-web</artifactId>
    </dependency>

    <!-- 3. 测试 -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-test</artifactId>
        <scope>test</scope>
    </dependency>

    <!-- 4. Lombok -->
    <dependency>
        <groupId>org.projectlombok</groupId>
        <artifactId>lombok</artifactId>
        <optional>true</optional>
    </dependency>

    <!-- 5. Hutool -->
    <dependency>
        <groupId>cn.hutool</groupId>
        <artifactId>hutool-all</artifactId>
    </dependency>
</dependencies>
```

关键点：

- `beetl-framework-starter` 是 Beetl 官方提供的 Spring Boot Starter，引入后自动配置好 `BeetlViewResolver`（视图解析器）和 `GroupTemplate`（模板引擎核心对象）。**注意它没有走父 POM 的 `dependencyManagement`，所以这里手写了版本 `1.1.63.RELEASE`**——因为 Beetl 不是 Spring Boot 官方维护的依赖，版本要自己锁。
- `spring-boot-starter-web` 提供 Spring MVC，模板渲染依赖它的 `DispatcherServlet` 和视图解析机制。
- Lombok 的 `@Slf4j` 给控制器注入日志对象 `log`（本模块虽未实际打印日志，但引入了该注解）。

> 💡 前端类比：`beetl-framework-starter` 就像 Express 里 `npm i ejs`，装上之后框架就能识别 `.ejs` 模板。Starter 把"注册视图解析器、配置模板根路径"这些自动化了。

---

## 四、配置文件 `application.yml`

```yaml
server:
  port: 8080
  servlet:
    context-path: /demo
```

本模块的 yml 非常简单，只有端口和 context-path。**没有显式配置 Beetl**——因为 `beetl-framework-starter` 的自动配置已经把默认值都设好了：模板根路径默认是 `classpath:/templates/`，后缀默认 `.btl`。所以你什么都不写，它也能工作。

如果需要自定义（比如改模板根路径、改后缀、开启热加载），可以加：

```yaml
beetl:
  # 这些是示例，本模块未使用，仅展示可配置项
  prefix: classpath:/templates/    # 模板根路径
  suffix: .btl                     # 模板后缀
  cache: false                     # 开发期关闭模板缓存（改模板即时生效）
```

---

## 五、逐行拆解控制器

### 5.1 `IndexController` —— 主页 + 登录态判断

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
            mv.setViewName("page/index.btl");
            mv.addObject(user);
        }

        return mv;
    }
}
```

**注意这里用的是 `@Controller`，不是 `@RestController`！** 这是关键区别：

- `@RestController`：返回值直接写进响应体（JSON/文本），不渲染页面。
- `@Controller`：返回值被当作**视图名**，交给视图解析器去渲染模板。

**`@GetMapping(value = {"", "/"})`**：映射空路径和根路径，即访问 `http://localhost:8080/demo/` 或 `http://localhost:8080/demo` 都会进这个方法。

**`ModelAndView`**：同时承载"视图名"和"模型数据"的对象。

- `mv.setViewName("redirect:/user/login")`：`redirect:` 前缀表示**重定向**，浏览器会跳到 `/demo/user/login`。
- `mv.setViewName("page/index.btl")`：没有 `redirect:` 前缀，表示**渲染模板**，视图解析器会去 `templates/page/index.btl` 找模板。
- `mv.addObject(user)`：把 user 对象塞进模型，模板里就能用 `${user.name}` 取到值。`addObject` 不传 key 时，默认用类名首字母小写作为 key（`user`）。

**登录态判断逻辑**：从 session 取 `user`，没有就重定向到登录页，有就渲染主页。这是最朴素的 session 登录态管理（后续 `demo-session` 模块会讲更规范的方案）。

> 💡 前端类比：`ModelAndView` 像 Express 的 `res.render('index', { user })`——视图名 + 数据一起传。`redirect:` 像 `res.redirect('/login')`。

### 5.2 `UserController` —— 登录表单与提交

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
        return new ModelAndView("page/login.btl");
    }
}
```

**`@RequestMapping("/user")` 加在类上**：类级别路径 + 方法级别路径拼接成完整路径。所以：

- `GET /user/login` → `login()` 方法，返回登录表单页
- `POST /user/login` → `login(User, HttpServletRequest)` 方法，处理表单提交

**`@PostMapping("/login")` 的 `login(User user, ...)`**：注意参数 `User user` 前面没有任何注解！这是 Spring MVC 的**表单对象绑定**——当方法参数是一个普通对象（不是 `@RequestParam`/`@PathVariable` 等标注的），Spring 会自动把表单字段（`name=xxx&password=yyy`）按属性名映射到对象上。所以前端表单的 `name="name"` 和 `name="password"` 会自动填充到 `user.name` 和 `user.password`。

**登录逻辑**：把 user 存进 session，然后重定向回主页 `redirect:/`。主页的 `IndexController` 再从 session 取出 user 渲染欢迎页。这是一个完整的"登录 → 跳转 → 展示"闭环。

> 💡 前端类比：表单对象绑定像 Vue 里 `v-model` 双向绑定表单到对象，只不过这里是后端接收时自动绑定。`@PostMapping` 对应 Express 的 `app.post('/user/login', ...)`。

### 5.3 `User` 模型

```java
@Data
public class User {
    private String name;
    private String password;
}
```

简单的 POJO + Lombok `@Data`（自动生成 getter/setter）。表单字段名和属性名一致（`name`、`password`），Spring 才能自动绑定。

---

## 六、逐行拆解模板文件

### 6.1 公共头部 `templates/common/head.html`

```html
<head>
	<meta charset="UTF-8">
	<meta name="viewport"
	      content="width=device-width, user-scalable=no, initial-scale=1.0, maximum-scale=1.0, minimum-scale=1.0">
	<meta http-equiv="X-UA-Compatible" content="ie=edge">
	<title>spring-boot-demo-template-beetl</title>
</head>
```

一个普通的 HTML 片段，放公共的 `<head>` 内容。它会被其他模板 include 复用，避免每个页面重复写 meta 标签。

### 6.2 主页 `templates/page/index.btl`

```html
<!doctype html>
<html lang="en">
<% include("/common/head.html"){} %>
<body>
<div id="app" style="margin: 20px 20%">
	欢迎登录，${user.name}！
</div>
</body>
</html>
```

**Beetl 语法解析：**

- `<% ... %>`：Beetl 的脚本块定界符，里面写 Beetl 指令（类似 JSP 的 `<% %>`）。
- `include("/common/head.html"){}`：`include` 指令，引入另一个模板文件的内容。路径相对 `templates/` 根目录。后面的 `{}` 是 Beetl 特有的"布局占位"，这里为空表示单纯引入。
- `${user.name}`：变量占位符，输出 `user` 对象的 `name` 属性。这个 `user` 就是控制器 `mv.addObject(user)` 传进来的。

> 💡 前端类比：`<% include(...) %>` 像 EJS 的 `<%- include('head') %>` 或 Pug 的 `include head`；`${user.name}` 像 EJS 的 `<%= user.name %>` 或 Vue 模板的 `{{ user.name }}`。语法符号不同，概念完全一致。

### 6.3 登录页 `templates/page/login.btl`

```html
<!doctype html>
<html lang="en">
<% include("/common/head.html"){} %>
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

一个原生 HTML 表单：

- `action="/demo/user/login"`：注意要带上 context-path `/demo`，因为这是浏览器提交的路径，浏览器不知道 Spring 的 context-path。
- `method="post"`：对应控制器的 `@PostMapping`。
- `name="name"` 和 `name="password"`：表单字段名，必须和 `User` 对象属性名一致，Spring 才能自动绑定。

---

## 七、运行与验证

### 7.1 启动

```sh
mvn spring-boot:run
```

### 7.2 验证完整流程

| 步骤 | 操作 | 结果 |
| --- | --- | --- |
| 1 | 访问 `http://localhost:8080/demo/` | 未登录，重定向到登录页 |
| 2 | 登录页显示表单 | 输入用户名密码 |
| 3 | 点击登录，POST 到 `/demo/user/login` | 存 session，重定向回主页 |
| 4 | 主页渲染 | 显示"欢迎登录，{你输入的用户名}！" |

### 7.3 关键观察点

- 看 Network 面板：访问 `/demo/` 会返回 `302` 重定向到 `/demo/user/login`。
- 登录提交后，浏览器收到 `302` 重定向回 `/demo/`，再请求主页，主页返回渲染好的 HTML。
- session 里存了 user，所以刷新主页仍是登录态（直到关浏览器或 session 过期）。

---

## 八、动手练习

1. **加一个登出接口**：写 `@GetMapping("/user/logout")`，从 session 移除 user（`request.getSession().removeAttribute("user")`），重定向到登录页。
2. **模板里用条件判断**：在 `index.btl` 里用 Beetl 的 `<% if(user != null){ %> ... <% } %>` 包裹欢迎语，体会模板里的流程控制。
3. **加一个列表渲染**：在控制器构造一个 `List<User>` 传给模板，用 Beetl 的 `<% for(user in userList){ %> <p>${user.name}</p> <% } %>` 渲染列表。
4. **改模板后缀**：尝试把 `.btl` 改成 `.html`，观察是否仍能工作（提示：视图名要带全路径，Beetl 对后缀不强制）。
5. **对比 `@Controller` 和 `@RestController`**：把 `IndexController` 改成 `@RestController`，访问主页，观察返回的是 HTML 还是把视图名字符串当文本返回了，体会两者区别。

---

## 九、本模块知识点总结（结合实际开发详解）

模板引擎是 Spring Boot 的"传统艺能"，虽然前后端分离时代用得少了，但理解它有助于看懂老项目、写后台管理页和邮件/报表模板。下面把核心知识点放到真实开发场景里讲透。

### 9.1 `@Controller` vs `@RestController`：什么时候用哪个？

这是本模块最核心的认知转变。两者只差一个 `@ResponseBody`，但行为完全不同：

| 注解 | 返回值处理 | 典型场景 |
| --- | --- | --- |
| `@Controller` | 返回值当视图名，交给视图解析器渲染模板 | 服务端渲染页面（SSR） |
| `@RestController` | 返回值直接写进响应体（JSON/文本） | 前后端分离，返回 JSON API |

**实际开发中的选择：**

- **现代项目 90% 用 `@RestController`**：前后端分离，后端只出 JSON，前端 Vue/React 渲染。
- **后台管理系统、邮件模板、报表**用 `@Controller`：需要服务端拼 HTML。
- **混合场景**：同一个项目里，API 控制器用 `@RestController`，页面控制器用 `@Controller`，各司其职。

**常见坑：**

- 用了 `@Controller` 但忘了方法上加 `@ResponseBody`，导致返回的 JSON 对象被当成视图名，报 `404` 或 `Circular view path`。
- 用了 `@RestController` 却期望渲染页面——返回的字符串直接当文本返回了，浏览器看到的是视图名字符串而不是 HTML。
- **方法级 `@ResponseBody` 可覆盖类级 `@Controller`**：`@Controller` 类里的某个方法加了 `@ResponseBody`，该方法就返回 JSON，其他方法仍渲染页面。这是混合场景的灵活写法。

### 9.2 `ModelAndView` 与视图解析机制

`ModelAndView` 是 Spring MVC 渲染模板的核心对象，它包含两部分：

- **View（视图）**：`setViewName("page/index.btl")` 指定要渲染哪个模板。
- **Model（模型）**：`addObject(key, value)` 存放传给模板的数据。

**视图解析器（ViewResolver）的工作流程：**

1. 控制器返回 `ModelAndView`，视图名是 `page/index.btl`。
2. `DispatcherServlet` 拿到视图名，交给 `ViewResolver`（Beetl 的是 `BeetlViewResolver`）。
3. 解析器根据配置的前缀（`templates/`）+ 视图名 + 后缀，定位到模板文件。
4. 引擎把 Model 数据填进模板，输出最终 HTML，写到响应。

**实际开发的替代写法：**

除了 `ModelAndView`，更现代的写法是用方法参数 `Model` 注入数据，直接返回视图名字符串：

```java
@Controller
public class IndexController {
    @GetMapping("/")
    public String index(Model model) {        // 注入 Model
        model.addAttribute("user", currentUser);  // 塞数据
        return "page/index";                    // 只返回视图名（字符串）
    }
}
```

这种写法把"数据"和"视图名"分离，代码更清晰，是实际项目更常用的姿势。`ModelAndView` 把两者揉在一起，适合简单 demo。

**常见坑：**

- 视图名拼错：`page/index` 写成 `page/Index`（大小写）或 `page/index.btl`（有些配置下后缀要省略），导致找不到模板报 404。
- 模板路径不在 `templates/` 下：Spring Boot 默认模板根路径是 `classpath:/templates/`，放错位置解析不到。
- `addObject` 的 key 和模板里 `${}` 取的变量名对不上：模板里 `${user.name}` 要求 key 是 `user`，传成 `currentUser` 就取不到。

### 9.3 重定向 vs 转发：`redirect:` 与 `forward:`

本模块用了 `redirect:/user/login`。Spring MVC 视图名前缀有两种：

| 前缀 | 机制 | URL 变化 | 数据传递 |
| --- | --- | --- | --- |
| `redirect:` | 重定向 | 浏览器 URL 变成新地址 | 不能直接传 Model 数据（需 session/参数） |
| `forward:` | 转发 | 浏览器 URL 不变 | 能直接传 Model 数据（服务器内部跳转） |

**实际开发怎么选？**

- **登录后跳转主页**：用 `redirect:`，因为登录是 POST，刷新主页不应重复提交表单（PRG 模式：Post-Redirect-Get）。
- **内部转发到另一个控制器方法**：用 `forward:`，URL 不变，共享 Request 域数据。
- **带参数重定向**：`redirect:/user/list?id=123` 或用 `RedirectAttributes` 的 `addFlashAttribute`（基于 session，重定向后即失效）。

**常见坑：**

- `redirect:/` 漏写 context-path？其实不用写——Spring 会自动补 context-path，`redirect:/` 实际跳到 `/demo/`。但模板里写 `<form action>` 时要手写全 `/demo/...`，因为那是浏览器提交的，浏览器不知道 context-path。
- 用 `redirect:` 传复杂数据：Model 数据在重定向时会丢失（除非用 flash attribute），新手常困惑"为什么重定向后取不到数据"。

### 9.4 表单对象绑定：无注解参数的魔法

`login(User user, ...)` 的 `User` 前面没有任何注解，Spring 却能自动把表单字段填进去。这是 **ServletRequestDataBinder** 的能力：对没有标注解的复杂对象参数，Spring 按属性名从请求参数里取值填充。

**实际开发中的表单绑定场景：**

| 请求类型 | 参数位置 | 绑定方式 |
| --- | --- | --- |
| GET 表单 / URL 参数 | query string | `@RequestParam` 或对象绑定 |
| POST 表单（form-urlencoded） | body | 对象绑定（本模块用法） |
| POST JSON | body | `@RequestBody`（必须加注解） |

**常见坑：**

- **JSON 提交用对象绑定会失败**：如果前端用 `fetch` 发 `application/json`，后端用无注解对象接收，会绑定不到（因为无注解绑定只读 form 参数，不读 JSON body）。JSON 必须用 `@RequestBody`。这是前后端分离项目最常踩的坑。
- **字段名不匹配**：表单 `name="userName"` 但对象属性是 `name`，绑定不上。要么改表单，要么用 `@InitBinder` 自定义绑定。
- **嵌套对象**：表单字段名用 `.` 表示嵌套，如 `address.city` 能绑定到 `user.address.city`。

### 9.5 Beetl 语法速览与模板引擎选型

本模块用到的 Beetl 语法：

| 语法 | 作用 | 类比 |
| --- | --- | --- |
| `${user.name}` | 输出变量 | EJS `<%= %>` / Vue `{{ }}` |
| `<% include("/x"){} %>` | 引入子模板 | EJS `<%- include() %>` |
| `<% if(...){} %>` | 条件 | EJS `<% if() %>` |
| `<% for(x in list){} %>` | 循环 | EJS `<% for() %>` |

**Spring Boot 生态的模板引擎选型对比：**

| 引擎 | 特点 | 适用场景 |
| --- | --- | --- |
| **Thymeleaf** | Spring Boot 官方推荐，HTML 原生（可直接浏览器打开） | 新项目首选，前后端协作友好 |
| **Freemarker** | 老牌，功能强大，语法经典（`<#if>`） | 老项目、邮件/报表模板 |
| **Beetl** | 国产，性能高，语法接近 JS | 追求性能、国产化要求 |
| **Enjoy** | JFinal 出品，极简 | JFinal 生态 |

**实际开发建议：**

- **新项目**：用 Thymeleaf（官方推荐、生态好、HTML 原生可预览）。
- **老项目维护**：看原项目用什么就继续用什么，别折腾迁移。
- **纯 API 项目**：根本不用模板引擎，`@RestController` + JSON 搞定。
- **邮件/报表/代码生成**：Freemarker 或 Beetl 都行，看团队熟悉度。

**常见坑：**

- 多个模板引擎共存：同时引 Thymeleal 和 Beetl，视图解析器冲突，要手动指定优先级。
- 模板缓存：开发时改模板不生效，因为引擎默认缓存模板，要关闭缓存或重启。
- Beetl 的 `${}` 和 Spring 的 `${}` 占位符冲突？不会——Beetl 的 `${}` 在模板文件里，Spring 的 `${}` 在配置文件里，作用域不同。

### 9.6 Session 登录态：最朴素的认证方式

本模块用 `HttpSession` 存登录用户：`request.getSession().setAttribute("user", user)`，取的时候 `getAttribute("user")`。这是最原始的登录态保持方式。

**实际开发的演进路径：**

1. **单机 Session**（本模块）：存在 Tomcat 内存里，重启丢失，不能跨服务器。
2. **Session 持久化**：存 Redis，解决跨服务器共享（`demo-session` 模块讲）。
3. **Token/JWT**：无状态，客户端存 token，服务端签名校验（`demo-rbac-security` 模块讲）。
4. **OAuth2 / SSO**：第三方登录、单点登录（`demo-social` / `demo-oauth` 模块讲）。

**本模块方式的局限与坑：**

- **重启丢失**：Tomcat 重启 session 清空，用户要重新登录。
- **不能水平扩展**：用户登录在 A 服务器，下次请求到 B 服务器就取不到 session（除非 session 共享）。
- **CSRF 风险**：表单直接 POST，没有 CSRF token，易受跨站请求伪造攻击（生产要加 token）。
- **session 固定攻击**：登录后不换 session id，攻击者可窃取。生产应在登录后调用 `request.changeSessionId()`。

> 💡 前端类比：Session 像服务端的 cookie-session（Express 的 `req.session`），JWT 像 localStorage 里存 token + 请求头带 Authorization。本模块是 Express `express-session` 的等价物。

---

> 📌 **学习建议**：模板引擎这一块，作为前端转后端的同学其实很有亲切感——它就是你在 Node.js 里用 EJS/Handlebars 的那一套。重点理解 `@Controller` 和 `@RestController` 的区别（差一个 `@ResponseBody`，行为天差地别），以及视图解析器"视图名 → 模板文件 → 填充数据 → HTML"的链路。实际工作中，如果你做的是前后端分离项目，模板引擎可能很少用到，但理解它有助于看懂 Spring MVC 的视图层机制，也为后续写邮件模板、报表、代码生成打下基础。
