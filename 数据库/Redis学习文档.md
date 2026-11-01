# Redis 学习文档

> Redis 是 Java 后端开发中**使用频率最高的中间件**，没有之一。它几乎出现在每一个面试题、每一份简历和每一个线上故障复盘里。
> 本篇以 **Redis 7.x** 为基准（兼容 6.x，附 8.0 新特性说明），从"为什么用"讲到"怎么用不炸"，覆盖数据类型、持久化、高可用、缓存三大问题、分布式锁、Spring Boot 集成与典型业务场景。
> 思路：**业务场景 → 命令 → 原理 → 坑 → 落地代码**。带 ⭐ 的是开发高频/面试重点。

---

## 📖 目录

1. [先搞清楚：我们为什么需要 Redis](#一先搞清楚我们为什么需要-redis)
2. [安装、配置与连接](#二安装配置与连接)
3. [九大数据类型与业务场景 ⭐](#三九大数据类型与业务场景-)
4. [Key 设计与内存管理](#四key-设计与内存管理)
5. [过期策略与内存淘汰 ⭐](#五过期策略与内存淘汰-)
6. [持久化：RDB / AOF / 混合](#六持久化rdb--aof--混合)
7. [事务与 Lua 脚本](#七事务与-lua-脚本)
8. [发布订阅与 Stream 消息队列](#八发布订阅与-stream-消息队列)
9. [高可用：主从 / 哨兵 / Cluster](#九高可用主从--哨兵--cluster)
10. [缓存三大问题与一致性 ⭐⭐](#十缓存三大问题与一致性-)
11. [分布式锁 ⭐⭐](#十一分布式锁-)
12. [Spring Boot 集成 Redis ⭐](#十二spring-boot-集成-redis-)
13. [典型业务实战](#十三典型业务实战)
14. [运维、监控与安全](#十四运维监控与安全)
15. [常见坑清单](#十五常见坑清单)
16. [新版本补充](#十六新版本补充)
17. [📌 在 Spring Boot 中](#-在-spring-boot-中)
18. [本章小结](#本章小结)

---

## 一、先搞清楚：我们为什么需要 Redis

### 1.1 一个真实的场景

学生管理系统上线三个月，`student` 表 50 万行，首页要展示"班级排行榜"：

```sql
SELECT c.name, AVG(s.mark) AS avg_mark
FROM class c
JOIN student st ON st.class_id = c.id
JOIN score s ON s.student_id = st.id
GROUP BY c.name
ORDER BY avg_mark DESC;
```

单次执行 300ms，QPS 200 时数据库 CPU 打满。但这份排行榜**变化很慢**——一天更新几次就够了。

于是加一层 Redis：查之前先看 Redis，有就直接返回（1ms）；没有就查 MySQL 再写回 Redis（300ms），30 分钟过期。数据库压力瞬间降两个数量级。

**这就是缓存最朴素的价值：用内存换时间，用空间换数据库的命。**

### 1.2 Redis 的能力边界

| 能力 | 说明 | 典型场景 |
| :--- | :--- | :--- |
| 缓存 | 内存 KV，读写 10 万+ QPS | 热点数据、字典、配置 |
| 分布式共享 | 多台应用服务器看到同一份数据 | 登录 Token、Session |
| 原子计数器 | 单线程执行命令，天然原子 | 点赞数、库存扣减、限流 |
| 数据结构 | List/Set/ZSet/Hash 等 | 排行榜、去重、队列 |
| 消息 | Pub/Sub、Stream | 轻量异步、事件通知 |
| 分布式锁 | `SET NX EX` + Lua | 防止重复下单、重复任务 |
| 地理位置 / 基数统计 | GEO、HyperLogLog | 附近的人、UV 统计 |

### 1.3 和邻居们的区别

| 对比对象 | 定位 | 关键差异 |
| :--- | :--- | :--- |
| MySQL | 持久化关系库 | 磁盘、强一致、慢；Redis 是内存、最终一致、快 |
| Memcached | 纯 KV 缓存 | Memcached 只有 String，无持久化，无集群原生支持；Redis 数据类型丰富 |
| Caffeine | JVM 本地缓存 | 本地缓存无网络开销、更快，但多实例不共享、容量受堆限制；**生产常用"本地 + Redis"两级缓存** |
| MongoDB | 文档数据库 | 面向持久化存储；Redis 面向内存高速访问 |
| RabbitMQ/Kafka | 专业消息队列 | Redis 消息无重试/堆积治理/顺序保证等企业级能力，只适合轻量场景 |

> 💡 **一句话选型**：单机热点用 Caffeine，跨实例共享用 Redis，持久化真数据用 MySQL。三者不是替代关系，是一条链路上的不同层。

### 1.4 版本选择

| 版本 | 关键变化 | 建议 |
| :--- | :--- | :--- |
| 6.0 | ACL、多线程 I/O、RESP3 | 最低要求 |
| 7.0 | Function、Multi-Part AOF、Sharded Pub/Sub、`> ` 大改进 | **主流生产版本** |
| 7.2 | Hash 字段级过期（预览）、`WAITAOF` | 可用 |
| 7.4 | Hash 字段级过期、`HSCAN NOVALUES` | 可用 |
| 8.0 | Hash 字段过期 GA、向量集合（Vector Set）、内置查询引擎 | 新项目可评估 |

> ⚠️ Redis 官方在 7.4 之后把许可证改为 RSALv2/SSPLv1，社区衍生出 **Valkey**（Linux 基金会）。如果公司对开源协议敏感，需要提前确认；**API 与协议基本兼容**，客户端无需改动。

---

## 二、安装、配置与连接

### 2.1 Docker 启动（开发环境推荐）

```yaml
# docker-compose.yml
services:
  redis:
    image: redis:7.4
    container_name: redis-dev
    ports:
      - "6379:6379"
    command: ["redis-server", "/usr/local/etc/redis/redis.conf"]
    volumes:
      - ./redis.conf:/usr/local/etc/redis/redis.conf
      - ./data:/data
    restart: unless-stopped
```

```bash
docker compose up -d
docker exec -it redis-dev redis-cli
```

### 2.2 redis.conf 生产必改项

```conf
# ---- 网络 ----
bind 0.0.0.0              # 生产建议绑定内网网卡，如 bind 192.168.1.10
port 6379
protected-mode yes
timeout 0                 # 客户端空闲超时，0 表示不主动断开
tcp-keepalive 300

# ---- 安全 ----
requirepass YourStrongPwd!   # 必须设密码；ACL 更细的权限见 14.3
# rename-command FLUSHALL ""   # 禁用危险命令（7.0 后推荐用 ACL 限制）

# ---- 内存 ----
maxmemory 4gb
maxmemory-policy allkeys-lru   # 纯缓存场景；有持久化数据时按需选择

# ---- 持久化 ----
appendonly yes
appendfsync everysec
save 3600 1 300 100 60 10000

# ---- 慢查询 ----
slowlog-log-slower-than 10000   # 10ms
slowlog-max-len 128

# ---- 并发 ----
io-threads 4               # 建议 = CPU 核数，最多 8
```

### 2.3 客户端工具

| 工具 | 说明 |
| :--- | :--- |
| `redis-cli` | 官方命令行，排查问题首选 |
| RedisInsight | 官方 GUI，可视化 key、慢日志、内存分析 |
| Another Redis Desktop Manager | 国内常用轻量 GUI |

```bash
redis-cli -h 127.0.0.1 -p 6379 -a 'YourStrongPwd!'
127.0.0.1:6379> PING
PONG
127.0.0.1:6379> INFO server     # 查看版本、运行时长
127.0.0.1:6379> DBSIZE
```

### 2.4 ACL（6.0+，比密码更细）

```bash
# 创建只读用户，只能访问 user: 前缀的 key
ACL SETUSER app_ro on '>ReadPwd123' '~user:*' +get +mget +exists +ttl
ACL LIST
ACL WHOAMI
```

> ⚠️ **不要把 Redis 暴露到公网**。历史上大量服务器因为 `bind 0.0.0.0` + 无密码被植入挖矿程序。云服务器安全组只放行内网。

---

## 三、九大数据类型与业务场景 ⭐

Redis 的 key 永远是好理解的，但 value 用什么结构，**决定了你的业务代码是 3 行还是 300 行**。

### 3.1 类型总览

| 类型 | 底层结构（7.x） | 一句话用途 | 典型场景 |
| :--- | :--- | :--- | :--- |
| String | int / embstr / raw / SDS | 万能类型 | 缓存对象、计数器、锁、Token |
| Hash | listpack → hashtable | 字段级操作的对象 | 购物车、用户信息局部更新 |
| List | quicklist（listpack 节点） | 有序可重复 | 消息队列、最新列表、栈 |
| Set | intset / listpack / hashtable | 无序去重 | 点赞用户、标签、共同好友 |
| ZSet | listpack → skiplist | 带分数的有序集合 | 排行榜、延迟队列、滑动窗口 |
| Bitmap | String 的位操作 | 位级布尔 | 签到、活跃用户统计 |
| HyperLogLog | 稀疏/稠密 HLL | 基数估算（误差 0.81%） | UV、去重计数 |
| GEO | ZSet 封装 | 地理位置 | 附近的人、门店距离 |
| Stream | radix tree | 持久化消息流 | 可靠消息、消费组 |

查看编码：`OBJECT ENCODING key`。编码不是背知识点用的——**它是判断某个 key 是否"大 key"的第一步**。

### 3.2 String —— 不止是字符串

```bash
SET user:1:name "张三"
SET user:1:json '{"id":1,"name":"张三"}' EX 3600   # 带过期
SET lock:order:100 1 NX EX 30                      # 分布式锁
GET user:1:name
MSET k1 v1 k2 v2
MGET k1 k2

INCR article:1:views          # 原子自增，不存在则从 0 开始
INCRBY article:1:views 10
DECRBY stock:1001 2
APPEND log:a "line1"
STRLEN user:1:name
```

**实际开发场景**：

```java
// 场景 1：把整个对象序列化后存 String（最常用）
String key = "student:info:" + id;
String json = redisTemplate.opsForValue().get(key);
if (json != null) {
    return JSON.parseObject(json, StudentVO.class);
}
StudentVO vo = loadFromDb(id);
redisTemplate.opsForValue().set(key, JSON.toJSONString(vo), 30, TimeUnit.MINUTES);
return vo;

// 场景 2：计数器（浏览量、点赞数）
Long views = redisTemplate.opsForValue().increment("article:1:views");
```

> ⚠️ **`INCR` 是不会失败的原子操作**，但它不知道业务上限。库存扣减不要用 `INCR` 硬扛，要用 Lua 判断库存是否充足。

> ⚠️ **String 存对象时不要频繁"读-改-写"**。并发下 `GET` + 修改 + `SET` 会互相覆盖。需要局部更新字段请用 Hash，或加锁/Lua。

### 3.3 Hash —— 对象的"部分更新"神器

```bash
HSET user:1 name "张三" age 20 sex "男"
HGET user:1 name
HMGET user:1 name age
HGETALL user:1
HINCRBY user:1 age 1
HDEL user:1 sex
HEXISTS user:1 name
HKEYS user:1
HLEN user:1
HSCAN user:1 0 MATCH "na*" COUNT 100   # 大 Hash 禁止 HGETALL，用 HSCAN
```

**业务场景：购物车**

```bash
# key = cart:{userId}, field = 商品ID, value = 数量
HSET cart:1001 2001 2
HINCRBY cart:1001 2001 1
HGETALL cart:1001
HDEL cart:1001 2001
```

**业务场景：用户信息局部更新**

```java
// 只改昵称，别的字段不动，也不需要先读出整个对象
redisTemplate.opsForHash().put("user:1", "nickname", "新昵称");
```

> ⚠️ **大 Hash 是典型大 key**。`HGETALL` 会一次性把所有字段拉回客户端并阻塞单线程，10 万字段的 Hash 可能让 Redis 卡顿数百毫秒。读大 Hash 一律用 `HSCAN` 分批。

> ⚠️ Hash 字段级过期（`HEXPIRE`/`HPEXPIREAT`/`HTTL`/`HPERSIST`）需要 **Redis 7.4+**。低版本想实现"每个字段独立过期"只能用 ZSet 记录 field → 到期时间，自己扫描删除。

### 3.4 List —— 简单的队列与栈

```bash
LPUSH queue:mail "task1"      # 左边进
RPUSH queue:mail "task2"      # 右边进
LPOP queue:mail               # 左边出
RPOP queue:mail 2             # 右边出 2 个（6.2+）
LRANGE queue:mail 0 -1        # 查看全部
LLEN queue:mail
LTRIM queue:mail 0 99         # 只保留前 100 条（固定长度列表）
BLPOP queue:mail 5            # 阻塞 5 秒等待，实现工作队列
RPOPLPUSH src dst             # 安全队列：处理失败可回捞
```

**业务场景：最新 N 条动态**

```bash
LPUSH feed:user:1 "动态ID:1001"
LTRIM feed:user:1 0 99        # 永远只留 100 条
LRANGE feed:user:1 0 9
```

**业务场景：简易队列（不推荐用于核心业务）**

```java
// 生产者
redisTemplate.opsForList().leftPush("queue:mail", task);

// 消费者（轮询）
while (true) {
    Object task = redisTemplate.opsForList().rightPop("queue:mail", 5, TimeUnit.SECONDS);
    if (task != null) handle(task);
}
```

> ⚠️ List 做队列的问题：**没有 ACK、没有消费组、没有重试**。消费者 `RPOP` 后宕机，这条消息就丢了。可靠消息用 Stream（见第八章）或专业 MQ。

### 3.5 Set —— 去重与集合运算

```bash
SADD article:1:likes 1001 1002 1003
SISMEMBER article:1:likes 1001    # 是否点过赞
SCARD article:1:likes             # 点赞数
SMEMBERS article:1:likes          # 大 Set 禁用，改 SSCAN
SREM article:1:likes 1001
SRANDMEMBER article:1:likes 3     # 随机抽 3 个（抽奖）
SPOP article:1:likes              # 随机弹出（不可重复抽奖）

SINTER user:1:tags user:2:tags    # 共同关注
SUNION ...
SDIFF ...
SINTERSTORE result:tags ...       # 把结果存起来
```

**业务场景：点赞**

```bash
SADD like:article:1 {userId}
SREM like:article:1 {userId}
SCARD like:article:1
SISMEMBER like:article:1 {userId}
```

> ⚠️ "点赞数"用 `SCARD` 是准确的；"阅读量"用 `INCR` 更合适。**不要用 `SET` 存一堆 userId 再拼字符串判断**，那是把 Redis 当 JSON 文件用。

### 3.6 ZSet —— 排行榜与延迟队列

```bash
ZADD rank:score 95 stu:1 88 stu:2 76 stu:3
ZREVRANGE rank:score 0 9 WITHSCORES          # Top10（分数从高到低）
ZRANGE rank:score 0 9 WITHSCORES             # 从低到高
ZRANK rank:score stu:1                        # 升序名次（从 0 开始）
ZREVRANK rank:score stu:1                     # 降序名次
ZSCORE rank:score stu:1
ZINCRBY rank:score 5 stu:1                    # 加分
ZCOUNT rank:score 90 100                      # 分数区间人数
ZREMRANGEBYRANK rank:score 0 99               # 删除排名 0-99（保留 Top100）
ZREMRANGEBYSCORE rank:score 0 59              # 删除 60 分以下
```

**业务场景：排行榜（含同分处理）**

```java
// 分数高在前；同分时按时间早的在前 —— 用 score + 时间戳拼成小数
double score = mark + (1 - timestamp / 1e13);
redisTemplate.opsForZSet().add("rank:student", studentId, score);

Set<ZSetOperations.TypedTuple<Object>> top10 =
    redisTemplate.opsForZSet().reverseRangeWithScores("rank:student", 0, 9);
```

**业务场景：延迟队列（订单 30 分钟未支付自动取消）**

```bash
# score = 到期时间戳（毫秒），member = 订单ID
ZADD delay:order 1735660800000 order:1001

# 消费者：取出所有 score <= now 的
ZRANGEBYSCORE delay:order 0 1735660800000 LIMIT 0 100
ZREM delay:order order:1001
```

> ⚠️ ZSet 延迟队列的"取出 + 删除"不是原子的，多消费者会重复消费，需要 Lua 或 `ZPOPMIN` 配合判断到期时间。生产上更推荐 **Redis Stream + 消费组** 或 **RocketMQ 延迟消息**。

### 3.7 Bitmap —— 一年签到只占 46 字节

```bash
SETBIT sign:user:1:2026 0 1     # 1 月 1 日签到（offset 0）
SETBIT sign:user:1:2026 31 1
GETBIT sign:user:1:2026 0
BITCOUNT sign:user:1:2026        # 总签到天数
BITCOUNT sign:user:1:2026 0 0    # 只统计第 1 个字节（前 8 天）
BITOP AND active:20260101 active:20260102 ...   # 连续活跃用户
BITPOS sign:user:1:2026 0        # 第一个 0 的位置
```

**业务场景：签到、活跃用户、布尔型去重**

```java
// 用户 1001 在 2026 年第 100 天签到
redisTemplate.opsForValue().setBit("sign:1001:2026", 99, true);
Boolean signed = redisTemplate.opsForValue().getBit("sign:1001:2026", 99);
Long days = redisTemplate.execute((RedisCallback<Long>) conn ->
        conn.stringCommands().bitCount("sign:1001:2026".getBytes()));
```

> ⚠️ Bitmap 本质是 String，**offset 越大内存越大**。用 `userId` 当 offset 时，如果 userId 是雪花 ID（19 位），一个 Bitmap 会直接撑爆内存。必须是**连续小整数 ID** 或用"用户 → 位序号"映射。

### 3.8 HyperLogLog —— 用 12KB 统计 UV

```bash
PFADD uv:20260101 user:1001 user:1002
PFCOUNT uv:20260101
PFMERGE uv:week uv:20260101 uv:20260102   # 合并多天
```

**业务场景**：网站 UV、搜索词去重数。**标准误差 0.81%，不保留明细，不能判断某个元素是否存在**。要精确去重请用 Set/Bitmap。

### 3.9 GEO —— 附近的人

```bash
GEOADD shop:location 116.397128 39.916527 shop:1
GEOADD shop:location 116.410244 39.916344 shop:2
GEODIST shop:location shop:1 shop:2 km
GEOPOS shop:location shop:1
GEOSEARCH shop:location FROMLONLAT 116.40 39.91 BYRADIUS 3 km ASC COUNT 10 WITHDIST
```

**业务场景**：外卖"附近门店"、打车"附近司机"。底层是 ZSet + GeoHash 编码，**精度约 0.6 米，跨区域误差会变大**。

### 3.10 Stream —— Redis 的"正经"消息队列

```bash
# 生产
XADD stream:order * orderId 1001 status paid
# 读取
XLEN stream:order
XRANGE stream:order - + COUNT 10
XREAD COUNT 10 BLOCK 5000 STREAMS stream:order $      # 阻塞读新消息

# 消费组
XGROUP CREATE stream:order g1 0 MKSTREAM
XREADGROUP GROUP g1 c1 COUNT 10 BLOCK 5000 STREAMS stream:order '>'
XACK stream:order g1 1735660800000-0                 # 确认消费
XPENDING stream:order g1                             # 查看未确认
XAUTOCLAIM stream:order g1 c2 60000 0-0               # 认领超时消息
XTRIM stream:order MAXLEN ~ 10000                     # 限制长度
```

**核心概念**：消息 ID（`时间戳-序号`）、消费组、Pending 列表（已投递未 ACK）、自动认领。**这才是能用于可靠业务的消息模型**。

### 3.11 选型速查

| 需求 | 首选 | 备选 |
| :--- | :--- | :--- |
| 缓存一个对象 | String(JSON) | Hash |
| 只更新对象某字段 | Hash | String + 锁 |
| 计数 | String INCR | Hash HINCRBY |
| 排行榜 | ZSet | — |
| 去重 | Set | Bitmap（ID 连续时更省内存） |
| UV 估算 | HyperLogLog | Set（要精确时） |
| 签到 | Bitmap | Set |
| 简单队列 | List | Stream |
| 可靠消息 | Stream | RocketMQ / Kafka |
| 附近的人 | GEO | PostgreSQL PostGIS |

---

## 四、Key 设计与内存管理

### 4.1 Key 命名规范

```
业务线:模块:对象:标识
```

```text
student:info:1001          # 学生详情
student:score:1001         # 学生成绩
cache:dict:sex             # 字典
lock:order:1001            # 订单锁
limit:api:user:1001        # 限流
```

> ⚠️ **key 必须有业务前缀且不要太长**。key 本身也占内存，`very_long_prefix_for_student_information_module:...` 这种设计在千万级 key 下会浪费几百 MB。
> ⚠️ **同一个业务前缀的 TTL 要加随机值**，否则同一时刻批量过期容易触发缓存雪崩（见第十章）。

### 4.2 内存占用怎么看

```bash
MEMORY USAGE user:1                 # 单个 key 估算
MEMORY USAGE user:1 SAMPLES 0       # 精确计算（大 key 慎用，会阻塞）
redis-cli --bigkeys                 # 扫描大 key（生产慎用，可用 --scan）
redis-cli --memkeys                 # 按内存排序
INFO memory                         # used_memory / used_memory_human / mem_fragmentation_ratio
```

### 4.3 大 key 与热 key

| 问题 | 定义 | 危害 | 治理 |
| :--- | :--- | :--- | :--- |
| 大 key | 单个 String > 10KB，Hash/List/Set/ZSet 元素 > 5000 | 读写阻塞、网络拥塞、删除卡顿 | 拆分、`HSCAN` 分页、`UNLINK` 异步删除 |
| 热 key | 单个 key 的 QPS 远超其他 | 单分片打满、Cluster 倾斜 | 本地缓存、key 加随机后缀打散、读写分离 |

```bash
# 大 key 删除：用 UNLINK 替代 DEL
UNLINK big:hash

# 热 key 排查（7.0+，需先开启）
CONFIG SET lfu-log-factor 10
OBJECT FREQ hot:key
redis-cli --hotkeys
```

**大 key 拆分示例**：一个 `article:1:comments` List 存 20 万条评论 → 改成

```text
comment:article:1:page:1    # 每页 200 条
comment:article:1:page:2
comment:article:1:index     # 分页索引（或直接查 MySQL）
```

### 4.4 内存碎片

`INFO memory` 中的 `mem_fragmentation_ratio`：

- **1 ~ 1.5**：正常
- **> 1.5**：碎片较多，可开启 `activedefrag yes`（需 `activedefrag` 配置支持）
- **< 1**：发生了 swap，性能会断崖式下降，必须排查

---

## 五、过期策略与内存淘汰 ⭐

这是面试必问、线上必踩的一块。**"Redis 过期 key 是怎么删的"** 直接决定你能不能解释"为什么设置过期了内存还在涨"。

### 5.1 设置与查看过期

```bash
EXPIRE key 60            # 秒
PEXPIRE key 60000        # 毫秒
EXPIREAT key 1767225600  # 时间戳（秒）
TTL key                  # 剩余秒数：-1 永不过期，-2 不存在
PTTL key
PERSIST key              # 去掉过期时间
SET key value KEEPTTL    # 重设值但保留 TTL（否则 SET 会清掉 TTL！）
```

> ⚠️ **对已有 key 执行 `SET` 会清除 TTL**。`SET key value` 后 `TTL` 变回 `-1`，这是丢过期时间最常见的原因。要么用 `KEEPTTL`，要么显式再设一次过期。

### 5.2 过期删除策略：惰性 + 定期

| 策略 | 做法 | 缺点 |
| :--- | :--- | :--- |
| 惰性删除 | 访问 key 时才判断是否过期，过期就删 | 不访问的 key 永远不删，占内存 |
| 定期删除 | 每 100ms 随机抽取 20 个带 TTL 的 key，删掉过期的；若过期比例 > 25% 继续抽 | 抽不到的就漏掉（但会被下一轮覆盖） |

**结论：Redis 不会"到点就删"，而是"惰性 + 定期"组合。** 所以会出现：

- `DBSIZE` 比预期大 —— 过期 key 还没被清理
- 内存没降 —— 同上
- 从库读到了已过期的 key —— 主从过期是**主库删除后同步 DEL 命令**，从库不主动过期（Redis 3.2+ 从库读时会返回 null，但数据仍在）

### 5.3 内存淘汰策略（maxmemory-policy）

当 `used_memory > maxmemory` 时触发：

| 策略 | 含义 | 适用 |
| :--- | :--- | :--- |
| `noeviction`（默认） | 不淘汰，写入报错 `OOM command not allowed` | 有重要数据、不能丢 |
| `allkeys-lru` | 所有 key 中淘汰最久未使用的 | **纯缓存场景首选** |
| `allkeys-lfu` | 淘汰访问频率最低的（4.0+） | 热点集中的缓存 |
| `allkeys-random` | 随机淘汰 | 几乎不用 |
| `volatile-lru` | 只在**设置了过期时间**的 key 中按 LRU 淘汰 | 缓存 + 持久数据混存 |
| `volatile-lfu` | 同上，按 LFU | 同上 |
| `volatile-random` | 同上，随机 | 很少用 |
| `volatile-ttl` | 优先淘汰快过期的 | 有时效的缓存 |

> ⚠️ **`volatile-*` 策略下，如果所有 key 都没设 TTL，行为退化成 `noeviction`，写入直接报错**。很多"Redis 写不进去"的故障都是这个原因。
>
> ⚠️ **LRU 在 Redis 里是近似 LRU**（采样 5 个 key 选最久未用），不是精确链表。`maxmemory-samples` 越大越精确，默认 5。

### 5.4 生产配置建议

```conf
maxmemory 4gb                 # 留 20% 给 copy-on-write / 碎片，别等于机器内存
maxmemory-policy allkeys-lru  # 纯缓存
maxmemory-samples 5
```

> 💡 **如果 Redis 里既有缓存又有"不能丢"的数据**（如分布式锁、队列），建议**拆成两个实例**：缓存实例用 `allkeys-lru`，数据实例用 `noeviction` 并做好持久化。混用是很多事故的根源。

---

## 六、持久化：RDB / AOF / 混合

Redis 是内存数据库，**宕机 = 丢数据**。持久化就是决定"丢多少"。

### 6.1 RDB —— 某一时刻的快照

```conf
save 3600 1 300 100 60 10000   # 满足任一条件就触发 bgsave
dbfilename dump.rdb
dir /data
rdbcompression yes
rdbchecksum yes
stop-writes-on-bgsave-error yes
```

- **触发方式**：`BGSAVE`（fork 子进程，主进程继续服务）、`SAVE`（阻塞，禁用）、shutdown、主从全量同步
- **优点**：文件紧凑、恢复快、适合备份和灾备
- **缺点**：两次快照之间的数据会丢；fork 时大内存实例可能卡顿（copy-on-write）

### 6.2 AOF —— 追加写命令日志

```conf
appendonly yes
appendfilename "appendonly.aof"
appendfsync everysec        # always / everysec / no
no-appendfsync-on-rewrite no
auto-aof-rewrite-percentage 100
auto-aof-rewrite-min-size 64mb
```

| appendfsync | 丢数据 | 性能 |
| :--- | :--- | :--- |
| `always` | 几乎不丢 | 最差（每次都 fsync） |
| `everysec`（默认） | 最多 1 秒 | 好 |
| `no` | 由 OS 决定，可能几十秒 | 最好 |

- 7.0 起 AOF 采用 **Multi-Part**：`appendonly.aof.1.base.rdb`（基础快照）+ `appendonly.aof.1.incr.aof`（增量）+ `manifest`（清单）
- `aof-use-rdb-preamble yes`（默认）：基础文件用 RDB 格式，加载更快

### 6.3 混合持久化（推荐）

```conf
appendonly yes
aof-use-rdb-preamble yes     # Redis 4.0+ 默认，AOF 重写时前半段用 RDB
```

重启加载顺序：**先加载 AOF（如果开启），否则 RDB**。

### 6.4 选型

| 场景 | 建议 |
| :--- | :--- |
| 纯缓存，允许全部丢失 | RDB 即可，甚至可关闭持久化 |
| 允许丢 1 秒 | AOF `everysec` |
| 绝对不能丢 | AOF `always` + 主从 + 定期 RDB 备份 |
| 备份/迁移 | `BGSAVE` + 拷贝 `dump.rdb` |

> ⚠️ **主从复制 + 持久化才是完整方案**。只开 RDB 的机器如果宕机后快速重启，可能用旧快照覆盖从库（`repl-backlog` 不够大时）。生产建议 `appendonly yes` + 至少一主一从。

---

## 七、事务与 Lua 脚本

### 7.1 Redis 事务不是关系型事务

```bash
MULTI
SET account:1 900
DECRBY account:1 100
INCRBY account:2 100
EXEC
```

特点：

1. **命令入队，EXEC 时一次性顺序执行**，中间不会插入其他客户端命令
2. **没有回滚**：某条命令运行时报错（如对 String 执行 `LPUSH`），其他命令仍会执行
3. **不支持隔离级别**，天然串行
4. `WATCH key` 实现乐观锁：key 被其他客户端改过，`EXEC` 返回 nil

```bash
WATCH stock:1001
val = GET stock:1001
MULTI
DECR stock:1001
EXEC          # 若 stock:1001 被别人改过，EXEC 失败，需要重试
```

> ⚠️ **集群模式下 WATCH 必须在同一个 slot**，跨 slot 的多 key 事务不可用。

### 7.2 Lua 脚本才是真正的原子操作

```bash
EVAL "return redis.call('SET', KEYS[1], ARGV[1])" 1 mykey myvalue
SCRIPT LOAD "return 1"      # 缓存脚本，返回 sha1
EVALSHA <sha1> 0
```

**为什么 Lua 原子**：Redis 单线程执行业令，脚本执行期间不会处理其他客户端请求。

**实战 1：库存扣减（防超卖）**

```lua
-- stock.lua
-- KEYS[1] = 库存 key
-- ARGV[1] = 扣减数量
local stock = tonumber(redis.call('GET', KEYS[1]))
if stock == nil then
    return -1                     -- 库存不存在
end
if stock < tonumber(ARGV[1]) then
    return 0                      -- 库存不足
end
redis.call('DECRBY', KEYS[1], ARGV[1])
return 1                          -- 扣减成功
```

```java
private static final DefaultRedisScript<Long> STOCK_SCRIPT =
    new DefaultRedisScript<>(
        "local stock = tonumber(redis.call('GET', KEYS[1])) " +
        "if stock == nil then return -1 end " +
        "if stock < tonumber(ARGV[1]) then return 0 end " +
        "redis.call('DECRBY', KEYS[1], ARGV[1]) return 1", Long.class);

Long result = redisTemplate.execute(STOCK_SCRIPT,
        Collections.singletonList("stock:1001"), "1");
```

**实战 2：接口滑动窗口限流**

```lua
-- KEYS[1] = 限流 key, ARGV[1] = 窗口秒数, ARGV[2] = 最大请求数
local now = tonumber(redis.call('TIME')[1])
local windowStart = now - tonumber(ARGV[1])
redis.call('ZREMRANGEBYSCORE', KEYS[1], 0, windowStart)
local count = redis.call('ZCARD', KEYS[1])
if count >= tonumber(ARGV[2]) then
    return 0
end
redis.call('ZADD', KEYS[1], now, now .. ':' .. math.random())
redis.call('EXPIRE', KEYS[1], tonumber(ARGV[1]) + 1)
return 1
```

**实战 3：分布式锁安全释放（见第十一章）**

> ⚠️ **Lua 脚本要短**。脚本执行期间 Redis 阻塞，写个死循环或遍历百万 key 的脚本会让整个实例不可用。复杂逻辑放应用层，脚本只做"判断 + 原子改"。
>
> ⚠️ **集群模式下脚本操作的所有 key 必须在同一 slot**，否则报 `CROSSSLOT`。

---

## 八、发布订阅与 Stream 消息队列

### 8.1 Pub/Sub

```bash
SUBSCRIBE news:student
PUBLISH news:student "考试成绩已发布"
PSUBSCRIBE news:*
```

- **优点**：简单、实时、广播
- **缺点**：**消息不持久、不重试、无 ACK**，订阅者掉线期间的消息永久丢失
- 适合：配置变更通知、轻量事件广播、WebSocket 广播

### 8.2 Stream

前面 3.10 已给命令。关键设计：

| 概念 | 说明 |
| :--- | :--- |
| Consumer Group | 多个消费者分担消息，同组内一条消息只被一个消费者消费 |
| Pending List | 已投递未 ACK 的消息，消费者宕机后其他消费者可 `XAUTOCLAIM` 认领 |
| `MAXLEN ~` | 近似裁剪，控制内存 |
| `XACK` | 业务处理完必须 ACK，否则永远 Pending |

```java
// Spring Data Redis 消费 Stream
StreamListener<String, MapRecord<String, Object, Object>> listener =
    StreamMessageListenerContainer.StreamMessageListenerContainerOptions
        .builder()
        .pollTimeout(Duration.ofSeconds(2))
        .build();

container.receiveAutoAck(
    Consumer.from("g1", "c1"),
    StreamOffset.create("stream:order", ReadOffset.lastConsumed()),
    message -> {
        // 处理消息
    });
```

> ⚠️ Stream 不是万能的：**没有死信队列、没有消息堆积告警、没有延迟消息**。核心业务（订单、支付）请用 RocketMQ/Kafka。

---

## 九、高可用：主从 / 哨兵 / Cluster

### 9.1 主从复制

```conf
# 从节点
replicaof 192.168.1.10 6379
masterauth YourStrongPwd!
```

- 主写从读，异步复制（`WAIT` 可同步等待 N 个副本确认）
- 全量同步（RDB + backlog）→ 增量同步（offset）
- **主节点宕机需要人工切换**

### 9.2 哨兵 Sentinel

```conf
# sentinel.conf
sentinel monitor mymaster 192.168.1.10 6379 2
sentinel down-after-milliseconds mymaster 30000
sentinel failover-timeout mymaster 180000
sentinel parallel-syncs mymaster 1
```

- 至少 **3 个哨兵**（奇数），`quorum=2`
- 主观下线 → 客观下线 → 选举 leader → 提升从库 → 通知客户端
- 客户端（Lettuce/Jedis）配置哨兵地址，自动感知主节点切换

```yaml
spring:
  data:
    redis:
      sentinel:
        master: mymaster
        nodes: 192.168.1.11:26379,192.168.1.12:26379,192.168.1.13:26379
```

### 9.3 Cluster

- **16384 个 slot**，`CRC16(key) % 16384`
- 至少 3 主 3 从
- 客户端收到 `MOVED`/`ASK` 后重定向

```bash
redis-cli --cluster create \
  192.168.1.10:6379 192.168.1.11:6379 192.168.1.12:6379 \
  192.168.1.13:6379 192.168.1.14:6379 192.168.1.15:6379 \
  --cluster-replicas 1
redis-cli -c -p 6379 CLUSTER INFO
```

**Cluster 的限制（开发必知）**：

1. 多 key 操作必须**同一 slot**：`MGET k1 k2` 可能跨 slot 报错
2. 解决：**hash tag** —— `{user:1001}:name` 和 `{user:1001}:age` 会落到同一 slot
3. 不支持跨 slot 事务、跨 slot Lua
4. `SELECT` 不可用（只有 db0）
5. 数据库数量、`KEYS *` 等运维命令受限（用 `SCAN`）

```bash
# hash tag 示例
SET {order:1001}:info xxx
SET {order:1001}:status paid   # 与上面同 slot
```

### 9.4 选型

| 规模 | 方案 |
| :--- | :--- |
| 单机，可接受短暂不可用 | 单节点 + 持久化 |
| 读多写少、数据 < 16GB | 主从 + 哨兵 |
| 数据 > 单机内存 / 写并发高 | Cluster |
| 云环境 | 直接用云 Redis（托管主从/集群） |

---

## 十、缓存三大问题与一致性 ⭐⭐

这是 **Redis 面试 100% 会问、线上 100% 会遇到**的一章。

### 10.1 缓存穿透

**现象**：查询一个**数据库里也不存在**的数据（如 `id = -1`），缓存永远不命中，每次请求都打到 MySQL。恶意攻击时数据库直接被打挂。

**解决方案**：

| 方案 | 做法 | 优缺点 |
| :--- | :--- | :--- |
| 空值缓存 | 查不到也缓存 `""`，TTL 短（1~5 分钟） | 简单；可能被大量随机 key 攻击，占用内存 |
| 布隆过滤器 | 所有合法 ID 先过 BloomFilter，不存在直接返回 | 省内存；有误判、删除困难 |
| 参数校验 | ID 必须合法、字符串长度校验、限流 | 第一道防线，必须做 |

```java
public StudentVO getStudent(Long id) {
    if (id == null || id <= 0) {
        return null;                       // 参数校验
    }
    String key = "student:info:" + id;
    String cached = redisTemplate.opsForValue().get(key);
    if (cached != null) {
        return EMPTY_FLAG.equals(cached) ? null : JSON.parseObject(cached, StudentVO.class);
    }
    StudentVO vo = studentMapper.selectById(id);
    if (vo == null) {
        redisTemplate.opsForValue().set(key, EMPTY_FLAG, 2, TimeUnit.MINUTES);  // 空值缓存
        return null;
    }
    redisTemplate.opsForValue().set(key, JSON.toJSONString(vo), 30, TimeUnit.MINUTES);
    return vo;
}
```

**布隆过滤器（Redisson 实现）**：

```java
RBloomFilter<Long> bloomFilter = redissonClient.getBloomFilter("student:ids");
bloomFilter.tryInit(1_000_000L, 0.01);   // 预计 100 万条，误判率 1%

if (!bloomFilter.contains(id)) {
    return null;                          // 一定不存在
}
// 可能存在（有 1% 误判），继续查缓存/DB
```

> ⚠️ **布隆过滤器不能删除元素**（标准 BloomFilter），删除需要 Counting BloomFilter 或定期重建。

### 10.2 缓存击穿

**现象**：某个**热点 key 突然过期**，瞬间大量请求同时发现缓存失效，一起打到数据库。

**解决方案**：

| 方案 | 做法 | 特点 |
| :--- | :--- | :--- |
| 互斥锁 | 只允许一个线程回源，其他线程等待后读缓存 | 强一致、有等待；注意锁超时与重试 |
| 逻辑过期 | 缓存永不物理过期，value 里存逻辑过期时间；过期后异步刷新 | 高可用、可容忍短暂旧数据 |
| 热点 key 永不过期 + 后台定时刷新 | 定时任务主动更新 | 最简单，适合可预知的热点 |

```java
// 互斥锁方案
public StudentVO getWithMutex(Long id) {
    String key = "student:info:" + id;
    String cached = redisTemplate.opsForValue().get(key);
    if (cached != null) return JSON.parseObject(cached, StudentVO.class);

    String lockKey = "lock:" + key;
    boolean locked = Boolean.TRUE.equals(
            redisTemplate.opsForValue().setIfAbsent(lockKey, "1", 10, TimeUnit.SECONDS));
    if (!locked) {
        try {
            Thread.sleep(50);
            return getWithMutex(id);       // 自旋重试（生产要限制重试次数）
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            return null;
        }
    }
    try {
        // 双重检查：可能别人已经回填了
        cached = redisTemplate.opsForValue().get(key);
        if (cached != null) return JSON.parseObject(cached, StudentVO.class);

        StudentVO vo = studentMapper.selectById(id);
        if (vo != null) {
            redisTemplate.opsForValue().set(key, JSON.toJSONString(vo), 30, TimeUnit.MINUTES);
        }
        return vo;
    } finally {
        redisTemplate.delete(lockKey);     // 生产用 Lua 校验持有者后再删
    }
}
```

### 10.3 缓存雪崩

**现象**：**大量 key 同一时刻过期**，或 **Redis 集群整体宕机**，请求全部涌向数据库。

**解决方案**：

1. **TTL 加随机值**：`30分钟 + random(0, 5分钟)`
2. **多级缓存**：Caffeine（本地）→ Redis → MySQL
3. **Redis 高可用**：主从 + 哨兵/Cluster，避免单点
4. **限流降级**：Sentinel/Resilience4j 保护数据库
5. **预热**：启动时或定时任务提前加载热点数据

```java
// TTL 打散
long ttl = 30 * 60 + ThreadLocalRandom.current().nextInt(0, 300);
redisTemplate.opsForValue().set(key, json, ttl, TimeUnit.SECONDS);
```

```java
// 多级缓存骨架
public StudentVO get(Long id) {
    String key = "student:info:" + id;
    // L1：本地缓存（毫秒级，无网络）
    StudentVO local = caffeineCache.getIfPresent(key);
    if (local != null) return local;
    // L2：Redis
    String json = redisTemplate.opsForValue().get(key);
    if (json != null) {
        StudentVO vo = JSON.parseObject(json, StudentVO.class);
        caffeineCache.put(key, vo);
        return vo;
    }
    // L3：MySQL
    StudentVO vo = studentMapper.selectById(id);
    if (vo != null) {
        redisTemplate.opsForValue().set(key, JSON.toJSONString(vo), 30, TimeUnit.MINUTES);
        caffeineCache.put(key, vo);
    }
    return vo;
}
```

> ⚠️ 多级缓存的一致性问题更复杂：更新数据时要**同时失效 L1 和 L2**，且多实例的 L1 需要广播失效（Redis Pub/Sub 通知各实例清本地缓存）。

### 10.4 缓存与数据库一致性 ⭐

**先更新数据库，再删除缓存（Cache Aside）** 是业界最常用方案：

```java
@Transactional
public void updateStudent(Student student) {
    studentMapper.updateById(student);                 // 1. 更新 DB
    redisTemplate.delete("student:info:" + student.getId());  // 2. 删除缓存
}
```

为什么是**删除**而不是更新缓存？

- 更新缓存：并发写时可能写入旧值（后写的反而是旧数据）
- 删除缓存：下次读时按 DB 最新值重建，简单可靠
- **懒加载思想**：不读的数据不用缓存，省一次写

**仍然存在的不一致窗口**：

| 场景 | 时序 | 结果 |
| :--- | :--- | :--- |
| 正常 | 写 DB → 删缓存 | 一致 |
| 并发读 | 读缓存 miss → 查 DB(旧) → 写缓存；同时写 DB → 删缓存 | 缓存中留下旧值 |

**补救方案**：

1. **延时双删**：删除缓存 → 更新 DB → 延迟 500ms 再删一次
2. **消息队列补偿**：删除失败进入 MQ 重试
3. **订阅 binlog**：Canal 监听 MySQL binlog，异步删缓存 / 更新缓存（最终一致，业务代码零侵入）
4. **强一致场景**：加分布式锁或直接查库，不要依赖缓存

> 💡 **重要认知：缓存和数据库做到"强一致"的成本极高，绝大多数业务只需要"最终一致"。** 不要为了理论上的 1ms 不一致引入复杂的分布式事务。

---

## 十一、分布式锁 ⭐

### 11.1 为什么需要分布式锁

单机 `synchronized` 只在一个 JVM 内有效。部署 3 个实例时，同一时刻可能有 3 个线程同时执行"查询库存 → 判断 → 扣减"，导致超卖。

### 11.2 正确的加锁姿势

```bash
SET lock:order:1001 <唯一标识> NX EX 30
```

- `NX`：key 不存在才设置（互斥）
- `EX 30`：过期时间，防止持锁进程崩溃后死锁
- **必须是原子命令**，不能拆成 `SETNX` + `EXPIRE`

```java
String lockKey = "lock:order:" + orderId;
String requestId = UUID.randomUUID().toString();
Boolean ok = redisTemplate.opsForValue()
        .setIfAbsent(lockKey, requestId, 30, TimeUnit.SECONDS);
if (!Boolean.TRUE.equals(ok)) {
    throw new BizException("订单处理中，请勿重复提交");
}
try {
    doBusiness(orderId);
} finally {
    // 释放锁：必须校验是自己的锁，且"比较 + 删除"必须原子
    String script =
        "if redis.call('GET', KEYS[1]) == ARGV[1] then " +
        "  return redis.call('DEL', KEYS[1]) " +
        "else return 0 end";
    redisTemplate.execute(new DefaultRedisScript<>(script, Long.class),
            Collections.singletonList(lockKey), requestId);
}
```

**三个必踩的坑**：

1. **不设过期时间** → 进程崩溃后锁永远不释放
2. **直接 `DEL`** → 可能删掉别人的锁（A 超时后 B 拿到锁，A 执行完把 B 的锁删了）
3. **业务执行时间 > 锁过期时间** → 锁自动释放，其他线程进入，等于没锁

### 11.3 Redisson：生产级实现

手写锁很难覆盖"锁续期、可重入、公平锁、读写锁"，生产建议直接用 **Redisson**。

```java
@Bean(destroyMethod = "shutdown")
public RedissonClient redissonClient() {
    Config config = new Config();
    config.useSingleServer()
          .setAddress("redis://127.0.0.1:6379")
          .setPassword("YourStrongPwd!")
          .setDatabase(0);
    return Redisson.create(config);
}
```

```java
RLock lock = redissonClient.getLock("lock:order:" + orderId);
boolean locked = false;
try {
    // tryLock(waitTime, leaseTime, unit)
    // leaseTime = -1 时启用看门狗，默认 30s，每 10s 自动续期
    locked = lock.tryLock(3, TimeUnit.SECONDS);
    if (!locked) {
        throw new BizException("系统繁忙，请稍后再试");
    }
    doBusiness(orderId);
} catch (InterruptedException e) {
    Thread.currentThread().interrupt();
} finally {
    if (locked && lock.isHeldByCurrentThread()) {
        lock.unlock();     // 必须判断持有者，否则抛 IllegalMonitorStateException
    }
}
```

**Redisson 的关键机制**：

| 机制 | 说明 |
| :--- | :--- |
| 看门狗（Watch Dog） | 不指定 leaseTime 时，后台每 10s 把锁续到 30s，业务没执行完锁不会丢 |
| 可重入 | Hash 结构记录 `{线程ID: 重入次数}`，与 Java 锁语义一致 |
| 安全解锁 | Lua 脚本判断持有者再删除 |
| 等待唤醒 | 用 Pub/Sub 通知等待线程，避免无脑自旋 |

> ⚠️ **指定了 `leaseTime` 就不会启动看门狗**，业务超时后锁仍会释放。除非你能保证执行时间，否则用 `tryLock(waitTime, unit)`。
>
> ⚠️ **主从架构下的锁丢失问题**：主节点写入锁后未同步到从库就宕机，哨兵提升从库 → 新主节点没有锁 → 两个客户端同时持锁。**RedLock 算法**试图解决，但存在争议（Martin Kleppmann 的经典质疑），且实现复杂、性能差。
>
> **实践的正确答案**：分布式锁只做"降低并发"的第一道防线，**最终一致性要靠数据库唯一索引/乐观锁兜底**。例如下单用 `order_no` 唯一索引，即使锁失效也不会产生重复订单。

### 11.4 幂等 ≠ 锁

```sql
-- 最可靠的幂等：数据库唯一约束
ALTER TABLE orders ADD UNIQUE KEY uk_order_no (order_no);
```

```java
try {
    orderMapper.insert(order);   // 重复插入抛 DuplicateKeyException
} catch (DuplicateKeyException e) {
    return orderMapper.selectByOrderNo(order.getOrderNo());  // 幂等返回已有结果
}
```

> 💡 **锁解决"同时做"，幂等解决"做多次"**。资金、订单类业务两者都要有。

---

## 十二、Spring Boot 集成 Redis ⭐

### 12.1 依赖

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-data-redis</artifactId>
</dependency>
<!-- Lettuce 连接池需要 -->
<dependency>
    <groupId>org.apache.commons</groupId>
    <artifactId>commons-pool2</artifactId>
</dependency>
<!-- 缓存注解 -->
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-cache</artifactId>
</dependency>
<!-- 分布式锁（可选） -->
<dependency>
    <groupId>org.redisson</groupId>
    <artifactId>redisson-spring-boot-starter</artifactId>
    <version>3.37.0</version>
</dependency>
```

### 12.2 application.yml（Spring Boot 3.x）

> ⚠️ **Spring Boot 3.0 起配置前缀从 `spring.redis` 改为 `spring.data.redis`**，老项目升级时别漏改。

```yaml
spring:
  data:
    redis:
      host: 127.0.0.1
      port: 6379
      password: YourStrongPwd!
      database: 0
      timeout: 3s
      lettuce:
        pool:
          max-active: 16      # 最大连接数
          max-idle: 8         # 最大空闲连接
          min-idle: 2         # 最小空闲连接（保证连接可用）
          max-wait: 2s        # 获取连接最大等待时间
        shutdown-timeout: 200ms
  cache:
    type: redis
    redis:
      time-to-live: 30m       # 默认过期时间
      cache-null-values: false
      key-prefix: "demo:cache:"
```

**连接池参数怎么定**：

- `max-active` ≈ 业务线程数 × (平均命令数 / 命令耗时占比)，经验值先给 8~16
- **不是越大越好**：Redis 单线程处理，连接过多只会增加上下文切换
- 必须监控 `lettuce_command_completion_latency`、连接池 active/idle

### 12.3 序列化配置（最容易踩坑的地方）

默认的 `RedisTemplate` 用 **JDK 序列化**，存进去是乱码，且不同语言无法读取。生产必须换成 JSON：

```java
@Configuration
public class RedisConfig {

    @Bean
    public RedisTemplate<String, Object> redisTemplate(RedisConnectionFactory factory) {
        RedisTemplate<String, Object> template = new RedisTemplate<>();
        template.setConnectionFactory(factory);

        StringRedisSerializer keySerializer = new StringRedisSerializer();
        GenericJackson2JsonRedisSerializer valueSerializer =
                new GenericJackson2JsonRedisSerializer();

        template.setKeySerializer(keySerializer);
        template.setHashKeySerializer(keySerializer);
        template.setValueSerializer(valueSerializer);
        template.setHashValueSerializer(valueSerializer);
        template.afterPropertiesSet();
        return template;
    }

    /** 专用于 String（计数器、锁、Token），不经过 JSON 序列化 */
    @Bean
    public StringRedisTemplate stringRedisTemplate(RedisConnectionFactory factory) {
        return new StringRedisTemplate(factory);
    }
}
```

**几个必须知道的点**：

1. `GenericJackson2JsonRedisSerializer` 会写入 `@class` 字段（全限定类名），**反序列化时不依赖泛型**，但：
   - 类改名/挪包后旧缓存无法反序列化
   - 存在反序列化安全风险（不要开放默认类型解析给不可信数据）
2. 存 `LocalDateTime` 需要注册 `JavaTimeModule`，否则报 `InvalidDefinitionException`：

```java
ObjectMapper om = new ObjectMapper();
om.registerModule(new JavaTimeModule());
om.disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS);
om.activateDefaultTyping(LaissezFaireSubTypeValidator.instance,
        ObjectMapper.DefaultTyping.NON_FINAL, JsonTypeInfo.As.PROPERTY);
GenericJackson2JsonRedisSerializer serializer =
        new GenericJackson2JsonRedisSerializer(om);
```

3. **只有 `StringRedisTemplate` 存的 key 是干净的**，用 `RedisTemplate<String, String>` 也一样。排查时 `keys *` 看到 `\xac\xed...` 就是 JDK 序列化没配。
4. Spring Boot 4 / Spring Framework 7 开始默认 Jackson 3（`tools.jackson.*` 包），`GenericJackson2JsonRedisSerializer` 的构造与默认行为有变化，升级时需回归验证序列化兼容性。

### 12.4 常用操作封装

```java
@Component
@RequiredArgsConstructor
public class RedisUtil {

    private final StringRedisTemplate stringRedisTemplate;
    private final RedisTemplate<String, Object> redisTemplate;

    // ---------- String ----------
    public void set(String key, String value, Duration ttl) {
        stringRedisTemplate.opsForValue().set(key, value, ttl);
    }

    public String get(String key) {
        return stringRedisTemplate.opsForValue().get(key);
    }

    public boolean setIfAbsent(String key, String value, Duration ttl) {
        return Boolean.TRUE.equals(
                stringRedisTemplate.opsForValue().setIfAbsent(key, value, ttl));
    }

    public Long increment(String key, long delta) {
        return stringRedisTemplate.opsForValue().increment(key, delta);
    }

    // ---------- Hash ----------
    public void hSet(String key, String field, Object value) {
        redisTemplate.opsForHash().put(key, field, value);
    }

    public Object hGet(String key, String field) {
        return redisTemplate.opsForHash().get(key, field);
    }

    // ---------- ZSet ----------
    public void zAdd(String key, Object member, double score) {
        redisTemplate.opsForZSet().add(key, member, score);
    }

    public Set<Object> zReverseRange(String key, long start, long end) {
        return redisTemplate.opsForZSet().reverseRange(key, start, end);
    }

    // ---------- 通用 ----------
    public boolean expire(String key, Duration ttl) {
        return Boolean.TRUE.equals(redisTemplate.expire(key, ttl));
    }

    public boolean delete(String key) {
        return Boolean.TRUE.equals(redisTemplate.delete(key));
    }

    public Set<String> scan(String pattern, int count) {
        Set<String> keys = new HashSet<>();
        ScanOptions options = ScanOptions.scanOptions().match(pattern).count(count).build();
        try (Cursor<byte[]> cursor = stringRedisTemplate.executeWithStickyConnection(
                connection -> connection.keyCommands().scan(options))) {
            while (cursor != null && cursor.hasNext()) {
                keys.add(new String(cursor.next(), StandardCharsets.UTF_8));
            }
        }
        return keys;
    }
}
```

> ⚠️ **永远不要在生产使用 `keys *`**，它会遍历全部 key 并阻塞单线程。用 `SCAN` 游标分批。上面的 `SCAN` 封装只适合小规模排查，业务代码中慎用。

### 12.5 Spring Cache 注解

```java
@Service
@RequiredArgsConstructor
public class StudentService {

    private final StudentMapper studentMapper;

    @Cacheable(cacheNames = "student", key = "#id", unless = "#result == null")
    public StudentVO getById(Long id) {
        return studentMapper.selectVOById(id);
    }

    @CachePut(cacheNames = "student", key = "#student.id")
    public StudentVO update(StudentDTO student) {
        // 更新 DB 并返回最新对象，同时刷新缓存
        return doUpdate(student);
    }

    @CacheEvict(cacheNames = "student", key = "#id")
    public void delete(Long id) {
        studentMapper.deleteById(id);
    }

    @Caching(evict = {
        @CacheEvict(cacheNames = "student", key = "#id"),
        @CacheEvict(cacheNames = "student:page", allEntries = true)
    })
    public void updateName(Long id, String name) {
        // 删除单条 + 清空列表缓存
    }
}
```

| 注解 | 作用 |
| :--- | :--- |
| `@Cacheable` | 先查缓存，命中直接返回；未命中执行方法并写缓存 |
| `@CachePut` | 每次都执行方法，并把结果写入缓存 |
| `@CacheEvict` | 删除缓存，`allEntries=true` 清空整个 cacheName |
| `@Caching` | 组合多个缓存操作 |

**按 cacheName 设置不同 TTL：**

```java
@Configuration
@EnableCaching
public class CacheConfig {

    @Bean
    public RedisCacheManager cacheManager(RedisConnectionFactory factory) {
        RedisCacheConfiguration defaultConfig = RedisCacheConfiguration
                .defaultCacheConfig()
                .entryTtl(Duration.ofMinutes(30))
                .prefixCacheNameWith("study:cache:")
                .computePrefixWith(cacheName -> "study:cache:" + cacheName + ":")
                .serializeKeysWith(RedisSerializationContext.SerializationPair
                        .fromSerializer(new StringRedisSerializer()))
                .serializeValuesWith(RedisSerializationContext.SerializationPair
                        .fromSerializer(new GenericJackson2JsonRedisSerializer()))
                .disableCachingNullValues();

        Map<String, RedisCacheConfiguration> configs = new HashMap<>();
        configs.put("student", defaultConfig.entryTtl(Duration.ofMinutes(10)));
        configs.put("dict", defaultConfig.entryTtl(Duration.ofHours(24)));
        configs.put("rank", defaultConfig.entryTtl(Duration.ofMinutes(1)));

        return RedisCacheManager.builder(factory)
                .cacheDefaults(defaultConfig)
                .withInitialCacheConfigurations(configs)
                .transactionAware()   // 事务提交后再操作缓存
                .build();
    }
}
```

**`@Cacheable` 的 5 个必踩坑**：

1. **同类内部调用不生效**：`this.getById()` 不走 Spring AOP 代理，注解失效
2. **异常不缓存**：方法抛异常，缓存不会写入（正确行为）
3. **`unless` 与 `condition` 区别**：`condition` 在方法执行前判断是否查缓存；`unless` 在方法执行后判断是否写缓存
4. **缓存穿透**：`disableCachingNullValues()` 时空结果不会缓存，需业务层兜底
5. **缓存一致性**：`@CachePut`/`@CacheEvict` 与事务的顺序问题，建议 `transactionAware()`

### 12.6 多数据源/多实例

```yaml
spring:
  data:
    redis:
      # 多个 Redis 实例：手动定义多个 RedisConnectionFactory + RedisTemplate Bean
```

```java
@Configuration
public class MultiRedisConfig {

    @Bean
    @Primary
    public RedisConnectionFactory cacheConnectionFactory() {
        LettuceConnectionFactory factory =
                new LettuceConnectionFactory("127.0.0.1", 6379);
        factory.afterPropertiesSet();
        return factory;
    }

    @Bean
    public RedisConnectionFactory lockConnectionFactory() {
        LettuceConnectionFactory factory =
                new LettuceConnectionFactory("127.0.0.2", 6379);
        factory.afterPropertiesSet();
        return factory;
    }

    @Bean
    public RedisTemplate<String, Object> lockRedisTemplate(
            @Qualifier("lockConnectionFactory") RedisConnectionFactory factory) {
        RedisTemplate<String, Object> template = new RedisTemplate<>();
        template.setConnectionFactory(factory);
        template.setKeySerializer(new StringRedisSerializer());
        template.setValueSerializer(new StringRedisSerializer());
        template.afterPropertiesSet();
        return template;
    }
}
```

---

## 十三、典型业务实战

### 13.1 登录 Token（替代 Session）

```
key: login:token:{token}
value: {"userId":1001,"role":"STUDENT","loginTime":...}
ttl: 7 天
```

```java
public String login(LoginDTO dto) {
    User user = userMapper.selectByUsername(dto.getUsername());
    if (user == null || !passwordEncoder.matches(dto.getPassword(), user.getPassword())) {
        throw new BizException("用户名或密码错误");
    }
    String token = UUID.randomUUID().toString().replace("-", "");
    LoginUser loginUser = new LoginUser(user.getId(), user.getRole());
    redisTemplate.opsForValue().set(
            "login:token:" + token, loginUser,
            7, TimeUnit.DAYS);
    return token;
}
```

**续期策略**：每次请求刷新 TTL（滑动过期）；或双 Token（access + refresh）。

### 13.2 短信验证码

```java
// 发送
String code = String.format("%06d", ThreadLocalRandom.current().nextInt(1_000_000));
redisTemplate.opsForValue().set("sms:code:" + phone, code, 5, TimeUnit.MINUTES);

// 校验（Lua 保证"比较 + 删除"原子，防止并发重复使用）
String script =
    "local v = redis.call('GET', KEYS[1]) " +
    "if v == ARGV[1] then redis.call('DEL', KEYS[1]) return 1 else return 0 end";
Long ok = redisTemplate.execute(new DefaultRedisScript<>(script, Long.class),
        Collections.singletonList("sms:code:" + phone), inputCode);
```

**配套限流**：同一手机号 60 秒只能发一次（`SET sms:limit:phone 1 NX EX 60`），每天最多 10 次（`INCR` + 过期）。

### 13.3 排行榜（ZSet）

```java
public void addScore(Long studentId, double mark) {
    redisTemplate.opsForZSet().add("rank:student", studentId, mark);
}

public List<RankVO> topN(int n) {
    return redisTemplate.opsForZSet()
            .reverseRangeWithScores("rank:student", 0, n - 1)
            .stream()
            .map(t -> new RankVO((Long) t.getValue(), t.getScore()))
            .toList();
}

public Long myRank(Long studentId) {
    Long rank = redisTemplate.opsForZSet()
            .reverseRank("rank:student", studentId);
    return rank == null ? null : rank + 1;   // 转成 1 开始的自然排名
}
```

> 💡 排行榜数据量大时，**只保留 TopN**：`ZREMRANGEBYRANK key 0 -(N+1)`。

### 13.4 接口限流（固定窗口）

```java
public boolean tryAcquire(String api, Long userId, int limit, int seconds) {
    String key = "limit:" + api + ":" + userId;
    Long count = redisTemplate.opsForValue().increment(key);
    if (count != null && count == 1) {
        redisTemplate.expire(key, Duration.ofSeconds(seconds));
    }
    return count != null && count <= limit;
}
```

> ⚠️ 固定窗口在窗口边界可能出现 **2 倍流量**（最后一秒 + 第一秒），要求严格用滑动窗口（Lua + ZSet，见 7.2）。

### 13.5 购物车（Hash）

```java
public void addCart(Long userId, Long productId, int num) {
    redisTemplate.opsForHash().increment("cart:" + userId,
            productId.toString(), num);
}

public Map<Object, Object> listCart(Long userId) {
    return redisTemplate.opsForHash().entries("cart:" + userId);
}

public void removeCart(Long userId, Long productId) {
    redisTemplate.opsForHash().delete("cart:" + userId, productId.toString());
}
```

### 13.6 分布式 Session（Spring Session Redis）

```xml
<dependency>
    <groupId>org.springframework.session</groupId>
    <artifactId>spring-session-data-redis</artifactId>
</dependency>
```

```yaml
spring:
  session:
    store-type: redis
    timeout: 30m
    redis:
      namespace: "study:session"
```

多实例部署时，用户请求打到任意一台都能拿到同一个 Session。

### 13.7 防止重复提交

```java
// 前端请求带 requestId，后端用 SET NX 做幂等
String key = "idempotent:" + requestId;
if (!Boolean.TRUE.equals(redisTemplate.opsForValue()
        .setIfAbsent(key, "1", 5, TimeUnit.MINUTES))) {
    throw new BizException("请勿重复提交");
}
try {
    doSubmit(request);
} catch (Exception e) {
    redisTemplate.delete(key);    // 业务失败允许重试
    throw e;
}
```

---

## 十四、运维、监控与安全

### 14.1 常用排查命令

```bash
INFO                              # 全量信息
INFO memory                       # 内存
INFO stats                        # 命中率、连接数、命令统计
INFO replication                  # 主从状态
INFO keyspace                     # 各库 key 数量

SLOWLOG GET 10                    # 最近 10 条慢查询
SLOWLOG LEN
SLOWLOG RESET

CLIENT LIST                       # 当前连接
CLIENT KILL ID 12345              # 杀掉异常连接

LATENCY DOCTOR
redis-cli --latency -h 127.0.0.1  # 网络延迟
redis-cli --intrinsic-latency 100 # Redis 自身延迟
redis-cli --stat                  # 实时 QPS
```

**关键指标**：

| 指标 | 健康值 | 异常含义 |
| :--- | :--- | :--- |
| `keyspace_hits / (hits + misses)` | > 90% | 命中率低 → 缓存设计或 TTL 有问题 |
| `used_memory / maxmemory` | < 80% | 接近上限 → 频繁淘汰或 OOM |
| `connected_clients` | 稳定 | 暴涨 → 连接泄漏 |
| `blocked_clients` | 接近 0 | 有阻塞命令 |
| `rejected_connections` | 0 | 连接数打满 |
| `latest_fork_usec` | < 100ms | fork 太慢 → 大内存实例持久化卡顿 |
| `used_cpu_sys` | 稳定 | 突增 → 慢查询/大 key |

> ⚠️ `KEYS`、`FLUSHALL`、`FLUSHDB`、`SAVE`、`CONFIG SET`、`DEBUG` 等命令生产必须限制：

```conf
rename-command KEYS ""
rename-command FLUSHALL ""
rename-command FLUSHDB ""
rename-command CONFIG ""
```

> 💡 7.0+ 更推荐用 ACL 控制命令权限，`rename-command` 会让客户端工具也变难用。

### 14.2 监控接入

- 云 Redis：直接用云监控（命中率、慢日志、大 key 分析）
- 自建：Prometheus + `redis_exporter` + Grafana（Dashboard ID 763）
- 告警：内存 > 80%、命中率 < 80%、主从延迟 > 5s、连接数 > 80%、慢查询增长

### 14.3 安全检查清单

- [ ] 绑定内网 IP，安全组只放行应用服务器
- [ ] 设置强密码 / 使用 ACL 最小权限
- [ ] 禁用/重命名危险命令
- [ ] 不使用的端口不暴露（如 Sentinel 26379 也要保护）
- [ ] 定期备份 RDB/AOF
- [ ] 升级已知漏洞版本

---

## 十五、常见坑清单

| # | 坑 | 现象 | 正确做法 |
| :--- | :--- | :--- | :--- |
| 1 | `SET` 覆盖后 TTL 丢失 | key 永不过期，内存上涨 | 用 `SET ... KEEPTTL` 或重设 TTL |
| 2 | `keys *` 线上执行 | Redis 卡死、其他请求超时 | 用 `SCAN` |
| 3 | 大 Hash `HGETALL` | 单次返回几十 MB，阻塞 | `HSCAN` 分批 |
| 4 | `volatile-lru` 但 key 没 TTL | 内存满后写入报 OOM | 统一加 TTL 或换 `allkeys-lru` |
| 5 | 分布式锁 `DEL` 未校验持有者 | 误删他人锁 | Lua 比较再删 |
| 6 | 锁无过期时间 | 宕机后死锁 | `NX EX` |
| 7 | 业务时间 > 锁时间 | 并发进入 | Redisson 看门狗 |
| 8 | 缓存和 DB 双写不一致 | 读到旧数据 | 删缓存而非更新缓存 + 最终一致 |
| 9 | 大量 key 同时过期 | 数据库被打挂 | TTL 加随机 |
| 10 | `@Cacheable` 自调用 | 注解不生效 | 拆类或注入自身代理 |
| 11 | Cluster 下 `MGET` 跨 slot | `CROSSSLOT` 报错 | hash tag `{id}` |
| 12 | 用 `userId` 当 Bitmap offset | 内存爆炸 | 映射为连续小整数 |
| 13 | 连接池 `max-active` 过大 | 上下文切换、超时 | 压测后定值，监控连接池 |
| 14 | 用 List 做核心队列 | 消息丢失、无重试 | Stream / MQ |
| 15 | 反序列化失败 | 类改包后旧缓存报错 | 固定 DTO 包路径，或加版本前缀 |
| 16 | `repeatSubmit` 锁粒度太大 | 正常请求被拒 | 锁 key 精确到用户 + 业务 ID |
| 17 | 忘记 `commons-pool2` | Lettuce 连接池配置不生效 | 显式引入依赖 |
| 18 | 主从延迟读到旧值 | 写后立刻读不一致 | 写后短时间读主库 |
| 19 | `TTL` 返回 -2 以为是 -1 | 判断逻辑错误 | -1 永不过期，-2 不存在 |
| 20 | Lua 脚本太复杂 | Redis 阻塞 | 脚本只做原子判断与修改 |

---

## 十六、新版本补充

- **Redis 7.0**：Redis Functions（服务端脚本库，替代 EVAL 的演进方向）、Multi-Part AOF、Sharded Pub/Sub（减少 Cluster 广播）、ACL 增强。
- **Redis 7.2/7.4**：Hash 字段级过期（`HEXPIRE`/`HTTL`/`HPERSIST`）、`HSCAN NOVALUES`（只扫字段名）、`WAITAOF`（等待 AOF 落盘）。
- **Redis 8.0**：Hash 字段过期 GA、Vector Set（向量相似度检索，AI 场景）、新增 JSON/时间序列/布隆过滤器等模块能力整合进发行版。
- **客户端生态**：Spring Boot 3 默认 **Lettuce**（Netty，线程安全、支持异步/响应式）；Jedis 轻量但非线程安全（需连接池）。Spring Boot 4 起与 Jackson 3 的兼容需回归序列化逻辑。

---

## 📌 在 Spring Boot 中

| 本篇概念 | Spring Boot 中的对应 |
| :--- | :--- |
| 连接配置 | `spring.data.redis.*` + `RedisConnectionFactory` 自动配置 |
| String 操作 | `StringRedisTemplate` / `RedisTemplate.opsForValue()` |
| Hash/List/Set/ZSet | `opsForHash()` / `opsForList()` / `opsForSet()` / `opsForZSet()` |
| 事务 | `redisTemplate.execute(SessionCallback)` / `setEnableTransactionSupport(true)` |
| Lua | `DefaultRedisScript` + `redisTemplate.execute()` |
| 缓存 | `@Cacheable` / `@CachePut` / `@CacheEvict` + `RedisCacheManager` |
| 分布式锁 | Redisson `RLock`（推荐）或 `setIfAbsent` 手写 |
| Session 共享 | `spring-session-data-redis` |
| 限流 | 自己封装 Lua，或 Sentinel/Resilience4j + Redis 存储 |
| 多级缓存 | Caffeine + Redis，用 Pub/Sub 广播失效 |
| 消息 | `StreamMessageListenerContainer` / `RedisMessageListenerContainer` |

**和本仓库其他文档的关系**：

- 第 6 章《事务与隔离级别》→ Redis 的"事务"只是命令批处理，别和关系型事务混淆
- [MySQL 学习文档](MySQL学习文档.md) → 缓存的数据源，缓存一致性要和事务一起考虑
- [JDBC](JDBC.md) / [15-数据库操作_MyBatis](../Spring实战/15-数据库操作_MyBatis.md) → 缓存层通常包在 Mapper/Service 之上
- [51-分布式限流_RateLimitRedis](../Spring实战/51-分布式限流_RateLimitRedis.md) → 本章限流部分的工程化展开
- [19-Redis缓存_CacheRedis](../Spring实战/19-Redis缓存_CacheRedis.md) → Spring Cache 注解的完整模块示例

> 一句话：**Redis 不是"加个缓存就快了"，而是一套需要设计 TTL、容量、淘汰策略、失效策略和降级方案的系统组件。** 写得进不难，线上不炸才难。

---

## 本章小结

本篇从 Redis 的定位讲到落地：

1. **数据类型选择**决定了代码质量：对象用 String/Hash，排行榜用 ZSet，去重用 Set/Bitmap，可靠消息用 Stream。
2. **过期与淘汰**要分清：过期是"删 key 的逻辑"，淘汰是"内存不够时的取舍"，`volatile-*` 策略在 key 无 TTL 时会退化。
3. **持久化**是"丢多少数据"的选择题：缓存可以只开 RDB，重要数据用 AOF `everysec` + 主从。
4. **缓存三大问题**（穿透/击穿/雪崩）是线上高频故障，方案要按业务选，不要无脑套模板。
5. **一致性**只能做到最终一致，删除缓存 + 兜底（唯一索引/消息补偿）比追求强一致更实际。
6. **分布式锁**首选 Redisson，且永远记住"锁不能替代幂等"。
7. **Spring Boot 集成**的核心是序列化和连接池，配置错了两者都会以"线上偶发超时/乱码"的形式惩罚你。

**动手练习**：

1. 用 Docker 起一个 Redis，完成 String/Hash/List/Set/ZSet 各 3 个命令的实操。
2. 用 ZSet 实现"班级成绩排行榜"，支持 Top10、我的排名、按分数段统计人数。
3. 用 Lua 实现"库存扣减"，并用 JMeter/ab 压测验证不会超卖。
4. 用 Spring Boot + Redisson 实现分布式锁，模拟 10 个线程抢同一订单，验证只有一个成功。
5. 复现缓存穿透（查不存在的 ID），分别用"空值缓存"和"布隆过滤器"解决，对比效果。
6. 用 `@Cacheable` 给某个查询接口加缓存，通过日志验证第二次请求没有查数据库。
