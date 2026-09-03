# MVC 设计模式

前几篇你看到了一个清晰的分工：Servlet 取参数、调业务（Controller 的活），JSP 从域取数据渲染页面（View 的活），JavaBean 承载数据（Model 的活）。这种"三分工"就是 **MVC**。本篇讲清 MVC 的思想、JSP Model1 与 Model2 的区别、MVC 在 JavaWeb 中的落地，以及它如何演化为分层架构。这是 Spring MVC 的直接前身——`@Controller`/`@Service`/`@Repository` 就是 MVC 三层在 Spring 里的注解化。

> 💡 本篇建议把 11/12 篇的用户列表案例，按本篇的 MVC 结构重写一遍：`UserServlet`（Controller）→ `UserService`（业务）→ `User`（Model）→ `userList.jsp`（View）。亲手体验"一个请求被三层各司其职处理"的清晰感。

---

## 一、为什么需要 MVC

### 1.1 没有 MVC 时的混乱

早期 JSP 开发（Model1 模式）把所有代码塞进 JSP：

```jsp
<%-- Model1：JSP 干所有事（反面教材） --%>
<%@ page import="java.sql.*" %>
<%
    // 1. 取参数（Controller 的活）
    String name = request.getParameter("name");
    // 2. 连数据库查（Model + 业务 的活）
    Class.forName("com.mysql.cj.jdbc.Driver");
    Connection conn = DriverManager.getConnection("jdbc:mysql:///test", "root", "123456");
    PreparedStatement ps = conn.prepareStatement("SELECT * FROM user WHERE name=?");
    ps.setString(1, name);
    ResultSet rs = ps.executeQuery();
    // 3. 渲染 HTML（View 的活）
    while (rs.next()) {
        out.println("<tr><td>" + rs.getString("name") + "</td></tr>");
    }
    conn.close();
%>
```

**痛点**：
- JSP 里写满 Java + SQL + HTML，**职责混杂**，改一个地方要翻整个页面
- 前端开发者看不懂（满屏 Java），后端要管页面
- 无法复用：查用户的逻辑在 A 页面写一遍，B 页面要再写一遍
- 难测试：业务逻辑嵌在 JSP 里，没法单元测试

> ⚠️ **这就是 12 篇说的"SQL 标签库废弃"的原因**：JSP 里写 SQL 是 Model1 的极端，严重违反 MVC。理解了这个痛点，就理解了 MVC 为何而生。

### 1.2 MVC 的核心思想

**MVC**（Model-View-Controller）把应用分成三部分，各司其职：

```
        请求
         ↓
   ┌──────────┐
   │ Controller│  控制器：接收请求、调业务、选视图（调度员）
   └────┬─────┘
        │ 调用
        ↓
   ┌──────────┐
   │   Model   │  模型：业务逻辑 + 数据（核心）
   └────┬─────┘
        │ 返回数据
        ↓
   ┌──────────┐
   │   View    │  视图：渲染页面（只展示）
   └──────────┘
```

| 角色 | 职责 | JavaWeb 对应 | Spring MVC 对应 |
| :--- | :--- | :--- | :--- |
| **Model** | 业务逻辑 + 数据 | JavaBean/Service/DAO | `@Service`/`@Repository`/Entity |
| **View** | 渲染页面 | JSP/Thymeleaf | Thymeleaf/JSON |
| **Controller** | 接请求、调业务、选视图 | Servlet | `@Controller` |

> 💡 **MVC 的本质是"关注点分离"**：谁干什么，分得清清楚楚。Controller 不碰数据库，View 不写业务，Model 不管页面。**改业务不影响页面，改页面不影响业务**——这就是可维护性的来源。

> 💡 **Controller 是"瘦"的**：Controller 只做三件事——取参数、调 Service、选视图。业务逻辑全在 Model（Service）里。**Controller 胖了就是反模式**（Fat Controller），和 Model1 一样难维护。

---

## 二、Model1 与 Model2 ⭐

### 2.1 Model1：JSP 干所有事

