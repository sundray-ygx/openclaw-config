# Sing-box 代理服务文档

**位置**: `knowledge/tech/infrastructure/singbox/`  
**用途**: sing-box 代理服务的配置、脚本和报告

---

## 文件说明

| 文件 | 类型 | 用途 |
|------|------|------|
| `update_singbox_subscription.py` | Python脚本 | 解析VLESS订阅URL并自动更新sing-box配置 |
| `singbox_status.sh` | Bash脚本 | 查询sing-box运行状态、出口IP、节点统计 |
| `singbox_report.txt` | 文本报告 | 完整的sing-box服务状态报告（99个节点详情） |
| `README.md` | 说明文档 | 本文件 |

---

## 快速使用

### 查看状态
```bash
./singbox_status.sh
```

### 更新订阅
```bash
python3 update_singbox_subscription.py
```

---

## 服务配置

- **配置文件**: `/etc/sing-box/config.json`
- **监听端口**: 1080 (HTTP + SOCKS5)
- **容器管理**: Docker
- **总节点数**: 99个 (16个TROJAN + 83个VLESS Reality)

---

## 归档历史

- **2026-04-10**: 从 workspace 根目录迁移至此
