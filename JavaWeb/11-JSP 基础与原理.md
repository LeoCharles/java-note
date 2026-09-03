# JSP 基础与原理

前面十篇你写的都是 Servlet——用 Java 代码拼 HTML 字符串（`resp.getWriter().write("<html>...")`），痛苦且易错。能不能在 HTML 里直接写 Java？这就是 **JSP**（JavaServer Pages）。本篇讲清 JSP 的本质——**它最终会被编译成一个 Servlet**，以及九大内置对象、指令/脚本/动作三大元素。按路线图设计理念，JSP 的细节（自定义标签、EL 函数）在前后端分离时代已无生产价值，本篇**只保留原理内核**——因为它是 Spring MVC 视图解析、Thymeleaf 模板引擎的前身。

> 💡 本篇建议写一个 `hello.jsp`，访问后去 Tomcat 的 `work` 目录找到它编译出的 `.java` 文件，打开看——你会发现 JSP 变成了一个继承 `HttpServlet` 的类，`out.print()` 满屏都是。亲眼看到"JSP 就是 Servlet"。

---

## 一、JSP 是什么

### 1.1 定义

**JSP** 是一种允许在 HTML 中嵌入 Java 代码的页面技术。你写 `.jsp` 文件，Tomcat 第一次访问时把它**翻译成一个 Servlet 类**（`.java`），再编译成 `.class` 执行。

```
hello.jsp（你写的）
   ↓ Tomcat 翻译
hello_jsp.java（生成的 Servlet）
   ↓ javac 编译
hello_jsp.class（执行的）
   ↓ 运行
HTTP 响应（HTML）
```

> 💡 **JSP 的本质就是 Servlet**：JSP 不是新语言，只是"写 Servlet 的另一种语法"。你写的 HTML 模板，Tomcat 翻译成 `out.write("<html>...")`；你写的 Java 脚本，原样塞进 `service()` 方法。理解这一点，JSP 的所有特性都不神秘。

> ⚠️ **为什么学 JSP**：现代前后端分离，JSP 几乎不用了。但它的"模板 + 数据 = 页面"思想是 Thymeleaf/Vue 的前身；它的"编译为 Servlet"原理让你理解 Spring MVC 的视图解析；它的九大内置对象就是 Servlet 的 Request/Response/Session 等。**学 JSP 是学原理，不是学生产工具**。

### 1.2 第一个 JSP

```jsp
<%@ page contentType="text/html;charset=UTF-8" %>
<html>
<body>
    <h1>Hello JSP</h1>
    <%
        // 这是 Java 脚本，会被塞进 service() 方法
        String name = "张三";
        out.println("<p>欢迎 " + name + "</p>");
    %>
    <p>当前时间：<%= new java.util.Date() %></p>
</body>
</html>
```

访问 `hello.jsp`，浏览器收到渲染后的 HTML。Tomcat 把它翻译成的 Servlet 大致长这样：

```java
// hello_jsp.java（Tomcat 自动生成，你不用写）
public final class hello_jsp extends HttpJspBase {  // 继承 HttpServlet
    public void _jspService(HttpServletRequest req, HttpServletResponse resp) {
        // 九大内置对象在这里创建
        PageContext pageContext = ...;
        HttpSession session = ...;
        ServletContext application = ...;
        JspWriter out = ...;   // resp.getWriter() 的包装

        out.write("<html><body>");
        out.write("<h1>Hello JSP</h1>");
        // 你的脚本原样塞进来
        String name = "张三";
        out.println("<p>欢迎 " + name + "</p>");
        out.write("<p>当前时间：");
        out.print(new java.util.Date());   // <%= %> 翻译成 out.print()
        out.write("</p>");
        out.write("</body></html>");
    }
}
```

> 💡 **看懂这个翻译结果，JSP 就懂了**：HTML 变成 `out.write()`，`<% %>` 脚本原样塞进方法体，`<%= %>` 变成 `out.print()`。**JSP 的所有魔法，本质都是"翻译成 Servlet 代码"**。

---

## 二、JSP 三大元素 ⭐

