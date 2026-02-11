# 3D模型目录

将FBX格式的3D模型文件放在此目录下。

## 支持的格式

- **FBX** (.fbx) - Autodesk FBX格式，支持二进制和ASCII

## 模型要求

### 性能建议

| 参数 | 建议值 |
|------|--------|
| 多边形数 | < 10,000 面 |
| 骨骼数 | < 100 |
| 材质数 | < 10 |
| 纹理大小 | < 2048x2048 |
| 文件大小 | < 10 MB |

### 动画支持

- 骨骼动画 (Skeleton Animation)
- 关键帧动画 (Keyframe Animation)
- 混合形状 (Blend Shapes) - 用于口型同步

## 推荐模型来源

### 免费资源

1. **Mixamo** (https://www.mixamo.com)
   - 免费角色模型
   - 自带动画
   - 可直接下载FBX

2. **Sketchfab** (https://sketchfab.com)
   - 大量免费模型
   - 支持FBX下载

3. **TurboSquid** (https://www.turbosquid.com)
   - 免费和付费模型

### 付费资源

1. **Unity Asset Store**
2. **Unreal Engine Marketplace**
3. **CGTrader**

## 模型设置

### 在Blender中导出FBX

1. 选择要导出的模型
2. 文件 → 导出 → FBX
3. 设置:
   - 选中物体: ✓
   - 动画: ✓ (如果需要)
   - 骨骼: ✓ (如果需要)
   - 应用变换: ✓

### 在Maya中导出FBX

1. 选择要导出的模型
2. 文件 → 导出选择
3. 文件类型: FBX export
4. 设置:
   - 动画: ✓ (如果需要)
   - 骨骼: ✓ (如果需要)
   - 烘焙动画: ✓

## 默认模型

如果没有提供FBX文件，应用将显示一个默认的彩色立方体。

要添加自定义模型:

1. 将FBX文件复制到此目录
2. 重命名为 `default.fbx` 或修改配置文件
3. 重启应用

## 口型同步

要实现口型同步，模型需要:

1. 面部骨骼或混合形状
2. 嘴部开合的控制器

应用会根据语音音量自动控制嘴部开合度。
