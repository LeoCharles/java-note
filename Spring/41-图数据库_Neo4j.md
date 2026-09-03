# 41 - 图数据库 Neo4j

> 对应项目模块：`demo-neo4j`
> 前置知识：已学完关系型数据库（JPA/MyBatis）相关模块，了解 ORM 基本概念
> 学习目标：理解图数据库与关系型数据库的本质区别，掌握 Spring Data Neo4j 的节点/关系建模、Repository 派生查询与 Cypher 自定义查询，能看懂并改写本模块的校园关系网示例。

---

## 一、本模块要解决什么问题？

前面学的 JdbcTemplate、JPA、MyBatis 操作的都是**关系型数据库**（MySQL 等），它们用"表 + 外键 + JOIN"来表达数据间的关联。但有一类问题，关系型数据库处理起来非常吃力——**多跳的关系查询**。

举个例子：在一个校园系统里，你想查"漩涡鸣人和宇智波佐助因为一起上了哪些课而成为同学"，用关系型数据库要这样写：

```sql
-- 学生表、选课表（中间表）、课程表，三层 JOIN
SELECT s2.name
FROM student s1
JOIN student_lesson sl1 ON s1.id = sl1.student_id
JOIN lesson l ON sl1.lesson_id = l.id
JOIN student_lesson sl2 ON l.id = sl2.lesson_id
JOIN student s2 ON sl2.student_id = s2.id
WHERE s1.name = '漩涡鸣人' AND s2.id <> s1.id
```

如果再追问"这些同学各自的班主任是谁、班主任还教了哪些课、那些课又有哪些学生"——关系型数据库的 JOIN 层数会爆炸式增长，查询性能急剧下降，SQL 也变得难以维护。

**图数据库就是为这类"关系密集型"查询而生的。** 它把数据存成"节点（Node）+ 关系（Relationship）"，关系是"一等公民"——不用 JOIN，沿着关系遍历即可，多跳查询性能稳定。

> 💡 前端类比：关系型数据库像把数据存成多张 Excel 表，靠外键关联；图数据库像把数据存成一张**节点关系图**（类似前端的可视化知识图谱、D3.js 力导向图），节点之间用带方向的边直接连起来。查询"谁和谁有关系"就是顺着边走，不用拼表。

本模块用 **Neo4j**（最流行的图数据库）实现一个校园人物关系网，涵盖：

- 4 种节点：学生 Student、教师 Teacher、课程 Lesson、班级 Class
- 4 种关系：学生-班级、班级-班主任、课程-教师、学生-选课
- 派生查询（按方法名自动生成）、Cypher 自定义查询、深度查询、事务

---

## 二、先搞懂 Neo4j 与 Cypher 的核心概念

在写代码前，必须先建立图数据库的心智模型，否则后面的注解和查询语句会看不懂。

### 2.1 节点（Node）、关系（Relationship）、属性（Property）、标签（Label）

| 概念 | 说明 | 本模块例子 | 前端类比 |
| --- | --- | --- | --- |
| **节点 Node** | 实体，图里的一个点 | 学生"漩涡鸣人" | 类比对象的一个实例 |
| **标签 Label** | 节点的类型/分类 | `Student`、`Teacher` | 类比 JS 的 class/构造函数名 |
| **关系 Relationship** | 节点之间的有向连接 | 学生-选课->课程 | 类比对象间的引用字段 |
| **关系类型** | 关系的分类 | `R_LESSON_OF_STUDENT` | 类比外键的语义命名 |
| **属性 Property** | 节点或关系上的键值对 | 学生有 `name` 属性 | 类比对象的字段 |

关键区别：**关系在图数据库里是独立存储的一等公民**，有方向、可以有属性。而关系型数据库的"关系"靠外键字段+JOIN 临时计算，不是独立存储的。

### 2.2 Cypher 查询语言

Neo4j 用类 SQL 的声明式查询语言 **Cypher**。它的核心语法是"模式匹配"——用括号表示节点、箭头表示关系：

```cypher
-- 创建一个学生节点
CREATE (s:Student {name: '漩涡鸣人'})

-- 创建学生选课的关系
MATCH (s:Student {name: '漩涡鸣人'}), (l:Lesson {name: '体术'})
CREATE (s)-[:R_LESSON_OF_STUDENT]->(l)

-- 查询鸣人选了哪些课：顺着 R_LESSON_OF_STUDENT 关系走一跳
MATCH (s:Student {name: '漩涡鸣人'})-[:R_LESSON_OF_STUDENT]->(l:Lesson)
RETURN l

-- 查询鸣人的同学：鸣人-选课->课程<-选课-另一个学生
MATCH (s:Student {name: '漩涡鸣人'})-[:R_LESSON_OF_STUDENT]->(l:Lesson)<-[:R_LESSON_OF_STUDENT]-(classmate:Student)
RETURN DISTINCT classmate
```

