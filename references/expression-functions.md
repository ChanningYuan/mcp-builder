# express 表达式函数全集

映射类型 `express`（见 `mapping-rules.md §4`）的可用函数完整目录：**7 组 82 个**（平台函数目录全量导出）。

> **什么时候查这份**：`mapping-rules.md §4` 列了「API→MCP」日常够用的几个（身份换算 / GET / COALESCE / IF / CONCATENATE）。只有要做**复杂数据变换**（日期计算、集合运算、数学、字符串处理）才来翻这份全集。绝大多数建工具场景用不到。
>
> ⚠️ 写法：表达式放 `expression` 字段（见 mapping-rules §4）。变量引用：工具入参 `${@("node_start/$/<key>")}`、系统参数对象 `${@("system_node/$")}`；字面量字符串用单引号。函数可任意嵌套（变量进函数、函数套函数、三层嵌套均实证可用）。
>
> ⚠️ 存量工具 rules 里偶见的 `USERID2UIDBYCORPID` / `CORPID2ORGID` **不在本目录**——那是平台「推荐映射」自动注入的内部函数，不是用户可选目录函数。本目录的身份换算只有「系统函数」组那 4 个（unionId 互转）。

## 实测结论（72 用例回显后端全量验证）

**序列化形态（映射到 string 参数时）**：
1. boolean → `true`/`false` 小写串；number → 数字串，**double 运算结果带 `.0`**（如 `POWER(2,3)`→`8.0`，严格要整数串套 `INT()`/`TEXT()`）；
2. **date → 毫秒时间戳串**（要人读格式必须套 `DATEFORMAT(…,'yyyy/MM/dd HH:mm:ss')`）；
3. **collection 直接映射会丢数据**（LIST/SPLIT/FOREACH/REPEAT 直出只剩第一个元素）——**先 `JOIN(…,sep)` 成字符串再映射**（`JOIN(SPLIT(csv,','),'-')`→`x-y-z` ✅）；
4. `deapRunId` 等会话类系统参数在 **debug 场景为 null**（非真实 agent 会话），属预期。

**下表 3 处文档瑕疵（实测纠正）**：`NE(1,2)` 实际=true（示例笔误）；`ISEMPTY(' ')` 实际=false（纯空格不算空，判空格串用 `ISEMPTY(TRIM(x))`）；`JOIN` 的示例把函数名误写成 GET（按签名 `JOIN(collection,sep)` 用即可）。

## 目录（按组）
- 集合函数（10）· 日期函数（13）· 逻辑函数（14）· 数学函数（15）· 字符串函数（21）· JSON 函数（5）· 系统函数（4）

### 集合函数（10）

| 函数 | 参数 | 返回 | 说明 |
|------|------|------|------|
| `IN` | any, collection | boolean | IN(ele,collection) 判断元素是否位于集合中<br>例：IN('选项 1', LIST('选项 1','选项 2')) 的结果为 true |
| `INTER` | collection, dynamic:collection | collection | INTER(collection1,collection2) 计算两个集合的交集<br>例：INTER(LIST(1,2,3),LIST(2,3,5,6)) 的结果是 LIST(2,3) |
| `SUPPLE` | collection, dynamic:collection | collection | SUPPLE(collection1,collection2) 计算两个集合的补集<br>例：SUPPLE(LIST(1,2,3,4),LIST(3,4)) 的结果是 LIST(1,2) |
| `LIST` | dynamic:any | collection | LIST(ele1, ele2, ...) 生成一个由 ele1 ele2 ... 组成的集合<br>例：LIST('选项1','选项2') |
| `UNION` | collection, dynamic:collection | collection | UNION(collection1,collection2) 计算两个集合的并集<br>例：UNION(LIST(1,2),LIST(3,4)) 的结果是 LIST(1,2,3,4) |
| `COALESCE` | any, dynamic:any | any | COALESCE(ele1,ele2,...) 返回第一个不为空的元素<br>例：COALESCE(null,null,1,null,2) 的结果是 1 |
| `LISTITEM` | collection, number | any | LISTITEM(list,index) 获取 list index 位置的元素,下标从 1 开始<br>例：LISTITEM(LIST(1,2,3),2) 的结果为 2 |
| `SIZE` | collection | number | SIZE(list) 返回集合的大小<br>例：SIZE(LIST(1,2,3)) 的结果为 3 |
| `FOREACH` | collection, any | collection | FOREACH(list, func(_)) 对list中每个元素应用第2个参数中的运算，得到一个新的list；其二个参数用 _ 代表list中的单个元素<br>例：FOREACH(LIST(1,2,3),_*2) 对 list 中的每个元素乘2，结果是 LIST(2,4,6); FOREACH(LIST('aaa','bb','c'),LEN(_)) 对 list 中每个元素求长度，的结果是 LIST(3,2,1) |
| `REPEAT` | number, any | collection | REPEAT(number,item) 构建一个将 item 重复 number 次的列表<br>例：REPEAT(3,'a') 的结果为 LIST('a','a','a') |

