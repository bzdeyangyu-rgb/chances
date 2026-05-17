# Self-Improving Template

## 使用说明

当执行 skill 时，如果出现以下情况，应在 `references/self-improving.md` 末尾追加记录：
- 现有主流程不能覆盖真实高频路径
- 排障后确认了新的失败模式
- 找到了更稳定的执行方法
- 发现了值得沉淀的新事实

记录原则：
1. 禁止修改主 `SKILL.md`
2. 所有新增经验、观察、排障结论，只能追加到 `references/self-improving.md`
3. `references/self-improving.md`只记录事实，不记录推断，不记录猜测
4. 两种记录类型必须分开写，不要混写

---

## Observation

用于记录一次执行中实际发生了什么，只写事实。

```text
[Observation]
Context: 当前任务背景
URL: 实际 URL；如果没有 URL，就写"无"
Page: 当前页面 / 界面的简洁描述
Action: 实际执行的动作
Target: 动作作用的目标对象
Coord: 使用到的坐标；如果不依赖坐标就写"无"
Result: 实际发生了什么，以及最终结果
Notes: 其他需要补充的事实
```

## Failure Pattern

用于记录经过确认的失败模式，只写事实。

```text
[Failure Pattern]
Context: 当前任务背景
URL: 实际 URL；如果没有 URL，就写"无"
Page: 当前页面 / 界面的简洁描述
Symptom: 失败现象
Checks Performed: 已经做过的检查
Resolution: 最终采用的处理方式
Notes: 其他需要补充的事实
```