读懂 Cypher 的关键符号：

| 符号 | 含义 |
| --- | --- |
| `(n:Label)` | 一个带 Label 标签的节点，绑定到变量 n |
| `{name:'x'}` | 节点的属性匹配 |
| `-[r:REL_TYPE]->` | 一条有向关系，类型 REL_TYPE，绑定到 r |
| `<-[:REL]-` | 反向关系 |
| `MATCH ... RETURN` | 匹配模式，返回结果 |
| `WITH ...` | 类似 SQL 的子查询管道，把上一步结果传给下一步 |
| `collect(x)` | 聚合函数，把多个值收成列表（类似 JS 的 reduce 成数组） |
| `count(x)` | 计数 |

> 💡 前端类比：Cypher 的 `(node)-[:REL]->(node)` 模式匹配，很像正则表达式——你画出一个"形状"，Neo4j 去图里找匹配这个形状的所有子图。`WITH` 则像管道操作符 `|`，把上一步的结果流给下一步处理。

---

## 三、项目结构

```
demo-neo4j/
├── pom.xml
└── src/main/java/com/xkcoding/neo4j/
    ├── SpringBootDemoNeo4jApplication.java   # 启动类
    ├── config/
    │   └── CustomIdStrategy.java             # 自定义主键生成策略
    ├── constants/
    │   └── NeoConsts.java                    # 关系类型常量
    ├── model/                                # 节点实体
    │   ├── Student.java                      # 学生节点
    │   ├── Teacher.java                      # 教师节点
    │   ├── Lesson.java                       # 课程节点
    │   └── Class.java                         # 班级节点
    ├── payload/                              # 查询结果投影
    │   ├── ClassmateInfoGroupByLesson.java
    │   └── TeacherStudent.java
    └── repository/                           # Repository 接口
        ├── StudentRepository.java
        ├── TeacherRepository.java
        ├── LessonRepository.java
        └── ClassRepository.java
```

注意：本模块**没有 Controller**，所有操作通过测试类 `Neo4jTest` 触发。这是因为图数据库常用于后台分析、关系挖掘，不一定直接对外提供 HTTP 接口。

---

## 四、逐行拆解 pom.xml

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-data-neo4j</artifactId>
</dependency>
```

`spring-boot-starter-data-neo4j` 是 Spring Boot 为 Neo4j 提供的起步依赖，它传递引入：

- `spring-data-neo4j`：Spring Data Neo4j（类似 Spring Data JPA，提供 Repository 抽象）
- `neo4j-ogm`：Neo4j Object-Graph Mapping，把图节点映射成 Java 对象（类似 JPA 的 ORM）
- `neo4j-java-driver`：通过 Bolt 协议连接 Neo4j 服务端的驱动

其他依赖（web、test、lombok、hutool、guava）前面模块都见过，不再赘述。

---

## 五、配置文件 application.yml

```yaml
spring:
  data:
    neo4j:
      uri: bolt://localhost
      username: neo4j
      password: admin
      open-in-view: false
```

| 配置项 | 作用 |
| --- | --- |
| `uri: bolt://localhost` | Neo4j 的连接地址，`bolt://` 是 Neo4j 的二进制协议端口（默认 7687），比 HTTP 快 |
| `username` / `password` | 登录凭证（Neo4j 初始密码是 neo4j，首次登录会要求改密码，这里改成 admin） |
| `open-in-view: false` | 是否在视图层开启 Session 延迟加载，和 JPA 的 `spring.jpa.open-in-view` 一个道理 |

> 💡 前端类比：`bolt://localhost` 就像 `ws://localhost`，是一个协议+地址。Neo4j 有两个端口：7474 是 HTTP 管理后台（浏览器访问），7687 是 Bolt 协议端口（程序连接用）。

---

## 六、节点实体建模（核心）

图数据库建模和关系型数据库建模思路完全不同。关系型是"先建表，再用外键关联"；图数据库是"直接在实体类上声明关系"。

### 6.1 教师节点 Teacher.java（最简单，先看它）

