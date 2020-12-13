# Request

## Request 对象继承体系

`ServletRequest`(接口) -->  `HttpServletRequest`(接口) --> `RequestFacade`(Tomcat 实现类)

## 获取请求行数据

+ `getMethod()`：请求方法

+ `getContextPath()`：获取虚拟目录

+ `getServletPath()`：获取 Servlet 路径

+ `getQueryString()`：获取 GET 请求参数

+ `getRequestURI()`：获取请求的 URI

+ `getRequestURL()`：获取请求的 URL

+ `getProtocol()`：获取协议和版本

+ `getRemoteAddr()`：获取客户机 IP

```java
@WebServlet("/request_demo")
public class RequestDemo extends HttpServlet {
  protected void doPost(HttpServletRequest request, HttpServletResponse response) throws ServletException, IOException {
    // 统一在 doGet 中处理，不需要单独在 doPost 获取请求体数据
    this.doGet(request, response);
  }

  protected void doGet(HttpServletRequest request, HttpServletResponse response) throws ServletException, IOException {
    // 获取请求方式
    String method = request.getMethod();

    // 获取虚拟目录
    String contextPath = request.getContextPath();

    // 获取 Servlet 路径
    String servletPath = request.getServletPath();

    // 获取 GET 请求参数
    String queryString = request.getQueryString();

    // 获取请求的 URI
    String requestURI = request.getRequestURI();

    // 获取请求的 URL
    StringBuffer requestURL = request.getRequestURL();

    // 获取协议和版本
    String protocol = request.getProtocol();

    // 获取客户机 IP
    String remoteAddr = request.getRemoteAddr();
  }
}
```

## 获取请求头数据

+ `getHeaderNames()`：获取所有的请求头名称，返回一个枚举

+ `getHeader()`：通过请求头的名称，获取值

```java
@WebServlet("/request_demo")
public class RequestDemo extends HttpServlet {
  protected void doPost(HttpServletRequest request, HttpServletResponse response) throws ServletException, IOException {
    // 统一在 doGet 中处理，不需要单独在 doPost 获取请求体数据
    this.doGet(request, response);
  }

  protected void doGet(HttpServletRequest request, HttpServletResponse response) throws ServletException, IOException {
    // 获取所有请求头名称
    Enumeration<String> headerNames = request.getHeaderNames();
    // 遍历所有的请求头名称
    while (headerNames.hasMoreElements()) {
      String name = headerNames.nextElement();

      // 根据请求头名称获取值
      String header = request.getHeader(name);
      System.out.println(name + ":" + header);
    }
  }
}
```

## 获取请求体数据

先获取流对象，再从流对象中获取数据

+ `getReader()`: 获取字符输入流，只能操作字符数据

+ `getInputStream()`: 获取字节输入流，可以操作所有类型数据，用于文件上传等

```java
@WebServlet("/request_demo")
public class RequestDemo extends HttpServlet {
  protected void doPost(HttpServletRequest request, HttpServletResponse response) throws ServletException, IOException {
    // 获取字符流
    BufferedReader br = request.getReader();
    // 读取字符流数据
    String line = null;
    while ((line = br.readLine()) != null) {
        System.out.println(line);
    }
  }

  protected void doGet(HttpServletRequest request, HttpServletResponse response) throws ServletException, IOException {
    this.doPost(request, response);
  }
}
```

## 获取请求参数的通用方法

GET 和 POST 都可以使用

在获取参数前设置编码： `request.setCharacterEncoding("utf-8");`

+ `getParameter()`: 根据参数名获取参数值

+ `getParameterValues()`: 根据参数名获取参数值数组

+ `getParameterNames()`: 根据所有的参数名，返回一个枚举

+ `getParameterMap()`: 获取所有参数的 Map 集合

