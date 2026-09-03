# AJAX 与 JSON

前面十三篇的 Web 都是"同步"的：浏览器发请求 → 等服务器 → 服务器返回整页 HTML → 浏览器刷新整页。点个赞都要刷新整个页面，体验很差。能不能只更新页面的一小块而不刷新整页？这就是 **AJAX**。配合 **JSON** 这种轻量数据格式，前后端分离的大门就此打开。本篇讲清 AJAX 的原理、JSON 的格式与转换、跨域问题。这是 Spring Boot `@RestController` + Jackson 自动序列化 + `@CrossOrigin` 的底层。

> 💡 本篇建议用浏览器原生 `XMLHttpRequest` 写一个 AJAX 请求，F12 看 Network 面板——你会看到一次"后台请求"，页面不刷新但局部更新了。再对比 jQuery `$.ajax` 和现代 `fetch`，感受 AJAX 的进化。

---

## 一、AJAX 是什么

### 1.1 定义

**AJAX**（Asynchronous JavaScript And XML）是用 JS 在**不刷新整页**的情况下，向服务器发请求并局部更新页面的技术。虽然名字带 XML，但实际数据格式几乎都用 JSON。

```
传统同步：点链接 → 整页刷新 → 服务器返回整页 HTML
AJAX 异步：JS 后台发请求 → 服务器返回数据 → JS 局部更新 DOM，页面不刷新
```

> 💡 **AJAX 的核心价值**：局部更新。点赞只更新点赞数、搜索联想只更新下拉框、表单校验只提示错误——不用刷新整页。**这是现代 Web 体验的基础**，没有 AJAX 就没有 Web 2.0。

> 💡 **名字带 XML 但用 JSON**：早期（2005 年）用 XML 传数据，但 XML 啰嗦（`<user><name>张三</name></user>`），JSON 更轻（`{"name":"张三"}`）。所以 AJAX 的 X 已是历史，实际用 JSON。

### 1.2 XMLHttpRequest（XHR）

AJAX 的底层是浏览器的 `XMLHttpRequest` 对象（XHR）：

```javascript
// 原生 AJAX（理解原理用这个）
var xhr = new XMLHttpRequest();
xhr.open("GET", "/api/user?id=1", true);   // true = 异步
xhr.onreadystatechange = function() {
    if (xhr.readyState === 4 && xhr.status === 200) {
        // 请求完成且成功
        var data = JSON.parse(xhr.responseText);   // 解析 JSON
        document.getElementById("name").innerText = data.name;  // 局部更新
    }
};
xhr.send();
```

| readyState | 含义 |
| :--- | :--- |
| 0 | 未初始化（open 未调） |
| 1 | 已 open，未 send |
| 2 | 已 send，收到响应头 |
| 3 | 响应体接收中 |
| 4 | **响应完成**（最终判断） |

> 💡 **readyState 4 + status 200 是成功标志**：4 表示响应接收完，200 表示成功。这是原生 AJAX 判断成功的标准写法。现代用 `fetch` + Promise 更简洁，但底层还是这套机制。

### 1.3 同步 vs 异步

```javascript
xhr.open("GET", "/api/user", true);   // 第三个参数 true = 异步
```

- **异步（true，默认）**：`xhr.send()` 不阻塞，JS 继续执行，响应到了回调 `onreadystatechange`。
- **同步（false）**：`xhr.send()` 阻塞，直到响应返回 JS 才继续——**已废弃**，会卡死浏览器。

> ⚠️ **同步 AJAX 已废弃**：主线程上的同步请求会冻结 UI，用户体验极差。现代浏览器对主线程同步 XHR 直接警告。**永远用异步**。

---

## 二、JSON 数据格式 ⭐

### 2.1 什么是 JSON

**JSON**（JavaScript Object Notation）是轻量级数据交换格式，用键值对和数组表示数据。

```json
{
    "id": 1,
    "name": "张三",
    "age": 20,
    "hobbies": ["读书", "编程"],
    "address": { "city": "北京", "zip": "100000" },
    "active": true,
    "score": null
}
```