### 日期函数（13）

| 函数 | 参数 | 返回 | 说明 |
|------|------|------|------|
| `DATEDELTA` | date, number, dynamic:string | date | DATEDELTA(date, deltadays) 将指定日期加/减指定天数,正数为增加，负数为减少<br>例：DATEDELTA(date, 1) date日期加一天；DATEDELTA(date, - 1) date日期减一天 |
| `DATEDIF` | date, date, dynamic:string | number | DATEDIF(startDate, endDate, [unit]) 计算两个时间的差值； startDate 必需。 一个代表开始时间的日期；endDate 必需。 一个代表结束时间的日期；Unit 可选。一个可选参数，默认为 “d”，可以是 “y” 、“M”、“d”、“h”、“m”、“s” ，分别代表计算两个日期相差的年数、月数、天数、小时数、分钟数、秒数。（区分大小写，大写M代表月，小写m代表分。）<br>例：DATEDIF('2020-01-01','2020-01-02','d') 结果是 1 |
| `DATE` | string | date | DATE(string \| number) 获得给定字符串代表的日期或给定时间戳代表的日期，支持yyyy-MM-dd HH:mm:ss、yyyy-MM-dd HH:mm、yyyy-MM-dd HH、yyyy-MM-dd类型的字符串，以及时间戳<br>例：DATE('2020-12-28 11:11:00') 返回该字符串代表的日期，DATE(1694586359000) 返回该时间戳代表的日期 |
| `DAY` | date | number | DAY(date) 返回某日期的天数。 天数是介于 1 到 31 之间的整数。<br>例：DAY('2020-01-02') 的结果是 2 |
| `HOUR` | date | number | HOUR(date) 返回某日期的小时数。<br>例：HOUR('2020-12-09 11:03:04') 的结果是 11 |
| `MINUTE` | date | number | MINUTE(date) 返回某日期的分钟数。<br>例：MINUTE('2020-12-09 12:03:04') 的结果是3 |
| `MONTH` | date | number | MONTH(date)返回某日期的月份。 月份是介于 1 到 12 之间的整数。<br>例：MONTH('2020-12-09 11:03:04') 的结果是12 |
| `NETWORKDAYS` | date, date, dynamic:date | number | NETWORKDAYS(startDate,endDate,[holidays]) 返回参数 start_date 和 end_date 之间完整的工作日数值。 工作日不包括周末和 holidays 指定的假期。<br>例：NETWORKDAYS('2020-12-26', '2021-01-01'， '2020-01-01') 的结果是 4 |
| `NOW` |  | date | NOW() 返回当前时间。<br>例：NOW() |
| `SECOND` | date | number | SECOND(date) 返回某日期的秒数。<br>例：SECOND('2021-01-12 12:23:32') 返回32 |
| `TIMESTAMP` | date | number | TIMESTAMP(date) 将日期对象转换成时间戳，单位毫秒。<br>例：TIMESTAMP('2020-12-23 12:23:34') 返回 1608697414000 |
| `YEAR` | date | number | YEAR(date) 返回某日期的年份。<br>例：YEAR('2020-12-09') 的结果是2020 |
| `DATEFORMAT` | date, string | string | DATEFORMAT(date,format) 将日期格式化为指定类型。<br>例：DATEFORMAT(NOW(),'yyyy/MM/dd HH:mm:ss') 的结果是 2020/01/02 17:02:30(依据当前时间)。 |

### 逻辑函数（14）

