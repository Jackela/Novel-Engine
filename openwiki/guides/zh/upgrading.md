# Upgrading

升级 Novel Engine 的方式是拉取新代码并重新构建镜像。你的手稿住在
`novel-engine-data` volume 里，升级永远不会碰它，而且工作室在每次启动时
都会准备自己的安全备份——所以升级是件例行公事。

## Before you upgrade

用[备份](backup-and-restore.md)流程往机器外拿一份副本。工作室每次启动都
会自动备份，但当升级期间磁盘坏掉时，真正救你的是那份放在移动硬盘或私人
云盘文件夹里的副本。

## Get the new code

- **如果你克隆了仓库**：在检出的文件夹里运行 `git pull`。
- **如果你下载的是 ZIP**：下载新的 ZIP，解压到一个**新的**文件夹，然后把
  你的 `.env` 复制进去——那里存着你的 provider key。如果你还为了改端口这
  类结构性调整建过 `compose.override.yaml`，把它也复制过去。旧文件夹留着
  或删掉都行；你的数据不在里面。

## Rebuild and restart

在包含 `compose.yaml` 的文件夹里：

```bash
docker compose up -d --build
```

重建需要几分钟（新代码要编译成新镜像）；用
`docker compose logs -f novel-engine` 看进度。

## What happens automatically on the first start

启动序列以固定的顺序保护你的数据：

1. **安全备份**——如果数据库存在，先往 `backups/` 写入一份带时间戳的副
   本。
2. **迁移**——数据库结构被自动升级到新版本的形态。
3. **对账**——导出记录和历史字数会与磁盘上的文件核对。
4. **任务恢复**——上次关闭时被打断的生成任务会被清理。

这之后工作室才开始对外服务。你的登录状态在升级后依然有效，因为会话密钥
存在数据 volume 里。

在浏览器打开 `http://localhost:8000/version` 确认新版本。

## What an upgrade does not do

- 它不删除、不重置数据：volume 在重建和容器替换之后留存。丢掉 volume 的
  唯一方式是 `docker compose down -v`。
- 它不把任何东西传到你机器之外。
- 它不能被简单地撤销：数据库结构只向前走。如果你之后必须运行旧版本，先
  恢复升级前的备份
  （[backup and restore](backup-and-restore.md#restoring)）。

## Upgrading from 0.3.x (the retired Python stack)

0.4.0 版是一次重写切换，它的数据库格式与 Python 时代毫无关系。Python 时
代的数据库无法迁移：用一个全新的数据目录启动 0.4.0 或更高版本，创建所有
者账户，再用 [README](../../../README.md#commands) 里的 import 命令重新导入
旧工作区。切换前的代码保留在 Git tag `python-final` 供参考。