| JSON 类型 | 示例 | Java 对应 |
| :--- | :--- | :--- |
| 对象 | `{"name":"张三"}` | `Map`/对象 |
| 数组 | `[1, 2, 3]` | `List`/数组 |
| 字符串 | `"hello"`（必须双引号） | `String` |
| 数字 | `123` / `3.14` | `int`/`double` |
| 布尔 | `true`/`false` | `boolean` |
| null | `null` | `null` |

> ⚠️ **JSON 字符串必须用双引号**：`"name":"张三"` 合法，`'name':'张三'`（单引号）非法。这是 JSON 和 JS 对象字面量的关键区别——JS 允许单引号，JSON 严格双引号。

> 💡 **JSON 是前后端的通用语言**：后端 Java 对象 → 序列化 → JSON 字符串 → 网络 → 前端 JS `JSON.parse` → JS 对象。**JSON 是前后端分离时代的"数据桥梁"**。

### 2.2 Java 与 JSON 互转

Java 后端把对象转 JSON（序列化）、JSON 转对象（反序列化），用 Jackson 或 Fastjson：

```java
// Jackson（Spring Boot 默认）
ObjectMapper mapper = new ObjectMapper();

// 对象 → JSON 字符串（序列化）
User user = new User(1, "张三", 20);
String json = mapper.writeValueAsString(user);
// {"id":1,"name":"张三","age":20}

// JSON 字符串 → 对象（反序列化）
String json = "{\"id\":1,\"name\":\"张三\",\"age\":20}";
User u = mapper.readValue(json, User.class);

// 集合
List<User> list = mapper.readValue(jsonArray, new TypeReference<List<User>>(){});
```

> 💡 **Jackson 是 Spring Boot 默认的 JSON 库**：`@ResponseBody`/`@RequestBody` 底层就是 Jackson。Fastjson（阿里）国内也常用，但近年因安全漏洞减少使用。**Spring Boot 默认 Jackson，不用额外引入**。

### 2.3 JSON 与 JavaBean 的映射规则

```java
public class User {
    private Integer id;
    private String name;
    private Integer age;
    // getter/setter 省略
}
```

```json
{"id":1, "name":"张三", "age":20}
```

| 规则 | 说明 |
| :--- | :--- |
| 字段名对应 | JSON 的 `name` 对应 Java 的 `name` 字段（走 getter/setter） |
| 类型转换 | JSON 数字 → int/Integer，字符串 → String，自动 |
| 忽略字段 | `@JsonIgnore` 标注的字段不序列化 |
| 日期格式 | `@JsonFormat(pattern="yyyy-MM-dd")` |
| 别名 | `@JsonProperty("user_name")` 映射下划线命名 |

> 💡 **驼峰 vs 下划线**：Java 用驼峰（`userName`），数据库/前端常用下划线（`user_name`）。Jackson 默认按字段名序列化，要映射下划线用 `@JsonProperty("user_name")` 或全局配 `spring.jackson.property-naming-strategy=SNAKE_CASE`。

---

## 三、AJAX 实战

### 3.1 原生 AJAX：GET 请求

```javascript
function loadUser(id) {
    var xhr = new XMLHttpRequest();
    xhr.open("GET", "/api/user?id=" + id, true);
    xhr.onreadystatechange = function() {
        if (xhr.readyState === 4) {
            if (xhr.status === 200) {
                var user = JSON.parse(xhr.responseText);
                document.getElementById("name").innerText = user.name;
            } else {
                alert("请求失败：" + xhr.status);
            }
        }
    };
    xhr.send();
}
```

### 3.2 原生 AJAX：POST JSON

```javascript
function saveUser() {
    var user = { name: "张三", age: 20 };
    var xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/user", true);
    xhr.setRequestHeader("Content-Type", "application/json");   // ★ 告诉服务器发的是 JSON
    xhr.onreadystatechange = function() {
        if (xhr.readyState === 4 && xhr.status === 200) {
            alert("保存成功");
        }
    };
    xhr.send(JSON.stringify(user));   // ★ JS 对象转 JSON 字符串发送
}
```

> ⚠️ **POST JSON 必须设 `Content-Type: application/json`**：不设，服务器不知道请求体是 JSON，`@RequestBody` 解析失败（415）。这是前后端分离最常见的坑。

### 3.3 jQuery AJAX（简化版）

