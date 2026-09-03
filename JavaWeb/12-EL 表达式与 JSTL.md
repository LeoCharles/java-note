# EL 表达式与 JSTL

上一篇的 JSP 里写满 `<% %>` Java 脚本——循环、判断、取属性，页面变成"嵌 HTML 的 Java 程序"，前端看不懂、后端难维护。能不能在 JSP 里**不写 Java 代码**也能取数据、做循环判断？这就是 **EL 表达式**和 **JSTL** 标签库。本篇讲清 EL 的取值与运算、11 个隐式对象，以及 JSTL 的 `<c:if>`/`<c:forEach>` 核心标签。按路线图理念，EL/JSTL 的格式化标签等细节已无生产价值，本篇**只保留原理**——因为它是 Thymeleaf `${}`/`th:each` 的前身。

> 💡 本篇建议把 11 篇那个写满脚本的 `userList.jsp` 用 EL + JSTL 重写一遍，对比两种写法——你会直观感受到"脚本 JSP"到"标签 JSP"的进化，这正是走向 Thymeleaf 的第一步。

---

## 一、EL 表达式

### 1.1 什么是 EL

**EL**（Expression Language，表达式语言）是 JSP 2.0 引入的轻量表达式语法，用 `${...}` 取值和运算，替代 `<%= %>` 脚本。

```jsp
<%-- 脚本写法（11 篇的） --%>
<%= ((User)request.getAttribute("user")).getName() %>

<%-- EL 写法（本篇） --%>
${user.name}
```

> 💡 **EL 的核心价值**：用 `${user.name}` 替代一长串强转 + getAttribute + getter。**EL 自动从域对象找数据、自动调 getter、自动处理 null**，不用写 Java 代码。这是"把 Java 逻辑挪出 JSP"的第一步。

### 1.2 EL 取值：从域对象找数据

EL 表达式 `${user}` 会按**从小到大**的顺序在四大域里找名为 `user` 的属性：

```
${user} 的查找顺序：
PageContext → request → Session → application
找到第一个就返回，找不到返回 null（不报错）
```

```jsp
<%
    // Servlet 里存数据（Controller 的活）
    request.setAttribute("user", new User("张三", 20));
    session.setAttribute("count", 100);
%>

<%-- EL 取值（View 的活） --%>
${user.name}      <%-- 自动调 getName() --%>
${user.age}       <%-- 自动调 getAge() --%>
${count}          <%-- 直接取值 --%>
```

> 💡 **EL 的属性访问规则**：`${user.name}` 等价于 `user.getName()`——EL 把 `name` 的首字母大写加 `get`，调 getter。如果 `user` 是 `Map`，则 `user.name` 等价 `user.get("name")`。**EL 不直接访问字段，永远走 getter**，这是封装的体现。

> ⚠️ **EL 找不到不报错**：`${notExist}` 取不到时返回空字符串而非异常。这和 `<%= %>` 取到 null 再调用会 NPE 不同——EL 更"宽容"，适合页面渲染。

### 1.3 EL 运算

EL 支持算术、关系、逻辑、empty 运算：

```jsp
${1 + 2}            <%-- 3 --%>
${user.age > 18}    <%-- true/false --%>
${empty user}       <%-- user 为 null 或空字符串返回 true --%>
${not empty list}   <%-- 列表非空 --%>
${a > b ? "大" : "小"}  <%-- 三元 --%>
```

> 💡 **`empty` 是 EL 最常用的运算符**：`${empty user}` 判断 user 是否为 null/空字符串/空集合，页面渲染前判空用它，避免 NPE。等价 JSTL 的 `<c:if test="${empty user}">`。

### 1.4 EL 的 11 个隐式对象 ⭐

EL 内置了 11 个隐式对象（注意：和 JSP 的九大内置对象不同），用于访问各种数据：

