# 11 - 模板引擎 Enjoy（JFinal-Enjoy）

> 对应项目模块：`demo-template-enjoy`
> 前置知识：已学完前序模板引擎模块（Freemarker/Thymeleaf/Beetl），了解 `@Controller`、`ModelAndView`、视图解析器的基本概念
> 学习目标：掌握如何在 Spring Boot 中集成 JFinal-Enjoy 模板引擎，理解手动配置 ViewResolver 的通用套路，能看懂并改写 Enjoy 模板语法。

---

## 一、本模块要解决什么问题？

前面三个模板引擎模块（Freemarker、Thymeleaf、Beetl）都有一个共同点：Spring Boot 官方或社区提供了对应的 Starter，引入依赖后**自动配置**就生效了，你几乎不用写配置类。

但现实开发中，你会遇到很多**没有官方 Starter** 的技术——比如某些小众模板引擎、公司自研组件、老系统的遗留框架。这时候你就得**手动写配置类，把第三方库"嫁接"到 Spring Boot 体系里**。本模块用 JFinal-Enjoy 模板引擎演示这种"手动集成"的套路。

**Enjoy 是什么？** 它是 JFinal 框架自带的模板引擎，语法简洁、性能不错，特点是"指令式"语法（用 `#` 开头的指令控制逻辑）。虽然在前端工程师眼里它的语法有点像 JSP，但理解它能帮你建立"模板引擎通用心智模型"，并掌握手动配置 ViewResolver 的能力。

> 💡 前端类比：这就像你在一个 Vite 项目里，想用一个没有官方 Vite 插件的模板引擎（比如公司自研的），你需要自己写一个 Vite 插件把它接进去。本模块干的就是这件事——写配置类把 Enjoy 接进 Spring Boot。

---

## 二、项目结构

```
demo-template-enjoy/
├── pom.xml
└── src/main/
    ├── java/com/xkcoding/template/enjoy/
    │   ├── SpringBootDemoTemplateEnjoyApplication.java   # 启动类
    │   ├── config/
    │   │   └── EnjoyConfig.java                          # 手动配置 ViewResolver（核心）
    │   ├── controller/
    │   │   ├── IndexController.java                      # 主页（登录拦截）
    │   │   └── UserController.java                       # 登录页 + 登录处理
    │   └── model/
    │       └── User.java                                 # 用户实体
    └── resources/
        ├── application.yml
        └── templates/
            ├── common/
            │   └── head.html                             # 公共头部片段
            └── page/
                ├── index.html                            # 首页模板
                └── login.html                            # 登录页模板
```

注意模板放在 `templates/` 下，分 `common`（公共片段）和 `page`（页面）两个子目录——这是模板组织的常见做法，方便复用。

---

## 三、逐行拆解 pom.xml

```xml
<properties>
    <enjoy.version>3.5</enjoy.version>
</properties>

<dependencies>
    <!-- Spring Boot Web 起步依赖 -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-web</artifactId>
    </dependency>

    <!-- JFinal-Enjoy 模板引擎（注意：没有 Spring Boot Starter，需手动配置） -->
    <dependency>
        <groupId>com.jfinal</groupId>
        <artifactId>enjoy</artifactId>
        <version>${enjoy.version}</version>
    </dependency>

    <dependency>
        <groupId>org.projectlombok</groupId>
        <artifactId>lombok</artifactId>
        <optional>true</optional>
    </dependency>

    <dependency>
        <groupId>cn.hutool</groupId>
        <artifactId>hutool-all</artifactId>
    </dependency>
</dependencies>
```

**关键点：Enjoy 没有官方 Starter。**

对比前几个模板引擎：
- Freemarker：`spring-boot-starter-freemarker`，引入即自动配置
- Thymeleaf：`spring-boot-starter-thymeleaf`，引入即自动配置
- **Enjoy：只引了 `com.jfinal:enjoy` 这个裸库，没有任何自动配置**

