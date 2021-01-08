# Spring 快速入门

Spring 是以 `IoC(控制反转)` 和 `AOP(面向切面编程)`为核心的容器框架。

## Spring 特点

1. 非侵入式：基于 Spring 开发的应用中的对象可以不依赖于 Spring 的 API

2. 依赖注入(Dependency Injection)：控制反转(IoC) 的经典实现

3. 面向切面编程：AOP

4. 容器：Spring 是一个容器，它包含并管理应用对象的生命周期

5. 组件化：Spring 可以使用 XML 和注解配置组合应用对象

6. 一站式：在 IoC 和 AOP 的基础上可以整合各种企业应用的开源框架

## Spring 框架模块结构

![spring](../Image/spring-overview.png)

+ Test: Spring 的单元测试模块

+ Core Container：核心容器(IoC)
  + Beans：spring-beans
  + Core：spring-core
  + Context：spring-context
  + SpEL：spring-expression，表达式语言

+ AOP + Aspects：面向切面编程模块

+ Data Access / Integration：数据访问 / 集成
  + JDBC：spring-jdbc，操作数据库
  + ORM：spring-orm，对象关系映射
  + OXM：spring-ox，对象XML映射
  + JMS：spring-jms，消息服务
  + Transactions：spring-tx，事务

+ Web：Wrb 应用模块
  + Websocket：spring-websocket
  + Servlet：spring-web，和原生 web 相关
  + Web：spring-webmvc，开发 web 项目
  + Portlet：spring-webmvc-portlet，开发 web 项目的组件集成

需要用到那个模块就导入相应的 jar 包