| 隐式对象 | 作用 | 示例 |
| :--- | :--- | :--- |
| `pageScope` | 只查页面域 | `${pageScope.name}` |
| `requestScope` | 只查请求域 | `${requestScope.user}` |
| `sessionScope` | 只查会话域 | `${sessionScope.cart}` |
| `applicationScope` | 只查应用域 | `${applicationScope.config}` |
| `param` | 请求参数（单值） | `${param.name}` 等价 `request.getParameter("name")` |
| `paramValues` | 请求参数（多值） | `${paramValues.hobby[0]}` |
| `header` | 请求头（单值） | `${header["User-Agent"]}` |
| `headerValues` | 请求头（多值） | `${headerValues["Accept"][0]}` |
| `cookie` | Cookie | `${cookie.user.value}` |
| `initParam` | 全局初始化参数 | `${initParam.dbUrl}` |
| `pageContext` | 页面上下文 | `${pageContext.request.contextPath}` |

```jsp
<%-- 指定域取值（避免歧义） --%>
${requestScope.user.name}   <%-- 只从 request 域找 --%>
${sessionScope.cart}       <%-- 只从 Session 域找 --%>

<%-- 取请求参数 --%>
${param.username}          <%-- 等价 request.getParameter("username") --%>

<%-- 取 Cookie --%>
${cookie.JSESSIONID.value} <%-- 取 JSESSIONID 的值 --%>

<%-- 取项目路径（最常用） --%>
${pageContext.request.contextPath}  <%-- 如 /myapp，用于拼 URL --%>
```

> 💡 **`${pageContext.request.contextPath}` 是 EL 最常用之一**：动态获取项目名拼 URL，避免硬编码。如 `<a href="${pageContext.request.contextPath}/user">用户</a>`，部署到不同项目名都能用。Spring Boot 里对应 `@RequestMapping` 的相对路径。

> ⚠️ **EL 隐式对象 vs JSP 九大内置对象**：两者不同。JSP 九大内置对象（request/session 等）是 Java 对象，在脚本里用；EL 的 11 个隐式对象（pageScope/param 等）是 EL 专用的 Map，在 `${}` 里用。`pageContext` 是唯一重叠的——它既是 JSP 内置对象，也是 EL 隐式对象。

---

## 二、JSTL 标签库

### 2.1 什么是 JSTL

**JSTL**（JSP Standard Tag Library，JSP 标准标签库）是用 XML 风格标签替代 Java 脚本完成循环、判断、格式化。它让 JSP 彻底告别 `<% %>`。

```jsp
<%-- 脚本循环（11 篇的） --%>
<%
    for (User u : users) {
        out.println("<tr><td>" + u.getName() + "</td></tr>");
    }
%>

<%-- JSTL 循环（本篇） --%>
<c:forEach items="${users}" var="u">
    <tr><td>${u.name}</td></tr>
</c:forEach>
```

### 2.2 引入 JSTL

```jsp
<%-- 引入核心标签库 --%>
<%@ taglib uri="http://java.sun.com/jsp/jstl/core" prefix="c" %>
```

需要依赖（Maven）：

```xml
<dependency>
    <groupId>javax.servlet</groupId>
    <artifactId>jstl</artifactId>
    <version>1.2</version>
</dependency>
```

> 💡 **JSTL 的本质也是 Servlet 代码**：`<c:forEach>` 在 JSP 翻译时被转成 Java 的 `for` 循环，`<c:if>` 转成 `if`。**JSTL 没有脱离"JSP 编译成 Servlet"的原理**（11 篇讲过），只是用标签语法替代脚本，让页面更干净、前端更易读。

### 2.3 核心标签 ⭐

JSTL 核心标签库（`c` 前缀）最常用：

#### `<c:if>` 条件判断

```jsp
<c:if test="${not empty user}">
    <p>欢迎 ${user.name}</p>
</c:if>
<c:if test="${empty user}">
    <p>请登录</p>
</c:if>
```

> ⚠️ **`<c:if>` 没有 else**：JSTL 的 `<c:if>` 只有 `test`，没有 else 分支。要 if-else 用 `<c:choose>`（见下）。

#### `<c:choose>` 多分支（if-else if-else）

```jsp
<c:choose>
    <c:when test="${user.age < 18}">
        未成年
    </c:when>
    <c:when test="${user.age < 60}">
        成年
    </c:when>
    <c:otherwise>
        老年
    </c:otherwise>
</c:choose>
```