```java
@Data
@NoArgsConstructor
@RequiredArgsConstructor(staticName = "of")
@AllArgsConstructor
@Builder
@NodeEntity
public class Teacher {
    @Id
    @GeneratedValue(strategy = CustomIdStrategy.class)
    private String id;

    @NonNull
    private String name;
}
```

- `@NodeEntity`：标记这是一个**图节点**实体（类似 JPA 的 `@Entity` 标记表）。Neo4j OGM 会把它映射成一个带 `Teacher` 标签的节点。
- `@Id` + `@GeneratedValue(strategy = CustomIdStrategy.class)`：主键，用自定义策略生成（见下节）。
- `@NonNull` + Lombok 的 `@RequiredArgsConstructor(staticName = "of")`：`name` 是必填字段，Lombok 生成一个静态工厂方法 `Teacher.of("迈特凯")`，方便构造。
- `@Builder`：生成链式构造器 `Teacher.builder().name("x").build()`。

### 6.2 自定义主键策略 CustomIdStrategy.java

```java
public class CustomIdStrategy implements IdStrategy {
    @Override
    public Object generateId(Object o) {
        return IdUtil.fastUUID();
    }
}
```

Neo4j 节点默认可以用自增 ID，但本模块用 UUID 作为业务主键。实现 `IdStrategy` 接口，在 `generateId` 里用 Hutool 生成 UUID。这样 `@GeneratedValue(strategy = CustomIdStrategy.class)` 就会用这个策略生成主键。

> 💡 为什么不用 Neo4j 自带的内部 ID？因为 Neo4j 的内部 ID 是节点存储位置的偏移量，**节点删除后 ID 可能被复用**，作为业务主键不安全。用 UUID 更稳定。

### 6.3 课程节点 Lesson.java（带关系）

```java
@NodeEntity
public class Lesson {
    @Id
    @GeneratedValue(strategy = CustomIdStrategy.class)
    private String id;

    @NonNull
    private String name;

    @Relationship(NeoConsts.R_TEACHER_OF_LESSON)
    @NonNull
    private Teacher teacher;
}
```

新增了 `@Relationship` 注解——这是图数据库建模的核心：

- `@Relationship(R_TEACHER_OF_LESSON)` 表示 Lesson 节点和 Teacher 节点之间有一条类型为 `R_TEACHER_OF_LESSON` 的有向关系。
- 保存这个 Lesson 时，Neo4j OGM 会自动创建 Lesson 节点、Teacher 节点，以及它们之间的有向边。

### 6.4 学生节点 Student.java（多重关系）

```java
@NodeEntity
public class Student {
    @Id
    @GeneratedValue(strategy = CustomIdStrategy.class)
    private String id;

    @NonNull
    private String name;

    @Relationship(NeoConsts.R_LESSON_OF_STUDENT)
    @NonNull
    private List<Lesson> lessons;       // 一个学生选多门课（一对多）

    @Relationship(NeoConsts.R_STUDENT_OF_CLASS)
    @NonNull
    private Class clazz;                 // 一个学生属于一个班级（多对一）
}
```

一个学生有两条关系：选了多门课（List）、属于一个班级。`List<Lesson>` 表示一对多关系，`Class` 表示多对一关系。

### 6.5 班级节点 Class.java

```java
@NodeEntity
public class Class {
    @Id
    @GeneratedValue(strategy = CustomIdStrategy.class)
    private String id;

    @NonNull
    private String name;

    @Relationship(NeoConsts.R_BOSS_OF_CLASS)
    @NonNull
    private Teacher boss;                // 班级的班主任
}
```

### 6.6 关系常量 NeoConsts.java

```java
public interface NeoConsts {
    String R_STUDENT_OF_CLASS = "R_STUDENT_OF_CLASS";    // 班级拥有的学生
    String R_BOSS_OF_CLASS = "R_BOSS_OF_CLASS";          // 班级的班主任
    String R_TEACHER_OF_LESSON = "R_TEACHER_OF_LESSON";  // 课程的老师
    String R_LESSON_OF_STUDENT = "R_LESSON_OF_STUDENT";  // 学生选的课
}
```

把关系类型名抽成常量，避免字符串硬编码散落各处。用 `interface` 当常量容器是 Java 常见写法（接口字段默认 `public static final`）。

### 6.7 整体关系图

把四个节点和四条关系连起来，就是一张校园关系图：

```
Teacher <--R_BOSS_OF_CLASS-- Class --R_STUDENT_OF_CLASS--> Student
Teacher <--R_TEACHER_OF_LESSON-- Lesson <--R_LESSON_OF_STUDENT-- Student
```

