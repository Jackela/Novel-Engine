# Backup and restore

你的手稿是你机器上的一个 SQLite 文件，住在一个属于你的 Docker volume
里。没有任何东西存在别人的服务器上，也没有任何东西阻止你拿一份副本：本
页展示把这份文件备份、以及把一份副本放回去的受支持方式。

## Where your data physically lives

用 Docker Compose 时，所有状态都住在**named volume** `novel-engine-data`
里，它在容器内挂载于 `/app/data`：

| volume 中的路径 | 内容 |
|---|---|
| `novel-engine.sqlite3` | 数据库——每个项目、章节、修订和设置。这就是手稿本身。 |
| `backups/` | 带时间戳的安全副本（`.sqlite3.bak`），由你、也由工作室自己写入。 |
| `exports/` | 你的 Markdown/DOCX/EPUB 导出的归档副本。 |
| `.secret` | 首次启动时生成的会话密钥（会话因此能在重启后存活）。 |

这个 volume 会在 `docker compose stop`、`docker compose down`、删除容器、
重建以及[升级](upgrading.md)之后留存。只有 `docker compose down -v` 会删
掉它——**永久地**。对 `-v` 要像对手稿文件夹上的 `rm` 一样避让。

你可以用 `docker volume inspect novel-engine-data` 查看 Docker 把这个
volume 放在了磁盘哪里，但你永远不需要去那里：用下面的命令就好。

## Running CLI commands in Docker

工作室镜像里带着服务器自己用的同一个命令行工具。有一条规则很关键：
**backup 和 restore 以独占方式持有数据目录**，而正在运行的工作室已经持有
它。先停工作室，再跑命令，最后把工作室启动回来：

```bash
docker compose stop novel-engine
docker compose run --rm novel-engine node server/dist/apps/cli/main.js <command>
docker compose start novel-engine
```

如果忘了停这一步，命令会拒绝执行并提示
"The data directory is already owned by another Novel Engine process."，
不做任何改动。

## Backing up

```bash
docker compose stop novel-engine
docker compose run --rm novel-engine node server/dist/apps/cli/main.js backup
docker compose start novel-engine
```

`backup` 命令会在 backups 目录下写入一份一致的在线备份，并打印它的路径，
例如：

```text
/app/data/backups/novel-engine-20260913T093000123Z.sqlite3.bak
```

在一个还没有数据库的全新安装上，它会打印 `No database exists yet.`，什么
也不写。

把副本从 Docker 里拿到宿主机上，放进一个比如叫 `novel-engine-backups`
的文件夹：

```bash
docker compose cp novel-engine:/app/data/backups/. ./novel-engine-backups/
```

`docker compose cp` 需要服务的容器存在——`stop` 之后它还在；`down` 会把
容器删掉，所以要在 `down` 之前复制。尽可能把副本放到机器之外：一块移动
硬盘，或任何私人云盘文件夹。只活在原件旁边的备份不是备份。

工作室也在暗中保护你：**每一次启动**都会在触碰数据库之前先写一份带时间
戳的安全备份（迁移和升级因此可逆——见 [upgrading](upgrading.md)）。旧备
份永远不会被自动删除；请自己定期清理 `backups/` 目录。

## Restoring

`restore --input BACKUP` 先验证备份文件，备份当前数据库，然后原子地替换
它。对一份已经在 volume 里的备份运行：

```bash
docker compose stop novel-engine
docker compose run --rm novel-engine node server/dist/apps/cli/main.js restore \
  --input /app/data/backups/novel-engine-20260913T093000123Z.sqlite3.bak
docker compose start novel-engine
```

要从你宿主机上的一份副本恢复，先把它复制进 volume，再照上面继续：

```bash
docker compose cp ./novel-engine-backups/my-backup.sqlite3.bak \
  novel-engine:/app/data/backups/
```

成功的恢复会逐步报告：

```text
Verifying restore input: /app/data/backups/novel-engine-20260913T093000123Z.sqlite3.bak
Backed up the replaced database: /app/data/backups/novel-engine-20260913T100001456Z.sqlite3.bak
Restored the database: /app/data/novel-engine.sqlite3
```

可以依赖的行为：

- 输入先做完整性检查。缺失、为空或损坏的文件会**拒绝恢复且什么都不碰**。
- 被替换的数据库先拿到它自己的安全备份——恢复本身是可撤销的。
- 替换是原子的；一次失败的恢复绝不会留下一份写了一半的数据库。
- 恢复一个与当前运行中不同的数据库视为一次主动登出：工作室重启后请重新
  登录。

## Manual copy: the last resort

如果你只需要原始数据库文件——比如要搬去一台没有这份指南的机器——停掉工
作室，把文件从 volume 里复制出来：

```bash
docker compose stop novel-engine
docker run --rm -v novel-engine-data:/data -v "$PWD:/host" alpine \
  cp /data/novel-engine.sqlite3 /host/
docker compose start novel-engine
```

把文件复制回去就是同样的做法反过来。只要存在 `.bak` 文件，就优先用
`restore` 命令：它能验证裸复制无法验证的东西。只在工作室停止时复制文
件。`-v "$PWD:/host"` 这个挂载写法适用于 macOS 和 Linux 终端；在
Windows 上，请改用 `docker compose cp` 移动文件（见上文 "Backing up" 和
"Restoring"）。