这就是为什么本模块必须写一个 `EnjoyConfig` 配置类——没人帮你配，你得自己来。`<version>3.5</version>` 在本模块自己声明了（因为 Enjoy 不在 Spring Boot 的 BOM 管理范围内，父 POM 没锁它的版本）。

---

## 四、核心：手动配置 ViewResolver

`config/EnjoyConfig.java` 是本模块的灵魂，它演示了"如何把一个模板引擎接入 Spring MVC"：

```java
@Configuration
public class EnjoyConfig {
    @Bean(name = "jfinalViewResolver")
    public JFinalViewResolver getJFinalViewResolver() {
        JFinalViewResolver jfr = new JFinalViewResolver();
        // setDevMode 配置放在最前面
        jfr.setDevMode(true);
        // 使用 ClassPathSourceFactory 从 class path 与 jar 包中加载模板文件
        jfr.setSourceFactory(new ClassPathSourceFactory());
        // 在使用 ClassPathSourceFactory 时要使用 setBaseTemplatePath
        // 代替 jfr.setPrefix("/view/")
        JFinalViewResolver.engine.setBaseTemplatePath("/templates/");

        jfr.setSessionInView(true);
        jfr.setSuffix(".html");
        jfr.setContentType("text/html;charset=UTF-8");
        jfr.setOrder(0);
        return jfr;
    }
}
```

逐行看：

### 4.1 `@Configuration` + `@Bean` —— 手动注册组件

- `@Configuration`：标记这是配置类，会被 Spring 扫描。
- `@Bean(name = "jfinalViewResolver")`：把这个方法返回的对象注册成 Spring Bean，名字叫 `jfinalViewResolver`。相当于在 XML 里写 `<bean id="jfinalViewResolver" class="...">`。

> 💡 前端类比：这就像在 Vue 的 `app.config.globalProperties` 上手动挂载一个插件——没有官方封装，你手动 new 出实例并塞进框架。

### 4.2 `JFinalViewResolver` —— Enjoy 提供的 Spring MVC 适配器

`JFinalViewResolver` 是 Enjoy 官方提供的一个类，它实现了 Spring MVC 的 `ViewResolver` 接口。**这是 Enjoy 能接入 Spring 的桥梁**——只要它实现了 `ViewResolver`，Spring MVC 就能用它来解析视图名（如 `page/index`）到真实模板文件。

### 4.3 各项配置含义

| 配置 | 作用 | 实际开发注意 |
| --- | --- | --- |
| `setDevMode(true)` | 开发模式，模板修改实时生效（不缓存） | 生产环境要设 `false`，开启缓存提升性能 |
| `setSourceFactory(new ClassPathSourceFactory())` | 从 classpath 加载模板（支持 jar 内） | 部署成 jar 包后，模板在 jar 里，必须用 ClassPath 加载 |
| `setBaseTemplatePath("/templates/")` | 模板根目录 | 用 ClassPathSourceFactory 时用这个，代替 `setPrefix` |
| `setSessionInView(true)` | 模板里能直接访问 `session` 对象 | 方便但有安全争议，见后文 |
| `setSuffix(".html")` | 模板文件后缀 | Controller 返回 `page/index`，实际找 `/templates/page/index.html` |
| `setContentType("text/html;charset=UTF-8")` | 响应内容类型 | 防止中文乱码 |
| `setOrder(0)` | ViewResolver 优先级 | 数字越小优先级越高，多引擎共存时决定谁先解析 |

**`setDevMode` 必须放最前面**——注释特意提醒。因为 Enjoy 的引擎初始化顺序敏感，devMode 影响后续所有配置的缓存行为，先设好才不会出问题。这是 Enjoy 特有的"坑"，体现了第三方库接入时要注意其初始化约定。

### 4.4 为什么 `setBaseTemplatePath` 用 `JFinalViewResolver.engine`？