原生 XHR 太啰嗦，jQuery 封装了 `$.ajax`：

```javascript
$.ajax({
    url: "/api/user",
    type: "POST",
    contentType: "application/json",
    data: JSON.stringify({ name: "张三", age: 20 }),
    success: function(data) { console.log(data); },
    error: function(xhr, status, err) { console.error(err); }
});

// 更简洁的 $.get / $.post
$.get("/api/user?id=1", function(data) { console.log(data); });
```

### 3.4 现代 fetch（推荐）

现代开发用 `fetch` + Promise + async/await：

```javascript
// GET
async function getUser(id) {
    let resp = await fetch("/api/user?id=" + id);
    if (resp.ok) {
        let user = await resp.json();
        console.log(user.name);
    }
}

// POST JSON
async function saveUser() {
    let resp = await fetch("/api/user", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: "张三", age: 20 })
    });
    let result = await resp.json();
    console.log(result);
}
```

> 💡 **fetch 是现代标准**：Promise 链式调用、async/await 同步写法，比 XHR 清晰。但底层还是 AJAX 机制（异步请求、局部更新）。**理解了原生 XHR，fetch 就是语法糖**。

---

## 四、跨域与 CORS ⭐

### 4.1 同源策略

浏览器有**同源策略**：JS 默认只能发同源请求（协议+域名+端口都相同）。不同源的 AJAX 请求会被浏览器拦截。

```
http://localhost:8080  →  http://localhost:8081/api   ❌ 端口不同，跨域
http://a.com           →  http://b.com/api             ❌ 域名不同，跨域
http://a.com           →  https://a.com/api            ❌ 协议不同，跨域
```

> ⚠️ **跨域是浏览器行为，不是服务器**：服务器能收到请求并响应，但浏览器检查响应头发现不允许跨域，就拦截响应。**跨域问题只在浏览器 AJAX 出现**——Postman/curl 不受同源策略限制。

### 4.2 CORS 解决跨域

**CORS**（Cross-Origin Resource Sharing）是标准跨域方案：服务器在响应头声明"允许哪些源访问"，浏览器看到允许就放行。

```
// 服务器响应头
Access-Control-Allow-Origin: http://localhost:8081   // 允许的源
Access-Control-Allow-Methods: GET, POST, PUT, DELETE  // 允许的方法
Access-Control-Allow-Headers: Content-Type, Authorization  // 允许的头
```

**原生 Servlet 实现 CORS**：

```java
@WebServlet("/api/user")
public class UserServlet extends HttpServlet {
    protected void doGet(HttpServletRequest req, HttpServletResponse resp) throws IOException {
        // ★ 设 CORS 响应头
        resp.setHeader("Access-Control-Allow-Origin", "http://localhost:8081");
        resp.setHeader("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE");
        resp.setHeader("Access-Control-Allow-Headers", "Content-Type, Authorization");

        resp.setContentType("application/json;charset=utf-8");
        resp.getWriter().write("{\"name\":\"张三\"}");
    }
}
```

> 💡 **CORS 的本质是响应头**：服务器主动声明"我允许 XX 源访问"，浏览器看到这个声明就放行。**跨域问题的根因是浏览器同源策略，解法是服务器响应头声明**。理解了这点，Spring Boot 的 `@CrossOrigin` 就不神秘。

### 4.3 预检请求（OPTIONS）

非简单请求（如 POST JSON、带自定义头）浏览器会先发一个 **OPTIONS 预检请求**，问服务器"我能不能发这个请求"：

```
1. 浏览器 → OPTIONS /api/user（预检）
2. 服务器 → 响应 CORS 头（允许）
3. 浏览器 → POST /api/user（真实请求）
4. 服务器 → 响应数据
```

> 💡 **预检是自动的**：浏览器判断请求是"非简单"就自动发 OPTIONS，你不用手写。但服务器要处理 OPTIONS 请求（返回 CORS 头）。Spring Boot 的 `@CrossOrigin` 自动处理预检。

### 4.4 JSONP（历史方案）

CORS 之前用 **JSONP**（JSON with Padding）绕过同源策略——利用 `<script>` 标签不受同源限制的特性：