#### `<c:forEach>` 循环 ⭐

```jsp
<%-- 遍历集合 --%>
<c:forEach items="${users}" var="u" varStatus="vs">
    <tr>
        <td>${vs.index}</td>     <%-- 当前索引（从 0） --%>
        <td>${vs.count}</td>     <%-- 当前序号（从 1） --%>
        <td>${u.name}</td>
    </tr>
</c:forEach>

<%-- 数字循环 --%>
<c:forEach begin="1" end="10" var="i">
    <a href="?page=${i}">第 ${i} 页</a>
</c:forEach>
```

> 💡 **`varStatus` 是分页利器**：`${vs.count}` 给序号、`${vs.index}` 给索引、`${vs.first}`/`${vs.last}` 判首尾。分页列表渲染常用。

### 2.4 其他标签库

| 标签库 | 前缀 | 用途 | 现代价值 |
| :--- | :--- | :--- | :--- | 
| 核心库 | `c` | 循环/判断/URL | ⭐ 唯一还有原理价值 |
| 格式化库 | `fmt` | 日期/数字格式化 | 低（前端格式化） |
| 函数库 | `fn` | 字符串函数 | 低（EL 3.0 内置） |
| SQL 库 | `sql` | JSP 里写 SQL | ❌ 已废弃（违反 MVC） |
| XML 库 | `x` | XML 处理 | ❌ 已废弃 |

> ⚠️ **SQL 标签库是反面教材**：JSTL 曾有 `<sql:query>` 让你在 JSP 里直接写 SQL——这严重违反 MVC（视图不该碰数据库），已被废弃。**理解了为什么废弃，就理解了 MVC 的意义**（13 篇讲）。

---

## 三、EL + JSTL 替代脚本

### 3.1 对比：同一个页面三种写法

需求：显示用户列表，空列表提示"暂无数据"。

**脚本版（11 篇风格，乱）**：

```jsp
<%
    List<User> users = (List<User>) request.getAttribute("users");
    if (users == null || users.isEmpty()) {
        out.println("<p>暂无数据</p>");
    } else {
        for (User u : users) {
            out.println("<tr><td>" + u.getName() + "</td></tr>");
        }
    }
%>
```

**EL + JSTL 版（本篇，干净）**：

```jsp
<c:choose>
    <c:when test="${empty users}">
        <p>暂无数据</p>
    </c:when>
    <c:otherwise>
        <c:forEach items="${users}" var="u">
            <tr><td>${u.name}</td></tr>
        </c:forEach>
    </c:otherwise>
</c:choose>
```

> 💡 **进化方向**：脚本 → EL + JSTL → Thymeleaf → 前后端分离。每一步都在"把 Java 逻辑挪出页面"。EL + JSTL 是第二步，Thymeleaf 是第三步（`th:each`/`th:if` 对应 `<c:forEach>`/`<c:if>`），前后端分离是终极（页面挪到前端，后端只给 JSON）。

---

## ⚠️ 重点

1. **EL 用 `${}` 取值，替代 `<%= %>`**：`${user.name}` 自动走 getter，自动处理 null。
2. **EL 按域从小到大查找**：PageContext → request → Session → application，可用 `requestScope` 等指定域。
3. **`empty` 运算符最常用**：`${empty user}` 判空，避免 NPE。
4. **EL 的 11 个隐式对象**：`pageScope`/`requestScope`/`sessionScope`/`applicationScope`/`param`/`paramValues`/`header`/`headerValues`/`cookie`/`initParam`/`pageContext`。
5. **`${pageContext.request.contextPath}` 拼项目路径**：动态获取项目名，最常用。
6. **JSTL `<c:forEach>` 循环、`<c:if>`/`<c:choose>` 判断**：替代脚本循环判断。
7. **`<c:if>` 没有 else**：用 `<c:choose>`/`<c:when>`/`<c:otherwise>` 实现多分支。
8. **JSTL 本质还是编译成 Servlet**：标签翻译成 Java 代码，没脱离 JSP 原理。
9. **SQL 标签库已废弃**：JSP 里写 SQL 违反 MVC，是反面教材。