JSP 有三种语法元素：**指令**、**脚本**、**动作**。

### 2.1 指令（Directive）：配置页面

指令是给 Tomcat 的"翻译指示"，不产生输出。

```jsp
<%@ page contentType="text/html;charset=UTF-8" import="java.util.*" %>
<%@ include file="header.jsp" %>
<%@ taglib uri="http://java.sun.com/jsp/jstl/core" prefix="c" %>
```

| 指令 | 作用 | 示例 |
| :--- | :--- | :--- |
| `page` | 配置页面属性（编码、导入包、错误页） | `<%@ page import="java.util.*" %>` |
| `include` | 静态包含（编译期合并） | `<%@ include file="header.jsp" %>` |
| `taglib` | 引入标签库（JSTL） | `<%@ taglib uri="..." prefix="c" %>` |

> 💡 **静态包含 vs 动态包含**：`<%@ include %>` 是**静态包含**——编译期把另一个 JSP 的源码合并进来，变成一个 Servlet；`<jsp:include>` 是**动态包含**——运行时调用另一个 JSP 的 Servlet，各自独立。静态包含用于公共页眉页脚（合并成一个类），动态包含用于可独立变化的片段。

### 2.2 脚本（Scriptlet）：嵌入 Java

脚本是直接写在 JSP 里的 Java 代码，三种形式：

```jsp
<%  // 脚本片段：普通 Java 语句
    int a = 10;
    for (int i = 0; i < a; i++) {
        out.println(i);
    }
%>

<%=  // 表达式：直接输出值（翻译成 out.print()）
    new java.util.Date()
%>

<%!  // 声明：定义类的成员变量/方法（不在 service 里，在类体里）
    private int counter = 0;
    public String greet() { return "hello"; }
%>
```

| 语法 | 翻译结果 | 位置 |
| :--- | :--- | :--- |
| `<% 代码 %>` | 原样塞进 `_jspService()` | 方法体 |
| `<%= 表达式 %>` | `out.print(表达式)` | 方法体 |
| `<%! 声明 %>` | 类的成员变量/方法 | 类体 |

> ⚠️ **`<%! %>` 声明要小心**：它定义的是**类的成员变量**，JSP 编译出的 Servlet 是单例——所以 `<%! %>` 里的变量是**共享的、非线程安全**的（和 02 篇讲的 Servlet 单例同理）。不要在 `<%! %>` 放可变状态，用 `<% %>` 局部变量才安全。

> 💡 **脚本越多越乱**：JSP 里写满 Java 代码（连数据库、循环、判断），页面变成"嵌 HTML 的 Java 程序"，难维护。这就是为什么后来有了 EL 表达式 + JSTL（12 篇）替代脚本，以及 MVC（13 篇）把 Java 逻辑挪出 JSP。**现代开发连 JSP 都不用了**——前后端分离，后端只返回 JSON。

### 2.3 动作（Action）：内置标签

动作是 JSP 规范预定义的 XML 标签，执行特定操作：

```jsp
<!-- 动态包含 -->
<jsp:include page="header.jsp" />

<!-- 转发 -->
<jsp:forward page="/result.jsp" />

<!-- 用 JavaBean -->
<jsp:useBean id="user" class="com.example.User" scope="request" />
<jsp:setProperty name="user" property="name" value="张三" />
<jsp:getProperty name="user" property="name" />
```

> 💡 **动作的底层**：`<jsp:forward>` 翻译成 `RequestDispatcher.forward()`（04 篇讲过）；`<jsp:include>` 翻译成运行时调用另一个 JSP 的 Servlet。**JSP 动作本质是 Servlet API 的标签化封装**。

---

## 三、九大内置对象 ⭐

JSP 的 `_jspService()` 方法里，Tomcat 自动创建了 9 个对象，你在脚本里直接用，不用声明：