```javascript
// 前端动态创建 script 标签
var script = document.createElement("script");
script.src = "http://b.com/api?callback=handleData";
document.body.appendChild(script);

// 服务器返回：handleData({"name":"张三"})  —— 把 JSON 包在回调里
function handleData(data) { console.log(data); }
```

> ⚠️ **JSONP 已过时**：只支持 GET、不安全、难调试。CORS 是现代标准，Spring Boot 用 `@CrossOrigin` 一行搞定。**JSONP 了解原理即可，新项目用 CORS**。

---

## ⚠️ 重点

1. **AJAX = 异步请求 + 局部更新**：不刷新整页，用 XHR/fetch 后台请求。
2. **JSON 是前后端数据桥梁**：双引号、键值对、轻量，Java 用 Jackson 序列化。
3. **`readyState===4 && status===200` 是成功标志**：原生 XHR 的判断。
4. **POST JSON 必须设 `Content-Type: application/json`**：否则服务器解析失败（415）。
5. **Jackson 是 Spring Boot 默认 JSON 库**：`@ResponseBody`/`@RequestBody` 底层是它。
6. **跨域是浏览器同源策略**：服务器能收到请求，浏览器拦截响应。
7. **CORS 用响应头解决跨域**：`Access-Control-Allow-Origin` 等头声明允许源。
8. **非简单请求触发 OPTIONS 预检**：浏览器自动发，服务器要处理。
9. **JSONP 已过时**：用 `<script>` 绕过同源，只支持 GET，已被 CORS 取代。

---

## 💻 实战案例：搜索联想（AJAX + JSON）

需求：输入框输入时，AJAX 请求后端，返回匹配的用户列表，局部更新下拉框。

**后端 Servlet（返回 JSON）**：

```java
@WebServlet("/api/search")
public class SearchServlet extends HttpServlet {
    protected void doGet(HttpServletRequest req, HttpServletResponse resp) throws IOException {
        // CORS（前端在不同端口）
        resp.setHeader("Access-Control-Allow-Origin", "*");

        String keyword = req.getParameter("keyword");
        // 模拟搜索
        List<User> users = Arrays.asList(
            new User(1, "张三", 20),
            new User(2, "张伟", 22),
            new User(3, "李四", 21)
        ).stream()
         .filter(u -> u.getName().contains(keyword == null ? "" : keyword))
         .collect(Collectors.toList());

        // 序列化为 JSON 返回
        resp.setContentType("application/json;charset=utf-8");
        ObjectMapper mapper = new ObjectMapper();
        resp.getWriter().write(mapper.writeValueAsString(users));
    }
}
```

**前端（fetch + 局部更新）**：

```html
<input type="text" id="keyword" onkeyup="search()" placeholder="输入姓名">
<ul id="result"></ul>

<script>
async function search() {
    var keyword = document.getElementById("keyword").value;
    if (!keyword) { document.getElementById("result").innerHTML = ""; return; }
    let resp = await fetch("/api/search?keyword=" + encodeURIComponent(keyword));
    let users = await resp.json();
    var html = users.map(u => `<li>${u.name} (${u.age})</li>`).join("");
    document.getElementById("result").innerHTML = html;   // 局部更新
}
</script>
```

> 💡 **这就是前后端分离的雏形**：后端返回 JSON（不渲染 HTML），前端 AJAX 取数据局部渲染。**本篇的 Servlet 返回 JSON，就是 Spring Boot `@RestController` 的前身**——`@RestController` 把"序列化 JSON + 写响应体"自动化了。

---

## 🚀 新版本补充

- **fetch API**：现代浏览器原生，Promise 化，替代 XHR。`async/await` 让异步代码像同步。
- **CORS 标准**：W3C 标准，所有现代浏览器支持，JSONP 已淘汰。
- **HTTP/2**：多路复用，一个连接并发多请求，AJAX 性能更好。
- **WebSocket**：全双工通信，替代 AJAX 轮询（16 篇讲）。

---

## 📌 在 Spring Boot 中

> 本篇讲的 AJAX、JSON 序列化、CORS 跨域，在 Spring Boot 中由 `@RestController` + Jackson + `@CrossOrigin` 全自动接管。下面逐一对照，给出实际开发代码，以及"出问题怎么回到 AJAX/JSON 原理排查"。实际开发你不用手动 `writeValueAsString`、不用手动设 CORS 头——Spring Boot 一个注解搞定，但理解了本篇，返回 JSON、跨域报错、415/400 问题时才知道怎么查。