即：
- 班级有班主任（Teacher）
- 班级有学生（Student）
- 学生选了课程（Lesson）
- 课程有任教老师（Teacher）

---

## 七、Repository：派生查询与 Cypher 自定义查询

Spring Data Neo4j 的 Repository 和 Spring Data JPA 几乎一样——继承接口就能用，方法名能自动翻译成查询。

### 7.1 最简 Repository（Teacher/Lesson/Class）

```java
public interface TeacherRepository extends Neo4jRepository<Teacher, String> { }
public interface LessonRepository extends Neo4jRepository<Lesson, String> { }
public interface ClassRepository extends Neo4jRepository<Class, String> {
    Optional<Class> findByName(String name);   // 派生查询
}
```

- `Neo4jRepository<T, ID>`：Spring Data Neo4j 的基础接口，泛型是实体类型和主键类型。继承它就自动有了 `save`、`findById`、`findAll`、`deleteAll`、`count` 等方法（和 JPA 的 `JpaRepository` 一个套路）。
- `findByName(String name)`：**派生查询**——只写方法名，Spring Data 自动解析成 Cypher `MATCH (n:Class {name: $name}) RETURN n`，不用写语句。

> 💡 前端类比：这就像前端 ORM（Prisma）的 `prisma.class.findFirst({ where: { name } })`，或者 GraphQL 的按字段查询——你声明"按什么查"，框架帮你翻译。

### 7.2 StudentRepository（重点：自定义 Cypher + 深度查询）

```java
public interface StudentRepository extends Neo4jRepository<Student, String> {

    // 1. 派生查询 + 深度参数
    Optional<Student> findByName(String name, @Depth int depth);

    // 2. 自定义 Cypher：按班级统计人数
    @Query("MATCH (s:Student)-[r:R_STUDENT_OF_CLASS]->(c:Class{name:{className}}) return count(s)")
    Long countByClassName(@Param("className") String className);

    // 3. 自定义 Cypher：按课程分组查同学关系
    @Query("match (s:Student)-[:R_LESSON_OF_STUDENT]->(l:Lesson)<-[:R_LESSON_OF_STUDENT]-(:Student) "
         + "with l.name as lessonName,collect(distinct s) as students return lessonName,students")
    List<ClassmateInfoGroupByLesson> findByClassmateGroupByLesson();

    // 4. 自定义 Cypher：师生关系（班主任路线）
    @Query("match (s:Student)-[:R_STUDENT_OF_CLASS]->(:Class)-[:R_BOSS_OF_CLASS]->(t:Teacher) "
         + "with t.name as teacherName,collect(distinct s) as students return teacherName,students")
    List<TeacherStudent> findTeacherStudentByClass();

    // 5. 自定义 Cypher：师生关系（任课老师路线）
    @Query("match ((s:Student)-[:R_LESSON_OF_STUDENT]->(:Lesson)-[:R_TEACHER_OF_LESSON]->(t:Teacher)) "
         + "with t.name as teacherName,collect(distinct s) as students return teacherName,students")
    List<TeacherStudent> findTeacherStudentByLesson();
}
```

逐个拆解：

**① 深度查询 `@Depth`**

```java
Optional<Student> findByName(String name, @Depth int depth);
```

`@Depth` 是 Spring Data Neo4j 特有的参数注解，控制**查询时沿着关系遍历几跳**：

- `depth=0`：只返回 Student 节点本身，`lessons` 和 `clazz` 都是 null（不加载关系）。
- `depth=1`：加载学生 + 直接关联的课程和班级，但课程的 `teacher` 是 null。
- `depth=2`：加载学生 + 课程 + 班级 + 课程的任教老师。

这是图数据库查询的关键概念——**按需加载关系的深度**，避免一次查询把整张图都拉出来。

**② `@Query` 自定义 Cypher + `@Param` 参数绑定**

```java
@Query("MATCH (s:Student)-[r:R_STUDENT_OF_CLASS]->(c:Class{name:{className}}) return count(s)")
Long countByClassName(@Param("className") String className);
```

- `@Query`：写原生 Cypher 语句。
- `{className}`：占位符，绑定 `@Param("className")` 标注的方法参数。
- 返回 `Long`：Cypher 的 `count(s)` 是数字，直接映射成 Long。

**③ 投影到自定义对象 `@QueryResult`**