注意这行和其他行不同，它操作的是 `JFinalViewResolver.engine`（静态引擎实例），而不是 `jfr` 实例本身。这是 Enjoy API 的特殊设计——基础模板路径是引擎级配置，不是实例级。这种"实例配置 + 静态引擎配置"混合的写法，在接入不规范的第三方库时很常见，照着官方文档抄即可。

---

## 五、模型与控制器

### 5.1 User 实体

```java
@Data
public class User {
    private String name;
    private String password;
}
```

用 Lombok `@Data` 自动生成 getter/setter。模板里要访问 `user.name`，必须有 getter，`@Data` 帮你搞定。

### 5.2 IndexController —— 主页（带登录拦截）

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

逐行看：

- `@Controller`（不是 `@RestController`）：因为要返回视图，不是 JSON。返回的字符串会被 ViewResolver 当成视图名解析。
- `@GetMapping(value = {"", "/"})`：同时映射空路径和 `/`，访问 `http://localhost:8080/demo/` 或 `http://localhost:8080/demo` 都进这个方法。
- `ModelAndView`：Spring MVC 的核心返回对象，同时承载"视图名"和"模型数据"。
  - `setViewName("page/index")`：视图名，ViewResolver 会解析成 `/templates/page/index.html`。
  - `mv.addObject(user)`：把 user 对象放进模型，模板里就能用 `#(user.name)` 访问。注意没写 key，默认用类名首字母小写 `user` 作为 key。
- 登录拦截逻辑：从 session 取 user，没有就重定向到登录页。这是最朴素的"session 登录态"实现，后续 Security/Shiro 模块会讲更专业的方案。
- `redirect:` 前缀：Spring MVC 特殊约定，表示重定向（302）而不是视图名解析。

> 💡 前端类比：`ModelAndView` 像一个"渲染上下文对象"，`setViewName` 指定渲染哪个组件，`addObject` 像 `props` 传数据。`redirect:` 像前端路由的 `router.replace()`。

### 5.3 UserController —— 登录页与登录处理

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

注意这里有两个 `login` 方法（方法重载）：
- `GET /user/login`：展示登录表单页，返回 `page/login` 视图。
- `POST /user/login`：处理表单提交。`User user` 参数会自动绑定表单的 `name` 和 `password` 字段（Spring MVC 的对象参数绑定）。然后把 user 存进 session，重定向回首页。

**表单对象绑定**：HTML 表单 `<input name="name">` 和 `<input name="password">`，Spring MVC 自动把同名字段塞进 `User` 对象的对应属性。这比一个个 `@RequestParam` 取方便多了。

> 💡 前端类比：这像前端框架的 `v-model` 双向绑定，但这里是"表单提交 → 后端对象"的单向绑定。

---

## 六、模板文件与 Enjoy 语法

### 6.1 公共头部 `common/head.html`

```html
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="...">
    <meta http-equiv="X-UA-Compatible" content="ie=edge">
    <title>spring-boot-demo-template-enjoy</title>
</head>
```

纯 HTML，没有 Enjoy 指令。它是被其他模板 `#include` 进来的公共片段。

### 6.2 首页 `page/index.html`

```html
<!doctype html>
<html lang="en">
#include("/common/head.html")
<body>
<div id="app" style="margin: 20px 20%">
    欢迎登录，#(user.name)！
</div>
</body>
</html>
```

Enjoy 语法：
- `#include("/common/head.html")`：指令，把 head.html 内容原样插入此处。路径相对于 `baseTemplatePath`（`/templates/`），所以实际是 `/templates/common/head.html`。
- `#(user.name)`：输出表达式，等价于其他模板引擎的 `${user.name}`。取模型里 `user` 对象的 `name` 属性并输出。

### 6.3 登录页 `page/login.html`