| 函数 | 参数 | 返回 | 说明 |
|------|------|------|------|
| `AND` | boolean|collection, dynamic:boolean | boolean | AND(logic1, logic2..) 只要有一个参数是false就返回false，所有参数都为true才返回true; 集合参数会被自动展开成多个参数<br>例：AND(true,false,true) 的结果是 false; AND(LIST(true,false,true)) 的结果也是 false |
| `EQ` | any, any | boolean | EQ(value1, value2),如果value1和value2的值相等，则为true，否则为false<br>例：EQ('aa', 'aa') 和 EQ(1,1) 的结果为 true |
| `FALSE` |  | boolean | FALSE() 返回false<br>例：FALSE() |
| `GE` | number|date, number|date | boolean | GE(value1, value2) 如果 value1 大于等于 value2 返回 true，反之则返回 false<br>例：GE(2, 1) 和 GE(1, 1) 的结果都是 true |
| `GT` | number|date, number|date | boolean | GT(value1,value2) 如果 value1 大于 value2 则返回 true，反之返回 false<br>例：GT(2,1) 的结果为 true |
| `IF` | boolean, any, any | any | IF(logic, value1, value2) 如果logic为true，则返回value1， 否则返回value2<br>例：IF(70>=60, '及格', '不及格') 的结果是 及格 |
| `ISEMPTY` | any | boolean | ISEMPTY(param) 参数如果为空，则返回为true，反之则返回false<br>例：ISEMPTY(' ') 的结果为 true |
| `LE` | number|date, number|date | boolean | LE(value1, value2) 如果 value1 小于等于 value2 则返回true，反之返回false<br>例：LE(1,2) 和 LE(1,1) 的结果都为 true |
| `LT` | number|date, number|date | boolean | LT(value1,value2) 如果 value1 小于 value2 则返回 true，反之返回 false<br>例：LT(1,2) 的结果为 true |
| `NE` | any, any | boolean | NE(value1, value2) 如果value1和value2的值不相等，则返回为true，否则返回false<br>例：NE(1,2) 的结果为 false |
| `NOT` | boolean | boolean | NOT(logic) 返回参数的取反，如果参数是true,则返回false ，如果参数是false，则返回true<br>例：NOT(true) 的结果为 false |
| `OR` | boolean|collection, dynamic:boolean | boolean | OR(logic1, logic2..) 只要有一个参数是true就返回true，所有参数都为false才返回false; 集合参数会被自动展开成多个参数<br>例：OR(true,false) 的结果是 true; OR(LIST(true,false)) 的结果是 true |
| `TRUE` |  | boolean | TRUE() 返回true<br>例：TRUE() |
| `XOR` |  | boolean | XOR(logic1, logic2) 异或运算，如果两个参数不一样则返回true，如果两个参数一样则返回false<br>例：XOR(true, true) 的结果为 false |

### 数学函数（15）

| 函数 | 参数 | 返回 | 说明 |
|------|------|------|------|
| `ABS` | number | number | ABS(number) 返回数字的绝对值<br>例：ABS(-123.456) 的结果为123.456 |
| `AVERAGE` | number, dynamic:number | number | AVERAGE(number1, number2, ...) 求数字的平均值<br>例：AVERAGE(1,2) 的结果为 1.5 |
| `CEILING` | number, number | number | CEILING(number, significance) 返回将参数 number 向上舍入（沿绝对值增大的方向）为最接近的指定基数的倍数。<br>例：CEILING(22.43, 2) 向上取整到2的倍数， 所以返回24 |
| `FIXED` | number, number | number | FIXED(number) 将数字向下舍入到指定的小数位数。<br>例：FIXED(10.8963, 2) 返回的结果是10.89 |
| `INT` | number | number | INT(number)将数字向下舍入到最接近的整数。<br>例：INT(3.45) 返回3；INT(-3.45) 返回-4 |
| `MAX` | number|collection, dynamic:number | number | MAX(number1, number2, ...) 获取这组数字中的最大值。<br>例：MAX(1, 4, 6.7, 10, 2) 返回10 |
| `MIN` | number|collection, dynamic:number | number | MIN(number1, number2, ...) 返回数组中的最小值。<br>例：MIN(1, 3, 5, 7, 2, 4) 返回1 |
| `MOD` | number, number | number | MOD(number, divisor) 返回两数相除的余数。<br>例：MOD(37, 6) 返回值为1 |
| `PI` |  | number | PI() 返回圆周率3.14159265358979323846。<br>例：计算半径长为r的圆的面积 PI() * POWER(r, 2) 如果r=1，那么返回3.14159265358979323846 |
| `POWER` | number, number | number | POWER(number, power) 返回数字乘幂的结果。<br>例：POWER(2, 2) 的结果是 4。 |
| `PRODUCT` | number, dynamic:number | number | PRODUCT(number1, number2...) 函数将所有参数相乘并返回乘积。<br>例：PRODUCT(2, 3) 的结果是 6。 |
| `RAND` |  | number | RAND() 返回大于等于 0 且小于 1 的均匀分布随机实数。每一次触发计算都会变化。<br>例：RAND() 的结果是 0.601931207820683。 |
| `ROUND` | number, number | number | ROUND(number, numDigits) 将数字四舍五入到指定的位数。<br>例：ROUND(1.2345, 2) 返回1.23；ROUND(12345, 2) 返回12345 |
| `SUM` | number|collection, dynamic:number | number | SUM(number1, number2...) 函数将所有参数求和并返回。集合参数会被自动展开成多个参数<br>例：SUM(1.23, 1.45, 100) 返回102.68; SUM(LIST(1,2,3,4,5)) 的结果是 15 |
| `NUMRANGE` | number, number, number, dynamic:string | boolean | NUMRANGE(number,start,end,[mode]) 判断 number 是否在区间中，默认情况下区间包含 start 和 end。mode 可选，包括 'closed'（两侧闭区间）'open'（两侧开区间） 'leftOpen'（左侧开区间,右侧闭区间） 'rightOpen'（左侧闭区间,右测开区间）, 默认是 'closed'<br>例：NUMRANGE(2,2,3) 的结果为 true,NUMRANGE(2,2,3,'leftOpen') 的结果为 false。 |