```
请求 → JSP（取参 + 业务 + 渲染）→ 响应
```

JSP 既当 Controller 又当 Model 又当 View，全部塞一起。前面 1.1 的代码就是 Model1。

> ⚠️ **Model1 的局限**：无法维护、无法复用、无法测试。**只适合极小的 demo**，稍大一点就失控。

### 2.2 Model2：MVC 的落地 ⭐

```
请求 → Servlet（Controller）→ Service（Model 业务）→ DAO（Model 数据）
                              ↓ 返回数据
                          Servlet 存进 request 域
                              ↓ 转发
                          JSP（View）渲染 → 响应
```

| 阶段 | 角色 | 做什么 |
| :--- | :--- | :--- |
| 1 | Controller（Servlet） | 取参数、调 Service、存数据、转发 |
| 2 | Model（Service + DAO + Bean） | 业务逻辑、数据库访问、数据承载 |
| 3 | View（JSP） | 从 request 域取数据、渲染 HTML |

> 💡 **Model2 就是 MVC 在 JavaWeb 的标准落地**：Servlet 做 Controller，JavaBean/Service 做 Model，JSP 做 View。**本系列前 12 篇其实一直在为 Model2 铺路**——Request 取参（04）、forward 转发（04）、request 域传值（10）、JSP 渲染（11）、EL/JSTL（12），全是 Model2 的零件。

---

## 三、MVC 实战：用户增删改查

需求：按 MVC 结构实现用户列表查询，体会三层分工。

### 3.1 Model 层

**Entity（数据承载）**：

```java
public class User {
    private Integer id;
    private String name;
    private Integer age;
    // 构造、getter/setter 省略
}
```

**DAO（数据访问）**：

```java
public class UserDao {
    public List<User> findAll() {
        // JDBC 查询（17/18 篇讲连接池和 DBUtils 简化）
        List<User> list = new ArrayList<>();
        // 伪代码：SELECT * FROM user → 填充 list
        return list;
    }
}
```

**Service（业务逻辑）**：

```java
public class UserService {
    private UserDao dao = new UserDao();

    public List<User> listUsers() {
        // 业务逻辑（如过滤、排序、权限判断）
        return dao.findAll();
    }
}
```

> 💡 **Model 分两层：Service 和 DAO**。Service 是业务（"做什么"），DAO 是数据访问（"怎么存"）。**分开的好处**：换数据库（MySQL→Oracle）只改 DAO，业务不变；换业务规则只改 Service，数据访问不变。这就是分层架构的雏形。

### 3.2 Controller 层

```java
@WebServlet("/user/list")
public class UserListServlet extends HttpServlet {
    private UserService service = new UserService();   // Controller 调 Model

    protected void doGet(HttpServletRequest req, HttpServletResponse resp)
            throws ServletException, IOException {
        // 1. 取参数（本例无参数）
        // 2. 调 Model 业务
        List<User> users = service.listUsers();
        // 3. 存进 request 域（给 View 用）
        req.setAttribute("users", users);
        // 4. 选视图并转发
        req.getRequestDispatcher("/userList.jsp").forward(req, resp);
    }
}
```

> 💡 **Controller 只做这四步**：取参 → 调业务 → 存数据 → 转发。**没有业务逻辑、没有 SQL、没有 HTML**——这就是"瘦 Controller"。Spring MVC 的 `@Controller` 方法也是这个骨架，只是注解化了。

### 3.3 View 层

```jsp
<%@ page contentType="text/html;charset=UTF-8" %>
<%@ taglib uri="http://java.sun.com/jsp/jstl/core" prefix="c" %>
<html><body>
    <table border="1">
        <c:forEach items="${users}" var="u">
            <tr><td>${u.id}</td><td>${u.name}</td><td>${u.age}</td></tr>
        </c:forEach>
    </table>
</body></html>
```

> 💡 **View 只渲染**：从 request 埢取 `${users}`，`<c:forEach>` 循环输出。**没有 Java 逻辑、没有 SQL**——纯展示。这就是 MVC 的 View 层。