```html
<!doctype html>
<html lang="en">
#include("/common/head.html")
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

注意 `action="/demo/user/login"`——因为配了 `context-path: /demo`，表单提交地址要带 `/demo` 前缀。这是 context-path 在模板里最容易被忽略的坑。

### 6.4 Enjoy 常用语法速查

| 语法 | 作用 | 示例 |
| --- | --- | --- |
| `#(expr)` | 输出表达式 | `#(user.name)` |
| `#include(path)` | 包含文件 | `#include("/common/head.html")` |
| `#if(cond)` ... `#end` | 条件判断 | `#if(user) 已登录 #end` |
| `#for(item : list)` ... `#end` | 循环 | `#for(u : users) #(u.name) #end` |
| `#set(var = expr)` | 定义变量 | `#set(title = "首页")` |

> 💡 前端类比：Enjoy 的 `#` 指令语法类似 EJS 的 `<% %>` 或 Pug 的 `if/each`，都是"在 HTML 里嵌入逻辑指令"。它比 Thymeleaf 的标签属性语法更直接，但模板和逻辑耦合也更紧。

---

## 七、运行与验证

### 7.1 启动

```sh
mvn spring-boot:run
```

### 7.2 访问流程

1. 访问 `http://localhost:8080/demo/` → 检测 session 无 user → 重定向到 `/demo/user/login`
2. 登录页展示表单 → 填用户名密码提交（POST `/demo/user/login`）
3. 后端把 user 存入 session → 重定向回 `/demo/`
4. 首页检测到 session 有 user → 渲染 `page/index.html`，显示"欢迎登录，xxx！"

### 7.3 验证模板热更新

因为 `setDevMode(true)`，修改 `index.html` 后刷新浏览器（不用重启）就能看到变化。生产环境务必改成 `false`。

---

## 八、动手练习

1. **加一个循环**：在 IndexController 里往 ModelAndView 加一个 `users` 列表，在 `index.html` 用 `#for` 遍历输出每个用户名。
2. **加条件判断**：在模板里用 `#if(user.name == "admin")` 显示"管理员"标识，否则显示普通用户。
3. **切换 devMode**：把 `setDevMode(true)` 改成 `false`，修改模板后重启，观察是否还能热更新（不能，因为开了缓存）。
4. **体验 context-path 坑**：把 `application.yml` 的 `context-path` 注释掉，但忘了改 `login.html` 里的 `action="/demo/user/login"`，观察表单提交会 404。
5. **对比其他引擎**：把同一个登录页用 Thymeleaf 语法改写一遍，体会两种语法的差异。

---

## 九、本模块知识点总结（结合实际开发详解）

本模块的核心价值不是 Enjoy 本身，而是它演示的"手动集成第三方库到 Spring Boot"的通用套路。下面把关键知识点放到真实开发场景里讲透。

### 9.1 手动配置 ViewResolver：接入任意模板引擎的通用模式

**实际开发中什么时候需要手动配 ViewResolver？**

- 用没有官方 Starter 的模板引擎（如本模块的 Enjoy、Velocity、自研引擎）
- 需要自定义官方 Starter 的默认配置（如 Thymeleaf 想改模板目录、Beetl 想加共享变量）
- 多模板引擎共存（比如同时用 Thymeleaf 渲染页面 + Freemarker 渲染邮件模板）

**通用套路三步走：**

1. **引裸库依赖**：`pom.xml` 引入模板引擎的核心 jar（不带 Spring Boot 适配）。
2. **写 `@Configuration` 类**：`@Bean` 声明一个 `ViewResolver` 实现类，配置模板路径、后缀、编码等。
3. **让 Spring 扫到**：配置类放在启动类所在包或子包下，`@ComponentScan` 自动扫到。

**最佳实践：**

- 配置类统一放 `config` 包，命名 `XxxConfig`，职责单一。
- 用 `@Bean` 而不是 XML，符合 Spring Boot"零 XML"理念。
- 关键参数（模板路径、是否缓存）尽量可配置化，用 `@Value` 或 `@ConfigurationProperties` 从 yml 读，方便不同环境调整。

**常见坑：**

