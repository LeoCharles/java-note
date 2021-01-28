# IOC

## 控制反转(Inversion of Control)

控制，即资源的获取方式，分为主动式和被动式

主动式：资源由自己创建(new)

被动式：资源的获取交给容器来创建和设置

控制反转，即主动的创建(new)资源，变为被动的接收资源，是一种思想。

## 依赖注入(Dependency Injection)

依赖注入是 IOC 的一种具体实现。

容器通过反射的形式，将容器中准备好的对象注入。

### 构造器注入

```xml
<bean id="person03" class="com.leocode.bean.Person">
    <!-- 构造器注入，可省略 name 属性，需按照构造器参数顺序赋值 -->
    <constructor-arg name="name" value="Lucy" />
    <constructor-arg name="age" value="25" />
    <constructor-arg name="gender" value="女" />
</bean>
```

### Set 方式注入

```xml
<bean id="person01" class="com.leocode.bean.Person" scope="prototype">
    <property name="name" value="Leo"/>
    <property name="age" value="30"/>
    <property name="gender" value="男"/>
</bean>
```

### 拓展方式注入

```xml
<!-- p 命名空间注入（通过 Set 注入），需要加入 xmlns:p="http://www.springframework.org/schema/p" 约束 -->
<bean id="person02" class="com.leocode.bean.Person" p:name="Tom" p:age="20" p:gender="男" />

<!-- c 命名空间注入（通过构造器），需要 xmlns:c="http://www.springframework.org/schema/c" 约束 -->
<bean id="person04" class="com.leocode.bean.Person" c:name="Eva" c:age="18" c:gender="女" />

```

## 配置文件

使用 `<bean>` 标签注册组件，属性有：

+ id：唯一标识

+ class：注册的组件全类名

使用 `<bean>` 标签中的 `<property>` 标签进行赋值

+ name：指定属性名

+ value：指定属性值

+ scope：作用域，singleton（单例，默认）、prototype（原型）、request、session、application

## 使用注解配置

添加约束和支持：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<beans xmlns="http://www.springframework.org/schema/beans"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xmlns:context="http://www.springframework.org/schema/context"
    xsi:schemaLocation="http://www.springframework.org/schema/beans
        https://www.springframework.org/schema/beans/spring-beans.xsd
        http://www.springframework.org/schema/context
        https://www.springframework.org/schema/context/spring-context.xsd">

    <context:annotation-config/>

</beans>
```

### @Autowired

自动装配

+ byName：自动在容器上下文中查找和自己对象 set 方法后面的值对应的 Id

+ byType：自动在容器上下文中查找和自己对象属性类型相同的 bean
