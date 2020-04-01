# Map 接口

Collection 接口中的集合元素都是孤立存在的，称为单列集合。

Map 接口中的集合元素是成对存在的，称为双列集合。

Map 接口不能包含重复的键，值可以重复；每个键只能对应一个值。

Map 接口中常用方法：

`public V put(K key, V value)`:  把指定的键与指定的值添加到 Map 集合中。

`public V remove(Object key)`: 把指定的键所对应的键值对元素 在 Map 集合中删除，返回被删除元素的值。

`public V get(Object key)`: 根据指定的键，在 Map 集合中获取对应的值。

`boolean containsKey(Object key)`: 判断集合中是否包含指定的键。

`public Set<K> keySet()`: 获取 Map 集合中所有的键，存储到 Set 集合中。

`public Set<Map.Entry<K,V>> entrySet()`: 获取到 Map 集合中所有的键值对对象的集合(Set集合)。

键值对对象 Map.Entry 对象中的方法:

`K getKey()`: 返回与此项对应的键。

`V getValue()`: 返回与此项对应的值。

```java
public class MapTest {
  public static void main(String[] args) {
    // 创建 Map 集合，使用多态
    Map<String, Integer> map = new HashMap<>();

    // put 添加键值对，若 key 重复，返回被替换的 value，否则返回的是 null
    map.put("Leo", 30);
    map.put("Amy", 23);
    map.put("Van", 34);
    map.put("Rex", 23);
    map.put("Joy", 43);
    System.out.println(map.put("Leo", 32)); // 返回被替换的 value
    System.out.println(map); // 重写了 toString

    // get 通过指定的 key 获取对应的 value
    System.out.println(map.get("Leo"));

    // containsKey 判断集合是否包含指定的 key
    System.out.println(map.containsKey("Leo"));

    // remove 删除 key 指定的元素，若 key 存在，返回 value，否则返回 null
    System.out.println(map.remove("Van"));

    // KeySet 把 Map 中的 key 取出来 存储在 Set 中
    Set<String> keys = map.keySet();

    // 通过迭代器遍历
    Iterator<String> it = keys.iterator();
    while (it.hasNext()) {
      System.out.println("key: " + it.next() + ", value: " + map.get(it.next()));
    }

    // 通过增强 for 遍历
    for (Object key : map.keySet()) {
      System.out.println("key: " + key + ", value: " + map.get(key));
    }

    // entrySet 把 Map 中的 Entry 对象(键值对对象)存储到 Set 集合中
    Set<Map.Entry<String, Integer>> entries = map.entrySet();
    System.out.println("使用 Map.Entry 对象遍历 Map");
    for (Map.Entry<String, Integer> entry : entries) {
      System.out.println("key: " + entry.getKey() + ", value: " + entry.getValue());
    }
  }
}
```

`java.util.HashMap<k, v> 集合  implements Map<k, v> 接口`

HashMap 哈希表底层是数组 + 单向链表/红黑树，查询速度快。

HashMap 是一个无序集合，存储元素和取出元素的顺序可能不一致。

HashMap 存储自定义类型键值，必须重写 hashCode 方法和 equals 方法

```java
public class MapTest {
  public static void main(String[] args) {
    testHashMap01();
    testHashMap02();
  }
  public static void testHashMap01() {
    // HashMap 存储自定义类型键值
    // key: String 类型，已经重写了 hashCode 和 equals 方法
    // value: Person 类型。可以重复
    HashMap<String, Person> map = new HashMap<>();
    map.put("武汉", new Person("Leo", 20));
    map.put("上海", new Person("Eve", 23));
    map.put("广州", new Person("Van", 34));
    map.put("重庆", new Person("Rex", 30));
    // 遍历 Map 集合
    for (String k : map.keySet()) {
        Person p = map.get(k);
        System.out.println(k + "-->" + p);
    }
  }
  public static void testHashMap02() {
    // HashMap 存储自定义类型键值
    // key: Person 类型，必须重写 hashCode 和 equals
    // value: String 类型，可以重复
    HashMap<Person, String> map = new HashMap<>();
    map.put(new Person("Leo", 20), "武汉");
    map.put(new Person("Rex", 24), "北京");
    map.put(new Person("Van", 30), "杭州");
    map.put(new Person("Leo", 20), "成都"); // key 重复会替换原来的value
    // 使用 entrySet() 和 增强 for 遍历 Map
    Set<Map.Entry<Person, String>> entries = map.entrySet();
    for (Map.Entry<Person, String> entry : entries) {
        System.out.println(entry.getKey() + "-->" + entry.getValue());
    }
  }
}
```

`java.util.LinkedHashMap 集合 extends HashMap<k, v> 集合`

LinkedHashMap 底层是哈希表 + 链表。

LinkedHashMap 是一个有序集合。

```java
public class MapTest {
  public static void main(String[] args) {
    // hashMap 是无序集合，存和取的顺序可能不一致
    HashMap<String, String> hashMap = new HashMap<>();
    hashMap.put("A", "aaa");
    hashMap.put("C", "ccc");
    hashMap.put("B", "bbb");
    System.out.println(hashMap);

    // LinkedHashMap 存和取的顺序一致
    LinkedHashMap<String, String> linkedHashMap = new LinkedHashMap<>();
    linkedHashMap.put("A", "aaa");
    linkedHashMap.put("C", "ccc");
    linkedHashMap.put("B", "bbb");
    System.out.println(linkedHashMap);
  }
}
```