---

## 💻 实战案例：分页用户列表

需求：用 EL + JSTL 重写 11 篇的用户列表，加分页。

**PageServlet（Controller）**：

```java
@WebServlet("/users")
public class UserListServlet extends HttpServlet {
    protected void doGet(HttpServletRequest req, HttpServletResponse resp) throws ServletException, IOException {
        int page = Integer.parseInt(req.getParameter("page") == null ? "1" : req.getParameter("page"));
        // 模拟分页查询
        List<User> users = userService.findByPage(page, 10);
        int total = userService.count();
        int totalPages = (total + 9) / 10;

        req.setAttribute("users", users);
        req.setAttribute("page", page);
        req.setAttribute("totalPages", totalPages);
        req.getRequestDispatcher("/userList.jsp").forward(req, resp);
    }
}
```

**userList.jsp（View，纯 EL + JSTL，无脚本）**：

```jsp
<%@ page contentType="text/html;charset=UTF-8" %>
<%@ taglib uri="http://java.sun.com/jsp/jstl/core" prefix="c" %>
<html>
<body>
    <table border="1">
        <tr><th>序号</th><th>ID</th><th>姓名</th></tr>
        <c:choose>
            <c:when test="${empty users}">
                <tr><td colspan="3">暂无数据</td></tr>
            </c:when>
            <c:otherwise>
                <c:forEach items="${users}" var="u" varStatus="vs">
                    <tr>
                        <td>${vs.count}</td>
                        <td>${u.id}</td>
                        <td>${u.name}</td>
                    </tr>
                </c:forEach>
            </c:otherwise>
        </c:choose>
    </table>

    <%-- 分页导航 --%>
    <c:forEach begin="1" end="${totalPages}" var="i">
        <a href="${pageContext.request.contextPath}/users?page=${i}"
           style="${i == page ? 'font-weight:bold' : ''}">
           ${i}
        </a>
    </c:forEach>
</body>
</html>
```

> 💡 **这就是 MVC 的 View 层**：JSP 只负责渲染，不写 Java 逻辑——数据从 request 域取（`${users}`），循环用 `<c:forEach>`，判断用 `<c:choose>`，路径用 `${pageContext.request.contextPath}`。**Controller（Servlet）取数据，View（JSP）渲染，Model（User）承载数据**——这就是 13 篇要讲的 MVC。Spring MVC 的 `@Controller` + Thymeleaf 是这个模式的工程化。

---

## 🚀 新版本补充

- **EL 3.0（JSR 341）**：EL 独立于 JSP，支持流式操作（`${users.stream().filter(u -> u.age > 18).toList()}`）、Lambda。但实际很少在页面用这么复杂的表达式。
- **JSTL 1.2**：稳定版本，核心标签足够用。
- **替代趋势**：EL + JSTL → Thymeleaf（`th:each`/`th:if`/`${}`）→ 前后端分离（Vue/React）。

---

## 📌 在 Spring Boot 中

> 本篇讲的 EL 表达式、JSTL 标签、`${}` 取值、`<c:forEach>` 循环，在 Spring Boot 中由 Thymeleaf 的 `${}`/`th:each`/`th:if` 接管，且 JSTL 在 Spring Boot 中几乎不用。下面逐一对照，给出实际开发代码，以及"出问题怎么回到 EL/JSTL 原理排查"。实际开发你几乎不写 EL/JSTL——页面渲染用 Thymeleaf，前后端分离返回 JSON，但理解了本篇，Thymeleaf 的表达式、循环判断、变量取值对你就是透明的。

### 1. 表达式取值：从"EL ${user.name}"到"Thymeleaf ${user.name}"

**原生**：JSP 的 EL `${user.name}` 从域对象取值，自动调 getter。
**Spring Boot**：Thymeleaf 的 `${user.name}` 语法几乎一样，从 Model 取值。

```html
<!-- Thymeleaf（和 EL 语法几乎一样） -->
<p>欢迎 <span th:text="${user.name}">默认值</span></p>
<p>年龄：<span th:text="${user.age}"></span></p>
```