```java
@Query("match (s:Student)-[:R_LESSON_OF_STUDENT]->(l:Lesson)<-[:R_LESSON_OF_STUDENT]-(:Student) "
     + "with l.name as lessonName,collect(distinct s) as students return lessonName,students")
List<ClassmateInfoGroupByLesson> findByClassmateGroupByLesson();
```

这条 Cypher 的含义：找所有"两个学生选了同一门课"的关系，按课程名分组，把同选一门课的学生收成列表。返回结果不是 Student，而是自定义的 `ClassmateInfoGroupByLesson`：

```java
@Data
@QueryResult
public class ClassmateInfoGroupByLesson {
    private String lessonName;
    private List<Student> students;
}
```

- `@QueryResult`：标记这是一个查询结果投影对象（类似 JPA 的 DTO 投影）。Cypher 返回的 `lessonName`、`students` 列会按字段名自动映射进这个对象。

**④⑤ 两条路线查师生关系**

- `findTeacherStudentByClass`：学生-班级-班主任，走"班主任"路线
- `findTeacherStudentByLesson`：学生-课程-任课老师，走"任课老师"路线

两条 Cypher 结构相似，都是 `match (起点)-[:关系]->(中间)-[:关系]->(终点) with 终点名 as X, collect(distinct 起点) as Y return X,Y`——把两跳关系的结果按终点分组聚合。

---

## 八、Service 层：组装业务

`NeoService` 是业务编排层，注入 4 个 Repository + 1 个 `SessionFactory`：

### 8.1 初始化数据 initData()

```java
@Transactional
public void initData() {
    // 1. 存老师
    Teacher akai = Teacher.of("迈特凯");
    teacherRepo.save(akai);
    // ... 共 5 个老师

    // 2. 存课程（构造时关联老师）
    Lesson tishu = Lesson.of("体术", akai);
    lessonRepo.save(tishu);
    // ... 共 7 门课

    // 3. 存班级（关联班主任）
    Class seven = Class.of("第七班", kakaxi);
    classRepo.save(seven);

    // 4. 存学生（关联选课和班级）
    List<Student> threeClass = Lists.newArrayList(
        Student.of("漩涡鸣人", Lists.newArrayList(tishu, shoulijian, luoxuanwan, xianshu), seven),
        Student.of("宇智波佐助", Lists.newArrayList(huanshu, zhouyin, shoulijian), seven),
        Student.of("春野樱", Lists.newArrayList(tishu, yiliao, shoulijian), seven)
    );
    studentRepo.saveAll(threeClass);
}
```

关键点：**保存一个 Student 时，Neo4j OGM 会级联保存它关联的 Lesson 和 Class**（如果它们还没存）。但本模块为了清晰，先存老师、再存课程、再存班级、最后存学生，保证每个节点都已存在，学生只负责建立关系。

`@Transactional` 保证整个初始化在一个事务里，要么全成功要么全回滚。

### 8.2 删除数据 delete()

```java
@Transactional
public void delete() {
    // 方式一：直接执行 Cypher 删除
    Session session = sessionFactory.openSession();
    Transaction transaction = session.beginTransaction();
    session.query("match (n)-[r]-() delete n,r", Maps.newHashMap());  // 删节点和关系
    session.query("match (n)-[r]-() delete r", Maps.newHashMap());    // 删关系
    session.query("match (n) delete n", Maps.newHashMap());           // 删节点
    transaction.commit();

    // 方式二：用 repository 删除
    studentRepo.deleteAll();
    classRepo.deleteAll();
    lessonRepo.deleteAll();
    teacherRepo.deleteAll();
}
```

注意 Cypher 删除的顺序：**必须先删关系再删节点**（或同时删），否则节点有关系时无法直接删除。`match (n)-[r]-() delete n,r` 表示匹配所有有关系的节点，连同关系一起删。

`Session` 是 Neo4j OGM 的底层会话对象，`sessionFactory.openSession()` 手动开一个会话执行原生 Cypher——这是 Repository 之外的"逃生舱"，需要精细控制时用。

### 8.3 查询方法

