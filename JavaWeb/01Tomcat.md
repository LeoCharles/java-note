# Tomcat

开源的 Web 服务器软件

## Tomcat 安装与启动

1. 下载：http://tomcat.apache.org/

2. 安装：解压压缩包即可

3. 删除：删除目录即可

4. 启动：`bin\startup.bat`, 双击运行该文件

5. 关闭:
    + `bin\shutdown.bat`, 双击运行该文件
    + `ctrl+c`

## Tomcat 配置

1. 直接将项目放到 `/webapps` 目录下即可

2. 将项目打成一个 war 包，再将 war 包放置到 `/webapps` 目录下，war 包会自动解压缩

3. 配置 `conf\server.xml` 文件，在`<Host>` 标签体中配置 `<Context docBase="D:\hello" path="/hello" />`
    + docBase: 项目存放的路径
    + path：虚拟目录

4. 在 `conf\Catalina\localhost` 创建任意名称的 xml 文件，在文件中编写 `<Context docBase="D:\hello" />`
    + docBase: 项目存放的路径
    + xml 文件的名称就是虚拟目录