### 3.4 三层调用链

```
浏览器 ──/user/list──▶ UserListServlet（Controller）
                          │ 调用
                          ▼
                       UserService（Service 业务）
                          │ 调用
                          ▼
                       UserDao（DAO 数据访问）
                          │ JDBC
                          ▼
                        MySQL
                          │ 返回 List<User>
                          ▼
                       UserService ← UserDao
                          │ 返回
                          ▼
                       UserListServlet ← UserService
                          │ 存 request 域，转发
                          ▼
                       userList.jsp（View 渲染）
                          │
                          ▼
                        浏览器
```

> 💡 **这就是 MVC 的完整调用链**：Controller 调 Service，Service 调 DAO，DAO 查数据库，数据原路返回，Controller 存进域转发给 View 渲染。**每一层只和相邻层打交道**，职责清晰。Spring MVC 的 `@Controller` → `@Service` → `@Repository` 完全是这个结构的注解化。

---

## 四、从 MVC 到分层架构 ⭐

### 4.1 三层架构

MVC 演化出更通用的**三层架构**（Layered Architecture）：

| 层 | 职责 | JavaWeb 对应 | Spring 对应 |
| :--- | :--- | :--- | :--- |
| **表现层（Web）** | 接请求、返回响应 | Servlet + JSP | `@Controller` + View |
| **业务层（Service）** | 业务逻辑 | Service | `@Service` |
| **持久层（DAO）** | 数据库访问 | DAO + JDBC | `@Repository` + MyBatis/JPA |

> 💡 **MVC vs 三层架构**：MVC 是表现层内部的分工（Controller/View/Model-View），三层架构是整个应用的分层。**MVC 的 Model 在三层架构里拆成 Service（业务层）和 DAO（持久层）**，View 和 Controller 都属于表现层。两者不矛盾，是不同粒度的划分。

### 4.2 分层的价值

```
改数据库（MySQL→Oracle）   → 只动 DAO 层
改业务规则（加权限校验）   → 只动 Service 层
换前端（JSP→Vue）          → 只动 Controller + View
```

> 💡 **分层的本质是"隔离变化"**：每一层封装一种变化原因，改一处不影响其他层。这是软件设计的核心原则——**单一职责**和**依赖方向稳定**（上层依赖下层，下层不依赖上层）。Spring 的 `@Controller`/`@Service`/`@Repository` 注解就是这三层的显式标记。

> ⚠️ **不要跨层调用**：Controller 不能直接调 DAO（绕过 Service），否则业务逻辑散落、Service 形同虚设。**严格按 Controller→Service→DAO 单向依赖**，这是分层架构的纪律。

---

## 五、MVC 的演化方向

### 5.1 前后端分离：View 挪到前端

传统 MVC：Controller 选 View（JSP），服务端渲染 HTML。
前后端分离：Controller 只返回 JSON（数据），View 交给前端（Vue/React）。

```
传统 MVC：    请求 → Controller → JSP 渲染 → HTML 响应
前后端分离：  请求 → @RestController → JSON 响应 → 前端 Vue 渲染
```

> 💡 **前后端分离是 MVC 的进化**：View 从服务端挪到前端，Controller 从"选视图"变成"返回数据"。**MVC 的"关注点分离"思想没变**，只是 View 的位置变了。Spring 的 `@RestController` = `@Controller` + `@ResponseBody`，`@ResponseBody` 让返回值变 JSON 而非视图名。

### 5.2 RESTful：Controller 的规范化

MVC 的 Controller 路径设计早期很随意（`/userList`、`/deleteUser`）。RESTful 用 HTTP 方法 + 资源路径规范：

| 操作 | 早期写法 | RESTful |
| :--- | :--- | :--- |
| 列表 | `/userList` | `GET /users` |
| 详情 | `/userDetail?id=1` | `GET /users/1` |
| 新增 | `/addUser` | `POST /users` |
| 修改 | `/updateUser` | `PUT /users/1` |
| 删除 | `/deleteUser?id=1` | `DELETE /users/1` |