### 字符串函数（21）

| 函数 | 参数 | 返回 | 说明 |
|------|------|------|------|
| `CONCATENATE` | any, dynamic:any | string | CONCATENATE(text1, text2, text3...) 将多个字符串类型的参数拼接后返回。<br>例：CONCATENATE('A', 'B') 的结果为 'AB' |
| `CONTAIN` | string, string | boolean | CONTAIN(text1, text2) 判断 text1 是否包含 text2。<br>例：CONTAIN('text1', 'text') 的结果为 true。 |
| `EXACT` | string, string | string | EXACT(text1, text2) 判断字符串是否完全相等，如果相等，则返回true，如果不相等，则返回false，区分大小写。<br>例：EXACT('abc', 'Abc') 返回false。 |
| `LEFT` | string, number | string | LEFT(text, number)从一个文本字符串的第一个字符开始返回指定个数的字符，如果字符个数不足，则抛出异常。<br>例：LEFT('abcd', 2) 返回 'ab' |
| `LEN` | string | number | LEN(text) 返回字符串长度。<br>例：LEN('abc') 的结果为 3 |
| `LOWER` | string | string | LOWER(text) 将参数中的所有字母转换成小写字母返回。<br>例：LOWER('AbCd') 的结果是 'abcd' |
| `MID` | string, number, number | string | MID(text, start, length) 返回文本字符串中从指定位置开始的特定数目的字符。<br>例：MID('abcdefgh', 2, 3) 从位置2的地方返回3个字符，即 'bcd' |
| `REPLACE` | string, number, number, string | string | REPLACE(oldText, startNum, numChars, newText) 将oldText的从startNum开始的numChars个字符替换成newText,startNum从1开始。<br>例：REPLACE('12345678', 2, 3, 'ABCD') 结果是1ABCD5678 |
| `REPT` | string, number | string | REPT(text, numberTimes) 将text重复numberTimes次数后返回。<br>例：REPT('ABC', 2) 的结果是 'ABCABC'。 |
| `RIGHT` | string, number | string | RIGHT(text, numChar) 返回文本值中最右边的 numChar 个字符。<br>例：RIGHT('12345', 2) 的结果为 '45'。 |
| `SPLIT` | string, string | collection | SPLIT(text, textSeparator) 将字符串分割。<br>例：SPLIT('ABABAB', 'B') 的结果为 LIST('A','A','A')。 |
| `STARTWITH` | string, string | boolean | STARTWITH(text1, text2) 判断文本字符串是否以特定字符串开始。<br>例：STARTWITH('ABCDEF', 'ABC') 返回true。 |
| `TEXT` | any, dynamic:string | string | TEXT(number) 将其他类型数据转换为文本; TEXT(null) 的结果是空字符串;TEXT(number,string)将时间戳转换为对应日期格式的文本;TEXT(Date,string)将日期格式转换为对应日期格式的文本<br>例：TEXT(12) 的结果是 '12'。TEXT(1608697414000,'yyyy') 的结果是 '2020'。TEXT(DATE('2020-12-28 11:11:00'),'yyyy')的结果是 '2020'。 |
| `TRIM` | string | string | TRIM(text) 删除字符串首尾的空格。<br>例：TRIM(' ABCD ') 返回的结果是 'ABCD'。 |
| `UPPER` | string | string | UPPER(text) 将文本字符串中的所有小写字母转换成大写字母。<br>例：UPPER('AbCd') 返回结果是 'ABCD'。 |
| `VALUE` | string | number | VALUE(text) 将文本转化成数字。<br>例：VALUE('123') 的结果为 123。 |
| `GETUUID` |  | string | GETUUID() 生成一个 UUID 字符串。<br>例：GETUUID() 的结果是 1d6b3482-c9c3-41ef-a4c4-a7e634bfd205 (每次结果不一样)。 |
| `MD5` | string | string | MD5(text) 对一段文本进行 MD5 摘要，结果是一个128位散列值的16进制小写字符串表示。<br>例：MD5('test') 的结果是 098f6bcd4621d373cade4e832627b4f6。如果想要大写16进制的话可以使用 UPPER(MD5('test')), 它的结果是 098F6BCD4621D373CADE4E832627B4F6。需要注意的是如果你一不小心传入了null，MD5(null)的结果为空字符串 |
| `JOIN` | collection, string | string | JOIN(list, delimiter) 将数组列表转换为由delimiter分割的字符串<br>例：GET(LIST(1,2,3), ',') 返回的结果是 '1,2,3' |
| `TEXTREPLACE` | string, string, string | string | TEXTREPLACE(string, string, string) 将参数1里与参数2相匹配的字符替换成参数3<br>例：TEXTREPLACE('ABBC','B','b') 返回的结果是 'AbbC' |
| `UNESCAPEHTML` | string | string | UNESCAPEHTML(string), 根据org.apache.commons.lang3.StringEscapeUtils.unescapeHtml4对HTML编码后的字符串进行解码<br>例：UNESCAPEHTML('{&quot;AgentId&quot;:23452345345&quot;'),结果为{'AgentId':23452345345} |

