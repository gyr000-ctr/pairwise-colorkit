# pairwise-colorkit

## 题面（可直接粘贴）

多租户图像服务接入 HDR 素材后颜色整体发灰：同一 profile 的转换结果在并发请求间互相污染、缓存不区分管线版本导致 v1 与 v2 结果串台、超色域像素在 v1 被静默裁剪而在 v2 应保留、缓存计数在切换版本后不归零。colorkit/core.py 是核心，tests/test_core.py 15 个红。要修的是：一次转换与批量转换逐元素一致；并发与串行结果一致且缓存命中计数正确；缓存键必须含版本；v1 裁剪到 [0,1] 而 v2 保留超范围；未知色彩空间、非法版本、NaN 抛 ValueError。

## 运行方式

```bash
python -m pytest tests -q
```

初始结果应为 `15 failed`（全部因 `NotImplementedError` 失败，无 collection error）。

## 字段

- 所属领域：游戏、图形与多媒体
- 子方向：图像处理
- 任务类型：Bugfix
- 语言/框架：Python 3, pytest
- 环境可复现等级：无外部依赖