| 对象 | 类型 | 对应 Servlet 对象 | 作用 |
| :--- | :--- | :--- | :--- |
| `request` | `HttpServletRequest` | 就是 Servlet 的 req | 请求 |
| `response` | `HttpServletResponse` | 就是 Servlet 的 resp | 响应 |
| `session` | `HttpSession` | `req.getSession()` | 会话 |
| `application` | `ServletContext` | `getServletContext()` | 全局域 |
| `out` | `JspWriter` | `resp.getWriter()` 的包装 | 输出 |
| `pageContext` | `PageContext` | JSP 专属 | 页面域（最小域对象） |
| `config` | `ServletConfig` | Servlet 配置 | 初始化参数 |
| `page` | `Object`（this） | 当前 Servlet 实例 | 极少用 |
| `exception` | `Throwable` | 异常 | 仅错误页可用 |

```jsp
<%
    // 九大内置对象直接用，不用声明
    String name = request.getParameter("name");     // request
    session.setAttribute("user", name);             // session
    application.setAttribute("appStart", new java.util.Date());  // application
    out.println("当前页面 URL：" + request.getRequestURL());   // out
%>
```

> 💡 **九大内置对象就是 Servlet 对象**：`request`/`response`/`session`/`application` 就是前几篇讲的 Request/Response/Session/ServletContext。**JSP 没有新发明对象，只是把 Servlet 的对象"内置"了，让你不用写 `req.getParameter` 而直接 `request.getParameter`**。

> 💡 **pageContext 是九大对象的入口**：`pageContext.getRequest()`、`pageContext.getSession()`、`pageContext.getServletContext()`——它能取到其他八个对象。它也是四大域对象里最小的"页面域"（10 篇讲过）。

> ⚠️ **exception 只在错误页可用**：要先用 `<%@ page isErrorPage="true" %>` 声明错误页，才能用 `exception` 对象。这是 JSP 异常处理机制。

---

## 四、JSP 与 Servlet 的关系 ⭐

这是本篇核心：**JSP 和 Servlet 是同一东西的两种形态**。

### 4.1 翻译过程

```
hello.jsp  ──翻译──▶  hello_jsp.java（Servlet）──编译──▶  hello_jsp.class
```

- 第一次访问 JSP：Tomcat 翻译 `.jsp` → `.java`（Servlet），再编译 → `.class`，**首次较慢**。
- 后续访问：直接用已编译的 `.class`，和普通 Servlet 一样快。
- JSP 修改后：Tomcat 检测到文件变化，重新翻译编译（热加载）。

### 4.2 何时用 Servlet，何时用 JSP

| 场景 | 选谁 | 理由 |
| :--- | :--- | :--- |
| 返回 JSON、少量 HTML | **Servlet** | 逻辑为主，少量输出 |
| 生成复杂 HTML 页面 | **JSP** | HTML 为主，少量 Java |
| 前后端分离 | **都不用** | 后端返回 JSON，前端渲染 |

> 💡 **MVC 分工**：Servlet 做 Controller（取参、调业务、转发），JSP 做 View（渲染 HTML）。这就是 13 篇要讲的 MVC 模式——**Servlet + JSP 天然就是 MVC 的落地**，Spring MVC 的 `@Controller` + 模板引擎是这个模式的工程化。

> ⚠️ **JSP 的衰落**：JSP 把 Java 嵌进 HTML，前后端耦合，前端开发者看不懂，后端要管页面。前后端分离后，后端只返回 JSON，前端用 Vue/React 渲染。**JSP 在新项目中几乎绝迹**，但它的"模板 + 数据"思想活在 Thymeleaf 等服务端模板里，活在 Vue 的单文件组件里。

---

## 五、JSP 的四大作用域

JSP 的 `pageContext` 提供了访问四大域对象的统一入口（10 篇讲过四大域）：

```jsp
<%
    // pageContext 统一操作四大域
    pageContext.setAttribute("p", "页面域", PageContext.PAGE_SCOPE);       // 当前页
    pageContext.setAttribute("r", "请求域", PageContext.REQUEST_SCOPE);    // 一次请求
    pageContext.setAttribute("s", "会话域", PageContext.SESSION_SCOPE);    // 一次会话
    pageContext.setAttribute("a", "应用域", PageContext.APPLICATION_SCOPE);// 全应用

    // 也可直接用内置对象
    request.setAttribute("user", "张三");
    session.setAttribute("cart", "商品");
    application.setAttribute("config", "xxx");
%>
```

