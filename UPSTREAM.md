# 来源与署名

Northstar Recovery 是独立的 avr 适配分支，不是从零编写的 Recovery，也不代表上游官方版本。

| 层次 | 来源 | 本分支基线 |
| --- | --- | --- |
| 设备树 | [qingxin94/avr-recovery](https://github.com/qingxin94/avr-recovery) | `ccb833314bd543ac017bfdb5a9782513c79d665e` |
| Recovery 引擎 | [AERA-Recovery/android_bootable_recovery](https://github.com/AERA-Recovery/android_bootable_recovery) | `5508665b35f8598262fe6eb63e04c27dd04e971c` |
| 构建系统 | [AERA-Recovery/android_build_make](https://github.com/AERA-Recovery/android_build_make) | `ee2c190b1387f8db94c958ce0aea81773294688c` |
| 原始候选镜像引擎 | AERA Recovery | 镜像自报 `e37b7ce3fbb147f7b29baa690c398fc57254090e`，仅作为自报信息 |
| AVB 工具和公开测试密钥 | [Android Open Source Project](https://android.googlesource.com/platform/external/avb/+/refs/tags/android-16.0.0_r1/) | `android-16.0.0_r1`，下载时校验 SHA256 |

感谢 qingxin94 的设备树和预编译资源、AERA Recovery 项目，以及 TeamWin、OrangeFox、Android Recovery 等历史上游贡献者。原有版权头、命名空间和许可证声明保留。原仓库完整 Git 历史保留在本地工作区；公开仓库以源码快照导入，并以上表的准确提交号追溯来源，避免把历史二进制资源再次复制进 Git。界面中的上游归属放在“关于”页，文件系统另有 `/system/etc/northstar/credits.txt`。

本分支新增的 Python/Shell 工具和 `assets/northstar.svg` 采用 MIT 许可，详见 `LICENSE-NORTHSTAR`。原有代码仍遵守各自文件中的许可；本仓库不对没有许可声明的上游文件自行授予额外许可。

设备驱动和 Goodix 用户态程序来自用户授权读取的 XT2611-1 当前固件，权利归各厂商所有。只提取运行需要的模块、程序和公开固件配置；不包含用户数据、密钥、分区序列号或账户文件。这里的工具代码许可不覆盖这些厂商二进制文件。

品牌名称和图标已更换为 Northstar。构建变量、接口、内部存储路径保留上游名称以维持兼容；这些内部符号不表示仍使用上游品牌对外发布。