### JSON函数（5）

| 函数 | 参数 | 返回 | 说明 |
|------|------|------|------|
| `JSONPARSE` | string | any | JSONPARSE(jsonString) 转换json字符串为json对象<br>例：JSONPARSE(" { 'key' : 'value' } ") 等价于 {'key' : 'value'} |
| `GET` | string, any | any | GET(key, jsonObj) 获取jsonObj对应的Value值, 主要是应对key为特殊字符，无特殊字符可直接使用.取值<br>例：GET('key-1', {'key-1':'value'}) 返回的结果是 'value' |
| `JACKSONJSONPATHEVAL` | any, string | any | JACKSONJSONPATHEVAL(object,jsonpath), 根据依赖jackson包的jsonpath从对象中取值,jsonpath参考https://jsonpath.com/<br>例：JACKSONJSONPATHEVAL(LIST(1,2,3), '$[0]')结果为第1个元素 |
| `JSONTOSTRING` | any | string | JSONTOSTRING(object), 根据fastjson包的JSON.toJSONString将JSON对象转换为字符串<br>例：JSONTOSTRING({'a':'b'}),结果为'{'a':'b'}' |
| `SORTED_JSONSTRING` | any | string | SORTED_JSONSTRING(object \| string), 可将JSON对象或JSON字符串转换为字段有序的字符串<br>例：SORTED_JSONSTRING({'b':1,'a':2}),结果为'{'a':2,'b':1}' |

### 系统函数（4）

| 函数 | 参数 | 返回 | 说明 |
|------|------|------|------|
| `USERID2UNIONID` | string, string | string | USERID2UNIONID(corpId, userId) 通过corpId与userId获取unionId<br>例：USERID2UNIONID('dingxxxxxx', 'manager922') 返回的结果是unionId |
| `UNIONID2USERID` | string, string | string | UNIONID2USERID(corpId, unionId) 通过corpId与unionId获取userId<br>例：UNIONID2USERID('dingxxxxxx', 'w0PUiPIbZBR8904NbXtLG7wiEiE') 返回的结果是userId |
| `BATCHUSERID2UNIONID` | string, collection | collection | BATCHUSERID2UNIONID(corpId, userIdList) 通过corpId与userId列表批量获取unionId列表<br>例：BATCHUSERID2UNIONID('dingxxxxxx', ['manager922', 'manager923']) 返回的结果是unionId列表 |
| `BATCHUNIONID2USERID` | string, collection | collection | BATCHUNIONID2USERID(corpId, unionIdList) 通过corpId与unionId列表批量获取userId列表<br>例：BATCHUNIONID2USERID('dingxxxxxx', ['w0PUiPIbZBR8904NbXtLG7wiEiE', 'w0PUiPIbZBR8904NbXtLG7wiEiF']) 返回的结果是userId列表 |
