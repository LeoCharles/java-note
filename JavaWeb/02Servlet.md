# Servlet

Servlet 是运行在服务器端的小程序

Servlet 就是一个接口，定义了Java 类被浏览器访问到的规则

## 配置 Servlet

1. 创建 JavaEE 项目

2. 定义一个类，实现 Servlet 接口

    `public class ServletDemo1 implements Servlet`

3. 实现接口中的抽象方法

4. 在 web.xml 中的 `<web-app>` 配置 Servlet

```xml
  <web-app>
      <!-- 配置 servlet -->
      <servlet>
          <servlet-name>demo1</servlet-name>
          <servlet-class>web.servlet.ServletDemo1</servlet-class>
      </servlet>

      <!-- 配置 servlet 映射 -->
      <servlet-mapping>
          <servlet-name>demo1</servlet-name>
          <url-pattern>/demo1</url-pattern>
      </servlet-mapping>
  </web-app>
```

Servlet3.0 以上的版本 ，支持注解配置，可以不创建 web.xml

在实现类上使用 `@WebServlet("资源路径")` 注解，进行配置

```java
@WebServlet("/demo2")
public class ServletDemo implements Servlet {

  // 初始化方法，只会执行一次
  @Override
  public void init(ServletConfig servletConfig) throws ServletException {
      System.out.println("服务器初始化...");
  }

  @Override
  public ServletConfig getServletConfig() {
      return null;
  }

  // 提供服务的方法
  @Override
  public void service(ServletRequest servletRequest, ServletResponse servletResponse) throws ServletException, IOException {
      System.out.println("服务器被访问了...");
  }

  @Override
  public String getServletInfo() {
      return null;
  }

  // 销毁之前执行
  @Override
  public void destroy() {
      System.out.println("服务器关闭了...");
  }
}
```

## 执行原理

1. 当服务器接收到客户端浏览器的请求后，会解析请求 URL 路径，获取访问的 Servlet 的资源路径

2. 查找 web.xml 文件，是否有对应的 `<url-pattern>` 标签体内容。

3. 如果有，则在找到对应的 `<servlet-class>` 全类名

4. tomcat 会将字节码文件加载进内存，并且创建其对象

5. 调用其方法

## 生命周期

1. init：被创建时只执行一次

2. service: 每次访问 Servlet 时，都会被调用一次

3. destroy：在 Servlet 被销毁之前执行，一般用于释放资源

## Servlet 体系结构

`Servlet`(接口) --> `GenericServlet`(抽象类)  --> `HttpServlet`(抽象类)

+ `GenericServlet`：将 Servlet 接口中其他的方法做了默认空实现，只将 service 方法作为抽象

+ `HttpServlet`：对 http 协议的一种封装，简化操作

```java
@WebServlet("/demo3")
public class HttpServletDemo extends HttpServlet {

    @Override
    protected void doGet(HttpServletRequest req, HttpServletResponse resp) throws ServletException, IOException {
        System.out.println("doGet...");
    }

    @Override
    protected void doPost(HttpServletRequest req, HttpServletResponse resp) throws ServletException, IOException {
        System.out.println("doPost...");
    }
}
```