> 💡 **RESTful 是 MVC + HTTP 语义的结合**：用 HTTP 方法（GET/POST/PUT/DELETE）表达 CRUD，用路径表达资源。Spring MVC 的 `@GetMapping`/`@PostMapping`/`@PutMapping`/`@DeleteMapping` 就是 RESTful 的注解化（03 篇讲过）。

---

## ⚠️ 重点

1. **MVC = Model（业务+数据）+ View（渲染）+ Controller（调度）**，核心是关注点分离。
2. **Model1（JSP 干所有事）是反面教材**，Model2（Servlet+JSP+Bean）是 MVC 的落地。
3. **Controller 是瘦的**：只做取参→调业务→存数据→转发，不写业务/SQL/HTML。
4. **Model 分 Service（业务）和 DAO（数据）两层**：换数据库改 DAO，换业务改 Service。
5. **View 只渲染**：从域取数据展示，不写 Java 逻辑、不碰数据库。
6. **MVC 演化为三层架构**：表现层（Controller+View）/业务层（Service）/持久层（DAO）。
7. **不要跨层调用**：Controller→Service→DAO 单向依赖，不跨层。
8. **前后端分离是 MVC 进化**：View 挪到前端，Controller 返回 JSON。
9. **RESTful 规范化 Controller**：HTTP 方法 + 资源路径，Spring 的 `@XxxMapping` 是其注解化。

---

## 💻 实战案例：MVC 用户管理（增删改查）

需求：按 MVC + 三层架构实现用户 CRUD，体会完整分层。

**Model 层**：

```java
// Entity
public class User {
    private Integer id;
    private String name;
    private Integer age;
    public User() {}
    public User(Integer id, String name, Integer age) { this.id=id; this.name=name; this.age=age; }
    // getter/setter 省略
}

// DAO
public class UserDao {
    public List<User> findAll() { /* SELECT * FROM user */ return new ArrayList<>(); }
    public User findById(int id) { /* SELECT * FROM user WHERE id=? */ return null; }
    public void save(User u) { /* INSERT */ }
    public void update(User u) { /* UPDATE */ }
    public void delete(int id) { /* DELETE */ }
}

// Service（业务逻辑，如校验）
public class UserService {
    private UserDao dao = new UserDao();
    public List<User> list() { return dao.findAll(); }
    public User get(int id) { return dao.findById(id); }
    public void add(User u) {
        if (u.getName() == null || u.getName().trim().isEmpty()) {
            throw new RuntimeException("用户名不能为空");   // 业务校验
        }
        dao.save(u);
    }
    public void update(User u) { dao.update(u); }
    public void remove(int id) { dao.delete(id); }
}
```

**Controller 层**：

```java
@WebServlet("/user/*")   // /user/list, /user/add, /user/delete 等
public class UserController extends HttpServlet {
    private UserService service = new UserService();

    protected void doGet(HttpServletRequest req, HttpServletResponse resp)
            throws ServletException, IOException {
        String action = req.getPathInfo();   // /list, /detail
        if ("/list".equals(action)) {
            req.setAttribute("users", service.list());
            req.getRequestDispatcher("/userList.jsp").forward(req, resp);
        } else if ("/detail".equals(action)) {
            int id = Integer.parseInt(req.getParameter("id"));
            req.setAttribute("user", service.get(id));
            req.getRequestDispatcher("/userDetail.jsp").forward(req, resp);
        } else if ("/delete".equals(action)) {
            int id = Integer.parseInt(req.getParameter("id"));
            service.remove(id);
            resp.sendRedirect(req.getContextPath() + "/user/list");  // PRG
        }
    }

    protected void doPost(HttpServletRequest req, HttpServletResponse resp)
            throws ServletException, IOException {
        req.setCharacterEncoding("utf-8");
        String action = req.getPathInfo();
        if ("/add".equals(action)) {
            User u = new User();
            u.setName(req.getParameter("name"));
            u.setAge(Integer.parseInt(req.getParameter("age")));
            service.add(u);
            resp.sendRedirect(req.getContextPath() + "/user/list");  // PRG 模式
        }
    }
}
```