> 💡 **JSP 的四大作用域就是 10 篇的四大域对象**：PageContext（页面）/ request（请求）/ Session（会话）/ ServletContext（应用）。JSP 只是多了 `pageContext` 这个统一入口和"页面域"这个最小域。选型原则不变：能用小范围就不用大范围。

---

## ⚠️ 重点

1. **JSP 本质是 Servlet**：JSP 被翻译成继承 `HttpServlet` 的类，HTML 变 `out.write()`，脚本塞进 `service()`。
2. **三大元素**：指令（配置）、脚本（嵌入 Java）、动作（内置标签）。
3. **九大内置对象就是 Servlet 对象**：request/response/session/application/out/pageContext/config/page/exception。
4. **`<%= %>` 输出表达式，`<% %>` 脚本，`<%! %>` 声明类成员**（单例，非线程安全）。
5. **静态包含（编译期合并）vs 动态包含（运行时调用）**：`<%@ include %>` vs `<jsp:include>`。
6. **首次访问 JSP 慢**：要翻译 + 编译，后续访问用已编译的 class。
7. **JSP + Servlet = MVC 雏形**：Servlet 做 Controller，JSP 做 View。
8. **JSP 已衰落**：前后端分离时代后端返回 JSON，但"模板 + 数据"思想活在 Thymeleaf/Vue。

---

## 💻 实战案例：用户列表页

需求：Servlet 查用户列表存进 request 域，转发到 JSP 渲染表格——经典的 Controller + View 分工。

**UserListServlet（Controller）**：

```java
@WebServlet("/users")
public class UserListServlet extends HttpServlet {
    protected void doGet(HttpServletRequest req, HttpServletResponse resp) throws ServletException, IOException {
        // 1. 查数据（模拟）
        List<User> users = Arrays.asList(
            new User(1, "张三", 20),
            new User(2, "李四", 22)
        );
        // 2. 存进 request 域（转发链共享）
        req.setAttribute("users", users);
        // 3. 转发到 JSP 渲染
        req.getRequestDispatcher("/userList.jsp").forward(req, resp);
    }
}
```

**userList.jsp（View）**：

```jsp
<%@ page contentType="text/html;charset=UTF-8" import="com.example.User,java.util.*" %>
<html>
<body>
    <table border="1">
        <tr><th>ID</th><th>姓名</th><th>年龄</th></tr>
        <%
            // 从 request 域取数据（转发链传来）
            List<User> users = (List<User>) request.getAttribute("users");
            for (User u : users) {
        %>
            <tr>
                <td><%= u.getId() %></td>
                <td><%= u.getName() %></td>
                <td><%= u.getAge() %></td>
            </tr>
        <%
            }
        %>
    </table>
</body>
</html>
```

> 💡 **这就是 MVC 的雏形**：Servlet 取数据存 request 域、转发，JSP 从 request 域取数据渲染——Controller 和 View 分工。但 JSP 里写满 Java 脚本很乱，下篇 12 用 EL + JSTL 替代脚本，13 篇用 MVC 把这个模式正式化。**Spring MVC 的 `@Controller` + Thymeleaf 就是这个模式的工程化**。

---

## 🚀 新版本补充

- **JSP 2.1+**：支持 EL 表达式（`${user.name}`），减少脚本。
- **Servlet 3.1+**：JSP 可与异步 Servlet 配合，但实际很少这么用。
- **JSP 的替代**：Thymeleaf（Spring Boot 推荐）、FreeMarker、Velocity——都是"模板 + 数据 = 页面"思想，但语法更干净、不嵌 Java。

---

## 📌 在 Spring Boot 中