### 1. 返回 JSON：从"手动 Jackson + getWriter"到"@ResponseBody 自动序列化"

**原生**：本篇实战用 `ObjectMapper.writeValueAsString` + `resp.getWriter().write` 手动序列化。
**Spring Boot**：`@RestController` 返回对象，Jackson 自动序列化。

```java
@RestController   // 返回值自动序列化为 JSON
@RequestMapping("/api/users")
public class UserApiController {

    @Autowired
    private UserService userService;

    @GetMapping
    public List<User> list() {
        return userService.list();   // List<User> → JSON 数组，自动完成
        // 底层：Jackson writeValueAsString → Content-Type: application/json → getWriter().write
    }

    @GetMapping("/{id}")
    public User get(@PathVariable Long id) {
        return userService.get(id);   // User → JSON 对象，自动完成
    }
}
```

> 💡 **原理对应**：`@RestController` = `@Controller` + `@ResponseBody`。`@ResponseBody` 底层就是本篇的 `ObjectMapper.writeValueAsString` + `getWriter().write`——把返回值用 Jackson 序列化成 JSON 写进响应体。**你本篇手动拼的 JSON 代码，Spring Boot 一个注解搞定**，且自动设 `Content-Type: application/json`。

> 💡 **原理排查**：返回的 JSON 字段名不对？检查 `@JsonProperty`/`@JsonIgnore`、`spring.jackson.property-naming-strategy`。返回 null 字段被过滤？检查 `@JsonInclude`。日期格式不对？检查 `@JsonFormat` 或全局 `spring.jackson.date-format`。回到 JSON 原理：序列化由 Jackson 配置决定。

### 2. 接收 JSON：从"getReader + readValue"到"@RequestBody 自动反序列化"

**原生**：本篇 3.2 前端 POST JSON，后端用 `req.getReader()` 读流 + `ObjectMapper.readValue` 反序列化。
**Spring Boot**：`@RequestBody` 自动反序列化。

```java
@PostMapping
public User create(@RequestBody User user) {   // JSON → User，自动完成
    // 底层：getReader() 读流 → Jackson readValue → User 对象
    userService.add(user);
    return user;   // 返回时再序列化为 JSON
}

@PostMapping("/batch")
public List<User> batch(@RequestBody List<User> users) {  // JSON 数组 → List
    userService.addAll(users);
    return users;
}
```

> 💡 **原理对应**：`@RequestBody` 底层就是本篇的 `getReader()` + `ObjectMapper.readValue()`。**本篇强调的"请求体只能读一次"（04 篇），`@RequestBody` 同样适用**——只能用一次，Filter 先读了 body，Controller 的 `@RequestBody` 就拿不到。

> 💡 **原理排查**：报 415 Unsupported Media Type？前端 `Content-Type` 不是 `application/json`（本篇 3.2 强调过）。报 400 Bad Request？JSON 字段名和实体类对不上、类型转换失败（age 传了字符串）。回到 JSON 原理：`Content-Type` 决定解析方式，字段映射决定能否反序列化。

### 3. CORS 跨域：从"手动设响应头"到"@CrossOrigin / 全局配置"

**原生**：本篇 4.2 手动 `resp.setHeader("Access-Control-Allow-Origin", "*")`。
**Spring Boot**：`@CrossOrigin` 注解或全局配置。

```java
// 方法级 CORS
@RestController
@RequestMapping("/api/users")
@CrossOrigin(origins = "http://localhost:8081")   // 允许前端源
public class UserApiController { ... }

// 或全局配置（推荐，统一管理）
@Configuration
public class CorsConfig implements WebMvcConfigurer {
    @Override
    public void addCorsMappings(CorsRegistry registry) {
        registry.addMapping("/api/**")
                .allowedOrigins("http://localhost:8081")
                .allowedMethods("GET", "POST", "PUT", "DELETE")
                .allowedHeaders("*")
                .allowCredentials(true);   // 允许带 Cookie
    }
}
```