> 💡 **一个 Controller 管一个资源的所有操作**：`/user/*` 用 `getPathInfo()` 区分 list/detail/add/delete。这是"一个 Controller 管一个资源"的雏形，Spring MVC 的 `@RestController` + `@RequestMapping("/users")` 是它的注解化。

> 💡 **PRG 模式**：POST 新增后 `sendRedirect` 到 GET 列表（05 篇讲过），防止刷新重复提交。这是 MVC Controller 的标准写法。

**View 层（userList.jsp）**：

```jsp
<%@ page contentType="text/html;charset=UTF-8" %>
<%@ taglib uri="http://java.sun.com/jsp/jstl/core" prefix="c" %>
<html><body>
    <a href="${pageContext.request.contextPath}/user/add.jsp">新增</a>
    <table border="1">
        <tr><th>ID</th><th>姓名</th><th>年龄</th><th>操作</th></tr>
        <c:forEach items="${users}" var="u">
            <tr>
                <td>${u.id}</td>
                <td>${u.name}</td>
                <td>${u.age}</td>
                <td>
                    <a href="${pageContext.request.contextPath}/user/detail?id=${u.id}">详情</a>
                    <a href="${pageContext.request.contextPath}/user/delete?id=${u.id}">删除</a>
                </td>
            </tr>
        </c:forEach>
    </table>
</body></html>
```

> 💡 **完整 MVC 链路**：Controller（`UserController`）取参调业务、Service（`UserService`）做业务校验、DAO（`UserDao`）访问数据、View（JSP）渲染。**每一层只和相邻层打交道，职责清晰**。做完这个案例，你会强烈感受到"手动 new Service、手动转发、手写 JSP"的繁琐——这正是 Spring Boot 要解决的痛点。

---

## 🚀 新版本补充

- **前端 MVC**：MVC 思想从前端走到后端又走回前端——Vue/React 也有组件内 MVC（Model 是数据、View 是模板、Controller 是事件处理）。
- **MVVM**：Vue 是 MVVM（Model-View-ViewModel），`v-model` 双向绑定替代 Controller 手动同步——比 MVC 更进一步。
- **Spring MVC 的进化**：从 XML 配置 → 注解驱动（`@Controller`）→ Spring Boot 自动配置，MVC 思想不变，工程效率倍增。

---

## 📌 在 Spring Boot 中

> 本篇讲的 MVC 三层、Model1/Model2、分层架构、Controller 瘦身，在 Spring Boot 中由 `@Controller`/`@Service`/`@Repository` 注解化，并由 IoC 容器自动管理依赖。下面逐一对照，给出实际开发代码，以及"出问题怎么回到 MVC 原理排查"。实际开发你不再手动 new Service、不再写 JSP——Spring 注解 + Thymeleaf/JSON 接管，但 MVC 的三层分工、依赖方向、瘦 Controller 原则完全不变。

### 1. 三层注解：从"手动 new"到"@Controller/@Service/@Repository"

**原生**：本篇 3.1 手动 `new UserService()`、`new UserDao()`，Controller 持有 Service 引用。
**Spring Boot**：三层用注解标记，IoC 容器自动创建并注入依赖。

```java
@Controller   // 表现层（等价本篇的 Servlet）
public class UserController {
    @Autowired
    private UserService userService;   // Spring 自动注入，不用 new
}

@Service      // 业务层
public class UserService {
    @Autowired
    private UserDao userDao;   // 自动注入 DAO
    public List<User> list() { return userDao.findAll(); }
}

@Repository   // 持久层
public class UserDao {
    public List<User> findAll() { /* JDBC/MyBatis */ }
}
```