```java
public List<Lesson> findLessonsFromStudent(String studentName, int depth) {
    List<Lesson> lessons = Lists.newArrayList();
    studentRepo.findByName(studentName, depth).ifPresent(student -> lessons.addAll(student.getLessons()));
    return lessons;
}

public Long studentCount(String className) {
    if (StrUtil.isBlank(className)) {
        return studentRepo.count();               // 全校人数
    } else {
        return studentRepo.countByClassName(className);  // 班级人数
    }
}

public Map<String, List<Student>> findClassmatesGroupByLesson() {
    List<ClassmateInfoGroupByLesson> groupByLesson = studentRepo.findByClassmateGroupByLesson();
    Map<String, List<Student>> result = Maps.newHashMap();
    groupByLesson.forEach(c -> result.put(c.getLessonName(), c.getStudents()));
    return result;
}

public Map<String, Set<Student>> findTeacherStudent() {
    List<TeacherStudent> byClass = studentRepo.findTeacherStudentByClass();
    List<TeacherStudent> byLesson = studentRepo.findTeacherStudentByLesson();
    Map<String, Set<Student>> result = Maps.newHashMap();
    byClass.forEach(ts -> result.put(ts.getTeacherName(), Sets.newHashSet(ts.getStudents())));
    byLesson.forEach(ts -> result.put(ts.getTeacherName(), Sets.newHashSet(ts.getStudents())));
    return result;
}
```

Service 做的事：调用 Repository 查询，把结果组装成业务需要的 Map 结构。`findTeacherStudent` 把两条路线（班主任、任课老师）的结果合并到同一个 Map，用 Set 去重——一个老师可能既是班主任又是任课老师。

---

## 九、测试类 Neo4jTest

```java
@Slf4j
public class Neo4jTest extends SpringBootDemoNeo4jApplicationTests {
    @Autowired
    private NeoService neoService;

    @Test
    public void testSave() { neoService.initData(); }

    @Test
    public void testDelete() { neoService.delete(); }

    @Test
    public void testFindLessonsByStudent() {
        // 深度为1，则课程的任教老师的属性为null
        // 深度为2，则会把课程的任教老师的属性赋值
        List<Lesson> lessons = neoService.findLessonsFromStudent("漩涡鸣人", 2);
        lessons.forEach(lesson -> log.info("【lesson】= {}", JSONUtil.toJsonStr(lesson)));
    }

    @Test
    public void testCountStudent() {
        Long all = neoService.studentCount(null);
        Long seven = neoService.studentCount("第七班");
    }

    @Test
    public void testFindClassmates() {
        Map<String, List<Student>> classmates = neoService.findClassmatesGroupByLesson();
        classmates.forEach((k, v) -> log.info("因为一起上了【{}】这门课，成为同学关系的有：{}", k, ...));
    }

    @Test
    public void testFindTeacherStudent() {
        Map<String, Set<Student>> teacherStudent = neoService.findTeacherStudent();
    }
}
```

测试类继承 `SpringBootDemoNeo4jApplicationTests`（带 `@SpringBootTest` 的基类），所以能注入 Spring Bean。测试顺序：先 `testSave` 初始化数据，再跑查询测试，最后 `testDelete` 清理。

注意 `testFindLessonsByStudent` 的注释——深度 1 和 2 的区别，这是理解图查询的关键。

---

## 十、运行与验证

### 10.1 启动 Neo4j

```sh
docker pull neo4j:3.5.0
docker run -d -p 7474:7474 -p 7687:7687 --name neo4j-3.5.0 neo4j:3.5.0
```

浏览器访问 `http://localhost:7474`，初始账号密码 `neo4j/neo4j`，首次登录改密码为 `neo4j/admin`（和 yml 配置一致）。

### 10.2 运行测试

在 IDE 里依次运行：`testSave` → `testFindLessonsByStudent` → `testCountStudent` → `testFindClassmates` → `testFindTeacherStudent`。

### 10.3 在 Neo4j 后台查看图

运行完测试后，在 `http://localhost:7474` 的 Cypher 输入框执行：

```cypher
MATCH (n) RETURN n
```

就能看到所有节点和关系以图形化方式展示——学生、老师、课程、班级之间的连线一目了然，这正是图数据库的可视化优势。

---

## 十一、动手练习

1. **改深度看差异**：把 `testFindLessonsByStudent` 的 depth 改成 0、1、2 分别运行，观察返回的 Lesson 对象里 `teacher` 字段是否有值，理解深度查询。
2. **加一个新关系**：给 Student 加一个"朋友"关系 `R_FRIEND_OF`，存两个互为朋友的学生，写一条 Cypher 查"朋友的朋友"（两跳关系）。
3. **写派生查询**：在 `TeacherRepository` 加 `findByName(String name)`，不写 Cypher，验证自动生成。
4. **加属性到关系上**：给"选课"关系加一个 `score` 属性（成绩），查询某学生各科成绩。注意关系属性需要用 `@RelationshipEntity` 建模，查文档实现。
5. **对比 SQL**：把 `findByClassmateGroupByLesson` 的 Cypher 翻译成等价的关系型 SQL（多表 JOIN），体会图查询的简洁。
6. **性能对比**：构造 1000 个学生、100 门课的随机选课数据，分别用 Neo4j Cypher 和关系型 SQL 查"同学关系"，对比查询耗时。