> 💡 **原理对应**：`@CrossOrigin` 底层就是本篇的 `Access-Control-Allow-Origin` 等响应头——Spring MVC 在响应时自动加 CORS 头。**本篇手动设的 CORS 头，Spring Boot 用注解/配置统一管理**，且自动处理 OPTIONS 预检请求。

> 💡 **原理排查**：跨域报 "CORS policy: No 'Access-Control-Allow-Origin'"？检查 `@CrossOrigin` 的 `origins` 是否匹配前端源、是否配了 `allowCredentials(true)` 时 origins 用了 `*`（带 Cookie 时不能用 `*`，要具体源）。回到 CORS 原理：浏览器看响应头判断是否放行。

### 4. AJAX 前端：从"原生 XHR"到"fetch / axios"

**原生**：本篇 3.1 用 `XMLHttpRequest` + `onreadystatechange`。
**现代**：前端用 `fetch` 或 `axios`（Vue/React 生态常用）。

```javascript
// fetch（浏览器原生）
const resp = await fetch("/api/users");
const users = await resp.json();

// axios（第三方库，Vue/React 常用）
const { data } = await axios.get("/api/users");
```

> 💡 **原理对应**：`fetch`/`axios` 底层还是 XHR（或 fetch API），本质都是 AJAX——异步请求、局部更新。**本篇学的 AJAX 机制（异步、回调、JSON 解析）是所有现代前端请求库的基础**。后端（Spring Boot）不关心前端用 XHR 还是 axios，它只管收请求返回 JSON。

### 5. JSON 序列化配置：从"手动 ObjectMapper"到"全局 yml 配置"

**原生**：手动 `new ObjectMapper()`，每个 Servlet 配一遍。
**Spring Boot**：`application.yml` 全局配置 Jackson。

```yaml
spring:
  jackson:
    date-format: yyyy-MM-dd HH:mm:ss   # 日期格式
    time-zone: GMT+8                    # 时区
    default-property-inclusion: non_null  # 不序列化 null 字段
    property-naming-strategy: SNAKE_CASE  # 驼峰转下划线
```

> 💡 **原理对应**：`spring.jackson.*` 底层配置全局唯一的 `ObjectMapper`。**本篇手动配的 Jackson 选项，Spring Boot 用 yml 全局生效**，所有 `@ResponseBody`/`@RequestBody` 都用这个配置。

> 💡 **原理排查**：全局 Jackson 配置不生效？检查 yml 缩进、`spring.jackson` 前缀、是否有自定义 `ObjectMapper` Bean 覆盖了默认配置。回到 JSON 原理：序列化行为由 `ObjectMapper` 配置决定。

---

> 一句话：**AJAX + JSON 是前后端分离的基石**。Spring Boot 里你不用手动序列化 JSON、不用手动设 CORS 头——`@RestController`/`@ResponseBody` 自动序列化，`@RequestBody` 自动反序列化，`@CrossOrigin` 自动处理跨域，`spring.jackson.*` 全局配置。但底层还是本篇的 Jackson + 响应头 + AJAX 机制。理解了本篇，返回 JSON、跨域报错、415/400 问题对你就是透明的。**出 JSON 字段不对、跨域被拦、415/400 问题时，你仍要回到本篇原理排查**：`Content-Type` 对吗、CORS 头配了吗、Jackson 配置对吗、字段映射对吗。

## 本章小结

本篇讲清了 AJAX 和 JSON：AJAX 用 XHR/fetch 异步请求、局部更新页面（不刷新整页）；JSON 是轻量数据格式（双引号、键值对），Java 用 Jackson 序列化/反序列化；跨域由浏览器同源策略引起，用 CORS 响应头解决。重点掌握 `readyState===4 && status===200` 成功判断、POST JSON 必须设 `Content-Type: application/json`、Jackson 是 Spring Boot 默认 JSON 库、CORS 的 `Access-Control-Allow-Origin` 头、OPTIONS 预检、JSONP 已过时。核心认知：**AJAX + JSON 是前后端分离的底层，Spring Boot 的 `@RestController`/`@RequestBody`/`@CrossOrigin` 是它的自动化**。下一篇 [15-文件上传下载](15-文件上传下载.md) 讲 multipart 文件上传与 `MultipartFile` 的底层。