> 💡 **原理对应**：`@Controller`/`@Service`/`@Repository` 就是本篇 MVC 三层的注解标记——Controller（表现层）、Service（业务层）、DAO（持久层）。**本篇手动 new 的依赖关系，Spring 用 `@Autowired` 自动注入**，这就是 IoC（控制反转）——对象的创建和依赖由容器管，业务代码只声明"我要什么"。理解了本篇的 MVC 分层，Spring 的三层注解就是它的注解化。

> 💡 **原理排查**：`@Autowired` 注入失败（NoSuchBeanDefinitionException）？检查目标类是否有 `@Service`/`@Repository`、是否在扫描包下、接口是否有实现类。回到 MVC 原理：Service 要先被容器创建（标记为 Bean），Controller 才能注入它。

### 2. Controller：从"HttpServlet + getPathInfo"到"@Controller + @RequestMapping"

**原生**：本篇实战用 `HttpServlet` + `req.getPathInfo()` 手动分发 `/user/list`、`/user/add`。
**Spring Boot**：`@Controller` + `@RequestMapping`/`@GetMapping` 注解映射。

```java
@Controller
@RequestMapping("/users")   // 等价本篇 /user/*
public class UserController {

    @Autowired
    private UserService userService;

    @GetMapping     // GET /users（列表，对应本篇 /user/list）
    public String list(Model model) {
        model.addAttribute("users", userService.list());  // 等价 setAttribute
        return "userList";                                   // 等价 forward 到 JSP
    }

    @GetMapping("/{id}")   // GET /users/1（详情，RESTful）
    public String detail(@PathVariable Long id, Model model) {
        model.addAttribute("user", userService.get(id));
        return "userDetail";
    }

    @PostMapping     // POST /users（新增）
    public String add(User user) {   // 表单自动绑定到 User 对象
        userService.add(user);
        return "redirect:/users";    // PRG 模式（等价 sendRedirect）
    }

    @DeleteMapping("/{id}")   // DELETE /users/1（删除，RESTful）
    public String delete(@PathVariable Long id) {
        userService.remove(id);
        return "redirect:/users";
    }
}
```

> 💡 **原理对应**：本篇的 `getPathInfo()` 手动分发，Spring MVC 用 `@RequestMapping`/`@GetMapping`/`@PostMapping` 自动映射——URL + HTTP 方法直接对应方法。**本篇的"取参→调业务→存数据→转发"四步，Spring 用注解 + Model + 返回视图名全部封装**。`@PathVariable` 取路径参数（04 篇讲过），`Model.addAttribute` 存 request 域（10 篇讲过），`return "userList"` 转发到模板（11 篇讲过）。

> 💡 **原理排查**：Controller 方法不触发？检查 `@RequestMapping` 路径、`@GetMapping` vs `@PostMapping` 是否匹配请求方法、类是否在扫描包下。回到 MVC 原理：Controller 要被映射到 URL 才能接请求。

### 3. 瘦 Controller 原则：从"手动校验"到"Service + 校验注解"

**原生**：本篇 Service 里手动 `if (name == null) throw`。
**Spring Boot**：用 Bean Validation 注解声明校验，Controller 瘦身。

```java
// Entity 加校验注解
public class User {
    @NotBlank(message = "用户名不能为空")   // 等价本篇的 if 判空
    private String name;
    @Min(0) @Max(150)
    private Integer age;
}

// Controller 用 @Valid 触发校验
@PostMapping
public String add(@Valid User user, BindingResult result) {
    if (result.hasErrors()) {
        return "userForm";   // 校验失败回表单页
    }
    userService.add(user);
    return "redirect:/users";
}
```

> 💡 **原理对应**：本篇 Service 里的业务校验（`if name == null`），Spring 用 `@NotBlank`/`@Min` 注解声明 + `@Valid` 触发。**Controller 仍是瘦的**——只声明"我要什么校验"，校验逻辑由框架执行。这就是 MVC"关注点分离"在校验上的体现。

### 4. 前后端分离：从"Controller + JSP"到"@RestController + JSON"

**原生**：本篇 Controller 选 JSP 视图，服务端渲染。
**Spring Boot**：`@RestController` 返回 JSON，前端渲染。