```java
@WebServlet("/request_demo")
public class RequestDemo extends HttpServlet {
  protected void doPost(HttpServletRequest request, HttpServletResponse response) throws ServletException, IOException {
    // 统一在 doGet 中处理，不需要单独在 doPost 获取请求体数据
    this.doGet(request, response);
  }

  protected void doGet(HttpServletRequest request, HttpServletResponse response) throws ServletException, IOException {
    // 设置流的编码，防止中文乱码
    request.setCharacterEncoding("utf-8");

    // 获取所有请求头名称
    Enumeration<String> headerNames = request.getHeaderNames();
    // 遍历所有的请求头名称
    while (headerNames.hasMoreElements()) {
      String name = headerNames.nextElement();

      // 根据请求头名称获取值
      String header = request.getHeader(name);
      System.out.println(name + ":" + header);
    }

    // 根据请求参数名获取值
    String password = request.getParameter("password");
    System.out.println("password:" + password);

    // 根据参数名获取参数值的数组
    String[] hobbies = request.getParameterValues("hobby");
    if (hobbies != null) {
      for (String hobby : hobbies) {
          System.out.println(hobby);
      }
    }

    // 获取所有请求参数
    Enumeration<String> parameterNames = request.getParameterNames();
    while (parameterNames.hasMoreElements()) {
        String name = parameterNames.nextElement();
        String value = request.getParameter(name);
        System.out.println(name + ":" + value);
    }

    // 获取所有参数的 Map 集合
    Map<String, String[]> parameterMap = request.getParameterMap();
    Set<String> keySet = parameterMap.keySet();
    for (String key : keySet) {
        String[] values = parameterMap.get(key);
        for (String value : values) {
            System.out.println(key + ":" + value);
        }
    }
  }
}
```

## 数据共享和请求转发

request 域：一次请求的范围，一般用于请求转发的多个资源中共享数据

+ `setAttribute()`: 存储数据

+ `getAttitude()`: 通过键获取值

+ `removeAttribute()`: 通过键移除键值对

请求转发：只能转发到当前服务器内部资源中；浏览器访问路径不变；转发是一次请求

+ `getRequestDispatcher()`：通过 request 对象获取获取转发器对象

+ `forward()`: 转发器对象调用该方法进行转发

```java
@WebServlet("/request_demo")
public class RequestDemo extends HttpServlet {
  protected void doPost(HttpServletRequest request, HttpServletResponse response) throws ServletException, IOException {
    // 统一在 doGet 中处理，不需要单独在 doPost 获取请求体数据
    this.doGet(request, response);
  }

  protected void doGet(HttpServletRequest request, HttpServletResponse response) throws ServletException, IOException {
    // 共享数据，可以在转发之前存储数据到 request 域中
    request.setAttribute("msg", "hello");

    /*
    // 在转发后的 /request_demo2 Servlet 中获取数据
    Object msg = request.getAttribute("msg");
    */

    // 请求转发，先获取转发器对象，再调用 forward() 方法转发
    // 转发到 /request_demo2 的 servlet 中
    request.getRequestDispatcher("/request_demo2").forward(request, response);
  }
}
```

## ServletContext 对象

ServletContext 是一个域对象，代表整个 Web 应用，可以和服务器通信

ServletContext 对象可以获取 MIME 类型；共享数据；获取文件的真实路径

+ `request.getServletContext()`: 获取 ServletContext 对象

+ `this.getServletContext()`: 直接从 HttpServlet 获取 ServletContext 对象

```java
@WebServlet("/request_demo")
public class RequestDemo extends HttpServlet {
  protected void doPost(HttpServletRequest request, HttpServletResponse response) throws ServletException, IOException {
    // 统一在 doGet 中处理，不需要单独在 doPost 获取请求体数据
    this.doGet(request, response);
  }

  protected void doGet(HttpServletRequest request, HttpServletResponse response) throws ServletException, IOException {
    // 获取 ServletContext，可以和服务器通信
    ServletContext servletContext = request.getServletContext();
  }
}
```