> 💡 **原理对应**：Thymeleaf 的 `${user.name}` 和本篇 EL 的 `${user.name}` **语法几乎一样、原理一样**——都从域/Model 取值、自动调 getter。**本篇学的 EL 取值规则，Thymeleaf 原样继承**。区别是 Thymeleaf 用 `th:text` 标签属性而非 `${}` 直接输出（更 HTML 友好，浏览器能直接打开预览）。

> 💡 **原理排查**：Thymeleaf `${user.name}` 不显示？检查 Model 是否 `addAttribute("user", user)`、`user` 是否有 `getName()`、模板里 `${}` 拼写。回到 EL 原理：取值靠 getter，数据要在域/Model 里。

### 2. 循环：从"<c:forEach>"到"th:each"

**原生**：JSTL `<c:forEach items="${users}" var="u">`。
**Spring Boot**：Thymeleaf `th:each="u : ${users}"`。

```html
<!-- Thymeleaf 循环（对应 <c:forEach>） -->
<tr th:each="u, vs : ${users}">
    <td th:text="${vs.count}"></td>     <!-- 对应 varStatus.count -->
    <td th:text="${u.id}"></td>
    <td th:text="${u.name}"></td>
</tr>
```

> 💡 **原理对应**：Thymeleaf 的 `th:each` 对应 JSTL 的 `<c:forEach>`，`vs` 对应 `varStatus`（状态变量），`${vs.count}` 取序号。**本篇学的循环 + 状态变量模式，Thymeleaf 完全继承**，只是语法从 XML 标签变成 HTML 属性。

### 3. 条件判断：从"<c:if>/<c:choose>"到"th:if/th:switch"

**原生**：JSTL `<c:if test="${empty users}">` 和 `<c:choose>`/`<c:when>`/`<c:otherwise>`。
**Spring Boot**：Thymeleaf `th:if`/`th:switch`/`th:case`。

```html
<!-- Thymeleaf 条件（对应 <c:choose>） -->
<div th:if="${empty users}">暂无数据</div>     <!-- 对应 <c:if> -->
<tr th:each="u : ${users}">
    <td th:text="${u.name}"></td>
</tr>

<!-- 多分支（对应 <c:choose>/<c:when>） -->
<div th:switch="${user.age}">
    <span th:case="*{lt 18}">未成年</span>
    <span th:case="*{ge 18}">成年</span>
</div>
```

> 💡 **原理对应**：Thymeleaf 的 `th:if` 对应 `<c:if>`，`th:switch`/`th:case` 对应 `<c:choose>`/`<c:when>`。**本篇学的条件判断模式，Thymeleaf 用 HTML 属性表达，更贴合 HTML 语法**。

### 4. 项目路径：从"${pageContext.request.contextPath}"到"相对路径 / @{...}"

**原生**：EL `${pageContext.request.contextPath}/user` 拼项目路径。
**Spring Boot**：Thymeleaf 的 `@{...}` 自动处理上下文路径。

```html
<!-- Thymeleaf URL（对应 EL 的 contextPath 拼接） -->
<a th:href="@{/user}">用户</a>          <!-- 自动加项目路径 -->
<form th:action="@{/login}" method="post">  <!-- 自动加项目路径 -->
```

> 💡 **原理对应**：Thymeleaf 的 `@{/user}` 自动拼接应用上下文路径，等价本篇的 `${pageContext.request.contextPath}/user`。**本篇学的"动态拼项目路径"，Thymeleaf 用 `@{}` 一键搞定**，不用手写 `pageContext.request.contextPath`。

> 💡 **原理排查**：Thymeleaf 链接路径不对？检查 `@{}` 是否用了（别用普通 `/user`）、Spring Boot 的 `server.servlet.context-path` 配置。回到 EL 原理：路径要带项目名，`@{}` 自动处理。

### 5. 取请求参数：从"${param.name}"到"@RequestParam / 表单绑定"

**原生**：EL `${param.name}` 取请求参数（GET 查询串或 POST 表单）。
**Spring Boot**：Controller 用 `@RequestParam` 取，或表单绑定到对象。

