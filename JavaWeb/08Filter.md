# Filter

概念：一般用于完成通用的操作，如：登录验证、统一编码处理、敏感字符过滤等

## 使用步骤

1. 定义一个类，实现 Filter 接口
2. 复写方法 doFilter
3. 配置拦截路径
4. 设置过滤条件后，调用 filterChain.doFilter() 方法放行

## 配置拦截路径方式

使用 web.xml 配置:

```xml
    <filter>
        <filter-name>demo1</filter-name>
        <filter-class>web.filter.FilterDemo</filter-class>
    </filter>
    <filter-mapping>
        <filter-name>demo1</filter-name>
        <url-pattern>/*</url-pattern>
    </filter-mapping>
```

使用注解配置： `@WebFilter("/*")`

## 配置拦截路径

1. 具体资源路径：/index.jsp
2. 拦截目录：/user/*  访问 /user 下的所有资源时过滤器都会被执行
3. 后缀名拦截：*.jsp 访问所有的 jsp 文件都会被拦截
4. 拦截所有资源： /*  访问所有资源时，都会被拦截

## 拦截方式配置

使用注解设置 dispatcherTypes 属性

+ REQUEST：浏览器直接访问时触发过滤器，默认
+ FORWARD：转发访问时触发过滤器
+ INCLUDE：包含访问资源
+ ERROR：错误跳转资源
+ ASYNC：异步访问
