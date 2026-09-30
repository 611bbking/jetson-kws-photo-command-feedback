# 项目摘要
现在我们在做麦克风的收音和放音功能，基于KMS模型，需要能收到关键词唤醒，然后收到特定词后回应，收到关键词回到唤醒前，麦克风连接的Jetson Nano Super，代码需要在本机win11系统写好，通过ssh放到Jetson的项目目录~/Documents/voice/

# Jetson Nano Super的接线方式
| Jetson Orin Nano Super | 模块 | 作用 |
|---|---|---|
| Pin 2 或 4 | VCC | 5V 供电 |
| Pin 6 | GND | 地 |
| Pin 12 | BCLK / SCK | I2S 位时钟 |
| Pin 35 | LRCLK / WS | 左右声道时钟 |
| Pin 40 | DIN | Jetson 输出到播放器 |
| Pin 38 | SD | 麦克风输出到 Jetson |

# ssh配置，端口默认22
Host 10.176.16.102
    HostName 10.176.16.102
    User jetson