```java
// Spring Boot 取参数（对应 ${param.name}）
@GetMapping("/search")
public String search(@RequestParam String name, Model model) {
    // name 已自动注入（等价 ${param.name}）
    model.addAttribute("result", service.search(name));
    return "result";
}

// 表单绑定（更高级）
@PostMapping("/save")
public String save(User user) {   // 表单字段自动绑定到 User 对象
    userService.save(user);
    return "redirect:/users";
}
```

> 💡 **原理对应**：EL 的 `${param.name}` 在 Spring Boot 里用 `@RequestParam String name` 替代——Controller 取参数，存进 Model，模板用 `${}` 显示。**本篇的 EL 取参数，Spring MVC 用注解 + Model 分层处理**，不再在页面直接取参数。

### 6. 前后端分离：从"EL/JSTL 服务端渲染"到"JSON + 前端渲染"

**原生**：EL + JSTL 在服务端渲染完整 HTML。
**Spring Boot**：`@RestController` 返回 JSON，前端用 Vue 的 `v-for`/`v-if` 渲染。

```java
@RestController
public class UserApiController {
    @GetMapping("/api/users")
    public List<User> list() {
        return userService.findAll();   // 返回 JSON
    }
}
```

```html
<!-- Vue 前端渲染（对应 EL + JSTL） -->
<tr v-for="(u, i) in users" :key="u.id">
    <td>{{ i + 1 }}</td>          <!-- 对应 ${vs.count} -->
    <td>{{ u.name }}</td>          <!-- 对应 ${u.name} -->
</tr>
<div v-if="users.length === 0">暂无数据</div>  <!-- 对应 <c:if> -->
```

> 💡 **原理对应**：Vue 的 `{{ u.name }}` 对应 EL 的 `${u.name}`，`v-for` 对应 `<c:forEach>`，`v-if` 对应 `<c:if>`。**本篇学的"表达式取值 + 循环判断"模式，在 Vue 里原样复现**，只是渲染从服务端挪到前端。理解了 EL/JSTL，Vue 的模板语法对你就是熟悉的。

> 💡 **选型**：服务端渲染（SEO 友好、首屏快）用 Thymeleaf；前后端分离（交互复杂、跨端）用 `@RestController` + Vue/React。**EL/JSTL 在 Spring Boot 里几乎不用**——Thymeleaf 比 JSTL 干净，JSON 模式比 JSTL 解耦。

---

> 一句话：**EL + JSTL 是"把 Java 逻辑挪出 JSP"的中间形态**。Spring Boot 里你几乎不写 EL/JSTL——页面渲染用 Thymeleaf（`${}`/`th:each`/`th:if` 对应 EL 的 `${}`/`<c:forEach>`/`<c:if>`），前后端分离用 `@RestController` + Vue（`{{}}`/`v-for`/`v-if` 对应 EL/JSTL）。但"表达式取值、循环判断、动态路径"的模板思想完全一样。理解了本篇，Thymeleaf、Vue 的模板语法对你就是透明的。**出模板不渲染、取值失败、循环不对问题时，你仍要回到 EL/JSTL 原理排查**：数据在 Model 里吗、getter 有吗、`@{}` 用了吗。

## 本章小结

本篇讲清了 EL 表达式和 JSTL：EL 用 `${}` 取值（自动走 getter、按域查找、`empty` 判空），有 11 个隐式对象（`param`/`cookie`/`pageContext` 等最常用）；JSTL 用 `<c:forEach>` 循环、`<c:if>`/`<c:choose>` 判断，替代 JSP 脚本。重点掌握 `${user.name}` 取值规则、`${pageContext.request.contextPath}` 拼路径、`<c:forEach>` 的 `varStatus`、`<c:if>` 无 else 用 `<c:choose>`。核心认知：EL/JSTL 是"脚本 JSP → Thymeleaf → 前后端分离"进化的中间一步，`${}`/`th:each`/`v-for` 一脉相承。至此阶段五的视图层基础完成，下一篇 [13-MVC 设计模式](13-MVC%20设计模式.md) 把 Servlet + JSP 的分工正式化为 MVC 模式——理解 Spring MVC 的前身。