- 忘了 `@Configuration` 或 `@Bean`，Bean 没注册进容器，ViewResolver 不生效。
- 模板路径配错：用 `ClassPathSourceFactory` 时路径以 `/` 开头表示 classpath 根，不是文件系统绝对路径。
- 多 ViewResolver 共存时不设 `setOrder`，优先级不确定，可能用错引擎解析。

> 💡 前端类比：这就像在 Vite 里手动写一个插件 `defineConfig({ plugins: [myEngine()] })`——你 new 出引擎实例、配置入口路径、注册到框架插件体系。Spring 的 `@Bean` 就是"注册插件"的动作。

### 9.2 `@Controller` vs `@RestController`：何时用哪个

本模块所有控制器都用 `@Controller`（不是 `@RestController`），因为要返回视图页面。

**两者区别：**

| 注解 | 返回值处理 | 适用场景 |
| --- | --- | --- |
| `@Controller` | 返回值当视图名，ViewResolver 解析 | 服务端渲染页面（SSR） |
| `@RestController` | 返回值直接写响应体（JSON） | 前后端分离的 API |

**实际开发怎么选？**

- **传统多页应用 / 后台管理系统**：用 `@Controller`，返回 HTML 页面。很多企业内部管理系统仍用这种模式，开发快、SEO 友好。
- **前后端分离项目**：用 `@RestController`，后端只吐 JSON，前端 Vue/React 自己渲染。这是现在的主流。
- **混合模式**：同一个项目里，页面用 `@Controller`，API 用 `@RestController`，或在一个 `@Controller` 类里给特定方法加 `@ResponseBody`。

**最佳实践：** 现代新项目优先前后端分离（`@RestController` + 前端框架）。只有在需要 SEO、内部管理后台、对首屏速度要求极高时才考虑服务端渲染。

**常见坑：** 用了 `@Controller` 但忘了方法上没加 `@ResponseBody`，导致返回的 JSON 字符串被当成视图名，报 404 或循环视图解析错误。

### 9.3 `ModelAndView` 的三种用法

本模块展示了 `ModelAndView` 的几种写法：

```java
// 写法一：new 空对象，逐步 set
ModelAndView mv = new ModelAndView();
mv.setViewName("page/index");
mv.addObject(user);

// 写法二：构造时传视图名
return new ModelAndView("page/login");

// 写法三：重定向
mv.setViewName("redirect:/user/login");
```

**实际开发建议：**

- 简单返回视图：用写法二，一行搞定。
- 需要带数据：用写法一，清晰。
- 重定向：`redirect:` 前缀，或用 `RedirectAttributes` 传闪存数据。

**`addObject` 的 key 规则：** 不传 key 时，默认用"类名首字母小写"作为 key（`User` → `user`）。建议显式传 key（`mv.addObject("user", user)`）避免歧义。

**常见坑：** `addObject` 忘了传 key，模板里用 `#(user.name)` 但实际 key 是别的名字，取不到值。或者重定向时 `addObject` 的数据不会传递到重定向后的请求（重定向是新请求），要用 `RedirectAttributes.addFlashAttribute`。

### 9.4 `setSessionInView(true)` 的安全争议

Enjoy 配置里有 `jfr.setSessionInView(true)`，让模板里能直接写 `#(session.getAttribute("xxx"))` 访问 session。

**为什么有这个选项？** 方便——模板里直接拿 session 数据，不用 Controller 先取出来传进 ModelAndView。

**为什么有争议？** 它打破了 MVC 分层——模板（View）直接访问了 session（属于 Controller/基础设施层），导致模板和 session 耦合，测试和维护变难。

**实际开发建议：**

- **不推荐**用 `sessionInView`。正确做法是在 Controller 里把需要的数据从 session 取出，放进 ModelAndView，模板只管渲染传入的数据。
- 这符合 MVC 的"依赖注入"思想：模板不该知道数据从哪来，只管展示。

**常见坑：** 开了 `sessionInView` 后，模板里滥用 session 访问，导致改一个页面要翻 Controller + Session + 模板三处，维护成本飙升。