```java
@RestController   // = @Controller + @ResponseBody，返回 JSON 不选视图
@RequestMapping("/api/users")
public class UserApiController {

    @Autowired
    private UserService userService;

    @GetMapping
    public List<User> list() {
        return userService.list();   // 自动序列化为 JSON
    }

    @GetMapping("/{id}")
    public User get(@PathVariable Long id) {
        return userService.get(id);   // 返回单个对象 JSON
    }

    @PostMapping
    public User create(@RequestBody User user) {   // @RequestBody 接收 JSON
        userService.add(user);
        return user;
    }
}
```

> 💡 **原理对应**：`@RestController` 让 Controller 从"选视图渲染"变成"返回数据"。**本篇 MVC 的 View（JSP）挪到前端**，Controller 只负责 Model（数据）。三层分工没变，只是 View 的位置变了——这是 MVC 的进化，不是否定。

> 💡 **选型**：传统 Web 应用（有页面、SEO）用 `@Controller` + Thymeleaf；前后端分离（交互复杂、跨端）用 `@RestController` + Vue/React。**两者都是 MVC，只是 View 的实现不同**。

### 5. 分层架构：从"手动分层"到"Spring 模块化"

**原生**：本篇手动建 Controller/Service/DAO 三层，手动 new 依赖。
**Spring Boot**：用注解 + 包结构 + IoC 容器规范化分层。

```
com.example.demo/
├── controller/    @Controller      表现层
├── service/        @Service         业务层
├── repository/     @Repository      持久层
├── entity/         @Entity          数据模型
└── config/         @Configuration  配置
```

> 💡 **原理对应**：Spring 的包结构 + 注解就是本篇三层架构的规范化——`controller` 包放 `@Controller`，`service` 包放 `@Service`，`repository` 包放 `@Repository`。**本篇讲的"Controller→Service→DAO 单向依赖、不跨层"，Spring 用注解 + 包结构显式表达**。理解了本篇的分层，Spring 的工程结构对你就是顺理成章。

> 💡 **原理排查**：循环依赖报错（`BeanCurrentlyInCreationException`）？通常是分层违反了单向依赖——Service 依赖 Controller、或相互依赖。回到 MVC 原理：严格单向依赖（Controller→Service→DAO），下层不引用上层。

---

> 一句话：**MVC 是"关注点分离"的设计模式，三层架构是它的工程化**。Spring Boot 里你不再手动 new Service、不再写 JSP——`@Controller`/`@Service`/`@Repository` 注解标记三层，`@Autowired` 自动注入依赖，`@RestController` 返回 JSON 实现前后端分离。但 MVC 的核心不变：Controller 瘦（只调度）、Model 分业务和数据、View 只渲染、单向依赖不跨层。理解了本篇，Spring MVC 的注解、分层、依赖注入对你就是"本篇手写版的自动化"。**出 Bean 注入失败、Controller 不触发、职责混乱问题时，你仍要回到 MVC 原理排查**：三层标记了吗、依赖方向对吗、Controller 胖了吗。

## 本章小结

本篇讲清了 MVC：Model（业务+数据）、View（渲染）、Controller（调度）三分工，核心是关注点分离。重点掌握 Model1（JSP 干所有事，反面教材）vs Model2（Servlet+JSP+Bean，MVC 落地）、Controller 瘦身四步（取参→调业务→存数据→转发）、Model 分 Service/DAO 两层、三层架构（表现/业务/持久）、单向依赖不跨层、前后端分离是 MVC 进化、RESTful 规范化 Controller。核心认知：**Spring MVC 就是 MVC 的工程化**，`@Controller`/`@Service`/`@Repository` 是三层的注解化，`@Autowired` 替代手动 new。至此阶段五完成，你已理解 Spring MVC 的前身。下一篇 [14-AJAX 与 JSON](14-AJAX%20与%20JSON.md) 进入阶段六，讲前后端分离的关键技术——AJAX 异步交互与 JSON 数据格式。