---

## 十二、本模块知识点总结（结合实际开发详解）

图数据库是小众但强大的工具，用在正确场景能化繁为简，用错场景则徒增复杂。下面把核心知识点放到真实开发里讲透。

### 12.1 关系型 vs 图数据库：什么时候该用 Neo4j？

**实际开发中的判断标准——看"关系本身是不是查询重点"。**

| 场景 | 推荐存储 | 理由 |
| --- | --- | --- |
| 电商订单、用户账号、财务流水 | 关系型（MySQL） | 数据结构固定，关系简单，事务强一致 |
| 社交网络"好友的朋友"、推荐系统 | 图数据库 | 关系多跳查询是核心需求 |
| 知识图谱、风控反欺诈（资金流向关联） | 图数据库 | 实体间关系密集且需灵活扩展 |
| 权限模型 RBAC（用户-角色-权限） | 关系型即可 | 关系层级浅，JOIN 几层够用 |
| 组织架构（上下级、跨部门协作） | 图数据库 | 多层级、多类型关系 |

**最佳实践：不要为了用图而用图。** 大多数业务系统用关系型数据库足够。只有当"查询关系链路"成为性能瓶颈或开发痛点时（比如 3 层以上 JOIN、动态关系类型、需要图算法），才引入图数据库。很多项目采用**双写**：关系型存主数据，图数据库存关系视图，各取所长。

**常见坑：**

- 把图数据库当通用存储：图数据库的事务、聚合分析能力弱于关系型，用它存订单流水是灾难。
- 以为图数据库更快：对于单表 CRUD、简单聚合统计，关系型反而更快。图数据库的优势在**关系遍历**，不是全表扫描。

### 12.2 Spring Data Neo4j 的两套 API：OGM vs 新版

本模块用的是 **Neo4j OGM**（`@NodeEntity`、`Neo4jRepository`），这是 Spring Boot 2.x 默认的方式。需要注意的是，Spring Data Neo4j 在 6.x（Spring Boot 2.4+）之后做了大改：

| 特性 | OGM（本模块/旧版） | 新版 SDN（Spring Boot 2.4+） |
| --- | --- | --- |
| 实体注解 | `@NodeEntity`（neo4j.ogm 包） | `@Node`（spring-data-neo4j 包） |
| 关系注解 | `@Relationship`（ogm） | `@Relationship`（spring-data） |
| Repository | `Neo4jRepository` | `Neo4jRepository`（接口不变） |
| 映射方式 | OGM 全量对象图映射 | 轻量级，基于投影 |
| 深度查询 | `@Depth` 参数 | 默认按需，无 `@Depth` |

**实际开发建议**：新项目用 Spring Boot 2.4+ 时，直接用新版 SDN 的 `@Node` 注解，更轻量、性能更好。本模块的 OGM 写法在旧项目维护时仍会遇到，理解原理即可。

**常见坑：** 从 OGM 迁移到新版 SDN 时，`@Depth` 查询行为变化最大——OGM 默认深度 0，新版默认加载一级关系，迁移时查询结果会"突然变多"，需要重新调整。

### 12.3 节点建模：关系方向与双向关系

本模块所有关系都是单向的（如 Student-选课->Lesson）。但实际业务常有双向关系——"A 是 B 的朋友"反过来也成立。

**Neo4j 的关系是有方向的**，建模时要决定方向：

```java
// 单向：只存 A->B，查 B->A 要反向写 Cypher
@Relationship("R_FRIEND_OF")
private List<Person> friends;

// 双向：用 @Relationship(direction = INCOMING/UNDIRECTED) 控制
@Relationship(value = "R_FRIEND_OF", direction = Relationship.UNDIRECTED)
private List<Person> friends;
```

**最佳实践：** 关系方向应反映业务语义。"学生选课"天然是学生指向课程；"朋友"则用无向。建模时想清楚"谁主动建立这个关系"，方向就明确了。

