#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速训练脚本 - 用于快速测试和调试
"""

from train_model import main

if __name__ == "__main__":
    # 快速训练，使用较少的数据
    print("🚀 快速训练模式")
    main(data_size=5000, use_existing_data=False)