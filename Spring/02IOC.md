# IOC

## 控制反转(Inversion of Control)

控制，即资源的获取方式，分为主动式和被动式

主动式：资源由自己创建(new)

被动式：资源的获取交给容器来创建和设置

控制反转，即主动的创建(new)资源，变为被动的接收资源，是一种思想。

## 依赖注入(Dependency Injection)

依赖注入是 IOC 的一种具体实现。

容器通过反射的形式，将容器中准备好的对象注入。

## 开发步骤

1. 导入 Maven 坐标

2. 创建 Bean

3. 创建配置文件 `applicationContext.xml` (文件名可自定义)

4. 在配置文件中进行配置

5. 创建 `ApplicationContext` 对象，调用 `getBean()` 方法

6. 测试

## 配置文件

使用 `<bean>` 标签注册组件，属性有：

+ id：唯一标识

+ class：注册的组件全类名

使用 `<bean>` 标签中的 `<property>` 标签进行赋值

+ name：指定属性名

+ value：指定属性值