**常见坑：** 忘了方向导致查询为空——存的是 A->B，用 `MATCH (b)-[:REL]->(a)` 查不到，要用 `MATCH (b)<-[:REL]-(a)` 或 `MATCH (a)-[:REL]->(b)`。

### 12.4 深度查询：图数据库的"按需加载"

`@Depth` 是 OGM 时代的关键概念，对应关系型数据库的"延迟加载 vs 立即加载"，但更灵活——可以精确控制遍历几跳。

**实际开发中的深度策略：**

- 列表页：depth=0，只查节点本身，性能最优。
- 详情页：depth=1，加载直接关联。
- 关系分析：depth=2 或更深，按业务需要。

**常见坑：**

- depth 设太大：可能把整张图都加载进来，内存爆炸、查询超时。图数据库的"深度爆炸"比关系型的 N+1 更危险——关系是网状的，深度每加一层，数据量可能指数增长。
- depth=0 却访问关系字段：得到 null，误以为数据没存进去。要先确认深度是否足够。

### 12.5 Cypher 查询：派生查询 vs 自定义查询的边界

**派生查询（按方法名）适合：** 简单的单字段、按属性匹配，如 `findByName`、`existsByName`。

**自定义 `@Query` 适合：**

- 多跳关系遍历（本模块的所有复杂查询都是）
- 聚合分组（`collect`、`count`）
- 投影到自定义对象（`@QueryResult`）
- 子查询管道（`WITH`）

**最佳实践：** 涉及关系遍历的查询一律用 `@Query` 写 Cypher，不要试图用派生查询方法名表达复杂关系（方法名会变成 `findByLessonsTeacherName` 这种怪物，且不一定支持）。Cypher 本身就是为关系遍历设计的，直接写更清晰。

**常见坑：**

- Cypher 占位符语法：OGM 时代用 `{param}` + `@Param`，新版 SDN 用 `$param`，混用会报错。
- `collect` 里忘了 `distinct`：聚合时出现重复元素，结果集膨胀。

### 12.6 事务与 Session：图数据库的事务特性

本模块的 `initData` 和 `delete` 都加了 `@Transactional`。Neo4j 支持事务，但和关系型数据库的事务有差异：

- Neo4j 事务是**图级别**的，锁粒度不如关系型数据库精细（早期版本是库级锁，3.x+ 改进为节点/关系级锁）。
- 图数据库事务主要用于保证"一批节点和关系要么全写入要么全回滚"，不适合长事务。

**最佳实践：**

- 批量初始化数据用 `@Transactional` 包住，避免写一半失败留下脏数据。
- 删除操作务必先删关系再删节点，且放在事务里。
- 需要精细控制时用 `SessionFactory.openSession()` 手动管理（本模块 delete 方法演示了这种"逃生舱"用法）。

**常见坑：** 在事务里做大量节点写入，事务过大导致锁等待或 OOM。图数据批量导入应该用 Neo4j 的 `LOAD CSV` 或官方批量导入工具，而不是在应用层循环 save。

### 12.7 图数据库的部署与运维

本模块用 Docker 跑单机 Neo4j。生产环境要注意：

- **集群部署**：Neo4j 支持因果集群（Causal Cluster），读写分离，但配置复杂。
- **内存配置**：Neo4j 是内存敏感型，要调 `dbms.memory.heap.max_size` 和 `pagecache.size`，否则大数据量查询会 OOM。
- **备份**：图数据库备份用 `neo4j-admin dump`，和关系型的 binlog 不同。
- **可视化**：Neo4j 自带浏览器（7474 端口）能直接画图，这是调试图数据的利器，比看 JSON 直观得多。

**常见坑：** 生产环境忘了改默认密码、忘了限制 7474 端口的外网访问，导致图数据库裸奔。Neo4j 的管理后台暴露在外网是严重安全隐患。

---

> 📌 **学习建议**：作为前端工程师，图数据库可能是你接触起来最"亲切"的 NoSQL——它的节点关系模型和前端的对象引用模型几乎同构，Cypher 的模式匹配也像正则一样直观。建议重点掌握两点：一是"什么时候该用图数据库"（关系是查询重点时），二是 Cypher 的关系遍历语法（`()-[:REL]->()`）。本模块的校园关系网是个很好的练手场景，把"同学关系""师生关系"这些多跳查询用 Cypher 写一遍，再想象用 SQL 写一遍，你就能体会到图数据库的价值所在。另外，Neo4j 自带的浏览器可视化非常直观，跑完数据后一定要去 7474 端口看看那张图，比读任何文档都管用。