> 本篇讲的 JSP 编译为 Servlet、九大内置对象、模板渲染，在 Spring Boot 中由 Thymeleaf 等模板引擎接管，且 JSP 在 Spring Boot（尤其 jar 打包）中**不推荐使用**。下面逐一对照，给出实际开发代码，以及"出问题怎么回到 JSP 原理排查"。实际开发你几乎不写 JSP——前后端分离返回 JSON，或用 Thymeleaf 渲染页面，但理解了本篇，模板引擎、视图解析、Model 传值对你就是透明的。

### 1. 视图渲染：从"JSP + 脚本"到"Thymeleaf 模板"

**原生**：本篇实战用 `userList.jsp` + `<% %>` 脚本循环渲染表格。
**Spring Boot**：Thymeleaf 模板，`th:each` 循环，不写 Java 代码。

```html
<!-- userList.html（Thymeleaf，放在 templates/ 下） -->
<html xmlns:th="http://www.thymeleaf.org">
<body>
    <table border="1">
        <tr><th>ID</th><th>姓名</th><th>年龄</th></tr>
        <tr th:each="u : ${users}">           <!-- 等价 <% for(User u : users) %> -->
            <td th:text="${u.id}"></td>         <!-- 等价 <%= u.getId() %> -->
            <td th:text="${u.name}"></td>
            <td th:text="${u.age}"></td>
        </tr>
    </table>
</body>
</html>
```

```java
// Controller（等价本篇的 UserListServlet）
@GetMapping("/users")
public String userList(Model model) {
    List<User> users = userService.findAll();
    model.addAttribute("users", users);   // 等价 req.setAttribute
    return "userList";                    // 等价 forward 到 userList.html
}
```

> 💡 **原理对应**：Thymeleaf 的 `th:each` 等价 JSP 的 `<% for %>`，`${users}` 等价 `<%= request.getAttribute("users") %>`。**本篇讲的"模板 + 数据 = 页面"思想完全一样**——Controller 存数据、模板取数据渲染。只是 Thymeleaf 不嵌 Java，语法更干净，是"HTML 友好"的模板。

> 💡 **原理排查**：Thymeleaf 页面不渲染？检查模板是否在 `templates/` 下、`return "userList"` 是否对应 `userList.html`、`Model.addAttribute` 的 key 和模板里的 `${users}` 是否一致。回到 JSP 原理：视图名要对应模板文件，数据要存进域（request 域）才能取到。

### 2. 视图解析：从"RequestDispatcher.forward"到"ViewResolver"

**原生**：`req.getRequestDispatcher("/userList.jsp").forward(req, resp)` 手动转发到 JSP。
**Spring Boot**：`ViewResolver` 根据 Controller 返回的视图名自动找模板。

```java
@GetMapping("/users")
public String userList(Model model) {
    model.addAttribute("users", userService.findAll());
    return "userList";   // ViewResolver 把 "userList" 解析成 templates/userList.html
}
```

> 💡 **原理对应**：Spring MVC 的 `ViewResolver` 就是本篇 `RequestDispatcher.forward` 的封装——Controller 返回逻辑视图名（`userList`），ViewResolver 拼接前缀（`classpath:/templates/`）和后缀（`.html`），找到模板文件，再 forward 过去。**本篇的"转发到 JSP"，Spring MVC 用 ViewResolver 自动化了**。

> 💡 **原理排查**：报 404 或模板找不到？检查 `spring.thymeleaf.prefix`（默认 `classpath:/templates/`）、`suffix`（默认 `.html`）、视图名拼写。回到 JSP 原理：转发路径要对得上文件路径。

### 3. 九大内置对象：从"JSP 内置"到"Spring 注入"

**原生**：JSP 里直接用 `request`/`session`/`application` 等九大内置对象。
**Spring Boot**：Controller 方法签名注入需要的对象。

```java
@GetMapping("/profile")
public String profile(
        HttpServletRequest request,      // 等价 JSP 的 request
        HttpSession session,             // 等价 JSP 的 session
        ServletContext application,      // 等价 JSP 的 application
        Model model) {                   // 等价往 request 域 setAttribute
    String name = request.getParameter("name");
    session.setAttribute("user", name);
    model.addAttribute("msg", "欢迎");
    return "profile";
}
```

