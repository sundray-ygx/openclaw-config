# 🔐 OpenClaw 配置安全检查报告

**检查时间**: 2026-03-23 09:00:23 (Asia/Shanghai)
**安全评分**: 85/100 (🟢 B)

## 检查结果

### 发现问题

- 🔴 **permissions**: 以 root 运行

### 通过检查项

- ✅ Gateway 绑定安全
- ✅ Gateway 使用 token 认证
- ✅ openclaw.json 权限正确
- ✅ 密钥配置检查完成

## 总结

本次检查发现 1 个低风险问题：当前以 root 用户运行 OpenClaw。建议在生产环境中使用非特权用户运行以降低潜在风险。

---
*Config Checker v1.0*
