# 验证与回退

只适配 Lenovo XT2611-1 / avr。当前二进制基线为内核 `6.12.58-android16-6-gb0a9599c6c01-ab14987696-4k`、2026-09-05 安全补丁。其他固件需要重新提取并验证模块，不能只看“6.12.58”就判断兼容。

## 已做的离线检查

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python tools/validate.py
python tools/validate.py --image recovery.img
```

打包工具另行校验输入镜像 SHA256、模块/用户态依赖、每个设备资源的哈希、128 MiB 分区大小、AVB RSA4096 签名和内容哈希。CI 结果见 Actions，不能把 CI 通过理解为触摸已经可用。

## 实机验收顺序

1. 核实型号、Bootloader 解锁状态、当前槽位和 recovery 分区大小，先备份当前槽位 recovery，并核验备份 SHA256。
2. 仅刷入当前槽位 recovery，保留另一个槽位与原 boot/vendor_boot；不切换槽位，不擦除数据。
3. 先确认 ADB，再查看 `/tmp/northstar-modules.log`、`/tmp/northstar-touch.log`、`/proc/bus/input/devices` 和 `dmesg`。检查是否有 `gdix_input_agent` 输入节点及实际触摸事件。
4. 确认触摸后再测试 UI、解密、MTP、Wi-Fi、fastbootd 与电池。任何格式化、清除和安装操作都需用户明确选择。
5. 失败时在 Fastboot 把刷入前的 recovery 备份写回原槽位，再重启系统。回到系统后读取该分区 SHA256，确认与备份一致。

本项目使用公开测试密钥签名，不能重新锁定 Bootloader 来运行它。常量 `ro.boot.*` 不用于伪装解锁状态。

## 品牌边界

源码构建使用完整 Northstar 名称、北极星图标，“关于”保留 AERA 与 qingxin94 归属。重打包 beta 为保持 ELF 字符串长度，少量标题使用 `STAR Recovery` / `About STAR`；内核接口、文件路径、版权署名中的上游名字保留。完整界面布局须以源码构建和实机截图验收。