> 💡 **原理对应**：Spring MVC 让你在 Controller 方法签名注入 `HttpServletRequest`/`HttpSession`/`ServletContext`——就是本篇 JSP 的九大内置对象。**JSP 把它们"内置"（不用声明），Spring 让你"按需注入"（声明才用）**，本质都是 Servlet 对象。

### 4. 前后端分离：从"JSP 渲染页面"到"@RestController 返回 JSON"

**原生**：JSP 在服务端渲染完整 HTML 发给浏览器。
**Spring Boot**：`@RestController` 返回 JSON，前端（Vue/React）渲染页面。

```java
@RestController   // 返回 JSON，不渲染页面
public class UserApiController {
    @GetMapping("/api/users")
    public List<User> list() {
        return userService.findAll();   // 自动序列化为 JSON
        // 前端拿到 [{"id":1,"name":"张三"},...]，自己渲染表格
    }
}
```

> 💡 **原理对应**：前后端分离后，后端不再渲染 HTML（不用 JSP/Thymeleaf），只返回数据（JSON）。**本篇的"模板 + 数据 = 页面"中，后端只负责"数据"，"模板"挪到前端**。`@RestController` = `@Controller` + `@ResponseBody`，`@ResponseBody` 把返回值序列化成 JSON 写进响应体（05 篇讲过）。

> 💡 **选型**：传统 Web 应用（有页面、同域）用 Thymeleaf；前后端分离/跨域用 `@RestController` + JSON。**JSP 在两者中都已边缘化**——Thymeleaf 比 JSP 干净，JSON 模式比 JSP 解耦。

### 5. JSP 在 Spring Boot 的局限

> ⚠️ **Spring Boot 不推荐 JSP**：Spring Boot 默认 jar 打包，JSP 在 jar 里无法解析（JSP 规范要求文件在文件系统的 `WEB-INF/` 下，jar 内不支持）。要用 JSP 必须 war 打包 + 配置 `spring.mvc.view.prefix=/WEB-INF/jsp/`。**这是 JSP 落落的直接技术原因之一**——Thymeleaf 从 classpath 读模板，jar 打包完美支持。

> 💡 **原理排查**：Spring Boot 用 JSP 报 404 或白页？检查是否 war 打包、JSP 是否在 `src/main/webapp/WEB-INF/jsp/`、`spring.mvc.view.prefix/suffix` 配置。回到 JSP 原理：JSP 要被 Tomcat 翻译编译，需要文件系统路径，jar 内做不到。

---

> 一句话：**JSP 是"写 Servlet 的 HTML 语法"，本质编译成 Servlet**。Spring Boot 里你几乎不用 JSP——页面渲染用 Thymeleaf（`th:each`/`${}` 对应 JSP 的脚本/EL），前后端分离用 `@RestController` 返回 JSON。但 JSP 的"模板 + 数据 = 页面"思想、九大内置对象（就是 Servlet 对象）、ViewResolver 转发原理，全部活在 Spring MVC 里。理解了本篇，Thymeleaf、视图解析、Model 传值对你就是透明的。**出模板不渲染、视图找不到、JSP 404 问题时，你仍要回到 JSP 原理排查**：视图名对吗、模板在 classpath 吗、数据存进域了吗、jar 打包别用 JSP。

## 本章小结

本篇讲清了 JSP：它本质是编译成 Servlet 的页面技术，HTML 变 `out.write()`，脚本塞进 `service()`。重点掌握三大元素（指令/脚本/动作）、九大内置对象（就是 Servlet 对象）、`<%= %>` 输出 vs `<% %>` 脚本 vs `<%! %>` 声明（单例非线程安全）、静态包含 vs 动态包含、JSP + Servlet 的 MVC 雏形。核心认知：JSP 已衰落但"模板 + 数据"思想活在 Thymeleaf，九大内置对象就是 Spring 可注入的 Servlet 对象。下一篇 [12-EL 表达式与 JSTL](12-EL%20表达式与%20JSTL.md) 讲如何用 EL + JSTL 替代 JSP 脚本，让页面更干净——理解 Thymeleaf 表达式的前身。
