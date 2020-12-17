# Session

Session 服务端会话技术，将数据保存在服务器端对象中，Session 依赖 Cookie 来实现

浏览器关闭后再重新打开两次获取的 session 不同，如何需要相同，可以将 JSESSIONID 作为键，session.getId() 获取 id 作为值保存到 cookie

特点：

+ 用于存储一次会话的多次请求数据，存在服务器
+ 可以存储任意类型，任意大小的数据

HttpSession 域对象

+ `request.getSession()`：获取 HttpSession 对象
+ `Object getAttribute(String name)`：获取数据
+ `void setAttribute(String name, Object value)`：存储数据
+ `void removeAttribute(String name)`：删除数据

钝化:

+ 在服务器正常关闭前，将 Session 对象序列化到硬盘上

活化:

+ 在服务器启动后，将 Session 文件转化我i内存中的 Session 对象

销毁:

+ 服务器关闭
+ Session 对象调用 invalidate() 方法
+ Session 默认失效时间 30 分钟

Session 与 Cookie 的区别

+ Session 存储数据在服务器端，Cookie在客户端
+ Session 没有数据大小限制，Cookie有大小限制(4kb)
+ Session 数据安全，Cookie 相对于不安全

```java
@WebServlet("/session_servlet")
public class SessionDemo extends HttpServlet {
    protected void doPost(HttpServletRequest request, HttpServletResponse response) throws ServletException, IOException {
        // 获取 Session
        HttpSession session = request.getSession();

        // 存储数据
        session.setAttribute("msg", "hello session");

        // 获取数据
        Object msg = session.getAttribute("msg");
        System.out.println(msg);

        // 将 JSESSIONID 保存到 cookie 持久化保存
        Cookie jsessionid = new Cookie("JSESSIONID", session.getId());
        jsessionid.setMaxAge(60 * 60 * 24);
        response.addCookie(jsessionid);

        // Session 销毁
        //session.invalidate();
    }

    protected void doGet(HttpServletRequest request, HttpServletResponse response) throws ServletException, IOException {
        this.doPost(request, response);
    }
}
```

保存登录信息

```java
@WebServlet("/login_servlet")
public class LoginServlet extends HttpServlet {
    protected void doPost(HttpServletRequest request, HttpServletResponse response) throws ServletException, IOException {
        // 设置编码
        request.setCharacterEncoding("utf-8");

        // 获取参数
        String username = request.getParameter("username");
        String password = request.getParameter("password");
        String checkCode = request.getParameter("checkCode");

        // 获取生成的验证码
        HttpSession session = request.getSession();
        String check_code_session = (String) session.getAttribute("check_code_session");

        // 获取验证码后立马删除，只能用一次
        session.removeAttribute("check_code_session");

        // 判断验证码是否正确，忽略大小写
        if (check_code_session != null && check_code_session.equalsIgnoreCase(checkCode)) {
            // 判断用户名密码是否正确
            if ("leo".equals(username) && "123456".equals(password)) {
                // 登录成功，存储用户信息
                session.setAttribute("user", username);
                // 重定向到欢迎页
                response.sendRedirect(request.getContextPath() + "/index.jsp");
            } else {
                // 存储信息
                request.setAttribute("login_error", "用户名或密码错误");
                // 转发到登录页
                request.getRequestDispatcher("/login.jsp").forward(request, response);
            }
        } else {
            // 存储信息
            request.setAttribute("check_code_error", "验证码错误");
            // 转发到登录页
            request.getRequestDispatcher("/login.jsp").forward(request, response);
        }
    }

    protected void doGet(HttpServletRequest request, HttpServletResponse response) throws ServletException, IOException {
        this.doPost(request, response);
    }
}
```
