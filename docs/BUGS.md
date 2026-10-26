# 缺陷与验证状态

“已修复”表示实现和对应离线检查通过，不代表所有硬件已通过实机验收。

| 问题 | 证据与处理 | 状态 |
| --- | --- | --- |
| 驱动名单存在，实际镜像没有设备模块 | 原镜像有 82 个加载名称，但 ramdisk 不含这些模块。按现有固件依赖闭包补入 83 个模块，目录与加载器对齐 | 已修复打包并读回校验 |
| PRODUCT_COPY_FILES 使用绝对构建输出路径 | AOSP/AERA 会再拼 PRODUCT_OUT。改为将资源显式放入 recovery/root，并验证最终镜像内容 | 已修复 |
| 只加载 Goodix 内核模块，缺少 THP 程序 | 实机有 odm_tsc 和 libgdix_tsa_avr 等，原镜像没有。补入程序、dlopen 依赖及配置 | 实现完成，触摸待实测 |
| 触摸控制路径不存在 | 实机无 /sys/class/touch/touch_dev/enable_touch_raw；真实设备为 goodix_thp.0 | 删除错误等待和写入 |
| 触摸程序依赖解密后的 /data | 二进制使用 /data/vendor/touchscreen。按等长路径重定向至 /tmp，不要求解密或修改 userdata | 离线确认原路径已移除，运行待实测 |
| 模块顺序和固件版本不匹配 | 从当前 vendor_boot/vendor_dlkm/system_dlkm 获取模块，解析 .modinfo 递归排序，缺依赖直接失败 | 83 个模块依赖闭包通过 |
| 可选模块失败会挡住触摸启动 | 触摸启动条件改为 Goodix 和 touchscreen_mmi 已加载，不让电池/USB 的单独错误阻断触摸 | 已修复逻辑 |
| 写死槽位和解锁状态 | system.prop 包含空 slot_suffix、unlocked 常量。删除，保留 bootloader 实际值 | 静态检查通过 |
| 虚构补丁日期与无效日期格式 | 原配置使用 2099-12-31，vendor/boot 补丁被设置成 99.87.36。改为当前固件 2026-09-05 与 Android 16 | 源码和候选头/属性一致 |
| Wi-Fi 写入实机不存在的 fs_ready | 当前系统没有该节点，移除硬编码写入 | 已修复配置，Wi-Fi 待实测 |
| WLAN 就绪等待无期限 | 改为最多 30 秒并记录错误属性和日志 | Shell 语法检查通过 |
| supplicant 配置依赖未挂载的 vendor | 提供镜像内配置，运行时复制到 /tmp | 已打包校验，连接待实测 |
| socket 目录全局可写 | 0777 收紧为 0750 root:wifi | 已修复 |
| 重打包后文件哈希清单过期 | 每次重新生成 ramdisk-files.txt 和 ramdisk-files.sha256sum | 全量清单复核通过 |
| 下载未校验，失败后继续解压 | 下载记录固定 URL/SHA256，校验失败即停止 | 已实现 |
| Git 历史被删除、同步错误循环上千次 | 保留 repo/Git 信息，不再批量删除未知 manifest 项；失败保留日志 | 已修复构建脚本 |
| 预编译包覆盖下游 init 脚本 | 只导入内核/DTB/固件，不导入预编译包旧 rc；打包前验证 Northstar import | 已修复 |
| Windows AVB 使用 /dev/urandom | 显式传确定性 salt；官方工具复核签名和分区哈希 | 本地验证通过 |
| AVB 描述符要求 recovery.img 文件名 | 用临时硬链接提供分区名称，验证后自动清理 | 本地验证通过 |
| 上游模块去重未处理横杠/下划线 | 内核使用 qcom_scm 等名称，文件常为 qcom-scm.ko。源码补丁统一归一化；同时关闭提前返回时的目录句柄并检查模块拷贝失败 | 补丁已校验，仅应用于源码构建 |

仍需实机验收：触摸事件、屏幕旋转/映射、FBE 解密、MTP、fastbootd、Wi-Fi、电池/充电状态、重启/关机。没有把这些功能标成已修好。原镜像测试结果为“可启动、ADB 可用、触摸无反应”，已恢复原 recovery 并核对原分区哈希。

本仓库尚未完成全量源代码构建；Actions 提供手动构建入口。当前 beta 为经校验的重打包候选，不能冒充已从最新源代码完整编译或已通过硬件测试的正式版本。