### 9.5 模板引擎选型：Enjoy 在生态中的位置

**主流 Java 模板引擎对比：**

| 引擎 | 语法风格 | Spring Boot 支持 | 适用场景 |
| --- | --- | --- | --- |
| Thymeleaf | HTML 标签属性（`th:text`） | 官方 Starter，自动配置 | Spring Boot 默认推荐，能被浏览器直接打开预览 |
| Freemarker | `${}` 占位符 + 标签 | 官方 Starter | 老牌，功能强，常用于邮件/代码生成 |
| Beetl | 定界符可配，接近 FM | 社区 Starter | 性能好，语法灵活 |
| **Enjoy** | `#` 指令式 | 无 Starter，手动配 | JFinal 生态，简洁高性能 |
| Velocity | `#` 指令式（类似 Enjoy） | 已被 Spring 弃用 | 老项目遗留，新项目不推荐 |

**实际开发怎么选？**

- **新项目、Spring Boot 生态**：首选 Thymeleaf（官方支持最好，IDE 插件完善）。
- **需要复杂逻辑/宏**：Freemarker 更强。
- **JFinal 老项目迁移**：继续用 Enjoy，减少改动。
- **新项目别用 Enjoy/Velocity**：生态小、资料少、招人也难。

**最佳实践：** 技术选型不只看性能，更要看**生态、可维护性、团队熟悉度**。Enjoy 性能再好，团队没人会、出问题搜不到答案，也是灾难。

### 9.6 context-path 与模板里硬编码路径的坑

`login.html` 里写了 `action="/demo/user/login"`，这个 `/demo` 是 `context-path`。这埋了个雷：

**坑：** 一旦改了 `context-path`（比如从 `/demo` 改成 `/api`），模板里所有硬编码的路径全得手动改，漏一个就 404。

**实际开发的解决方案：**

1. **用模板引擎的 URL 函数**：Thymeleaf 的 `@{}`、Freemarker 的 `<@spring.url>`，它们自动带上 context-path。
2. **相对路径**：用 `action="user/login"`（相对当前路径），但容易在嵌套路径下出错。
3. **前后端分离**：API 用独立域名/网关前缀，彻底绕开 context-path 问题。
4. **配置化**：把 context-path 注入模板变量，用变量拼接。

**最佳实践：** 模板里永远别硬编码 context-path，用引擎提供的 URL 函数或变量。

### 9.7 `@Bean` 的命名与多 ViewResolver 共存

配置里写了 `@Bean(name = "jfinalViewResolver")`，显式命名。为什么？

**多 ViewResolver 共存时：** 如果项目同时配了 Thymeleaf 和 Enjoy，Spring 需要区分它们。Bean 名字是重要标识，且 `setOrder` 决定解析优先级——数字小的先尝试解析，解析不了才轮到下一个。

**实际开发场景：**

- 主页面用 Thymeleaf（`order=0`），邮件模板用 Freemarker（`order=1`）。
- 通过 `setOrder` 控制谁先解析，配合视图名后缀/前缀区分该用哪个引擎。

**常见坑：** 多引擎共存时不设 order，或 order 一样，导致解析顺序不确定，时灵时不灵。建议每个 ViewResolver 设不同 order，且用不同的模板后缀/目录区分。

---

> 📌 **学习建议**：本模块真正要掌握的不是 Enjoy 的语法，而是"手动配置 `@Bean` 接入第三方库"这套通用技能。Spring Boot 的自动配置再强，也覆盖不了所有库——遇到没 Starter 的技术，你能冷静地写 `@Configuration` + `@Bean` 把它接进来，这才是"理解了 Spring 而不只是会用 Spring Boot"。建议你拿一个没接触过的小库（比如某个工具库），试着写配置类把它注册成 Bean 并在 Controller 里用起来，巩固这套套路。另外，模板引擎系列到此结束，现代项目多前后端分离，模板引擎用得少，但理解它的视图解析机制对理解 Spring MVC 整体流程很有帮助。
